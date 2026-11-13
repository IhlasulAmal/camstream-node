import cv2
import threading
import time
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel


class StreamConfig(BaseModel):
    width: int
    height: int
    fps: int
    quality: int


class CameraManager:
    def __init__(self, source: str):
        self.source = int(source) if source.isdigit() else source
        self.width = int(os.getenv("FRAME_WIDTH", "1280"))
        self.height = int(os.getenv("FRAME_HEIGHT", "720"))
        self.fps = int(os.getenv("FPS", "30"))
        self.quality = int(os.getenv("JPEG_QUALITY", "80"))

        self.cap = None
        self.frame = None
        self.active_clients = 0
        self.running = True
        self.lock = threading.Lock()
        self.client_lock = threading.Lock()

        self._open_camera()
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _open_camera(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.source)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def update_config(self, width: int, height: int, fps: int, quality: int):
        with self.lock:
            res_changed = (self.width != width) or (self.height != height)
            self.width = width
            self.height = height
            self.fps = fps
            self.quality = quality

            if self.cap and self.cap.isOpened():
                if res_changed:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self.cap.set(cv2.CAP_PROP_FPS, fps)

    def _capture_loop(self):
        while self.running:
            with self.lock:
                if self.cap is None or not self.cap.isOpened():
                    self._open_camera()
                    time.sleep(1)
                    continue
                ret, frame = self.cap.read()
                if ret:
                    self.frame = frame

            if not ret:
                time.sleep(0.1)
            else:
                time.sleep(0.005)

    def get_jpeg_bytes(self):
        with self.lock:
            if self.frame is None:
                return None
            ret, buffer = cv2.imencode(
                ".jpg", self.frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            )
            return buffer.tobytes() if ret else None

    def increment_clients(self):
        with self.client_lock:
            self.active_clients += 1

    def decrement_clients(self):
        with self.client_lock:
            self.active_clients = max(0, self.active_clients - 1)

    def release(self):
        self.running = False
        with self.lock:
            if self.cap:
                self.cap.release()


CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
camera = CameraManager(CAMERA_SOURCE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    camera.release()


app = FastAPI(title="CamStream Node", lifespan=lifespan)


def generate_mjpeg():
    camera.increment_clients()
    try:
        while True:
            start_time = time.time()
            frame_bytes = camera.get_jpeg_bytes()
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            interval = 1.0 / max(1, camera.fps)
            elapsed = time.time() - start_time
            if elapsed < interval:
                time.sleep(interval - elapsed)
    finally:
        camera.decrement_clients()


@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/snapshot")
def snapshot():
    frame_bytes = camera.get_jpeg_bytes()
    if frame_bytes is None:
        return Response(content="Kamera belum siap", status_code=503)
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={"Content-Disposition": f"inline; filename=snapshot_{int(time.time())}.jpg"},
    )


@app.get("/status")
def get_status():
    is_connected = camera.cap is not None and camera.cap.isOpened()
    return {
        "status": "online" if is_connected else "offline",
        "source": str(camera.source),
        "resolution": f"{camera.width}x{camera.height}",
        "width": camera.width,
        "height": camera.height,
        "fps": camera.fps,
        "quality": camera.quality,
        "active_clients": camera.active_clients,
    }


@app.post("/config")
def update_config(cfg: StreamConfig):
    camera.update_config(cfg.width, cfg.height, cfg.fps, cfg.quality)
    return {"message": "Konfigurasi diperbarui", "config": cfg.model_dump()}
