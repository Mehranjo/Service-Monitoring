# Direct Debit Service Status Dashboard

A lightweight monitoring and control dashboard for Direct Debit banking services (Pay / Create). View real-time status (Stable / Unstable / Inaccessible) across multiple banks and change statuses — individually or in bulk — without needing tools like Postman.

![status](https://img.shields.io/badge/status-active-success) ![type](https://img.shields.io/badge/type-single--file%20HTML-blue)

## Features

- Tabular view of every bank/service combination with clear status color-coding
- Filter by status (Stable / Unstable / Inaccessible) and by service type (Pay / Create)
- Single-row or bulk status changes — bulk actions are sent sequentially under the hood, since most APIs only accept one change per request
- Real-time status sync from the server (if a read/GET endpoint is available)
- Manual "import latest snapshot" fallback (if no read endpoint exists)
- Persistent change history, stored in the browser's IndexedDB — survives page reloads and browser restarts, with no backend or internet connection required
- Runs entirely client-side — just one HTML file, no build step, no server

## Screenshots

*(add a screenshot or short GIF here once you have one — it makes a big difference for a public repo)*

## Files

| File | Purpose |
|---|---|
| `dashboard.html` | The dashboard itself — open this directly in your browser |
| `proxy_server.py` | Local CORS-bypass proxy, pure Python (standard library only, no extra installs) |
| `proxy_server.ps1` | The same proxy, in PowerShell (already built into every Windows machine — no Python required) |

## Why a proxy?

If your banking API doesn't return an `Access-Control-Allow-Origin` header, browsers will block direct requests sent from a local HTML file with a **CORS** error. These proxy scripts listen only on `127.0.0.1` (your own machine), receive the request from the browser, forward it themselves (with no CORS restriction, since they aren't browsers), and return the response with the correct CORS header attached.

If your API already supports CORS, you don't need the proxy at all — just point the dashboard's settings directly at your real API URL.

## Setup

### 1. Run the proxy (only needed if you hit CORS errors)

**With Python:**
```bash
python proxy_server.py
```

**Or with PowerShell (Windows, no Python installation needed):**
```powershell
powershell -ExecutionPolicy Bypass -File proxy_server.ps1
```

Both listen on port `2080` by default. Before running, edit two things inside the script:
- `TARGET_DOMAIN` (Python) / `$targetDomain` (PowerShell) — your real API's domain
- `FORWARD_HEADERS` (Python) / `$forwardHeaders` (PowerShell) — the list of header names your API uses for authentication (defaults to `accessCode` and `Cookie`; swap in `Authorization`, `X-API-Key`, or whatever your API expects)

### 2. Open the dashboard

Open `dashboard.html` directly in your browser — just double-click it. No server or build step required.

### 3. Connection settings

Click **⚙ Connection Settings** inside the dashboard and fill in:
- **Base URL** — the status-change (POST) endpoint
- **Status All URL** — the read-status (GET) endpoint, if your API has one. If not, leave it and use the "Import latest snapshot" feature instead.
- **accessCode** / **Cookie** — your API's authentication values

If you're using the local proxy, point both URLs at `http://127.0.0.1:2080/...` (this is the dashboard's default).

## Security note

Credentials (`accessCode`, `Cookie`) are kept only in the browser tab's in-memory state — never written to disk, and never committed to this repo. They're cleared on page reload/close, by design. **Never commit real credentials into this code.**

## Adapting this to your organization

This project isn't tied to any specific provider. Before using it for real, you'll want to update:
- The bank list (`BANKS`) and display names (`DEFAULT_BANK_NAMES`) in `dashboard.html`
- The API endpoint URLs (`baseUrl`, `statusAllUrl`)
- The proxy target domain (`TARGET_DOMAIN` / `$targetDomain`)

## License

MIT — feel free to use, modify, and adapt this for your own monitoring needs.
