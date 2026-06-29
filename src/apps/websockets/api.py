import logging
from uuid import uuid4
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from src.core.schemas import ApiSuccessResponse
from src.core.types import HashId
from src.apps.websockets.manager import manager
from src.apps.websockets.schemas import Connection
from src.apps.websockets.auth import get_websocket_user
from src.apps.iam.services.policy_service import PolicyService 
from src.core.dependencies import get_db
from src.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ws", tags=["WebSockets"])


@router.websocket("/{org_slug}/connect")
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
        
        await manager.connect(connection)
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

@router.post("/test_user/{user_id}",response_model=ApiSuccessResponse[dict] | ApiSuccessResponse[None])
async def send_to_user(user_id: HashId):
    payload = {
        "type": "test",
        "message": f"Hello user {user_id}",
    }

    success = await manager.send_to_user(user_id, payload)
    if not success:
        return ApiSuccessResponse(
            message=f"Failed to send message to user {user_id}",
            data= None
        )

    return ApiSuccessResponse(
        message=f"Message sent to user {user_id}",
        data={
            "user_id": user_id,
            "payload": payload
        },
    )