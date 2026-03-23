# tm1-auth

A Python library for authenticating with IBM Planning Analytics (TM1) in environments that use Cognos Access Manager (CAM) with multi-factor authentication.

TM1py requires a `cam_passport` to connect to CAM-secured environments, but obtaining one programmatically is non-trivial when MFA is involved. `tm1-auth` handles the browser-based login flow for you and captures the passport automatically.

---

## Features

- Automated CAM passport retrieval via a browser login window
- Works alongside TM1py - pass the retrieved passport directly to `TM1Service`
- Supports system browsers (Edge, Chrome) as well as Playwright's bundled Chromium
- Optional in-memory passport caching via `PassportCache`
- Cross-platform: Windows, macOS, Linux

---

## Requirements

- Python 3.8+
- [Playwright](https://playwright.dev/python/)

```bash
pip install playwright
playwright install chromium
```

---

## Installation

```bash
pip install tm1-auth
```

---

## Quick start

```python
from tm1_auth import get_cam_passport
from TM1py import TM1Service

passport = get_cam_passport(
    auth_url="https://your-cognos-server/ibmcognos/bi/v1/disp"
)

with TM1Service(address="your-tm1-server", port=5001,
                cam_passport=passport, ssl=True) as tm1:
    print(tm1.server.get_product_version())
```

A browser window opens, you complete the login flow (including MFA), and the passport is captured automatically. The window closes once the passport is detected.

---

## Multiple environments

By default all calls share the same browser profile (`~/.tm1_auth/browser_profile`). Whether this is useful depends on your setup.

**Isolated sessions** — use when environments have different credentials, or you want explicit login control for each:

```python
stg_passport = get_cam_passport(
    auth_url="https://stg-cognos/ibmcognos/bi/v1/disp",
    profile_dir="~/.tm1_auth/stg",
)

prd_passport = get_cam_passport(
    auth_url="https://prd-cognos/ibmcognos/bi/v1/disp",
    profile_dir="~/.tm1_auth/prd",
)
```

Each call gets its own browser session and will prompt for login independently.

**Shared session** — use when environments share the same identity provider and you want to avoid repeated logins:

```python
stg_passport = get_cam_passport(
    auth_url="https://stg-cognos/ibmcognos/bi/v1/disp",
)

prd_passport = get_cam_passport(
    auth_url="https://prd-cognos/ibmcognos/bi/v1/disp",
)
```

Both calls use the default shared profile. If your identity provider supports SSO, the second call may complete without prompting for credentials or MFA again. This is not guaranteed — it depends entirely on your IdP configuration and session policies.

---

## Caching passports

If you connect to TM1 multiple times within the same script, use `PassportCache` to avoid repeated browser logins:

```python
from tm1_auth import get_cam_passport
from tm1_auth.cache import PassportCache

cache = PassportCache(ttl_seconds=3600)

def get_passport(auth_url):
    passport = cache.get(auth_url)
    if not passport:
        passport = get_cam_passport(auth_url)
        cache.set(auth_url, passport)
    return passport
```

If a cached passport is rejected by TM1py, call `cache.invalidate(auth_url)` and re-authenticate:

```python
try:
    tm1 = TM1Service(address=address, port=port,
                     cam_passport=get_passport(auth_url), ssl=True)
except Exception:
    cache.invalidate(auth_url)
    tm1 = TM1Service(address=address, port=port,
                     cam_passport=get_passport(auth_url), ssl=True)
```

`PassportCache` is in-memory only and does not persist across Python processes.

---

## API reference

### `get_cam_passport`

```python
get_cam_passport(
    auth_url: str,
    profile_dir: str | None = None,
    timeout_seconds: int = 90,
    headless: bool = False,
    executable_path: str | None = None,
    verbose: bool = True,
) -> str
```

| Parameter | Description |
|---|---|
| `auth_url` | The Cognos dispatcher URL (e.g. `.../ibmcognos/bi/v1/disp`) |
| `profile_dir` | Persistent browser profile directory. Same directory = shared session. Different directories = isolated sessions. Defaults to `~/.tm1_auth/browser_profile`. |
| `timeout_seconds` | Seconds to wait for login before raising `PassportTimeoutError`. Default `90`. |
| `headless` | Run without a visible browser window. Not recommended for MFA flows. Default `False`. |
| `executable_path` | Path to a specific browser executable. If not set, tries system Edge then Chrome then Playwright's bundled Chromium. |
| `verbose` | Print progress messages to stdout. Default `True`. |

**Returns:** The `cam_passport` cookie value as a string.

**Raises:**
- `AuthenticationError` — browser failed to launch or could not navigate to the auth URL
- `PassportTimeoutError` — no passport detected within `timeout_seconds`

---

### `PassportCache`

```python
PassportCache(ttl_seconds: int = 3600)
```

| Method | Description |
|---|---|
| `get(auth_url)` | Return cached passport or `None` if missing/expired |
| `set(auth_url, passport)` | Cache a passport |
| `invalidate(auth_url)` | Remove a specific entry |
| `clear()` | Remove all entries |

---

## Exceptions

```python
from tm1_auth.exceptions import AuthenticationError, PassportTimeoutError
```

Both inherit from `AuthenticationError`. Catch `AuthenticationError` to handle all auth failures, or the specific subclass for finer control.

---

## Contributing

Contributions welcome. Please open an issue before submitting a pull request for significant changes.

---

## Licence

MIT
