from fastapi import APIRouter

v1_router = APIRouter()
# Tenant endpoints are now exposed via GraphQL (see tenant_graphql.py) and the REST
# router has been removed.