import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';

describe('Tool State', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      connectors: new Map(),
      activeTool: 'pointer',
      selectedObjectIds: new Set(),
      selectedConnectorId: null,
      pendingConnectorSourceId: null,
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  describe('setActiveTool', () => {
    it('sets activeTool to pointer', () => {
      useDiagramStore.getState().setActiveTool('connector');
      useDiagramStore.getState().setActiveTool('pointer');
      expect(useDiagramStore.getState().activeTool).toBe('pointer');
    });

    it('sets activeTool to connector', () => {
      useDiagramStore.getState().setActiveTool('connector');
      expect(useDiagramStore.getState().activeTool).toBe('connector');
    });

    it('sets activeTool to place-service with serviceType', () => {
      useDiagramStore.getState().setActiveTool({ type: 'place-service', serviceType: 'lambda' });
      expect(useDiagramStore.getState().activeTool).toEqual({
        type: 'place-service',
        serviceType: 'lambda',
      });
    });

    it('sets place-service for each supported service type', () => {
      const serviceTypes = ['lambda', 's3', 'api-gateway', 'dynamodb', 'iam', 'cloudwatch'] as const;
      for (const st of serviceTypes) {
        useDiagramStore.getState().setActiveTool({ type: 'place-service', serviceType: st });
        expect(useDiagramStore.getState().activeTool).toEqual({
          type: 'place-service',
          serviceType: st,
        });
      }
    });
  });

  describe('selectConnector', () => {
    it('sets selectedConnectorId', () => {
      useDiagramStore.getState().selectConnector('conn-1');

      expect(useDiagramStore.getState().selectedConnectorId).toBe('conn-1');
    });

    it('deselects when called with null', () => {
      useDiagramStore.setState({ selectedConnectorId: 'conn-1' });
      useDiagramStore.getState().selectConnector(null);

      expect(useDiagramStore.getState().selectedConnectorId).toBeNull();
    });
  });
});
