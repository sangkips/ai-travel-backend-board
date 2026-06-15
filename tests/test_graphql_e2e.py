"""End-to-end exercise of the GraphQL API against a real DB + Valkey.

Drives the full user journey through the ``/graphql`` endpoint: sign-up,
login, place creation, spatial search, reviews, votes, and notifications —
plus the key authorization/validation rejections.
"""

import uuid

import httpx

SUFFIX = uuid.uuid4().hex[:8]


async def _gql(client: httpx.AsyncClient, query: str, token: str | None = None) -> dict:
    """POST a GraphQL operation and return the raw JSON body."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = await client.post("/graphql", json={"query": query}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _data(client, query, token=None) -> dict:
    """Run an operation expected to succeed; assert no GraphQL errors."""
    body = await _gql(client, query, token)
    assert not body.get("errors"), body.get("errors")
    return body["data"]


async def _expect_error(client, query, token=None) -> str:
    """Run an operation expected to fail; return the first error message."""
    body = await _gql(client, query, token)
    assert body.get("errors"), f"expected an error, got: {body}"
    return body["errors"][0]["message"]


async def test_full_graphql_flow(client: httpx.AsyncClient):
    guide_email = f"guide_{SUFFIX}@example.com"
    tourist_email = f"tourist_{SUFFIX}@example.com"

    # 1. Sign up two users (a place creator and a reviewer).
    d = await _data(
        client,
        f'mutation {{ signUp(data: {{name: "Guide {SUFFIX}", email: "{guide_email}",'
        f' role: TOUR_GUIDE, password: "supersecret"}}) {{ accessToken tokenType }} }}',
    )
    guide = d["signUp"]["accessToken"]
    assert d["signUp"]["tokenType"] == "bearer"

    d = await _data(
        client,
        f'mutation {{ signUp(data: {{name: "Tourist {SUFFIX}", email: "{tourist_email}",'
        f' role: TOURIST, password: "supersecret"}}) {{ accessToken }} }}',
    )
    tourist = d["signUp"]["accessToken"]

    # Duplicate email is rejected.
    msg = await _expect_error(
        client,
        f'mutation {{ signUp(data: {{name: "Dup", email: "{guide_email}",'
        f' role: TOURIST, password: "supersecret"}}) {{ accessToken }} }}',
    )
    assert "already exists" in msg.lower()

    # 2. Login (and reject a wrong password).
    d = await _data(
        client,
        f'mutation {{ login(data: {{email: "{guide_email}", password: "supersecret"}}) {{ accessToken }} }}',
    )
    assert d["login"]["accessToken"]
    await _expect_error(
        client,
        f'mutation {{ login(data: {{email: "{guide_email}", password: "WRONG"}}) {{ accessToken }} }}',
    )

    # 3. me — authenticated identity, and null when anonymous.
    d = await _data(client, "{ me { id name role reputationScore } }", token=guide)
    assert d["me"]["role"] == "TOUR_GUIDE"
    assert d["me"]["name"] == f"Guide {SUFFIX}"
    d = await _data(client, "{ me { id } }")
    assert d["me"] is None

    # 4. Create a place (requires auth).
    pname = f"Watamu Beach {SUFFIX}"
    d = await _data(
        client,
        f'mutation {{ createPlace(data: {{name: "{pname}", lat: -3.35, lng: 40.02,'
        f' city: "Watamu", country: "Kenya"}}) {{ id name safetyLabel isDiscoveredByMe }} }}',
        token=guide,
    )
    place = d["createPlace"]
    place_id = place["id"]
    assert place["isDiscoveredByMe"] is True
    assert place["safetyLabel"] == "AVOID"  # no reviews yet → default

    await _expect_error(
        client,
        f'mutation {{ createPlace(data: {{name: "{pname} x", lat: 0, lng: 0}}) {{ id }} }}',
    )

    # 5. Fetch by id, spatial nearby search, and "my places".
    d = await _data(client, f'{{ place(placeId: "{place_id}") {{ name city }} }}', token=guide)
    assert d["place"]["name"] == pname

    d = await _data(
        client,
        "{ nearbyPlaces(lat: -3.35, lng: 40.02, radiusKm: 25) { id name distanceKm safetyLabel } }",
        token=guide,
    )
    hit = next((p for p in d["nearbyPlaces"] if p["id"] == place_id), None)
    assert hit is not None
    assert hit["distanceKm"] == 0.0

    # tourismType filter accepts a valid enum (no results expected yet).
    await _data(
        client,
        "{ nearbyPlaces(lat: -3.35, lng: 40.02, radiusKm: 25, tourismType: ADVENTURE) { id } }",
        token=guide,
    )
    # invalid enum value is rejected by the schema, not 500.
    await _expect_error(
        client,
        "{ nearbyPlaces(lat: -3.35, lng: 40.02, tourismType: NOPE) { id } }",
        token=guide,
    )

    d = await _data(client, "{ myPlaces { id } }", token=guide)
    assert any(p["id"] == place_id for p in d["myPlaces"])

    # 6. Tourist reviews the guide's place.
    d = await _data(
        client,
        f'mutation {{ createReview(data: {{placeId: "{place_id}", safetyScore: 5,'
        f' tourismType: NATURE, text: "Safe and lovely"}}) {{ id safetyScore createdAt }} }}',
        token=tourist,
    )
    review_id = d["createReview"]["id"]

    d = await _data(client, f'{{ placeReviews(placeId: "{place_id}") {{ id }} }}', token=guide)
    assert any(r["id"] == review_id for r in d["placeReviews"])

    d = await _data(client, "{ myReviews { id } }", token=tourist)
    assert any(r["id"] == review_id for r in d["myReviews"])

    # Aggregates on the place recompute after the review.
    d = await _data(
        client,
        f'{{ place(placeId: "{place_id}") {{ totalReviews averageSafetyScore safetyLabel }} }}',
        token=guide,
    )
    assert d["place"]["totalReviews"] == 1
    assert d["place"]["averageSafetyScore"] == 5.0
    assert d["place"]["safetyLabel"] == "SAFE"

    # 7. Voting — guide upvotes; self-vote is blocked.
    d = await _data(
        client,
        f'mutation {{ voteReview(data: {{reviewId: "{review_id}", isUpvote: true}}) {{ upvoteCount myVote }} }}',
        token=guide,
    )
    assert d["voteReview"]["upvoteCount"] == 1
    assert d["voteReview"]["myVote"] is True

    msg = await _expect_error(
        client,
        f'mutation {{ voteReview(data: {{reviewId: "{review_id}", isUpvote: true}}) {{ id }} }}',
        token=tourist,
    )
    assert "own review" in msg.lower()

    # 8. The guide is notified of the new review; mark it read.
    d = await _data(client, "{ notifications { id placeName reviewerRole isRead } }", token=guide)
    notif = next((n for n in d["notifications"] if n["placeName"] == pname), None)
    assert notif is not None
    assert notif["reviewerRole"] == "TOURIST"
    assert notif["isRead"] is False

    d = await _data(
        client,
        f'mutation {{ markNotificationRead(notificationId: "{notif["id"]}") }}',
        token=guide,
    )
    assert d["markNotificationRead"] is True

    d = await _data(client, "{ notifications(unreadOnly: true) { id } }", token=guide)
    assert not any(n["id"] == notif["id"] for n in d["notifications"])
