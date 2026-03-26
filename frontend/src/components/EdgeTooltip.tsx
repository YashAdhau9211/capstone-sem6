import React from 'react';

interface EdgeTooltipProps {
  source: string;
  target: string;
  coefficient: number;
  confidence: number;
  edgeType: 'linear' | 'nonlinear';
  position: { x: number; y: number };
}

export const EdgeTooltip: React.FC<EdgeTooltipProps> = ({
  source,
  target,
  coefficient,
  confidence,
  edgeType,
  position,
}) => {
  const confidencePercent = (confidence * 100).toFixed(1);
  const confidenceColor = confidence > 0.8 ? '#4CAF50' : confidence > 0.5 ? '#FFC107' : '#F44336';

  return (
    <div
      style={{
        position: 'fixed',
        left: position.x + 10,
        top: position.y + 10,
        background: 'rgba(0, 0, 0, 0.9)',
        color: 'white',
        padding: '12px',
        borderRadius: '6px',
        fontSize: '12px',
        zIndex: 1000,
        pointerEvents: 'none',
        minWidth: '220px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
      }}
    >
      <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>
        {source} → {target}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div>
          <span style={{ color: '#aaa' }}>Causal Coefficient:</span>{' '}
          <span style={{ fontWeight: 'bold', fontSize: '13px' }}>{coefficient.toFixed(4)}</span>
        </div>
        <div>
          <span style={{ color: '#aaa' }}>Confidence Score:</span>{' '}
          <span style={{ fontWeight: 'bold', color: confidenceColor, fontSize: '13px' }}>
            {confidencePercent}%
          </span>
        </div>
        <div>
          <span style={{ color: '#aaa' }}>Edge Type:</span>{' '}
          <span
            style={{
              fontWeight: 'bold',
              textTransform: 'capitalize',
              color: edgeType === 'linear' ? '#2196F3' : '#9C27B0',
            }}
          >
            {edgeType}
          </span>
        </div>
      </div>
      <div
        style={{
          marginTop: '8px',
          paddingTop: '8px',
          borderTop: '1px solid rgba(255, 255, 255, 0.2)',
          fontSize: '11px',
          color: '#bbb',
        }}
      >
        {coefficient > 0
          ? `Positive causal effect: increasing ${source} increases ${target}`
          : `Negative causal effect: increasing ${source} decreases ${target}`}
      </div>
    </div>
  );
};
