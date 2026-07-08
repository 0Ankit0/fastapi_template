from fastapi import APIRouter, Depends, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.apps.iam.schemas.otp import OtpEnableResponse
from src.apps.iam.models.user import User
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import DisableOTPRequest, VerifyOTPRequest
from src.apps.iam.services.auth import auth_service
from src.core.dependencies import DB, get_current_user
from src.core.schemas import ApiSuccessResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

OTP_RATE_LIMIT = limiter.limit("1/second")


@router.post("/otp/enable/", response_model=ApiSuccessResponse[OtpEnableResponse])
@OTP_RATE_LIMIT
async def enable_otp(
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[OtpEnableResponse]:
    return await auth_service.enable_otp(db, current_user=current_user)


@router.post("/otp/verify/", response_model=ApiSuccessResponse[None])
@OTP_RATE_LIMIT
async def verify_otp(
    otp_data: VerifyOTPRequest,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[None]:
    return await auth_service.verify_otp(
        db,
        otp_data=otp_data,
        current_user=current_user,
    )


@router.post("/otp/disable/", response_model=ApiSuccessResponse[None])
@OTP_RATE_LIMIT
async def disable_otp(
    otp_data: DisableOTPRequest,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[None]:
    return await auth_service.disable_otp(
        db,
        otp_data=otp_data,
        current_user=current_user,
    )


@router.post("/otp/validate/", response_model=ApiSuccessResponse[Token] | ApiSuccessResponse[None])
@OTP_RATE_LIMIT
async def validate_otp_login(
    otp_data: VerifyOTPRequest,
    request: Request,
    response: Response,
    db: DB,
    set_cookie: bool = False,
) -> ApiSuccessResponse[Token] | ApiSuccessResponse[None]:
    return await auth_service.validate_otp_login(
        db,
        request=request,
        response=response,
        otp_data=otp_data,
        set_cookie=set_cookie,
    )
