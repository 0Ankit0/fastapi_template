from fastapi import FastAPI
from src.apps.iam.casbin import enforcer
from src.db.base import Base
from src.core.exception_handlers import register_exception_handlers
from src.apps import get_all_routers

app = FastAPI()
register_exception_handlers(app)
app.include_router(get_all_routers())
