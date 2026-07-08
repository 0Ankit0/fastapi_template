import casbin
from casbin_sqlalchemy_adapter import Adapter
from src.core.config import settings
from pathlib import Path

model_path = Path(__file__).parent / "model.conf"

DATABASE_URL = settings.DATABASE_URL


class _DebugEnforcer:
    def enforce(self, *args, **kwargs):
        return True

    def add_policy(self, *args, **kwargs):
        return True

    def remove_policy(self, *args, **kwargs):
        return True

    def get_filtered_policy(self, *args, **kwargs):
        return []

    def add_grouping_policy(self, *args, **kwargs):
        return True

    def remove_grouping_policy(self, *args, **kwargs):
        return True

    def get_roles_for_user_in_domain(self, *args, **kwargs):
        return ["member"]

    def delete_roles_for_user_in_domain(self, *args, **kwargs):
        return True

    def get_filtered_grouping_policy(self, *args, **kwargs):
        return []

    def get_implicit_permissions_for_user(self, *args, **kwargs):
        return []

    def load_policy(self):
        return None

    def enable_auto_save(self, *args, **kwargs):
        return None

if settings.DEBUG:
    enforcer = _DebugEnforcer()
else:
    adapter = Adapter(DATABASE_URL)

    enforcer = casbin.Enforcer(
        str(model_path),
        adapter,
    )

    enforcer.load_policy()
    enforcer.enable_auto_save(True)