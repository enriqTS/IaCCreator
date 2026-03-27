'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { COMPACT_LAYOUT_THRESHOLD } from '@/components/config/panel-constants';
import type { GlobalTerraformConfig, TerraformVariableType } from '@/types/terraform-variables';

const inputStyle: React.CSSProperties = {
  backgroundColor: '#2a2a2a',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  padding: '4px 8px',
  fontSize: '13px',
  width: '180px',
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  width: '140px',
};

const labelStyle: React.CSSProperties = {
  color: 'rgba(255,255,255,0.6)',
  fontSize: '13px',
};

const sectionHeadingStyle: React.CSSProperties = {
  color: 'rgba(255,255,255,0.9)',
  fontSize: '13px',
  fontWeight: 600,
  marginBottom: '8px',
};

const sectionStyle: React.CSSProperties = {
  marginBottom: '16px',
};

const addButtonStyle: React.CSSProperties = {
  padding: '4px 10px',
  fontSize: '12px',
  color: '#3b82f6',
  backgroundColor: 'transparent',
  border: '1px solid rgba(59,130,246,0.4)',
  borderRadius: '4px',
  cursor: 'pointer',
};

const removeButtonStyle: React.CSSProperties = {
  padding: '2px 8px',
  fontSize: '11px',
  color: '#ef4444',
  backgroundColor: 'transparent',
  border: '1px solid rgba(239,68,68,0.4)',
  borderRadius: '4px',
  cursor: 'pointer',
};

interface GlobalTerraformConfigPanelProps {
  panelHeight?: number;
}

const cardStyle: React.CSSProperties = {
  padding: '4px 0',
};

/** Renders project-level Terraform configuration: backend, provider, versions, environments, global variables. */
export default function GlobalTerraformConfigPanel({ panelHeight }: GlobalTerraformConfigPanelProps) {
  const config = useDiagramStore((s) => s.globalTerraformConfig);
  const updateConfig = useDiagramStore((s) => s.updateGlobalTerraformConfig);

  const updateBackend = (updates: Partial<GlobalTerraformConfig['backend']>) => {
    updateConfig({ backend: { ...config.backend, ...updates } });
  };

  const updateProvider = (updates: Partial<GlobalTerraformConfig['provider']>) => {
    updateConfig({ provider: { ...config.provider, ...updates } });
  };

  const updateVersionConstraints = (updates: Partial<GlobalTerraformConfig['versionConstraints']>) => {
    updateConfig({ versionConstraints: { ...config.versionConstraints, ...updates } });
  };

  const isCompact = panelHeight !== undefined && panelHeight <= COMPACT_LAYOUT_THRESHOLD;

  const containerStyle: React.CSSProperties = isCompact
    ? {
        display: 'flex',
        flexDirection: 'row',
        overflowX: 'auto',
        gap: '24px',
      }
    : {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '24px',
      };

  const sectionCardStyle: React.CSSProperties = isCompact
    ? { ...cardStyle, minWidth: '200px', flexShrink: 0 }
    : { ...cardStyle, flex: '1 1 auto', minWidth: '160px' };

  return (
    <div data-testid="global-terraform-config-panel">
      <div style={containerStyle} data-testid="config-sections-container">
        {/* Backend Configuration */}
        <div style={sectionCardStyle} data-testid="backend-config-section">
          <div style={sectionHeadingStyle}>Backend Configuration</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
              <span style={labelStyle}>Backend Type</span>
              <select
                data-testid="backend-type"
                value={config.backend.type}
                onChange={(e) => {
                  const newType = e.target.value;
                  updateBackend({ type: newType, config: newType === 's3' ? { bucket: '', key: 'terraform.tfstate', region: 'us-east-1', dynamodb_table: '' } : {} });
                }}
                style={selectStyle}
              >
                <option value="local">local</option>
                <option value="s3">s3</option>
              </select>
            </label>
            {config.backend.type === 's3' && (
              <>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                  <span style={labelStyle}>Bucket</span>
                  <input
                    data-testid="backend-bucket"
                    type="text"
                    value={config.backend.config.bucket ?? ''}
                    onChange={(e) => updateBackend({ config: { ...config.backend.config, bucket: e.target.value } })}
                    placeholder="my-tf-state"
                    style={inputStyle}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                  <span style={labelStyle}>Key</span>
                  <input
                    data-testid="backend-key"
                    type="text"
                    value={config.backend.config.key ?? ''}
                    onChange={(e) => updateBackend({ config: { ...config.backend.config, key: e.target.value } })}
                    placeholder="terraform.tfstate"
                    style={inputStyle}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                  <span style={labelStyle}>Region</span>
                  <input
                    data-testid="backend-region"
                    type="text"
                    value={config.backend.config.region ?? ''}
                    onChange={(e) => updateBackend({ config: { ...config.backend.config, region: e.target.value } })}
                    placeholder="us-east-1"
                    style={inputStyle}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                  <span style={labelStyle}>DynamoDB Table</span>
                  <input
                    data-testid="backend-dynamodb-table"
                    type="text"
                    value={config.backend.config.dynamodb_table ?? ''}
                    onChange={(e) => updateBackend({ config: { ...config.backend.config, dynamodb_table: e.target.value } })}
                    placeholder="tf-locks"
                    style={inputStyle}
                  />
                </label>
              </>
            )}
          </div>
        </div>

        {/* Provider Configuration */}
        <div style={sectionCardStyle} data-testid="provider-config-section">
          <div style={sectionHeadingStyle}>Provider Configuration</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
              <span style={labelStyle}>Region</span>
              <input
                data-testid="provider-region"
                type="text"
                value={config.provider.region}
                onChange={(e) => updateProvider({ region: e.target.value })}
                placeholder="us-east-1"
                style={inputStyle}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
              <span style={labelStyle}>Profile (optional)</span>
              <input
                data-testid="provider-profile"
                type="text"
                value={config.provider.profile ?? ''}
                onChange={(e) => updateProvider({ profile: e.target.value || undefined })}
                placeholder="default"
                style={inputStyle}
              />
            </label>
          </div>
        </div>

        {/* Version Constraints */}
        <div style={sectionCardStyle} data-testid="version-constraints-section">
          <div style={sectionHeadingStyle}>Version Constraints</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
              <span style={labelStyle}>Terraform Version</span>
              <input
                data-testid="terraform-version"
                type="text"
                value={config.versionConstraints.terraformVersion ?? ''}
                onChange={(e) => updateVersionConstraints({ terraformVersion: e.target.value || undefined })}
                placeholder=">= 1.5.0"
                style={inputStyle}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
              <span style={labelStyle}>AWS Provider Version</span>
              <input
                data-testid="aws-provider-version"
                type="text"
                value={config.versionConstraints.awsProviderVersion ?? ''}
                onChange={(e) => updateVersionConstraints({ awsProviderVersion: e.target.value || undefined })}
                placeholder="~> 5.0"
                style={inputStyle}
              />
            </label>
          </div>
        </div>

        {/* Environment Settings */}
        <EnvironmentSettings config={config} updateConfig={updateConfig} sectionCardStyle={sectionCardStyle} />

        {/* Global Variables */}
        <GlobalVariablesSection config={config} updateConfig={updateConfig} sectionCardStyle={sectionCardStyle} />
      </div>
    </div>
  );
}

function EnvironmentSettings({
  config,
  updateConfig,
  sectionCardStyle,
}: {
  config: GlobalTerraformConfig;
  updateConfig: (updates: Partial<GlobalTerraformConfig>) => void;
  sectionCardStyle: React.CSSProperties;
}) {
  const addEnvironment = () => {
    updateConfig({
      environments: [...config.environments, { name: '', variableOverrides: {} }],
    });
  };

  const removeEnvironment = (index: number) => {
    updateConfig({
      environments: config.environments.filter((_, i) => i !== index),
    });
  };

  const updateEnvironmentName = (index: number, name: string) => {
    const envs = [...config.environments];
    envs[index] = { ...envs[index], name };
    updateConfig({ environments: envs });
  };

  const updateOverride = (envIndex: number, key: string, value: string) => {
    const envs = [...config.environments];
    envs[envIndex] = {
      ...envs[envIndex],
      variableOverrides: { ...envs[envIndex].variableOverrides, [key]: value },
    };
    updateConfig({ environments: envs });
  };

  const addOverride = (envIndex: number) => {
    const envs = [...config.environments];
    const overrides = { ...envs[envIndex].variableOverrides };
    // Find a unique key name
    let keyName = 'variable';
    let counter = 1;
    while (overrides[keyName] !== undefined) {
      keyName = `variable_${counter++}`;
    }
    overrides[keyName] = '';
    envs[envIndex] = { ...envs[envIndex], variableOverrides: overrides };
    updateConfig({ environments: envs });
  };

  const removeOverride = (envIndex: number, key: string) => {
    const envs = [...config.environments];
    const overrides = { ...envs[envIndex].variableOverrides };
    delete overrides[key];
    envs[envIndex] = { ...envs[envIndex], variableOverrides: overrides };
    updateConfig({ environments: envs });
  };

  return (
    <div style={sectionCardStyle} data-testid="environment-settings-section">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <span style={sectionHeadingStyle}>Environment Settings</span>
        <button data-testid="add-environment" onClick={addEnvironment} style={addButtonStyle}>
          + Add Environment
        </button>
      </div>
      {config.environments.map((env, envIndex) => (
        <div
          key={envIndex}
          data-testid={`environment-${envIndex}`}
          style={{
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '4px',
            padding: '10px',
            marginBottom: '8px',
            backgroundColor: '#252525',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
              <span style={labelStyle}>Name</span>
              <input
                data-testid={`env-name-${envIndex}`}
                type="text"
                value={env.name}
                onChange={(e) => updateEnvironmentName(envIndex, e.target.value)}
                placeholder="e.g. dev, staging, prod"
                style={inputStyle}
              />
            </label>
            <button
              data-testid={`remove-environment-${envIndex}`}
              onClick={() => removeEnvironment(envIndex)}
              style={{ ...removeButtonStyle, alignSelf: 'flex-end', marginBottom: '2px' }}
            >
              Remove
            </button>
          </div>
          <div style={{ marginLeft: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ ...labelStyle, fontSize: '12px' }}>Variable Overrides</span>
              <button
                data-testid={`add-override-${envIndex}`}
                onClick={() => addOverride(envIndex)}
                style={{ ...addButtonStyle, fontSize: '11px', padding: '2px 8px' }}
              >
                + Add
              </button>
            </div>
            {Object.entries(env.variableOverrides).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
                <input
                  data-testid={`override-key-${envIndex}-${key}`}
                  type="text"
                  value={key}
                  readOnly
                  style={{ ...inputStyle, width: '120px', opacity: 0.7 }}
                />
                <input
                  data-testid={`override-value-${envIndex}-${key}`}
                  type="text"
                  value={value}
                  onChange={(e) => updateOverride(envIndex, key, e.target.value)}
                  placeholder="value"
                  style={{ ...inputStyle, width: '140px' }}
                />
                <button
                  data-testid={`remove-override-${envIndex}-${key}`}
                  onClick={() => removeOverride(envIndex, key)}
                  style={removeButtonStyle}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function GlobalVariablesSection({
  config,
  updateConfig,
  sectionCardStyle,
}: {
  config: GlobalTerraformConfig;
  updateConfig: (updates: Partial<GlobalTerraformConfig>) => void;
  sectionCardStyle: React.CSSProperties;
}) {
  const addVariable = () => {
    updateConfig({
      globalVariables: [
        ...config.globalVariables,
        { name: '', type: 'string' as TerraformVariableType, description: '', default: '' },
      ],
    });
  };

  const removeVariable = (index: number) => {
    updateConfig({
      globalVariables: config.globalVariables.filter((_, i) => i !== index),
    });
  };

  const updateVariable = (index: number, updates: Partial<GlobalTerraformConfig['globalVariables'][number]>) => {
    const vars = [...config.globalVariables];
    vars[index] = { ...vars[index], ...updates };
    updateConfig({ globalVariables: vars });
  };

  return (
    <div style={sectionCardStyle} data-testid="global-variables-section">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <span style={sectionHeadingStyle}>Global Variables</span>
        <button data-testid="add-global-variable" onClick={addVariable} style={addButtonStyle}>
          + Add Variable
        </button>
      </div>
      {config.globalVariables.map((variable, index) => (
        <div
          key={index}
          data-testid={`global-variable-${index}`}
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
            alignItems: 'flex-end',
            marginBottom: '8px',
            padding: '8px',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '4px',
            backgroundColor: '#252525',
          }}
        >
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
            <span style={labelStyle}>Name</span>
            <input
              data-testid={`gvar-name-${index}`}
              type="text"
              value={variable.name}
              onChange={(e) => updateVariable(index, { name: e.target.value })}
              placeholder="variable_name"
              style={{ ...inputStyle, width: '140px' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
            <span style={labelStyle}>Type</span>
            <select
              data-testid={`gvar-type-${index}`}
              value={variable.type}
              onChange={(e) => updateVariable(index, { type: e.target.value as TerraformVariableType })}
              style={selectStyle}
            >
              <option value="string">string</option>
              <option value="number">number</option>
              <option value="bool">bool</option>
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
            <span style={labelStyle}>Description</span>
            <input
              data-testid={`gvar-description-${index}`}
              type="text"
              value={variable.description}
              onChange={(e) => updateVariable(index, { description: e.target.value })}
              placeholder="Description"
              style={{ ...inputStyle, width: '180px' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
            <span style={labelStyle}>Default</span>
            <input
              data-testid={`gvar-default-${index}`}
              type="text"
              value={variable.default ?? ''}
              onChange={(e) => updateVariable(index, { default: e.target.value })}
              placeholder="default value"
              style={{ ...inputStyle, width: '140px' }}
            />
          </label>
          <button
            data-testid={`remove-global-variable-${index}`}
            onClick={() => removeVariable(index)}
            style={{ ...removeButtonStyle, marginBottom: '2px' }}
          >
            Remove
          </button>
        </div>
      ))}
    </div>
  );
}
