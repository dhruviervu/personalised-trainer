/**
 * Displays current set rep count and session total.
 */
export default function RepCounter({ setReps, totalReps }) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 60,
        right: 16,
        zIndex: 90,
        background: 'rgba(20,20,20,0.9)',
        border: '1px solid #2a2a2a',
        borderRadius: 12,
        padding: '12px 16px',
        minWidth: 130,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 72, lineHeight: 1, fontWeight: 800, color: '#00ff88' }}>
        {setReps ?? 0}
      </div>
      <div style={{ color: '#888', fontSize: 12, textTransform: 'lowercase' }}>reps</div>
      <div style={{ color: '#777', fontSize: 11, marginTop: 4 }}>
        Session total: {totalReps ?? 0}
      </div>
    </div>
  );
}
