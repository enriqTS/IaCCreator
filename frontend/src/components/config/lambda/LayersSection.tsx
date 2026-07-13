'use client';

import { useState } from 'react';
import { ChevronUp, ChevronDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const LAYER_ARN_REGEX =
  /^arn:aws:lambda:[a-z]{2}(-gov)?-[a-z]+-\d:\d{12}:layer:[a-zA-Z0-9_-]+:\d+$/;

const MAX_LAYERS = 5;

/**
 * Parse a Lambda Layer ARN and extract the `<layer-name>:<version>` label.
 * Returns the raw ARN if it doesn't match the expected format.
 */
export function parseLayerLabel(arn: string): string {
  if (!LAYER_ARN_REGEX.test(arn)) {
    return arn;
  }
  const parts = arn.split(':');
  // ARN structure: arn:aws:lambda:<region>:<account-id>:layer:<layer-name>:<version>
  // Indices:        0   1    2       3         4         5       6            7
  const layerName = parts[6];
  const version = parts[7];
  return `${layerName}:${version}`;
}

interface LayersSectionProps {
  layers: string[];
  onChange: (layers: string[]) => void;
}

/**
 * Layers list within Lambda configuration panel.
 * Provides ARN input with validation, reordering controls, and a max-5 limit.
 */
export default function LayersSection({ layers, onChange }: LayersSectionProps) {
  const [inputValue, setInputValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const atLimit = layers.length >= MAX_LAYERS;

  const handleAdd = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    if (!LAYER_ARN_REGEX.test(trimmed)) {
      setValidationError(
        'Invalid ARN format. Expected: arn:aws:lambda:<region>:<account-id>:layer:<name>:<version>'
      );
      return;
    }

    if (atLimit) return;

    onChange([...layers, trimmed]);
    setInputValue('');
    setValidationError(null);
  };

  const handleRemove = (index: number) => {
    onChange(layers.filter((_, i) => i !== index));
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const next = [...layers];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    onChange(next);
  };

  const handleMoveDown = (index: number) => {
    if (index === layers.length - 1) return;
    const next = [...layers];
    [next[index], next[index + 1]] = [next[index + 1], next[index]];
    onChange(next);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Label className="text-xs font-medium text-muted-foreground">Layers</Label>

      {/* Layer rows */}
      {layers.length > 0 && (
        <div className="flex flex-col gap-1">
          {layers.map((arn, index) => (
            <div
              key={`${arn}-${index}`}
              className="flex items-center gap-1 rounded-md border border-border bg-muted/30 px-2 py-1.5 text-sm"
            >
              <span className="min-w-0 flex-1 truncate" title={arn}>
                {parseLayerLabel(arn)}
              </span>

              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => handleMoveUp(index)}
                disabled={index === 0}
                aria-label="Move layer up"
                className="shrink-0 text-muted-foreground hover:text-foreground"
              >
                <ChevronUp className="size-3" />
              </Button>

              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => handleMoveDown(index)}
                disabled={index === layers.length - 1}
                aria-label="Move layer down"
                className="shrink-0 text-muted-foreground hover:text-foreground"
              >
                <ChevronDown className="size-3" />
              </Button>

              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => handleRemove(index)}
                aria-label="Remove layer"
                className="shrink-0 text-muted-foreground hover:text-destructive"
              >
                <X className="size-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add input */}
      <div className="flex flex-col gap-1">
        <div className="flex gap-1">
          <Input
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              if (validationError) setValidationError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="arn:aws:lambda:region:account:layer:name:version"
            className="h-7 text-xs"
            disabled={atLimit}
            aria-invalid={!!validationError}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleAdd}
            disabled={atLimit || !inputValue.trim()}
            className="shrink-0"
          >
            Add
          </Button>
        </div>

        {validationError && (
          <p className="text-xs text-destructive">{validationError}</p>
        )}

        {atLimit && (
          <p className="text-xs text-muted-foreground">Maximum of 5 layers reached</p>
        )}
      </div>
    </div>
  );
}
