import pytest

BASE_URL = "/api/v1/movie_theater"


@pytest.mark.asyncio
async def test_create_movie_as_admin(client, admin_user, sample_movie_data):
    _, _, tokens = admin_user
    response = await client.post(
        f"{BASE_URL}/movies",
        json=sample_movie_data,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Inception" in data["name"]
    assert data["certification"]["name"] == "PG-13"


@pytest.mark.asyncio
async def test_create_movie_forbidden_for_regular_user(
        client, logged_in_active_user, sample_movie_data
):
    _, _, tokens = logged_in_active_user
    response = await client.post(
        f"{BASE_URL}/movies",
        json=sample_movie_data,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_movies_list_and_filtering(
        client, admin_user, sample_movie_data
):
    _, _, tokens = admin_user
    await client.post(
        f"{BASE_URL}/movies",
        json=sample_movie_data,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    # Test filtering by name
    response = await client.get(
        f"{BASE_URL}/movies",
        params={"name": "Inception"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) > 0

    # Test filtering by year
    response = await client.get(
        f"{BASE_URL}/movies",
        params={"min_year": 2000, "max_year": 2020},
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.json()["total_items"] >= 1


@pytest.mark.asyncio
async def test_get_movie_by_id_404(client):
    response = await client.get(f"{BASE_URL}/movies/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found."


@pytest.mark.asyncio
async def test_update_movie(client, admin_user, sample_movie_data):
    _, _, tokens = admin_user
    # Create
    create_res = await client.post(
        f"{BASE_URL}/movies",
        json=sample_movie_data,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    movie_id = create_res.json()["id"]

    # Update
    update_payload = {"name": "Inception Updated", "imdb": 9.0}
    response = await client.patch(
        f"{BASE_URL}/movies/{movie_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Inception Updated"
    assert response.json()["imdb"] == 9.0


@pytest.mark.asyncio
async def test_rate_movie(
        client, db_session, logged_in_user_with_profile, test_movie
):
    _, tokens = logged_in_user_with_profile
    movie = test_movie
    rating_payload = {"score": 10}
    response = await client.post(
        f"{BASE_URL}/movies/{movie.id}/rate",
        json=rating_payload,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["user_score"] == 10
    assert response.json()["total_ratings"] == 1


@pytest.mark.asyncio
async def test_toggle_favorite(
        client, logged_in_user_with_profile, test_movie
):
    user_obj, tokens = logged_in_user_with_profile
    movie = test_movie

    # Favorite
    response = await client.post(
        f"{BASE_URL}/{movie.id}/favorite",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert "added to favorites" in response.json()["message"]

    # Unfavorite
    response = await client.post(
        f"{BASE_URL}/{movie.id}/favorite",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert "removed from favorites" in response.json()["message"]


@pytest.mark.asyncio
async def test_delete_movie(client, admin_user, sample_movie_data):
    _, _, tokens = admin_user
    res = await client.post(
        f"{BASE_URL}/movies",
        json=sample_movie_data,
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    movie_id = res.json()["id"]

    response = await client.delete(
        f"{BASE_URL}/movies/{movie_id}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Movie deleted."


@pytest.mark.asyncio
async def test_get_genres_list(client, admin_user):
    _, _, tokens = admin_user
    response = await client.get(
        f"{BASE_URL}/genres",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert "items" in response.json()
