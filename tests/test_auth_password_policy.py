from src.schemas.auth import ForgotPasswordConfirmRequest, RegisterRequest
from src.schemas.user import PasswordChange, UserCreate


def test_register_request_accepts_short_test_password():
    request = RegisterRequest(
        email="learner@example.com",
        password="x",
        full_name="Learner Example",
    )

    assert request.password == "x"


def test_forgot_password_confirm_accepts_short_test_password():
    request = ForgotPasswordConfirmRequest(
        token="reset-token-12345",
        new_password="x",
    )

    assert request.new_password == "x"


def test_user_create_accepts_short_test_password():
    request = UserCreate(
        email="learner@example.com",
        password="x",
        full_name="Learner Example",
    )

    assert request.password == "x"


def test_password_change_accepts_short_test_password():
    request = PasswordChange(
        current_password="old-password",
        new_password="x",
    )

    assert request.new_password == "x"
