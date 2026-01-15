"""Authentication refresh and recovery logic.

Implements a 3-layer recovery strategy for handling expired tokens:
1. Layer 1: Refresh CSRF/session tokens (handled in client.py)
2. Layer 2: Reload cookies from disk (handled here)
3. Layer 3: Headless Chrome auth (handled here)
"""

import time
import subprocess
from pathlib import Path
from typing import Any

from nlm.core.auth import AuthManager, Profile
from nlm.utils.cdp import (
    CDP_DEFAULT_PORT,
    NOTEBOOKLM_URL,
    find_or_create_notebooklm_page,
    get_current_url,
    get_debugger_url,
    get_page_cookies,
    get_page_html,
    is_logged_in,
    is_profile_locked,
    launch_chrome,
    launch_chrome_process,
    extract_csrf_token,
    extract_session_id,
    navigate_to_url,
    get_chrome_path,
)


def has_fresher_tokens_on_disk(profile: Profile, max_age_seconds: int = 300) -> Profile | None:
    """Check if tokens on disk are significantly fresher than the current profile.
    
    This handles the case where the user re-authenticated in another terminal
    running 'nlm login' or the MCP re-authenticated.
    
    Args:
        profile: The in-memory profile currently in use
        max_age_seconds: Threshold to consider on-disk tokens as "fresh" (default 5 mins)
        
    Returns:
        The updated Profile loaded from disk if fresher, otherwise None.
    """
    if not profile or not profile.name:
        return None
        
    auth_manager = AuthManager(profile.name)
    if not auth_manager.profile_exists():
        return None
        
    try:
        disk_profile = auth_manager.load_profile()
        
        # If disk profile has no validation time, we can't compare
        if not disk_profile.last_validated:
            return None
            
        # If current profile has no validation time, disk is fresher
        if not profile.last_validated:
            return disk_profile
            
        # Calculate age difference
        disk_ts = disk_profile.last_validated.timestamp()
        current_ts = profile.last_validated.timestamp()
        
        # If disk is newer by at least 1 second
        if disk_ts > current_ts:
            return disk_profile
            
        # Also check if disk tokens are absolutely "fresh" (less than max_age_seconds old)
        # This helps in cases where we don't have a good base comparison
        if (time.time() - disk_ts) < max_age_seconds:
            return disk_profile
            
    except Exception:
        pass
        
    return None


def run_headless_auth(port: int = 9223, timeout: int = 30) -> dict[str, Any] | None:
    """Run authentication in headless mode (no user interaction).
    
    This only works if the Chrome profile already has saved Google login.
    The Chrome process is automatically terminated after token extraction.
    
    Args:
        port: Chrome DevTools port (use diff port than interactive to avoid conflicts)
        timeout: Maximum time to wait for auth extraction
        
    Returns:
        Dict with keys: cookies, csrf_token, session_id
        Or None if failed
    """
    # 1. Check prerequisites: Chrome exists, profile not locked
    if is_profile_locked():
        # Profile in use interactively - can't use it headlessly
        return None
        
    if not get_chrome_path():
        return None
        
    chrome_process = None
    
    try:
        # 2. Launch headless Chrome
        # We need a subprocess handle to kill it later, but launch_chrome returns bool.
        # So we'll reimplement specific launch logic here for fine-grained control
        # or rely on launch_chrome's behavior and find process by port (less reliable).
        
        # BETTER: Let's reuse launch_chrome but we need to ensure we can kill it.
        # The cdp.launch_chrome uses Popen but doesn't return the process object.
        # We should modify cdp.launch_chrome or create a local version.
        # For now, we'll create a local version that returns the process.
        
        chrome_process = launch_chrome_process(port, headless=True)
        if not chrome_process:
            return None
            
        # 3. Connect and extract
        # Wait for debugger
        debugger_url = None
        for _ in range(5):
            debugger_url = get_debugger_url(port)
            if debugger_url:
                break
            time.sleep(1)
            
        if not debugger_url:
            return None
            
        page = find_or_create_notebooklm_page(port)
        if not page:
            return None
            
        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            return None
            
        # Navigate if needed
        current_url = page.get("url", "")
        if "notebooklm.google.com" not in current_url:
            navigate_to_url(ws_url, NOTEBOOKLM_URL)
            
        # Check login status
        current_url = get_current_url(ws_url)
        if not is_logged_in(current_url):
            # Not logged in - headless can't do anything
            return None
            
        # Extract everything
        cookies = get_page_cookies(ws_url)
        html = get_page_html(ws_url)
        csrf_token = extract_csrf_token(html)
        session_id = extract_session_id(html)
        
        if not cookies:
            return None
            
        return {
            "cookies": cookies,
            "csrf_token": csrf_token,
            "session_id": session_id
        }
        
    except Exception:
        return None
        
    finally:
        # 4. Clean up: Terminate Chrome
        if chrome_process:
            try:
                chrome_process.terminate()
                chrome_process.wait(timeout=5)
            except Exception:
                try:
                    chrome_process.kill()
                except Exception:
                    pass



