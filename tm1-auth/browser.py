"""
Browser launch helpers.

Tries to find a suitable browser executable in this order:
  1. Caller-supplied executable_path
  2. System Microsoft Edge (most likely to work in managed/restricted environments)
  3. System Google Chrome
  4. Playwright's bundled Chromium (fallback)
"""

import os
import sys
from typing import Optional


# Common browser paths by platform
_EDGE_PATHS_WIN = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

_CHROME_PATHS_WIN = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

_EDGE_PATHS_MAC = [
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

_CHROME_PATHS_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

_CHROME_PATHS_LINUX = [
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]


def find_browser_executable(executable_path: Optional[str] = None) -> Optional[str]:
    """
    Return the path to a usable browser executable, or None to use
    Playwright's bundled Chromium.
    """
    if executable_path:
        if os.path.exists(executable_path):
            return executable_path
        raise FileNotFoundError(f"Specified browser not found: {executable_path}")

    candidates = []

    if sys.platform == "win32":
        candidates = _EDGE_PATHS_WIN + _CHROME_PATHS_WIN
    elif sys.platform == "darwin":
        candidates = _EDGE_PATHS_MAC + _CHROME_PATHS_MAC
    else:
        candidates = _CHROME_PATHS_LINUX

    for path in candidates:
        if os.path.exists(path):
            return path

    return None  # Fall back to Playwright's bundled Chromium


def get_default_profile_dir() -> str:
    """
    Return the default persistent browser profile directory.
    Stored in the user's home directory so it persists across projects
    and the IdP session is shared between calls.
    """
    home = os.path.expanduser("~")
    return os.path.join(home, ".tm1_auth", "browser_profile")
