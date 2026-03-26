import fc from 'fast-check';
import type {
  ServiceType,
  Point,
  Viewport,
  DiagramElement,
  Connector,
  ResourceConfig,
  CanvasObject,
  ArchitectureBlock,
  LineObject,
  GeometricObject,
  GeometricShape,
  StrokeStyle,
} from '@/types/diagram';
import {
  DEFAULT_BLOCK_VISUAL,
  DEFAULT_LINE_VISUAL,
  DEFAULT_GEO_VISUAL,
} from '@/types/diagram';

const SERVICE_TYPES: ServiceType[] = [
  'lambda',
  's3',
  'api-gateway',
  'dynamodb',
  'iam',
  'cloudwatch',
];

/**
 * Generates a random Point with x/y in a reasonable range.
 */
export function pointArbitrary(): fc.Arbitrary<Point> {
  return fc.record({
    x: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
  });
}

/**
 * Generates a random Viewport with scale in [0.1, 5.0] and reasonable offsets.
 */
export function viewportArbitrary(): fc.Arbitrary<Viewport> {
  return fc.record({
    offsetX: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
    offsetY: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
    scale: fc.double({ min: 0.1, max: 5.0, noNaN: true, noDefaultInfinity: true }),
  });
}

/**
 * Generates one of the 6 supported service types.
 */
export function serviceTypeArbitrary(): fc.Arbitrary<ServiceType> {
  return fc.constantFrom(...SERVICE_TYPES);
}


/**
 * Generates a valid ResourceConfig for a given service type.
 */
export function resourceConfigArbitrary(serviceType?: ServiceType): fc.Arbitrary<ResourceConfig> {
  if (!serviceType) {
    return serviceTypeArbitrary().chain((st) => resourceConfigArbitrary(st));
  }

  switch (serviceType) {
    case 'lambda':
      return fc.record({
        handler: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
        runtime: fc.option(fc.constantFrom('nodejs18.x', 'nodejs20.x', 'python3.12'), { nil: undefined }),
        memory_size: fc.option(fc.integer({ min: 128, max: 10240 }), { nil: undefined }),
        timeout: fc.option(fc.integer({ min: 1, max: 900 }), { nil: undefined }),
        is_layer: fc.option(fc.boolean(), { nil: undefined }),
      });
    case 's3':
      return fc.record({
        versioning: fc.option(fc.boolean(), { nil: undefined }),
      });
    case 'dynamodb':
      return fc.record({
        billing_mode: fc.option(fc.constantFrom('PAY_PER_REQUEST', 'PROVISIONED'), { nil: undefined }),
        hash_key: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
        hash_key_type: fc.option(fc.constantFrom('S', 'N', 'B'), { nil: undefined }),
        range_key: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
        range_key_type: fc.option(fc.constantFrom('S', 'N', 'B'), { nil: undefined }),
      });
    case 'api-gateway':
      return fc.record({
        protocol_type: fc.option(fc.constantFrom('HTTP', 'WEBSOCKET'), { nil: undefined }),
      });
    case 'cloudwatch':
      return fc.record({
        retention_in_days: fc.option(fc.constantFrom(1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365), { nil: undefined }),
      });
    case 'iam':
      return fc.constant({});
    default:
      return fc.constant({});
  }
}

/**
 * Generates a random DiagramElement with valid service type, position, and config.
 */
export function diagramElementArbitrary(): fc.Arbitrary<DiagramElement> {
  return serviceTypeArbitrary().chain((st) =>
    fc.record({
      id: fc.uuid(),
      serviceType: fc.constant(st),
      name: fc.string({ minLength: 1, maxLength: 30 }),
      position: pointArbitrary(),
      config: resourceConfigArbitrary(st),
    })
  );
}

/**
 * Generates a random Connector between provided element IDs.
 * If no element IDs provided, generates with random UUIDs.
 */
export function connectorArbitrary(elementIds?: string[]): fc.Arbitrary<Connector> {
  if (elementIds && elementIds.length >= 2) {
    return fc.record({
      id: fc.uuid(),
      sourceId: fc.constantFrom(...elementIds),
      targetId: fc.constantFrom(...elementIds),
      connectionType: fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
    }).filter((c) => c.sourceId !== c.targetId);
  }
  return fc.record({
    id: fc.uuid(),
    sourceId: fc.uuid(),
    targetId: fc.uuid(),
    connectionType: fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
  }).filter((c) => c.sourceId !== c.targetId);
}

/**
 * Generates a complete random diagram state with elements and connectors
 * (ensuring connector references are valid).
 */
export function diagramStateArbitrary() {
  return fc
    .array(diagramElementArbitrary(), { minLength: 0, maxLength: 10 })
    .chain((elements) => {
      const ids = elements.map((e) => e.id);
      const connArb =
        ids.length >= 2
          ? fc.array(connectorArbitrary(ids), { minLength: 0, maxLength: 5 })
          : fc.constant([] as Connector[]);
      return connArb.map((connectors) => ({ elements, connectors }));
    });
}

/**
 * Generates a random valid operation for the current state.
 * Operations: add element, move element, delete element, add connector, delete connector, update config.
 */
export function operationArbitrary(elementIds: string[], connectorIds: string[]) {
  const ops: fc.Arbitrary<{ type: string; payload: unknown }>[] = [
    // Always available: add element
    fc.record({
      type: fc.constant('addElement'),
      payload: fc.record({
        serviceType: serviceTypeArbitrary(),
        position: pointArbitrary(),
      }),
    }),
  ];

  if (elementIds.length > 0) {
    // Move element
    ops.push(
      fc.record({
        type: fc.constant('moveElement'),
        payload: fc.record({
          id: fc.constantFrom(...elementIds),
          position: pointArbitrary(),
        }),
      })
    );
    // Delete element
    ops.push(
      fc.record({
        type: fc.constant('deleteElement'),
        payload: fc.record({
          id: fc.constantFrom(...elementIds),
        }),
      })
    );
    // Update config
    ops.push(
      fc.record({
        type: fc.constant('updateConfig'),
        payload: fc.record({
          id: fc.constantFrom(...elementIds),
          config: resourceConfigArbitrary(),
        }),
      })
    );
  }

  if (elementIds.length >= 2) {
    // Add connector
    ops.push(
      fc.record({
        type: fc.constant('addConnector'),
        payload: fc
          .record({
            sourceId: fc.constantFrom(...elementIds),
            targetId: fc.constantFrom(...elementIds),
          })
          .filter((p) => p.sourceId !== p.targetId),
      })
    );
  }

  if (connectorIds.length > 0) {
    // Delete connector
    ops.push(
      fc.record({
        type: fc.constant('deleteConnector'),
        payload: fc.record({
          id: fc.constantFrom(...connectorIds),
        }),
      })
    );
  }

  return fc.oneof(...ops);
}


// --- Canvas Object Arbitraries ---

/**
 * Generates a random GeometricShape.
 */
export function geometricShapeArbitrary(): fc.Arbitrary<GeometricShape> {
  return fc.constantFrom('rectangle', 'ellipse');
}

/**
 * Generates a random StrokeStyle.
 */
export function strokeStyleArbitrary(): fc.Arbitrary<StrokeStyle> {
  return fc.constantFrom('solid', 'dashed');
}

/**
 * Generates a random canvas object creation payload (without id) for any of the three types.
 * Uses fc.oneof to randomly pick between architecture-block, line, and geometric.
 */
export function canvasObjectWithoutIdArbitrary(): fc.Arbitrary<Omit<CanvasObject, 'id'>> {
  return fc.oneof(
    architectureBlockWithoutIdArbitrary(),
    lineObjectWithoutIdArbitrary(),
    geometricObjectWithoutIdArbitrary(),
  );
}

/**
 * Generates a random ArchitectureBlock creation payload (without id).
 */
export function architectureBlockWithoutIdArbitrary(): fc.Arbitrary<Omit<ArchitectureBlock, 'id'>> {
  return serviceTypeArbitrary().chain((st) =>
    fc.record({
      objectType: fc.constant('architecture-block' as const),
      serviceType: fc.constant(st),
      name: fc.string({ minLength: 1, maxLength: 30 }),
      position: pointArbitrary(),
      config: resourceConfigArbitrary(st),
      visualConfig: fc.constant({ ...DEFAULT_BLOCK_VISUAL }),
    })
  );
}

/**
 * Generates a random LineObject creation payload (without id).
 */
export function lineObjectWithoutIdArbitrary(): fc.Arbitrary<Omit<LineObject, 'id'>> {
  return fc.record({
    objectType: fc.constant('line' as const),
    name: fc.string({ minLength: 1, maxLength: 30 }),
    start: pointArbitrary(),
    end: pointArbitrary(),
    visualConfig: fc.constant({ ...DEFAULT_LINE_VISUAL }),
  });
}

/**
 * Generates a random GeometricObject creation payload (without id).
 */
export function geometricObjectWithoutIdArbitrary(): fc.Arbitrary<Omit<GeometricObject, 'id'>> {
  return fc.record({
    objectType: fc.constant('geometric' as const),
    name: fc.string({ minLength: 1, maxLength: 30 }),
    position: pointArbitrary(),
    visualConfig: fc.constant({ ...DEFAULT_GEO_VISUAL }),
  });
}
