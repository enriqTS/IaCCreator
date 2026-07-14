import { describe, it, expect } from 'vitest';
import {
  findConnectorForLine,
  getSchemaForConnector,
  ensureConnectorForLine,
} from '@/connections/connector-utils';
import { CONNECTION_SCHEMA_REGISTRY } from '@/connections';
import type {
  LineObject,
  Connector,
  CanvasObject,
  ArchitectureBlock,
  GeometricObject,
} from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL } from '@/types/diagram';

// --- Test Helpers ---

function makeBlock(id: string, serviceType: string, name?: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: serviceType as ArchitectureBlock['serviceType'],
    name: name ?? id,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function makeLine(
  id: string,
  sourceObjectId: string | null,
  targetObjectId: string | null,
): LineObject {
  return {
    id,
    objectType: 'line',
    name: 'line',
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    sourceAnchor: sourceObjectId ? { objectId: sourceObjectId, anchorPosition: 'right' } : null,
    targetAnchor: targetObjectId ? { objectId: targetObjectId, anchorPosition: 'left' } : null,
    visualConfig: { ...DEFAULT_LINE_VISUAL },
    zIndex: 0,
  };
}

function makeConnector(id: string, sourceId: string, targetId: string): Connector {
  return {
    id,
    sourceId,
    targetId,
    connectionType: 'triggers',
  };
}

function makeGeoObject(id: string): GeometricObject {
  return {
    id,
    objectType: 'geometric',
    name: 'shape',
    position: { x: 0, y: 0 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
    zIndex: 0,
  };
}

// --- findConnectorForLine ---

describe('findConnectorForLine', () => {
  it('returns the matching connector when line connects two architecture blocks', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', 'block-a', 'block-b');
    const connector = makeConnector('conn-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);
    const connectors = new Map<string, Connector>([['conn-1', connector]]);

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBe(connector);
  });

  it('returns null when line has no sourceAnchor', () => {
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', null, 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([['block-b', blockB]]);
    const connectors = new Map<string, Connector>();

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBeNull();
  });

  it('returns null when line has no targetAnchor', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const line = makeLine('line-1', 'block-a', null);

    const canvasObjects = new Map<string, CanvasObject>([['block-a', blockA]]);
    const connectors = new Map<string, Connector>();

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBeNull();
  });

  it('returns null when source object is not an architecture block', () => {
    const geo = makeGeoObject('geo-1');
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', 'geo-1', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['geo-1', geo],
      ['block-b', blockB],
    ]);
    const connectors = new Map<string, Connector>();

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBeNull();
  });

  it('returns null when target object is not an architecture block', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const geo = makeGeoObject('geo-1');
    const line = makeLine('line-1', 'block-a', 'geo-1');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['geo-1', geo],
    ]);
    const connectors = new Map<string, Connector>();

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBeNull();
  });

  it('returns null when no connector matches the source/target pair', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const blockB = makeBlock('block-b', 'lambda');
    const blockC = makeBlock('block-c', 's3');
    const line = makeLine('line-1', 'block-a', 'block-b');
    // Connector exists but for a different pair
    const connector = makeConnector('conn-1', 'block-a', 'block-c');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
      ['block-c', blockC],
    ]);
    const connectors = new Map<string, Connector>([['conn-1', connector]]);

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBeNull();
  });

  it('returns null when source object does not exist in canvasObjects', () => {
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', 'missing-block', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([['block-b', blockB]]);
    const connectors = new Map<string, Connector>();

    const result = findConnectorForLine(line, connectors, canvasObjects);
    expect(result).toBeNull();
  });
});

// --- getSchemaForConnector ---

describe('getSchemaForConnector', () => {
  it('returns the correct schema for api-gateway → lambda', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const blockB = makeBlock('block-b', 'lambda');
    const connector = makeConnector('conn-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);

    const schema = getSchemaForConnector(connector, canvasObjects);
    expect(schema).not.toBeNull();
    expect(schema!.label).toBe('API Gateway → Lambda');
  });

  it('returns the correct schema for sqs → lambda', () => {
    const blockA = makeBlock('block-a', 'sqs');
    const blockB = makeBlock('block-b', 'lambda');
    const connector = makeConnector('conn-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);

    const schema = getSchemaForConnector(connector, canvasObjects);
    expect(schema).not.toBeNull();
    expect(schema!.label).toBe('SQS → Lambda');
  });

  it('returns the correct schema for lambda → dynamodb', () => {
    const blockA = makeBlock('block-a', 'lambda');
    const blockB = makeBlock('block-b', 'dynamodb');
    const connector = makeConnector('conn-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);

    const schema = getSchemaForConnector(connector, canvasObjects);
    expect(schema).not.toBeNull();
    expect(schema!.label).toBe('Lambda → DynamoDB');
  });

  it('returns null for an unsupported service pair', () => {
    const blockA = makeBlock('block-a', 's3');
    const blockB = makeBlock('block-b', 'dynamodb');
    const connector = makeConnector('conn-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);

    const schema = getSchemaForConnector(connector, canvasObjects);
    expect(schema).toBeNull();
  });

  it('returns null when source block is not found', () => {
    const blockB = makeBlock('block-b', 'lambda');
    const connector = makeConnector('conn-1', 'missing', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([['block-b', blockB]]);

    const schema = getSchemaForConnector(connector, canvasObjects);
    expect(schema).toBeNull();
  });

  it('returns null when target block is not an architecture block', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const geo = makeGeoObject('geo-1');
    const connector = makeConnector('conn-1', 'block-a', 'geo-1');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['geo-1', geo],
    ]);

    const schema = getSchemaForConnector(connector, canvasObjects);
    expect(schema).toBeNull();
  });
});

// --- ensureConnectorForLine ---

describe('ensureConnectorForLine', () => {
  it('returns existing connector when one already exists', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', 'block-a', 'block-b');
    const connector = makeConnector('conn-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);
    const connectors = new Map<string, Connector>([['conn-1', connector]]);

    const result = ensureConnectorForLine(line, canvasObjects, connectors);
    expect(result).toBe(connector);
  });

  it('creates a new connector when none exists for the block pair', () => {
    const blockA = makeBlock('block-a', 'api-gateway');
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);
    const connectors = new Map<string, Connector>();

    const result = ensureConnectorForLine(line, canvasObjects, connectors);
    expect(result).not.toBeNull();
    expect(result!.sourceId).toBe('block-a');
    expect(result!.targetId).toBe('block-b');
    expect(result!.connectionType).toBe('triggers');
    expect(result!.id).toBeDefined();
  });

  it('returns null when line has no sourceAnchor', () => {
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', null, 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([['block-b', blockB]]);
    const connectors = new Map<string, Connector>();

    const result = ensureConnectorForLine(line, canvasObjects, connectors);
    expect(result).toBeNull();
  });

  it('returns null when source is not an architecture block', () => {
    const geo = makeGeoObject('geo-1');
    const blockB = makeBlock('block-b', 'lambda');
    const line = makeLine('line-1', 'geo-1', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['geo-1', geo],
      ['block-b', blockB],
    ]);
    const connectors = new Map<string, Connector>();

    const result = ensureConnectorForLine(line, canvasObjects, connectors);
    expect(result).toBeNull();
  });

  it('newly created connector has a unique id', () => {
    const blockA = makeBlock('block-a', 'lambda');
    const blockB = makeBlock('block-b', 's3');
    const line = makeLine('line-1', 'block-a', 'block-b');

    const canvasObjects = new Map<string, CanvasObject>([
      ['block-a', blockA],
      ['block-b', blockB],
    ]);
    const connectors = new Map<string, Connector>();

    const result1 = ensureConnectorForLine(line, canvasObjects, connectors);
    const result2 = ensureConnectorForLine(line, canvasObjects, connectors);

    // Both calls create new connectors (since neither is persisted to the map)
    expect(result1).not.toBeNull();
    expect(result2).not.toBeNull();
    expect(result1!.id).not.toBe(result2!.id);
  });
});
