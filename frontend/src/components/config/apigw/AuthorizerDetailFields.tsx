'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import ListEditor from '@/components/config/editors/ListEditor';
import type { AuthorizerItem } from '@/types/apigw-config';

interface AuthorizerDetailFieldsProps {
  authorizer: AuthorizerItem;
  onUpdate: (updates: Partial<AuthorizerItem>) => void;
}

const AUTHORIZER_TYPES = ['JWT', 'REQUEST', 'COGNITO_USER_POOLS'] as const;
const PAYLOAD_FORMAT_VERSIONS = ['1.0', '2.0'] as const;

export default function AuthorizerDetailFields({ authorizer, onUpdate }: AuthorizerDetailFieldsProps) {
  // Debounced text states
  const [nameValue, setNameValue] = useState(authorizer.name);
  const [issuerUrlValue, setIssuerUrlValue] = useState(authorizer.issuer_url ?? '');
  const [lambdaArnValue, setLambdaArnValue] = useState(authorizer.lambda_function_arn ?? '');
  const [cognitoEndpointValue, setCognitoEndpointValue] = useState(authorizer.cognito_endpoint ?? '');

  // Sync local state when authorizer prop changes
  useEffect(() => {
    setNameValue(authorizer.name);
  }, [authorizer.id, authorizer.name]);

  useEffect(() => {
    setIssuerUrlValue(authorizer.issuer_url ?? '');
  }, [authorizer.id, authorizer.issuer_url]);

  useEffect(() => {
    setLambdaArnValue(authorizer.lambda_function_arn ?? '');
  }, [authorizer.id, authorizer.lambda_function_arn]);

  useEffect(() => {
    setCognitoEndpointValue(authorizer.cognito_endpoint ?? '');
  }, [authorizer.id, authorizer.cognito_endpoint]);

  // Debounce name
  useEffect(() => {
    if (nameValue === authorizer.name) return;
    const timer = setTimeout(() => {
      onUpdate({ name: nameValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [nameValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce issuer_url
  useEffect(() => {
    if (issuerUrlValue === (authorizer.issuer_url ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ issuer_url: issuerUrlValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [issuerUrlValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce lambda_function_arn
  useEffect(() => {
    if (lambdaArnValue === (authorizer.lambda_function_arn ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ lambda_function_arn: lambdaArnValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [lambdaArnValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce cognito_endpoint
  useEffect(() => {
    if (cognitoEndpointValue === (authorizer.cognito_endpoint ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ cognito_endpoint: cognitoEndpointValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [cognitoEndpointValue]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Name */}
      <div className="flex flex-col gap-1.5">
        <Label>Name</Label>
        <Input
          type="text"
          value={nameValue}
          onChange={(e) => setNameValue(e.target.value)}
          placeholder="my-authorizer"
          className="w-full"
        />
      </div>

      {/* Type */}
      <div className="flex flex-col gap-1.5">
        <Label>Type</Label>
        <Select
          value={authorizer.type}
          onValueChange={(value) =>
            onUpdate({
              type: value as AuthorizerItem['type'],
              // Clear type-specific fields when type changes
              ...(value !== 'JWT' ? { issuer_url: undefined, audience: undefined } : {}),
              ...(value !== 'REQUEST' ? { lambda_function_arn: undefined, payload_format_version: undefined } : {}),
              ...(value !== 'COGNITO_USER_POOLS' ? { cognito_endpoint: undefined, client_ids: undefined } : {}),
            })
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select type" />
          </SelectTrigger>
          <SelectContent>
            {AUTHORIZER_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* JWT fields */}
      {authorizer.type === 'JWT' && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label>Issuer URL</Label>
            <Input
              type="text"
              value={issuerUrlValue}
              onChange={(e) => setIssuerUrlValue(e.target.value)}
              placeholder="https://issuer.example.com"
              className="w-full"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Audience</Label>
            <ListEditor
              value={authorizer.audience}
              onChange={(value) => onUpdate({ audience: value })}
              description="Accepted audience values for JWT validation"
            />
          </div>
        </>
      )}

      {/* REQUEST fields */}
      {authorizer.type === 'REQUEST' && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label>Lambda Function ARN</Label>
            <Input
              type="text"
              value={lambdaArnValue}
              onChange={(e) => setLambdaArnValue(e.target.value)}
              placeholder="arn:aws:lambda:us-east-1:123456789:function:my-auth"
              className="w-full"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Payload Format Version</Label>
            <Select
              value={authorizer.payload_format_version ?? '2.0'}
              onValueChange={(value) =>
                onUpdate({ payload_format_version: value as '1.0' | '2.0' })
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select version" />
              </SelectTrigger>
              <SelectContent>
                {PAYLOAD_FORMAT_VERSIONS.map((version) => (
                  <SelectItem key={version} value={version}>
                    {version}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}

      {/* COGNITO_USER_POOLS fields */}
      {authorizer.type === 'COGNITO_USER_POOLS' && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label>Cognito Endpoint</Label>
            <Input
              type="text"
              value={cognitoEndpointValue}
              onChange={(e) => setCognitoEndpointValue(e.target.value)}
              placeholder="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123"
              className="w-full"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Client IDs</Label>
            <ListEditor
              value={authorizer.client_ids}
              onChange={(value) => onUpdate({ client_ids: value })}
              description="App client IDs for the Cognito User Pool"
            />
          </div>
        </>
      )}
    </div>
  );
}
