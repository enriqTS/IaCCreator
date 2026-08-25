/** Backend-owned service support metadata used by the local icon renderer. */

import { create } from 'zustand';
import { apiClient } from '@/utils/api-client';

interface EditorDomainState {
  supportedServices: Set<string> | null;
  load: () => Promise<void>;
}

export const useEditorDomainStore = create<EditorDomainState>()((set) => ({
  supportedServices: null,
  load: async () => {
    const result = await apiClient.getEditorBootstrap();
    if (!result.ok) return;
    set({
      supportedServices: new Set(
        result.data.services
          .filter((service) => service.supported)
          .map((service) => service.service_type),
      ),
    });
  },
}));
