from __future__ import annotations

from typing import Any

from app.integrations.open_meteo import OpenMeteoClient


class OpenMeteoProvider:
    def __init__(self, client: OpenMeteoClient) -> None:
        self._client = client

    async def get_weather(self, city: str) -> dict[str, Any]:
        return await self._client.fetch_weather(city)
