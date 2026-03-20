"""
Tests for tm1-auth.

These tests mock Playwright so they run without a real browser or TM1 server.
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_playwright():
    """
    Returns a mock sync_playwright context manager that simulates a successful
    login — a cam_passport cookie appears on the first poll.
    """
    mock_cookie = {"name": "cam_passport", "value": "test_passport_value_abc123"}

    mock_context = MagicMock()
    mock_context.cookies.return_value = [mock_cookie]

    mock_page = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser_type = MagicMock()
    mock_browser_type.launch_persistent_context.return_value = mock_context

    mock_p = MagicMock()
    mock_p.chromium = mock_browser_type

    mock_sync_playwright = MagicMock()
    mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_p)
    mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

    return mock_sync_playwright, mock_context, mock_page


@pytest.fixture
def mock_playwright_timeout():
    """Simulates a login timeout — no cam_passport cookie ever appears."""
    mock_context = MagicMock()
    mock_context.cookies.return_value = [
        {"name": "some_other_cookie", "value": "irrelevant"}
    ]

    mock_page = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser_type = MagicMock()
    mock_browser_type.launch_persistent_context.return_value = mock_context

    mock_p = MagicMock()
    mock_p.chromium = mock_browser_type

    mock_sync_playwright = MagicMock()
    mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_p)
    mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

    return mock_sync_playwright, mock_context


# ── Tests: get_cam_passport ───────────────────────────────────────────────────

class TestGetCamPassport:

    def test_returns_passport_on_successful_login(self, mock_playwright, tmp_path):
        mock_sync_playwright, mock_context, mock_page = mock_playwright

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            result = get_cam_passport(
                auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                profile_dir=str(tmp_path),
                verbose=False,
            )

        assert result == "test_passport_value_abc123"

    def test_raises_timeout_error_when_no_passport(self, mock_playwright_timeout, tmp_path):
        mock_sync_playwright, _ = mock_playwright_timeout

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            from tm1_auth.exceptions import PassportTimeoutError

            with pytest.raises(PassportTimeoutError):
                get_cam_passport(
                    auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                    profile_dir=str(tmp_path),
                    timeout_seconds=2,
                    verbose=False,
                )

    def test_navigates_to_auth_url(self, mock_playwright, tmp_path):
        mock_sync_playwright, mock_context, mock_page = mock_playwright
        auth_url = "https://fake-server/ibmcognos/bi/v1/disp"

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            get_cam_passport(
                auth_url=auth_url,
                profile_dir=str(tmp_path),
                verbose=False,
            )

        mock_page.goto.assert_called_once_with(
            auth_url, wait_until="load", timeout=30000
        )

    def test_closes_context_after_success(self, mock_playwright, tmp_path):
        mock_sync_playwright, mock_context, _ = mock_playwright

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            get_cam_passport(
                auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                profile_dir=str(tmp_path),
                verbose=False,
            )

        mock_context.close.assert_called_once()

    def test_closes_context_after_timeout(self, mock_playwright_timeout, tmp_path):
        mock_sync_playwright, mock_context = mock_playwright_timeout

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            from tm1_auth.exceptions import PassportTimeoutError

            with pytest.raises(PassportTimeoutError):
                get_cam_passport(
                    auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                    profile_dir=str(tmp_path),
                    timeout_seconds=2,
                    verbose=False,
                )

        mock_context.close.assert_called_once()

    def test_raises_authentication_error_on_browser_launch_failure(self, tmp_path):
        mock_sync_playwright = MagicMock()
        mock_p = MagicMock()
        mock_p.chromium.launch_persistent_context.side_effect = Exception("Browser crashed")
        mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_p)
        mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            from tm1_auth.exceptions import AuthenticationError

            with pytest.raises(AuthenticationError, match="Browser failed to launch"):
                get_cam_passport(
                    auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                    profile_dir=str(tmp_path),
                    verbose=False,
                )

    def test_uses_custom_profile_dir(self, mock_playwright, tmp_path):
        mock_sync_playwright, mock_context, _ = mock_playwright
        custom_dir = str(tmp_path / "my_profile")

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            get_cam_passport(
                auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                profile_dir=custom_dir,
                verbose=False,
            )

        call_kwargs = mock_context.new_page.call_args
        launch_kwargs = mock_p = mock_sync_playwright.return_value.__enter__.return_value
        launch_call = launch_kwargs = mock_sync_playwright.return_value.__enter__\
            .return_value.chromium.launch_persistent_context.call_args
        assert launch_call.kwargs.get("user_data_dir") == custom_dir or \
               launch_call.args[0] == custom_dir

    def test_passport_detected_in_cookie_with_prefix(self, tmp_path):
        """cam_passport cookie name might have a prefix e.g. 'cam_passport_default'"""
        mock_cookie = {"name": "cam_passport_default", "value": "prefixed_passport_xyz"}

        mock_context = MagicMock()
        mock_context.cookies.return_value = [mock_cookie]
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_p = MagicMock()
        mock_p.chromium.launch_persistent_context.return_value = mock_context

        mock_sync_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_p)
        mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

        with patch("tm1_auth.auth.sync_playwright", mock_sync_playwright):
            from tm1_auth import get_cam_passport
            result = get_cam_passport(
                auth_url="https://fake-server/ibmcognos/bi/v1/disp",
                profile_dir=str(tmp_path),
                verbose=False,
            )

        assert result == "prefixed_passport_xyz"


# ── Tests: PassportCache ──────────────────────────────────────────────────────

class TestPassportCache:

    def test_get_returns_none_when_empty(self):
        from tm1_auth.cache import PassportCache
        cache = PassportCache()
        assert cache.get("https://server/auth") is None

    def test_set_and_get(self):
        from tm1_auth.cache import PassportCache
        cache = PassportCache()
        cache.set("https://server/auth", "my_passport")
        assert cache.get("https://server/auth") == "my_passport"

    def test_get_returns_none_after_expiry(self):
        from tm1_auth.cache import PassportCache
        import time
        cache = PassportCache(ttl_seconds=0)
        cache.set("https://server/auth", "my_passport")
        time.sleep(0.01)
        assert cache.get("https://server/auth") is None

    def test_invalidate_removes_entry(self):
        from tm1_auth.cache import PassportCache
        cache = PassportCache()
        cache.set("https://server/auth", "my_passport")
        cache.invalidate("https://server/auth")
        assert cache.get("https://server/auth") is None

    def test_clear_removes_all_entries(self):
        from tm1_auth.cache import PassportCache
        cache = PassportCache()
        cache.set("https://server-a/auth", "passport_a")
        cache.set("https://server-b/auth", "passport_b")
        cache.clear()
        assert cache.get("https://server-a/auth") is None
        assert cache.get("https://server-b/auth") is None

    def test_separate_keys_for_different_urls(self):
        from tm1_auth.cache import PassportCache
        cache = PassportCache()
        cache.set("https://stg/auth", "stg_passport")
        cache.set("https://prd/auth", "prd_passport")
        assert cache.get("https://stg/auth") == "stg_passport"
        assert cache.get("https://prd/auth") == "prd_passport"


# ── Tests: browser helpers ────────────────────────────────────────────────────

class TestFindBrowserExecutable:

    def test_returns_specified_path_if_exists(self, tmp_path):
        from tm1_auth.browser import find_browser_executable
        fake_exe = tmp_path / "browser.exe"
        fake_exe.write_text("")
        assert find_browser_executable(str(fake_exe)) == str(fake_exe)

    def test_raises_if_specified_path_missing(self):
        from tm1_auth.browser import find_browser_executable
        with pytest.raises(FileNotFoundError):
            find_browser_executable("/nonexistent/browser.exe")

    def test_returns_none_when_no_system_browser_found(self):
        from tm1_auth.browser import find_browser_executable
        with patch("os.path.exists", return_value=False):
            result = find_browser_executable()
        assert result is None

    def test_default_profile_dir_is_in_home(self):
        from tm1_auth.browser import get_default_profile_dir
        import os
        result = get_default_profile_dir()
        assert result.startswith(os.path.expanduser("~"))
        assert "tm1_auth" in result
