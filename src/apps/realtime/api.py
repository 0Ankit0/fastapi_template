from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Path, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from src.core.schemas import ApiSuccessResponse
from src.core.types import HashId
from src.apps.realtime.manager import manager
from src.apps.realtime.schemas import Connection, RealtimeEvent, SSEConnection
from src.apps.realtime.auth import get_websocket_user
from src.apps.iam.services.policy_service import PolicyService 
from src.core.dependencies import CurrentUser, get_db
from src.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
websocket_router = APIRouter(prefix="/api/v1/ws", tags=["WebSockets"])
sse_router = APIRouter(prefix="/api/v1/sse", tags=["Server-Sent Events"])
router = websocket_router


def _format_sse(event: RealtimeEvent) -> str:
    return (
        f"event: {event.event}\n"
        f"data: {json.dumps(event.data, default=str)}\n"
        f"id: {event.id or ''}\n"
        f"retry: {event.retry or 3000}\n\n"
    )


@websocket_router.websocket("/{org_slug}/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    org_slug: str,
    db = Depends(get_db)
):
    # Accept the handshake first to allow communication/error codes
    await websocket.accept()
    
    connection_id = str(uuid4())
    authenticated = False
    
    try:
        # 1. Authenticate the user
        user = await get_websocket_user(websocket=websocket, db=db)
        
        # 2. Utilize PolicyService to verify organization membership
        if not PolicyService.is_org_member(user=user, org_slug=org_slug):
            logger.warning(
                f"User {user.id} denied WS access to org '{org_slug}' (Failed policy check)"
            )
            await websocket.close(code=1008)  # 1008: Policy Violation
            return

        # 3. Create connection schema and register with manager
        connection = Connection(
            connection_id=connection_id,
            user_id=user.id,
            organization_slug=org_slug,
            websocket=websocket
        )
        
        await manager.connect_websocket(connection)
        authenticated = True
        logger.info(f"User {user.id} authorized and connected to org '{org_slug}' ({connection_id})")
        
        # 4. Keep connection alive
        while True:
            await websocket.receive_text()
            
    except AuthenticationError:
        logger.warning(f"WebSocket connection rejected: Unauthenticated for /ws/{org_slug}/connect")
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: {connection_id}")
        
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket lifecycle for org {org_slug}: {e}")
        
    finally:
        # 5. Always clean up local memory if the connection was successfully registered
        if authenticated:
            manager.disconnect(connection_id)

@websocket_router.post(
    "/test_user/{user_id}",
    response_model=ApiSuccessResponse[dict[str, Any]],
    summary="Send websocket test event",
    description="Broadcasts a small test payload to every active websocket and SSE connection for the target user.",
)
async def send_to_user(
    user_id: Annotated[HashId, Path(description="Target user identifier")],
):
    payload = {
        "event": "test.message",
        "message": f"Hello user {user_id}",
    }

    delivered = await manager.send_to_user(user_id, payload)

    return ApiSuccessResponse(
        message=f"Message sent to user {user_id}",
        data={
            "user_id": user_id,
            "delivered": delivered,
            "payload": payload,
        },
    )


@sse_router.get(
    "/{org_slug}/connect",
    summary="Open SSE stream",
    description="Opens a server-sent events stream for the authenticated user and streams real-time notifications.",
    response_class=StreamingResponse,
)
async def sse_endpoint(
    request: Request,
    org_slug: Annotated[str, Path(description="Organization slug to stream for")],
    current_user: CurrentUser,
):
    if not PolicyService.is_org_member(user=current_user, org_slug=org_slug):
        raise AuthenticationError(message="Not authorized for this organization")

    connection_id = str(uuid4())
    connection = SSEConnection(
        connection_id=connection_id,
        user_id=current_user.id,
        organization_slug=org_slug,
    )

    await manager.connect_sse(connection)

    async def event_stream():
        try:
            yield _format_sse(
                RealtimeEvent(
                    event="connected",
                    data={
                        "connection_id": connection_id,
                        "user_id": current_user.id,
                        "organization_slug": org_slug,
                        "transport": "sse",
                    },
                    id=connection_id,
                )
            )

            while True:
                if await request.is_disconnected():
                    break

                try:
                    payload = await asyncio.wait_for(connection.queue.get(), timeout=15)
                    yield _format_sse(
                        RealtimeEvent(
                            event=str(payload.get("event", "message")),
                            data=dict(payload),
                            id=str(payload.get("id") or connection_id),
                        )
                    )
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            manager.disconnect(connection_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@sse_router.post(
    "/test_user/{user_id}",
    response_model=ApiSuccessResponse[dict[str, Any]],
    summary="Send SSE test event",
    description="Broadcasts a small test payload to every active websocket and SSE connection for the target user.",
)
async def send_sse_to_user(
    user_id: Annotated[HashId, Path(description="Target user identifier")],
):
    payload = {
        "event": "test.sse",
        "message": f"Hello user {user_id}",
    }

    delivered = await manager.send_to_user(user_id, payload)

    return ApiSuccessResponse(
        message=f"SSE message sent to user {user_id}",
        data={
            "user_id": user_id,
            "delivered": delivered,
            "payload": payload,
        },
    )