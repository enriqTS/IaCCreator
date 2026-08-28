'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useDiagramStore } from '@/store/diagram-store';
import { useToastStore } from '@/store/toast-store';
import { apiClient } from '@/utils/api-client';

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function ImportArchitectureDialog({ open, onClose }: Props) {
  const [content, setContent] = useState('');
  const [pending, setPending] = useState(false);
  const addToast = useToastStore((state) => state.addToast);

  if (!open) return null;

  const handleImport = async () => {
    let architecture: unknown;
    try {
      architecture = JSON.parse(content);
    } catch {
      addToast('Architecture must be valid JSON.', 'error');
      return;
    }
    setPending(true);
    const result = await apiClient.importArchitecture(architecture);
    setPending(false);
    if (!result.ok) {
      addToast(result.error.message, 'error');
      return;
    }
    useDiagramStore.getState().loadDiagramState(result.data.diagram);
    addToast(
      `Imported ${result.data.imported_resource_count} resources and inferred ${result.data.inferred_container_count} containers.`,
      'success',
    );
    setContent('');
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-[min(720px,90vw)] rounded-xl bg-[#1e1e1e] p-6 text-[#e5e5e5] shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="mb-2 text-lg font-semibold">Import Architecture</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Paste an ArchitectureDescription JSON payload. The backend infers Regions and supported semantic containment.
        </p>
        <textarea
          aria-label="Architecture JSON"
          className="h-80 w-full resize-y rounded-md border bg-background p-3 font-mono text-xs"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder='{"project_name":"existing-infrastructure",...}'
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={pending || content.trim() === ''} onClick={() => void handleImport()}>
            {pending ? 'Importing…' : 'Import'}
          </Button>
        </div>
      </div>
    </div>
  );
}
