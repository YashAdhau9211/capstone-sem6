import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface DAGVersion {
  dag_id: string;
  version: number;
  algorithm: string;
  created_at: string;
  created_by: string;
}

interface VersionHistoryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  stationId: string;
  currentVersion: number;
  onLoadVersion: (version: number) => Promise<void>;
}

export const VersionHistoryDialog: React.FC<VersionHistoryDialogProps> = ({
  isOpen,
  onClose,
  stationId,
  currentVersion,
  onLoadVersion,
}) => {
  const [versions, setVersions] = useState<DAGVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingVersion, setLoadingVersion] = useState<number | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadVersions();
    }
  }, [isOpen, stationId]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.dags.listVersions(stationId);
      setVersions(response.versions.slice(0, 50)); // Limit to 50 versions
    } catch (err: any) {
      setError(err.message || 'Failed to load version history');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadVersion = async (version: number) => {
    try {
      setLoadingVersion(version);
      await onLoadVersion(version);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to load version');
    } finally {
      setLoadingVersion(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'white',
          borderRadius: '8px',
          padding: '24px',
          width: '700px',
          maxWidth: '90%',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: '0 0 20px 0' }}>Version History</h2>

        {error && (
          <div
            style={{
              padding: '10px',
              background: '#ffebee',
              color: '#c62828',
              borderRadius: '4px',
              marginBottom: '15px',
              fontSize: '14px',
            }}
          >
            {error}
          </div>
        )}

        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>Loading...</div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {versions.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
                No version history available
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ddd' }}>
                    <th style={{ padding: '10px', textAlign: 'left' }}>Version</th>
                    <th style={{ padding: '10px', textAlign: 'left' }}>Algorithm</th>
                    <th style={{ padding: '10px', textAlign: 'left' }}>Created By</th>
                    <th style={{ padding: '10px', textAlign: 'left' }}>Created At</th>
                    <th style={{ padding: '10px', textAlign: 'center' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((version) => (
                    <tr
                      key={version.version}
                      style={{
                        borderBottom: '1px solid #eee',
                        background: version.version === currentVersion ? '#e3f2fd' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '10px' }}>
                        <strong>v{version.version}</strong>
                        {version.version === currentVersion && (
                          <span
                            style={{
                              marginLeft: '8px',
                              padding: '2px 6px',
                              background: '#4CAF50',
                              color: 'white',
                              borderRadius: '3px',
                              fontSize: '11px',
                            }}
                          >
                            CURRENT
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '10px' }}>{version.algorithm}</td>
                      <td style={{ padding: '10px' }}>{version.created_by}</td>
                      <td style={{ padding: '10px' }}>
                        {new Date(version.created_at).toLocaleString()}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'center' }}>
                        {version.version !== currentVersion && (
                          <button
                            onClick={() => handleLoadVersion(version.version)}
                            disabled={loadingVersion !== null}
                            style={{
                              padding: '4px 12px',
                              borderRadius: '4px',
                              border: '1px solid #4CAF50',
                              background: 'white',
                              color: '#4CAF50',
                              cursor: loadingVersion !== null ? 'not-allowed' : 'pointer',
                              fontSize: '12px',
                            }}
                          >
                            {loadingVersion === version.version ? 'Loading...' : 'Load'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #ddd',
              background: 'white',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
