from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pyotp
import qrcode
from fastapi import HTTPException, Request, Response

from src.apps.iam.models.user import User
from src.apps.iam.repositories import iam_repository
from src.apps.iam.schemas.otp import OtpEnableResponse, OtpRequiredResponse
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import (
    ChangePasswordRequest,
    DisableOTPRequest,
    EmailVerificationRequest,
    LoginRequest,
    ResetPasswordConfirm,
    ResetPasswordRequest,
    UserCreate,
    VerifyOTPRequest,
)
from src.apps.iam.services.email import AuthEmailService
from src.apps.iam.services.users import user_service
from src.apps.iam.utils.ip_access import get_client_ip, revoke_tokens_for_ip
from src.core import security
from src.core.cache import RedisCache
from src.core.config import settings
from src.core.cookies import set_auth_cookies
from src.core.enums import UserStatus
from src.core.exceptions import AuthorizationError, RateLimitError, ValidationError
from src.core.schemas import ApiSuccessResponse
from src.core.security import TokenType


class AuthService:
    async def login(
        self,
        db,
        *,
        request: Request,
        response: Response,
        login_data: LoginRequest,
        set_cookie: bool,
    ) -> ApiSuccessResponse[Token] | ApiSuccessResponse[OtpRequiredResponse]:
        """Authenticate user credentials and issue access/refresh tokens."""
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        user = await iam_repository.get_user_by_username(db, login_data.username)
        if not user:
            await iam_repository.create_login_attempt(
                db,
                user_id=None,
                ip_address=ip_address,
                attempted_username=login_data.username,
                user_agent=user_agent,
                success=False,
                failure_reason="User not found",
            )
            await iam_repository.commit(db)
            raise ValidationError(message="Invalid username or password")

        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_confirmed:
            raise AuthorizationError(message="Email verification required. Please check your inbox.")

        if settings.MAX_LOGIN_ATTEMPTS > 0 and settings.ACCOUNT_LOCKOUT_DURATION_MINUTES > 0:
            window_start = datetime.now() - timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
            failures = await iam_repository.get_login_failures(db, user_id=user.id, window_start=window_start)
            if len(failures) >= settings.MAX_LOGIN_ATTEMPTS:
                lockout_expires = failures[0].timestamp + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
                remaining_seconds = int((lockout_expires - datetime.now()).total_seconds())
                if remaining_seconds > 0:
                    remaining_minutes = (remaining_seconds + 59) // 60
                    raise RateLimitError(
                        message=f"Too many failed login attempts. Account locked for {remaining_minutes} more minutes."
                    )

        if not security.verify_password(login_data.password, user.password_hash):
            await iam_repository.create_login_attempt(
                db,
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=login_data.username,
                user_agent=user_agent,
                success=False,
                failure_reason="Incorrect password",
            )
            await iam_repository.commit(db)
            raise ValidationError(message="Invalid username or password")

        if user.status != UserStatus.ACTIVE:
            await iam_repository.create_login_attempt(
                db,
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=login_data.username,
                user_agent=user_agent,
                success=False,
                failure_reason="User account is inactive",
            )
            await iam_repository.commit(db)
            raise ValidationError(message="User account is inactive. Please contact support.")

        if user.otp_enabled and user.otp_verified:
            temp_token = security.create_temp_auth_token(user.id, login_data.organization)
            return ApiSuccessResponse[OtpRequiredResponse](
                data=OtpRequiredResponse(requires_otp=True, temp_token=temp_token),
                message="OTP verification required",
            )

        await iam_repository.create_login_attempt(
            db,
            user_id=user.id,
            ip_address=ip_address,
            attempted_username=login_data.username,
            user_agent=user_agent,
            success=True,
            failure_reason="",
        )

        access_token = security.create_access_token(
            user.id,
            login_data.organization,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = security.create_refresh_token(user.id, login_data.organization)

        access_payload = security.decode_token(access_token)
        refresh_payload = security.decode_token(refresh_token)

        await revoke_tokens_for_ip(db, user.id, ip_address)
        await iam_repository.create_token_tracking(
            db,
            user_id=user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(access_payload),
        )
        await iam_repository.create_token_tracking(
            db,
            user_id=user.id,
            token_jti=refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(refresh_payload),
        )
        await iam_repository.commit(db)

        if set_cookie:
            set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
            return ApiSuccessResponse[Token](
                data=Token(access="", refresh="", token_type=TokenType.BEARER.value),
                message="Logged in successfully",
            )

        return ApiSuccessResponse[Token](
            data=Token(access=access_token, refresh=refresh_token, token_type=TokenType.BEARER.value),
            message="Logged in successfully",
        )

    async def signup(
        self,
        db,
        *,
        request: Request,
        response: Response,
        signup_data: UserCreate,
        set_cookie: bool,
    ) -> ApiSuccessResponse[Token]:
        """Create a new user account and issue initial tokens."""
        existing_user = await iam_repository.get_user_by_username(db, signup_data.username)
        if existing_user:
            raise ValidationError(message="Username already exists")

        new_user = await iam_repository.create_user(
            db,
            username=signup_data.username,
            email=signup_data.email,
            password_hash=security.get_password_hash(signup_data.password),
        )
        await iam_repository.create_profile(
            db,
            user_id=new_user.id,
            first_name=signup_data.first_name or "",
            last_name=signup_data.last_name or "",
            phone=signup_data.phone or "",
        )
        await iam_repository.commit(db)

        await user_service.invalidate_user_listing_cache()
        await AuthEmailService.send_welcome_email(new_user)

        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        access_token = security.create_access_token(
            new_user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = security.create_refresh_token(new_user.id)

        access_payload = security.decode_token(access_token)
        refresh_payload = security.decode_token(refresh_token)

        await revoke_tokens_for_ip(db, new_user.id, ip_address)
        await iam_repository.create_token_tracking(
            db,
            user_id=new_user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(access_payload),
        )
        await iam_repository.create_token_tracking(
            db,
            user_id=new_user.id,
            token_jti=refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(refresh_payload),
        )
        await iam_repository.commit(db)

        if set_cookie:
            set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
            return ApiSuccessResponse[Token](
                message="Account created successfully",
                data=Token(access="", refresh="", token_type=TokenType.BEARER.value),
            )

        return ApiSuccessResponse[Token](
            message="Account created successfully",
            data=Token(access=access_token, refresh=refresh_token, token_type=TokenType.BEARER.value),
        )

    async def verify_email(self, db, *, token: str) -> ApiSuccessResponse[None]:
        """Validate an email verification token and confirm the user email."""
        try:
            token_data = security.verify_secure_url_token(token)
        except Exception:
            raise ValidationError(message="Invalid or expired verification token")

        user_id = token_data.get("user_id")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")
        if not all([user_id, paseto_token]) or purpose != "email_verification":
            raise ValidationError(message="Invalid token data")

        if not isinstance(paseto_token, str):
            raise ValidationError(message="Invalid token format")
        if not isinstance(user_id, (int, str)):
            raise ValidationError(message="Invalid user ID in token")

        payload = security.verify_token(paseto_token, token_type=TokenType.EMAIL_VERIFICATION)
        token_jti = payload.get("jti")
        if str(payload.get("sub")) != str(user_id):
            raise ValidationError(message="Token data mismatch - possible tampering detected")

        if token_jti and await iam_repository.get_used_token_by_jti(db, token_jti):
            raise ValidationError(message="This verification link has already been used")

        user = await iam_repository.get_user_by_id(db, int(user_id))
        if not user:
            raise ValidationError(message="User not found for this token")

        user.is_confirmed = True
        if token_jti:
            await iam_repository.mark_used_token(
                db,
                token_jti=token_jti,
                user_id=int(user_id),
                purpose="email_verification",
            )

        await iam_repository.commit(db)
        await user_service.invalidate_user_cache(int(user_id))
        return ApiSuccessResponse[None](message="Email verified successfully")

    async def resend_verification_email(self, db, *, data: EmailVerificationRequest) -> ApiSuccessResponse[None]:
        """Queue a new email verification message when the user exists."""
        user = await iam_repository.get_user_by_email(db, data.email)
        if user:
            verification_token = security.create_email_verification_token(user.id)
            await AuthEmailService.send_verification_email(user, verification_token)
        return ApiSuccessResponse[None](
            message="If an account with that email exists, a verification email has been sent"
        )

    async def request_password_reset(self, db, *, reset_data: ResetPasswordRequest) -> ApiSuccessResponse[None]:
        """Queue a password reset email without revealing account existence."""
        user = await iam_repository.get_user_by_email(db, str(reset_data.email))
        if user:
            reset_token = security.create_password_reset_token(user.id)
            await AuthEmailService.send_password_reset_email(user, reset_token)
        return ApiSuccessResponse[None](message="If the email exists, a password reset link has been sent")

    async def confirm_password_reset(self, db, *, body: ResetPasswordConfirm) -> ApiSuccessResponse[None]:
        """Apply a password reset token and rotate active sessions."""
        try:
            token_data = security.verify_secure_url_token(body.token)
        except Exception:
            raise ValidationError("Invalid or expired reset token")

        user_id = token_data.get("user_id")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")
        if not all([user_id, paseto_token]) or purpose != "password_reset":
            raise ValidationError("Invalid reset token data")

        if not isinstance(paseto_token, str):
            raise ValidationError("Invalid token format")
        if not isinstance(user_id, (int, str)):
            raise ValidationError("Invalid user ID in token")

        payload = security.verify_token(paseto_token, token_type=TokenType.PASSWORD_RESET)
        token_jti = payload.get("jti")
        if str(payload.get("sub")) != str(user_id):
            raise ValidationError("Token data mismatch - possible tampering detected")

        if token_jti and await iam_repository.get_used_token_by_jti(db, token_jti):
            raise ValidationError("This password reset link has already been used")

        user = await iam_repository.get_user_by_id(db, int(user_id))
        if not user:
            raise ValidationError("User not found for this reset token")

        user.password_hash = security.get_password_hash(body.new_password)
        if token_jti:
            await iam_repository.mark_used_token(
                db,
                token_jti=token_jti,
                user_id=int(user_id),
                purpose="password_reset",
            )

        tokens = await iam_repository.list_active_tokens(db, user.id)
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Password reset"

        await iam_repository.commit(db)
        await user_service.invalidate_user_cache(int(user_id))
        await RedisCache.clear_pattern(f"tokens:active:{user_id}:*")
        return ApiSuccessResponse[None](message="Password has been reset successfully")

    async def change_password(
        self,
        db,
        *,
        password_data: ChangePasswordRequest,
        current_user: User,
    ) -> ApiSuccessResponse[None]:
        """Change a logged-in user's password and revoke active sessions."""
        if not security.verify_password(password_data.current_password, current_user.password_hash):
            raise ValidationError("Current password is incorrect")

        current_user.password_hash = security.get_password_hash(password_data.new_password)
        tokens = await iam_repository.list_active_tokens(db, current_user.id)
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Password changed"

        await iam_repository.commit(db)
        await user_service.invalidate_user_cache(current_user.id)
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
        return ApiSuccessResponse[None](message="Password changed successfully")

    async def enable_otp(self, db, *, current_user: User) -> ApiSuccessResponse[OtpEnableResponse]:
        """Start OTP setup by generating secret, URI, and QR payload."""
        if current_user.otp_enabled:
            raise ValidationError("OTP is already enabled for this account")

        otp_base32 = pyotp.random_base32()
        otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
            name=current_user.email,
            issuer_name=settings.APP_INSTANCE_NAME,
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        img.get_image().save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

        current_user.otp_base32 = otp_base32
        current_user.otp_auth_url = otp_auth_url
        current_user.otp_verified = False
        await iam_repository.commit(db)

        return ApiSuccessResponse[OtpEnableResponse](
            message="OTP setup initiated. Please verify OTP code to enable.",
            data=OtpEnableResponse(
                otp_base32=otp_base32,
                auth_uri=otp_auth_url,
                qr_code=f"data:image/png;base64,{qr_code_base64}",
            ),
        )

    async def verify_otp(
        self,
        db,
        *,
        otp_data: VerifyOTPRequest,
        current_user: User,
    ) -> ApiSuccessResponse[None]:
        """Validate OTP code and enable OTP on the account."""
        if not current_user.otp_base32:
            raise ValidationError("OTP setup not initiated for this account")

        if not pyotp.TOTP(current_user.otp_base32).verify(otp_data.otp_code):
            raise ValidationError("Invalid OTP code")

        current_user.otp_enabled = True
        current_user.otp_verified = True
        await iam_repository.commit(db)
        await user_service.invalidate_user_cache(current_user.id)
        return ApiSuccessResponse[None](message="OTP verified and enabled successfully")

    async def disable_otp(
        self,
        db,
        *,
        otp_data: DisableOTPRequest,
        current_user: User,
    ) -> ApiSuccessResponse[None]:
        """Disable OTP after verifying the user's password."""
        if not current_user.otp_enabled:
            raise ValidationError("OTP is not enabled")

        if not security.verify_password(otp_data.password, current_user.password_hash):
            raise ValidationError("Incorrect password")

        current_user.otp_enabled = False
        current_user.otp_verified = False
        current_user.otp_base32 = ""
        current_user.otp_auth_url = ""
        await iam_repository.commit(db)
        await user_service.invalidate_user_cache(current_user.id)
        return ApiSuccessResponse[None](message="OTP disabled successfully")

    async def validate_otp_login(
        self,
        db,
        *,
        request: Request,
        response: Response,
        otp_data: VerifyOTPRequest,
        set_cookie: bool,
    ) -> ApiSuccessResponse[Token] | ApiSuccessResponse[None]:
        """Validate OTP temp token flow and issue full auth tokens."""
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        if not otp_data.temp_token:
            raise AuthorizationError("Temporary token required for OTP validation")

        try:
            payload = security.verify_token(otp_data.temp_token, token_type=TokenType.TEMP_AUTH)
            user_id = payload.get("sub")
            if not user_id:
                raise AuthorizationError("Invalid temporary token")
        except Exception:
            raise AuthorizationError(message="Invalid temporary token")

        user = await iam_repository.get_user_by_id(db, int(user_id))
        if not user:
            raise AuthorizationError("Invalid temporary token")

        if settings.MAX_LOGIN_ATTEMPTS > 0 and settings.ACCOUNT_LOCKOUT_DURATION_MINUTES > 0:
            window_start = datetime.now() - timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
            failures = await iam_repository.get_login_failures(db, user_id=user.id, window_start=window_start)
            if len(failures) >= settings.MAX_LOGIN_ATTEMPTS:
                lockout_expires = failures[0].timestamp + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
                remaining_seconds = int((lockout_expires - datetime.now()).total_seconds())
                if remaining_seconds > 0:
                    remaining_minutes = (remaining_seconds + 59) // 60
                    raise RateLimitError(
                        f"Account locked due to too many failed OTP attempts. Try again in {remaining_minutes} minute(s)."
                    )

        if not user.otp_enabled:
            raise ValidationError("OTP not enabled for this account")

        if not pyotp.TOTP(user.otp_base32).verify(otp_data.otp_code):
            await iam_repository.create_login_attempt(
                db,
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=user.username,
                user_agent=user_agent,
                success=False,
                failure_reason="Invalid OTP code",
            )
            await iam_repository.commit(db)
            raise ValidationError("Invalid OTP code")

        await iam_repository.create_login_attempt(
            db,
            user_id=user.id,
            ip_address=ip_address,
            attempted_username=user.username,
            user_agent=user_agent,
            success=True,
            failure_reason="",
        )

        access_token = security.create_access_token(
            user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = security.create_refresh_token(user.id)

        access_payload = security.decode_token(access_token)
        refresh_payload = security.decode_token(refresh_token)

        await revoke_tokens_for_ip(db, user.id, ip_address)
        await iam_repository.create_token_tracking(
            db,
            user_id=user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(access_payload),
        )
        await iam_repository.create_token_tracking(
            db,
            user_id=user.id,
            token_jti=refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(refresh_payload),
        )
        await iam_repository.commit(db)

        if set_cookie:
            set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
            return ApiSuccessResponse[Token](
                message="OTP validated successfully",
                data=Token(access="", refresh="", token_type=TokenType.BEARER.value),
            )

        return ApiSuccessResponse[Token](
            message="OTP validated successfully",
            data=Token(access=access_token, refresh=refresh_token, token_type=TokenType.BEARER.value),
        )


auth_service = AuthService()
