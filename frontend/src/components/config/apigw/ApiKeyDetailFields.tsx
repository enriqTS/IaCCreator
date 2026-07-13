'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import type { ApiKeyItem } from '@/types/apigw-config';

interface ApiKeyDetailFieldsProps {
  apiKey: ApiKeyItem;
  onUpdate: (updates: Partial<ApiKeyItem>) => void;
}

export default function ApiKeyDetailFields({ apiKey, onUpdate }: ApiKeyDetailFieldsProps) {
  // Debounced text states
  const [nameValue, setNameValue] = useState(apiKey.name);
  const [descriptionValue, setDescriptionValue] = useState(apiKey.description ?? '');
  const [valueValue, setValueValue] = useState(apiKey.value ?? '');

  // Sync local state when apiKey prop changes
  useEffect(() => {
    setNameValue(apiKey.name);
  }, [apiKey.id, apiKey.name]);

  useEffect(() => {
    setDescriptionValue(apiKey.description ?? '');
  }, [apiKey.id, apiKey.description]);

  useEffect(() => {
    setValueValue(apiKey.value ?? '');
  }, [apiKey.id, apiKey.value]);

  // Debounce name input
  useEffect(() => {
    if (nameValue === apiKey.name) return;
    const timer = setTimeout(() => {
      onUpdate({ name: nameValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [nameValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce description input
  useEffect(() => {
    if (descriptionValue === (apiKey.description ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ description: descriptionValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [descriptionValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce value input
  useEffect(() => {
    if (valueValue === (apiKey.value ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ value: valueValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [valueValue]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Name */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`api-key-name-${apiKey.id}`}>Name *</Label>
        <Input
          id={`api-key-name-${apiKey.id}`}
          type="text"
          value={nameValue}
          onChange={(e) => setNameValue(e.target.value)}
          placeholder="my-api-key"
          maxLength={128}
          pattern="[a-zA-Z0-9\-_]+"
          className="w-full"
        />
        <span className="text-xs text-muted-foreground">
          1–128 alphanumeric, hyphen, or underscore characters
        </span>
      </div>

      {/* Description */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`api-key-description-${apiKey.id}`}>Description</Label>
        <textarea
          id={`api-key-description-${apiKey.id}`}
          className="min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:border-ring focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30"
          value={descriptionValue}
          onChange={(e) => setDescriptionValue(e.target.value)}
          placeholder="Optional description for this API key"
          maxLength={1024}
        />
        <span className="text-xs text-muted-foreground">
          0–1024 characters
        </span>
      </div>

      {/* Value Mode */}
      <div className="flex flex-col gap-1.5">
        <Label>Value Mode</Label>
        <RadioGroup
          value={apiKey.value_mode}
          onValueChange={(value) =>
            onUpdate({
              value_mode: value as ApiKeyItem['value_mode'],
              ...(value === 'auto' ? { value: undefined } : {}),
            })
          }
        >
          <div className="flex items-center gap-2">
            <RadioGroupItem value="auto" id={`api-key-mode-auto-${apiKey.id}`} />
            <Label htmlFor={`api-key-mode-auto-${apiKey.id}`} className="cursor-pointer font-normal">
              Auto-generated
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <RadioGroupItem value="user_specified" id={`api-key-mode-user-${apiKey.id}`} />
            <Label htmlFor={`api-key-mode-user-${apiKey.id}`} className="cursor-pointer font-normal">
              User-specified
            </Label>
          </div>
        </RadioGroup>
      </div>

      {/* Value (conditional — shown only when user_specified) */}
      {apiKey.value_mode === 'user_specified' && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`api-key-value-${apiKey.id}`}>Value</Label>
          <Input
            id={`api-key-value-${apiKey.id}`}
            type="text"
            value={valueValue}
            onChange={(e) => setValueValue(e.target.value)}
            placeholder="Enter API key value"
            minLength={20}
            maxLength={128}
            className="w-full"
          />
          <span className="text-xs text-muted-foreground">
            20–128 characters
          </span>
        </div>
      )}
    </div>
  );
}
