'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { SIDEBAR_RESPONSIVE_THRESHOLD } from '@/components/config/panel-constants';
import type { GlobalTerraformConfig, TerraformVariableType } from '@/types/terraform-variables';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';

interface GlobalTerraformConfigPanelProps {
  panelWidth?: number;
}

/** Renders project-level Terraform configuration: backend, provider, versions, environments, global variables. */
export default function GlobalTerraformConfigPanel({ panelWidth }: GlobalTerraformConfigPanelProps) {
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

  const isTwoColumn = panelWidth !== undefined && panelWidth >= SIDEBAR_RESPONSIVE_THRESHOLD;
  const fieldGrid = isTwoColumn ? 'grid grid-cols-2 gap-3' : 'flex flex-col gap-3';

  return (
    <div data-testid="global-terraform-config-panel" className="flex flex-col gap-4">
      <div data-testid="config-sections-container" className="flex flex-col gap-4">
        {/* Backend Configuration */}
        <Card data-testid="backend-config-section" className="py-3 gap-2">
          <CardHeader className="px-4 py-0">
            <CardTitle className="text-sm">Backend Configuration</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className={fieldGrid}>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Backend Type</Label>
                <Select
                  value={config.backend.type}
                  onValueChange={(value) => {
                    updateBackend({
                      type: value,
                      config: value === 's3'
                        ? { bucket: '', key: 'terraform.tfstate', region: 'us-east-1', dynamodb_table: '' }
                        : {},
                    });
                  }}
                >
                  <SelectTrigger data-testid="backend-type" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="local">local</SelectItem>
                    <SelectItem value="s3">s3</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {config.backend.type === 's3' && (
                <>
                  <div className="flex flex-col gap-1.5">
                    <Label className="text-xs text-muted-foreground">Bucket</Label>
                    <Input
                      data-testid="backend-bucket"
                      type="text"
                      value={config.backend.config.bucket ?? ''}
                      onChange={(e) => updateBackend({ config: { ...config.backend.config, bucket: e.target.value } })}
                      placeholder="my-tf-state"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label className="text-xs text-muted-foreground">Key</Label>
                    <Input
                      data-testid="backend-key"
                      type="text"
                      value={config.backend.config.key ?? ''}
                      onChange={(e) => updateBackend({ config: { ...config.backend.config, key: e.target.value } })}
                      placeholder="terraform.tfstate"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label className="text-xs text-muted-foreground">Region</Label>
                    <Input
                      data-testid="backend-region"
                      type="text"
                      value={config.backend.config.region ?? ''}
                      onChange={(e) => updateBackend({ config: { ...config.backend.config, region: e.target.value } })}
                      placeholder="us-east-1"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label className="text-xs text-muted-foreground">DynamoDB Table</Label>
                    <Input
                      data-testid="backend-dynamodb-table"
                      type="text"
                      value={config.backend.config.dynamodb_table ?? ''}
                      onChange={(e) => updateBackend({ config: { ...config.backend.config, dynamodb_table: e.target.value } })}
                      placeholder="tf-locks"
                    />
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Provider Configuration */}
        <Card data-testid="provider-config-section" className="py-3 gap-2">
          <CardHeader className="px-4 py-0">
            <CardTitle className="text-sm">Provider Configuration</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className={fieldGrid}>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Region</Label>
                <Input
                  data-testid="provider-region"
                  type="text"
                  value={config.provider.region}
                  onChange={(e) => updateProvider({ region: e.target.value })}
                  placeholder="us-east-1"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Profile (optional)</Label>
                <Input
                  data-testid="provider-profile"
                  type="text"
                  value={config.provider.profile ?? ''}
                  onChange={(e) => updateProvider({ profile: e.target.value || undefined })}
                  placeholder="default"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Version Constraints */}
        <Card data-testid="version-constraints-section" className="py-3 gap-2">
          <CardHeader className="px-4 py-0">
            <CardTitle className="text-sm">Version Constraints</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className={fieldGrid}>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Terraform Version</Label>
                <Input
                  data-testid="terraform-version"
                  type="text"
                  value={config.versionConstraints.terraformVersion ?? ''}
                  onChange={(e) => updateVersionConstraints({ terraformVersion: e.target.value || undefined })}
                  placeholder=">= 1.5.0"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">AWS Provider Version</Label>
                <Input
                  data-testid="aws-provider-version"
                  type="text"
                  value={config.versionConstraints.awsProviderVersion ?? ''}
                  onChange={(e) => updateVersionConstraints({ awsProviderVersion: e.target.value || undefined })}
                  placeholder="~> 5.0"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Environment Settings */}
        <EnvironmentSettings config={config} updateConfig={updateConfig} isTwoColumn={isTwoColumn} />

        {/* Global Variables */}
        <GlobalVariablesSection config={config} updateConfig={updateConfig} isTwoColumn={isTwoColumn} />
      </div>
    </div>
  );
}

function EnvironmentSettings({
  config,
  updateConfig,
  isTwoColumn,
}: {
  config: GlobalTerraformConfig;
  updateConfig: (updates: Partial<GlobalTerraformConfig>) => void;
  isTwoColumn: boolean;
}) {
  const fieldGrid = isTwoColumn ? 'grid grid-cols-2 gap-3' : 'flex flex-col gap-3';

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
    <Card data-testid="environment-settings-section" className="py-3 gap-2">
      <CardHeader className="px-4 py-0">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm">Environment Settings</CardTitle>
          <button
            data-testid="add-environment"
            onClick={addEnvironment}
            className="text-xs text-blue-500 border border-blue-500/40 rounded px-2 py-0.5 hover:bg-blue-500/10"
          >
            + Add Environment
          </button>
        </div>
      </CardHeader>
      <CardContent className="px-4">
        {config.environments.map((env, envIndex) => (
          <div
            key={envIndex}
            data-testid={`environment-${envIndex}`}
            className="border border-border rounded-md p-3 mb-2 bg-muted/30"
          >
            <div className={`${fieldGrid} mb-2`}>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Name</Label>
                <Input
                  data-testid={`env-name-${envIndex}`}
                  type="text"
                  value={env.name}
                  onChange={(e) => updateEnvironmentName(envIndex, e.target.value)}
                  placeholder="e.g. dev, staging, prod"
                />
              </div>
              <div className="flex items-end">
                <button
                  data-testid={`remove-environment-${envIndex}`}
                  onClick={() => removeEnvironment(envIndex)}
                  className="text-xs text-red-500 border border-red-500/40 rounded px-2 py-1 hover:bg-red-500/10"
                >
                  Remove
                </button>
              </div>
            </div>
            <div className="ml-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-muted-foreground">Variable Overrides</span>
                <button
                  data-testid={`add-override-${envIndex}`}
                  onClick={() => addOverride(envIndex)}
                  className="text-[11px] text-blue-500 border border-blue-500/40 rounded px-2 py-0.5 hover:bg-blue-500/10"
                >
                  + Add
                </button>
              </div>
              {Object.entries(env.variableOverrides).map(([key, value]) => (
                <div key={key} className="flex gap-2 items-center mb-1">
                  <Input
                    data-testid={`override-key-${envIndex}-${key}`}
                    type="text"
                    value={key}
                    readOnly
                    className="w-28 opacity-70"
                  />
                  <Input
                    data-testid={`override-value-${envIndex}-${key}`}
                    type="text"
                    value={value}
                    onChange={(e) => updateOverride(envIndex, key, e.target.value)}
                    placeholder="value"
                    className="w-32"
                  />
                  <button
                    data-testid={`remove-override-${envIndex}-${key}`}
                    onClick={() => removeOverride(envIndex, key)}
                    className="text-xs text-red-500 border border-red-500/40 rounded px-1.5 py-0.5 hover:bg-red-500/10"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function GlobalVariablesSection({
  config,
  updateConfig,
  isTwoColumn,
}: {
  config: GlobalTerraformConfig;
  updateConfig: (updates: Partial<GlobalTerraformConfig>) => void;
  isTwoColumn: boolean;
}) {
  const fieldGrid = isTwoColumn ? 'grid grid-cols-2 gap-3' : 'flex flex-col gap-3';

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
    <Card data-testid="global-variables-section" className="py-3 gap-2">
      <CardHeader className="px-4 py-0">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm">Global Variables</CardTitle>
          <button
            data-testid="add-global-variable"
            onClick={addVariable}
            className="text-xs text-blue-500 border border-blue-500/40 rounded px-2 py-0.5 hover:bg-blue-500/10"
          >
            + Add Variable
          </button>
        </div>
      </CardHeader>
      <CardContent className="px-4">
        {config.globalVariables.map((variable, index) => (
          <div
            key={index}
            data-testid={`global-variable-${index}`}
            className="border border-border rounded-md p-3 mb-2 bg-muted/30"
          >
            <div className={fieldGrid}>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Name</Label>
                <Input
                  data-testid={`gvar-name-${index}`}
                  type="text"
                  value={variable.name}
                  onChange={(e) => updateVariable(index, { name: e.target.value })}
                  placeholder="variable_name"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Type</Label>
                <Select
                  value={variable.type}
                  onValueChange={(value) => updateVariable(index, { type: value as TerraformVariableType })}
                >
                  <SelectTrigger data-testid={`gvar-type-${index}`} className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="string">string</SelectItem>
                    <SelectItem value="number">number</SelectItem>
                    <SelectItem value="bool">bool</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Description</Label>
                <Input
                  data-testid={`gvar-description-${index}`}
                  type="text"
                  value={variable.description}
                  onChange={(e) => updateVariable(index, { description: e.target.value })}
                  placeholder="Description"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs text-muted-foreground">Default</Label>
                <Input
                  data-testid={`gvar-default-${index}`}
                  type="text"
                  value={variable.default ?? ''}
                  onChange={(e) => updateVariable(index, { default: e.target.value })}
                  placeholder="default value"
                />
              </div>
              <div className="flex items-end">
                <button
                  data-testid={`remove-global-variable-${index}`}
                  onClick={() => removeVariable(index)}
                  className="text-xs text-red-500 border border-red-500/40 rounded px-2 py-1 hover:bg-red-500/10"
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
