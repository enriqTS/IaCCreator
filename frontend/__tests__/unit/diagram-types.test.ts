import { describe, it, expect } from 'vitest';
import { getObjectBounds } from '@/types/diagram';
import type { ArchitectureBlock, LineObject, GeometricObject, Rect, ObjectGroup } from '@/types/diagram';

describe('getObjectBounds', () => {
  it('computes bounds for architecture block (position is center)', () => {
    const block: ArchitectureBlock = {
      id: 'b1',
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'lambda-1',
      position: { x: 100, y: 200 },
      config: {},
      visualConfig: { width: 80, height: 60 },
      zIndex: 0,
    };
    const bounds = getObjectBounds(block);
    expect(bounds).toEqual({ x: 60, y: 170, width: 80, height: 60 });
  });

  it('computes bounds for geometric object (position is center)', () => {
    const geo: GeometricObject = {
      id: 'g1',
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 50, y: 50 },
      visualConfig: { width: 120, height: 80, fill: false, fillColor: '#000', borderColor: '#fff', borderWidth: 2, shape: 'rectangle' },
      zIndex: 1,
    };
    const bounds = getObjectBounds(geo);
    expect(bounds).toEqual({ x: -10, y: 10, width: 120, height: 80 });
  });

  it('computes bounds for line object (min/max of start/end)', () => {
    const line: LineObject = {
      id: 'l1',
      objectType: 'line',
      name: 'line-1',
      start: { x: 10, y: 20 },
      end: { x: 110, y: 80 },
      visualConfig: { color: '#fff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false },
      zIndex: 2,
    };
    const bounds = getObjectBounds(line);
    expect(bounds).toEqual({ x: 10, y: 20, width: 100, height: 60 });
  });

  it('handles line with reversed start/end', () => {
    const line: LineObject = {
      id: 'l2',
      objectType: 'line',
      name: 'line-2',
      start: { x: 200, y: 300 },
      end: { x: 50, y: 100 },
      visualConfig: { color: '#fff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false },
      zIndex: 0,
    };
    const bounds = getObjectBounds(line);
    expect(bounds).toEqual({ x: 50, y: 100, width: 150, height: 200 });
  });

  it('handles line with zero-length (same start and end)', () => {
    const line: LineObject = {
      id: 'l3',
      objectType: 'line',
      name: 'line-3',
      start: { x: 50, y: 50 },
      end: { x: 50, y: 50 },
      visualConfig: { color: '#fff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false },
      zIndex: 0,
    };
    const bounds = getObjectBounds(line);
    expect(bounds).toEqual({ x: 50, y: 50, width: 0, height: 0 });
  });
});

describe('Type structure validation', () => {
  it('ObjectGroup has required fields', () => {
    const group: ObjectGroup = {
      id: 'group-1',
      name: 'Group 1',
      memberIds: ['obj-1', 'obj-2'],
    };
    expect(group.id).toBe('group-1');
    expect(group.name).toBe('Group 1');
    expect(group.memberIds).toEqual(['obj-1', 'obj-2']);
  });

  it('Rect has required fields', () => {
    const rect: Rect = { x: 10, y: 20, width: 100, height: 50 };
    expect(rect.x).toBe(10);
    expect(rect.y).toBe(20);
    expect(rect.width).toBe(100);
    expect(rect.height).toBe(50);
  });

  it('CanvasObject interfaces include zIndex and optional groupId', () => {
    const block: ArchitectureBlock = {
      id: 'b1',
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'test',
      position: { x: 0, y: 0 },
      config: {},
      visualConfig: { width: 80, height: 80 },
      zIndex: 5,
      groupId: 'g1',
    };
    expect(block.zIndex).toBe(5);
    expect(block.groupId).toBe('g1');

    const line: LineObject = {
      id: 'l1',
      objectType: 'line',
      name: 'test',
      start: { x: 0, y: 0 },
      end: { x: 10, y: 10 },
      visualConfig: { color: '#fff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false },
      zIndex: 3,
    };
    expect(line.zIndex).toBe(3);
    expect(line.groupId).toBeUndefined();
  });
});
