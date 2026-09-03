from typing import Protocol

import jwt
from jwt import InvalidTokenError, PyJWKClient


class InvalidIdentity(Exception):
    """Session token is missing, expired, or not from this Clerk app."""


class TokenVerifier(Protocol):
    def clerk_user_id(self, token: str) -> str: ...


def clerk_user_id_from_claims(claims: dict, *, authorized_party: str) -> str:
    """Take identity from the token. Ignore any role/plan fields a client might send."""
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise InvalidIdentity("token is missing sub")
    if authorized_party:
        if claims.get("azp") != authorized_party:
            raise InvalidIdentity("token authorized party mismatch")
    return sub.strip()


def issuer_from_jwks_url(jwks_url: str) -> str | None:
    marker = "/.well-known/jwks.json"
    if jwks_url.endswith(marker):
        return jwks_url[: -len(marker)]
    return None


class ClerkJwtVerifier:
    def __init__(self, jwks_url: str, authorized_party: str) -> None:
        self._jwks_url = jwks_url
        self._authorized_party = authorized_party
        self._client: PyJWKClient | None = None

    def clerk_user_id(self, token: str) -> str:
        if not self._jwks_url:
            raise InvalidIdentity("Clerk JWKS URL is not configured")
        if self._client is None:
            self._client = PyJWKClient(self._jwks_url)
        try:
            signing_key = self._client.get_signing_key_from_jwt(token)
            decode_kwargs: dict = {
                "algorithms": ["RS256"],
                "options": {"verify_aud": False},
            }
            issuer = issuer_from_jwks_url(self._jwks_url)
            if issuer:
                decode_kwargs["issuer"] = issuer
            claims = jwt.decode(token, signing_key.key, **decode_kwargs)
        except InvalidTokenError as exc:
            raise InvalidIdentity("invalid session token") from exc
        return clerk_user_id_from_claims(claims, authorized_party=self._authorized_party)
