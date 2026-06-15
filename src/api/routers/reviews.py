"""Reviews router – submit reviews and cast votes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_current_user, get_review_service, get_vote_service
from src.schemas.reviews import CreateReviewInput, ReviewOut, VoteInput
from src.services.review_service import ReviewService
from src.services.vote_service import VoteService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post(
    "",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a safety review for a place",
)
async def create_review(
    body: CreateReviewInput,
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    """Write a review.

    - Safety score: 1 (avoid) – 5 (very safe).
    - The reviewer's role is snapshotted automatically from the JWT.
    - The place creator is notified if they didn't write this review.
    """
    try:
        return await service.create_review(
            data=body,
            author_id=current_user["user_id"],
            author_role=current_user["role"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "",
    response_model=list[ReviewOut],
    summary="List reviews for a place",
)
async def list_reviews(
    place_id: uuid.UUID = Query(...),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> list[ReviewOut]:
    """Return reviews for a place, newest first."""
    return await service.get_place_reviews(place_id, limit=limit, offset=offset)


@router.get(
    "/mine",
    response_model=list[ReviewOut],
    summary="List the authenticated user's own reviews",
)
async def my_reviews(
    current_user: dict = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> list[ReviewOut]:
    """Return all reviews written by the current user."""
    return await service.get_my_reviews(current_user["user_id"])


@router.post(
    "/{review_id}/vote",
    response_model=ReviewOut,
    summary="Upvote or downvote a review",
)
async def vote_review(
    review_id: uuid.UUID,
    body: VoteInput,
    current_user: dict = Depends(get_current_user),
    service: VoteService = Depends(get_vote_service),
) -> ReviewOut:
    """Cast or change a vote on a review. Self-voting is not allowed."""
    try:
        return await service.cast_vote(
            review_id=review_id,
            voter_id=current_user["user_id"],
            data=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
