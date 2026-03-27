import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  diagramStateArbitrary,
  viewportArbitrary,
  pointArbitrary,
  serviceTypeArbitrary,
  resourceConfigArbitrary,
} from './arbitraries';

beforeEach(() => {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    projectName: '',
    environments: [],
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
    selectedElementId: null,
    selectedConnectorId: null,
    pendingConnectorSourceId: null,
    activeTool: 'pointer',
  });
});

// Feature: diagram-editor-frontend, Property 9: Diagram state serialization round-trip
// **Validates: Requirements 6.4, 6.5, 9.2**
describe('Property 9: Diagram state serialization round-trip', () => {
  test('serialize → deserialize produces equivalent state with same elements, connectors, viewport, project settings', () => {
    fc.assert(
      fc.property(
        diagramStateArbitrary(),
        viewportArbitrary(),
        fc.string({ minLength: 1, maxLength: 30 }),
        (diagramState, viewport, projectName) => {
          // Reset store
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
            projectName: '',
            environments: [],
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          const store = useDiagramStore.getState();

          // Add elements to the store
          const idMapping = new Map<string, string>();
          for (const el of diagramState.elements) {
            const newId = store.addElement(el.serviceType, el.position);
            idMapping.set(el.id, newId);
            const s = useDiagramStore.getState();
            s.updateElementName(newId, el.name);
            if (Object.keys(el.config).length > 0) {
              useDiagramStore.getState().updateElementConfig(newId, el.config);
            }
          }

          // Add connectors using the mapped IDs
          for (const conn of diagramState.connectors) {
            const mappedSource = idMapping.get(conn.sourceId);
            const mappedTarget = idMapping.get(conn.targetId);
            if (mappedSource && mappedTarget && mappedSource !== mappedTarget) {
              try {
                useDiagramStore.getState().addConnector(mappedSource, mappedTarget, conn.connectionType);
              } catch {
                // Skip invalid connectors (e.g., self-connections after mapping)
              }
            }
          }

          // Set project name and viewport
          useDiagramStore.getState().setProjectName(projectName);
          useDiagramStore.setState({ viewport });

          // Snapshot the state before serialization
          const stateBefore = useDiagramStore.getState();
          const elementsBefore = Array.from(stateBefore.elements.values());
          const connectorsBefore = Array.from(stateBefore.connectors.values());
          const viewportBefore = { ...stateBefore.viewport };
          const projectNameBefore = stateBefore.projectName;

          // Serialize
          const serialized = useDiagramStore.getState().serializeDiagramState();

          // Load into a fresh state
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
            projectName: '',
            environments: [],
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });
          useDiagramStore.getState().loadDiagramState(serialized);

          const stateAfter = useDiagramStore.getState();

          // Verify elements match
          expect(stateAfter.elements.size).toBe(elementsBefore.length);
          for (const elBefore of elementsBefore) {
            const elAfter = stateAfter.elements.get(elBefore.id);
            expect(elAfter).toBeDefined();
            expect(elAfter!.serviceType).toBe(elBefore.serviceType);
            expect(elAfter!.name).toBe(elBefore.name);
            expect(elAfter!.position.x).toBe(elBefore.position.x);
            expect(elAfter!.position.y).toBe(elBefore.position.y);
            expect(elAfter!.config).toEqual(elBefore.config);
          }

          // Verify connectors match
          expect(stateAfter.connectors.size).toBe(connectorsBefore.length);
          for (const connBefore of connectorsBefore) {
            const connAfter = stateAfter.connectors.get(connBefore.id);
            expect(connAfter).toBeDefined();
            expect(connAfter!.sourceId).toBe(connBefore.sourceId);
            expect(connAfter!.targetId).toBe(connBefore.targetId);
            expect(connAfter!.connectionType).toBe(connBefore.connectionType);
          }

          // Verify viewport matches
          expect(stateAfter.viewport.offsetX).toBe(viewportBefore.offsetX);
          expect(stateAfter.viewport.offsetY).toBe(viewportBefore.offsetY);
          expect(stateAfter.viewport.scale).toBe(viewportBefore.scale);

          // Verify project name matches
          expect(stateAfter.projectName).toBe(projectNameBefore);
        }
      ),
      { numRuns: 100 }
    );
  });
});


// Feature: diagram-editor-frontend, Property 10: Export serialization maps diagram to ArchitectureDescription
// **Validates: Requirements 7.1, 7.2, 7.3**
describe('Property 10: Export serialization maps diagram to ArchitectureDescription', () => {
  test('for any diagram with N elements and M connectors, resources length N, connections length M, fields match', () => {
    fc.assert(
      fc.property(
        diagramStateArbitrary(),
        fc.string({ minLength: 1, maxLength: 30 }),
        (diagramState, projectName) => {
          // Reset store
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            canvasObjects: new Map(),
            viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
            projectName: '',
            environments: [],
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          const store = useDiagramStore.getState();

          // Add elements to the store (for connector validation) and canvas objects (for resource serialization)
          const idMapping = new Map<string, string>();
          for (const el of diagramState.elements) {
            const newId = store.addElement(el.serviceType, el.position);
            idMapping.set(el.id, newId);
            const s = useDiagramStore.getState();
            s.updateElementName(newId, el.name);
            if (Object.keys(el.config).length > 0) {
              useDiagramStore.getState().updateElementConfig(newId, el.config);
            }
            // Also add a corresponding canvas object for serializeToArchitectureDescription
            useDiagramStore.setState((state) => {
              const next = new Map(state.canvasObjects);
              next.set(newId, {
                id: newId,
                objectType: 'architecture-block' as const,
                serviceType: el.serviceType,
                name: useDiagramStore.getState().elements.get(newId)!.name,
                position: { ...el.position },
                config: { ...useDiagramStore.getState().elements.get(newId)!.config },
                terraformVariables: {},
                visualConfig: { width: 80, height: 80 },
                zIndex: next.size,
              });
              return { canvasObjects: next };
            });
          }

          // Add connectors using the mapped IDs
          let addedConnectors = 0;
          for (const conn of diagramState.connectors) {
            const mappedSource = idMapping.get(conn.sourceId);
            const mappedTarget = idMapping.get(conn.targetId);
            if (mappedSource && mappedTarget && mappedSource !== mappedTarget) {
              try {
                useDiagramStore.getState().addConnector(mappedSource, mappedTarget, conn.connectionType);
                addedConnectors++;
              } catch {
                // Skip invalid connectors
              }
            }
          }

          // Set project name
          useDiagramStore.getState().setProjectName(projectName);

          const currentState = useDiagramStore.getState();
          const elementsArray = Array.from(currentState.elements.values());
          const connectorsArray = Array.from(currentState.connectors.values());

          // Serialize to ArchitectureDescription
          const archDesc = currentState.serializeToArchitectureDescription();

          // (a) resources has length N with matching service_type and config
          expect(archDesc.resources.length).toBe(elementsArray.length);
          for (const el of elementsArray) {
            const resource = archDesc.resources.find((r) => r.name === el.name);
            expect(resource).toBeDefined();
            expect(resource!.service_type).toBe(el.serviceType);
            expect(resource!.config).toEqual(el.config);
          }

          // (b) connections has length M with matching source/target names
          expect(archDesc.connections.length).toBe(connectorsArray.length);
          for (const conn of connectorsArray) {
            const sourceEl = currentState.elements.get(conn.sourceId);
            const targetEl = currentState.elements.get(conn.targetId);
            const connection = archDesc.connections.find(
              (c) =>
                c.source === sourceEl?.name &&
                c.target === targetEl?.name &&
                c.connection_type === conn.connectionType
            );
            expect(connection).toBeDefined();
          }

          // (c) project_name matches
          expect(archDesc.project_name).toBe(projectName);
        }
      ),
      { numRuns: 100 }
    );
  });
});
