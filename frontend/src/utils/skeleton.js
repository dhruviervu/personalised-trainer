/**
 * MediaPipe Pose skeleton connections (35 pairs between 33 landmarks).
 * Mirrors mediapipe.solutions.pose.POSE_CONNECTIONS.
 */
export const CONNECTIONS = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 7],
  [0, 4],
  [4, 5],
  [5, 6],
  [6, 8],
  [9, 10],
  [11, 12],
  [11, 13],
  [13, 15],
  [15, 17],
  [15, 19],
  [15, 21],
  [17, 19],
  [12, 14],
  [14, 16],
  [16, 18],
  [16, 20],
  [16, 22],
  [18, 20],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [27, 29],
  [27, 31],
  [29, 31],
  [24, 26],
  [26, 28],
  [28, 30],
  [28, 32],
  [30, 32],
];

const VISIBILITY_THRESHOLD = 0.5;
const BONE_COLOR = '#00ff88';
const BONE_WIDTH = 2;
const JOINT_RADIUS = 4;
const JOINT_FILL = '#ffffff';
const JOINT_STROKE = '#00ff88';

/**
 * Draw pose skeleton on a 2D canvas context.
 * Landmarks are normalised 0–1; scaled to canvas pixel dimensions.
 */
export function drawSkeleton(ctx, landmarks, canvasWidth, canvasHeight) {
  if (!landmarks || landmarks.length === 0) {
    return;
  }

  const isVisible = (index) => {
    const lm = landmarks[index];
    return lm && (lm.visibility ?? 1) > VISIBILITY_THRESHOLD;
  };

  const toPixel = (lm) => ({
    x: lm.x * canvasWidth,
    y: lm.y * canvasHeight,
  });

  ctx.lineWidth = BONE_WIDTH;
  ctx.strokeStyle = BONE_COLOR;

  for (const [startIdx, endIdx] of CONNECTIONS) {
    if (!isVisible(startIdx) || !isVisible(endIdx)) {
      continue;
    }

    const start = toPixel(landmarks[startIdx]);
    const end = toPixel(landmarks[endIdx]);

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.stroke();
  }

  for (let i = 0; i < landmarks.length; i += 1) {
    if (!isVisible(i)) {
      continue;
    }

    const { x, y } = toPixel(landmarks[i]);

    ctx.beginPath();
    ctx.arc(x, y, JOINT_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = JOINT_FILL;
    ctx.strokeStyle = JOINT_STROKE;
    ctx.lineWidth = BONE_WIDTH;
    ctx.fill();
    ctx.stroke();
  }
}
