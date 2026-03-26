import { describe, it, expect } from 'vitest';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';

describe('AWS Icon Registry', () => {
  it('has exactly 26 categories', () => {
    expect(AWS_ICON_REGISTRY).toHaveLength(26);
  });

  it('maps Lambda to correct icon path and serviceType', () => {
    const compute = AWS_ICON_REGISTRY.find((c) => c.name === 'Compute');
    const lambda = compute?.services.find((s) => s.name === 'Lambda');
    expect(lambda).toBeDefined();
    expect(lambda!.iconPath).toBe('/aws-icons/Compute/Lambda.svg');
    expect(lambda!.serviceType).toBe('lambda');
  });

  it('maps S3 to correct icon path and serviceType', () => {
    const storage = AWS_ICON_REGISTRY.find((c) => c.name === 'Storage');
    const s3 = storage?.services.find((s) => s.name === 'Simple Storage Service');
    expect(s3).toBeDefined();
    expect(s3!.iconPath).toBe('/aws-icons/Storage/Simple-Storage-Service.svg');
    expect(s3!.serviceType).toBe('s3');
  });

  it('maps API Gateway to correct icon path and serviceType', () => {
    const appIntegration = AWS_ICON_REGISTRY.find((c) => c.name === 'App Integration');
    const apiGw = appIntegration?.services.find((s) => s.name === 'API Gateway');
    expect(apiGw).toBeDefined();
    expect(apiGw!.iconPath).toBe('/aws-icons/App-Integration/API-Gateway.svg');
    expect(apiGw!.serviceType).toBe('api-gateway');
  });

  it('maps DynamoDB to correct icon path and serviceType', () => {
    const database = AWS_ICON_REGISTRY.find((c) => c.name === 'Database');
    const dynamo = database?.services.find((s) => s.name === 'DynamoDB');
    expect(dynamo).toBeDefined();
    expect(dynamo!.iconPath).toBe('/aws-icons/Database/DynamoDB.svg');
    expect(dynamo!.serviceType).toBe('dynamodb');
  });

  it('maps IAM to correct icon path and serviceType', () => {
    const security = AWS_ICON_REGISTRY.find((c) => c.name === 'Security Identity Compliance');
    const iam = security?.services.find((s) => s.name === 'Identity and Access Management');
    expect(iam).toBeDefined();
    expect(iam!.iconPath).toBe('/aws-icons/Security-Identity-Compliance/Identity-and-Access-Management.svg');
    expect(iam!.serviceType).toBe('iam');
  });

  it('maps CloudWatch to correct icon path and serviceType', () => {
    const mgmt = AWS_ICON_REGISTRY.find((c) => c.name === 'Management Governance');
    const cw = mgmt?.services.find((s) => s.name === 'CloudWatch');
    expect(cw).toBeDefined();
    expect(cw!.iconPath).toBe('/aws-icons/Management-Governance/CloudWatch.svg');
    expect(cw!.serviceType).toBe('cloudwatch');
  });
});
