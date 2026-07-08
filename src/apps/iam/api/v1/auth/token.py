from fastapi import APIRouter, Body, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.apps.iam.schemas.token import Token
from src.apps.iam.services.tokens import token_service
from src.core.schemas import ApiSuccessResponse
from src.core.dependencies import DB

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

TOKEN_REFRESH_RATE_LIMIT = limiter.limit("5/minute")


@router.post("/refresh/", response_model=ApiSuccessResponse[Token] | ApiSuccessResponse[None])
@TOKEN_REFRESH_RATE_LIMIT
async def refresh_token(
    response: Response,
    request: Request,
    db: DB,
    set_cookie: bool = False,
    refresh_token: str | None = Body(None, embed=True),
) -> ApiSuccessResponse[Token] | ApiSuccessResponse[None]:
    return await token_service.refresh_token(
        db,
        response=response,
        request=request,
        refresh_token=refresh_token,
        set_cookie=set_cookie,
    )
