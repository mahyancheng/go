from ollama import AsyncClient

class LLMHandler:
    """
    Handles communication with the qwen2.5:32b-instruct model via Ollama.
    """
    def __init__(self, model_name: str = "qwen2.5:32b-instruct"):
        self.model = model_name
        self.client = AsyncClient()

    async def generate(self, messages: list[dict], stream: bool = False) -> str:
        if stream:
            chunks = []
            async for chunk in await self.client.chat(model=self.model, messages=messages, stream=True):
                chunks.append(chunk["message"]["content"])
            return "".join(chunks)
        else:
            response = await self.client.chat(model=self.model, messages=messages, stream=False)
            return response["message"]["content"]
