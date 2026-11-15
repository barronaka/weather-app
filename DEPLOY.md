# Deploying to Render

## 1. Push the project to GitHub

Your folder should contain: `main.py`, `requirements.txt`, `render.yaml`, `.gitignore`,
`static/index.html` (and optionally `README.md`, `test_deployed.py`).

In PowerShell, inside `F:\weather app`:

```powershell
git init
git add .
git commit -m "Weather app"
git branch -M main
```

Create an empty repository on https://github.com/new (e.g. `weather-app`), then:

```powershell
git remote add origin https://github.com/<your-username>/weather-app.git
git push -u origin main
```

## 2. Create the service on Render

1. Sign up / log in at https://render.com (you can sign in with GitHub).
2. Click **New +** > **Blueprint** and select your `weather-app` repository.
   Render reads `render.yaml` and fills in the settings automatically.
   (Alternative: **New +** > **Web Service**, then use build command
   `pip install -r requirements.txt` and start command
   `uvicorn main:app --host 0.0.0.0 --port $PORT`.)
3. Click **Apply / Create**. The first build takes a few minutes.
4. When it shows **Live**, copy the URL (like `https://weather-app-xxxx.onrender.com`).

## 3. Test it

```powershell
python test_deployed.py https://weather-app-xxxx.onrender.com
```

Also open the URL in a browser and try a few cities.

## Notes

- Free instances go to sleep when idle, so the first visit after a quiet period can take
  up to about a minute. That is normal, not a bug.
- Updating the app: `git add .`, `git commit -m "..."`, `git push`. Render redeploys itself.
- Open-Meteo's free tier is for non-commercial use.
