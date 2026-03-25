from datetime import timedelta

import pytest
from sqlalchemy import select

from database.models.user import (
    UserModel,
    ActivationTokenModel,
    RefreshTokenModel,
    PasswordResetTokenModel
)
from tests.conftest import client

BASE_URL = "/api/v1/auth"

@pytest.mark.asyncio
async def test_register_new_user_success(client, db_session):
    payload = {"email": "new@test.com", "password": "Test1@Password!"}
    response = await client.post(url=f"{BASE_URL}/register", json=payload)

    fail_message = (
        f"Registration failed. Status code: {response.status_code}."
        " != 200"
    )
    assert response.status_code == 200, fail_message
    expected_message = "An activation link has sent to your email."
    fail_message = (
        f"Registration failed. Status code: {response.json()['message']} != "
        f"{expected_message}"
    )

    assert response.json()["message"] == expected_message, fail_message

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == payload["email"]))
    fail_message = "Registration failed. User doesn't exist in the database."
    assert user is not None, fail_message
    fail_message = "User registration. User is active after registration."
    assert not user.is_active, fail_message


@pytest.mark.asyncio
async def test_login_inactive_user_fails(client, registered_user):
    _, payload = registered_user
    response = await client.post(f"{BASE_URL}/login", json=payload)

    fail_message = (
        f"Login inactive user. Status code: {response.status_code} != 403."
    )
    assert response.status_code == 403, fail_message
    expected_message = (
        "Account is not activated. Please check your email."
    )
    fail_message = (
        f"Login inactive user. Message: {response.json()['detail']} != "
        f"{expected_message}"
    )
    assert response.json()["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_login_with_wrong_credentials(client):
    response = await client.post(
        url=f"{BASE_URL}/login",
        json={
            "email": "wrong@test.com",
            "password": "Wrong_Password123@#"
        }
    )
    fail_message = (
        f"Login with wrong credentials. Status code: {response.status_code} "
        f"!= 401"
    )
    assert response.status_code == 401, fail_message
    data = response.json()
    expected_message = "Incorrect email or password"
    fail_message = (
        f"Login with wrong credentials: {data['detail']} != "
        f"{expected_message}"
    )
    assert data["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_user_activation_success(client, db_session, registered_user):
    user, _ = registered_user
    token_inst = await db_session.scalar(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id
        )
    )
    response = await client.get(
        f"{BASE_URL}/activate?token={token_inst.token}"
    )
    fail_message = (
        f"User activation failed. Status code: {response.status_code} != 200."
    )
    assert response.status_code == 200, fail_message
    expected_message = "Account successfully activated! You can now log in."
    fail_message = (
        f"Account activation by link. Response message: "
        f"{response.json()["message"]} != {expected_message}"
    )
    assert response.json()["message"] == expected_message, fail_message

    await db_session.refresh(user)
    assert user.is_active
    no_token = await db_session.scalar(
        select(ActivationTokenModel).where(
            ActivationTokenModel.token == token_inst.token
        )
    )
    fail_message = "User activation. Activation token has not been deleted."
    assert no_token is None, fail_message


@pytest.mark.asyncio
async def test_login_success_after_activation(
        client, db_session, logged_in_active_user
):
    _, _, token_pair = logged_in_active_user
    fail_message = (
        "Login active user. The token pair hasn't been provided."
    )
    assert "access_token" in token_pair, fail_message


@pytest.mark.asyncio
async def test_password_change_wrong_old_password(
        client,
        logged_in_active_user,
        db_session
):
    _, _, token_pair = logged_in_active_user
    response = await client.post(
        url=f"{BASE_URL}/password-change",
        json={"old_password": "WrongPassword123!",
              "password": "NewSecurePassword123!"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"Password change (wrong old password). Status code: "
        f"{response.status_code} != 200."
    )
    assert response.status_code == 401, fail_message
    assert response.json()["detail"] == "Incorrect old password."


@pytest.mark.asyncio
async def test_refresh_token(client, db_session, logged_in_active_user):
    # Refresh Wrong Token
    _, _, token_pair = logged_in_active_user
    response = await client.post(
        url=f"{BASE_URL}/refresh",
        json={"refresh_token": "wrong_token"}
    )
    assert response.status_code == 401
    wrong_data = response.json()
    fail_message = (
        "Refresh token pair (true token). Error message: "
        f"{wrong_data['detail']} != 'Invalid refresh token'"
    )
    assert wrong_data["detail"] == "Invalid refresh token", fail_message

    # Refresh True Token
    response = await client.post(
        url=f"{BASE_URL}/refresh",
        json={
            "refresh_token": token_pair["refresh_token"],
        }
    )
    fail_message = (
        "Refresh token pair (true token). "
        f"Status code: {response.status_code} != 200"
    )
    assert response.status_code == 200, fail_message
    data = response.json()
    fail_message = (
        "Refresh token pair (true token). No access token in response."
    )
    assert "access_token" in data, fail_message


@pytest.mark.asyncio
async def test_password_change_with_wrong_token(
        client, db_session, logged_in_active_user
):
    _, _, token_pair = logged_in_active_user
    response = await client.post(
        url=f"{BASE_URL}/password-change",
        json={
            "old_password": "WrongOldPassword$1",
            "password": "NewTestUserPassword#1"
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        "Change password with token (wrong old password). "
        f"Status code: {response.status_code} != 401"
    )
    assert response.status_code == 401, fail_message
    wrong_data = response.json()
    expected_message = "Incorrect old password."
    fail_message = (
        "Change password with token (wrong old password). Error message: "
        f"{wrong_data['detail']} != {expected_message}"
    )
    assert wrong_data['detail'] == expected_message, fail_message


@pytest.mark.asyncio
async def test_logout(client, db_session, logged_in_active_user):
    _, _, token_pair = logged_in_active_user
    response = await client.post(
        url=f"{BASE_URL}/logout",
        json={
            "refresh_token": token_pair["refresh_token"]
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = f"Logout. Status code: {response.status_code} != 200"
    assert response.status_code == 200, fail_message
    response_data = response.json()
    expected_message = "Successfully logged out"
    fail_message = (
        f"Logout. Success message: {response_data['message']} != "
        f"{expected_message}"
    )
    assert response_data["message"] == expected_message, fail_message
    refresh_token = await db_session.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token == token_pair["refresh_token"]
        )
    )
    fail_message = "Logout. Refresh token has not been deleted."
    assert refresh_token is None, fail_message


@pytest.mark.asyncio
async def test_password_change_with_correct_token(
        client, logged_in_active_user
):
    _, payload, token_pair = logged_in_active_user
    response = await client.post(
        url=f"{BASE_URL}/password-change",
        json={
            "old_password": payload["password"],
            "password": "NewTestUserPassword$1"
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"Change password with token. Status code: {response.status_code} "
        "!= 200"
    )
    assert response.status_code == 200, fail_message
    data = response.json()
    expected_message = "Password changed successfully"
    fail_message = (
        f"Change password with token. Success message: {data['message']} != "
        f"{expected_message}"
    )
    assert data["message"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_existing_user_registration(client, db_session, registered_user):
    _, payload = registered_user
    response = await client.post(
        f"{BASE_URL}/register",
        json=payload
    )
    fail_message = (
        f"Existing user registration. Status code: {response.status_code} "
        f"!= 400"
    )
    assert response.status_code == 400, fail_message
    data = response.json()
    expected_message = "A user with this email already exists."
    fail_message = (
        f"Existing user registration. Error message: {data['detail']} != "
        f"{expected_message}"
    )
    assert data["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_reset_password(client, db_session, logged_in_active_user):
    user, payload, _ = logged_in_active_user
    response = await client.post(
        url=f"{BASE_URL}/password-reset-request",
        json={
            "email": payload["email"]
        }
    )
    fail_message = (
        f"Password reset request. Status code: {response.status_code} != 200"
    )
    assert response.status_code == 200, fail_message
    data = response.json()
    expected_message = "If the account exists, a reset email has been sent."
    fail_message = (
        f"Password reset request. Message: {data['message']} "
        f"!= {expected_message}"
    )
    assert data["message"] == expected_message, fail_message
    reset_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    fail_message = f"Password reset request. Reset token doesn't exist"
    assert reset_token is not None, fail_message

    response = await client.post(
        url=f"{BASE_URL}/password-reset-confirm",
        json={
            "token": reset_token.token,
            "password": "NewTestUserPassword#1"
        }
    )
    fail_message = (
        f"Reset password confirm (valid token). Status code: "
        f"{response.status_code} != 200"
    )
    assert response.status_code == 200, fail_message
    data = response.json()
    expected_message = "Password updated successfully."
    fail_message = (
        f"Reset password confirm. Success message: {data['message']} != "
        f"{expected_message}"
    )
    assert data["message"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_reset_password_with_invalid_token(
        client, db_session, logged_in_active_user
):
    response = await client.post(
        url=f"{BASE_URL}/password-reset-confirm",
        json={
            "token": "wrong-token",
            "password": "NewTestUserPassword#1"
        }
    )
    fail_message = (
        f"Reset password confirm (invalid token). Status code: "
        f"{response.status_code} != 400"
    )
    assert response.status_code == 400, fail_message
    data = response.json()
    expected_message = "Invalid or already used reset token."
    fail_message = (
        f"Reset password confirm (invalid token). Exception detail: "
        f"{data['detail']} != {expected_message}"
    )
    assert data["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_reset_password_with_expired_token(
        client, db_session, logged_in_active_user
):
    user, payload, _ = logged_in_active_user

    await client.post(
        url=f"{BASE_URL}/password-reset-request",
        json={
            "email": payload["email"]
        }
    )
    reset_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    reset_token.expires_at -= timedelta(weeks=1)
    await db_session.commit()
    await db_session.refresh(reset_token)
    response = await client.post(
        url=f"{BASE_URL}/password-reset-confirm",
        json={
            "token": reset_token.token,
            "password": "NewTestUserPassword#1"
        }
    )
    fail_message = (
        f"Reset password confirm (expired token). Status code "
        f"{response.status_code} != 400"
    )
    assert response.status_code == 400, fail_message
    data = response.json()
    expected_message = "Reset link has expired."
    fail_message = (
        f"Reset password confirm (expired token). Exception detail: "
        f"{data['detail']} != {expected_message}"
    )
    assert data["detail"] == expected_message, fail_message

    reset_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token == reset_token.token
        )
    )
    fail_message = (
        "Reset password confirm (expired token). Token hasn't been deleted."
    )
    assert reset_token is None, fail_message


@pytest.mark.asyncio
async def test_reset_password_not_existed_user(
        client, db_session, logged_in_active_user
):
    user, payload, _ = logged_in_active_user
    await client.post(
        url=f"{BASE_URL}/password-reset-request",
        json={
            "email": payload["email"]
        }
    )
    reset_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    reset_token.user_id = -1
    await db_session.commit()
    await db_session.refresh(reset_token)
    response = await client.post(
        url=f"{BASE_URL}/password-reset-confirm",
        json={
            "token": reset_token.token,
            "password": "NewTestUserPassword#1"
        }
    )
    fail_message = (
        f"Reset password confirm (user doesn't exist). Status code "
        f"{response.status_code} != 404"
    )
    assert response.status_code == 404, fail_message
    data = response.json()
    fail_message = (
        f"Reset password confirm (user doesn't exist). Exception detail: "
        f"{data['detail']} != 'User not found.'"
    )
    assert data["detail"] == "User not found.", fail_message
    reset_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token == reset_token.token
        )
    )
    fail_message = (
        "Reset password confirm (user doesn't exist). Token hasn't been deleted."
    )
    assert reset_token is None, fail_message


@pytest.mark.parametrize(
    "email, password, expected_error",
    [
        (
                "wrong_email",
                "Valid@User2Password",
                "value is not a valid email address"
        ),
        (
                "test@test.com",
                "simplepassword",
                "Value error, Password must contain at least one number."
        ),
        (
                "test@test.com",
                "simple1password",
                "Value error, Password must contain at least one uppercase letter."
        ),
        (
                "test@test.com",
                "Simple1Password",
                "Value error, Password must contain at least one special character."
        )
    ]
)
@pytest.mark.asyncio
async def test_invalid_credentials(client, email, password, expected_error):
    response = await client.post(
        url=f"{BASE_URL}/register",
        json={
            "email": email,
            "password": password
        }
    )
    fail_message = (
        f"Invalid credentials. Status code: {response.status_code} != 422"
    )
    assert response.status_code == 422, fail_message
    fail_message = (
        f"Invalid credentials. Response text: {response.text} !=",
        expected_error
    )
    assert expected_error in response.text, fail_message
