'use client';

import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

interface DetailPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export default function DetailPanel({
  isOpen,
  onClose,
  title,
  children,
}: DetailPanelProps) {
  // Close on Escape key press
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    // Covers the panel it was opened from, so the master list stays where it was
    <div
      data-testid="detail-panel"
      className={cn(
        'absolute inset-0 z-10 flex flex-col rounded-md border bg-background shadow-lg',
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="truncate text-sm font-medium">{title}</span>
        <Button
          variant="ghost"
          size="icon-sm"
          data-testid="detail-panel-close-button"
          onClick={onClose}
          aria-label="Close detail panel"
        >
          <X className="size-4" />
        </Button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4">
        {children}
      </div>
    </div>
  );
}
