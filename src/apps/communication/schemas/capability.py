from src.core.schemas import BaseSchema

class CapabilitySummary(BaseSchema):
    active_providers: dict[str, str | None]