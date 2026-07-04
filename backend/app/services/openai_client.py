from __future__ import annotations

from openai import AsyncOpenAI

from app.config import Settings, get_settings


class OpenAIClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key.strip())

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    async def generate(self, messages: list[dict[str, str]]) -> str:
        if not self.is_configured:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=self.settings.openai_temperature,
            max_tokens=self.settings.openai_max_tokens,
        )

        choices = response.choices or []
        if not choices or not choices[0].message.content:
            raise RuntimeError("OpenAI returned an empty response.")
        return choices[0].message.content.strip()
