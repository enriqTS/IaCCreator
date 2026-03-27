'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';

export interface PreferencesDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function PreferencesDialog({ open, onClose }: PreferencesDialogProps) {
  const sidebarSide = useLayoutPreferencesStore((s) => s.sidebarSide);
  const toolbarPosition = useLayoutPreferencesStore((s) => s.toolbarPosition);
  const setSidebarSide = useLayoutPreferencesStore((s) => s.setSidebarSide);
  const setToolbarPosition = useLayoutPreferencesStore((s) => s.setToolbarPosition);

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent data-testid="preferences-dialog">
        <DialogHeader>
          <DialogTitle>Preferences</DialogTitle>
          <DialogDescription>
            Configure your workspace layout preferences.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-6">
          {/* Sidebar Position */}
          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium">Sidebar Position</legend>
            <RadioGroup
              value={sidebarSide}
              onValueChange={(value) => setSidebarSide(value as 'left' | 'right')}
              data-testid="sidebar-side-radio"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="left" id="sidebar-left" />
                <Label htmlFor="sidebar-left">Left</Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="right" id="sidebar-right" />
                <Label htmlFor="sidebar-right">Right</Label>
              </div>
            </RadioGroup>
          </fieldset>

          {/* Toolbar Position */}
          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium">Toolbar Position</legend>
            <RadioGroup
              value={toolbarPosition}
              onValueChange={(value) => setToolbarPosition(value as 'top' | 'bottom')}
              data-testid="toolbar-position-radio"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="top" id="toolbar-top" />
                <Label htmlFor="toolbar-top">Top</Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="bottom" id="toolbar-bottom" />
                <Label htmlFor="toolbar-bottom">Bottom</Label>
              </div>
            </RadioGroup>
          </fieldset>
        </div>
      </DialogContent>
    </Dialog>
  );
}
