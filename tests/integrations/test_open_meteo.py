import httpx
import pytest

GEOCODE_REGEX = r"^https://geocoding-api\.open-meteo\.com/v1/search.*$"
FORECAST_REGEX = r"^https://api\.open-meteo\.com/v1/forecast.*$"


def mock_geocoding_ok(respx_mock, *, name="New York", lat=40.7128, lon=-74.0060):
    return respx_mock.get(url__regex=GEOCODE_REGEX).respond(
        status_code=200,
        json={
            "results": [
                {
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "country": "United States",
                }
            ]
        },
    )


def mock_geocoding_empty(respx_mock):
    return respx_mock.get(url__regex=GEOCODE_REGEX).respond(
        status_code=200,
        json={"results": []},
    )


def mock_forecast_ok(respx_mock, *, temp=25.0):
    return respx_mock.get(url__regex=FORECAST_REGEX).respond(
        status_code=200,
        json={"current": {"temperature_2m": temp}},
    )


@pytest.mark.asyncio
async def test_fetch_weather_invalid_city(respx_mock, client):
    mock_geocoding_empty(respx_mock)

    with pytest.raises(Exception):
        await client.fetch_weather("NoSuchCity")


@pytest.mark.asyncio
async def test_fetch_weather_timeout(respx_mock, client):
    respx_mock.get(url__regex=GEOCODE_REGEX).side_effect = httpx.ReadTimeout("timeout")

    with pytest.raises(Exception):
        await client.fetch_weather("New York")


@pytest.mark.asyncio
async def test_fetch_weather_connection_error(respx_mock, client):
    respx_mock.get(url__regex=GEOCODE_REGEX).side_effect = httpx.ConnectError("boom")

    with pytest.raises(Exception):
        await client.fetch_weather("New York")


@pytest.mark.asyncio
async def test_fetch_weather_5xx_eventual_failure(respx_mock, client):
    mock_geocoding_ok(respx_mock)

    route = respx_mock.get(url__regex=FORECAST_REGEX)
    route.side_effect = [
        httpx.Response(503, json={"error": "unavailable"}),
        httpx.Response(503, json={"error": "unavailable"}),
        httpx.Response(503, json={"error": "unavailable"}),
    ]

    with pytest.raises(Exception):
        await client.fetch_weather("New York")


@pytest.mark.asyncio
async def test_fetch_weather_4xx_no_retry(respx_mock, client):
    mock_geocoding_ok(respx_mock)

    respx_mock.get(url__regex=FORECAST_REGEX).respond(
        status_code=400,
        json={"error": "bad request"},
    )

    with pytest.raises(Exception):
        await client.fetch_weather("New York")


@pytest.mark.asyncio
async def test_fetch_weather_forecast_4xx_no_retry(respx_mock, client):
    mock_geocoding_ok(respx_mock)

    respx_mock.get(url__regex=FORECAST_REGEX).respond(
        status_code=404,
        json={"error": "not found"},
    )

    with pytest.raises(Exception):
        await client.fetch_weather("New York")
