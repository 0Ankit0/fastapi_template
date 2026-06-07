import casbin
from casbin_sqlalchemy_adapter import Adapter
from core.config import settings

DATABASE_URL = settings.DATABASE_URL

adapter = Adapter(DATABASE_URL)

enforcer = casbin.Enforcer(
    "model.conf",
    adapter
)

enforcer.load_policy()

enforcer.enable_auto_save(True)