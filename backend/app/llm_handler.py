from ollama import AsyncClient

class LLMHandler:
    """
    Handles communication with the qwen2.5:32b-instruct model via Ollama.
    Implements asynchronous methods for generating responses and provides
    a minimal dict-like interface so that downstream code can use get, pop, etc.
    """
    def __init__(self, model_name: str = "qwen2.5:32b-instruct"):
        self.model = model_name
        self.client = AsyncClient()
        self._store = {}  # For minimal dict-like behavior

    async def generate(self, messages: list[dict], stream: bool = False) -> str:
        if stream:
            chunks = []
            async for chunk in await self.client.chat(model=self.model, messages=messages, stream=True):
                chunks.append(chunk["message"]["content"])
            return "".join(chunks)
        else:
            response = await self.client.chat(model=self.model, messages=messages, stream=False)
            return response["message"]["content"]

    async def invoke(self, messages: list[dict], **kwargs) -> str:
        message_history = list(messages)
        response = await self.client.chat(model=self.model, messages=message_history)
        return response["message"]["content"]

    async def aget(self, messages: list[dict], **kwargs) -> str:
        """
        Asynchronous alias for invoke.
        """
        return await self.invoke(messages, **kwargs)

    # --- Mapping (dict-like) interface ---
    def __getitem__(self, key):
        return self._store.get(key)

    def __setitem__(self, key, value):
        self._store[key] = value

    def pop(self, key, default=None):
        return self._store.pop(key, default)

    def get(self, key, default=None):
        return self._store.get(key, default)
