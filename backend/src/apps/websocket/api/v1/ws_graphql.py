"""GraphQL schema for WebSocket management helpers.

This exposes the same information that used to be available via the REST
endpoints under `/ws/` (stats + online checks), but via a GraphQL API.
"""

from typing import List

import strawberry
from strawberry.scalars import JSON
from fastapi import Depends
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from src.apps.iam.api.deps import get_current_user
from src.apps.iam.models.user import User
from src.apps.websocket.manager import manager


@strawberry.type
class WSStats:
    total_connections: int
    rooms: JSON
    users_online: List[int]


async def get_graphql_context(current_user: User = Depends(get_current_user)) -> dict:
    """Expose FastAPI dependencies to Strawberry resolvers."""
    return {"current_user": current_user}


@strawberry.type
class Query:
    @strawberry.field
    async def ws_stats(self, info: Info) -> WSStats:
        """Return current active WebSocket connection statistics."""
        # Ensure user is authenticated (get_current_user dependency will raise otherwise)
        _ = info.context["current_user"]
        return WSStats(
            total_connections=manager.total_connections,
            rooms=manager.rooms_stats,
            users_online=manager.users_online,
        )

    @strawberry.field
    async def ws_is_online(self, info: Info, user_id: int) -> bool:
        """Return whether a given user is currently connected via WebSocket."""
        _ = info.context["current_user"]
        return manager.is_online(user_id)


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema, context_getter=get_graphql_context)
