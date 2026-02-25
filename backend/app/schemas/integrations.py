from typing import List, Dict, Any
from sqlmodel import SQLModel

class OpenAIIdeaRequest(SQLModel):
    keywords: List[str]

class OpenAIIdeaResponse(SQLModel):
    ideas: Dict[str, Any]
