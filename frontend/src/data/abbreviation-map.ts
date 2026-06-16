/**
 * Static lookup table mapping common AWS service abbreviations to their
 * full service names as they appear in `aws-icon-registry.ts`.
 *
 * Keys are lowercase. Values are arrays because one abbreviation can
 * match multiple related services (e.g. "eks" → EKS, EKS Anywhere, …).
 */
export const ABBREVIATION_MAP: Record<string, string[]> = {
  s3: ['Simple Storage Service'],
  ec2: ['EC2', 'EC2 Auto Scaling', 'EC2 Image Builder'],
  ecs: ['Elastic Container Service', 'ECS Anywhere'],
  eks: ['Elastic Kubernetes Service', 'EKS Anywhere', 'EKS Cloud', 'EKS Distro'],
  rds: ['RDS', 'RDS on VMware'],
  sns: ['Simple Notification Service'],
  sqs: ['Simple Queue Service'],
  iam: ['Identity and Access Management'],
  cfn: ['CloudFormation'],
  bedrock: ['Bedrock', 'Bedrock Agent', 'Bedrock Guardrail', 'Bedrock Knowledge Base', 'Bedrock AgentCore'],
  sagemaker: ['SageMaker'],
  q: ['Amazon Q'],
};
