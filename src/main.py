from fastapi import FastAPI
from .apps.iam.casbin import enforcer

app = FastAPI()