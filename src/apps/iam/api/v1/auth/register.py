from fastapi import APIRouter, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import EmailVerificationRequest, UserCreate
from src.apps.iam.services.auth import auth_service
from src.core.config import settings
from src.core.dependencies import DB
from src.core.exceptions import AppError
from src.core.schemas import ApiSuccessResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

SIGNUP_RATE_LIMIT = limiter.limit(lambda: settings.RATE_LIMIT_SIGNUP)


@router.post("/signup/", response_model=ApiSuccessResponse[Token])
@SIGNUP_RATE_LIMIT
async def signup(
    request: Request,
    response: Response,
    login_data: UserCreate,
    db: DB,
    set_cookie: bool = False,
) -> ApiSuccessResponse[Token]:
    try:
        return await auth_service.signup(
            db,
            request=request,
            response=response,
            signup_data=login_data,
            set_cookie=set_cookie,
        )
    except AppError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


@router.post("/verify-email/", response_model=ApiSuccessResponse[None])
@SIGNUP_RATE_LIMIT
async def verify_email(
    t: str,
    request: Request,
    db: DB,
) -> ApiSuccessResponse[None]:
    return await auth_service.verify_email(db, token=t)


@router.post("/resend-verification/", response_model=ApiSuccessResponse[None])
@SIGNUP_RATE_LIMIT
async def resend_verification_email(
    data: EmailVerificationRequest,
    db: DB,
    request: Request,
) -> ApiSuccessResponse[None]:
    return await auth_service.resend_verification_email(db, data=data)
