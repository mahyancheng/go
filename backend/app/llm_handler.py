import asyncio
from typing import List, Optional
from ollama import AsyncClient
from pydantic import PrivateAttr
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage

class LLMHandler(BaseChatModel):
    model: str = "qwen2.5:32b-instruct"
    # Declare a private attribute using PrivateAttr so it is not a field.
    _client: AsyncClient = PrivateAttr()

    def __init__(self, model_name: str = "qwen2.5:32b-instruct", **data):
        # Initialize BaseChatModel with the field "model"
        super().__init__(model=model_name, **data)
        self.model = model_name
        # Set the asynchronous client as a private attribute.
        self._client = AsyncClient()

    # Implement _llm_type as a regular method (not as a property)
    def _llm_type(self) -> str:
        return "ollama"

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> dict:
        # Convert the messages to the expected list of dictionaries.
        message_list = [{"role": m.role, "content": m.content} for m in messages]
        response = await self._client.chat(model=self.model, messages=message_list, stream=False)
        content = response["message"]["content"]
        # Wrap the response as expected by BaseChatModel.
        return {"generations": [[AIMessage(content=content, role="assistant")]]}

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> dict:
        # Synchronously execute the asynchronous generation.
        return asyncio.run(self._agenerate(messages, stop=stop, **kwargs))

    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> AIMessage:
        result = await self._agenerate(messages, **kwargs)
        return result["generations"][0][0]

    def invoke(self, messages: List[BaseMessage], **kwargs) -> AIMessage:
        return self._generate(messages, **kwargs)

    async def aget(self, messages: List[BaseMessage], **kwargs) -> str:
        ai_message = await self.ainvoke(messages, **kwargs)
        return ai_message.content

    def get(self, messages: List[BaseMessage], **kwargs) -> str:
        return self.invoke(messages, **kwargs)
