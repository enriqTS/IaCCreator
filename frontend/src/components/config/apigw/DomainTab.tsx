'use client';

import { useApigwConfigStore } from '@/store/apigw-config-store';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function DomainTab() {
  const domainName = useApigwConfigStore((s) => s.domain_name);
  const certificateArn = useApigwConfigStore((s) => s.certificate_arn);
  const updateDomain = useApigwConfigStore((s) => s.updateDomain);

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="domain-name">Domain Name</Label>
        <Input
          id="domain-name"
          type="text"
          value={domainName}
          onChange={(e) => updateDomain({ domain_name: e.target.value })}
          placeholder="api.example.com"
        />
      </div>

      {domainName && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="certificate-arn">Certificate ARN</Label>
          <Input
            id="certificate-arn"
            type="text"
            value={certificateArn}
            onChange={(e) => updateDomain({ certificate_arn: e.target.value })}
            placeholder="arn:aws:acm:region:account:certificate/id"
          />
        </div>
      )}
    </div>
  );
}
