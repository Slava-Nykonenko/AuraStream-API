import uuid

import pytest

BASE_URL = "/api/v1/admin"


@pytest.mark.asyncio
async def test_admin_user_activate_by_user(
        client, db_session, logged_in_active_user, admin_user
):
    user_obj, user_payload, user_tokens = logged_in_active_user
    response = await client.patch(
        url=f"{BASE_URL}/activate-user",
        json={"email": user_payload["email"]},
        headers={
            "Authorization": f"Bearer {user_tokens['access_token']}"
        }
    )
    expected_message = "You do not have enough permissions to access this resource."
    fail_message = (
        f"Manual user activation by a USER. Status code: {response.status_code}"
        f" != 403"
    )
    assert response.status_code == 403, fail_message
    fail_message = (
        f"Manual user activation by a USER. Received message: "
        f"{response.json()['detail']} != {expected_message}"
    )
    assert response.json()["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_admin_404_user_activate(
        client, db_session, admin_user
):
    _, _, token_pair = admin_user
    response = await client.patch(
        url=f"{BASE_URL}/activate-user",
        json={"email": f"{uuid.uuid4()}@non-exist.com"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"Manual non-existent user activation by ADMIN. Status code: "
        f"{response.status_code} != 404"
    )
    assert response.status_code == 404, fail_message
    expected_message = "User not found."
    fail_message = (
        f"Manual non-existent user activation by ADMIN. Received message: "
        f"{response.text} != {expected_message}"
    )
    assert response.json()["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_admin_user_activate(
        client, registered_user, admin_user
):
    user, user_payload = registered_user
    _, _, token_pair = admin_user
    response = await client.patch(
        url=f"{BASE_URL}/activate-user",
        json={"email": user_payload["email"]},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    expected_message = f"User {user_payload['email']} activated by admin."
    fail_message = (
        f"Manual user activation by ADMIN. Status code: {response.status_code}"
        f" != 200"
    )
    assert response.status_code == 200, fail_message
    data = response.json()
    fail_message = (
        f"Manual user activation by ADMIN. Received message: "
        f"{data['message']} != {expected_message}"
    )
    assert data["message"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_admin_active_user_activate(
        client, admin_user, logged_in_active_user
):
    _, user_payload, _ = logged_in_active_user
    _, _, token_pair = admin_user
    response = await client.patch(
        url=f"{BASE_URL}/activate-user",
        json={"email": user_payload["email"]},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"Manual active user activation by ADMIN. Status code: "
        f"{response.status_code} != 400"
    )
    assert response.status_code == 400, fail_message
    expected_message = "User is already active."
    fail_message = (
        f"Manual active user activation. Received message: {response.text} != "
        f"{expected_message}"
    )
    assert response.json()["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_user_change_user_status(
        client, logged_in_active_user, registered_user
):
    _, _, token_pair = logged_in_active_user
    _, payload = registered_user
    response = await client.patch(
        url=f"{BASE_URL}/change-user-status",
        json={
            "email": payload["email"],
            "user_group": "ADMIN"
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"User changes user's status. Status code: {response.status_code}"
        f" != 403"
    )
    assert response.status_code == 403, fail_message


@pytest.mark.asyncio
async def test_admin_change_404_user_status(
        client, admin_user, logged_in_active_user
):
    _, _, token_pair = admin_user
    _, payload, _ = logged_in_active_user
    response = await client.patch(
        url=f"{BASE_URL}/change-user-status",
        json={
            "email": f"{uuid.uuid4()}@non-exist.com",
            "user_group": "MODERATOR"
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"Changing non-existent user status. Status code: "
        f"{response.status_code} != 404"
    )
    assert response.status_code == 404, fail_message
    expected_message = "User not found."
    fail_message = (
        f"Changing non-existent user status. Received message: "
        f"{response.text} != {expected_message}"
    )
    assert response.json()["detail"] == expected_message, fail_message


@pytest.mark.asyncio
async def test_admin_change_user_status(
        client, admin_user, logged_in_active_user
):
    _, _, token_pair = admin_user
    user, payload, _ = logged_in_active_user
    response = await client.patch(
        url=f"{BASE_URL}/change-user-status",
        json={
            "email": payload["email"],
            "user_group": "MODERATOR"
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    fail_message = (
        f"Admin changes user's status. Status code: {response.status_code} "
        f"!= 200"
    )
    assert response.status_code == 200, fail_message
    expected_message = (
        f"User with ID {user.id} (email: {user.email}) has been moved "
        f"into the MODERATOR group."
    )
    fail_message = (
        f"Admin changes user's status. Received message: "
        f"{response.json()['message']} != {expected_message}"
    )
    assert response.json()["message"] == expected_message, fail_message
