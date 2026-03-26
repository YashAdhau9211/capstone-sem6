import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnalysisWizard } from '../AnalysisWizard';
import type { CausalDAG } from '../../types';

describe('AnalysisWizard', () => {
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

  const mockFactualValues = {
    temperature: 100,
    pressure: 50,
    flow_rate: 25,
    energy: 1200,
    yield: 0.95,
  };

  it('renders template selection screen', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    expect(screen.getByText('Choose an Analysis Template')).toBeInTheDocument();
    expect(screen.getByText('Energy Optimization')).toBeInTheDocument();
    expect(screen.getByText('Yield Improvement')).toBeInTheDocument();
    expect(screen.getByText('What-If Simulation')).toBeInTheDocument();
    expect(screen.getByText('Root Cause Analysis')).toBeInTheDocument();
    expect(screen.getByText('Discover Relationships')).toBeInTheDocument();
  });

  it('displays template descriptions', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    expect(
      screen.getByText(/Find ways to reduce energy consumption while maintaining quality/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Identify factors that can increase production yield/i)
    ).toBeInTheDocument();
  });

  it('allows selecting a template', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const energyTemplate = screen.getByText('Energy Optimization');
    fireEvent.click(energyTemplate);

    expect(screen.getByText('Select Energy Variable')).toBeInTheDocument();
    expect(screen.getByText(/Step 1 of 3/i)).toBeInTheDocument();
  });

  it('shows progress bar in wizard', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('What-If Simulation');
    fireEvent.click(template);

    expect(screen.getByText(/Step 1 of 3/i)).toBeInTheDocument();
  });

  it('provides natural language guidance for each step', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('Energy Optimization');
    fireEvent.click(template);

    expect(screen.getByText(/Tip:/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Look for variables like "power_consumption", "energy_usage", or "electricity_kwh"/i
      )
    ).toBeInTheDocument();
  });

  it('allows navigating back to template selection', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('Energy Optimization');
    fireEvent.click(template);

    const backButton = screen.getByText('← Back to Templates');
    fireEvent.click(backButton);

    expect(screen.getByText('Choose an Analysis Template')).toBeInTheDocument();
  });

  it('calls onCancel when cancel button is clicked', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  it('shows variable selector in first step', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('What-If Simulation');
    fireEvent.click(template);

    expect(screen.getByText('Select Variables to Change')).toBeInTheDocument();
    expect(screen.getByText('Select Variables')).toBeInTheDocument();
  });

  it('disables next button when no variables selected', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('What-If Simulation');
    fireEvent.click(template);

    const nextButton = screen.getByText('Next →');
    expect(nextButton).toBeDisabled();
  });

  it('displays complete button on last step', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('Root Cause Analysis');
    fireEvent.click(template);

    // Select a variable
    const checkbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(checkbox);

    // Navigate to last step
    const nextButton = screen.getByText('Next →');
    fireEvent.click(nextButton);

    expect(screen.getByText('Complete ✓')).toBeInTheDocument();
  });

  it('calls onComplete with configuration when wizard is completed', () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();

    render(
      <AnalysisWizard
        dag={mockDAG}
        factualValues={mockFactualValues}
        onComplete={onComplete}
        onCancel={onCancel}
      />
    );

    const template = screen.getByText('Root Cause Analysis');
    fireEvent.click(template);

    // Select a variable
    const checkbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(checkbox);

    // Navigate to last step
    const nextButton = screen.getByText('Next →');
    fireEvent.click(nextButton);

    // Complete wizard
    const completeButton = screen.getByText('Complete ✓');
    fireEvent.click(completeButton);

    expect(onComplete).toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        template: 'root-cause-analysis',
        variables: expect.any(Array),
      })
    );
  });
});
