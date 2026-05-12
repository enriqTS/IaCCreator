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
  sidebarWidth: number;
  sidebarSide: 'left' | 'right';
}

export default function DetailPanel({
  isOpen,
  onClose,
  title,
  children,
  sidebarWidth,
  sidebarSide,
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

  const isLeft = sidebarSide === 'left';

  return (
    <div
      data-testid="detail-panel"
      className={cn(
        'fixed inset-y-0 z-50 flex flex-col bg-background shadow-lg',
        'transition-transform duration-200 ease-in-out',
        isLeft ? 'border-r' : 'border-l',
        isLeft ? 'translate-x-0' : 'translate-x-0',
      )}
      style={{
        width: `min(${sidebarWidth}px, calc(50% - ${sidebarWidth}px))`,
        ...(isLeft
          ? { left: `${sidebarWidth}px` }
          : { right: `${sidebarWidth}px` }),
      }}
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
