import { describe, expect, it } from 'vitest';
import { categoriesWithContainers } from '@/data/object-catalog';

describe('categoriesWithContainers', () => {
  it('builds architecture boundaries entirely from backend definitions', () => {
    const categories = categoriesWithContainers([
      { container_type: 'account', display_name: 'AWS Account' },
      { container_type: 'region', display_name: 'AWS Region' },
    ]);
    const scopes = categories.find((category) => category.category === 'Architecture Scopes');

    expect(scopes?.items.map((item) => item.name)).toEqual(['AWS Account', 'AWS Region']);
    expect(scopes?.items[0].tool).toEqual({
      type: 'place-semantic-container',
      containerType: 'account',
    });
  });
});
