'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { EnvironmentConfig } from '@/types/diagram';

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

  const inputStyle: React.CSSProperties = {
    padding: '6px 10px',
    borderRadius: 6,
    border: '1px solid #404040',
    background: '#2a2a2a',
    color: '#e5e5e5',
    fontSize: 14,
    outline: 'none',
    width: '100%',
  };

  const smallBtnStyle: React.CSSProperties = {
    padding: '4px 10px',
    borderRadius: 4,
    border: '1px solid #404040',
    background: 'transparent',
    color: '#a3a3a3',
    fontSize: 12,
    cursor: 'pointer',
  };

  return (
    <div
      data-testid="project-settings-overlay"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
    >
      <div
        data-testid="project-settings-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#1e1e1e',
          borderRadius: 12,
          padding: 24,
          minWidth: 480,
          maxHeight: '80vh',
          overflowY: 'auto',
          color: '#e5e5e5',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
        }}
      >
        <h2 style={{ margin: '0 0 20px', fontSize: 18, fontWeight: 600 }}>Project Settings</h2>

        {/* Project Name */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 13, color: '#a3a3a3' }}>
            Project Name
          </label>
          <input
            data-testid="project-name-input"
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="my-project"
            style={inputStyle}
          />
        </div>

        {/* Environments */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <label style={{ fontSize: 13, color: '#a3a3a3' }}>Environments</label>
            <button
              data-testid="add-environment-btn"
              onClick={addEnvironment}
              style={smallBtnStyle}
            >
              + Add Environment
            </button>
          </div>

          {environments.map((env, envIdx) => (
            <div
              key={envIdx}
              data-testid={`environment-${envIdx}`}
              style={{
                border: '1px solid #333',
                borderRadius: 8,
                padding: 12,
                marginBottom: 12,
                background: '#252525',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <input
                  data-testid={`env-name-${envIdx}`}
                  type="text"
                  value={env.name}
                  onChange={(e) => updateEnvName(envIdx, e.target.value)}
                  placeholder="Environment name"
                  style={{ ...inputStyle, flex: 1 }}
                />
                <button
                  data-testid={`remove-env-${envIdx}`}
                  onClick={() => removeEnvironment(envIdx)}
                  style={{ ...smallBtnStyle, color: '#ef4444', borderColor: '#ef4444' }}
                >
                  Remove
                </button>
              </div>

              <div style={{ fontSize: 12, color: '#737373', marginBottom: 6 }}>Variables</div>
              {env.variables.map((v, varIdx) => (
                <div key={varIdx} style={{ display: 'flex', gap: 6, marginBottom: 6, alignItems: 'center' }}>
                  <input
                    data-testid={`var-key-${envIdx}-${varIdx}`}
                    type="text"
                    value={v.key}
                    onChange={(e) => updateVariable(envIdx, varIdx, 'key', e.target.value)}
                    placeholder="Key"
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <input
                    data-testid={`var-value-${envIdx}-${varIdx}`}
                    type="text"
                    value={v.value}
                    onChange={(e) => updateVariable(envIdx, varIdx, 'value', e.target.value)}
                    placeholder="Value"
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <button
                    data-testid={`remove-var-${envIdx}-${varIdx}`}
                    onClick={() => removeVariable(envIdx, varIdx)}
                    style={{ ...smallBtnStyle, color: '#ef4444', borderColor: '#ef4444', flexShrink: 0 }}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                data-testid={`add-var-${envIdx}`}
                onClick={() => addVariable(envIdx)}
                style={{ ...smallBtnStyle, marginTop: 4 }}
              >
                + Add Variable
              </button>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button
            data-testid="project-settings-cancel"
            onClick={onClose}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: '1px solid #404040',
              background: 'transparent',
              color: '#e5e5e5',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            data-testid="project-settings-save"
            onClick={handleSave}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: 'none',
              background: '#3b82f6',
              color: '#fff',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
