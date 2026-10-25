# Deployment — one public URL for judges

The repository ships a single image that serves **both** the FastAPI API and the exported
Next.js UI. One URL means no CORS, no second service to cold-start, and no "frontend can't reach
backend" failure during judging.

```
Docker image
├── FastAPI  /api/*        (guidelines, scans, approval, analytics)
└── Next.js  /*            (static export from frontend/out)
```

---

## Option A — Render (recommended, free)

### 1. Push the code to a public GitHub repository

From the project root:

```powershell
git init
git add .
git commit -m "BrandGuard AI - Codex 48 Round 2"
git branch -M main
# create an empty public repo named brandguard-ai on github.com, then:
git remote add origin https://github.com/<your-username>/brandguard-ai.git
git push -u origin main
```

Make sure the repository visibility is **Public**. Judges must be able to open it without
signing in.

### 2. Deploy with the blueprint

1. Sign in at <https://dashboard.render.com> (GitHub sign-in is fine).
2. **New → Blueprint**.
3. Connect GitHub and select the `brandguard-ai` repository.
4. Render detects [`render.yaml`](../render.yaml). Click **Apply**.
5. Wait for the Docker build (first build 5–10 minutes).
6. Copy the service URL, e.g. `https://brandguard-ai-xxxx.onrender.com`.

The blueprint uses the **free** plan, the Singapore region, Docker, and health check
`/api/health`. No environment variables are required. The image already seeds the demo data
(16 clauses, 5 historical scans) on first boot.

### 3. Or deploy manually (no blueprint)

**New → Web Service → Build and deploy from a Git repository** → select the repo:

| Setting | Value |
| --- | --- |
| Language / runtime | Docker |
| Region | Singapore (or closest) |
| Plan | Free |
| Dockerfile path | `./Dockerfile` |
| Health check path | `/api/health` |

Click **Create Web Service**.

### 4. Free-tier behaviour (important)

- The instance **sleeps after ~15 minutes of inactivity**. The first request can take 30–60 s.
- **Open the URL five minutes before a demo or judging window** so it is warm.
- There is no persistent disk on the free plan, so the SQLite database resets on every deploy
  or restart. This is intentional: every visitor gets the same seeded demo, and destructive
  clicks by one judge do not affect the next.
- If the page spins, wait and refresh once; it is the cold start, not a broken build.

---

## Option B — any Docker host (Railway, Fly.io, VPS)

```powershell
docker build -t brandguard-ai .
docker run --rm -p 8000:8000 brandguard-ai
# open http://localhost:8000
```

On another host, expose the container port and set `PORT` if the platform requires it
(the start command already honours `$PORT`). No other variables are needed.

Fly.io sketch:

```powershell
fly launch --no-deploy        # accept the existing Dockerfile
fly deploy
fly open
```

---

## Option C — split deployment (Vercel frontend + Render API)

Use this only if you specifically want Vercel's CDN.

1. Deploy the API as a Render **Python** web service:
   - Root directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Env: `BRANDGUARD_CORS_ORIGINS=https://<your-vercel-app>.vercel.app`
2. Deploy the frontend to Vercel:
   - Root directory: `frontend`
   - Env: `NEXT_PUBLIC_API_URL=https://<your-render-api>.onrender.com`
3. Redeploy the frontend **after** setting the env var (Next inlines it at build time).

Do **not** set `NEXT_STATIC_EXPORT` for the Vercel build. The single-container path uses
`NEXT_PUBLIC_API_URL=/` as a same-origin marker.

---

## Verify before submitting (private window)

Open the deployed URL in an **Incognito/Private** window. Do not sign in to anything.

- [ ] Home page loads and shows the sample draft and **Run inspection**.
- [ ] Run inspection → findings appear across four agent tabs, with clause citations.
- [ ] Accept a suggestion → the draft changes and the score updates.
- [ ] Override a finding with a note → it is suppressed on re-scan.
- [ ] Switch role to **Manager** → **Approve draft** → **Publish**.
- [ ] Open **Insights** → KPIs, trend, inspector load, clarity index all render.
- [ ] `Ctrl/Cmd+K` search returns results; Enter opens a scan.
- [ ] Open `…/analytics` directly (hard refresh) — it must not 404.
- [ ] DevTools → Network: **no requests to `localhost:8000`**.
- [ ] Open the source repository in the same private window — it must be public.

If every box is ticked, the link satisfies the "anyone can open it without signing in" rule.

---

## Finalise the submission PDF

Once both links exist, regenerate the PDF so the cover contains the real URLs:

```powershell
.\backend\.venv\Scripts\python.exe scripts\build_submission_pdf.py `
  --demo-url https://your-service.onrender.com `
  --repo-url https://github.com/your-username/brandguard-ai
```

This writes `docs/BrandGuard-AI-Round-2-Submission.pdf`. Without both arguments the script writes
a clearly named `-DRAFT.pdf` instead, so a placeholder PDF cannot be submitted by accident. Upload
the final PDF to the Round 2 form.

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Page loads but data says "Could not reach the BrandGuard API" | The UI was built with the default `localhost:8000`. Rebuild with `NEXT_PUBLIC_API_URL=/` (the Dockerfile does this), or set the real API URL for a split deployment. |
| First request hangs ~40 s | Render free-tier cold start. Refresh; warm it before judging. |
| 404 on `/analytics` after hard refresh | The API container is not serving `FRONTEND_DIST`. Confirm the Docker image copied `frontend/out` to `/app/static` and that the env var is set. |
| 502 on Render | Build failed or health check failing. Open Render logs; check `/api/health` locally with `docker run`. |
| Data changed / demo looks messy | Free tier has no disk; restart the service to reseed. Locally, delete `backend/data/brandguard.db` and restart. |
| CORS error (split deployment only) | Add the exact frontend origin to `BRANDGUARD_CORS_ORIGINS`; include scheme, no trailing slash. |

---

## Updating the deployment

Push to `main`; Render auto-deploys from the blueprint (`autoDeploy: true`). The database is
recreated and reseeded on each deploy.

## Source repository checklist

- [ ] Repository is **Public**.
- [ ] `README.md` renders with quickstart and demo script.
- [ ] No `.env`, API keys, database files, or `node_modules` committed.
- [ ] `Dockerfile`, `render.yaml`, `docs/DEPLOY.md` present.
- [ ] License/attribution if you use third-party assets.
