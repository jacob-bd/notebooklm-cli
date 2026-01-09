"""Browser cookie extraction utilities."""

import json
import re
from pathlib import Path
from typing import Any

from nlm.core.exceptions import AuthenticationError


# NotebookLM domain for cookie filtering
NOTEBOOKLM_DOMAIN = ".google.com"
NOTEBOOKLM_URL = "https://notebooklm.google.com"


def extract_cookies(
    method: str = "cdp",
    browser: str | None = None,
    cdp_port: int = 9222,
) -> dict[str, str]:
    """
    Extract NotebookLM cookies using the specified method.
    
    Args:
        method: "cdp" (default, no keychain prompt) or "legacy" (browser-cookie3)
        browser: Browser name for legacy mode (chrome, firefox, etc.)
        cdp_port: Port for CDP connection
    
    Returns:
        Dictionary of cookie name -> value.
    
    Raises:
        AuthenticationError: If cookies cannot be extracted.
    """
    if method == "cdp":
        try:
            from nlm.utils.cdp import extract_cookies_via_cdp
            result = extract_cookies_via_cdp(port=cdp_port)
            return result["cookies"]
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(
                message=f"CDP extraction failed: {e}",
                hint="Try 'nlm login --legacy' for browser-cookie3 fallback.",
            ) from e
    elif method == "legacy":
        return extract_cookies_from_browser(browser)
    else:
        raise AuthenticationError(
            message=f"Unknown extraction method: {method}",
            hint="Use 'cdp' or 'legacy'.",
        )


def extract_cookies_from_browser(browser: str | None = None) -> dict[str, str]:
    """
    Extract NotebookLM cookies from browser.
    
    Args:
        browser: Browser name (chrome, firefox, safari, edge, brave) or None for auto-detect.
    
    Returns:
        Dictionary of cookie name -> value.
    
    Raises:
        AuthenticationError: If cookies cannot be extracted.
    """
    try:
        import browser_cookie3
    except ImportError as e:
        raise AuthenticationError(
            message="browser-cookie3 package not installed",
            hint="Run 'pip install browser-cookie3' to install it.",
        ) from e
    
    # Map browser names to browser_cookie3 functions
    browser_funcs = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "safari": browser_cookie3.safari,
        "edge": browser_cookie3.edge,
        "brave": browser_cookie3.brave,
        "opera": browser_cookie3.opera,
        "chromium": browser_cookie3.chromium,
    }
    
    cookies: dict[str, str] = {}
    
    if browser:
        # Use specific browser
        browser_lower = browser.lower()
        if browser_lower not in browser_funcs:
            raise AuthenticationError(
                message=f"Unsupported browser: {browser}",
                hint=f"Supported browsers: {', '.join(browser_funcs.keys())}",
            )
        try:
            cj = browser_funcs[browser_lower](domain_name=NOTEBOOKLM_DOMAIN)
            cookies = {c.name: c.value for c in cj if c.value}
        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to extract cookies from {browser}: {e}",
                hint="Make sure the browser is installed and you're logged into NotebookLM.",
            ) from e
    else:
        # Auto-detect: try browsers in order of popularity
        browser_order = ["chrome", "firefox", "edge", "brave", "safari", "opera", "chromium"]
        errors = []
        
        for browser_name in browser_order:
            try:
                cj = browser_funcs[browser_name](domain_name=NOTEBOOKLM_DOMAIN)
                cookies = {c.name: c.value for c in cj if c.value}
                if cookies:
                    break
            except Exception as e:
                errors.append(f"{browser_name}: {e}")
                continue
        
        if not cookies:
            raise AuthenticationError(
                message="Could not extract cookies from any browser",
                hint="Make sure you're logged into NotebookLM in your browser, then try again.",
            )
    
    return cookies


def parse_cookies_from_file(file_path: str | Path) -> dict[str, str]:
    """
    Parse cookies from a file.
    
    The file can contain:
    - Raw cookie header string (Cookie: name=value; name2=value2)
    - cURL command (copy as cURL from DevTools)
    - JSON object with cookies
    
    Args:
        file_path: Path to the file containing cookies.
    
    Returns:
        Dictionary of cookie name -> value.
    
    Raises:
        AuthenticationError: If file cannot be parsed.
    """
    path = Path(file_path).expanduser()
    
    if not path.exists():
        raise AuthenticationError(
            message=f"Cookie file not found: {path}",
            hint="Create the file with cookies copied from browser DevTools.",
        )
    
    content = path.read_text().strip()
    
    # Try to parse as JSON first
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        if isinstance(data, list):
            # List of cookie objects
            cookies = {}
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies[item["name"]] = item["value"]
            if cookies:
                return cookies
    except json.JSONDecodeError:
        pass
    
    # Try to extract from cURL command
    curl_match = re.search(r"-H\s+['\"]Cookie:\s*([^'\"]+)['\"]", content, re.IGNORECASE)
    if curl_match:
        content = curl_match.group(1)
    
    # Try to extract Cookie header value
    if content.lower().startswith("cookie:"):
        content = content[7:].strip()
    
    # Parse cookie string (name=value; name2=value2)
    cookies: dict[str, str] = {}
    for part in content.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            name = name.strip()
            value = value.strip()
            if name and value:
                cookies[name] = value
    
    if not cookies:
        raise AuthenticationError(
            message="Could not parse cookies from file",
            hint="The file should contain a Cookie header value or cURL command.",
        )
    
    return cookies


def cookies_to_header(cookies: dict[str, str]) -> str:
    """Convert cookies dict to Cookie header value."""
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


def validate_notebooklm_cookies(cookies: dict[str, str]) -> bool:
    """
    Check if cookies appear to be valid for NotebookLM.
    
    This is a basic check - actual validation requires making an API call.
    """
    # Check for essential Google auth cookies
    essential_patterns = ["SID", "HSID", "SSID", "APISID", "SAPISID"]
    found = sum(1 for pattern in essential_patterns if any(pattern in name for name in cookies))
    return found >= 2  # At least 2 essential cookies should be present
