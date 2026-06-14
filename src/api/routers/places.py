"""Places router – add a place, browse nearby, and view place detail."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_current_user, get_place_service
from src.schemas.places import CreatePlaceInput, PlaceListItem, PlaceOut
from src.services.place_service import PlaceService

router = APIRouter(prefix="/places", tags=["places"])


@router.post(
    "",
    response_model=PlaceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new place to the map",
)
async def create_place(
    body: CreatePlaceInput,
    current_user: dict = Depends(get_current_user),
    service: PlaceService = Depends(get_place_service),
) -> PlaceOut:
    """Add a new named location. The creator receives notifications when others review it."""
    return await service.create_place(body, created_by_id=current_user["user_id"])


@router.get(
    "/nearby",
    response_model=list[PlaceListItem],
    summary="Find places near a GPS coordinate",
)
async def nearby_places(
    lat: float = Query(..., description="Latitude of the user's location"),
    lng: float = Query(..., description="Longitude of the user's location"),
    radius_km: float = Query(10.0, description="Search radius in kilometres"),
    min_safety_score: float | None = Query(None, ge=1, le=5),
    tourism_type: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    service: PlaceService = Depends(get_place_service),
) -> list[PlaceListItem]:
    """Return places ordered by proximity.

    Optionally filter by minimum safety score (1-5) and tourism type.
    """
    return await service.get_nearby(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        min_safety_score=min_safety_score,
        tourism_type=tourism_type,
        limit=limit,
        offset=offset,
        current_user_id=current_user["user_id"],
    )


@router.get(
    "/mine",
    response_model=list[PlaceListItem],
    summary="List places added by the authenticated user",
)
async def my_places(
    current_user: dict = Depends(get_current_user),
    service: PlaceService = Depends(get_place_service),
) -> list[PlaceListItem]:
    """Return all places the current user has added (the 'discovered' places)."""
    return await service.get_my_places(current_user["user_id"])


@router.get(
    "/{place_id}",
    response_model=PlaceOut,
    summary="Get full details for a single place",
)
async def get_place(
    place_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: PlaceService = Depends(get_place_service),
) -> PlaceOut:
    """Return place details including aggregated safety score and safety label."""
    place = await service.get_place(place_id, current_user_id=current_user["user_id"])
    if place is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return place
