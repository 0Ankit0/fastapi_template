
# GraphQL OTP/2FA Management
from fastapi import APIRouter
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.iam.models.user import User
from src.apps.iam.api.deps import get_db, get_current_user
from src.apps.core.cache import RedisCache
from src.apps.core import security
from src.apps.core.config import settings
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import AuthEvents
from sqlmodel import select
import pyotp
import qrcode
from io import BytesIO
import base64
from graphql import GraphQLError

from src.apps.iam.schemas.graphql_otp import OTPDisableInput, OTPSetupType, OTPVerifyInput

router = APIRouter()

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def enable_otp(self, info: Info) -> OTPSetupType:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        if current_user.otp_enabled:
            raise GraphQLError("OTP is already enabled")
        otp_base32 = pyotp.random_base32()
        otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
            name=current_user.email,
            issuer_name=settings.PROJECT_NAME
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        pill_img = img.get_image()
        buffered = BytesIO()
        pill_img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        current_user.otp_base32 = otp_base32
        current_user.otp_auth_url = otp_auth_url
        current_user.otp_verified = False
        await db.commit()
        return OTPSetupType(
            otp_base32=otp_base32,
            otp_auth_url=otp_auth_url,
            qr_code=f"data:image/png;base64,{qr_code_base64}"
        )

    @strawberry.mutation
    async def verify_otp(self, info: Info, input: OTPVerifyInput) -> bool:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        analytics: AnalyticsService = info.context.get("analytics")
        if not current_user.otp_base32:
            raise GraphQLError("OTP not set up. Please enable OTP first")
        totp = pyotp.TOTP(current_user.otp_base32)
        if not totp.verify(input.otp_code):
            raise GraphQLError("Invalid OTP code")
        current_user.otp_enabled = True
        current_user.otp_verified = True
        await db.commit()
        await RedisCache.delete(f"user:profile:{current_user.id}")
        if analytics:
            await analytics.capture(str(current_user.id), AuthEvents.OTP_ENABLED)
        return True

    @strawberry.mutation
    async def disable_otp(self, info: Info, input: OTPDisableInput) -> bool:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        analytics: AnalyticsService = info.context.get("analytics")
        if not current_user.otp_enabled:
            raise GraphQLError("OTP is not enabled")
        if not security.verify_password(input.password, current_user.hashed_password):
            raise GraphQLError("Incorrect password")
        current_user.otp_enabled = False
        current_user.otp_verified = False
        current_user.otp_base32 = ""
        current_user.otp_auth_url = ""
        await db.commit()
        await RedisCache.delete(f"user:profile:{current_user.id}")
        if analytics:
            await analytics.capture(str(current_user.id), AuthEvents.OTP_DISABLED)
        return True

@strawberry.type
class Query:
    """Minimal query type required by Strawberry (unused)."""

    @strawberry.field
    def ping(self) -> str:
        return "pong"

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema)
