import React, { useState } from 'react';
import { api } from '../services/api';

interface ImportExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  stationId: string;
  onImportSuccess: () => void;
}

export const ImportExportDialog: React.FC<ImportExportDialogProps> = ({
  isOpen,
  onClose,
  stationId,
  onImportSuccess,
}) => {
  const [mode, setMode] = useState<'import' | 'export'>('export');
  const [format, setFormat] = useState<'dot' | 'graphml'>('dot');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleExport = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(
        `http://localhost:8000/api/v1/dags/${stationId}/export?format=${format}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const content = await response.text();
      const blob = new Blob([content], {
        type: format === 'dot' ? 'text/vnd.graphviz' : 'application/xml',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${stationId}_dag.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setSuccess(`DAG exported successfully as ${format.toUpperCase()}`);
    } catch (err: any) {
      setError(err.message || 'Failed to export DAG');
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!file) {
      setError('Please select a file to import');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const formData = new FormData();
      formData.append('file', file);
      formData.append('format', format);
      formData.append('created_by', 'current_user'); // TODO: Get from auth context

      const response = await fetch(
        `http://localhost:8000/api/v1/dags/${stationId}/import`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Import failed');
      }

      setSuccess(`DAG imported successfully from ${format.toUpperCase()}`);
      setTimeout(() => {
        onImportSuccess();
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to import DAG');
    } finally {
      setLoading(false);
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
          width: '500px',
          maxWidth: '90%',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: '0 0 20px 0' }}>Import/Export DAG</h2>

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

        {success && (
          <div
            style={{
              padding: '10px',
              background: '#e8f5e9',
              color: '#2e7d32',
              borderRadius: '4px',
              marginBottom: '15px',
              fontSize: '14px',
            }}
          >
            {success}
          </div>
        )}

        {/* Mode Selection */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Mode
          </label>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => setMode('export')}
              style={{
                flex: 1,
                padding: '10px',
                borderRadius: '4px',
                border: mode === 'export' ? '2px solid #4CAF50' : '1px solid #ddd',
                background: mode === 'export' ? '#e8f5e9' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: mode === 'export' ? 'bold' : 'normal',
              }}
            >
              Export
            </button>
            <button
              onClick={() => setMode('import')}
              style={{
                flex: 1,
                padding: '10px',
                borderRadius: '4px',
                border: mode === 'import' ? '2px solid #4CAF50' : '1px solid #ddd',
                background: mode === 'import' ? '#e8f5e9' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: mode === 'import' ? 'bold' : 'normal',
              }}
            >
              Import
            </button>
          </div>
        </div>

        {/* Format Selection */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Format
          </label>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => setFormat('dot')}
              style={{
                flex: 1,
                padding: '10px',
                borderRadius: '4px',
                border: format === 'dot' ? '2px solid #4CAF50' : '1px solid #ddd',
                background: format === 'dot' ? '#e8f5e9' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: format === 'dot' ? 'bold' : 'normal',
              }}
            >
              DOT (Graphviz)
            </button>
            <button
              onClick={() => setFormat('graphml')}
              style={{
                flex: 1,
                padding: '10px',
                borderRadius: '4px',
                border: format === 'graphml' ? '2px solid #4CAF50' : '1px solid #ddd',
                background: format === 'graphml' ? '#e8f5e9' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: format === 'graphml' ? 'bold' : 'normal',
              }}
            >
              GraphML
            </button>
          </div>
        </div>

        {/* Import File Selection */}
        {mode === 'import' && (
          <div style={{ marginBottom: '20px' }}>
            <label
              htmlFor="import-file"
              style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}
            >
              Select File
            </label>
            <input
              id="import-file"
              type="file"
              accept={format === 'dot' ? '.dot' : '.graphml,.xml'}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '14px',
              }}
              disabled={loading}
            />
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #ddd',
              background: 'white',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
            }}
          >
            Cancel
          </button>
          <button
            onClick={mode === 'export' ? handleExport : handleImport}
            disabled={loading || (mode === 'import' && !file)}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              background:
                loading || (mode === 'import' && !file) ? '#ccc' : '#4CAF50',
              color: 'white',
              cursor:
                loading || (mode === 'import' && !file) ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
            }}
          >
            {loading ? 'Processing...' : mode === 'export' ? 'Export' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
};
