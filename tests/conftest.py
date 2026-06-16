from __future__ import annotations

import os
import sys
import types
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["DEBUG"] = "true"
os.environ["EMAIL_SERVICE_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["PASETO_SECRET_KEY"] = "test-paseto-secret"


class FakeScalarResult:
    def __init__(self, value: Any = None, values: list[Any] | None = None) -> None:
        self.value = value
        self.values = values if values is not None else ([] if value is None else [value])

    def first(self) -> Any:
        return self.value

    def all(self) -> list[Any]:
        return self.values


class FakeExecuteResult:
    def __init__(self, value: Any = None, values: list[Any] | None = None) -> None:
        self.scalar_result = FakeScalarResult(value=value, values=values)

    def scalars(self) -> FakeScalarResult:
        return self.scalar_result

    def scalar_one_or_none(self) -> Any:
        return self.scalar_result.first()


class FakeDB:
    def __init__(self, *results: FakeExecuteResult) -> None:
        self.results = list(results)
        self.executed: list[Any] = []
        self.added: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if not self.results:
            raise AssertionError("No fake DB result queued for execute()")
        return self.results.pop(0)

    def add(self, instance: Any) -> None:
        if instance.__class__.__name__ == "User" and getattr(instance, "id", None) is None:
            instance.id = 1
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture
def fake_expiration() -> datetime:
    return datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def auth_client():
    from src.core.dependencies import get_session
    from src.core.exception_handlers import register_exception_handlers

    dependencies_stub = types.ModuleType("src.apps.iam.dependencies")
    dependencies_stub.get_current_user = lambda: None
    sys.modules["src.apps.iam.dependencies"] = dependencies_stub

    import src.apps.organizations.models  # noqa: F401

    def load_route_module(module_name: str, relative_path: str):
        spec = importlib.util.spec_from_file_location(module_name, PROJECT_ROOT / relative_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load {module_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    register_module = load_route_module(
        "tests.route_modules.iam_register",
        "src/apps/iam/api/v1/auth/register.py",
    )
    login_module = load_route_module(
        "tests.route_modules.iam_login",
        "src/apps/iam/api/v1/auth/login.py",
    )

    db_holder: dict[str, FakeDB | None] = {"db": None}
    modules = {"register": register_module, "login": login_module}
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(register_module.router, prefix="/api/v1/auth")
    app.include_router(login_module.router, prefix="/api/v1/auth")

    async def override_get_session():
        if db_holder["db"] is None:
            raise AssertionError("Test did not provide a fake DB")
        yield db_holder["db"]

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, db_holder, modules
