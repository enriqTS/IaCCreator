'use client';

import { useApigwConfigStore } from '@/store/apigw-config-store';
import CollectionPanel from './CollectionPanel';
import type { ApiKeyItem } from '@/types/apigw-config';

const MAX_API_KEYS = 10;

export default function ApiKeysTab() {
  const apiKeys = useApigwConfigStore((s) => s.api_keys);
  const selectedItemId = useApigwConfigStore((s) => s.selectedItemId);
  const addApiKey = useApigwConfigStore((s) => s.addApiKey);
  const selectItem = useApigwConfigStore((s) => s.selectItem);
  const removeApiKey = useApigwConfigStore((s) => s.removeApiKey);

  const handleAdd = () => {
    if (apiKeys.length >= MAX_API_KEYS) return;
    addApiKey();
    const newKeys = useApigwConfigStore.getState().api_keys;
    const newId = newKeys[newKeys.length - 1]?.id;
    if (newId) {
      selectItem(newId, 'api_key');
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <CollectionPanel<ApiKeyItem>
        items={apiKeys}
        selectedItemId={selectedItemId}
        onSelect={(id) => selectItem(id, 'api_key')}
        onAdd={handleAdd}
        onRemove={removeApiKey}
        renderSummary={(item) => (
          <span className="flex items-center gap-1.5">
            <span aria-hidden="true">🔑</span>
            <span className="truncate">{item.name || '(unnamed)'}</span>
            <span className="ml-auto shrink-0 text-xs text-muted-foreground">
              {item.value_mode === 'auto' ? 'Auto' : 'Manual'}
            </span>
          </span>
        )}
        addLabel="Add API Key"
        emptyMessage="No API keys configured. Add an API key to get started."
      />
      {apiKeys.length >= MAX_API_KEYS && (
        <p className="text-center text-xs text-muted-foreground">
          Maximum of {MAX_API_KEYS} API keys reached.
        </p>
      )}
    </div>
  );
}
