import uuid


def test_access_token_decodes_with_jti():
    from src.services.auth_service import create_access_token, decode_token

    token, expires_in = create_access_token(uuid.uuid4())
    payload = decode_token(token)

    assert payload.type == "access"
    assert payload.jti
    assert expires_in > 0


def test_refresh_token_decodes_with_jti():
    from src.services.auth_service import create_refresh_token, decode_token

    token = create_refresh_token(uuid.uuid4())
    payload = decode_token(token)

    assert payload.type == "refresh"
    assert payload.jti


def test_token_remaining_seconds_is_never_negative():
    from src.schemas.auth import TokenPayload
    from src.services.auth_service import get_token_remaining_seconds

    payload = TokenPayload(sub=str(uuid.uuid4()), type="access", exp=0, jti="token-1")

    assert get_token_remaining_seconds(payload) == 0
