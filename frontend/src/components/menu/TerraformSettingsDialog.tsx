'use client';

import GlobalTerraformConfigPanel from '@/components/config/GlobalTerraformConfigPanel';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface TerraformSettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

/** Project-level Terraform configuration, which belongs to no canvas object. */
export default function TerraformSettingsDialog({ open, onClose }: TerraformSettingsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <DialogContent
        data-testid="terraform-settings-dialog"
        className="grid max-h-[85vh] grid-cols-[minmax(0,1fr)] grid-rows-[auto_1fr] gap-0 overflow-hidden p-0 sm:max-w-2xl"
      >
        <DialogHeader className="border-b px-6 py-4 pr-14">
          <DialogTitle className="text-base">Terraform Settings</DialogTitle>
          <DialogDescription className="text-xs">
            Backend, provider and version constraints for the generated project
          </DialogDescription>
        </DialogHeader>
        <div className="min-w-0 overflow-y-auto px-6 py-4">
          <GlobalTerraformConfigPanel panelWidth={620} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
