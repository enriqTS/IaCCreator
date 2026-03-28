import type { GeometricShape } from '@/types/diagram';

/**
 * Pure function registry: each geometric shape maps to a function that returns
 * an SVG path `d` attribute string for the given width and height.
 *
 * All coordinates are within [0, w] for x and [0, h] for y.
 * Rectangle and ellipse use special-case paths for backward compatibility.
 */
export const SHAPE_PATH_REGISTRY: Record<GeometricShape, (w: number, h: number) => string> = {
  // --- Basic shapes ---

  rectangle: (w, h) =>
    `M 0 0 L ${w} 0 L ${w} ${h} L 0 ${h} Z`,

  'rounded-rectangle': (w, h) => {
    const r = Math.min(w, h) * 0.15;
    return `M ${r} 0 L ${w - r} 0 Q ${w} 0 ${w} ${r} L ${w} ${h - r} Q ${w} ${h} ${w - r} ${h} L ${r} ${h} Q 0 ${h} 0 ${h - r} L 0 ${r} Q 0 0 ${r} 0 Z`;
  },

  ellipse: (w, h) => {
    const rx = w / 2;
    const ry = h / 2;
    return `M ${rx} 0 A ${rx} ${ry} 0 1 1 ${rx} ${h} A ${rx} ${ry} 0 1 1 ${rx} 0 Z`;
  },

  circle: (w, h) => {
    const r = Math.min(w, h) / 2;
    const cx = w / 2;
    const cy = h / 2;
    return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx} ${cy + r} A ${r} ${r} 0 1 1 ${cx} ${cy - r} Z`;
  },

  // --- Polygons ---

  triangle: (w, h) =>
    `M ${w / 2} 0 L ${w} ${h} L 0 ${h} Z`,

  diamond: (w, h) =>
    `M ${w / 2} 0 L ${w} ${h / 2} L ${w / 2} ${h} L 0 ${h / 2} Z`,

  parallelogram: (w, h) => {
    const offset = w * 0.2;
    return `M ${offset} 0 L ${w} 0 L ${w - offset} ${h} L 0 ${h} Z`;
  },

  trapezoid: (w, h) => {
    const offset = w * 0.2;
    return `M ${offset} 0 L ${w - offset} 0 L ${w} ${h} L 0 ${h} Z`;
  },

  hexagon: (w, h) =>
    `M ${w * 0.25} 0 L ${w * 0.75} 0 L ${w} ${h / 2} L ${w * 0.75} ${h} L ${w * 0.25} ${h} L 0 ${h / 2} Z`,

  octagon: (w, h) => {
    const d = Math.min(w, h) * 0.29;
    return `M ${d} 0 L ${w - d} 0 L ${w} ${d} L ${w} ${h - d} L ${w - d} ${h} L ${d} ${h} L 0 ${h - d} L 0 ${d} Z`;
  },

  pentagon: (w, h) => {
    // Regular pentagon inscribed in the bounding box
    const cx = w / 2;
    const cy = h / 2;
    const rx = w / 2;
    const ry = h / 2;
    const points: [number, number][] = [];
    for (let i = 0; i < 5; i++) {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / 5;
      points.push([cx + rx * Math.cos(angle), cy + ry * Math.sin(angle)]);
    }
    return `M ${points.map(([x, y]) => `${x} ${y}`).join(' L ')} Z`;
  },

  star: (w, h) => {
    const cx = w / 2;
    const cy = h / 2;
    const outerRx = w / 2;
    const outerRy = h / 2;
    const innerRx = w * 0.2;
    const innerRy = h * 0.2;
    const points: [number, number][] = [];
    for (let i = 0; i < 10; i++) {
      const angle = -Math.PI / 2 + (Math.PI * i) / 5;
      const isOuter = i % 2 === 0;
      const rx = isOuter ? outerRx : innerRx;
      const ry = isOuter ? outerRy : innerRy;
      points.push([cx + rx * Math.cos(angle), cy + ry * Math.sin(angle)]);
    }
    return `M ${points.map(([x, y]) => `${x} ${y}`).join(' L ')} Z`;
  },

  cross: (w, h) => {
    const t = Math.min(w, h) / 3;
    const x1 = (w - t) / 2;
    const x2 = (w + t) / 2;
    const y1 = (h - t) / 2;
    const y2 = (h + t) / 2;
    return `M ${x1} 0 L ${x2} 0 L ${x2} ${y1} L ${w} ${y1} L ${w} ${y2} L ${x2} ${y2} L ${x2} ${h} L ${x1} ${h} L ${x1} ${y2} L 0 ${y2} L 0 ${y1} L ${x1} ${y1} Z`;
  },

  // --- Arrows ---

  'arrow-right': (w, h) => {
    const shaft = h * 0.3;
    const shaftTop = (h - shaft) / 2;
    const shaftBot = (h + shaft) / 2;
    const headStart = w * 0.6;
    return `M 0 ${shaftTop} L ${headStart} ${shaftTop} L ${headStart} 0 L ${w} ${h / 2} L ${headStart} ${h} L ${headStart} ${shaftBot} L 0 ${shaftBot} Z`;
  },

  'arrow-left': (w, h) => {
    const shaft = h * 0.3;
    const shaftTop = (h - shaft) / 2;
    const shaftBot = (h + shaft) / 2;
    const headEnd = w * 0.4;
    return `M ${w} ${shaftTop} L ${headEnd} ${shaftTop} L ${headEnd} 0 L 0 ${h / 2} L ${headEnd} ${h} L ${headEnd} ${shaftBot} L ${w} ${shaftBot} Z`;
  },

  'arrow-up': (w, h) => {
    const shaft = w * 0.3;
    const shaftLeft = (w - shaft) / 2;
    const shaftRight = (w + shaft) / 2;
    const headEnd = h * 0.4;
    return `M ${w / 2} 0 L ${w} ${headEnd} L ${shaftRight} ${headEnd} L ${shaftRight} ${h} L ${shaftLeft} ${h} L ${shaftLeft} ${headEnd} L 0 ${headEnd} Z`;
  },

  'arrow-down': (w, h) => {
    const shaft = w * 0.3;
    const shaftLeft = (w - shaft) / 2;
    const shaftRight = (w + shaft) / 2;
    const headStart = h * 0.6;
    return `M ${shaftLeft} 0 L ${shaftRight} 0 L ${shaftRight} ${headStart} L ${w} ${headStart} L ${w / 2} ${h} L 0 ${headStart} L ${shaftLeft} ${headStart} Z`;
  },

  chevron: (w, h) => {
    const indent = w * 0.2;
    return `M 0 0 L ${w - indent} 0 L ${w} ${h / 2} L ${w - indent} ${h} L 0 ${h} L ${indent} ${h / 2} Z`;
  },

  // --- Special shapes ---

  cylinder: (w, h) => {
    const ry = h * 0.12;
    const bodyTop = ry;
    const bodyBot = h - ry;
    return [
      // Top ellipse
      `M 0 ${bodyTop}`,
      `A ${w / 2} ${ry} 0 1 1 ${w} ${bodyTop}`,
      `A ${w / 2} ${ry} 0 1 1 0 ${bodyTop}`,
      // Right side down
      `M ${w} ${bodyTop}`,
      `L ${w} ${bodyBot}`,
      // Bottom ellipse
      `A ${w / 2} ${ry} 0 1 1 0 ${bodyBot}`,
      // Left side up
      `L 0 ${bodyTop}`,
    ].join(' ');
  },

  cloud: (w, h) => {
    // Cloud shape using cubic bezier curves
    return [
      `M ${w * 0.25} ${h * 0.6}`,
      `C ${w * 0.0} ${h * 0.6} ${w * 0.0} ${h * 0.3} ${w * 0.15} ${h * 0.25}`,
      `C ${w * 0.1} ${h * 0.0} ${w * 0.35} ${h * 0.0} ${w * 0.4} ${h * 0.15}`,
      `C ${w * 0.45} ${h * 0.0} ${w * 0.7} ${h * 0.0} ${w * 0.7} ${h * 0.2}`,
      `C ${w * 0.9} ${h * 0.1} ${w * 1.0} ${h * 0.3} ${w * 0.85} ${h * 0.5}`,
      `C ${w * 1.0} ${h * 0.65} ${w * 0.85} ${h * 0.8} ${w * 0.7} ${h * 0.75}`,
      `C ${w * 0.65} ${h * 0.9} ${w * 0.45} ${h * 0.95} ${w * 0.35} ${h * 0.8}`,
      `C ${w * 0.2} ${h * 0.95} ${w * 0.05} ${h * 0.8} ${w * 0.25} ${h * 0.6}`,
      'Z',
    ].join(' ');
  },

  callout: (w, h) => {
    // Rectangular callout with a tail at bottom-left
    const bodyH = h * 0.75;
    const tailW = w * 0.15;
    const tailStart = w * 0.1;
    return `M 0 0 L ${w} 0 L ${w} ${bodyH} L ${tailStart + tailW} ${bodyH} L ${tailStart} ${h} L ${tailStart + tailW * 0.5} ${bodyH} L 0 ${bodyH} Z`;
  },

  // --- Flowchart shapes ---

  document: (w, h) => {
    const waveH = h * 0.1;
    const bodyH = h - waveH;
    return [
      `M 0 0 L ${w} 0 L ${w} ${bodyH}`,
      `C ${w * 0.75} ${bodyH + waveH * 2} ${w * 0.25} ${bodyH - waveH * 0.5} 0 ${bodyH}`,
      'Z',
    ].join(' ');
  },

  process: (w, h) =>
    `M 0 0 L ${w} 0 L ${w} ${h} L 0 ${h} Z`,

  decision: (w, h) =>
    `M ${w / 2} 0 L ${w} ${h / 2} L ${w / 2} ${h} L 0 ${h / 2} Z`,

  data: (w, h) => {
    const skew = w * 0.15;
    return `M ${skew} 0 L ${w} 0 L ${w - skew} ${h} L 0 ${h} Z`;
  },

  'predefined-process': (w, h) => {
    const inset = w * 0.1;
    return [
      // Outer rectangle
      `M 0 0 L ${w} 0 L ${w} ${h} L 0 ${h} Z`,
      // Left vertical line
      `M ${inset} 0 L ${inset} ${h}`,
      // Right vertical line
      `M ${w - inset} 0 L ${w - inset} ${h}`,
    ].join(' ');
  },
};
