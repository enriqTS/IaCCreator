'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { RouteItem } from '@/types/apigw-config';

interface RouteDetailFieldsProps {
  route: RouteItem;
  onUpdate: (updates: Partial<RouteItem>) => void;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'ANY'] as const;
const INTEGRATION_TYPES = ['AWS_PROXY', 'HTTP_PROXY', 'HTTP', 'MOCK'] as const;
const PAYLOAD_FORMAT_VERSIONS = ['1.0', '2.0'] as const;

export default function RouteDetailFields({ route, onUpdate }: RouteDetailFieldsProps) {
  // Debounced path state
  const [pathValue, setPathValue] = useState(route.path);
  const [integrationMethodValue, setIntegrationMethodValue] = useState(route.integration_method ?? '');

  // Sync local state when route prop changes (e.g. switching selected item)
  useEffect(() => {
    setPathValue(route.path);
  }, [route.id, route.path]);

  useEffect(() => {
    setIntegrationMethodValue(route.integration_method ?? '');
  }, [route.id, route.integration_method]);

  // Debounce path input
  useEffect(() => {
    if (pathValue === route.path) return;
    const timer = setTimeout(() => {
      onUpdate({ path: pathValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [pathValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce integration_method input
  useEffect(() => {
    if (integrationMethodValue === (route.integration_method ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ integration_method: integrationMethodValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [integrationMethodValue]); // eslint-disable-line react-hooks/exhaustive-deps

  const showIntegrationMethod =
    route.integration_type === 'HTTP_PROXY' || route.integration_type === 'HTTP';
  const showPayloadFormatVersion = route.integration_type === 'AWS_PROXY';

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Method */}
      <div className="flex flex-col gap-1.5">
        <Label>Method</Label>
        <Select
          value={route.method}
          onValueChange={(value) => onUpdate({ method: value as RouteItem['method'] })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select method" />
          </SelectTrigger>
          <SelectContent>
            {HTTP_METHODS.map((method) => (
              <SelectItem key={method} value={method}>
                {method}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Path */}
      <div className="flex flex-col gap-1.5">
        <Label>Path</Label>
        <Input
          type="text"
          value={pathValue}
          onChange={(e) => setPathValue(e.target.value)}
          placeholder="/users/{id}"
          className="w-full"
        />
      </div>

      {/* Integration Type */}
      <div className="flex flex-col gap-1.5">
        <Label>Integration Type</Label>
        <Select
          value={route.integration_type ?? ''}
          onValueChange={(value) =>
            onUpdate({
              integration_type: (value || undefined) as RouteItem['integration_type'],
              // Clear dependent fields when type changes
              ...(value !== 'HTTP_PROXY' && value !== 'HTTP' ? { integration_method: undefined } : {}),
              ...(value !== 'AWS_PROXY' ? { payload_format_version: undefined } : {}),
            })
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="None" />
          </SelectTrigger>
          <SelectContent>
            {INTEGRATION_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Integration Method (shown for HTTP_PROXY / HTTP) */}
      {showIntegrationMethod && (
        <div className="flex flex-col gap-1.5">
          <Label>Integration Method</Label>
          <Input
            type="text"
            value={integrationMethodValue}
            onChange={(e) => setIntegrationMethodValue(e.target.value)}
            placeholder="GET"
            className="w-full"
          />
        </div>
      )}

      {/* Payload Format Version (shown for AWS_PROXY) */}
      {showPayloadFormatVersion && (
        <div className="flex flex-col gap-1.5">
          <Label>Payload Format Version</Label>
          <Select
            value={route.payload_format_version ?? '2.0'}
            onValueChange={(value) =>
              onUpdate({ payload_format_version: value as '1.0' | '2.0' })
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select version" />
            </SelectTrigger>
            <SelectContent>
              {PAYLOAD_FORMAT_VERSIONS.map((version) => (
                <SelectItem key={version} value={version}>
                  {version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}
