import strawberry

@strawberry.type
class OTPSetupType:
    otp_base32: str
    otp_auth_url: str
    qr_code: str

@strawberry.input
class OTPVerifyInput:
    otp_code: str

@strawberry.input
class OTPDisableInput:
    password: str
