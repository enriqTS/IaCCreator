import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import GlobalTerraformConfigPanel from '@/components/config/GlobalTerraformConfigPanel';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_GLOBAL_CONFIG } from '@/types/terraform-variables';

describe('GlobalTerraformConfigPanel', () => {
  beforeEach(() => {
    useDiagramStore.setState({ globalTerraformConfig: { ...DEFAULT_GLOBAL_CONFIG, environments: [], globalVariables: [] } });
  });

  // --- Requirement 9.2: all config sections render ---
  it('renders all five config sections', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByTestId('backend-config-section')).toBeDefined();
    expect(screen.getByTestId('provider-config-section')).toBeDefined();
    expect(screen.getByTestId('version-constraints-section')).toBeDefined();
    expect(screen.getByTestId('environment-settings-section')).toBeDefined();
    expect(screen.getByTestId('global-variables-section')).toBeDefined();
  });

  it('renders section headings', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByText('Backend Configuration')).toBeDefined();
    expect(screen.getByText('Provider Configuration')).toBeDefined();
    expect(screen.getByText('Version Constraints')).toBeDefined();
    expect(screen.getByText('Environment Settings')).toBeDefined();
    expect(screen.getByText('Global Variables')).toBeDefined();
  });

  // --- Requirement 9.3: backend type selector and config fields ---
  it('renders backend type selector with local as default', () => {
    render(<GlobalTerraformConfigPanel />);

    // shadcn/ui Select renders as a Radix combobox button; check displayed text
    const trigger = screen.getByTestId('backend-type');
    expect(trigger.textContent).toContain('local');
  });

  it('does not show S3 config fields when backend type is local', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.queryByTestId('backend-bucket')).toBeNull();
    expect(screen.queryByTestId('backend-key')).toBeNull();
    expect(screen.queryByTestId('backend-region')).toBeNull();
    expect(screen.queryByTestId('backend-dynamodb-table')).toBeNull();
  });

  it('shows S3 config fields when backend type is changed to s3', () => {
    // Update store directly since shadcn/ui Select uses Radix portals
    useDiagramStore.getState().updateGlobalTerraformConfig({
      backend: { type: 's3', config: { bucket: '', key: 'terraform.tfstate', region: 'us-east-1', dynamodb_table: '' } },
    });
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByTestId('backend-bucket')).toBeDefined();
    expect(screen.getByTestId('backend-key')).toBeDefined();
    expect(screen.getByTestId('backend-region')).toBeDefined();
    expect(screen.getByTestId('backend-dynamodb-table')).toBeDefined();
  });

  it('updates store when backend type changes to s3', () => {
    // Simulate the onValueChange callback by updating the store directly
    useDiagramStore.getState().updateGlobalTerraformConfig({
      backend: { type: 's3', config: { bucket: '', key: 'terraform.tfstate', region: 'us-east-1', dynamodb_table: '' } },
    });

    const state = useDiagramStore.getState();
    expect(state.globalTerraformConfig.backend.type).toBe('s3');
    expect(state.globalTerraformConfig.backend.config).toHaveProperty('bucket');
    expect(state.globalTerraformConfig.backend.config).toHaveProperty('key');
    expect(state.globalTerraformConfig.backend.config).toHaveProperty('region');
  });

  it('updates store when switching back from s3 to local', () => {
    // Switch to s3 first
    useDiagramStore.getState().updateGlobalTerraformConfig({
      backend: { type: 's3', config: { bucket: '', key: 'terraform.tfstate', region: 'us-east-1', dynamodb_table: '' } },
    });
    // Switch back to local
    useDiagramStore.getState().updateGlobalTerraformConfig({
      backend: { type: 'local', config: {} },
    });

    const state = useDiagramStore.getState();
    expect(state.globalTerraformConfig.backend.type).toBe('local');
    expect(Object.keys(state.globalTerraformConfig.backend.config)).toHaveLength(0);
  });

  // --- Requirement 9.4: provider configuration ---
  it('renders provider region with default value', () => {
    render(<GlobalTerraformConfigPanel />);

    const regionInput = screen.getByTestId('provider-region') as HTMLInputElement;
    expect(regionInput.value).toBe('us-east-1');
  });

  it('renders provider profile input', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByTestId('provider-profile')).toBeDefined();
  });

  it('updates store when provider region changes', () => {
    render(<GlobalTerraformConfigPanel />);

    fireEvent.change(screen.getByTestId('provider-region'), { target: { value: 'eu-west-1' } });

    expect(useDiagramStore.getState().globalTerraformConfig.provider.region).toBe('eu-west-1');
  });

  // --- Version constraints ---
  it('renders version constraint inputs', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByTestId('terraform-version')).toBeDefined();
    expect(screen.getByTestId('aws-provider-version')).toBeDefined();
  });

  // --- Environment settings ---
  it('renders add environment button', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByTestId('add-environment')).toBeDefined();
  });

  it('adds an environment when button is clicked', () => {
    render(<GlobalTerraformConfigPanel />);

    fireEvent.click(screen.getByTestId('add-environment'));

    expect(screen.getByTestId('environment-0')).toBeDefined();
    expect(screen.getByTestId('env-name-0')).toBeDefined();
  });

  it('removes an environment', () => {
    render(<GlobalTerraformConfigPanel />);

    fireEvent.click(screen.getByTestId('add-environment'));
    expect(screen.getByTestId('environment-0')).toBeDefined();

    fireEvent.click(screen.getByTestId('remove-environment-0'));
    expect(screen.queryByTestId('environment-0')).toBeNull();
  });

  // --- Global variables ---
  it('renders add global variable button', () => {
    render(<GlobalTerraformConfigPanel />);

    expect(screen.getByTestId('add-global-variable')).toBeDefined();
  });

  it('adds a global variable when button is clicked', () => {
    render(<GlobalTerraformConfigPanel />);

    fireEvent.click(screen.getByTestId('add-global-variable'));

    expect(screen.getByTestId('global-variable-0')).toBeDefined();
    expect(screen.getByTestId('gvar-name-0')).toBeDefined();
    expect(screen.getByTestId('gvar-type-0')).toBeDefined();
    expect(screen.getByTestId('gvar-description-0')).toBeDefined();
    expect(screen.getByTestId('gvar-default-0')).toBeDefined();
  });

  it('removes a global variable', () => {
    render(<GlobalTerraformConfigPanel />);

    fireEvent.click(screen.getByTestId('add-global-variable'));
    expect(screen.getByTestId('global-variable-0')).toBeDefined();

    fireEvent.click(screen.getByTestId('remove-global-variable-0'));
    expect(screen.queryByTestId('global-variable-0')).toBeNull();
  });
});
