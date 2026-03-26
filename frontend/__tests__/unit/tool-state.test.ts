import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';

describe('Tool State', () => {
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

  describe('selectElement', () => {
    it('sets selectedElementId and clears selectedConnectorId', () => {
      useDiagramStore.setState({ selectedConnectorId: 'some-connector' });
      useDiagramStore.getState().selectElement('elem-1');

      expect(useDiagramStore.getState().selectedElementId).toBe('elem-1');
      expect(useDiagramStore.getState().selectedConnectorId).toBeNull();
    });

    it('deselects when called with null', () => {
      useDiagramStore.setState({ selectedElementId: 'elem-1' });
      useDiagramStore.getState().selectElement(null);

      expect(useDiagramStore.getState().selectedElementId).toBeNull();
    });
  });

  describe('selectConnector', () => {
    it('sets selectedConnectorId and clears selectedElementId', () => {
      useDiagramStore.setState({ selectedElementId: 'some-element' });
      useDiagramStore.getState().selectConnector('conn-1');

      expect(useDiagramStore.getState().selectedConnectorId).toBe('conn-1');
      expect(useDiagramStore.getState().selectedElementId).toBeNull();
    });

    it('deselects when called with null', () => {
      useDiagramStore.setState({ selectedConnectorId: 'conn-1' });
      useDiagramStore.getState().selectConnector(null);

      expect(useDiagramStore.getState().selectedConnectorId).toBeNull();
    });
  });
});
