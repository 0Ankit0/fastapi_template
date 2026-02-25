from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from app.api import deps
from app.models.user import User
from app.db import session
from sqlmodel import select
from app.models.tenant import TenantMembership

# We use valid dependencies for WebSocket
# But for simplicity, we'll do manual auth inside endpoint or use Query param
from app.core import security
from jose import jwt, JWTError
from app.core.config import settings
from app.db.session import SessionLocal # We typically need sync or async generator manual usage

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Map user_id to list of WebSockets (user can have multiple tabs)
        self.active_connections: list[WebSocket] = []
        self.user_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int | None = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int | None = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    async def send_to_user(self, user_id: int, message: str):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    # Clean up dead connection?
                    pass

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(None),
) -> User | None:
    # Check query param or cookie
    if not token:
        token = websocket.cookies.get("access_token")
    
    if not token:
        return None
        
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            return None
    except (JWTError, Exception):
        return None
        
    # We need DB session. 
    # For async websocket, we can use `async with AsyncSession(...)` if we have factory
    # Or use `deps.get_db` generator manually?
    # Better to just trust token for now or use `db` dependency if possible in WebSocket (it is).
    # But for now stub user id from token.
    # Return User object if we fetch it, or just ID.
    # Let's fetch user.
    async with session.session_factory() as db:
        result = await db.execute(select(User).where(User.id == int(token_data)))
        user = result.scalars().first()
        return user

@router.websocket("/notifications/")
async def websocket_endpoint(
    websocket: WebSocket,
    # token: str = Query(None) # Can be passed here
):
    # Authenticate
    # Note: `Depends` in websocket is supported.
    # user = await get_current_user_ws(websocket, token)
    # Re-parse params manually to be safe or use `Depends`.
    
    # Try manual extraction for simplicity in this template
    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")
    user = None
    if token:
         try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                # Stub user object or fetch
                # For basic auth check, we assume valid if decoding works
                 pass
         except:
             pass
    
    user_id = None
    if token:
         try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
            token_sub = payload.get("sub")
            if token_sub:
                user_id = int(token_sub)
         except:
             pass
    
    if not token: # Strict check
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return # Close doesn't stop execution immediately?
    
    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong or messages
            # mimic Django consumer: {"type": "ping"} -> {"type": "pong"}
            import json
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)

@router.websocket("/tenant/{tenant_id}/")
async def websocket_tenant(
    websocket: WebSocket,
    tenant_id: int,
):
    # Auth check...
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # ...
    except WebSocketDisconnect:
        manager.disconnect(websocket)
