"""Place service – business logic for creating and querying places."""

import uuid
from typing import cast

from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.models.places import Place
from src.repositories.place_repository import PlaceRepository
from src.schemas.places import (
    CreatePlaceInput,
    PlaceListItem,
    PlaceOut,
    compute_safety_label,
)


class PlaceService:
    """Handles place creation and spatial discovery queries."""

    def __init__(self, place_repo: PlaceRepository) -> None:
        self._places = place_repo

    async def create_place(self, data: CreatePlaceInput, created_by_id: uuid.UUID) -> PlaceOut:
        """Add a new place to the map.

        The PostGIS POINT is built from (lng, lat) per the WGS84 convention.
        """
        geom = from_shape(Point(data.lng, data.lat), srid=4326)
        place = Place(
            name=data.name,
            location=geom,
            address=data.address,
            city=data.city,
            country=data.country,
            created_by_id=created_by_id,
        )
        place = await self._places.create(place)
        return self._to_place_out(place, current_user_id=created_by_id)

    async def get_place(self, place_id: uuid.UUID, current_user_id: uuid.UUID | None = None) -> PlaceOut | None:
        """Return a single place by ID with full details."""
        place = await self._places.get_by_id(place_id)
        if place is None:
            return None
        return self._to_place_out(place, current_user_id=current_user_id)

    async def get_nearby(
        self,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        min_safety_score: float | None = None,
        tourism_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
        current_user_id: uuid.UUID | None = None,
    ) -> list[PlaceListItem]:
        """Return places within radius_km filtered by safety and tourism type."""
        from src.models.enums import TourismType  # local import avoids top-level dep

        tourism_enum = TourismType(tourism_type) if tourism_type else None
        rows = await self._places.get_nearby(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            min_safety_score=min_safety_score,
            tourism_type=tourism_enum,
            limit=limit,
            offset=offset,
        )
        return [self._to_list_item(row["place"], distance_km=row["distance_km"]) for row in rows]

    async def get_my_places(self, user_id: uuid.UUID) -> list[PlaceListItem]:
        """Return all places added by the authenticated user."""
        places = await self._places.get_by_creator(user_id)
        return [self._to_list_item(p) for p in places]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_lat_lng(place: Place) -> tuple[float, float]:
        """Extract scalar lat/lng from the PostGIS geometry column."""
        from geoalchemy2.shape import to_shape

        pt = cast(Point, to_shape(place.location))
        return pt.y, pt.x  # WGS84: y=lat, x=lng

    def _to_list_item(self, place: Place, distance_km: float | None = None) -> PlaceListItem:
        lat, lng = self._extract_lat_lng(place)
        return PlaceListItem(
            id=place.id,
            name=place.name,
            lat=lat,
            lng=lng,
            city=place.city,
            country=place.country,
            average_safety_score=place.average_safety_score,
            safety_label=compute_safety_label(place.average_safety_score),
            total_reviews=place.total_reviews,
            dominant_tourism_type=place.dominant_tourism_type,
            distance_km=distance_km,
            created_at=place.created_at,
        )

    def _to_place_out(self, place: Place, current_user_id: uuid.UUID | None = None) -> PlaceOut:
        lat, lng = self._extract_lat_lng(place)
        return PlaceOut(
            id=place.id,
            name=place.name,
            lat=lat,
            lng=lng,
            address=place.address,
            city=place.city,
            country=place.country,
            average_safety_score=place.average_safety_score,
            safety_label=compute_safety_label(place.average_safety_score),
            total_reviews=place.total_reviews,
            dominant_tourism_type=place.dominant_tourism_type,
            distance_km=None,
            created_at=place.created_at,
            created_by_id=place.created_by_id,
            last_review_at=place.last_review_at,
            is_discovered_by_me=(current_user_id is not None and place.created_by_id == current_user_id),
        )
