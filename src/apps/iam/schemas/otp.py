from typing import Optional
from src.core.schemas import BaseSchema

class OtpRequiredResponse(BaseSchema):
    requires_otp: bool = True
    temp_token: str

class OtpEnableResponse(BaseSchema):
    otp_base32: str
    auth_uri: str
    qr_code: str 