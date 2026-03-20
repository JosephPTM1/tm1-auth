"""
Core authentication logic for tm1-auth.
"""

import os
from typing import Optional

from .browser import find_browser_executable, get_default_profile_dir
from .exceptions import AuthenticationError, PassportTimeoutError

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


_PASSPORT_COOKIE_NAME = "cam_passport"


def get_cam_passport(
    auth_url: str,
    profile_dir: Optional[str] = None,
    timeout_seconds: int = 90,
    headless: bool = False,
    executable_path: Optional[str] = None,
    verbose: bool = True,
) -> str:
    """
    Open a browser, navigate to the Cognos auth URL, wait for the user to
    log in (including MFA), capture the cam_passport cookie and return it.

    Args:
        auth_url:         The Cognos dispatcher URL, e.g.
                          "https://your-server/ibmcognos/bi/v1/disp"
        profile_dir:      Path to a persistent browser profile directory.
                          Defaults to ~/.tm1_auth/browser_profile.

                          The profile determines session isolation:
                          - Same profile_dir across calls = shared browser
                            session. If your identity provider supports SSO,
                            subsequent logins may complete silently without
                            re-entering credentials or MFA.
                          - Different profile_dir per environment = fully
                            isolated sessions, always prompts for login.

                          Use a shared profile only if you intentionally want
                          SSO behaviour across environments. Use separate
                          profiles if environments have different credentials
                          or you want explicit login control.

        timeout_seconds:  Seconds to wait for login before raising
                          PassportTimeoutError. Default 90.
        headless:         Run without a visible browser window. Not recommended
                          for MFA flows. Default False.
        executable_path:  Path to a specific browser executable. If not set,
                          tries system Edge / Chrome then Playwright's Chromium.
        verbose:          Print progress messages to stdout. Default True.

    Returns:
        The cam_passport cookie value as a string.

    Raises:
        AuthenticationError:   If the browser fails to launch.
        PassportTimeoutError:  If no passport is detected within timeout_seconds.

    Example — isolated sessions (independent credentials per environment):
        >>> stg_passport = get_cam_passport(
        ...     auth_url="https://stg-server/ibmcognos/bi/v1/disp",
        ...     profile_dir="~/.tm1_auth/stg_profile",
        ... )
        >>> prd_passport = get_cam_passport(
        ...     auth_url="https://prd-server/ibmcognos/bi/v1/disp",
        ...     profile_dir="~/.tm1_auth/prd_profile",
        ... )

    Example — shared session (same IdP, SSO carries over):
        >>> stg_passport = get_cam_passport(
        ...     auth_url="https://stg-server/ibmcognos/bi/v1/disp",
        ... )
        >>> prd_passport = get_cam_passport(
        ...     auth_url="https://prd-server/ibmcognos/bi/v1/disp",
        ... )
        >>> # If your IdP supports SSO, the second call may not prompt for login.
        >>> # This is not guaranteed — it depends entirely on your IdP configuration.
    """
    if sync_playwright is None:
        raise ImportError(
            "Playwright is required. Install it with:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )

    profile_dir = profile_dir or get_default_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)

    exe = find_browser_executable(executable_path)

    if verbose:
        browser_name = "system browser" if exe else "Playwright Chromium"
        print(f"[tm1-auth] Launching {browser_name}...")
        print(f"[tm1-auth] Profile: {profile_dir}")
        print(f"[tm1-auth] Navigating to: {auth_url}")
        print(f"[tm1-auth] Waiting for login (timeout: {timeout_seconds}s)...")

    poll_interval_ms = 2000
    max_polls = (timeout_seconds * 1000) // poll_interval_ms

    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": profile_dir,
            "headless":      headless,
            "args":          ["--no-sandbox"],
        }
        if exe:
            launch_kwargs["executable_path"] = exe

        try:
            context = p.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as e:
            raise AuthenticationError(
                f"Browser failed to launch: {e}\n"
                f"If running in a restricted environment, try deleting the "
                f"browser profile at: {profile_dir}"
            ) from e

        try:
            page = context.new_page()

            try:
                page.goto(auth_url, wait_until="load", timeout=30000)
            except Exception as e:
                raise AuthenticationError(
                    f"Failed to navigate to auth URL: {e}\n"
                    f"Check that the URL is reachable and your network/VPN "
                    f"is connected."
                ) from e

            passport = None
            for _ in range(int(max_polls)):
                try:
                    for cookie in context.cookies():
                        if _PASSPORT_COOKIE_NAME in cookie["name"]:
                            passport = cookie["value"]
                            break
                    if passport:
                        break
                except Exception:
                    pass
                page.wait_for_timeout(poll_interval_ms)

        finally:
            context.close()

    if not passport:
        raise PassportTimeoutError(
            f"No cam_passport cookie detected after {timeout_seconds} seconds. "
            f"Login may have timed out or the auth URL may not issue a CAM passport."
        )

    if verbose:
        print("[tm1-auth] Passport captured successfully.")

    return passport