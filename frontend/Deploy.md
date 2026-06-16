# 🚀 Frontend Deployment Guide — Edge AI OCR

> **Target**: Deploy the Vite/React frontend on your server PC (the same machine running the FastAPI backend).

---

## Prerequisites

Make sure the following are installed on your server PC:

| Tool | Purpose | Check |
|------|---------|-------|
| **Node.js ≥ 18** | Build the frontend | `node -v` |
| **npm ≥ 9** | Package manager | `npm -v` |
| A static file server (see options below) | Serve the `dist/` folder | — |

---

## Step 1 — Configure the API URL

The frontend is hardcoded to point to `http://localhost:5030`. This is fine **if the browser and the backend run on the same machine**.

If users access the app from **other machines on the network**, open [`frontend/src/App.jsx`](../frontend/src/App.jsx) and change line 16:

```js
// Before (localhost only)
const baseUrl = "http://localhost:5030";

// After (replace with your server's LAN IP or hostname)
const baseUrl = "http://192.168.x.x:5030";
```

> [!IMPORTANT]
> Do this **before** running the build in Step 2. The URL is baked into the compiled output.

---

## Step 2 — Install Dependencies

On your server PC, open a terminal inside the `frontend/` folder:

```bash
cd edge-ai-ocr/frontend
npm install
```

---

## Step 3 — Build the Production Bundle

```bash
npm run build
```

This creates a `frontend/dist/` folder containing optimised static files (HTML, JS, CSS, assets).

> [!NOTE]
> The `coo_template.xlsx` file in `public/` is automatically copied into `dist/` during the build.

---

## Step 4 — Serve the `dist/` Folder

Choose **one** of the options below.

---

### ✅ Option A — Quick: `serve` (Recommended for simple setups)

Install the `serve` package globally once:

```bash
npm install -g serve
```

Then run it pointing at the `dist/` folder:

```bash
serve -s dist -l 3000
```

The frontend is now available at `http://localhost:3000` (or `http://<server-ip>:3000` from other machines).

To keep it running in the background (Windows):

```powershell
Start-Process -WindowStyle Hidden powershell -ArgumentList "serve -s C:\path\to\edge-ai-ocr\frontend\dist -l 3000"
```

---

### ✅ Option B — Nginx (Recommended for production)

> [!TIP]
> Nginx is the most robust option — it serves static files efficiently, handles caching, and can proxy `/ocr/` requests to the FastAPI backend (avoids CORS entirely).

**1. Install Nginx** (Ubuntu/Debian):

```bash
sudo apt update && sudo apt install nginx -y
```

**2. Create a site config** at `/etc/nginx/sites-available/edge-ai-ocr`:

```nginx
server {
    listen 80;
    server_name localhost;          # or your server IP / domain

    # Serve the Vite build
    root /home/<user>/edge-ai-ocr/frontend/dist;
    index index.html;

    # React SPA: fall back to index.html for any unknown route
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Optional: Proxy API calls to FastAPI so the frontend
    # can use relative URLs (avoids CORS issues).
    # Uncomment if you change baseUrl to just "" in App.jsx.
    # location /ocr/ {
    #     proxy_pass         http://127.0.0.1:5030;
    #     proxy_set_header   Host $host;
    #     proxy_set_header   X-Real-IP $remote_addr;
    # }

    # Cache static assets aggressively
    location ~* \.(js|css|png|jpg|svg|ico|woff2|xlsx)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**3. Enable the site and reload Nginx:**

```bash
sudo ln -s /etc/nginx/sites-available/edge-ai-ocr /etc/nginx/sites-enabled/
sudo nginx -t          # test config — should say "syntax is ok"
sudo systemctl reload nginx
```

Frontend is now accessible at `http://<server-ip>/`.

---

### ✅ Option C — Python `http.server` (Quick test, not for production)

```bash
cd frontend/dist
python -m http.server 3000
```

---

## Step 5 — Start the FastAPI Backend

In a separate terminal (or use the process manager below):

```bash
cd edge-ai-ocr
# Activate your conda/venv environment first
conda activate llm_env          # or: source venv/bin/activate

python run.py
```

The API starts on port **5030** (configured in `.env`).

> [!WARNING]
> `run.py` currently uses `reload=True` which is for development only.
> For production, change it to `reload=False` or use `uvicorn` directly:
> ```bash
> uvicorn main:app --host 0.0.0.0 --port 5030 --workers 2
> ```

---

## Step 6 — Keep Both Processes Running (Optional but Recommended)

### Windows — PowerShell background jobs

```powershell
# Start backend
Start-Job -ScriptBlock {
    Set-Location "C:\path\to\edge-ai-ocr"
    & conda run -n llm_env python run.py
}

# Start frontend
Start-Job -ScriptBlock {
    serve -s "C:\path\to\edge-ai-ocr\frontend\dist" -l 3000
}
```

### Linux — systemd services

**Backend service** `/etc/systemd/system/edge-ai-ocr-api.service`:

```ini
[Unit]
Description=Edge AI OCR FastAPI Backend
After=network.target

[Service]
User=<your-user>
WorkingDirectory=/home/<your-user>/edge-ai-ocr
Environment="PATH=/home/<your-user>/miniconda3/envs/llm_env/bin"
ExecStart=/home/<your-user>/miniconda3/envs/llm_env/bin/uvicorn main:app --host 0.0.0.0 --port 5030 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Frontend service** (if using `serve` instead of Nginx) `/etc/systemd/system/edge-ai-ocr-web.service`:

```ini
[Unit]
Description=Edge AI OCR Frontend (serve)
After=network.target

[Service]
User=<your-user>
WorkingDirectory=/home/<your-user>/edge-ai-ocr/frontend/dist
ExecStart=/usr/bin/npx serve -s . -l 3000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable edge-ai-ocr-api edge-ai-ocr-web
sudo systemctl start edge-ai-ocr-api edge-ai-ocr-web

# Check status
sudo systemctl status edge-ai-ocr-api
sudo systemctl status edge-ai-ocr-web
```

---

## Step 7 — Verify the Deployment

Open a browser and go to:

| URL | Expected |
|-----|---------|
| `http://<server-ip>:3000` (or port 80 if Nginx) | Frontend loads, shows Edge-AI-OCR UI |
| `http://<server-ip>:5030/health` | `{ "status": "Healthy", "model_ready": true }` |
| `http://<server-ip>:5030/docs` | FastAPI Swagger UI |

In the frontend, the **green dot** (Health Indicator) in the top-left should show **Online**.

---

## Re-deploying After Code Changes

```bash
# 1. Pull latest code
git pull

# 2. Rebuild the frontend
cd frontend
npm install          # only if dependencies changed
npm run build        # regenerates dist/

# 3. Restart backend (if Python files changed)
sudo systemctl restart edge-ai-ocr-api   # Linux
# or just re-run: python run.py
```

---

## Quick Reference

```
edge-ai-ocr/
├── frontend/
│   ├── dist/          ← Serve this folder (output of npm run build)
│   ├── public/
│   │   └── coo_template.xlsx  ← Auto-included in dist/ on build
│   └── src/
│       └── App.jsx    ← Line 16: change baseUrl before building
├── main.py            ← FastAPI app entry
├── run.py             ← Dev server runner (port 5030)
└── .env               ← PORT, BASE_URL_LLM, MODEL_NAME
```
