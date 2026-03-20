# tm1-auth

A Python library for authenticating with IBM Planning Analytics (TM1) in environments that use Cognos Access Manager (CAM) with multi-factor authentication.

TM1py requires a `cam_passport` to connect to CAM-secured environments, but obtaining one programmatically is non-trivial when MFA is involved. `tm1-auth` handles the browser-based login flow for you, captures the passport automatically, and caches it for reuse — so you only go through MFA once per session, even across multiple environments.

---

## Features

- Automated CAM passport retrieval via a browser login window
- Passport caching — reuse across multiple connections without re-authenticating
- Single MFA challenge across multiple environments (STG, PRD etc.) when using the same identity provider (e.g. Okta)
- Works alongside TM1py — just pass the retrieved passport to `TM1Service`
- Supports system browsers (Edge, Chrome) as well as Playwright's bundled Chromium

---

## Requirements

- Python 3.8+
- [Playwright](https://playwright.dev/python/) (`pip install playwright && playwright install chromium`)
- A TM1 / Planning Analytics environment secured with CAM

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

A browser window opens, you log in (including MFA), and the passport is captured automatically. The window closes once the passport is detected.

---

## Multiple environments
 
By default all calls share the same browser profile (`~/.tm1_auth/browser_profile`).
Whether this is useful depends entirely on your setup:
 
**Isolated sessions (recommended if environments have different credentials):**
 
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
 
**Shared session (if environments share the same identity provider):**
 
```python
stg_passport = get_cam_passport(
    auth_url="https://stg-cognos/ibmcognos/bi/v1/disp",
)
 
prd_passport = get_cam_passport(
    auth_url="https://prd-cognos/ibmcognos/bi/v1/disp",
)
```
 
Both calls use the default shared profile. If your identity provider (e.g. Okta,
Azure AD) supports SSO, the second call may complete without prompting for
credentials or MFA again — the IdP session cookie from the first login is
already in the shared profile.
 
This is not guaranteed. It depends entirely on your IdP configuration and session
policies. Do not rely on this behaviour if environments have different credentials.

## API reference

### `get_cam_passport`

```python
get_cam_passport(
    auth_url: str,
    profile_dir: str | None = None,
    timeout_seconds: int = 90,
    headless: bool = False,
    executable_path: str | None = None,
) -> str
```

Opens a browser, navigates to `auth_url`, and waits for a `cam_passport` cookie to appear.

| Parameter | Description |
|---|---|
| `auth_url` | The Cognos dispatcher URL (e.g. `.../ibmcognos/bi/v1/disp`) |
| `profile_dir` | Path to a persistent browser profile directory. Defaults to `~/.tm1_auth/browser_profile`. Reusing the same directory preserves the IdP session across calls. |
| `timeout_seconds` | How long to wait for login before raising `TimeoutError`. Default `90`. |
| `headless` | Run the browser without a visible window. Not recommended for MFA flows. Default `False`. |
| `executable_path` | Path to a specific browser executable. If not set, tries system Edge then Playwright's Chromium. |

**Returns:** The `cam_passport` cookie value as a string.

**Raises:** `TimeoutError` if no passport is detected within `timeout_seconds`.

---

## How it works

1. A persistent browser context is launched pointing at your Cognos auth URL
2. You complete the login flow manually (username, password, MFA)
3. `tm1-auth` polls the browser's cookies until it detects a `cam_passport` cookie
4. The browser closes and the passport value is returned
5. On subsequent calls using the same `profile_dir`, the browser profile already contains your IdP session cookie — if your identity provider supports SSO, no further MFA is required

---

## Django / web app integration

If you're building a web application, you'll want to trigger the browser login from a background thread or async task rather than blocking the request/response cycle. See the [Django integration guide](docs/django.md) for a pattern that works with session-based passport caching.

---

## Roadmap

- [ ] Windows integrated authentication (Kerberos / NTLM)
- [ ] API key authentication (Planning Analytics on Cloud)
- [ ] Async support (`asyncio` compatible)
- [ ] Passport expiry detection and automatic refresh

---

## Contributing

Contributions welcome. Please open an issue before submitting a pull request for significant changes.

---

## Licence

MIT
