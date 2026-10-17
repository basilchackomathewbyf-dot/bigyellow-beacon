"""Auth: roster pairing, opaque device tokens, session JWT, role deps."""

from app.auth.deps import AuthPrincipal, get_current_user, require_role

__all__ = ["AuthPrincipal", "get_current_user", "require_role"]
