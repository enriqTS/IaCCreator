'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import KeyValueEditor from '@/components/config/KeyValueEditor';
import type { StageItem } from '@/types/apigw-config';

interface StageDetailFieldsProps {
  stage: StageItem;
  onUpdate: (updates: Partial<StageItem>) => void;
}

const MAX_STAGE_VARIABLES = 50;

export default function StageDetailFields({ stage, onUpdate }: StageDetailFieldsProps) {
  // Debounced text states
  const [nameValue, setNameValue] = useState(stage.name);
  const [burstLimitValue, setBurstLimitValue] = useState(String(stage.throttling_burst_limit));
  const [rateLimitValue, setRateLimitValue] = useState(String(stage.throttling_rate_limit));
  const [logRetentionValue, setLogRetentionValue] = useState(String(stage.log_retention_days ?? ''));
  const [logFormatValue, setLogFormatValue] = useState(stage.log_format ?? '');

  // Validation errors
  const [burstError, setBurstError] = useState('');
  const [rateError, setRateError] = useState('');

  // Sync local state when stage prop changes
  useEffect(() => {
    setNameValue(stage.name);
  }, [stage.id, stage.name]);

  useEffect(() => {
    setBurstLimitValue(String(stage.throttling_burst_limit));
    setBurstError('');
  }, [stage.id, stage.throttling_burst_limit]);

  useEffect(() => {
    setRateLimitValue(String(stage.throttling_rate_limit));
    setRateError('');
  }, [stage.id, stage.throttling_rate_limit]);

  useEffect(() => {
    setLogRetentionValue(String(stage.log_retention_days ?? ''));
  }, [stage.id, stage.log_retention_days]);

  useEffect(() => {
    setLogFormatValue(stage.log_format ?? '');
  }, [stage.id, stage.log_format]);

  // Debounce name
  useEffect(() => {
    if (nameValue === stage.name) return;
    const timer = setTimeout(() => {
      onUpdate({ name: nameValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [nameValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce burst limit with validation
  useEffect(() => {
    if (burstLimitValue === String(stage.throttling_burst_limit)) return;
    const timer = setTimeout(() => {
      const num = parseInt(burstLimitValue, 10);
      if (isNaN(num) || num < 1 || num > 5000) {
        setBurstError('Must be between 1 and 5000');
        return;
      }
      setBurstError('');
      onUpdate({ throttling_burst_limit: num });
    }, 300);
    return () => clearTimeout(timer);
  }, [burstLimitValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce rate limit with validation
  useEffect(() => {
    if (rateLimitValue === String(stage.throttling_rate_limit)) return;
    const timer = setTimeout(() => {
      const num = parseFloat(rateLimitValue);
      if (isNaN(num) || num < 1.0 || num > 10000.0) {
        setRateError('Must be between 1.0 and 10000.0');
        return;
      }
      setRateError('');
      onUpdate({ throttling_rate_limit: num });
    }, 300);
    return () => clearTimeout(timer);
  }, [rateLimitValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce log retention
  useEffect(() => {
    if (logRetentionValue === String(stage.log_retention_days ?? '')) return;
    const timer = setTimeout(() => {
      const num = parseInt(logRetentionValue, 10);
      onUpdate({ log_retention_days: isNaN(num) ? undefined : num });
    }, 300);
    return () => clearTimeout(timer);
  }, [logRetentionValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce log format
  useEffect(() => {
    if (logFormatValue === (stage.log_format ?? '')) return;
    const timer = setTimeout(() => {
      onUpdate({ log_format: logFormatValue });
    }, 300);
    return () => clearTimeout(timer);
  }, [logFormatValue]); // eslint-disable-line react-hooks/exhaustive-deps

  const stageVariableCount = Object.keys(stage.stage_variables).length;
  const isAtVariableLimit = stageVariableCount >= MAX_STAGE_VARIABLES;

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Name */}
      <div className="flex flex-col gap-1.5">
        <Label>Stage Name</Label>
        <Input
          type="text"
          value={nameValue}
          onChange={(e) => setNameValue(e.target.value)}
          placeholder="$default"
          className="w-full"
        />
      </div>

      {/* Auto Deploy */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="auto-deploy"
          checked={stage.auto_deploy}
          onCheckedChange={(checked) => onUpdate({ auto_deploy: checked === true })}
        />
        <Label htmlFor="auto-deploy">Auto Deploy</Label>
      </div>

      {/* Stage Variables */}
      <div className="flex flex-col gap-1.5">
        <Label>Stage Variables</Label>
        <KeyValueEditor
          value={stage.stage_variables}
          onChange={(value) => onUpdate({ stage_variables: value })}
        />
        {isAtVariableLimit && (
          <span className="text-xs text-muted-foreground">
            Maximum of {MAX_STAGE_VARIABLES} stage variables reached.
          </span>
        )}
      </div>

      {/* Throttling Burst Limit */}
      <div className="flex flex-col gap-1.5">
        <Label>Throttling Burst Limit</Label>
        <Input
          type="text"
          inputMode="numeric"
          value={burstLimitValue}
          onChange={(e) => setBurstLimitValue(e.target.value)}
          placeholder="5000"
          className="w-full"
          aria-invalid={!!burstError}
        />
        {burstError && (
          <span className="text-xs text-destructive">{burstError}</span>
        )}
      </div>

      {/* Throttling Rate Limit */}
      <div className="flex flex-col gap-1.5">
        <Label>Throttling Rate Limit</Label>
        <Input
          type="text"
          inputMode="numeric"
          value={rateLimitValue}
          onChange={(e) => setRateLimitValue(e.target.value)}
          placeholder="10000"
          className="w-full"
          aria-invalid={!!rateError}
        />
        {rateError && (
          <span className="text-xs text-destructive">{rateError}</span>
        )}
      </div>

      {/* Access Logging */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="access-logging"
          checked={stage.access_logging}
          onCheckedChange={(checked) => onUpdate({ access_logging: checked === true })}
        />
        <Label htmlFor="access-logging">Access Logging</Label>
      </div>

      {/* Conditional: Log Retention Days & Log Format */}
      {stage.access_logging && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label>Log Retention Days</Label>
            <Input
              type="text"
              inputMode="numeric"
              value={logRetentionValue}
              onChange={(e) => setLogRetentionValue(e.target.value)}
              placeholder="30"
              className="w-full"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Log Format</Label>
            <Input
              type="text"
              value={logFormatValue}
              onChange={(e) => setLogFormatValue(e.target.value)}
              placeholder="$context.requestId $context.identity.sourceIp"
              className="w-full"
            />
          </div>
        </>
      )}
    </div>
  );
}
