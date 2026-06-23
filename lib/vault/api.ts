// Helpers de client para consumir as rotas do Vault (uso na UI do 39A3).
import type {
  ConnectorTemplate,
  TenantConnection,
  PermissionGrant,
  ApprovalRequest,
  VaultAuditLog,
  CreateTenantConnectionInput,
  CreatePermissionGrantInput,
  CreateApprovalRequestInput,
  ConfigureWhatsAppInput,
  WhatsAppTestResult,
} from './types';

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  return res.json() as Promise<T>;
}

export function fetchConnectorTemplates() {
  return getJson<{ templates: ConnectorTemplate[] }>('/api/vault/templates');
}

export function fetchTenantConnections() {
  return getJson<{ connections: TenantConnection[] }>('/api/vault/connections');
}

export function createTenantConnection(input: CreateTenantConnectionInput) {
  return postJson<{ connection?: TenantConnection; error?: string }>('/api/vault/connections', input);
}

export function fetchConnection(connectionId: string) {
  return getJson<{ connection: TenantConnection }>(`/api/vault/connections/${connectionId}`);
}

export async function updateConnection(connectionId: string, patch: Record<string, unknown>) {
  const res = await fetch(`/api/vault/connections/${connectionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  return res.json() as Promise<{ connection?: TenantConnection; error?: string }>;
}

export function fetchPermissions(connectionId: string) {
  return getJson<{ permissions: PermissionGrant[] }>(`/api/vault/connections/${connectionId}/permissions`);
}

export function createPermission(connectionId: string, input: CreatePermissionGrantInput) {
  return postJson<{ permission?: PermissionGrant; error?: string }>(
    `/api/vault/connections/${connectionId}/permissions`,
    input,
  );
}

// SPEC-014 C-FIX-1 (E): revoga (não apaga) uma permissão.
export async function deletePermission(connectionId: string, grantId: string) {
  const res = await fetch(`/api/vault/connections/${connectionId}/permissions`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grant_id: grantId }),
  });
  return res.json() as Promise<{ ok?: boolean; error?: string }>;
}

// C-FIX-2: gerenciar conexão (arquivar / desconectar / excluir rascunho vazio).
export async function manageConnection(connectionId: string, mode: 'archive' | 'disconnect' | 'delete') {
  const res = await fetch(`/api/vault/connections/${connectionId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  return res.json() as Promise<{ ok?: boolean; status?: string; deleted?: boolean; error?: string }>;
}

// C-FIX-2: testar a conexão InfoCap usando o segredo já salvo (atualiza status real).
export async function testInfocapConnection(connectionId: string) {
  const res = await fetch('/api/attendance/connectors/infocap/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tenant_connection_id: connectionId }),
  });
  return res.json() as Promise<{ ok?: boolean; status?: string; health?: string; error?: string }>;
}

export function fetchApprovalRequests() {
  return getJson<{ approvals: ApprovalRequest[] }>('/api/vault/approvals');
}

export function createApprovalRequest(input: CreateApprovalRequestInput) {
  return postJson<{ approval?: ApprovalRequest; error?: string }>('/api/vault/approvals', input);
}

export function approveRequest(approvalId: string, reason?: string) {
  return postJson<{ approval?: ApprovalRequest; error?: string }>(
    `/api/vault/approvals/${approvalId}/approve`,
    reason ? { reason } : {},
  );
}

export function rejectRequest(approvalId: string, reason?: string) {
  return postJson<{ approval?: ApprovalRequest; error?: string }>(
    `/api/vault/approvals/${approvalId}/reject`,
    reason ? { reason } : {},
  );
}

export function fetchAuditLog() {
  return getJson<{ events: VaultAuditLog[] }>('/api/vault/audit');
}

export function configureWhatsAppConnection(connectionId: string, input: ConfigureWhatsAppInput) {
  return postJson<{ success?: boolean; connection?: TenantConnection; error?: string }>(
    `/api/vault/connections/${connectionId}/whatsapp/configure`,
    input,
  );
}

export function testWhatsAppConnection(connectionId: string) {
  return postJson<WhatsAppTestResult>(`/api/vault/connections/${connectionId}/whatsapp/test`, {});
}

export function executeApproval(approvalId: string) {
  return postJson<{
    success?: boolean;
    dry_run?: boolean;
    approval?: ApprovalRequest;
    message?: string;
    error?: string;
  }>(`/api/vault/approvals/${approvalId}/execute`, {});
}
