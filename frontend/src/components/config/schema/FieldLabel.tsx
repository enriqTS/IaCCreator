'use client';

import { Info } from 'lucide-react';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface FieldLabelProps {
  label: string;
  /** The long explanation, shown on the info icon rather than in the label. */
  description?: string;
  required?: boolean;
  /** Unit or qualifier shown after the name, such as MB or seconds. */
  unit?: string;
  htmlFor?: string;
}

/** The one label every configuration field uses: a short name, a unit, a marker, a tooltip. */
export default function FieldLabel({
  label,
  description,
  required,
  unit,
  htmlFor,
}: FieldLabelProps) {
  return (
    <Label htmlFor={htmlFor} className="gap-1.5 text-xs leading-none">
      <span>{label}</span>
      {unit && <span className="font-normal text-muted-foreground">{unit}</span>}
      {required && (
        <span aria-hidden className="text-destructive">
          *
        </span>
      )}
      {description && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={`What ${label} does`}
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                <Info className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">{description}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </Label>
  );
}
