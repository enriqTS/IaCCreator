'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useApigwConfigStore } from '@/store/apigw-config-store';
import type { RouteItem } from '@/types/apigw-config';
import MethodToggleGroup from './MethodToggleGroup';

interface RouteDetailFieldsProps {
  route: RouteItem;
  onUpdate: (updates: Partial<RouteItem>) => void;
}

const HTTP_METHODS = ['ANY', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'] as const;

const INTEGRATION_TYPES = [
  { value: 'AWS_PROXY', label: 'Lambda (AWS_PROXY)' },
  { value: 'HTTP_PROXY', label: 'HTTP Proxy' },
  { value: 'HTTP', label: 'HTTP Custom' },
  { value: 'MOCK', label: 'Mock' },
] as const;

const PAYLOAD_FORMAT_VERSIONS = ['1.0', '2.0'] as const;

export default function RouteDetailFields({ route, onUpdate }: RouteDetailFieldsProps) {
  const authorizers = useApigwConfigStore((s) => s.authorizers);

  // Debounced text states
  const [pathValue, setPathValue] = useState(route.path);
  const [targetUriValue, setTargetUriValue] = useState(route.target_service_uri ?? '');
  const [routeResponseKeyValue, setRouteResponseKeyValue] = useState(route.route_response_key ?? '');

  // Sync local state when route prop changes
  useEffect(() => {
    setPathValue(route.path);
  }, [route.id, route.path]);

  useEffect(() => {
    setTargetUriValue(route.target_service_uri ?? '');
  }, [route.id, route.target_service_uri]);

  useEffect(() => {
    setRouteResponseKeyValue(route.route_response_key ?? '');
  }, [route.id, route.route_response_key]);

  // Debounce path input
  useEffect(() => {
    if (pathValue === route.path) return;
    const timer = setTimeout(() => {
      onUpdate({ path: pathValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [pathValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce target URI input
  useEffect(() => {
    if (targetUriValue === (route.target_service_uri ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ target_service_uri: targetUriValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [targetUriValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce route response key input
  useEffect(() => {
    if (routeResponseKeyValue === (route.route_response_key ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ route_response_key: routeResponseKeyValue || undefined });
    }, 300);
    return () => clearTimeout(timer);
  }, [routeResponseKeyValue]); // eslint-disable-line react-hooks/exhaustive-deps

  const showIntegrationMethod =
    route.integration_type === 'HTTP_PROXY' || route.integration_type === 'HTTP';
  const showPayloadFormatVersion = route.integration_type === 'AWS_PROXY';
  const showTargetUri = route.integration_type && route.integration_type !== 'MOCK';

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Methods */}
      <div className="flex flex-col gap-1.5">
        <Label>Methods</Label>
        <MethodToggleGroup
          value={route.methods}
          onChange={(methods) => onUpdate({ methods })}
        />
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
          value={route.integration_type ?? '__none__'}
          onValueChange={(value) =>
            onUpdate({
              integration_type: value === '__none__' ? undefined : value as RouteItem['integration_type'],
              ...(value !== 'HTTP_PROXY' && value !== 'HTTP' ? { integration_method: undefined } : {}),
              ...(value !== 'AWS_PROXY' ? { payload_format_version: undefined } : {}),
              ...(value === 'MOCK' || value === '__none__' ? { target_service_uri: undefined } : {}),
            })
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select integration..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">None</SelectItem>
            {INTEGRATION_TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Target Service URI (shown for non-MOCK integrations) */}
      {showTargetUri && (
        <div className="flex flex-col gap-1.5">
          <Label>
            {route.integration_type === 'AWS_PROXY' ? 'Lambda Function ARN / Service URI' : 'Target URL'}
          </Label>
          <Input
            type="text"
            value={targetUriValue}
            onChange={(e) => setTargetUriValue(e.target.value)}
            placeholder={
              route.integration_type === 'AWS_PROXY'
                ? 'arn:aws:lambda:us-east-1:123456789:function:my-fn'
                : 'https://api.example.com/endpoint'
            }
            className="w-full"
          />
        </div>
      )}

      {/* Integration Method — dropdown (shown for HTTP_PROXY / HTTP) */}
      {showIntegrationMethod && (
        <div className="flex flex-col gap-1.5">
          <Label>Integration Method</Label>
          <Select
            value={route.integration_method ?? 'ANY'}
            onValueChange={(value) => onUpdate({ integration_method: value as RouteItem['integration_method'] })}
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

      {/* Authorizer */}
      <div className="flex flex-col gap-1.5">
        <Label>Authorizer</Label>
        <Select
          value={route.authorizer_name ?? '__none__'}
          onValueChange={(value) => onUpdate({ authorizer_name: value === '__none__' ? undefined : value })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="None (public)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">None (public)</SelectItem>
            {authorizers.map((auth) => (
              <SelectItem key={auth.id} value={auth.name}>
                {auth.name} ({auth.type})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {authorizers.length === 0 && (
          <span className="text-xs text-muted-foreground">
            Add authorizers in the Authorizers tab first.
          </span>
        )}
      </div>

      {/* API Key Required */}
      <div className="flex items-center gap-2">
        <Checkbox
          id={`route-api-key-${route.id}`}
          checked={route.api_key_required ?? false}
          onCheckedChange={(checked) => onUpdate({ api_key_required: checked === true })}
        />
        <Label htmlFor={`route-api-key-${route.id}`} className="cursor-pointer">
          Require API Key
        </Label>
      </div>

      {/* Route Response Key */}
      <div className="flex flex-col gap-1.5">
        <Label>Route Response Key</Label>
        <Input
          type="text"
          value={routeResponseKeyValue}
          onChange={(e) => setRouteResponseKeyValue(e.target.value)}
          placeholder="$default"
          className="w-full"
        />
        <span className="text-xs text-muted-foreground">
          Generates an aws_apigatewayv2_route_response resource when set.
        </span>
      </div>

      {/* Request Parameters */}
      {route.request_parameters && Object.keys(route.request_parameters).length > 0 && (
        <div className="flex flex-col gap-1.5">
          <Label>Request Parameters</Label>
          <div className="rounded-md border p-2">
            {Object.entries(route.request_parameters).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2 text-xs">
                <span className="font-mono text-muted-foreground">{key}</span>
                <span className="text-muted-foreground">&rarr;</span>
                <span className="font-mono">{value}</span>
              </div>
            ))}
          </div>
          <span className="text-xs text-muted-foreground">
            Route-level request parameter mappings (max 50 entries).
          </span>
        </div>
      )}
    </div>
  );
}
