'use client';

import { useState } from 'react';
import { Upload } from 'lucide-react';
import { useApigwConfigStore } from '@/store/apigw-config-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import KeyValueEditor from '@/components/config/editors/KeyValueEditor';
import ListEditor from '@/components/config/editors/ListEditor';
import { ImportOpenApiDialog } from './ImportOpenApiDialog';
import type { ProtocolType } from '@/types/apigw-config';

export default function SettingsTab() {
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  const protocolType = useApigwConfigStore((s) => s.protocol_type);
  const apiName = useApigwConfigStore((s) => s.api_name);
  const description = useApigwConfigStore((s) => s.description);
  const corsConfiguration = useApigwConfigStore((s) => s.cors_configuration);
  const disableExecuteApiEndpoint = useApigwConfigStore((s) => s.disable_execute_api_endpoint);
  const apiKeyRequired = useApigwConfigStore((s) => s.api_key_required);
  const vpcLinkName = useApigwConfigStore((s) => s.vpc_link_name);
  const subnetIds = useApigwConfigStore((s) => s.subnet_ids);
  const securityGroupIds = useApigwConfigStore((s) => s.security_group_ids);

  const setProtocolType = useApigwConfigStore((s) => s.setProtocolType);
  const updateSettings = useApigwConfigStore((s) => s.updateSettings);
  const updateVpcLink = useApigwConfigStore((s) => s.updateVpcLink);

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Import OpenAPI */}
      <Button
        variant="outline"
        className="w-full"
        onClick={() => setImportDialogOpen(true)}
      >
        <Upload className="size-4" />
        Import OpenAPI Spec
      </Button>

      <ImportOpenApiDialog open={importDialogOpen} onOpenChange={setImportDialogOpen} />

      {/* Protocol Type */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="protocol-type">Protocol Type</Label>
        <Select
          value={protocolType}
          onValueChange={(value) => setProtocolType(value as ProtocolType)}
        >
          <SelectTrigger id="protocol-type" className="w-full">
            <SelectValue placeholder="Select protocol" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="HTTP">HTTP</SelectItem>
            <SelectItem value="REST">REST</SelectItem>
            <SelectItem value="WEBSOCKET">WEBSOCKET</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* API Name */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="api-name">API Name</Label>
        <Input
          id="api-name"
          type="text"
          value={apiName}
          onChange={(e) => updateSettings({ api_name: e.target.value })}
          placeholder="my-api"
        />
      </div>

      {/* Description */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="api-description">Description</Label>
        <Input
          id="api-description"
          type="text"
          value={description}
          onChange={(e) => updateSettings({ description: e.target.value })}
          placeholder="API description"
        />
      </div>

      {/* CORS Configuration */}
      <div className="flex flex-col gap-1.5">
        <Label>CORS Configuration</Label>
        <KeyValueEditor
          value={corsConfiguration}
          onChange={(value) => updateSettings({ cors_configuration: value })}
        />
      </div>

      {/* Disable Execute API Endpoint */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="disable-execute-api-endpoint"
          checked={disableExecuteApiEndpoint}
          onCheckedChange={(checked) =>
            updateSettings({ disable_execute_api_endpoint: checked === true })
          }
        />
        <Label htmlFor="disable-execute-api-endpoint" className="cursor-pointer">
          Disable Execute API Endpoint
        </Label>
      </div>

      {/* API Key Required (hidden for REST) */}
      {protocolType !== 'REST' && (
        <div className="flex items-center gap-2">
          <Checkbox
            id="api-key-required"
            checked={apiKeyRequired}
            onCheckedChange={(checked) =>
              updateSettings({ api_key_required: checked === true })
            }
          />
          <Label htmlFor="api-key-required" className="cursor-pointer">
            API Key Required
          </Label>
        </div>
      )}

      {/* VPC Link Section */}
      <div className="flex flex-col gap-3 rounded-md border p-3">
        <span className="text-sm font-medium">VPC Link</span>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="vpc-link-name">VPC Link Name</Label>
          <Input
            id="vpc-link-name"
            type="text"
            value={vpcLinkName}
            onChange={(e) => updateVpcLink({ vpc_link_name: e.target.value })}
            placeholder="my-vpc-link"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Subnet IDs</Label>
          <ListEditor
            value={subnetIds}
            onChange={(value) => updateVpcLink({ subnet_ids: value })}
            description="Add subnet IDs for the VPC link"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Security Group IDs</Label>
          <ListEditor
            value={securityGroupIds}
            onChange={(value) => updateVpcLink({ security_group_ids: value })}
            description="Add security group IDs for the VPC link"
          />
        </div>
      </div>
    </div>
  );
}
