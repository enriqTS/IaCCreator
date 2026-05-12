import { create } from 'zustand';
import type {
  RouteItem,
  StageItem,
  AuthorizerItem,
  WebSocketRouteItem,
  ProtocolType,
} from '@/types/apigw-config';
import type { ResourceConfig } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

// ---------------------------------------------------------------------------
// State interface
// ---------------------------------------------------------------------------

export interface ApigwConfigState {
  // Current element binding
  elementId: string | null;

  // Protocol
  protocol_type: ProtocolType;

  // Collections
  routes: RouteItem[];
  stages: StageItem[];
  authorizers: AuthorizerItem[];
  websocket_routes: WebSocketRouteItem[];

  // Selection tracking
  selectedItemId: string | null;
  selectedItemType: 'route' | 'stage' | 'authorizer' | 'websocket_route' | null;

  // Settings fields
  api_name: string;
  description: string;
  cors_configuration: Record<string, string>;
  disable_execute_api_endpoint: boolean;
  api_key_required: boolean;
  route_selection_expression: string;

  // Domain fields
  domain_name: string;
  certificate_arn: string;

  // VPC Link fields
  vpc_link_name: string;
  subnet_ids: string[];
  security_group_ids: string[];

  // Actions
  initFromConfig: (elementId: string, config: ResourceConfig) => void;
  reset: () => void;

  // Collection CRUD
  addRoute: () => void;
  updateRoute: (id: string, updates: Partial<RouteItem>) => void;
  removeRoute: (id: string) => void;

  addStage: () => void;
  updateStage: (id: string, updates: Partial<StageItem>) => void;
  removeStage: (id: string) => void;

  addAuthorizer: () => void;
  updateAuthorizer: (id: string, updates: Partial<AuthorizerItem>) => void;
  removeAuthorizer: (id: string) => void;

  addWebSocketRoute: () => void;
  updateWebSocketRoute: (id: string, updates: Partial<WebSocketRouteItem>) => void;
  removeWebSocketRoute: (id: string) => void;

  // Settings actions
  setProtocolType: (type: ProtocolType) => void;
  updateSettings: (updates: Partial<Pick<ApigwConfigState, 'api_name' | 'description' | 'cors_configuration' | 'disable_execute_api_endpoint' | 'api_key_required' | 'route_selection_expression'>>) => void;
  updateDomain: (updates: Partial<Pick<ApigwConfigState, 'domain_name' | 'certificate_arn'>>) => void;
  updateVpcLink: (updates: Partial<Pick<ApigwConfigState, 'vpc_link_name' | 'subnet_ids' | 'security_group_ids'>>) => void;

  // Selection
  selectItem: (id: string | null, type: 'route' | 'stage' | 'authorizer' | 'websocket_route' | null) => void;
}

// ---------------------------------------------------------------------------
// Default state values
// ---------------------------------------------------------------------------

const DEFAULT_STATE = {
  elementId: null,
  protocol_type: 'HTTP' as ProtocolType,
  routes: [] as RouteItem[],
  stages: [] as StageItem[],
  authorizers: [] as AuthorizerItem[],
  websocket_routes: [] as WebSocketRouteItem[],
  selectedItemId: null,
  selectedItemType: null,
  api_name: '',
  description: '',
  cors_configuration: {} as Record<string, string>,
  disable_execute_api_endpoint: false,
  api_key_required: false,
  route_selection_expression: '$request.body.action',
  domain_name: '',
  certificate_arn: '',
  vpc_link_name: '',
  subnet_ids: [] as string[],
  security_group_ids: [] as string[],
};

// ---------------------------------------------------------------------------
// Default WebSocket special routes
// ---------------------------------------------------------------------------

function createDefaultWebSocketRoutes(): WebSocketRouteItem[] {
  return [
    { id: crypto.randomUUID(), route_key: '$connect', is_special: true, authorization_enabled: false },
    { id: crypto.randomUUID(), route_key: '$disconnect', is_special: true, authorization_enabled: false },
    { id: crypto.randomUUID(), route_key: '$default', is_special: true, authorization_enabled: false },
  ];
}

// ---------------------------------------------------------------------------
// Helper: ensure items have IDs
// ---------------------------------------------------------------------------

function ensureId<T extends { id?: string }>(item: T): T & { id: string } {
  return { ...item, id: item.id || crypto.randomUUID() } as T & { id: string };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useApigwConfigStore = create<ApigwConfigState>((set, get) => {
  // Private helper: sync current state back to diagram store
  function _syncToCanvas() {
    const state = get();
    if (!state.elementId) return;

    const config: ResourceConfig & Record<string, unknown> = {
      protocol_type: state.protocol_type,
      api_name: state.api_name,
      description: state.description,
      cors_configuration: state.cors_configuration,
      disable_execute_api_endpoint: state.disable_execute_api_endpoint,
      api_key_required: state.api_key_required,
      route_selection_expression: state.route_selection_expression,
      domain_name: state.domain_name,
      certificate_arn: state.certificate_arn,
      vpc_link_name: state.vpc_link_name,
      subnet_ids: state.subnet_ids,
      security_group_ids: state.security_group_ids,
      routes: state.routes,
      stages: state.stages,
      authorizers: state.authorizers,
      websocket_routes: state.websocket_routes,
    };

    useDiagramStore.getState().updateCanvasObject(state.elementId, { config } as never);
  }

  return {
    ...DEFAULT_STATE,

    // -----------------------------------------------------------------------
    // initFromConfig: hydrate store from existing ResourceConfig
    // -----------------------------------------------------------------------
    initFromConfig: (elementId: string, config: ResourceConfig) => {
      const cfg = config as ResourceConfig & Record<string, unknown>;

      const protocolType = (cfg.protocol_type as ProtocolType) || 'HTTP';

      // Parse collections, ensuring each item has an ID
      const routes = Array.isArray(cfg.routes)
        ? (cfg.routes as RouteItem[]).map(ensureId)
        : [];

      const stages = Array.isArray(cfg.stages)
        ? (cfg.stages as StageItem[]).map(ensureId)
        : [];

      const authorizers = Array.isArray(cfg.authorizers)
        ? (cfg.authorizers as AuthorizerItem[]).map(ensureId)
        : [];

      let websocketRoutes = Array.isArray(cfg.websocket_routes)
        ? (cfg.websocket_routes as WebSocketRouteItem[]).map(ensureId)
        : [];

      // Create default WebSocket routes when protocol is WEBSOCKET and none exist
      if (protocolType === 'WEBSOCKET' && websocketRoutes.length === 0) {
        websocketRoutes = createDefaultWebSocketRoutes();
      }

      set({
        elementId,
        protocol_type: protocolType,
        routes,
        stages,
        authorizers,
        websocket_routes: websocketRoutes,
        selectedItemId: null,
        selectedItemType: null,
        api_name: (cfg.api_name as string) || '',
        description: (cfg.description as string) || '',
        cors_configuration: (cfg.cors_configuration as Record<string, string>) || {},
        disable_execute_api_endpoint: Boolean(cfg.disable_execute_api_endpoint),
        api_key_required: Boolean(cfg.api_key_required),
        route_selection_expression: (cfg.route_selection_expression as string) || '$request.body.action',
        domain_name: (cfg.domain_name as string) || '',
        certificate_arn: (cfg.certificate_arn as string) || '',
        vpc_link_name: (cfg.vpc_link_name as string) || '',
        subnet_ids: Array.isArray(cfg.subnet_ids) ? (cfg.subnet_ids as string[]) : [],
        security_group_ids: Array.isArray(cfg.security_group_ids) ? (cfg.security_group_ids as string[]) : [],
      });
    },

    // -----------------------------------------------------------------------
    // reset: clear state when selection changes
    // -----------------------------------------------------------------------
    reset: () => {
      set({ ...DEFAULT_STATE });
    },

    // -----------------------------------------------------------------------
    // Route CRUD
    // -----------------------------------------------------------------------
    addRoute: () => {
      const newRoute: RouteItem = {
        id: crypto.randomUUID(),
        method: 'ANY',
        path: '/',
        integration_ref: '',
      };
      set((state) => ({ routes: [...state.routes, newRoute] }));
      _syncToCanvas();
    },

    updateRoute: (id: string, updates: Partial<RouteItem>) => {
      set((state) => ({
        routes: state.routes.map((r) => (r.id === id ? { ...r, ...updates } : r)),
      }));
      _syncToCanvas();
    },

    removeRoute: (id: string) => {
      set((state) => ({
        routes: state.routes.filter((r) => r.id !== id),
        // Clear selection if removed item was selected
        selectedItemId: state.selectedItemId === id ? null : state.selectedItemId,
        selectedItemType: state.selectedItemId === id ? null : state.selectedItemType,
      }));
      _syncToCanvas();
    },

    // -----------------------------------------------------------------------
    // Stage CRUD
    // -----------------------------------------------------------------------
    addStage: () => {
      const newStage: StageItem = {
        id: crypto.randomUUID(),
        name: '$default',
        auto_deploy: true,
        stage_variables: {},
        throttling_burst_limit: 5000,
        throttling_rate_limit: 10000,
        access_logging: false,
      };
      set((state) => ({ stages: [...state.stages, newStage] }));
      _syncToCanvas();
    },

    updateStage: (id: string, updates: Partial<StageItem>) => {
      set((state) => ({
        stages: state.stages.map((s) => (s.id === id ? { ...s, ...updates } : s)),
      }));
      _syncToCanvas();
    },

    removeStage: (id: string) => {
      set((state) => ({
        stages: state.stages.filter((s) => s.id !== id),
        selectedItemId: state.selectedItemId === id ? null : state.selectedItemId,
        selectedItemType: state.selectedItemId === id ? null : state.selectedItemType,
      }));
      _syncToCanvas();
    },

    // -----------------------------------------------------------------------
    // Authorizer CRUD
    // -----------------------------------------------------------------------
    addAuthorizer: () => {
      const newAuthorizer: AuthorizerItem = {
        id: crypto.randomUUID(),
        name: 'new-authorizer',
        type: 'JWT',
      };
      set((state) => ({ authorizers: [...state.authorizers, newAuthorizer] }));
      _syncToCanvas();
    },

    updateAuthorizer: (id: string, updates: Partial<AuthorizerItem>) => {
      set((state) => ({
        authorizers: state.authorizers.map((a) => (a.id === id ? { ...a, ...updates } : a)),
      }));
      _syncToCanvas();
    },

    removeAuthorizer: (id: string) => {
      set((state) => ({
        authorizers: state.authorizers.filter((a) => a.id !== id),
        selectedItemId: state.selectedItemId === id ? null : state.selectedItemId,
        selectedItemType: state.selectedItemId === id ? null : state.selectedItemType,
      }));
      _syncToCanvas();
    },

    // -----------------------------------------------------------------------
    // WebSocket Route CRUD
    // -----------------------------------------------------------------------
    addWebSocketRoute: () => {
      const newRoute: WebSocketRouteItem = {
        id: crypto.randomUUID(),
        route_key: '',
        is_special: false,
        authorization_enabled: false,
      };
      set((state) => ({ websocket_routes: [...state.websocket_routes, newRoute] }));
      _syncToCanvas();
    },

    updateWebSocketRoute: (id: string, updates: Partial<WebSocketRouteItem>) => {
      set((state) => ({
        websocket_routes: state.websocket_routes.map((r) => (r.id === id ? { ...r, ...updates } : r)),
      }));
      _syncToCanvas();
    },

    removeWebSocketRoute: (id: string) => {
      set((state) => ({
        websocket_routes: state.websocket_routes.filter((r) => r.id !== id),
        selectedItemId: state.selectedItemId === id ? null : state.selectedItemId,
        selectedItemType: state.selectedItemId === id ? null : state.selectedItemType,
      }));
      _syncToCanvas();
    },

    // -----------------------------------------------------------------------
    // Settings actions
    // -----------------------------------------------------------------------
    setProtocolType: (type: ProtocolType) => {
      set((state) => {
        const updates: Partial<ApigwConfigState> = { protocol_type: type };

        // Create default WebSocket routes when switching to WEBSOCKET and none exist
        if (type === 'WEBSOCKET' && state.websocket_routes.length === 0) {
          updates.websocket_routes = createDefaultWebSocketRoutes();
        }

        return updates;
      });
      _syncToCanvas();
    },

    updateSettings: (updates) => {
      set(updates);
      _syncToCanvas();
    },

    updateDomain: (updates) => {
      set(updates);
      _syncToCanvas();
    },

    updateVpcLink: (updates) => {
      set(updates);
      _syncToCanvas();
    },

    // -----------------------------------------------------------------------
    // Selection
    // -----------------------------------------------------------------------
    selectItem: (id: string | null, type: 'route' | 'stage' | 'authorizer' | 'websocket_route' | null) => {
      set({ selectedItemId: id, selectedItemType: type });
    },
  };
});
