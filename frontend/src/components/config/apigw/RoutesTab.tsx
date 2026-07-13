'use client';

import { useApigwConfigStore } from '@/store/apigw-config-store';
import CollectionPanel from './CollectionPanel';
import type { RouteItem } from '@/types/apigw-config';

export default function RoutesTab() {
  const routes = useApigwConfigStore((s) => s.routes);
  const selectedItemId = useApigwConfigStore((s) => s.selectedItemId);
  const addRoute = useApigwConfigStore((s) => s.addRoute);
  const selectItem = useApigwConfigStore((s) => s.selectItem);
  const removeRoute = useApigwConfigStore((s) => s.removeRoute);

  const handleAdd = () => {
    addRoute();
    const newRoutes = useApigwConfigStore.getState().routes;
    const newId = newRoutes[newRoutes.length - 1]?.id;
    if (newId) {
      selectItem(newId, 'route');
    }
  };

  return (
    <CollectionPanel<RouteItem>
      items={routes}
      selectedItemId={selectedItemId}
      onSelect={(id) => selectItem(id, 'route')}
      onAdd={handleAdd}
      onRemove={removeRoute}
      renderSummary={(item) => {
        const label = item.methods.join(', ') + ' ' + item.path;
        const truncated = label.length > 30 ? label.slice(0, 27) + '...' : label;
        return item.api_key_required ? `🔑 ${truncated}` : truncated;
      }}
      addLabel="Add Route"
      emptyMessage="No routes configured. Add a route to get started."
    />
  );
}
