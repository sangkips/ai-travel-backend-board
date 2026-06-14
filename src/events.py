"""Lightweight Valkey (Redis) pub/sub used by GraphQL subscriptions.

Mutations ``publish`` JSON payloads to per-entity channels; subscription
resolvers ``subscribe`` to a channel and receive an async stream of payloads.
Because publisher and subscriber talk through the Valkey server, this works
across separate requests/connections and (eventually) across processes.

TODO(scaling): This uses Valkey pub/sub, which is fire-and-forget — events
only reach subscribers connected at publish time, there is no replay/history,
and delivery isn't guaranteed across a sharded/multi-node Valkey. Fine for a
single-instance MVP. For guaranteed delivery and horizontal scaling, migrate
to Redis Streams (consumer groups + acks) or a dedicated broker.
"""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis


def review_added_channel(creator_id: uuid.UUID | str) -> str:
    """Channel a place creator listens on for new reviews of their places."""
    return f"events:review_added:{creator_id}"


def place_security_channel(place_id: uuid.UUID | str) -> str:
    """Channel watchers of a place listen on for safety-label changes."""
    return f"events:place_security:{place_id}"


async def publish(valkey: redis.Redis, channel: str, payload: dict[str, Any]) -> None:
    """Publish a JSON-serialisable payload to a channel."""
    await valkey.publish(channel, json.dumps(payload, default=str))


async def subscribe(valkey: redis.Redis, channel: str) -> AsyncIterator[dict[str, Any]]:
    """Yield decoded payloads published to ``channel`` until cancelled.

    The Valkey client is created with ``decode_responses=True``, so message
    data arrives as ``str`` and is parsed back into a dict.
    """
    pubsub = valkey.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
