import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExportDialog } from '../ExportDialog';
import type { CounterfactualResponse } from '../../types';

describe('ExportDialog', () => {
  const mockResult: CounterfactualResponse = {
    factual: { temperature: 100, pressure: 50, yield: 0.95 },
    counterfactual: { temperature: 120, pressure: 50, yield: 0.97 },
    difference: { temperature: 20, pressure: 0, yield: 0.02 },
    confidence_intervals: {
      temperature: [18, 22],
      pressure: [-1, 1],
      yield: [0.015, 0.025],
    },
  };

  const mockData = {
    stationId: 'furnace-01',
    interventions: { temperature: 120 },
    result: mockResult,
    analysisType: 'Counterfactual Simulation',
  };

  it('does not render when isOpen is false', () => {
    const onClose = vi.fn();

    const { container } = render(<ExportDialog isOpen={false} onClose={onClose} data={mockData} />);

    expect(container.firstChild).toBeNull();
  });

  it('renders when isOpen is true', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    expect(screen.getByText('Export Analysis Results')).toBeInTheDocument();
  });

  it('displays format selection options', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    expect(screen.getByText('PDF Report')).toBeInTheDocument();
    expect(screen.getByText('Excel/CSV')).toBeInTheDocument();
  });

  it('allows switching between PDF and Excel formats', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    const excelRadio = screen.getByLabelText(/Excel\/CSV/i);
    fireEvent.click(excelRadio);

    const exportButton = screen.getByText(/Export as EXCEL/i);
    expect(exportButton).toBeInTheDocument();
  });

  it('shows PDF-specific options when PDF is selected', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    expect(screen.getByText(/Include charts and visualizations/i)).toBeInTheDocument();
    expect(screen.getByText(/Include raw data tables/i)).toBeInTheDocument();
  });

  it('displays natural language description of export', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    expect(screen.getByText(/What will be exported:/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        /A formatted report with your analysis results, interventions, and predicted outcomes/i
      )
    ).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when clicking outside dialog', () => {
    const onClose = vi.fn();

    const { container } = render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    const backdrop = container.firstChild as HTMLElement;
    fireEvent.click(backdrop);

    expect(onClose).toHaveBeenCalled();
  });

  it('does not close when clicking inside dialog', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    const dialog = screen.getByText('Export Analysis Results').parentElement;
    if (dialog) {
      fireEvent.click(dialog);
    }

    expect(onClose).not.toHaveBeenCalled();
  });

  it('shows export button with correct format', () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    expect(screen.getByText(/Export as PDF/i)).toBeInTheDocument();
  });

  it('disables buttons while exporting', async () => {
    const onClose = vi.fn();

    render(<ExportDialog isOpen={true} onClose={onClose} data={mockData} />);

    const exportButton = screen.getByText(/Export as PDF/i);
    fireEvent.click(exportButton);

    // Button should show "Exporting..." state briefly
    expect(screen.getByText(/Exporting.../i)).toBeInTheDocument();
  });

  it('handles export with minimal data', () => {
    const onClose = vi.fn();
    const minimalData = {
      stationId: 'test-station',
    };

    render(<ExportDialog isOpen={true} onClose={onClose} data={minimalData} />);

    expect(screen.getByText('Export Analysis Results')).toBeInTheDocument();
  });
});
