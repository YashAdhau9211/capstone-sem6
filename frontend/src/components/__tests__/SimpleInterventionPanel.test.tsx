import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SimpleInterventionPanel } from '../SimpleInterventionPanel';
import type { CausalDAG } from '../../types';

describe('SimpleInterventionPanel', () => {
  const mockDAG: CausalDAG = {
    dag_id: 'test-dag-1',
    station_id: 'furnace-01',
    version: 1,
    nodes: ['temperature', 'pressure', 'flow_rate'],
    edges: [],
    algorithm: 'DirectLiNGAM',
    created_at: '2024-01-01T00:00:00Z',
    created_by: 'test-user',
    metadata: {},
  };

  const mockFactualValues = {
    temperature: 100,
    pressure: 50,
    flow_rate: 25,
  };

  it('renders without DAG and shows message', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={null}
        factualValues={{}}
        interventions={{}}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText('Set Interventions')).toBeInTheDocument();
    expect(screen.getByText(/Select a station to begin/i)).toBeInTheDocument();
  });

  it('renders with DAG and shows add intervention controls', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{}}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText('Add New Intervention')).toBeInTheDocument();
    expect(screen.getByText(/Select a variable to change/i)).toBeInTheDocument();
  });

  it('displays natural language description when enabled', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{}}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
        showNaturalLanguage={true}
      />
    );

    expect(screen.getByText(/What you're testing:/i)).toBeInTheDocument();
  });

  it('allows adding an intervention', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{}}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'temperature' } });

    const addButton = screen.getByText('Add');
    fireEvent.click(addButton);

    expect(onInterventionChange).toHaveBeenCalledWith('temperature', 100);
  });

  it('displays active interventions', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText(/Active Interventions \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText('temperature')).toBeInTheDocument();
  });

  it('shows current value, new value, and change percentage', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText('Current Value')).toBeInTheDocument();
    expect(screen.getByText('New Value')).toBeInTheDocument();
    expect(screen.getByText('Change')).toBeInTheDocument();
    expect(screen.getByText('+20.0%')).toBeInTheDocument();
  });

  it('allows removing an intervention', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    const removeButton = screen.getByText('Remove');
    fireEvent.click(removeButton);

    expect(onInterventionChange).toHaveBeenCalledWith('temperature', null);
  });

  it('allows clearing all interventions', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120, pressure: 60 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(onClearAll).toHaveBeenCalled();
  });

  it('supports different input modes', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText('Slider')).toBeInTheDocument();
    expect(screen.getByText('Percentage')).toBeInTheDocument();
    expect(screen.getByText('Direct Input')).toBeInTheDocument();
  });

  it('switches between input modes', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
      />
    );

    const percentageButton = screen.getByText('Percentage');
    fireEvent.click(percentageButton);

    expect(screen.getByText(/Adjust by percentage:/i)).toBeInTheDocument();
  });

  it('generates natural language description for interventions', () => {
    const onInterventionChange = vi.fn();
    const onClearAll = vi.fn();

    render(
      <SimpleInterventionPanel
        dag={mockDAG}
        factualValues={mockFactualValues}
        interventions={{ temperature: 120 }}
        onInterventionChange={onInterventionChange}
        onClearAll={onClearAll}
        showNaturalLanguage={true}
      />
    );

    expect(screen.getByText(/temperature increases by 20%/i)).toBeInTheDocument();
  });
});
