from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.api import deps
from app.models.user import User
from app.schemas.integrations import OpenAIIdeaRequest, OpenAIIdeaResponse
from app.services.openai import OpenAIClient

router = APIRouter()

@router.post("/openai/generate-ideas/", response_model=OpenAIIdeaResponse)
async def generate_ideas(
    request: OpenAIIdeaRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    try:
        # In a real async app, might want to run this in a thread pool if it's blocking
        result = await OpenAIClient.get_saas_ideas(request.keywords)
        # Convert result to dict if needed
        return {"ideas": result.model_dump() if hasattr(result, 'model_dump') else result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
