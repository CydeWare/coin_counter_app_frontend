# coin_counter_app_frontend
A frontend app for counting coins from images!

---
# Koin. — Frontend

A minimal dark-themed web app for the Rupiah Coin Counter. Upload or capture a photo of Indonesian coins and instantly see how many there are and the total value.

## Usage

Just open `index.html` in your browser. No build step, no dependencies — it's plain HTML, CSS, and JavaScript.

Make sure the FastAPI backend is running first:
```bash
# Either run main.py directly in VS Code, or:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open `index.html` and you're good to go.

## Features

- **Camera** — opens your device camera directly (defaults to rear camera on mobile)
- **Gallery** — pick an existing photo from your file system or gallery
- **Drag & drop** — drag an image onto the upload zone on desktop
- **Annotated result** — shows the original photo with green circles drawn on each detected coin and its denomination label
- **Animated total** — the Rp amount ticks up like a cash register when results arrive
- **Breakdown chips** — shows how many of each denomination was found (Rp 500, Rp 200, Rp 100)

## How it works

1. You select or capture a photo
2. On "Count coins", the image is sent to the FastAPI backend at `localhost:8000/detect`
3. The backend runs the coin detection model and returns the annotated image, coin count, total value, and denomination breakdown
4. The frontend displays everything — annotated image, total Rp, and per-denomination counts

## Coin labels

| Circle color | Meaning |
|---|---|
| 🟢 Green | Valid coin — counted toward total |
| 🟣 Magenta | Reference badge (blue pin) — used for size calibration, not counted |
| ⚫ Gray | Circle detected but radius didn't match any denomination |
| 🔴 Red | Failed validity check — likely a false positive |

## Configuration

The API URL is set at the top of the `<script>` block in `index.html`:

```js
const API_URL = "http://localhost:8000/detect";
```

Change this if your backend runs on a different host or port.

## Supported coins

- Rp 100
- Rp 200
- Rp 500
