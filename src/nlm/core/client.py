"""NotebookLM API client.

This client uses Google's batchexecute RPC protocol to interact with NotebookLM.
Ported from notebooklm-mcp with matching signatures for easy maintenance.
"""

import json
import os
import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from nlm.core.auth import AuthManager, get_auth_manager
from nlm.core.exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    NLMError,
)
from nlm.core.auth_refresh import has_fresher_tokens_on_disk, run_headless_auth
from nlm.core import constants


# ============================================================================
# Constants (ported from MCP)
# ============================================================================

BASE_URL = "https://notebooklm.google.com"
BATCHEXECUTE_URL = f"{BASE_URL}/_/LabsTailwindUi/data/batchexecute"

# Timeout constants
SOURCE_ADD_TIMEOUT = 120.0  # Extended timeout for adding sources (URLs, Drive, etc.)

# Ownership constants
OWNERSHIP_MINE = 1
OWNERSHIP_SHARED = 2


# ============================================================================
# RPC IDs (ported from MCP)
# ============================================================================

class RPC:
    """Known RPC IDs for NotebookLM batchexecute API."""
    
    # Notebook operations
    LIST_NOTEBOOKS = "wXbhsf"
    GET_NOTEBOOK = "rLM1Ne"
    CREATE_NOTEBOOK = "CCqFvf"
    RENAME_NOTEBOOK = "s0tc2d"  # Also used for chat configuration
    DELETE_NOTEBOOK = "WWINqb"
    
    # Source operations
    ADD_SOURCE = "izAoDd"  # URL, text, and Drive sources
    GET_SOURCE = "hizoJc"
    CHECK_FRESHNESS = "yR9Yof"
    SYNC_DRIVE = "FLmJqe"
    DELETE_SOURCE = "tGMBJ"
    
    # Summary operations
    GET_SUMMARY = "VfAZjd"  # Notebook summary
    GET_SOURCE_GUIDE = "tr032e"  # Source summary + keywords
    
    # Research operations
    START_FAST_RESEARCH = "Ljjv0c"
    START_DEEP_RESEARCH = "QA9ei"
    POLL_RESEARCH = "e3bVqc"
    IMPORT_RESEARCH = "LBwxtb"
    
    # Studio operations
    CREATE_STUDIO = "R7cb6c"
    POLL_STUDIO = "gArtLc"
    DELETE_STUDIO = "V5N4be"
    
    # Mind map operations
    GENERATE_MIND_MAP = "yyryJe"
    SAVE_MIND_MAP = "CYK0Xb"
    LIST_MIND_MAPS = "cFji9"
    DELETE_MIND_MAP = "AH0mwd"


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation (query + response)."""
    query: str
    answer: str
    turn_number: int


@dataclass
class Notebook:
    """Represents a NotebookLM notebook."""
    id: str
    title: str
    source_count: int = 0
    sources: list[dict] | None = None
    is_owned: bool = True
    is_shared: bool = False
    created_at: str | None = None
    modified_at: str | None = None
    
    @property
    def url(self) -> str:
        return f"https://notebooklm.google.com/notebook/{self.id}"
    
    @property
    def ownership(self) -> str:
        return "owned" if self.is_owned else "shared_with_me"


@dataclass
class SourceContent:
    """Represents raw source content data."""
    title: str
    source_type: str
    content: str
    char_count: int


@dataclass
class SourceGuide:
    """Represents AI-generated source guide (summary + keywords)."""
    summary: str
    keywords: list[str]


@dataclass
class DriveSource:
    """Represents a Drive source with sync status."""
    id: str
    title: str
    is_stale: bool
    type: str = "drive"
    original_type: str | None = None



def _parse_timestamp(ts_array: list | None) -> str | None:
    """Convert [seconds, nanoseconds] timestamp array to ISO format string."""
    if not ts_array or not isinstance(ts_array, list) or len(ts_array) < 1:
        return None
    try:
        seconds = ts_array[0]
        if not isinstance(seconds, (int, float)):
            return None
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OSError, OverflowError):
        return None


def _parse_notebook_data(nb_data: list) -> Notebook | None:
    """Parse raw notebook data array into a Notebook object."""
    if not isinstance(nb_data, list) or len(nb_data) < 3:
        return None
    
    title = nb_data[0] if isinstance(nb_data[0], str) else "Untitled"
    sources_data = nb_data[1] if len(nb_data) > 1 else []
    notebook_id = nb_data[2] if len(nb_data) > 2 else None
    
    if not notebook_id:
        return None
    
    is_owned = True
    is_shared = False
    created_at = None
    modified_at = None
    
    if len(nb_data) > 5 and isinstance(nb_data[5], list) and len(nb_data[5]) > 0:
        metadata = nb_data[5]
        is_owned = metadata[0] == constants.OWNERSHIP_MINE
        if len(metadata) > 1:
            is_shared = bool(metadata[1])
        if len(metadata) > 5:
            modified_at = _parse_timestamp(metadata[5])
        if len(metadata) > 8:
            created_at = _parse_timestamp(metadata[8])
    
    sources = []
    if isinstance(sources_data, list):
        for src in sources_data:
            if isinstance(src, list) and len(src) >= 2:
                src_ids = src[0] if src[0] else []
                src_title = src[1] if len(src) > 1 else "Untitled"
                src_id = src_ids[0] if isinstance(src_ids, list) and src_ids else src_ids
                
                # Extract source type and URL from metadata
                source_type = "unknown"
                url = ""
                
                if len(src) > 2 and isinstance(src[2], list):
                    metadata = src[2]
                    if len(metadata) > 4:
                        type_code = metadata[4]
                        source_type = constants.SOURCE_TYPES.get_name(type_code)
                    
                    # Extract URL (index 7)
                    # For web/youtube: metadata[7] -> ["https://..."]
                    if len(metadata) > 7 and isinstance(metadata[7], list) and len(metadata[7]) > 0:
                        potential_url = metadata[7][0]
                        if isinstance(potential_url, str):
                            url = potential_url
                
                sources.append({
                    "id": src_id, 
                    "title": src_title, 
                    "type": source_type,
                    "url": url
                })
    
    return Notebook(
        id=notebook_id,
        title=title,
        source_count=len(sources),
        sources=sources,
        is_owned=is_owned,
        is_shared=is_shared,
        created_at=created_at,
        modified_at=modified_at,
    )


# ============================================================================
# Client class (matching MCP signatures)
# ============================================================================


class NotebookLMClient:
    """Client for interacting with the NotebookLM API.
    
    Uses Google's batchexecute RPC protocol. Method signatures match
    notebooklm-mcp for easy maintenance.
    """
    
    # Query endpoint (different from batchexecute - streaming gRPC-style)
    QUERY_ENDPOINT = "/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed"
    
    # Headers for page fetch
    _PAGE_FETCH_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }
    
    def __init__(
        self,
        auth_manager: AuthManager | None = None,
        profile: str | None = None,
        cookies: dict[str, str] | None = None,
        csrf_token: str = "",
        session_id: str = "",
    ) -> None:
        """
        Initialize the client.
        
        Args:
            auth_manager: AuthManager instance (preferred).
            profile: Profile name to use (creates AuthManager if auth_manager not provided).
            cookies: Dict of cookies (alternative to auth_manager, for MCP compatibility).
            csrf_token: CSRF token (optional - auto-extracted if not provided).
            session_id: Session ID (optional - auto-extracted if not provided).
        """
        # Support both AuthManager and direct cookies (for MCP compatibility)
        if auth_manager:
            self.auth = auth_manager
            self.cookies = auth_manager.get_cookies()
            self.csrf_token = csrf_token or (auth_manager.load_profile().csrf_token or "")
            self._session_id = session_id or (auth_manager.load_profile().session_id or "")
        elif cookies:
            self.auth = None
            self.cookies = cookies
            self.csrf_token = csrf_token
            self._session_id = session_id
        else:
            self.auth = get_auth_manager(profile)
            self.cookies = self.auth.get_cookies()
            profile_obj = self.auth.load_profile()
            self.csrf_token = csrf_token or (profile_obj.csrf_token or "")
            self._session_id = session_id or (profile_obj.session_id or "")
        
        self._client: httpx.Client | None = None
        
        # Conversation cache for follow-up queries
        self._conversation_cache: dict[str, list[ConversationTurn]] = {}
        
        # Request counter for query endpoint
        import random
        self._reqid_counter = random.randint(100000, 999999)
        
        # Refresh CSRF token if not provided
        if not self.csrf_token:
            self._refresh_auth_tokens()
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None
    
    def __enter__(self) -> "NotebookLMClient":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()
    
    # =========================================================================
    # Core RPC Infrastructure (ported from MCP)
    # =========================================================================
    
    def _refresh_auth_tokens(self) -> None:
        """Refresh CSRF token and session ID by fetching NotebookLM page."""
        cookie_header = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        headers = {**self._PAGE_FETCH_HEADERS, "Cookie": cookie_header}
        
        with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
            response = client.get(f"{BASE_URL}/")
            
            if "accounts.google.com" in str(response.url):
                raise AuthenticationError(
                    message="Cookies have expired",
                    hint="Run 'nlm login' to re-authenticate.",
                )
            
            if response.status_code != 200:
                raise NetworkError(
                    message=f"Failed to fetch NotebookLM page: HTTP {response.status_code}",
                    hint="Check your internet connection.",
                )
            
            html = response.text
            
            # Extract CSRF token (SNlM0e)
            csrf_match = re.search(r'"SNlM0e":"([^"]+)"', html)
            if csrf_match:
                self.csrf_token = csrf_match.group(1)
            
            # Extract session ID (FdrFJe)
            sid_match = re.search(r'"FdrFJe":"([^"]+)"', html)
            if sid_match:
                self._session_id = sid_match.group(1)
            
            # Update profile if we have auth manager
            if self.auth and self.csrf_token:
                try:
                    self.auth.save_profile(
                        cookies=self.cookies,
                        csrf_token=self.csrf_token,
                        session_id=self._session_id,
                    )
                except Exception:
                    pass  # Caching is optional
    
    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            self._client = httpx.Client(
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Origin": BASE_URL,
                    "Referer": f"{BASE_URL}/",
                    "Cookie": cookie_str,
                    "X-Same-Domain": "1",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                },
                timeout=30.0,
            )
        return self._client
    
    def _build_request_body(self, rpc_id: str, params: Any) -> str:
        """Build the batchexecute request body."""
        params_json = json.dumps(params, separators=(',', ':'))
        f_req = [[[rpc_id, params_json, None, "generic"]]]
        f_req_json = json.dumps(f_req, separators=(',', ':'))
        
        body_parts = [f"f.req={urllib.parse.quote(f_req_json, safe='')}"]
        if self.csrf_token:
            body_parts.append(f"at={urllib.parse.quote(self.csrf_token, safe='')}")
        
        return "&".join(body_parts) + "&"
    
    def _build_url(self, rpc_id: str, source_path: str = "/") -> str:
        """Build the batchexecute URL with query params."""
        params = {
            "rpcids": rpc_id,
            "source-path": source_path,
            "bl": os.environ.get("NOTEBOOKLM_BL", "boq_labs-tailwind-frontend_20260108.06_p0"),
            "hl": "en",
            "rt": "c",
        }
        if self._session_id:
            params["f.sid"] = self._session_id
        
        query = urllib.parse.urlencode(params)
        return f"{BATCHEXECUTE_URL}?{query}"
    
    def _parse_response(self, response_text: str) -> list:
        """Parse the batchexecute response."""
        # Remove anti-XSSI prefix
        if response_text.startswith(")]}'"):
            response_text = response_text[4:]
        
        lines = response_text.strip().split("\n")
        results = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            try:
                int(line)  # byte count
                i += 1
                if i < len(lines):
                    try:
                        data = json.loads(lines[i])
                        results.append(data)
                    except json.JSONDecodeError:
                        pass
                i += 1
            except ValueError:
                try:
                    data = json.loads(line)
                    results.append(data)
                except json.JSONDecodeError:
                    pass
                i += 1
        
        return results
    
    def _extract_rpc_result(self, parsed_response: list, rpc_id: str) -> Any:
        """Extract the result for a specific RPC ID from parsed response."""
        for chunk in parsed_response:
            if isinstance(chunk, list):
                for item in chunk:
                    if isinstance(item, list) and len(item) >= 3:
                        if item[0] == "wrb.fr" and item[1] == rpc_id:
                            # Check for generic error signature (e.g. auth expired)
                            # Signature: ["wrb.fr", "RPC_ID", null, null, null, [16], "generic"]
                            if len(item) > 6 and item[6] == "generic" and isinstance(item[5], list) and 16 in item[5]:
                                from nlm.core.exceptions import AuthenticationError
                                raise AuthenticationError(
                                    message="Unable to fetch data - authentication may have expired (Code 16)",
                                    hint="Run 'nlm login' to re-authenticate."
                                )

                            result_str = item[2]
                            if isinstance(result_str, str):
                                try:
                                    return json.loads(result_str)
                                except json.JSONDecodeError:
                                    return result_str
                            return result_str
        return None
    
    def _call_rpc(
        self,
        rpc_id: str,
        params: Any,
        path: str = "/",
        timeout: float | None = None,
        _retry: bool = False,
        _deep_retry: bool = False,
    ) -> Any:
        """Execute an RPC call and return the extracted result.
        
        Includes automatic retry on auth failures with three-layer recovery:
        1. Refresh CSRF/session tokens (fast, handles token expiry)
        2. Reload cookies from disk (handles external re-authentication)
        3. Run headless auth (auto-refresh if Chrome profile has saved login)
        """
        from nlm.core.exceptions import AuthenticationError
        
        client = self._get_client()
        body = self._build_request_body(rpc_id, params)
        url = self._build_url(rpc_id, path)
        
        try:
            if timeout:
                response = client.post(url, content=body, timeout=timeout)
            else:
                response = client.post(url, content=body)
            
            response.raise_for_status()
            
            # Parse and extract RPC result (may raise AuthenticationError on Code 16)
            parsed = self._parse_response(response.text)
            result = self._extract_rpc_result(parsed, rpc_id)
            
            # Check for null result on list_notebooks (another auth failure symptom)
            if result is None and rpc_id == RPC.LIST_NOTEBOOKS:
                raise AuthenticationError(
                    message="Unable to fetch notebooks - authentication may have expired",
                    hint="Run 'nlm login' to re-authenticate.",
                )
            
            return result
            
        except (httpx.HTTPStatusError, AuthenticationError) as e:
            # Check for auth failures (401/403 HTTP or RPC Error 16)
            is_http_auth = isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (401, 403)
            is_rpc_auth = isinstance(e, AuthenticationError)
            
            if not (is_http_auth or is_rpc_auth):
                if isinstance(e, httpx.RequestError):
                    raise NetworkError(
                        message=f"Request failed: {e}",
                        hint="Check your internet connection.",
                    ) from e
                raise

            # Layer 1: Refresh CSRF/session tokens (first retry only)
            if not _retry:
                try:
                    self._refresh_auth_tokens()
                    self._client = None
                    return self._call_rpc(rpc_id, params, path, timeout, _retry=True)
                except Exception:
                    # CSRF refresh failed (cookies expired) - continue to layer 2
                    pass
            
            # Layer 2 & 3: Reload from disk or run headless auth (deep retry)
            if not _deep_retry and self.auth:
                if self._try_reload_or_headless_auth():
                    self._client = None
                    # Update internal auth state from profile
                    profile = self.auth.load_profile(force_reload=True)
                    self.cookies = profile.cookies
                    self.csrf_token = profile.csrf_token
                    self._session_id = profile.session_id
                    
                    return self._call_rpc(
                        rpc_id, params, path, timeout, _retry=True, _deep_retry=True
                    )
            
            # Re-raise if already retried or recovery failed
            if is_http_auth:
                raise AuthenticationError(
                    message="Authentication failed or session expired",
                    hint="Your session has expired. Run 'nlm login' to re-authenticate.",
                ) from e
            raise
            
        except httpx.RequestError as e:
            raise NetworkError(
                message=f"Request failed: {e}",
                hint="Check your internet connection.",
            ) from e

    def _try_reload_or_headless_auth(self) -> bool:
        """Try to recover authentication by reloading from disk or running headless auth.
        
        Returns:
             True if new valid tokens were obtained and saved to profile.
        """
        if not self.auth:
            return False
            
        # Layer 2: Check if disk has fresher tokens
        try:
            current_profile = self.auth.load_profile()
            fresher = has_fresher_tokens_on_disk(current_profile)
            if fresher:
                # AuthManager handles the loading, so we just need to report success
                # The caller will reload the profile from disk
                return True
        except Exception:
            pass
            
        # Layer 3: Headless Chrome Auth
        try:
            tokens = run_headless_auth()
            if tokens:
                # Save new tokens to profile
                self.auth.save_profile(
                    cookies=tokens["cookies"],
                    csrf_token=tokens["csrf_token"],
                    session_id=tokens["session_id"],
                )
                return True
        except Exception:
            pass
            
        return False
    
    # =========================================================================
    # Notebook Operations (matching MCP signatures)
    # =========================================================================
    
    def list_notebooks(self, debug: bool = False) -> list[Notebook]:
        """List all notebooks."""
        params = [None, 1, None, [2]]
        result = self._call_rpc(RPC.LIST_NOTEBOOKS, params)
        
        notebooks = []
        if result and isinstance(result, list):
            notebook_list = result[0] if result and isinstance(result[0], list) else result
            
            for nb_data in notebook_list:
                notebook = _parse_notebook_data(nb_data)
                if notebook:
                    notebooks.append(notebook)
        
        return notebooks
    
    def get_notebook(self, notebook_id: str) -> Notebook | None:
        """Get notebook details."""
        result = self._call_rpc(
            RPC.GET_NOTEBOOK,
            [notebook_id, None, [2], None, 0],
            f"/notebook/{notebook_id}",
        )
        
        # Result is [[notebook_data]] - extract the inner list
        if result and isinstance(result, list) and len(result) > 0:
            nb_data = result[0]
            return _parse_notebook_data(nb_data)
        return None
    
    def create_notebook(self, title: str = "") -> Notebook | None:
        """Create a new notebook."""
        params = [title, None, None, [2], [1, None, None, None, None, None, None, None, None, None, [1]]]
        result = self._call_rpc(RPC.CREATE_NOTEBOOK, params)
        
        if result and isinstance(result, list) and len(result) >= 3:
            notebook_id = result[2]
            if notebook_id:
                return Notebook(
                    id=notebook_id,
                    title=title or "Untitled notebook",
                    source_count=0,
                    sources=[],
                )
        return None
    
    def rename_notebook(self, notebook_id: str, new_title: str) -> bool:
        """Rename a notebook."""
        params = [notebook_id, [[None, None, None, [None, new_title]]]]
        result = self._call_rpc(RPC.RENAME_NOTEBOOK, params, f"/notebook/{notebook_id}")
        return result is not None
    
    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook."""
        params = [[notebook_id], [2]]
        result = self._call_rpc(RPC.DELETE_NOTEBOOK, params)
        return result is not None
    
    def get_notebook_summary(self, notebook_id: str) -> dict[str, Any]:
        """Get AI-generated summary and suggested topics for a notebook."""
        result = self._call_rpc(RPC.GET_SUMMARY, [notebook_id, [2]], f"/notebook/{notebook_id}")
        
        summary = ""
        suggested_topics = []
        
        if result and isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list) and len(result[0]) > 0:
                summary = result[0][0]
            
            if len(result) > 1 and result[1]:
                topics_data = result[1][0] if isinstance(result[1], list) and len(result[1]) > 0 else []
                for topic in topics_data:
                    if isinstance(topic, list) and len(topic) >= 2:
                        suggested_topics.append({
                            "question": topic[0],
                            "prompt": topic[1],
                        })
        
        return {
            "summary": summary,
            "suggested_topics": suggested_topics,
        }
    
    # =========================================================================
    # Source Operations (matching MCP signatures)
    # =========================================================================
    
    def list_sources(self, notebook_id: str) -> list[dict]:
        """List all sources in a notebook."""
        notebook = self.get_notebook(notebook_id)
        
        if notebook and notebook.sources:
            # Add 'type' field if missing (sources from Notebook don't have type)
            sources = []
            for src in notebook.sources:
                sources.append({
                    "id": src.get("id", ""),
                    "title": src.get("title", "Untitled"),
                    "type": src.get("type", "unknown"),
                    "url": src.get("url", ""),
                })
            return sources
        
        return []
    
    def add_source_url(self, notebook_id: str, url: str, timeout: float | None = None) -> dict | None:
        """Add a URL source to a notebook.
        
        Uses extended timeout (120s) by default for slow-loading URLs.
        """
        if timeout is None:
            timeout = SOURCE_ADD_TIMEOUT
        
        # YouTube URLs use different position than regular URLs
        is_youtube = "youtube.com" in url or "youtu.be" in url
        
        if is_youtube:
            source_data = [None, None, None, None, None, None, None, [url], None, None, 1]
        else:
            source_data = [None, None, [url], None, None, None, None, None, None, None, 1]
        
        params = [[source_data], notebook_id, [2], [1, None, None, None, None, None, None, None, None, None, [1]]]
        return self._call_rpc(RPC.ADD_SOURCE, params, f"/notebook/{notebook_id}", timeout=timeout)
    
    def add_source_text(self, notebook_id: str, text: str, title: str = "Pasted Text", timeout: float | None = None) -> dict | None:
        """Add a text source to a notebook.
        
        Uses extended timeout (120s) by default for large text sources.
        """
        if timeout is None:
            timeout = SOURCE_ADD_TIMEOUT
        
        source_data = [None, [title, text], None, 2, None, None, None, None, None, None, 1]
        params = [[source_data], notebook_id, [2], [1, None, None, None, None, None, None, None, None, None, [1]]]
        return self._call_rpc(RPC.ADD_SOURCE, params, f"/notebook/{notebook_id}", timeout=timeout)
    
    def add_source_drive(
        self,
        notebook_id: str,
        document_id: str,
        title: str,
        doc_type: str = "doc",
        timeout: float | None = None,
    ) -> dict | None:
        """Add a Google Drive document as a source.
        
        Uses extended timeout (120s) by default for large files like presentations.
        """
        # Use extended timeout for Drive sources (large files can take 60s+)
        if timeout is None:
            timeout = SOURCE_ADD_TIMEOUT
        mime_types = {
            "doc": "application/vnd.google-apps.document",
            "slides": "application/vnd.google-apps.presentation",
            "sheets": "application/vnd.google-apps.spreadsheet",
            "pdf": "application/pdf",
        }
        mime_type = mime_types.get(doc_type, mime_types["doc"])
        
        source_data = [[document_id, mime_type, 1, title], None, None, None, None, None, None, None, None, None, 1]
        params = [[source_data], notebook_id, [2], [1, None, None, None, None, None, None, None, None, None, [1]]]
        return self._call_rpc(RPC.ADD_SOURCE, params, f"/notebook/{notebook_id}", timeout=timeout)
    
    def get_source(self, source_id: str) -> dict | None:
        """Get source details."""
        params = [[source_id], [2], [2]]
        return self._call_rpc(RPC.GET_SOURCE, params)
    
    def get_source_guide(self, source_id: str) -> "SourceGuide":
        """Get AI-generated summary and keywords for a source."""
        result = self._call_rpc(RPC.GET_SOURCE_GUIDE, [[[[source_id]]]])
        
        summary = ""
        keywords = []
        
        if result and isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list):
                if len(result[0]) > 0 and isinstance(result[0][0], list):
                    inner = result[0][0]
                    if len(inner) > 1 and isinstance(inner[1], list) and len(inner[1]) > 0:
                        summary = inner[1][0]
                    if len(inner) > 2 and isinstance(inner[2], list) and len(inner[2]) > 0:
                        keywords = inner[2][0] if isinstance(inner[2][0], list) else []
        
        return SourceGuide(summary=summary, keywords=keywords)
    
    def describe_source(self, source_id: str) -> "SourceGuide":
        """Alias for get_source_guide (for CLI compatibility)."""
        return self.get_source_guide(source_id)
    
    def get_source_content(self, source_id: str) -> "SourceContent":
        """Get raw text content of a source (no AI processing).
        
        Returns the original indexed text from PDFs, web pages, pasted text,
        or YouTube transcripts.
        """
        params = [[source_id], [2], [2]]
        result = self._call_rpc(RPC.GET_SOURCE, params, "/")
        
        content = ""
        title = ""
        source_type = ""
        url = None
        
        if result and isinstance(result, list):
            # Extract from result[0] which contains source metadata
            if len(result) > 0 and isinstance(result[0], list):
                source_meta = result[0]
                
                # Title is at position 1
                if len(source_meta) > 1 and isinstance(source_meta[1], str):
                    title = source_meta[1]
                
                # Metadata is at position 2
                if len(source_meta) > 2 and isinstance(source_meta[2], list):
                    metadata = source_meta[2]
                    # Source type code is at position 4
                    if len(metadata) > 4:
                        type_code = metadata[4]
                        source_type = constants.SOURCE_TYPES.get_name(type_code)
                    
                    # URL might be at position 7 for web sources
                    if len(metadata) > 7 and isinstance(metadata[7], list):
                        url_info = metadata[7]
                        if len(url_info) > 0 and isinstance(url_info[0], str):
                            url = url_info[0]
            
            # Extract content from result[3][0] - array of content blocks
            if len(result) > 3 and isinstance(result[3], list):
                content_wrapper = result[3]
                if len(content_wrapper) > 0 and isinstance(content_wrapper[0], list):
                    content_blocks = content_wrapper[0]
                    # Collect all text from content blocks
                    text_parts = []
                    for block in content_blocks:
                        if isinstance(block, list):
                            texts = self._extract_all_text(block)
                            text_parts.extend(texts)
                    content = "\n\n".join(text_parts)
        
        return SourceContent(
            title=title,
            source_type=source_type,
            content=content,
            char_count=len(content),
        )
    
    def _extract_all_text(self, data: list) -> list[str]:
        """Recursively extract all text strings from nested arrays."""
        texts = []
        for item in data:
            if isinstance(item, str) and len(item) > 0:
                texts.append(item)
            elif isinstance(item, list):
                texts.extend(self._extract_all_text(item))
        return texts
    
    def delete_source(self, source_id: str) -> bool:
        """Delete a source."""
        params = [[[source_id]], [2]]
        result = self._call_rpc(RPC.DELETE_SOURCE, params)
        return result is not None
    
    def list_drive_sources(self, notebook_id: str, check_freshness: bool = True) -> list[DriveSource]:
        """List all Drive sources and their freshness status.
        
        Args:
            notebook_id: The notebook to list Drive sources from.
            check_freshness: If True (default), check freshness for each source.
                           If False, skip freshness checks for faster listing.
        """
        sources = self.list_sources(notebook_id)
        drive_sources = []
        
        for s in sources:
            # Check freshness for potential Drive sources
            # Only check explicit 'drive' type per user request
            stype = s.get("type", "unknown")
            valid_drive_types = ["google_docs", "google_slides_sheets", "pdf", "drive"]
            if stype not in valid_drive_types:
                continue
            
            # Determine staleness
            if check_freshness:
                # check_source_freshness returns True if fresh (not stale)
                is_fresh = self.check_source_freshness(s["id"])
                # If explicit False, it's stale. If None/True, assume fresh.
                is_stale = (is_fresh is False)
            else:
                # Skip freshness check - assume unknown (not stale)
                is_stale = False
            
            drive_sources.append(DriveSource(
                id=s["id"],
                title=s.get("title", "Untitled"),
                is_stale=is_stale,
                type=stype,
            ))
            
        return drive_sources

    def sync_sources(self, source_ids: list[str]) -> int:
        """Sync multiple sources. Returns number of successful syncs."""
        count = 0
        for sid in source_ids:
            if self.sync_drive_source(sid):
                count += 1
        return count

    def check_source_freshness(self, source_id: str) -> bool:
        """Check if a Drive source is fresh (True) or stale (False)."""
        params = [None, [source_id], [2]]
        result = self._call_rpc(RPC.CHECK_FRESHNESS, params)
        
        # Result is like [[None, True, ['id']]]
        if result and isinstance(result, list) and len(result) > 0:
            inner = result[0]
            if isinstance(inner, list) and len(inner) > 1:
                return inner[1] is True
                
        # If parsing fails, conservatively assume fresh to avoid false positives
        return True
    
    def sync_drive_source(self, source_id: str) -> bool:
        """Sync a Drive source with latest content."""
        params = [None, [source_id], [2]]
        result = self._call_rpc(RPC.SYNC_DRIVE, params)
        return result is not None
    
    # =========================================================================
    # Chat Configuration (matching MCP signatures)
    # =========================================================================
    
    def configure_chat(
        self,
        notebook_id: str,
        goal: str = "default",
        custom_prompt: str | None = None,
        response_length: str = "default",
    ) -> dict[str, Any]:
        """Configure notebook chat settings."""
        goal_code = constants.CHAT_GOALS.get_code(goal)
        length_code = constants.CHAT_RESPONSE_LENGTHS.get_code(response_length)
        
        if goal == "custom" and custom_prompt:
            goal_setting = [goal_code, custom_prompt]
        else:
            goal_setting = [goal_code]
        
        params = [notebook_id, [[None, None, None, None, None, None, None, [goal_setting, [length_code]]]]]
        result = self._call_rpc(RPC.RENAME_NOTEBOOK, params, f"/notebook/{notebook_id}")
        
        return {
            "goal": goal,
            "custom_prompt": custom_prompt,
            "response_length": response_length,
            "success": result is not None,
        }
    
    # =========================================================================
    # Studio Operations (matching MCP signatures)
    # =========================================================================
    
    def create_audio(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        format: str = "deep_dive",
        length: str = "default",
        format_code: int | None = None,
        length_code: int | None = None,
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create an Audio Overview from notebook sources.
        
        Accepts either string format/length or integer codes.
        If source_ids not provided, uses all sources from notebook.
        """
        # Get source IDs if not provided
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating audio.")
        
        # Convert string format to code
        # Convert string format to code
        if format_code is None:
            format_code = constants.AUDIO_FORMATS.get_code(format)
        
        # Convert string length to code
        if length_code is None:
            length_code = constants.AUDIO_LENGTHS.get_code(length)
        
        sources_nested = [[[sid]] for sid in source_ids]
        sources_simple = [[sid] for sid in source_ids]  # For audio_options
        
        # Audio options structure from reference MCP
        audio_options = [
            None,
            [
                focus_prompt,
                length_code,
                None,
                sources_simple,
                language,
                None,
                format_code
            ]
        ]
        
        params = [
            [2],
            notebook_id,
            [None, None, constants.STUDIO_TYPE_AUDIO, sources_nested, None, None, audio_options]
        ]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "audio",
                "status": "in_progress",
            }
        return None
    
    def create_video(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        format: str = "explainer",
        visual_style: str = "auto_select",
        format_code: int | None = None,
        visual_style_code: int | None = None,
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create a Video Overview from notebook sources."""
        # Get source IDs if not provided
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating video.")
        
        # Convert string format to code
        # Convert string format to code
        if format_code is None:
            format_code = constants.VIDEO_FORMATS.get_code(format)
        
        if visual_style_code is None:
            visual_style_code = constants.VIDEO_STYLES.get_code(visual_style)
        
        sources_nested = [[[sid]] for sid in source_ids]
        sources_simple = [[sid] for sid in source_ids]  # For video_options
        
        # Video options structure from reference MCP
        video_options = [
            None, None,
            [
                sources_simple,
                language,
                focus_prompt,
                None,
                format_code,
                visual_style_code
            ]
        ]
        
        params = [
            [2],
            notebook_id,
            [None, None, constants.STUDIO_TYPE_VIDEO, sources_nested, None, None, None, None, video_options]
        ]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "video",
                "status": "in_progress",
            }
        return None
    
    def create_report(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        report_format: str = "Briefing Doc",
        custom_prompt: str = "",
        language: str = "en",
    ) -> dict | None:
        """Create a Report from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating report.")
        
        sources_nested = [[[sid]] for sid in source_ids]
        sources_simple = [[sid] for sid in source_ids]  # For report_options
        
        # Format configs from reference MCP
        format_configs = {
            "Briefing Doc": {
                "title": "Briefing Doc",
                "description": "Key insights and important quotes",
                "prompt": "Create a comprehensive briefing document that includes an Executive Summary, detailed analysis of key themes, important quotes with context, and actionable insights.",
            },
            "Study Guide": {
                "title": "Study Guide",
                "description": "Short-answer quiz, essay questions, glossary",
                "prompt": "Create a comprehensive study guide that includes key concepts, short-answer practice questions, essay prompts for deeper exploration, and a glossary of important terms.",
            },
            "Blog Post": {
                "title": "Blog Post",
                "description": "Insightful takeaways in readable article format",
                "prompt": "Write an engaging blog post that presents the key insights in an accessible, reader-friendly format.",
            },
            "Create Your Own": {
                "title": "Custom Report",
                "description": "Custom format",
                "prompt": custom_prompt or "Create a report based on the provided sources.",
            },
        }
        
        config = format_configs.get(report_format, format_configs["Briefing Doc"])
        
        # Report options structure from reference MCP
        report_options = [
            None,
            [
                config["title"],
                config["description"],
                None,
                sources_simple,
                language,
                config["prompt"],
                None,
                True
            ]
        ]
        
        params = [
            [2],
            notebook_id,
            [None, None, constants.STUDIO_TYPE_REPORT, sources_nested, None, None, None, report_options]
        ]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "report",
                "status": "in_progress",
            }
        return None
    
    def create_quiz(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        question_count: int = 2,
        difficulty: int = 2,
    ) -> dict | None:
        """Create a quiz from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating quiz.")
        
        sources_nested = [[[sid]] for sid in source_ids]
        
        # Quiz options from reference MCP - uses FLASHCARDS type (4) with quiz variant
        quiz_options = [
            None,
            [
                2,  # Format/variant code for quiz
                None, None, None, None, None, None,
                [question_count, difficulty]
            ]
        ]
        
        content = [
            None, None,
            constants.STUDIO_TYPE_FLASHCARDS,  # Type 4 (shared with flashcards)
            sources_nested,
            None, None, None, None, None,
            quiz_options  # position 9
        ]
        
        params = [[2], notebook_id, content]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "quiz",
                "status": "in_progress",
            }
        return None
    
    def create_flashcards(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        difficulty: str = "medium",
    ) -> dict | None:
        """Create flashcards from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating flashcards.")
        
        diff_code = constants.FLASHCARD_DIFFICULTIES.get_code(difficulty)
        
        sources_nested = [[[sid]] for sid in source_ids]
        
        # Flashcard options from reference MCP
        flashcard_options = [
            None,
            [
                1,  # Default count base
                None, None, None, None, None,
                [diff_code, 2]  # [difficulty_code, count_code]
            ]
        ]
        
        content = [
            None, None,
            constants.STUDIO_TYPE_FLASHCARDS,
            sources_nested,
            None, None, None, None, None,  # 5 nulls (positions 4-8)
            flashcard_options  # position 9
        ]
        
        params = [[2], notebook_id, content]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "flashcards",
                "status": "in_progress",
            }
        return None
    
    def create_mindmap(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        title: str = "Mind Map",
    ) -> dict | None:
        """Create and save a mind map from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating mind map.")
        
        # Step 1: Generate mind map - from reference MCP
        sources_nested = [[[sid]] for sid in source_ids]
        
        gen_params = [
            sources_nested,
            None, None, None, None,
            ["interactive_mindmap", [["[CONTEXT]", ""]], ""],
            None,
            [2, None, [1]]
        ]
        
        result = self._call_rpc(RPC.GENERATE_MIND_MAP, gen_params)
        
        if not result or not isinstance(result, list) or len(result) == 0:
            return None
        
        # Parse generation result
        inner = result[0] if isinstance(result[0], list) else result
        mind_map_json = inner[0] if isinstance(inner[0], str) else None
        
        if not mind_map_json:
            return None
        
        # Step 2: Save mind map - from reference MCP
        sources_simple = [[sid] for sid in source_ids]
        metadata = [2, None, None, 5, sources_simple]
        
        save_params = [
            notebook_id,
            mind_map_json,
            metadata,
            None,
            title
        ]
        
        save_result = self._call_rpc(RPC.SAVE_MIND_MAP, save_params, f"/notebook/{notebook_id}")
        
        if save_result and isinstance(save_result, list) and len(save_result) > 0:
            inner = save_result[0] if isinstance(save_result[0], list) else save_result
            mind_map_id = inner[0] if len(inner) > 0 else None
            
            return {
                "mind_map_id": mind_map_id,
                "notebook_id": notebook_id,
                "title": title,
                "status": "completed",
            }
        return None
    
    def list_mindmaps(self, notebook_id: str) -> list[dict]:
        """List mind maps in a notebook. Skips deleted/tombstone entries."""
        params = [notebook_id]
        result = self._call_rpc(RPC.LIST_MIND_MAPS, params, f"/notebook/{notebook_id}")
        
        mindmaps = []
        if result and isinstance(result, list) and len(result) > 0:
            # Structure: [[mindmap_data, ...], timestamp]
            mm_list = result[0] if isinstance(result[0], list) else []
            for mm_entry in mm_list:
                # Check if it's a valid non-deleted entry: [uuid, [data...]]
                # Deleted entries look like: [uuid, null, 2]
                if isinstance(mm_entry, list) and len(mm_entry) >= 2 and mm_entry[1] is not None:
                    mm_id = str(mm_entry[0])
                    mm_title = "Untitled Mind Map"
                    
                    inner = mm_entry[1]
                    if isinstance(inner, list) and len(inner) > 4 and isinstance(inner[4], str):
                        mm_title = inner[4]
                        
                    mindmaps.append({
                        "id": mm_id,
                        "title": mm_title,
                    })
        return mindmaps
    
    def create_slides(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        format: str = "detailed",
        length: str = "default",
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create a slide deck from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating slides.")
        
        format_code = constants.SLIDE_DECK_FORMATS.get_code(format)
        length_code = constants.SLIDE_DECK_LENGTHS.get_code(length)
        
        sources_nested = [[[sid]] for sid in source_ids]
        
        # Options at position 16: [[focus_prompt, language, format, length]] from reference MCP
        slide_deck_options = [[focus_prompt or None, language, format_code, length_code]]
        
        content = [
            None, None,
            constants.STUDIO_TYPE_SLIDE_DECK,
            sources_nested,
            None, None, None, None, None, None, None, None, None, None, None, None,  # 12 nulls (positions 4-15)
            slide_deck_options  # position 16
        ]
        
        params = [[2], notebook_id, content]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "slide_deck",
                "status": "in_progress",
            }
        return None
    
    def create_infographic(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        orientation: str = "landscape",
        detail_level: str = "standard",
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create an infographic from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating infographic.")
        
        orient_code = constants.INFOGRAPHIC_ORIENTATIONS.get_code(orientation)
        detail_code = constants.INFOGRAPHIC_DETAILS.get_code(detail_level)
        
        sources_nested = [[[sid]] for sid in source_ids]
        
        # Options at position 14: [[focus_prompt, language, null, orientation, detail_level]] from reference MCP
        infographic_options = [[focus_prompt or None, language, None, orient_code, detail_code]]
        
        content = [
            None, None,
            constants.STUDIO_TYPE_INFOGRAPHIC,
            sources_nested,
            None, None, None, None, None, None, None, None, None, None,  # 10 nulls (positions 4-13)
            infographic_options  # position 14
        ]
        
        params = [[2], notebook_id, content]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "infographic",
                "status": "in_progress",
            }
        return None
    
    def create_data_table(
        self,
        notebook_id: str,
        description: str,
        source_ids: list[str] | None = None,
        language: str = "en",
    ) -> dict | None:
        """Create a data table from notebook sources."""
        if source_ids is None:
            sources = self.list_sources(notebook_id)
            source_ids = [s["id"] for s in sources]
        
        if not source_ids:
            from nlm.core.exceptions import NLMError
            raise NLMError("No sources in notebook. Add sources before creating data table.")
        
        sources_nested = [[[sid]] for sid in source_ids]
        
        # Data Table options from reference MCP - at position 18
        datatable_options = [None, [description, language]]
        
        content = [
            None, None,
            constants.STUDIO_TYPE_DATA_TABLE,  # Type 9
            sources_nested,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None,  # 14 nulls (positions 4-17)
            datatable_options  # position 18
        ]
        
        params = [[2], notebook_id, content]
        
        result = self._call_rpc(RPC.CREATE_STUDIO, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) else None
            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "data_table",
                "status": "in_progress",
            }
        return None
    
    def get_studio_status(self, notebook_id: str) -> list[dict]:
        """Get studio artifacts status including mind maps."""
        artifacts = self.poll_studio_status(notebook_id)
        
        # Also include mind maps for unified view
        try:
            mindmaps = self.list_mindmaps(notebook_id)
            for mm in mindmaps:
                artifacts.append({
                    "artifact_id": mm.get("id", ""),
                    "title": mm.get("title", "Untitled Mind Map"),
                    "type": "mindmap",
                    "status": "completed",  # Mind maps are always complete once saved
                })
        except Exception:
            pass  # Silently skip if mindmaps fail
        
        return artifacts
    
    def poll_studio_status(self, notebook_id: str) -> list[dict]:
        """Poll for studio content status."""
        params = [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        result = self._call_rpc(RPC.POLL_STUDIO, params, f"/notebook/{notebook_id}")
        
        artifacts = []
        if result and isinstance(result, list) and len(result) > 0:
            artifact_list = result[0] if isinstance(result[0], list) else result
            
            for artifact_data in artifact_list:
                if not isinstance(artifact_data, list) or len(artifact_data) < 5:
                    continue
                
                artifact_id = artifact_data[0]
                title = artifact_data[1] if len(artifact_data) > 1 else ""
                type_code = artifact_data[2] if len(artifact_data) > 2 else None
                status_code = artifact_data[4] if len(artifact_data) > 4 else None
                
                type_map = {
                    StudioType.AUDIO: "audio",
                    StudioType.REPORT: "report",
                    StudioType.VIDEO: "video",
                    StudioType.FLASHCARDS: "flashcards",
                    StudioType.INFOGRAPHIC: "infographic",
                    StudioType.SLIDE_DECK: "slide_deck",
                    StudioType.DATA_TABLE: "data_table",
                }
                
                artifacts.append({
                    "artifact_id": artifact_id,
                    "title": title,
                    "type": type_map.get(type_code, "unknown"),
                    "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                })
        
        return artifacts

    def delete_studio_artifact(self, artifact_id: str, notebook_id: str | None = None) -> bool:
        """Delete a studio artifact.
        
        Args:
            artifact_id: ID of the artifact to delete.
            notebook_id: Optional notebook ID. Required for deleting Mind Maps.
        """
        # 1. Try standard deletion (Audio, Video, etc.)
        try:
            params = [[2], artifact_id]
            result = self._call_rpc(RPC.DELETE_STUDIO, params)
            if result is not None:
                return True
        except Exception:
            # Continue to fallback if standard delete fails
            pass
            
        # 2. Fallback: Try Mind Map deletion if we have a notebook ID
        # Mind maps require a different RPC (AH0mwd) and payload structure
        if notebook_id:
            return self.delete_mind_map(notebook_id, artifact_id)
            
        return False
    
    def delete_mind_map(self, notebook_id: str, mind_map_id: str) -> bool:
        """Delete a Mind Map artifact using the observed two-step RPC sequence.
        
        Args:
            notebook_id: The notebook UUID.
            mind_map_id: The Mind Map artifact UUID.
        """
        # 1. We need the artifact-specific timestamp from LIST_MIND_MAPS
        params = [notebook_id]
        list_result = self._call_rpc(RPC.LIST_MIND_MAPS, params, f"/notebook/{notebook_id}")
        
        timestamp = None
        if list_result and isinstance(list_result, list) and len(list_result) > 0:
            mm_list = list_result[0] if isinstance(list_result[0], list) else []
            for mm_entry in mm_list:
                if isinstance(mm_entry, list) and mm_entry[0] == mind_map_id:
                    # Based on debug output: item[1][2][2] contains [seconds, micros]
                    try:
                        timestamp = mm_entry[1][2][2]
                    except (IndexError, TypeError):
                        pass
                    break
        
        # 2. Step 1: UUID-based deletion (AH0mwd)
        params_v2 = [notebook_id, None, [mind_map_id], [2]]
        self._call_rpc(RPC.DELETE_MIND_MAP, params_v2, f"/notebook/{notebook_id}")
        
        # 3. Step 2: Timestamp-based sync/deletion (cFji9)
        # This is required to fully remove it from the list and avoid "ghosts"
        if timestamp:
            params_v1 = [notebook_id, None, timestamp, [2]]
            self._call_rpc(RPC.LIST_MIND_MAPS, params_v1, f"/notebook/{notebook_id}")
            
        return True

    def delete_artifact(self, notebook_id: str, artifact_id: str) -> bool:
        """Delete a studio artifact. Alias for delete_studio_artifact."""
        return self.delete_studio_artifact(artifact_id, notebook_id)
    
    # =========================================================================
    # Research Operations (matching MCP signatures)
    # =========================================================================
    
    def start_research(
        self,
        notebook_id: str,
        query: str,
        source: str = "web",
        mode: str = "fast",
    ) -> dict | None:
        """Start a research session to discover sources."""
        source_code = constants.RESEARCH_SOURCES.get_code(source)
        mode_code = constants.RESEARCH_MODES.get_code(mode)
        
        if mode_code == constants.RESEARCH_MODE_FAST:
            params = [[query, source_code], None, constants.RESEARCH_MODE_FAST, notebook_id]
            rpc_id = RPC.START_FAST_RESEARCH
        else:
            params = [None, [1], [query, source_code], constants.RESEARCH_MODE_DEEP, notebook_id]
            rpc_id = RPC.START_DEEP_RESEARCH
        
        result = self._call_rpc(rpc_id, params, f"/notebook/{notebook_id}")
        
        if result and isinstance(result, list) and len(result) > 0:
            return {
                "task_id": result[0],
                "report_id": result[1] if len(result) > 1 else None,
                "notebook_id": notebook_id,
                "query": query,
                "source": source.lower(),
                "mode": mode.lower(),
            }
        return None
    
    def poll_research(self, notebook_id: str, target_task_id: str | None = None) -> dict | None:
        """Poll for research results.
        
        Returns dict with:
        - tasks: list of all research tasks found
        - status: overall status (completed if any completed, in_progress if any running, no_research otherwise)
        
        Each task has: task_id, status, sources, source_count
        """
        params = [None, None, notebook_id]
        result = self._call_rpc(RPC.POLL_RESEARCH, params, f"/notebook/{notebook_id}")
        
        if not result or not isinstance(result, list):
            return {"status": "no_research", "message": "No active research found", "tasks": []}
        
        # Parse research results (simplified)
        if isinstance(result[0], list) and len(result[0]) > 0:
            result = result[0]
        
        all_tasks = []
        
        for task_data in result:
            if not isinstance(task_data, list) or len(task_data) < 2:
                continue
            
            task_id = task_data[0]
            if not isinstance(task_id, str):
                continue
            
            # If looking for specific task, skip others
            if target_task_id and task_id != target_task_id:
                continue
            
            task_info = task_data[1]
            if not task_info or not isinstance(task_info, list):
                continue
            
            status_code = task_info[4] if len(task_info) > 4 else None
            sources_data = task_info[3][0] if len(task_info) > 3 and isinstance(task_info[3], list) else []
            
            sources = []
            for idx, src in enumerate(sources_data):
                if isinstance(src, list) and len(src) >= 2:
                    sources.append({
                        "index": idx,
                        "url": src[0] if isinstance(src[0], str) else "",
                        "title": src[1] if len(src) > 1 else "",
                        "type_code": src[3] if len(src) > 3 and isinstance(src[3], int) else None,
                    })
            
            task_dict = {
                "task_id": task_id,
                "status": "completed" if status_code == 6 else "in_progress",
                "sources": sources,
                "source_count": len(sources),
            }
            
            # If we found our specific task, return it directly (backward compat)
            if target_task_id:
                return task_dict
            
            all_tasks.append(task_dict)
        
        if target_task_id:
            return {"status": "no_research", "message": f"Task {target_task_id} not found", "tasks": []}
        
        if not all_tasks:
            return {"status": "no_research", "message": "No active research found", "tasks": []}
        
        # Determine overall status
        has_completed = any(t["status"] == "completed" for t in all_tasks)
        has_in_progress = any(t["status"] == "in_progress" for t in all_tasks)
        
        overall_status = "completed" if has_completed else ("in_progress" if has_in_progress else "no_research")
        
        # For backward compat, also include top-level fields from first task
        first_task = all_tasks[0]
        return {
            "status": overall_status,
            "tasks": all_tasks,
            "task_id": first_task["task_id"],
            "sources": first_task["sources"],
            "source_count": first_task["source_count"],
        }
    
    def import_research_sources(
        self,
        notebook_id: str,
        task_id: str,
        sources: list[dict],
    ) -> list[dict]:
        """Import research sources into the notebook.
        
        Uses the native research import RPC which handles source types correctly
        and avoids duplicates/ghost entries.
        """
        if not sources:
            return []

        # Build source array for import using the specific format required by RPC_IMPORT_RESEARCH
        # This matches the implementation in notebooklm-mcp/api_client.py
        source_array = []
        
        for src in sources:
            url = src.get("url", "")
            title = src.get("title", "Untitled")
            
            # Use type_code from research results (3rd index in raw list, mapped in poll_research)
            # Default to 1 (Web) if missing
            result_type = src.get("type_code", 1)
            
            # Skip deep_report sources (type 5) and empty URLs
            if result_type == 5 or not url:
                continue

            if result_type == 1:
                # Web source structure: [None, None, [url, title], None, None, None, None, None, None, None, 2]
                source_data = [None, None, [url, title], None, None, None, None, None, None, None, 2]
            else:
                # Drive source - extract document ID from URL
                # URL format: https://drive.google.com/open?id=<doc_id> or similar
                doc_id = None
                if "id=" in url:
                    doc_id = url.split("id=")[-1].split("&")[0]
                
                if doc_id:
                    # Determine MIME type from result_type (type_code)
                    mime_types = {
                        2: "application/vnd.google-apps.document",     # Doc
                        3: "application/vnd.google-apps.presentation", # Slide (Presentation)
                        8: "application/vnd.google-apps.spreadsheet",  # Sheet
                    }
                    mime_type = mime_types.get(result_type, "application/vnd.google-apps.document")
                    
                    # Drive source structure: [[doc_id, mime_type, 1, title], None x9, 2]
                    # The 1 at position 2 and trailing 2 are required
                    source_data = [[doc_id, mime_type, 1, title], None, None, None, None, None, None, None, None, None, 2]
                else:
                    # Fallback to web-style import if no ID found
                    source_data = [None, None, [url, title], None, None, None, None, None, None, None, 2]
            
            source_array.append(source_data)

        if not source_array:
            return []

        # Call RPC_IMPORT_RESEARCH with the batch
        # Params: [None, [1], task_id, notebook_id, source_array]
        params = [None, [1], task_id, notebook_id, source_array]
        
        try:
            # Import can take a long time when fetching multiple sources
            # Use 120s timeout instead of the default 30s
            # Note: _call_rpc returns the extracted result structure directly
            result = self._call_rpc(RPC.IMPORT_RESEARCH, params, f"/notebook/{notebook_id}", timeout=120.0)
            
            imported_sources = []
            if result and isinstance(result, list):
                # Unwrap nested list if present (common in batch execute)
                if (len(result) > 0 and isinstance(result[0], list) and 
                    len(result[0]) > 0 and isinstance(result[0][0], list)):
                    result = result[0]
                
                for src_data in result:
                    if isinstance(src_data, list) and len(src_data) >= 2:
                        # Extract source ID and Title
                        src_id = src_data[0][0] if src_data[0] and isinstance(src_data[0], list) else None
                        src_title = src_data[1] if len(src_data) > 1 else "Untitled"
                        if src_id:
                            imported_sources.append({"id": src_id, "title": src_title})
            
            return imported_sources

        except Exception as e:
            # If batch import fails, re-raise or handle
            print(f"Error importing sources batch: {e}")
            raise e
    
    def get_research_status(
        self,
        notebook_id: str,
        poll_interval: int = 30,
        max_wait: int = 300,
        compact: bool = True,
        task_id: str | None = None,
    ) -> dict:
        """Get research status. Wrapper around poll_research with CLI-compatible signature."""
        # For now, just do a single poll. Full polling loop could be added if needed.
        result = self.poll_research(notebook_id, target_task_id=task_id)
        # Add sources_found for CLI compatibility
        if result and "source_count" in result:
            result["sources_found"] = result["source_count"]
        return result
    
    def import_research(
        self,
        notebook_id: str,
        task_id: str,
        source_indices: list[int] | None = None,
    ) -> list[dict]:
        """Import research sources. CLI-compatible wrapper for import_research_sources."""
        # First get the research status to get source list (targeting specific task)
        research = self.poll_research(notebook_id, target_task_id=task_id)
        if not research or research.get("status") == "no_research":
            return []
        
        sources = research.get("sources", [])
        if not sources:
            return []
        
        # Filter by indices if specified
        if source_indices is not None:
            sources = [sources[i] for i in source_indices if i < len(sources)]
        
        return self.import_research_sources(notebook_id, task_id, sources)
    
    # =========================================================================
    # Query Operations (matching MCP signatures)
    # =========================================================================
    
    def query(
        self,
        notebook_id: str,
        query_text: str,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> dict | None:
        """Query the notebook with a question."""
        import uuid
        
        client = self._get_client()
        
        # Get source IDs if not provided
        # Get source metadata for citations
        used_sources = []
        notebook = self.get_notebook(notebook_id)
        
        if source_ids is None:
            if notebook and notebook.sources:
                source_ids = [s["id"] for s in notebook.sources]
                used_sources = notebook.sources
            else:
                source_ids = []
        else:
            # Resolve titles for requested source IDs
            if notebook and notebook.sources:
                lookup = {s["id"]: s for s in notebook.sources}
                used_sources = [lookup[sid] for sid in source_ids if sid in lookup]
        
        # Handle conversation
        is_new = conversation_id is None
        if is_new:
            conversation_id = str(uuid.uuid4())
            history = None
        else:
            history = self._build_conversation_history(conversation_id)
        
        sources_array = [[[sid]] for sid in source_ids] if source_ids else []
        
        params = [
            sources_array,
            query_text,
            history,
            [2, None, [1]],
            conversation_id,
        ]
        
        params_json = json.dumps(params, separators=(",", ":"))
        f_req = [None, params_json]
        f_req_json = json.dumps(f_req, separators=(",", ":"))
        
        body_parts = [f"f.req={urllib.parse.quote(f_req_json, safe='')}"]
        if self.csrf_token:
            body_parts.append(f"at={urllib.parse.quote(self.csrf_token, safe='')}")
        body = "&".join(body_parts) + "&"
        
        self._reqid_counter += 100000
        url_params = {
            "bl": os.environ.get("NOTEBOOKLM_BL", "boq_labs-tailwind-frontend_20251221.14_p0"),
            "hl": "en",
            "_reqid": str(self._reqid_counter),
            "rt": "c",
        }
        if self._session_id:
            url_params["f.sid"] = self._session_id
        
        query_string = urllib.parse.urlencode(url_params)
        url = f"{BASE_URL}{self.QUERY_ENDPOINT}?{query_string}"
        
        try:
            response = client.post(url, content=body)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise NetworkError(
                message=f"Query failed: {e}",
                hint="Check your internet connection.",
            ) from e
        
        answer, citations = self._parse_query_response(response.text)
        
        if answer:
            self._cache_conversation_turn(conversation_id, query_text, answer)
        
        turns = self._conversation_cache.get(conversation_id, [])
        
        return {
            "answer": answer,
            "conversation_id": conversation_id,
            "turn_number": len(turns),
            "is_follow_up": not is_new,
            "sources": used_sources,
            "citations": citations,
        }
    
    def _extract_source_ids(self, notebook_data: Any) -> list[str]:
        """Extract source IDs from notebook data."""
        source_ids = []
        
        # Handle Notebook object
        if hasattr(notebook_data, "sources") and notebook_data.sources:
            return [s["id"] for s in notebook_data.sources]
            
        # Handle raw list data (fallback)
        if notebook_data and isinstance(notebook_data, list):
            try:
                if len(notebook_data) > 0 and isinstance(notebook_data[0], list):
                    notebook_info = notebook_data[0]
                    if len(notebook_info) > 1 and isinstance(notebook_info[1], list):
                        for source in notebook_info[1]:
                            if isinstance(source, list) and len(source) > 0:
                                src_wrapper = source[0]
                                if isinstance(src_wrapper, list) and len(src_wrapper) > 0:
                                    source_ids.append(src_wrapper[0])
            except (IndexError, TypeError):
                pass
        return source_ids
    
    def _parse_query_response(self, response_text: str) -> tuple[str, dict[int, str]]:
        """Parse streaming query response and extract answer with citations.
        
        Returns:
            tuple: (answer_text, citations_dict) where citations_dict maps
                   1-indexed citation numbers to source UUIDs.
        """
        if response_text.startswith(")]}'"):
            response_text = response_text[4:]
        
        answer_parts = []
        citations: dict[int, str] = {}
        lines = response_text.strip().split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            try:
                int(line)
                i += 1
                if i < len(lines):
                    try:
                        data = json.loads(lines[i])
                        text, is_answer, chunk_citations = self._extract_answer_text(data)
                        if text and is_answer:
                            answer_parts.append(text)
                        if chunk_citations:
                            citations.update(chunk_citations)
                    except json.JSONDecodeError:
                        pass
                i += 1
            except ValueError:
                try:
                    data = json.loads(line)
                    text, is_answer, chunk_citations = self._extract_answer_text(data)
                    if text and is_answer:
                        answer_parts.append(text)
                    if chunk_citations:
                        citations.update(chunk_citations)
                except json.JSONDecodeError:
                    pass
                i += 1
        
        return answer_parts[-1] if answer_parts else "", citations
    
    def _extract_answer_text(self, data: Any) -> tuple[str, bool, dict[int, str]]:
        """Extract answer text and citation mappings from query response chunk.
        
        Returns:
            tuple: (text, is_answer, citations_dict) where citations_dict maps
                   1-indexed citation numbers to source UUIDs.
        """
        if not isinstance(data, list):
            return "", False, {}
        
        for chunk in data:
            if isinstance(chunk, list) and len(chunk) >= 3:
                if chunk[0] == "wrb.fr":
                    inner = chunk[2]
                    if isinstance(inner, str):
                        try:
                            parsed = json.loads(inner)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                first = parsed[0]
                                if isinstance(first, list) and len(first) > 0:
                                    text = first[0]
                                    if isinstance(text, str) and len(text) > 20:
                                        # Check if answer (type 1) vs thinking (type 2)
                                        is_answer = True
                                        if len(first) > 4 and isinstance(first[4], list):
                                            type_info = first[4]
                                            if len(type_info) > 0 and isinstance(type_info[-1], int):
                                                is_answer = type_info[-1] == 1
                                        
                                        # Extract citation mappings from parsed[1]
                                        citations: dict[int, str] = {}
                                        if len(parsed) > 1 and isinstance(parsed[1], list):
                                            citation_list = parsed[1]
                                            for idx, cite_item in enumerate(citation_list):
                                                try:
                                                    # Path: cite_item[5][0][0][0] = source UUID
                                                    source_uuid = cite_item[5][0][0][0]
                                                    if isinstance(source_uuid, str):
                                                        citations[idx + 1] = source_uuid
                                                except (IndexError, TypeError):
                                                    pass
                                        
                                        return text, is_answer, citations
                        except json.JSONDecodeError:
                            pass
        return "", False, {}
    
    def _build_conversation_history(self, conversation_id: str) -> list | None:
        """Build conversation history for follow-up queries."""
        turns = self._conversation_cache.get(conversation_id, [])
        if not turns:
            return None
        
        history = []
        for turn in reversed(turns):
            history.append([turn.answer, None, 2])
            history.append([turn.query, None, 1])
        
        return history
    
    def _cache_conversation_turn(self, conversation_id: str, query: str, answer: str) -> None:
        """Cache a conversation turn for follow-ups."""
        if conversation_id not in self._conversation_cache:
            self._conversation_cache[conversation_id] = []
        
        turns = self._conversation_cache[conversation_id]
        turns.append(ConversationTurn(
            query=query,
            answer=answer,
            turn_number=len(turns) + 1,
        ))

