from typing import Optional

# TODO: Improve commenting in this file for a docstring for the class and its methods.

_SERVICE = "tm1-auth"

class KeyringCache:
    def __init__(self, service: str = _SERVICE):
        import keyring as _keyring
        self.service = service

    def get(self, auth_url: str) -> Optional[str]:
        import keyring
        try:
            return keyring.get_password(self.service, auth_url)
        except Exception:
            return None
        
    def set(self, auth_url: str, passport: str) -> None:
        import keyring
        try:
            keyring.set_password(self.service, auth_url, passport)
        except Exception:
            pass

    def invalidate(self, auth_url: str) -> None:
        import keyring
        try:
            keyring.delete_password(self.service, auth_url)
        except keyring.errors.PasswordDeleteError:
            pass

    def clear(self) -> None:
        import keyring
        try:
            keyring.delete_password(self.service, "*")
        except keyring.errors.PasswordDeleteError:
            pass