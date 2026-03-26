import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VariableSelector } from '../VariableSelector';
import type { CausalDAG } from '../../types';

describe('VariableSelector', () => {
  const mockDAG: CausalDAG = {
    dag_id: 'test-dag-1',
    station_id: 'furnace-01',
    version: 1,
    nodes: ['temperature', 'pressure', 'flow_rate', 'energy', 'yield'],
    edges: [],
    algorithm: 'DirectLiNGAM',
    created_at: '2024-01-01T00:00:00Z',
    created_by: 'test-user',
    metadata: {},
  };

  it('renders without DAG and shows message', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector dag={null} selectedVariables={[]} onSelectionChange={onSelectionChange} />
    );

    expect(screen.getByText('Select Variables')).toBeInTheDocument();
    expect(screen.getByText(/No causal model available/i)).toBeInTheDocument();
  });

  it('renders with DAG in checkbox mode', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={[]}
        onSelectionChange={onSelectionChange}
        mode="checkbox"
      />
    );

    expect(screen.getByText('Select Variables')).toBeInTheDocument();
    expect(screen.getByText('temperature')).toBeInTheDocument();
    expect(screen.getByText('pressure')).toBeInTheDocument();
    expect(screen.getByText('flow_rate')).toBeInTheDocument();
  });

  it('allows selecting variables via checkbox', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={[]}
        onSelectionChange={onSelectionChange}
        mode="checkbox"
      />
    );

    const checkbox = screen.getByLabelText(/temperature/i);
    fireEvent.click(checkbox);

    expect(onSelectionChange).toHaveBeenCalledWith(['temperature']);
  });

  it('allows deselecting variables via checkbox', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={['temperature']}
        onSelectionChange={onSelectionChange}
        mode="checkbox"
      />
    );

    // Find the remove button for the selected variable
    const removeButton = screen.getByTitle('Remove');
    fireEvent.click(removeButton);

    expect(onSelectionChange).toHaveBeenCalledWith([]);
  });

  it('handles select all button', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={[]}
        onSelectionChange={onSelectionChange}
      />
    );

    const selectAllButton = screen.getByText('Select All');
    fireEvent.click(selectAllButton);

    expect(onSelectionChange).toHaveBeenCalledWith(mockDAG.nodes);
  });

  it('handles clear all button', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={['temperature', 'pressure']}
        onSelectionChange={onSelectionChange}
      />
    );

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(onSelectionChange).toHaveBeenCalledWith([]);
  });

  it('filters variables based on search term', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={[]}
        onSelectionChange={onSelectionChange}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search variables...');
    fireEvent.change(searchInput, { target: { value: 'temp' } });

    expect(screen.getByText('temperature')).toBeInTheDocument();
    expect(screen.queryByText('pressure')).not.toBeInTheDocument();
  });

  it('displays selected variables count', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={['temperature', 'pressure']}
        onSelectionChange={onSelectionChange}
      />
    );

    expect(screen.getByText(/Selected Variables \(2\)/i)).toBeInTheDocument();
  });

  it('allows removing selected variables', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={['temperature', 'pressure']}
        onSelectionChange={onSelectionChange}
      />
    );

    const removeButtons = screen.getAllByTitle('Remove');
    fireEvent.click(removeButtons[0]);

    expect(onSelectionChange).toHaveBeenCalledWith(['pressure']);
  });

  it('renders in drag-and-drop mode', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={[]}
        onSelectionChange={onSelectionChange}
        mode="drag-drop"
      />
    );

    expect(screen.getByText('Available Variables')).toBeInTheDocument();
    expect(screen.getByText(/Drag variables here to select them/i)).toBeInTheDocument();
  });

  it('uses custom title and description', () => {
    const onSelectionChange = vi.fn();
    render(
      <VariableSelector
        dag={mockDAG}
        selectedVariables={[]}
        onSelectionChange={onSelectionChange}
        title="Custom Title"
        description="Custom description"
      />
    );

    expect(screen.getByText('Custom Title')).toBeInTheDocument();
    expect(screen.getByText('Custom description')).toBeInTheDocument();
  });
});
