'use client';

import type { ArchitectureBlock } from '@/types/diagram';
import SchemaConfigForm from './SchemaConfigForm';

interface TerraformTabProps {
  block: ArchitectureBlock;
}

/** Renders the service-specific Terraform config form for the given architecture block. */
export default function TerraformTab({ block }: TerraformTabProps) {
  return (
    <div data-testid="terraform-tab">
      <SchemaConfigForm elementId={block.id} serviceType={block.serviceType} />
    </div>
  );
}
