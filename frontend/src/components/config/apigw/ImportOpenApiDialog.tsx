'use client';

import * as React from 'react';
import { Loader2, Upload, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { parseOpenApiSpec } from '@/lib/openapi/openapi-parser';
import { mapOpenApiToConfig } from '@/lib/openapi/openapi-mapper';
import { useApigwConfigStore } from '@/store/apigw-config-store';
import type { MapResult, ImportStrategy } from '@/lib/openapi/types';
import type { RouteItem, AuthorizerItem } from '@/types/apigw-config';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ImportOpenApiDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type DialogState = 'idle' | 'parsing' | 'error' | 'preview' | 'applying';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ImportOpenApiDialog({ open, onOpenChange }: ImportOpenApiDialogProps) {
  const [state, setState] = React.useState<DialogState>('idle');
  const [errorMessage, setErrorMessage] = React.useState('');
  const [pasteContent, setPasteContent] = React.useState('');
  const [mapResult, setMapResult] = React.useState<MapResult | null>(null);
  const [selectedServerUrl, setSelectedServerUrl] = React.useState<string | undefined>(undefined);
  const [strategy, setStrategy] = React.useState<ImportStrategy>('replace');

  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Store state
  const routes = useApigwConfigStore((s) => s.routes);
  const protocolType = useApigwConfigStore((s) => s.protocol_type);

  const hasExistingRoutes = routes.length > 0;

  // Reset state when dialog opens/closes
  React.useEffect(() => {
    if (!open) {
      setState('idle');
      setErrorMessage('');
      setPasteContent('');
      setMapResult(null);
      setSelectedServerUrl(undefined);
      setStrategy('replace');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }, [open]);

  // -------------------------------------------------------------------------
  // Parse logic
  // -------------------------------------------------------------------------

  function handleParse(content: string) {
    setState('parsing');

    // Use setTimeout to allow the UI to show the loading state
    setTimeout(() => {
      const result = parseOpenApiSpec(content);

      if (!result.success) {
        setErrorMessage(result.error);
        setState('error');
        return;
      }

      const mapped = mapOpenApiToConfig(result.spec, {
        selectedServerUrl: undefined,
      });

      setMapResult(mapped);
      // Default to first server URL if available
      if (mapped.serverUrls.length > 0) {
        setSelectedServerUrl(mapped.serverUrls[0]);
      }
      setState('preview');
    }, 50);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const content = reader.result as string;
      handleParse(content);
    };
    reader.onerror = () => {
      setErrorMessage('Failed to read file');
      setState('error');
    };
    reader.readAsText(file);
  }

  function handlePasteSubmit() {
    if (!pasteContent.trim()) return;
    handleParse(pasteContent);
  }

  function handleRetry() {
    setState('idle');
    setErrorMessage('');
    setPasteContent('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  // -------------------------------------------------------------------------
  // Server URL change — re-map with selected URL
  // -------------------------------------------------------------------------

  function handleServerUrlChange(url: string) {
    const resolvedUrl = url === '__none__' ? undefined : url;
    setSelectedServerUrl(resolvedUrl);

    // Re-map with the new server URL if we have a result
    if (mapResult) {
      // We need the original spec to re-map. Since we don't store it,
      // we just update target_service_uri on existing routes.
      const updatedRoutes = mapResult.routes.map((route) => ({
        ...route,
        target_service_uri: resolvedUrl ? resolvedUrl + route.path : undefined,
      }));
      setMapResult({ ...mapResult, routes: updatedRoutes });
    }
  }

  // -------------------------------------------------------------------------
  // Apply logic
  // -------------------------------------------------------------------------

  function handleApply() {
    if (!mapResult) return;

    setState('applying');

    setTimeout(() => {
      const store = useApigwConfigStore.getState();

      if (strategy === 'replace') {
        // Replace: clear existing and set imported data
        // Set routes to imported (replaces all existing)
        useApigwConfigStore.setState({ routes: mapResult.routes });
        // Set authorizers to imported
        useApigwConfigStore.setState({ authorizers: mapResult.authorizers });
        // Update settings
        store.updateSettings({
          api_name: mapResult.settings.api_name || '',
          description: mapResult.settings.description || '',
          api_key_required: mapResult.settings.api_key_required || false,
          cors_configuration: mapResult.settings.cors_configuration || {},
        });
        // Update protocol type if different
        if (mapResult.settings.protocol_type !== store.protocol_type) {
          store.setProtocolType(mapResult.settings.protocol_type);
        }
      } else {
        // Merge: add only unique routes and authorizers
        const existingRoutes = store.routes;
        const existingAuthorizers = store.authorizers;

        // Filter imported routes to only those with unique (method, path)
        const existingRouteKeys = new Set(
          existingRoutes.map((r: RouteItem) => `${r.method}:${r.path}`)
        );
        const uniqueRoutes = mapResult.routes.filter(
          (r) => !existingRouteKeys.has(`${r.method}:${r.path}`)
        );

        // Append unique routes
        useApigwConfigStore.setState({
          routes: [...existingRoutes, ...uniqueRoutes],
        });

        // Filter authorizers with unique names
        const existingAuthorizerNames = new Set(
          existingAuthorizers.map((a: AuthorizerItem) => a.name)
        );
        const uniqueAuthorizers = mapResult.authorizers.filter(
          (a) => !existingAuthorizerNames.has(a.name)
        );

        // Append unique authorizers
        useApigwConfigStore.setState({
          authorizers: [...existingAuthorizers, ...uniqueAuthorizers],
        });

        // Only update settings fields that are currently empty/default
        const settingsUpdates: Record<string, unknown> = {};
        if (!store.api_name && mapResult.settings.api_name) {
          settingsUpdates.api_name = mapResult.settings.api_name;
        }
        if (!store.description && mapResult.settings.description) {
          settingsUpdates.description = mapResult.settings.description;
        }
        if (!store.api_key_required && mapResult.settings.api_key_required) {
          settingsUpdates.api_key_required = mapResult.settings.api_key_required;
        }
        if (
          Object.keys(store.cors_configuration).length === 0 &&
          mapResult.settings.cors_configuration
        ) {
          settingsUpdates.cors_configuration = mapResult.settings.cors_configuration;
        }

        if (Object.keys(settingsUpdates).length > 0) {
          store.updateSettings(settingsUpdates as Parameters<typeof store.updateSettings>[0]);
        }
      }

      onOpenChange(false);
    }, 50);
  }

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------

  function renderIdleState() {
    return (
      <div className="flex flex-col gap-4">
        {/* File upload */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="openapi-file-upload">Upload specification file</Label>
          <Input
            id="openapi-file-upload"
            ref={fileInputRef}
            type="file"
            accept=".json,.yaml,.yml"
            onChange={handleFileChange}
          />
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-muted-foreground">or</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* Paste textarea */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="openapi-paste">Paste specification content</Label>
          <textarea
            id="openapi-paste"
            className="min-h-[120px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:border-ring focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30"
            placeholder="Paste your OpenAPI JSON or YAML here..."
            value={pasteContent}
            onChange={(e) => setPasteContent(e.target.value)}
          />
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handlePasteSubmit}
            disabled={!pasteContent.trim()}
          >
            Parse Specification
          </Button>
        </DialogFooter>
      </div>
    );
  }

  function renderParsingState() {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Parsing specification...</p>
      </div>
    );
  }

  function renderErrorState() {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3 rounded-md border border-destructive/50 bg-destructive/5 p-3">
          <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
          <p className="text-sm text-destructive">{errorMessage}</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleRetry}>Try Again</Button>
        </DialogFooter>
      </div>
    );
  }

  function renderPreviewState() {
    if (!mapResult) return null;

    const { settings, routes: importedRoutes, authorizers: importedAuthorizers, serverUrls, summary } = mapResult;

    // Group routes by tag
    const routesByTag: Record<string, RouteItem[]> = {};
    for (const route of importedRoutes) {
      const tag = route.tag || 'Untagged';
      if (!routesByTag[tag]) routesByTag[tag] = [];
      routesByTag[tag].push(route);
    }

    const protocolChangeWarning =
      settings.protocol_type && settings.protocol_type !== protocolType;

    return (
      <div className="flex flex-col gap-4">
        {/* API Info */}
        <div className="flex flex-col gap-1">
          {settings.api_name && (
            <p className="text-sm font-medium">{settings.api_name}</p>
          )}
          {settings.description && (
            <p className="text-xs text-muted-foreground line-clamp-2">
              {settings.description}
            </p>
          )}
        </div>

        {/* Summary badges */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
            {summary.routeCount} route{summary.routeCount !== 1 ? 's' : ''}
          </span>
          {summary.authorizerCount > 0 && (
            <span className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
              {summary.authorizerCount} authorizer{summary.authorizerCount !== 1 ? 's' : ''}
            </span>
          )}
          {summary.hasCors && (
            <span className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
              CORS
            </span>
          )}
        </div>

        {/* Security info */}
        <div className="flex flex-col gap-1 text-xs text-muted-foreground">
          <p>API Key Required: {summary.hasApiKey ? 'Yes' : 'No'}</p>
          {importedAuthorizers.length > 0 && (
            <p>
              Authorizers: {importedAuthorizers.map((a) => a.name).join(', ')}
            </p>
          )}
        </div>

        {/* Server URL selector */}
        {serverUrls.length > 1 && (
          <div className="flex flex-col gap-2">
            <Label>Server URL</Label>
            <Select
              value={selectedServerUrl || '__none__'}
              onValueChange={handleServerUrlChange}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a server URL" />
              </SelectTrigger>
              <SelectContent>
                {serverUrls.map((url) => (
                  <SelectItem key={url} value={url}>
                    {url}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {serverUrls.length === 1 && (
          <div className="text-xs text-muted-foreground">
            Server: {serverUrls[0]}
          </div>
        )}

        {/* Route list grouped by tag */}
        <div className="flex flex-col gap-2">
          <Label>Routes</Label>
          <div className="max-h-[200px] overflow-y-auto rounded-md border p-2">
            {Object.entries(routesByTag).map(([tag, tagRoutes]) => (
              <div key={tag} className="mb-2 last:mb-0">
                {Object.keys(routesByTag).length > 1 && (
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    {tag}
                  </p>
                )}
                <div className="flex flex-col gap-0.5">
                  {tagRoutes.map((route) => (
                    <div
                      key={`${route.method}-${route.path}`}
                      className="flex items-center gap-2 text-xs"
                    >
                      <span className="inline-flex w-16 shrink-0 items-center justify-center rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase">
                        {route.method}
                      </span>
                      <span className="font-mono text-muted-foreground">
                        {route.path}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Protocol change warning */}
        {protocolChangeWarning && (
          <div className="flex items-start gap-2 rounded-md border border-yellow-500/50 bg-yellow-500/5 p-2">
            <AlertCircle className="mt-0.5 size-3.5 shrink-0 text-yellow-600" />
            <p className="text-xs text-yellow-700 dark:text-yellow-400">
              Protocol will change from {protocolType} to {settings.protocol_type}
            </p>
          </div>
        )}

        {/* Import strategy selector — only shown when existing routes > 0 */}
        {hasExistingRoutes && (
          <div className="flex flex-col gap-2">
            <Label>Import Strategy</Label>
            <RadioGroup
              value={strategy}
              onValueChange={(val) => setStrategy(val as ImportStrategy)}
              className="flex gap-4"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="replace" id="strategy-replace" />
                <Label htmlFor="strategy-replace" className="font-normal">
                  Replace
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="merge" id="strategy-merge" />
                <Label htmlFor="strategy-merge" className="font-normal">
                  Merge
                </Label>
              </div>
            </RadioGroup>
            <p className="text-xs text-muted-foreground">
              {strategy === 'replace'
                ? 'All existing routes and authorizers will be replaced.'
                : 'Only new routes (unique method + path) will be added.'}
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleApply}>
            <Upload className="size-3.5" data-icon="inline-start" />
            Apply Import
          </Button>
        </DialogFooter>
      </div>
    );
  }

  function renderApplyingState() {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Applying configuration...</p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Main render
  // -------------------------------------------------------------------------

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import OpenAPI Specification</DialogTitle>
          <DialogDescription>
            Upload or paste an OpenAPI 3.x specification to import routes and settings.
          </DialogDescription>
        </DialogHeader>

        {state === 'idle' && renderIdleState()}
        {state === 'parsing' && renderParsingState()}
        {state === 'error' && renderErrorState()}
        {state === 'preview' && renderPreviewState()}
        {state === 'applying' && renderApplyingState()}
      </DialogContent>
    </Dialog>
  );
}
