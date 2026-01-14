from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_weather_service
from app.services.weather_service import WeatherService

router = APIRouter(tags=["weather"])


@router.get("/weather")
async def get_weather(
    city: str = Query(..., min_length=1),
    service: WeatherService = Depends(get_weather_service),
) -> dict:
    result = await service.get_weather(city)
    return {
        "city": result.city,
        "cache_hit": result.cache_hit,
        "data": result.data,
    }
