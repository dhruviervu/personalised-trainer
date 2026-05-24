const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "https://personalised-trainer.onrender.com"
const WS_URL = BACKEND_URL.replace("https", "wss").replace("http", "ws")

export { BACKEND_URL, WS_URL }
