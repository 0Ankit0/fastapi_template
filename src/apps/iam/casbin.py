import casbin
from casbin_sqlalchemy_adapter import Adapter
from src.core.config import settings
from pathlib import Path

model_path = Path(__file__).parent / "model.conf"

DATABASE_URL = settings.DATABASE_URL

adapter = Adapter(DATABASE_URL)

enforcer = casbin.Enforcer(
    str(model_path),
    adapter
)

enforcer.load_policy()

enforcer.enable_auto_save(True)