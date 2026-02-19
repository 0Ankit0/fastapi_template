from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

app = FastAPI(
    title="fastapi_template",
    description="A template for FastAPI applications",
    version="0.1.0",
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",  # Syntax highlighting theme
        "deepLinking": True,  # Enable deep linking to operations
        "displayOperationId": True,  # Show operation IDs
        "filter": True,  # Enable search/filter bar
        "showExtensions": True,  # Show vendor extensions
        "showCommonExtensions": True,
        "persistAuthorization": True,  # Remember authorization between reloads
        "displayRequestDuration": True,  # Show request duration
        "docExpansion": "list",  # Default expansion: "list", "full", or "none"
        "defaultModelsExpandDepth": 1,  # How deep to expand models
        "defaultModelExpandDepth": 1,
    }
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/")
def read_root():
    return {"Hello": "World"}