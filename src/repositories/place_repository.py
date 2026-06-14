"""Place repository – all DB access for the places table.

Nearby search uses PostGIS ``ST_DWithin`` with a geography cast so the
radius is specified in metres and the index is used correctly.
"""

import uuid
from typing import Any

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin
from sqlalchemy import cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import TourismType
from src.models.places import Place


class PlaceRepository:
    """Data-access layer for Place records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, place: Place) -> Place:
        """Persist a new place and return it with DB-generated fields."""
        self.db.add(place)
        await self.db.commit()
        await self.db.refresh(place)
        return place

    async def get_by_id(self, place_id: uuid.UUID) -> Place | None:
        """Return a place by primary key, or None."""
        result = await self.db.execute(select(Place).where(Place.id == place_id))
        return result.scalar_one_or_none()

    async def get_by_creator(self, user_id: uuid.UUID) -> list[Place]:
        """Return all places added by a specific user."""
        result = await self.db.execute(
            select(Place).where(Place.created_by_id == user_id).order_by(Place.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_nearby(
        self,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        min_safety_score: float | None = None,
        tourism_type: TourismType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return places within radius_km of (lat, lng) ordered by distance.

        Uses PostGIS ST_DWithin on geography so the radius is in metres and
        the spatial index fires correctly.

        Returns a list of dicts with all place columns plus ``distance_km``.
        """
        point = func.ST_MakePoint(lng, lat)
        # Cast to geography so the comparison is in metres and the index fires.
        place_geo = cast(Place.location, Geography)
        query_geo = cast(func.ST_SetSRID(point, 4326), Geography)

        stmt = (
            select(
                Place,
                func.ST_Distance(place_geo, query_geo).label("distance_m"),
            )
            .where(ST_DWithin(place_geo, query_geo, radius_km * 1000))
            .order_by("distance_m")
            .limit(limit)
            .offset(offset)
        )

        if min_safety_score is not None:
            stmt = stmt.where(Place.average_safety_score >= min_safety_score)

        if tourism_type is not None:
            stmt = stmt.where(Place.dominant_tourism_type == tourism_type)

        rows = await self.db.execute(stmt)
        results = []
        for place, distance_m in rows:
            results.append({"place": place, "distance_km": round(distance_m / 1000, 2)})
        return results

    async def refresh_aggregates(self, place_id: uuid.UUID) -> None:
        """Recompute and persist denormalised aggregate columns for a place.

        Called after every new review. Runs two SQL queries:
        1. Recalculate average_safety_score, total_reviews, last_review_at.
        2. Recalculate dominant_tourism_type (mode).
        """
        from src.models.reviews import Review  # local import avoids circular dep

        agg = await self.db.execute(
            select(
                func.avg(Review.safety_score).label("avg_score"),
                func.count(Review.id).label("total"),
                func.max(Review.created_at).label("last_at"),
            ).where(Review.place_id == place_id)
        )
        row = agg.one()

        # Dominant tourism type: the most frequently used category
        mode_result = await self.db.execute(
            select(Review.tourism_type)
            .where(Review.place_id == place_id)
            .group_by(Review.tourism_type)
            .order_by(func.count(Review.id).desc())
            .limit(1)
        )
        dominant = mode_result.scalar_one_or_none()

        await self.db.execute(
            update(Place)
            .where(Place.id == place_id)
            .values(
                average_safety_score=float(row.avg_score or 0),
                total_reviews=int(row.total or 0),
                last_review_at=row.last_at,
                dominant_tourism_type=dominant,
            )
        )
        await self.db.commit()
