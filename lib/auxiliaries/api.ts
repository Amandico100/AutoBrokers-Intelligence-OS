// Helpers de client para consumir as rotas de Auxiliares (usados na UI do 38A3).
import type {
  AuxiliaryRun,
  AuxiliaryTemplate,
  TenantAuxiliary,
  RunResumoResponse,
  ResumoConversation,
} from './types';

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export async function fetchTemplates(): Promise<{ templates: AuxiliaryTemplate[] }> {
  return getJson('/api/auxiliaries/templates');
}

export async function fetchInstalled(): Promise<{ installed: TenantAuxiliary[] }> {
  return getJson('/api/auxiliaries/installed');
}

export async function fetchRuns(): Promise<{ runs: AuxiliaryRun[] }> {
  return getJson('/api/auxiliaries/runs');
}

export async function fetchRun(runId: string): Promise<{ run: AuxiliaryRun }> {
  return getJson(`/api/auxiliaries/runs/${runId}`);
}

export async function fetchResumoConversations(): Promise<{ conversations: ResumoConversation[] }> {
  return getJson('/api/auxiliaries/resumo-atendimentos/conversations');
}

export async function runResumoAtendimentos(conversationId?: string): Promise<RunResumoResponse> {
  const res = await fetch('/api/auxiliaries/resumo-atendimentos/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(conversationId ? { conversation_id: conversationId } : {}),
  });
  return res.json() as Promise<RunResumoResponse>;
}
