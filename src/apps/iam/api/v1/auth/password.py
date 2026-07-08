from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.apps.iam.models.user import User
from src.apps.iam.schemas.user import ChangePasswordRequest, ResetPasswordConfirm, ResetPasswordRequest
from src.apps.iam.services.auth import auth_service
from src.core.config import settings
from src.core.dependencies import DB, get_current_user
from src.core.schemas import ApiSuccessResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

PASSWORD_RESET_RATE_LIMIT = limiter.limit(lambda: settings.RATE_LIMIT_PASSWORD_RESET)


@router.post("/password-reset-request/", response_model=ApiSuccessResponse[None])
@PASSWORD_RESET_RATE_LIMIT
async def request_password_reset(
    request: Request,
    reset_data: ResetPasswordRequest,
    db: DB,
) -> ApiSuccessResponse[None]:
    return await auth_service.request_password_reset(db, reset_data=reset_data)


@router.post("/password-reset-confirm/", response_model=ApiSuccessResponse[None])
@PASSWORD_RESET_RATE_LIMIT
async def confirm_password_reset(
    body: ResetPasswordConfirm,
    db: DB,
    request: Request,
) -> ApiSuccessResponse[None]:
    return await auth_service.confirm_password_reset(db, body=body)


@router.post("/change-password/", response_model=ApiSuccessResponse[None])
@PASSWORD_RESET_RATE_LIMIT
async def change_password(
    password_data: ChangePasswordRequest,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[None]:
    return await auth_service.change_password(
        db,
        password_data=password_data,
        current_user=current_user,
    )
