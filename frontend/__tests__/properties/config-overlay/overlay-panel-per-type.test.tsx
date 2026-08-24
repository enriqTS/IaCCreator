import fc from 'fast-check';
import { resolveConfigOverlayPanel } from '@/components/config/overlay/overlay-registry';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_GEO_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type {
  ArchitectureBlock,
  CanvasObject,
  Connector,
  GeometricObject,
  LineObject,
  ServiceType,
} from '@/types/diagram';

const EMPTY_CONTEXT = {
  canvasObjects: new Map<string, CanvasObject>(),
  connectors: new Map<string, Connector>(),
};

const arbName = fc.string({ minLength: 0, maxLength: 30 });

function block(id: string, serviceType: ServiceType, name = id): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType,
    name,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

describe('Property: the overlay registry picks a panel from the selected type alone', () => {
  const configurable: ServiceType[] = ['lambda', 's3', 'dynamodb', 'api-gateway'];

  test('any architecture block with a schema contributes a panel titled after it', () => {
    fc.assert(
      fc.property(fc.constantFrom(...configurable), arbName, (serviceType, name) => {
        const panel = resolveConfigOverlayPanel(
          block('block-1', serviceType, name),
          EMPTY_CONTEXT,
        );
        expect(panel).not.toBeNull();
        expect(panel!.key).toBe('block-1');
        expect(panel!.title).toBe(name);
      }),
      { numRuns: 100 },
    );
  });

  test('a service the backend serves no schema for still opens its visual panel', () => {
    const schemaless: ServiceType[] = ['clean-rooms', 'data-exchange', 'finspace'];
    fc.assert(
      fc.property(fc.constantFrom(...schemaless), (serviceType) => {
        expect(resolveConfigOverlayPanel(block('b', serviceType), EMPTY_CONTEXT)).not.toBeNull();
      }),
      { numRuns: 50 },
    );
  });

  test('objects with only an appearance still open a panel, labelled by kind', () => {
    const geometric: GeometricObject = {
      id: 'geo-1',
      objectType: 'geometric',
      name: 'shape',
      position: { x: 0, y: 0 },
      visualConfig: { ...DEFAULT_GEO_VISUAL },
      zIndex: 0,
    };
    const panel = resolveConfigOverlayPanel(geometric, EMPTY_CONTEXT);
    expect(panel?.subtitle).toBe('Shape');
    expect(panel?.title).toBe('shape');
  });

  test('nothing selected opens nothing', () => {
    expect(resolveConfigOverlayPanel(null, EMPTY_CONTEXT)).toBeNull();
  });

  test('a line with no connector behind it falls back to its visual panel', () => {
    fc.assert(
      fc.property(arbName, (name) => {
        const line: LineObject = {
          id: 'line-1',
          objectType: 'line',
          name,
          start: { x: 0, y: 0 },
          end: { x: 100, y: 100 },
          sourceAnchor: null,
          targetAnchor: null,
          visualConfig: { ...DEFAULT_LINE_VISUAL },
          zIndex: 0,
        };
        const panel = resolveConfigOverlayPanel(line, EMPTY_CONTEXT);
        expect(panel?.key).toBe('line-1');
        expect(panel?.subtitle).toBe('Line');
      }),
      { numRuns: 50 },
    );
  });
});
