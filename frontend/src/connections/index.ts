/**
 * Connections domain module barrel export.
 *
 * Re-exports the schema registry, shared types, connector utilities,
 * and all individual connection schema constants.
 */

// Registry value and shared types
export { CONNECTION_SCHEMA_REGISTRY } from './registry';
export type { SchemaFieldType, SchemaField, ConnectionSchema, SchemaRegistryKey } from './registry';

// Connector utility functions
export { findConnectorForLine, getSchemaForConnector, ensureConnectorForLine } from './connector-utils';

// Individual schema constants
export { apiGatewayLambdaSchema } from './apigw-lambda';
export { sqsLambdaSchema } from './sqs-lambda';
export { lambdaDynamodbSchema } from './lambda-dynamodb';
export { lambdaS3Schema } from './lambda-s3';
export { lambdaSnsSchema } from './lambda-sns';
export { lambdaSqsSchema } from './lambda-sqs';
export { snsLambdaSchema } from './sns-lambda';
export { snsSqsSchema } from './sns-sqs';
export { lambdaCloudwatchSchema } from './lambda-cloudwatch';
