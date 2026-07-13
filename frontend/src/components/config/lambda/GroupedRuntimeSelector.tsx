'use client';

import { useState } from 'react';
import { Check, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RuntimeOption {
  value: string;
  label: string;
  group?: string;
}

interface GroupedRuntimeSelectorProps {
  options: RuntimeOption[];
  value: string;
  onChange: (value: string) => void;
}

interface RuntimeGroup {
  name: string;
  options: RuntimeOption[];
}

/**
 * Collapsible-group runtime picker that groups runtime options by family.
 *
 * Displays the latest (first) version of each family prominently.
 * If a family has multiple versions, shows an expand control to reveal older ones.
 * Selecting any option sets the value and collapses the group.
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.7
 */
export default function GroupedRuntimeSelector({
  options,
  value,
  onChange,
}: GroupedRuntimeSelectorProps) {
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

  // Group options by their `group` field, preserving source order
  const groups: RuntimeGroup[] = [];
  const groupMap = new Map<string, RuntimeOption[]>();

  for (const option of options) {
    const groupName = option.group ?? 'Other';
    if (!groupMap.has(groupName)) {
      groupMap.set(groupName, []);
      groups.push({ name: groupName, options: groupMap.get(groupName)! });
    }
    groupMap.get(groupName)!.push(option);
  }

  const handleSelect = (optionValue: string) => {
    onChange(optionValue);
    setExpandedGroup(null);
  };

  const toggleGroup = (groupName: string) => {
    setExpandedGroup((prev) => (prev === groupName ? null : groupName));
  };

  return (
    <div className="flex flex-col gap-1" role="listbox" aria-label="Runtime selector">
      {groups.map((group) => {
        const [latest, ...olderVersions] = group.options;
        const hasOlderVersions = olderVersions.length > 0;
        const isExpanded = expandedGroup === group.name;
        const isLatestSelected = value === latest.value;
        const isAnyOlderSelected = olderVersions.some((o) => o.value === value);

        return (
          <div key={group.name} className="flex flex-col">
            {/* Group heading with latest version */}
            <div
              role="option"
              aria-selected={isLatestSelected}
              tabIndex={0}
              onClick={() => handleSelect(latest.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(latest.value);
                }
              }}
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors',
                'border-border bg-muted/30 hover:bg-muted/60',
                (isLatestSelected || isAnyOlderSelected) &&
                  'border-primary/50 bg-muted/50 ring-1 ring-primary/30'
              )}
            >
              {/* Selection indicator */}
              <span className="flex size-4 shrink-0 items-center justify-center">
                {isLatestSelected && <Check className="size-3.5 text-primary" />}
              </span>

              {/* Group label + latest version */}
              <span className="flex-1 truncate">
                <span className="font-medium text-muted-foreground">{group.name}:</span>{' '}
                {latest.label}
              </span>

              {/* Expand control for groups with multiple versions */}
              {hasOlderVersions && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleGroup(group.name);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.stopPropagation();
                      e.preventDefault();
                      toggleGroup(group.name);
                    }
                  }}
                  className="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-expanded={isExpanded}
                  aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${group.name} versions`}
                >
                  {isExpanded ? (
                    <ChevronDown className="size-4" />
                  ) : (
                    <ChevronRight className="size-4" />
                  )}
                </button>
              )}
            </div>

            {/* Older versions (expanded state) */}
            {hasOlderVersions && isExpanded && (
              <div className="ml-6 mt-0.5 flex flex-col gap-0.5">
                {olderVersions.map((option) => {
                  const isSelected = value === option.value;
                  return (
                    <div
                      key={option.value}
                      role="option"
                      aria-selected={isSelected}
                      tabIndex={0}
                      onClick={() => handleSelect(option.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          handleSelect(option.value);
                        }
                      }}
                      className={cn(
                        'flex cursor-pointer items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors',
                        'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                        isSelected && 'bg-muted/50 text-foreground'
                      )}
                    >
                      <span className="flex size-4 shrink-0 items-center justify-center">
                        {isSelected && <Check className="size-3.5 text-primary" />}
                      </span>
                      <span className="truncate">{option.label}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
