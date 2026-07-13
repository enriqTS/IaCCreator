'use client';

import { useState, useEffect, useMemo } from 'react';
import { useApigwConfigStore } from '@/store/apigw-config-store';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import type { ProtocolType } from '@/types/apigw-config';
import type { ArchitectureBlock } from '@/types/diagram';

import RoutesTab from './RoutesTab';
import ExpressionsTab from './ExpressionsTab';
import StagesTab from './StagesTab';
import AuthorizersTab from './AuthorizersTab';
import ApiKeysTab from './ApiKeysTab';
import DomainTab from './DomainTab';
import SettingsTab from './SettingsTab';

import DetailPanel from './DetailPanel';
import RouteDetailFields from './RouteDetailFields';
import StageDetailFields from './StageDetailFields';
import AuthorizerDetailFields from './AuthorizerDetailFields';
import ApiKeyDetailFields from './ApiKeyDetailFields';
import WebSocketRouteDetailFields from './WebSocketRouteDetailFields';

interface ApigwDynamicConfigUIProps {
  elementId: string;
}

const TABS_BY_PROTOCOL: Record<ProtocolType, string[]> = {
  HTTP: ['Settings', 'Routes', 'Stages', 'Authorizers', 'API Keys', 'Domain'],
  REST: ['Settings', 'Routes', 'Stages', 'Authorizers', 'API Keys', 'Domain'],
  WEBSOCKET: ['Settings', 'Expressions', 'Stages', 'Authorizers'],
};

export default function ApigwDynamicConfigUI({ elementId }: ApigwDynamicConfigUIProps) {
  const protocolType = useApigwConfigStore((s) => s.protocol_type);
  const selectedItemId = useApigwConfigStore((s) => s.selectedItemId);
  const selectedItemType = useApigwConfigStore((s) => s.selectedItemType);
  const routes = useApigwConfigStore((s) => s.routes);
  const stages = useApigwConfigStore((s) => s.stages);
  const authorizers = useApigwConfigStore((s) => s.authorizers);
  const apiKeys = useApigwConfigStore((s) => s.api_keys);
  const websocketRoutes = useApigwConfigStore((s) => s.websocket_routes);
  const updateRoute = useApigwConfigStore((s) => s.updateRoute);
  const updateStage = useApigwConfigStore((s) => s.updateStage);
  const updateAuthorizer = useApigwConfigStore((s) => s.updateAuthorizer);
  const updateApiKey = useApigwConfigStore((s) => s.updateApiKey);
  const updateWebSocketRoute = useApigwConfigStore((s) => s.updateWebSocketRoute);
  const selectItem = useApigwConfigStore((s) => s.selectItem);

  const sidebarWidth = useDiagramStore((s) => s.sidebarWidth);
  const sidebarSide = useLayoutPreferencesStore((s) => s.sidebarSide);

  const [activeTab, setActiveTab] = useState<string>('');

  const tabs = useMemo(() => TABS_BY_PROTOCOL[protocolType] ?? TABS_BY_PROTOCOL.HTTP, [protocolType]);

  // Initialize store from canvas object config on mount and when elementId changes
  useEffect(() => {
    const canvasObjects = useDiagramStore.getState().canvasObjects;
    const obj = canvasObjects.get(elementId) as ArchitectureBlock | undefined;
    const config = obj?.config ?? {};
    useApigwConfigStore.getState().initFromConfig(elementId, config);

    return () => {
      useApigwConfigStore.getState().reset();
    };
  }, [elementId]);

  // Set initial active tab
  useEffect(() => {
    if (tabs.length > 0 && !tabs.includes(activeTab)) {
      setActiveTab(tabs[0]);
    }
  }, [tabs, activeTab]);

  // When protocol changes and current tab is unavailable, switch to first tab
  // Also close the detail panel since the context has changed
  useEffect(() => {
    selectItem(null, null);
    if (activeTab && !tabs.includes(activeTab)) {
      setActiveTab(tabs[0]);
    }
  }, [protocolType]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close detail panel when switching tabs
  const handleTabChange = (tab: string) => {
    selectItem(null, null);
    setActiveTab(tab);
  };

  // Build detail panel title and content
  const detailPanelContent = useMemo(() => {
    if (!selectedItemId || !selectedItemType) return null;

    switch (selectedItemType) {
      case 'route': {
        const route = routes.find((r) => r.id === selectedItemId);
        if (!route) return null;
        return {
          title: `Route: ${route.method} ${route.path}`,
          content: (
            <RouteDetailFields
              route={route}
              onUpdate={(updates) => updateRoute(selectedItemId, updates)}
            />
          ),
        };
      }
      case 'stage': {
        const stage = stages.find((s) => s.id === selectedItemId);
        if (!stage) return null;
        return {
          title: `Stage: ${stage.name}`,
          content: (
            <StageDetailFields
              stage={stage}
              onUpdate={(updates) => updateStage(selectedItemId, updates)}
            />
          ),
        };
      }
      case 'authorizer': {
        const authorizer = authorizers.find((a) => a.id === selectedItemId);
        if (!authorizer) return null;
        return {
          title: `Authorizer: ${authorizer.name}`,
          content: (
            <AuthorizerDetailFields
              authorizer={authorizer}
              onUpdate={(updates) => updateAuthorizer(selectedItemId, updates)}
            />
          ),
        };
      }
      case 'api_key': {
        const apiKey = apiKeys.find((k) => k.id === selectedItemId);
        if (!apiKey) return null;
        return {
          title: `API Key: ${apiKey.name || '(unnamed)'}`,
          content: (
            <ApiKeyDetailFields
              apiKey={apiKey}
              onUpdate={(updates) => updateApiKey(selectedItemId, updates)}
            />
          ),
        };
      }
      case 'websocket_route': {
        const wsRoute = websocketRoutes.find((r) => r.id === selectedItemId);
        if (!wsRoute) return null;
        return {
          title: `WebSocket Route: ${wsRoute.route_key || '(empty)'}`,
          content: (
            <WebSocketRouteDetailFields
              route={wsRoute}
              onUpdate={(updates) => updateWebSocketRoute(selectedItemId, updates)}
            />
          ),
        };
      }
      default:
        return null;
    }
  }, [selectedItemId, selectedItemType, routes, stages, authorizers, apiKeys, websocketRoutes, updateRoute, updateStage, updateAuthorizer, updateApiKey, updateWebSocketRoute]);

  const effectiveTab = tabs.includes(activeTab) ? activeTab : tabs[0] ?? '';

  return (
    <>
      <Tabs value={effectiveTab} onValueChange={handleTabChange} className="w-full">
        <TabsList data-testid="apigw-tab-bar" className={cn('w-full h-auto grid gap-0', tabs.length === 4 ? 'grid-cols-4' : tabs.length === 6 ? 'grid-cols-6' : 'grid-cols-5')}>
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab}
              value={tab}
              data-testid={`apigw-tab-${tab.toLowerCase()}`}
              className="text-xs px-2"
            >
              {tab}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="Routes">
          <RoutesTab />
        </TabsContent>

        <TabsContent value="Expressions">
          <ExpressionsTab />
        </TabsContent>

        <TabsContent value="Stages">
          <StagesTab />
        </TabsContent>

        <TabsContent value="Authorizers">
          <AuthorizersTab />
        </TabsContent>

        <TabsContent value="API Keys">
          <ApiKeysTab />
        </TabsContent>

        <TabsContent value="Domain">
          <DomainTab />
        </TabsContent>

        <TabsContent value="Settings">
          <SettingsTab />
        </TabsContent>
      </Tabs>

      {/* Detail Panel rendered as sibling */}
      <DetailPanel
        isOpen={detailPanelContent !== null}
        onClose={() => selectItem(null, null)}
        title={detailPanelContent?.title ?? ''}
        sidebarWidth={sidebarWidth}
        sidebarSide={sidebarSide}
      >
        {detailPanelContent?.content}
      </DetailPanel>
    </>
  );
}
