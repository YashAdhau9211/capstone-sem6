import React from 'react';

interface NodeTooltipProps {
  nodeId: string;
  statistics?: {
    mean?: number;
    std?: number;
    min?: number;
    max?: number;
    count?: number;
  };
  position: { x: number; y: number };
}

export const NodeTooltip: React.FC<NodeTooltipProps> = ({ nodeId, statistics, position }) => {
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
        minWidth: '200px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
      }}
    >
      <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>{nodeId}</div>
      {statistics ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {statistics.mean !== undefined && (
            <div>
              <span style={{ color: '#aaa' }}>Mean:</span>{' '}
              <span style={{ fontWeight: 'bold' }}>{statistics.mean.toFixed(3)}</span>
            </div>
          )}
          {statistics.std !== undefined && (
            <div>
              <span style={{ color: '#aaa' }}>Std Dev:</span>{' '}
              <span style={{ fontWeight: 'bold' }}>{statistics.std.toFixed(3)}</span>
            </div>
          )}
          {statistics.min !== undefined && (
            <div>
              <span style={{ color: '#aaa' }}>Min:</span>{' '}
              <span style={{ fontWeight: 'bold' }}>{statistics.min.toFixed(3)}</span>
            </div>
          )}
          {statistics.max !== undefined && (
            <div>
              <span style={{ color: '#aaa' }}>Max:</span>{' '}
              <span style={{ fontWeight: 'bold' }}>{statistics.max.toFixed(3)}</span>
            </div>
          )}
          {statistics.count !== undefined && (
            <div>
              <span style={{ color: '#aaa' }}>Count:</span>{' '}
              <span style={{ fontWeight: 'bold' }}>{statistics.count}</span>
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: '#aaa', fontStyle: 'italic' }}>No statistics available</div>
      )}
    </div>
  );
};
