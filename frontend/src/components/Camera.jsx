import { useCallback, useEffect, useRef, useState } from 'react';
import { drawSkeleton } from '../utils/skeleton';

const FRAME_INTERVAL_MS = 100;
const JPEG_QUALITY = 0.7;

/**
 * Webcam capture, frame streaming, and skeleton overlay on live video.
 */
export default function Camera({ sendFrame, landmarks, connectionStatus, configReady }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const captureCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const [cameraError, setCameraError] = useState(null);

  const syncCanvasSize = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      return;
    }

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;

    canvas.width = width;
    canvas.height = height;
  }, []);

  // Draw skeleton whenever landmarks update from the backend
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (landmarks && landmarks.length > 0) {
      drawSkeleton(ctx, landmarks, canvas.width, canvas.height);
    }
  }, [landmarks]);

  // Start webcam
  useEffect(() => {
    let cancelled = false;

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'user',
            width: { ideal: 640 },
            height: { ideal: 480 },
          },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play();
          syncCanvasSize();
        }
      } catch (err) {
        console.error('Camera access failed:', err);
        setCameraError(
          'Could not access camera. Please allow camera permissions and reload.'
        );
      }
    }

    startCamera();

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, [syncCanvasSize]);

  // Capture and send frames at ~10 fps when connected
  useEffect(() => {
    if (connectionStatus !== 'connected' || !sendFrame || !configReady) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    if (!captureCanvasRef.current) {
      captureCanvasRef.current = document.createElement('canvas');
    }

    intervalRef.current = window.setInterval(() => {
      const video = videoRef.current;
      const captureCanvas = captureCanvasRef.current;
      if (!video || video.readyState < 2 || !captureCanvas) {
        return;
      }

      const width = video.videoWidth;
      const height = video.videoHeight;
      if (!width || !height) {
        return;
      }

      captureCanvas.width = width;
      captureCanvas.height = height;

      const ctx = captureCanvas.getContext('2d');
      ctx.drawImage(video, 0, 0, width, height);

      const dataUrl = captureCanvas.toDataURL('image/jpeg', JPEG_QUALITY);
      const base64 = dataUrl.replace(/^data:image\/jpeg;base64,/, '');
      sendFrame(base64);
    }, FRAME_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [connectionStatus, sendFrame, configReady]);

  const handleVideoMetadata = () => {
    syncCanvasSize();
  };

  if (cameraError) {
    return <div className="camera-error">{cameraError}</div>;
  }

  return (
    <div className="camera-container">
      <div className="camera-mirror">
        <video
          ref={videoRef}
          className="camera-video"
          playsInline
          muted
          onLoadedMetadata={handleVideoMetadata}
        />
        <canvas ref={canvasRef} className="camera-overlay" />
      </div>
    </div>
  );
}
