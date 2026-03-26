'use client';

import { useToastStore } from '@/store/toast-store';

export default function ToastProvider() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        pointerEvents: 'auto',
      }}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          onClick={() => removeToast(toast.id)}
          style={{
            padding: '10px 16px',
            borderRadius: 6,
            color: '#fff',
            fontSize: 14,
            maxWidth: 360,
            cursor: 'pointer',
            background: toast.type === 'error' ? '#dc2626' : '#16a34a',
            boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
          }}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}
