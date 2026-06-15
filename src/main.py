from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from src.api.routers.auth import router as auth_router
from src.api.routers.health import router as health_router
from src.api.routers.notifications import router as notifications_router
from src.api.routers.places import router as places_router
from src.api.routers.reviews import router as reviews_router
from src.graphql.context import get_graphql_context
from src.graphql.schema import schema as graphql_schema

app = FastAPI(
    title="SafeTrail – Travel Safety & Discovery",
    description=(
        "A role-aware travel review platform where safety is a first-class filter. "
        "Tourists, guides, and drivers leave reviews; place creators get notified."
    ),
    version="0.1.0",
)

# ── GraphQL (primary API for mobile clients) ─────────────────────────────────
graphql_app = GraphQLRouter(
    graphql_schema,
    graphql_ide="graphiql",
    context_getter=get_graphql_context,
)
app.include_router(graphql_app, prefix="/graphql")

# ── REST (escape hatch: auth, simple CRUD, admin tooling) ────────────────────
_V1 = "/api/v1"
app.include_router(health_router, prefix=_V1)
app.include_router(auth_router, prefix=_V1)
app.include_router(places_router, prefix=_V1)
app.include_router(reviews_router, prefix=_V1)
app.include_router(notifications_router, prefix=_V1)
