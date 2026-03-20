class AuthenticationError(Exception):
    """Raised when the browser fails to launch or the login flow errors."""
    pass


class PassportTimeoutError(AuthenticationError):
    """Raised when no cam_passport cookie is detected within the timeout."""
    pass
