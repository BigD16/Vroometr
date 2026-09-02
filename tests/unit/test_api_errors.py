from app.errors import AppError, error_body


def test_error_body_shape() -> None:
    body = error_body("not_found", "Bike not found")
    assert body == {"error": {"code": "not_found", "message": "Bike not found"}}


def test_app_error_defaults_to_400() -> None:
    err = AppError("bad_request", "Invalid hours")
    assert err.status_code == 400
    assert err.code == "bad_request"
