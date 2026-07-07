/**
 * Unit + property tests for Terraform variable store actions and serialization round-trip.
 *
 * Validates: Requirements 2.4, 2.5, 2.6
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';
import { getDefaultVariables, VARIABLE_SCHEMAS } from '@/types/terraform-variables';
import { architectureBlockWithoutIdArbitrary } from '../properties/arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    connectors: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    projectName: '',
    environments: [],
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

function addLambdaBlock(name = 'lambda-1'): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
  });
}

function getBlock(id: string): ArchitectureBlock {
  return useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
}

describe('DiagramStore - setTerraformVariable', () => {
  beforeEach(resetStore);

  it('updates a single variable on the correct block', () => {
    const id = addLambdaBlock();
    useDiagramStore.getState().setTerraformVariable(id, 'function_name', 'hello');

    expect(getBlock(id).terraformVariables.function_name).toBe('hello');
  });

  it('preserves other variables when updating one', () => {
    const id = addLambdaBlock();
    useDiagramStore.getState().setTerraformVariable(id, 'function_name', 'hello');
    useDiagramStore.getState().setTerraformVariable(id, 'timeout', 30);

    const vars = getBlock(id).terraformVariables;
    expect(vars.function_name).toBe('hello');
    expect(vars.timeout).toBe(30);
    // default should still be present
    expect(vars.memory_size).toBe(128);
  });

  it('does not affect other blocks', () => {
    const id1 = addLambdaBlock('lambda-1');
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 's3',
      name: 's3-1',
      position: { x: 100, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });

    useDiagramStore.getState().setTerraformVariable(id1, 'function_name', 'my-func');

    const s3Block = getBlock(id2);
    expect(s3Block.terraformVariables.function_name).toBeUndefined();
    // s3 defaults should be intact
    expect(s3Block.terraformVariables.versioning_enabled).toBe(false);
  });

  it('is a no-op for non-existent object', () => {
    const id = addLambdaBlock();
    const before = { ...getBlock(id).terraformVariables };
    useDiagramStore.getState().setTerraformVariable('nonexistent', 'function_name', 'x');
    expect(getBlock(id).terraformVariables).toEqual(before);
  });

  it('is a no-op for non-architecture-block objects', () => {
    const lineId = useDiagramStore.getState().addCanvasObject({
      objectType: 'line',
      name: 'line-1',
      start: { x: 0, y: 0 },
      end: { x: 100, y: 100 },
      sourceAnchor: null,
      targetAnchor: null,
      visualConfig: { color: '#fff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false },
    });
    // Should not throw
    useDiagramStore.getState().setTerraformVariable(lineId, 'foo', 'bar');
    const obj = useDiagramStore.getState().canvasObjects.get(lineId)!;
    expect(obj.objectType).toBe('line');
  });
});

describe('DiagramStore - setTerraformVariables (batch)', () => {
  beforeEach(resetStore);

  it('merges multiple variables at once', () => {
    const id = addLambdaBlock();
    useDiagramStore.getState().setTerraformVariables(id, {
      function_name: 'batch-func',
      handler: 'main.handler',
      timeout: 60,
    });

    const vars = getBlock(id).terraformVariables;
    expect(vars.function_name).toBe('batch-func');
    expect(vars.handler).toBe('main.handler');
    expect(vars.timeout).toBe(60);
    expect(vars.memory_size).toBe(128); // default preserved
  });
});

describe('DiagramStore - terraformVariables serialization/deserialization', () => {
  beforeEach(resetStore);

  it('serialization preserves terraformVariables on architecture blocks', () => {
    const id = addLambdaBlock();
    useDiagramStore.getState().setTerraformVariable(id, 'function_name', 'my-func');
    useDiagramStore.getState().setTerraformVariable(id, 'memory_size', 512);

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const sObj = serialized.canvasObjects!.find((o) => o.id === id)!;

    expect(sObj.terraformVariables).toBeDefined();
    expect(sObj.terraformVariables!.function_name).toBe('my-func');
    expect(sObj.terraformVariables!.memory_size).toBe(512);
  });

  it('deserialization restores terraformVariables', () => {
    const id = addLambdaBlock();
    useDiagramStore.getState().setTerraformVariable(id, 'function_name', 'restored-func');
    useDiagramStore.getState().setTerraformVariable(id, 'timeout', 15);

    const serialized = useDiagramStore.getState().serializeDiagramState();

    // Reset and reload
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const block = getBlock(id);
    expect(block.terraformVariables.function_name).toBe('restored-func');
    expect(block.terraformVariables.timeout).toBe(15);
    expect(block.terraformVariables.memory_size).toBe(128); // default
  });

  it('backward-compatible load: missing terraformVariables gets schema defaults', () => {
    // Simulate a v2 state saved before the terraform variables feature
    const state = {
      version: 2,
      projectName: 'old-project',
      environments: [],
      elements: [],
      connectors: [],
      canvasObjects: [
        {
          id: 'block-1',
          objectType: 'architecture-block' as const,
          name: 'lambda-1',
          x: 10,
          y: 20,
          serviceType: 'lambda' as const,
          config: { handler: 'index.handler' },
          visualConfig: { width: 80, height: 80 },
          // No terraformVariables field
        },
        {
          id: 'block-2',
          objectType: 'architecture-block' as const,
          name: 's3-1',
          x: 200,
          y: 20,
          serviceType: 's3' as const,
          config: {},
          visualConfig: { width: 80, height: 80 },
          // No terraformVariables field
        },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(state as any);

    const lambdaBlock = getBlock('block-1');
    expect(lambdaBlock.terraformVariables).toEqual(getDefaultVariables('lambda'));

    const s3Block = getBlock('block-2');
    expect(s3Block.terraformVariables).toEqual(getDefaultVariables('s3'));
  });

  it('serializeToArchitectureDescription includes terraform_variables per resource', () => {
    const id = addLambdaBlock();
    useDiagramStore.getState().setTerraformVariable(id, 'function_name', 'api-handler');

    const desc = useDiagramStore.getState().serializeToArchitectureDescription();
    const resource = desc.resources.find((r) => r.name === 'lambda-1')!;

    expect(resource.terraform_variables).toBeDefined();
    expect(resource.terraform_variables!.function_name).toBe('api-handler');
    expect(resource.terraform_variables!.memory_size).toBe(128);
  });
});

describe('Property 1: Round-trip consistency — serialize then deserialize produces equivalent terraformVariables', () => {
  beforeEach(resetStore);

  it('terraformVariables survive serialize → deserialize round-trip for any architecture block', () => {
    fc.assert(
      fc.property(
        fc.array(architectureBlockWithoutIdArbitrary(), { minLength: 1, maxLength: 6 }),
        (payloads) => {
          resetStore();
          const store = useDiagramStore.getState();
          const addedIds: string[] = [];

          for (const payload of payloads) {
            const id = store.addCanvasObject(payload);
            addedIds.push(id);
          }

          // Capture pre-serialization terraformVariables
          const preVars = new Map<string, Record<string, string | number | boolean>>();
          for (const id of addedIds) {
            const block = useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
            preVars.set(id, { ...block.terraformVariables });
          }

          // Serialize
          const serialized = useDiagramStore.getState().serializeDiagramState();

          // Reset and reload
          resetStore();
          useDiagramStore.getState().loadDiagramState(serialized);

          // Verify round-trip
          for (const [id, expectedVars] of preVars) {
            const postBlock = useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
            if (!postBlock) return false;

            const postVars = postBlock.terraformVariables;
            const expectedKeys = Object.keys(expectedVars).sort();
            const actualKeys = Object.keys(postVars).sort();

            if (expectedKeys.length !== actualKeys.length) return false;
            for (let i = 0; i < expectedKeys.length; i++) {
              if (expectedKeys[i] !== actualKeys[i]) return false;
              if (expectedVars[expectedKeys[i]] !== postVars[actualKeys[i]]) return false;
            }
          }

          return true;
        },
      ),
      { numRuns: 200 },
    );
  });

  it('custom variable values survive round-trip', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('lambda', 's3', 'dynamodb', 'api-gateway', 'cloudwatch'),
        fc.dictionary(
          fc.stringMatching(/^[a-z][a-z0-9_]{0,19}$/),
          fc.oneof(
            fc.string({ minLength: 0, maxLength: 50 }),
            fc.integer({ min: 0, max: 10000 }),
            fc.boolean(),
          ),
          { minKeys: 0, maxKeys: 5 },
        ),
        (serviceType, customVars) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject({
            objectType: 'architecture-block',
            serviceType: serviceType as any,
            name: `${serviceType}-test`,
            position: { x: 0, y: 0 },
            config: {},
            terraformVariables: {},
            visualConfig: { width: 80, height: 80 },
          });

          // Apply custom variables
          useDiagramStore.getState().setTerraformVariables(id, customVars);

          const preVars = { ...(useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock).terraformVariables };

          // Round-trip
          const serialized = useDiagramStore.getState().serializeDiagramState();
          resetStore();
          useDiagramStore.getState().loadDiagramState(serialized);

          const postVars = (useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock).terraformVariables;

          // All pre-serialization keys/values must match
          for (const key of Object.keys(preVars)) {
            if (preVars[key] !== postVars[key]) return false;
          }
          for (const key of Object.keys(postVars)) {
            if (preVars[key] !== postVars[key]) return false;
          }

          return true;
        },
      ),
      { numRuns: 200 },
    );
  });
});
