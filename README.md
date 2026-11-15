# Weather API

A small FastAPI service that returns real-time weather and a daily forecast using
[Open-Meteo](https://open-meteo.com) (free, no API key).

## Run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive docs.

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /weather?city=Semarang&days=3&units=metric` | Weather by city name |
| `GET /weather/coords?lat=-6.97&lon=110.42` | Weather by coordinates |
| `GET /health` | Health check |

`units` is `metric` (°C, km/h, mm) or `imperial` (°F, mph, inch). `days` is 1-16.

## Example

```bash
curl "http://127.0.0.1:8000/weather?city=Semarang&days=2"
```

Results are cached in memory for 5 minutes to reduce upstream calls.
Open-Meteo's free tier is for non-commercial use.
