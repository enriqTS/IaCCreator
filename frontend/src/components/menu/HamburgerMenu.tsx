'use client';

import {
  Menu,
  FilePlus,
  Save,
  FolderOpen,
  FileOutput,
  Settings,
  FileCog,
  Wrench,
  HelpCircle,
  Import,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';

export interface HamburgerMenuProps {
  onNewDiagram: () => void;
  onSave: () => void;
  onLoad: () => void;
  onImportArchitecture: () => void;
  onExport: () => void;
  onProjectSettings: () => void;
  onTerraformSettings: () => void;
  onPreferences: () => void;
  onReplayTour: () => void;
}

export default function HamburgerMenu(props: HamburgerMenuProps) {
  return (
    <div data-testid="hamburger-menu">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            data-testid="hamburger-button"
            variant="outline"
            size="icon"
            aria-label="Menu"
          >
            <Menu className="size-5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" data-testid="hamburger-dropdown">
          <DropdownMenuItem
            data-testid="menu-item-onNewDiagram"
            onSelect={props.onNewDiagram}
          >
            <FilePlus />
            New Diagram
          </DropdownMenuItem>
          <DropdownMenuItem
            data-testid="menu-item-onSave"
            onSelect={props.onSave}
          >
            <Save />
            Save
          </DropdownMenuItem>
          <DropdownMenuItem
            data-testid="menu-item-onLoad"
            onSelect={props.onLoad}
          >
            <FolderOpen />
            Load
          </DropdownMenuItem>
          <DropdownMenuItem
            data-testid="menu-item-onImportArchitecture"
            onSelect={props.onImportArchitecture}
          >
            <Import />
            Import Architecture
          </DropdownMenuItem>
          <DropdownMenuItem
            data-testid="menu-item-onExport"
            onSelect={props.onExport}
          >
            <FileOutput />
            Export to Terraform
          </DropdownMenuItem>
          <DropdownMenuItem
            data-testid="menu-item-onProjectSettings"
            onSelect={props.onProjectSettings}
          >
            <Wrench />
            Project Settings
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            data-testid="menu-item-onTerraformSettings"
            onSelect={props.onTerraformSettings}
          >
            <FileCog />
            Terraform Settings
          </DropdownMenuItem>

          <DropdownMenuItem
            data-testid="menu-item-onPreferences"
            onSelect={props.onPreferences}
          >
            <Settings />
            Preferences
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            data-testid="menu-item-onReplayTour"
            onSelect={props.onReplayTour}
          >
            <HelpCircle />
            Replay Tour
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
