import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import base64
import io
import uvicorn

app = FastAPI(title="Rupiah Coin Counter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model constants (from project_improved.ipynb) ──────────────────────────
CENTROIDS = [0.72410345, 0.7875909, 0.8518564]
LABELS    = ["100", "200", "500"]
PARAM1    = 180
PARAM2    = 40

# ── Core image processing functions ────────────────────────────────────────

def resize_image(img, new_width=800):
    h, w = img.shape[:2]
    new_h = int(new_width * h / w)
    return cv2.resize(img, (new_width, new_h), interpolation=cv2.INTER_AREA)


def preprocess_image(img):
    resized = resize_image(img)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=0.8, tileGridSize=(10, 10))
    gray_clahe = clahe.apply(gray)
    blur = cv2.medianBlur(gray_clahe, 7)
    return blur


def get_circles(img):
    circles = cv2.HoughCircles(
        preprocess_image(img),
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=40,
        param1=PARAM1,
        param2=PARAM2,
        minRadius=40,
        maxRadius=150,
    )
    return circles


def get_reference_circle(circles, img, blue_threshold=85, saturation_threshold=16):
    resized = resize_image(img)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    sorted_circles = sorted(circles[0], key=lambda c: c[2], reverse=True)

    for circle in sorted_circles:
        x, y, r = circle
        xi, yi, ri = int(x), int(y), int(r)
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (xi, yi), ri, 255, -1)
        mean_h, mean_s, _, _ = cv2.mean(hsv, mask=mask)
        if blue_threshold <= mean_h <= 120 and mean_s >= saturation_threshold:
            return circle
    return None


def check_coin_validity(circle, img, fill_ratio_threshold=0.90):
    resized = resize_image(img)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    x, y, r = circle
    xi, yi, ri = int(x), int(y), int(r)
    h, w = gray.shape
    foreground = gray > 20
    circle_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(circle_mask, (xi, yi), ri, 255, -1)
    foreground_inside = np.logical_and(foreground, circle_mask > 0)
    foreground_pixels = np.count_nonzero(foreground_inside)
    area = np.pi * (r ** 2)
    fill_ratio = foreground_pixels / area
    return fill_ratio > fill_ratio_threshold


def draw_text_outline(img, text, pos, font, scale, color, thickness):
    x, y = pos
    for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        cv2.putText(img, text, (x+dx, y+dy), font, scale, (0,0,0), thickness+2, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def detect_coins(img):
    """
    Run full coin-detection pipeline.
    Returns annotated image (BGR), coin_count, total_value, per-coin breakdown.
    """
    circles = get_circles(img)
    if circles is None:
        return resize_image(img), 0, 0, []

    reference_circle = get_reference_circle(circles, img)
    reference_radius = reference_circle[2] if reference_circle is not None else 70

    centroids = np.array(CENTROIDS)
    threshold = 0.06

    resized = resize_image(img)
    coin_count  = 0
    total_value = 0
    coins       = []   # list of {label, x, y, r}

    for circle in circles[0]:
        x, y, r = circle
        xi, yi, ri = int(x), int(y), int(r)

        # Mark reference circle (blue badge) but don't count it
        if reference_circle is not None and np.array_equal(circle, reference_circle):
            cv2.circle(resized, (xi, yi), ri, (255, 0, 255), 3)
            draw_text_outline(resized, "REF", (xi - 25, yi + 8),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)
            continue

        scaled_radius = r / reference_radius
        distances = np.abs(centroids - scaled_radius)
        nearest_idx = np.argmin(distances)

        if distances[nearest_idx] > threshold:
            # Unmatched — draw gray
            cv2.circle(resized, (xi, yi), ri, (100, 100, 100), 2)
            continue

        if not check_coin_validity(circle, img):
            # Invalid (not really a coin)
            cv2.circle(resized, (xi, yi), ri, (0, 0, 200), 2)
            continue

        label = LABELS[nearest_idx]
        total_value += int(label)
        coin_count  += 1
        coins.append({"label": label, "x": xi, "y": yi, "r": ri})

        cv2.circle(resized, (xi, yi), ri, (0, 255, 0), 2)
        draw_text_outline(
            resized, label,
            (xi - 30, yi + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            1, (255, 200, 100), 2,
        )

    return resized, coin_count, total_value, coins


def encode_image_b64(img_bgr: np.ndarray) -> str:
    success, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise RuntimeError("Failed to encode result image")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Rupiah Coin Counter API is running. POST an image to /detect"}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    raw = await file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")

    annotated, coin_count, total_value, coins = detect_coins(img)
    annotated_b64 = encode_image_b64(annotated)

    # Denomination breakdown
    breakdown = {}
    for c in coins:
        breakdown[c["label"]] = breakdown.get(c["label"], 0) + 1

    return JSONResponse({
        "coin_count":    coin_count,
        "total_value":   total_value,
        "breakdown":     breakdown,
        "annotated_image": annotated_b64,   # base64 JPEG
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)