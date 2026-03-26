'use client';

export default function IAMConfigForm({ elementId }: { elementId: string }) {
  void elementId; // no editable fields for v1
  return (
    <div data-testid="iam-config-form" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
      <span style={{ color: 'rgba(255,255,255,0.5)' }}>IAM Role/Policy</span>
    </div>
  );
}
