import openai
from app.core.config import settings
from typing import List, Dict, Any

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY

class OpenAIClient:
    @staticmethod
    async def get_saas_ideas(keywords: List[str]) -> Dict[str, Any]:
        prompt = f"Get me 3-5 {', '.join(keywords)} saas ideas"
        
        try:
            # Using async call if available or wrapping in run_in_executor
            # For simplicity using synchronous call as openai < 1.0 (check version)
            # If openai >= 1.0, syntax is different. Assuming < 1.0 based on existing code structure or latest?
            # Existing code used `openai.Completion.create`.
            # Let's assume typical usage.
            
            # NOTE: openai library is sync unless using AsyncOpenAI in v1+.
            # Pydantic v2 suggests v1+.
            # Let's try to be compatible or use standard.
            
            # Assuming older style for now based on 'openai.Completion.create' in django code.
            # But we should probably use newer client if installing fresh.
            # Let's stick to simple sync wrapper for now or check version installed.
            # Since I am installing `openai = "*"`, it will get latest (v1+).
            # v1+ syntax: client = OpenAI(...) client.completions.create(...)
            
            # However, to be safe and simple:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct", # text-davinci-003 is deprecated
                prompt=prompt,
                max_tokens=200,
                temperature=0.5
            )
            return response
            
        except Exception as e:
            # Handle error
            print(f"OpenAI Error: {e}")
            raise e
