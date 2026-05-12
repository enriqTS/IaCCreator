'use client';

import { useApigwConfigStore } from '@/store/apigw-config-store';
import CollectionPanel from './CollectionPanel';
import type { StageItem } from '@/types/apigw-config';

export default function StagesTab() {
  const stages = useApigwConfigStore((s) => s.stages);
  const selectedItemId = useApigwConfigStore((s) => s.selectedItemId);
  const addStage = useApigwConfigStore((s) => s.addStage);
  const selectItem = useApigwConfigStore((s) => s.selectItem);
  const removeStage = useApigwConfigStore((s) => s.removeStage);

  const handleAdd = () => {
    addStage();
    const newStages = useApigwConfigStore.getState().stages;
    const newId = newStages[newStages.length - 1]?.id;
    if (newId) {
      selectItem(newId, 'stage');
    }
  };

  return (
    <CollectionPanel<StageItem>
      items={stages}
      selectedItemId={selectedItemId}
      onSelect={(id) => selectItem(id, 'stage')}
      onAdd={handleAdd}
      onRemove={removeStage}
      renderSummary={(item) => item.name}
      addLabel="Add Stage"
      emptyMessage="No stages configured. A $default stage will be generated."
    />
  );
}
