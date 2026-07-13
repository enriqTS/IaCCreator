'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const ALL_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'ANY'] as const;

type HttpMethod = (typeof ALL_METHODS)[number];

interface MethodToggleGroupProps {
  value: string[];
  onChange: (methods: string[]) => void;
}

/**
 * Reusable multi-select button group for HTTP methods.
 *
 * Implements ANY mutual exclusivity:
 * - Selecting ANY deselects all other methods
 * - Selecting any other method deselects ANY
 * - At least one method must always be selected (empty selection not allowed)
 */
export default function MethodToggleGroup({ value, onChange }: MethodToggleGroupProps) {
  const handleToggle = (method: HttpMethod) => {
    if (method === 'ANY') {
      // Selecting ANY deselects all others
      if (!value.includes('ANY')) {
        onChange(['ANY']);
      }
      // If ANY is already selected and it's the only one, don't allow deselection
      return;
    }

    // Selecting a non-ANY method
    const withoutAny = value.filter((m) => m !== 'ANY');

    if (withoutAny.includes(method)) {
      // Deselecting this method — ensure at least one remains
      const next = withoutAny.filter((m) => m !== method);
      if (next.length === 0) return; // Don't allow empty selection
      onChange(next);
    } else {
      // Adding this method — remove ANY if present
      onChange([...withoutAny, method]);
    }
  };

  return (
    <div className="flex flex-wrap gap-1">
      {ALL_METHODS.map((method) => {
        const isSelected = value.includes(method);
        return (
          <Button
            key={method}
            type="button"
            size="xs"
            variant={isSelected ? 'default' : 'outline'}
            className={cn('min-w-[3rem] text-xs')}
            onClick={() => handleToggle(method)}
            aria-pressed={isSelected}
          >
            {method}
          </Button>
        );
      })}
    </div>
  );
}
