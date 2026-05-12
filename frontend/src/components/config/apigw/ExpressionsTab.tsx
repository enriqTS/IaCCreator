'use client';

import { useApigwConfigStore } from '@/store/apigw-config-store';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import CollectionPanel from './CollectionPanel';
import type { WebSocketRouteItem } from '@/types/apigw-config';

export default function ExpressionsTab() {
  const websocketRoutes = useApigwConfigStore((s) => s.websocket_routes);
  const routeSelectionExpression = useApigwConfigStore((s) => s.route_selection_expression);
  const selectedItemId = useApigwConfigStore((s) => s.selectedItemId);
  const addWebSocketRoute = useApigwConfigStore((s) => s.addWebSocketRoute);
  const selectItem = useApigwConfigStore((s) => s.selectItem);
  const removeWebSocketRoute = useApigwConfigStore((s) => s.removeWebSocketRoute);
  const updateSettings = useApigwConfigStore((s) => s.updateSettings);

  const handleAdd = () => {
    addWebSocketRoute();
    const newRoutes = useApigwConfigStore.getState().websocket_routes;
    const newId = newRoutes[newRoutes.length - 1]?.id;
    if (newId) {
      selectItem(newId, 'websocket_route');
    }
  };

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="route-selection-expression">Route Selection Expression</Label>
        <Input
          id="route-selection-expression"
          type="text"
          value={routeSelectionExpression}
          onChange={(e) => updateSettings({ route_selection_expression: e.target.value })}
          placeholder="$request.body.action"
        />
      </div>

      <CollectionPanel<WebSocketRouteItem>
        items={websocketRoutes}
        selectedItemId={selectedItemId}
        onSelect={(id) => selectItem(id, 'websocket_route')}
        onAdd={handleAdd}
        onRemove={removeWebSocketRoute}
        renderSummary={(item) => item.route_key || '(empty)'}
        addLabel="Add Route Key"
        emptyMessage="No custom routes configured."
        canRemove={(item) => !item.is_special}
        removeDisabledTooltip="Special routes cannot be removed"
      />
    </div>
  );
}
