'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { EnvironmentConfig } from '@/types/diagram';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

export interface ProjectSettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

interface EditableEnvironment {
  name: string;
  variables: { key: string; value: string }[];
}

function toEditable(envs: EnvironmentConfig[]): EditableEnvironment[] {
  return envs.map((env) => ({
    name: env.name,
    variables: Object.entries(env.variables).map(([key, value]) => ({ key, value })),
  }));
}

function fromEditable(envs: EditableEnvironment[]): EnvironmentConfig[] {
  return envs.map((env) => ({
    name: env.name,
    variables: Object.fromEntries(env.variables.map((v) => [v.key, v.value])),
  }));
}

export default function ProjectSettingsDialog({ open, onClose }: ProjectSettingsDialogProps) {
  const storeProjectName = useDiagramStore((s) => s.projectName);
  const storeEnvironments = useDiagramStore((s) => s.environments);

  const [projectName, setProjectName] = useState('');
  const [environments, setEnvironments] = useState<EditableEnvironment[]>([]);

  // Sync form state when dialog opens
  useEffect(() => {
    if (open) {
      setProjectName(storeProjectName);
      setEnvironments(toEditable(storeEnvironments));
    }
  }, [open, storeProjectName, storeEnvironments]);

  const handleSave = useCallback(() => {
    useDiagramStore.getState().setProjectName(projectName);
    useDiagramStore.getState().setEnvironments(fromEditable(environments));
    onClose();
  }, [projectName, environments, onClose]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  const addEnvironment = () => {
    setEnvironments((prev) => [...prev, { name: '', variables: [] }]);
  };

  const removeEnvironment = (index: number) => {
    setEnvironments((prev) => prev.filter((_, i) => i !== index));
  };

  const updateEnvName = (index: number, name: string) => {
    setEnvironments((prev) =>
      prev.map((env, i) => (i === index ? { ...env, name } : env))
    );
  };

  const addVariable = (envIndex: number) => {
    setEnvironments((prev) =>
      prev.map((env, i) =>
        i === envIndex ? { ...env, variables: [...env.variables, { key: '', value: '' }] } : env
      )
    );
  };

  const removeVariable = (envIndex: number, varIndex: number) => {
    setEnvironments((prev) =>
      prev.map((env, i) =>
        i === envIndex
          ? { ...env, variables: env.variables.filter((_, vi) => vi !== varIndex) }
          : env
      )
    );
  };

  const updateVariable = (envIndex: number, varIndex: number, field: 'key' | 'value', val: string) => {
    setEnvironments((prev) =>
      prev.map((env, i) =>
        i === envIndex
          ? {
              ...env,
              variables: env.variables.map((v, vi) =>
                vi === varIndex ? { ...v, [field]: val } : v
              ),
            }
          : env
      )
    );
  };

  if (!open) return null;

  return (
    <div
      data-testid="project-settings-overlay"
      onClick={onClose}
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]"
    >
      <div
        data-testid="project-settings-dialog"
        onClick={(e) => e.stopPropagation()}
        className="bg-[#1e1e1e] rounded-xl p-6 min-w-[480px] max-h-[80vh] overflow-y-auto text-[#e5e5e5] shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
      >
        <h2 className="m-0 mb-5 text-lg font-semibold">Project Settings</h2>

        {/* Project Name */}
        <div className="mb-5">
          <Label className="block mb-1.5 text-[13px] text-muted-foreground">
            Project Name
          </Label>
          <Input
            data-testid="project-name-input"
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="my-project"
            className="w-full"
          />
        </div>

        {/* Environments */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-3">
            <Label className="text-[13px] text-muted-foreground">Environments</Label>
            <Button
              data-testid="add-environment-btn"
              variant="outline"
              size="sm"
              onClick={addEnvironment}
            >
              + Add Environment
            </Button>
          </div>

          {environments.map((env, envIdx) => (
            <div
              key={envIdx}
              data-testid={`environment-${envIdx}`}
              className="border border-[#333] rounded-lg p-3 mb-3 bg-[#252525]"
            >
              <div className="flex items-center gap-2 mb-2">
                <Input
                  data-testid={`env-name-${envIdx}`}
                  type="text"
                  value={env.name}
                  onChange={(e) => updateEnvName(envIdx, e.target.value)}
                  placeholder="Environment name"
                  className="flex-1"
                />
                <Button
                  data-testid={`remove-env-${envIdx}`}
                  variant="destructive"
                  size="sm"
                  onClick={() => removeEnvironment(envIdx)}
                >
                  Remove
                </Button>
              </div>

              <div className="text-xs text-muted-foreground mb-1.5">Variables</div>
              {env.variables.map((v, varIdx) => (
                <div key={varIdx} className="flex gap-1.5 mb-1.5 items-center">
                  <Input
                    data-testid={`var-key-${envIdx}-${varIdx}`}
                    type="text"
                    value={v.key}
                    onChange={(e) => updateVariable(envIdx, varIdx, 'key', e.target.value)}
                    placeholder="Key"
                    className="flex-1"
                  />
                  <Input
                    data-testid={`var-value-${envIdx}-${varIdx}`}
                    type="text"
                    value={v.value}
                    onChange={(e) => updateVariable(envIdx, varIdx, 'value', e.target.value)}
                    placeholder="Value"
                    className="flex-1"
                  />
                  <Button
                    data-testid={`remove-var-${envIdx}-${varIdx}`}
                    variant="destructive"
                    size="xs"
                    onClick={() => removeVariable(envIdx, varIdx)}
                    className="shrink-0"
                  >
                    ×
                  </Button>
                </div>
              ))}
              <Button
                data-testid={`add-var-${envIdx}`}
                variant="outline"
                size="sm"
                onClick={() => addVariable(envIdx)}
                className="mt-1"
              >
                + Add Variable
              </Button>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button
            data-testid="project-settings-cancel"
            variant="outline"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            data-testid="project-settings-save"
            onClick={handleSave}
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}
