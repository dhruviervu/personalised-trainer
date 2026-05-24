import { useEffect, useRef } from 'react';
import { drawSkeleton } from '../utils/skeleton';

/**
 * Pure canvas component that renders the pose skeleton from landmarks.
 */
export default function SkeletonOverlay({ landmarks, width, height }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !width || !height) {
      return;
    }

    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);
    drawSkeleton(ctx, landmarks, width, height);
  }, [landmarks, width, height]);

  return (
    <canvas
      ref={canvasRef}
      className="skeleton-overlay"
      width={width}
      height={height}
      aria-hidden="true"
    />
  );
}
