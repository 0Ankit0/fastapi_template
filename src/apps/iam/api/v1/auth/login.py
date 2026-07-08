from fastapi import APIRouter, Depends, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.apps.iam.models.user import User
from src.apps.iam.schemas.otp import OtpRequiredResponse
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import LoginRequest
from src.apps.iam.services.auth import auth_service
from src.apps.iam.services.tokens import token_service
from src.core.config import settings
from src.core.dependencies import DB, get_current_user
from src.core.exceptions import AppError
from src.core.schemas import ApiSuccessResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login/", response_model=ApiSuccessResponse[Token] | ApiSuccessResponse[OtpRequiredResponse])
@limiter.limit(lambda: settings.RATE_LIMIT_LOGIN)
async def login_access_token(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: DB,
    set_cookie: bool = False,
) -> ApiSuccessResponse[Token] | ApiSuccessResponse[OtpRequiredResponse]:
    try:
        return await auth_service.login(
            db,
            request=request,
            response=response,
            login_data=login_data,
            set_cookie=set_cookie,
        )
    except AppError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


@router.post("/logout/")
async def logout(
    request: Request,
    response: Response,
    db: DB,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    return await token_service.logout(
        db,
        request=request,
        response=response,
        current_user=current_user,
    )
