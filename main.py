"""Weather API: real-time weather and forecasts via Open-Meteo (no API key needed)."""

import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

STATIC_DIR = Path(__file__).parent / "static"

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 300  # reuse results for 5 minutes

app = FastAPI(title="Weather API", version="1.0.0")

# Open-Meteo WMO weather codes -> human-readable text
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle", 57: "Dense freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}

_cache: dict[str, tuple[float, Any]] = {}


def cache_get(key: str) -> Any | None:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    _cache.pop(key, None)
    return None


def cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


async def fetch_json(url: str, params: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Upstream weather service timed out")
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Upstream weather service error: {exc}")


async def geocode(city: str) -> dict:
    key = f"geo:{city.lower()}"
    if (cached := cache_get(key)) is not None:
        return cached
    data = await fetch_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en"})
    results = data.get("results")
    if not results:
        raise HTTPException(404, f"City not found: {city}")
    place = results[0]
    location = {
        "name": place["name"],
        "country": place.get("country"),
        "region": place.get("admin1"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }
    cache_set(key, location)
    return location


async def get_weather(lat: float, lon: float, days: int, units: str) -> dict:
    key = f"wx:{lat:.2f}:{lon:.2f}:{days}:{units}"
    if (cached := cache_get(key)) is not None:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "precipitation,weather_code,wind_speed_10m,wind_direction_10m,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_sum,precipitation_probability_max",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": max(days, 2),  # at least 2 so 24 hourly values remain late in the day
        "timezone": "auto",
    }
    if units == "imperial":
        params.update(temperature_unit="fahrenheit", wind_speed_unit="mph",
                      precipitation_unit="inch")

    raw = await fetch_json(FORECAST_URL, params)
    cur, daily = raw["current"], raw["daily"]

    # Next 24 hours, starting from the current hour
    hr = raw["hourly"]
    start = cur["time"][:13] + ":00"
    first = hr["time"].index(start) if start in hr["time"] else 0
    hourly = [
        {
            "time": hr["time"][i],
            "temperature": hr["temperature_2m"][i],
            "precipitation_probability_percent": hr["precipitation_probability"][i],
            "condition": WEATHER_CODES.get(hr["weather_code"][i], "Unknown"),
        }
        for i in range(first, min(first + 24, len(hr["time"])))
    ]

    result = {
        "timezone": raw.get("timezone"),
        "hourly": hourly,
        "units": units,
        "current": {
            "time": cur["time"],
            "temperature": cur["temperature_2m"],
            "feels_like": cur["apparent_temperature"],
            "humidity_percent": cur["relative_humidity_2m"],
            "precipitation": cur["precipitation"],
            "wind_speed": cur["wind_speed_10m"],
            "wind_direction_deg": cur["wind_direction_10m"],
            "is_day": bool(cur["is_day"]),
            "condition": WEATHER_CODES.get(cur["weather_code"], "Unknown"),
        },
        "daily": [
            {
                "date": daily["time"][i],
                "condition": WEATHER_CODES.get(daily["weather_code"][i], "Unknown"),
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation_sum": daily["precipitation_sum"][i],
                "precipitation_probability_percent": daily["precipitation_probability_max"][i],
            }
            for i in range(min(days, len(daily["time"])))
        ],
    }
    cache_set(key, result)
    return result


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/weather")
async def weather_by_city(
    city: str = Query(..., min_length=1, description="City name, e.g. Semarang"),
    days: int = Query(3, ge=1, le=16, description="Forecast days"),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    location = await geocode(city)
    data = await get_weather(location["latitude"], location["longitude"], days, units)
    return {"location": location, **data}


@app.get("/weather/coords")
async def weather_by_coords(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(3, ge=1, le=16),
    units: str = Query("metric", pattern="^(metric|imperial)$"),
):
    data = await get_weather(lat, lon, days, units)
    return {"location": {"latitude": lat, "longitude": lon}, **data}


@app.get("/health")
async def health():
    return {"status": "ok"}
