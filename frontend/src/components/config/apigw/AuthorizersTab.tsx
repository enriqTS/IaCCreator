'use client';

import { useApigwConfigStore } from '@/store/apigw-config-store';
import CollectionPanel from './CollectionPanel';
import type { AuthorizerItem } from '@/types/apigw-config';

export default function AuthorizersTab() {
  const authorizers = useApigwConfigStore((s) => s.authorizers);
  const selectedItemId = useApigwConfigStore((s) => s.selectedItemId);
  const addAuthorizer = useApigwConfigStore((s) => s.addAuthorizer);
  const selectItem = useApigwConfigStore((s) => s.selectItem);
  const removeAuthorizer = useApigwConfigStore((s) => s.removeAuthorizer);

  const handleAdd = () => {
    addAuthorizer();
    const newAuthorizers = useApigwConfigStore.getState().authorizers;
    const newId = newAuthorizers[newAuthorizers.length - 1]?.id;
    if (newId) {
      selectItem(newId, 'authorizer');
    }
  };

  return (
    <CollectionPanel<AuthorizerItem>
      items={authorizers}
      selectedItemId={selectedItemId}
      onSelect={(id) => selectItem(id, 'authorizer')}
      onAdd={handleAdd}
      onRemove={removeAuthorizer}
      renderSummary={(item) => `${item.name} (${item.type})`}
      addLabel="Add Authorizer"
      emptyMessage="No authorizers configured."
    />
  );
}
