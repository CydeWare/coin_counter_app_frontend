# Rupiah Coin Counter — FastAPI Backend

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

| Method | Path      | Description |
|--------|-----------|-------------|
| GET    | `/`       | Health check |
| POST   | `/detect` | Detect coins in an image |

## `/detect` — Request

- Content-Type: `multipart/form-data`
- Field: `file` — any JPEG/PNG image

## `/detect` — Response

```json
{
  "coin_count": 18,
  "total_value": 4800,
  "breakdown": {
    "100": 6,
    "200": 7,
    "500": 5
  },
  "annotated_image": "<base64-encoded JPEG>"
}
```

- `annotated_image` is a base64 JPEG you can display as `<img src="data:image/jpeg;base64,...">`
- Green circles = valid coins with denomination label
- Magenta circle = reference badge (not counted)
- Gray circles = radius didn't match any denomination
- Red circles = failed fill-ratio validity check

## How the model works (from `project_improved.ipynb`)

1. **Resize** image to 800px width
2. **CLAHE** contrast enhancement + median blur
3. **Hough Circle Transform** to detect circles
4. **Reference circle** detection — looks for a blue-tinted circle (the painted badge in your photos), used as a size reference
5. **Scaled-radius clustering** — each coin's radius is divided by the reference radius, then matched to pre-computed centroids:
   - `0.724` → Rp 100
   - `0.788` → Rp 200
   - `0.852` → Rp 500
6. **Fill-ratio validity check** — rejects circles that don't have enough foreground pixels (e.g. false positives on dark backgrounds)