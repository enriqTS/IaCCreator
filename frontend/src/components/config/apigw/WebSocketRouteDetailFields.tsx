'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import type { WebSocketRouteItem } from '@/types/apigw-config';

interface WebSocketRouteDetailFieldsProps {
  route: WebSocketRouteItem;
  onUpdate: (updates: Partial<WebSocketRouteItem>) => void;
}

export default function WebSocketRouteDetailFields({ route, onUpdate }: WebSocketRouteDetailFieldsProps) {
  // Debounced route_key state
  const [routeKeyValue, setRouteKeyValue] = useState(route.route_key);

  // Sync local state when route prop changes
  useEffect(() => {
    setRouteKeyValue(route.route_key);
  }, [route.id, route.route_key]);

  // Debounce route_key
  useEffect(() => {
    if (routeKeyValue === route.route_key) return;
    const timer = setTimeout(() => {
      onUpdate({ route_key: routeKeyValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [routeKeyValue]); // eslint-disable-line react-hooks/exhaustive-deps

  const isConnectRoute = route.route_key === '$connect';
  const authorizationDisabled = !isConnectRoute;

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Route Key */}
      <div className="flex flex-col gap-1.5">
        <Label>Route Key</Label>
        <Input
          type="text"
          value={routeKeyValue}
          onChange={(e) => setRouteKeyValue(e.target.value)}
          placeholder="$default"
          className="w-full"
          disabled={route.is_special}
        />
        {route.is_special && (
          <span className="text-xs text-muted-foreground">
            Special routes cannot be renamed.
          </span>
        )}
      </div>

      {/* Authorization Enabled */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <Checkbox
            id="authorization-enabled"
            checked={route.authorization_enabled}
            onCheckedChange={(checked) => onUpdate({ authorization_enabled: checked === true })}
            disabled={authorizationDisabled}
          />
          <Label
            htmlFor="authorization-enabled"
            className={authorizationDisabled ? 'opacity-50' : ''}
          >
            Authorization Enabled
          </Label>
        </div>
        <span className="text-xs text-muted-foreground">
          Authorization is only available for the $connect route.
        </span>
      </div>
    </div>
  );
}
