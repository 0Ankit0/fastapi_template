import logging
from fastapi import WebSocket
from src.core.config import settings
from src.core.exceptions import AuthenticationError
from src.core.dependencies import authenticate_token, DB
from src.apps.iam.models.user import User

logger = logging.getLogger(__name__)

async def get_websocket_user(
    websocket: WebSocket,
    db: DB,
) -> User:
    # Clean fallback check
    token = websocket.query_params.get("token") or websocket.cookies.get(
        settings.ACCESS_TOKEN_COOKIE_NAME
    )

    if not token:
        await websocket.close(code=1008)  # 1008: Policy Violation
        raise AuthenticationError(message="Not authenticated")

    try:
        return await authenticate_token(token=token, db=db)
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        # Explicitly close the socket before raising so the client gets a clear error code
        await websocket.close(code=1008)
        raise AuthenticationError(message="Invalid or expired token")