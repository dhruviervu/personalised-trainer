# AI Personal Trainer (Phase 1)

A real-time fitness coaching application. Open the frontend in your browser, grant camera access, and perform squats while the system tracks your reps, movement phase, and form in real time.

**Phase 1** covers squat detection only: webcam frames stream to a FastAPI backend over WebSocket, MediaPipe Pose extracts skeleton landmarks server-side, and joint angles drive a squat state machine with live feedback on the frontend.

---

## Prerequisites

- **Docker** (recommended): Docker Engine + Docker Compose v2  
- **Manual setup**: Python 3.11+, Node.js 20+, a webcam, and a modern browser (Chrome, Edge, or Firefox)

---

## Quick start (Docker)

1. Copy the environment file:

   ```bash
   cp .env.example .env
   ```

2. Build and run both services:

   ```bash
   docker-compose up --build
   ```

3. Open [http://localhost:5173](http://localhost:5173), allow camera access, and start squatting.

- **Frontend**: http://localhost:5173  
- **Backend API**: http://localhost:8000  
- **Health check**: http://localhost:8000/health  

---

## Manual setup

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/ws` to `http://localhost:8000`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (React)                          │
│  ┌──────────┐   capture JPEG    ┌─────────────────────────────┐ │
│  │  Webcam  │ ─── 10 fps ──────►│ useWebSocket → /ws/session  │ │
│  │  <video> │                   └──────────────┬──────────────┘ │
│  └──────────┘                                  │                 │
│  ┌──────────┐   landmarks + reps              │ WebSocket       │
│  │ <canvas> │ ◄────────────────────────────────┘                 │
│  │ skeleton │   RepCounter · FormFeedback                        │
│  └──────────┘                                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ base64 JPEG (out) · JSON (in)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│  main.py                                                         │
│    decode JPEG → OpenCV BGR frame                                │
│         │                                                        │
│         ▼                                                        │
│  PoseDetector (MediaPipe Pose) → 33 landmarks                    │
│         │                                                        │
│         ▼                                                        │
│  FormAnalyser → joint angles (3-frame rolling average)           │
│         │                                                        │
│         ▼                                                        │
│  RepCounter → Squat state machine → reps, phase, form flags      │
└─────────────────────────────────────────────────────────────────┘
```

### WebSocket protocol

| Direction | Payload |
|-----------|---------|
| Client → server | Raw base64 JPEG string (no JSON wrapper) |
| Server → client | JSON: `landmarks`, `rep_count`, `good_reps`, `bad_reps`, `phase`, `form_flags`, `angles`, `feedback` |

### Squat phases

`standing` → `descending` → `bottom` → `ascending` → `standing` (rep counted if depth was reached)

---

## Project structure

```
personalised-trainer/
├── backend/          # FastAPI + MediaPipe vision pipeline
├── frontend/         # React + Vite UI
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Phase roadmap

| Phase | Focus |
|-------|--------|
| **1** | Squats only — pose detection, rep counting, form flags, skeleton overlay |
| **2** | Multiple exercises (lunges, push-ups), exercise selector UI |
| **3** | LLM voice/text coaching via Groq API using live session context |
| **4** | User accounts, workout history, progress dashboards |
| **5** | Mobile app, offline mode, trainer-customisable programs |

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Reserved for Phase 3 LLM coaching (unused in Phase 1) |

---

## Troubleshooting

- **No pose detected**: Step back so your full body (head to feet) is visible and well lit.
- **WebSocket disconnected**: Ensure the backend is running on port 8000; check the green/red status dot top-left.
- **Camera blocked**: Use HTTPS or `localhost`; grant camera permission in browser settings.
- **Docker + MediaPipe**: The backend container installs `libglib2.0-0` and `libgomp1` on first start. The pose model (`pose_landmarker_lite.task`) is downloaded automatically into `backend/models/` on first run.

---

## License

MIT (add your license as needed).
