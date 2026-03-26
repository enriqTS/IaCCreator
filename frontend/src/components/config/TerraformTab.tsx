'use client';

import type { ArchitectureBlock } from '@/types/diagram';
import LambdaConfigForm from './LambdaConfigForm';
import S3ConfigForm from './S3ConfigForm';
import DynamoDBConfigForm from './DynamoDBConfigForm';
import APIGatewayConfigForm from './APIGatewayConfigForm';
import CloudWatchConfigForm from './CloudWatchConfigForm';
import IAMConfigForm from './IAMConfigForm';

interface TerraformTabProps {
  block: ArchitectureBlock;
}

/** Renders the service-specific Terraform config form for the given architecture block. */
export default function TerraformTab({ block }: TerraformTabProps) {
  return (
    <div data-testid="terraform-tab">
      <ServiceConfigForm serviceType={block.serviceType} elementId={block.id} />
    </div>
  );
}

function ServiceConfigForm({ serviceType, elementId }: { serviceType: ArchitectureBlock['serviceType']; elementId: string }) {
  switch (serviceType) {
    case 'lambda':
      return <LambdaConfigForm elementId={elementId} />;
    case 's3':
      return <S3ConfigForm elementId={elementId} />;
    case 'dynamodb':
      return <DynamoDBConfigForm elementId={elementId} />;
    case 'api-gateway':
      return <APIGatewayConfigForm elementId={elementId} />;
    case 'cloudwatch':
      return <CloudWatchConfigForm elementId={elementId} />;
    case 'iam':
      return <IAMConfigForm elementId={elementId} />;
    default:
      return <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>No configuration available for this service type.</p>;
  }
}
