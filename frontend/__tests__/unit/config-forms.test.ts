import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';

describe('Config Forms - Service-specific config fields', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      activeTool: 'pointer',
      selectedElementId: null,
      selectedConnectorId: null,
      pendingConnectorSourceId: null,
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  describe('Lambda config fields', () => {
    it('stores handler, runtime, memory_size, timeout, and is_layer', () => {
      const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
      useDiagramStore.getState().updateElementConfig(id, {
        handler: 'index.handler',
        runtime: 'nodejs20.x',
        memory_size: 256,
        timeout: 30,
        is_layer: false,
      });

      const config = useDiagramStore.getState().elements.get(id)!.config;
      expect(config.handler).toBe('index.handler');
      expect(config.runtime).toBe('nodejs20.x');
      expect(config.memory_size).toBe(256);
      expect(config.timeout).toBe(30);
      expect(config.is_layer).toBe(false);
    });

    it('supports is_layer set to true', () => {
      const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
      useDiagramStore.getState().updateElementConfig(id, { is_layer: true });

      expect(useDiagramStore.getState().elements.get(id)!.config.is_layer).toBe(true);
    });
  });

  describe('S3 config fields', () => {
    it('stores versioning', () => {
      const id = useDiagramStore.getState().addElement('s3', { x: 0, y: 0 });
      useDiagramStore.getState().updateElementConfig(id, { versioning: true });

      const config = useDiagramStore.getState().elements.get(id)!.config;
      expect(config.versioning).toBe(true);
    });
  });

  describe('DynamoDB config fields', () => {
    it('stores billing_mode, hash_key, hash_key_type, range_key, and range_key_type', () => {
      const id = useDiagramStore.getState().addElement('dynamodb', { x: 0, y: 0 });
      useDiagramStore.getState().updateElementConfig(id, {
        billing_mode: 'PAY_PER_REQUEST',
        hash_key: 'pk',
        hash_key_type: 'S',
        range_key: 'sk',
        range_key_type: 'S',
      });

      const config = useDiagramStore.getState().elements.get(id)!.config;
      expect(config.billing_mode).toBe('PAY_PER_REQUEST');
      expect(config.hash_key).toBe('pk');
      expect(config.hash_key_type).toBe('S');
      expect(config.range_key).toBe('sk');
      expect(config.range_key_type).toBe('S');
    });
  });

  describe('API Gateway config fields', () => {
    it('stores protocol_type', () => {
      const id = useDiagramStore.getState().addElement('api-gateway', { x: 0, y: 0 });
      useDiagramStore.getState().updateElementConfig(id, { protocol_type: 'HTTP' });

      const config = useDiagramStore.getState().elements.get(id)!.config;
      expect(config.protocol_type).toBe('HTTP');
    });
  });

  describe('CloudWatch config fields', () => {
    it('stores retention_in_days', () => {
      const id = useDiagramStore.getState().addElement('cloudwatch', { x: 0, y: 0 });
      useDiagramStore.getState().updateElementConfig(id, { retention_in_days: 30 });

      const config = useDiagramStore.getState().elements.get(id)!.config;
      expect(config.retention_in_days).toBe(30);
    });
  });

  describe('IAM config fields', () => {
    it('has no service-specific config fields', () => {
      const id = useDiagramStore.getState().addElement('iam', { x: 0, y: 0 });

      const config = useDiagramStore.getState().elements.get(id)!.config;
      expect(config).toEqual({});
    });
  });
});
