# CamStream Node

Lightweight V4L2/USB camera streaming service built with FastAPI and OpenCV, packaged for Docker deployment. Allows a single physical camera attached to a host server to be consumed concurrently by multiple external clients (OpenCV, FFmpeg, web dashboards) via HTTP MJPEG without device locking conflicts.

## Repository Structure

```text
camstream-node/
├── app.py                  # FastAPI server & thread-safe OpenCV capture loop
├── templates/
│   └── index.html          # Broadcast-style control & monitoring UI
├── examples/
│   └── client_reader.py    # Sample OpenCV client script
├── Dockerfile              # Minimal Debian-slim container definition
├── docker-compose.yml      # Service orchestration & /dev/video0 passthrough
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
└── README.md               # Documentation
```

## Quick Start (Docker)

1. Copy the environment template and adjust your camera device path if needed:
   ```bash
   cp .env.example .env
   ```

2. Build and start the container:
   ```bash
   docker compose up -d --build
   ```

3. Open the web dashboard at `http://<SERVER-IP>:8000`.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Client Usage

Test reading the remote stream from another machine using the included example script:

```bash
pip install opencv-python
python examples/client_reader.py http://<SERVER-IP>:8000/video_feed
```

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web control & monitoring dashboard |
| `GET` | `/video_feed` | Continuous `multipart/x-mixed-replace` MJPEG stream |
| `GET` | `/snapshot` | Latest single frame encoded as JPEG |
| `GET` | `/status` | Current camera state, active config, and connected client count |
| `POST` | `/config` | Live-update resolution, FPS, and JPEG compression quality |
