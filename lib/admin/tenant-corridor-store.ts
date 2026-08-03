// SPEC-063 (03/08/2026) — corredores por corretora. Server-only.
//
// O CATÁLOGO VEM DO CÓDIGO
// ========================
// `GET /api/corridors/catalog` (backend) devolve os corredores que
// `backend/app/services/corridor_playbooks.py` sabe executar. É a mesma lista
// que o motor usa para acionar a seguradora — não há segunda lista em
// TypeScript, e é de propósito: duas listas divergem, e foi divergindo que a
// tela passou meses mostrando dois corredores enquanto o produto executava 13.
//
// `corridor_templates` NÃO É MAIS O CATÁLOGO — É A ÂNCORA DE ID
// =============================================================
// `tenant_corridors.corridor_template_id` é `uuid NOT NULL` com FK para
// `corridor_templates(id)` (verificado no banco em 03/08/2026). Sem migration,
// a ativação PRECISA de uma linha lá para apontar. Então cada corredor do
// código ganha, sob demanda e por corretora, uma linha de âncora: ela não diz
// o que o corredor é — nome, ramo, subserviços e desfecho continuam vindo do
// código. Se a âncora divergir do código, o código vence.
//
// Ativar/pausar continua gravando em `tenant_corridors`: é o registro do que a
// corretora quer usar. O que mudou foi de onde vem o CATÁLOGO.
//
// ESTE MÓDULO NÃO EXECUTA NADA: não liga canal, não abre portal, não envia
// mensagem. Só estado de configuração.
import type { SupabaseClient } from '@supabase/supabase-js';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import {
  buildCorridorCatalog,
  corridorIdForTemplateKey,
  foldActivationStatus,
  nextCorridorStatus,
  type CorridorCatalogItem,
  type CorridorFromCode,
} from '@/lib/admin/tenant-corridor-catalog';

const CATALOG_PATH = '/api/corridors/catalog';
/** O catálogo é o mesmo para todas as corretoras e só muda com deploy do
 *  backend. Um minuto de cache evita uma chamada por card renderizado sem
 *  esconder uma mudança por mais tempo do que ninguém repara. */
const CATALOG_TTL_MS = 60_000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

let catalogCache: { at: number; corridors: CorridorFromCode[] } | null = null;

/** O catálogo do código, ou `null` quando o backend não respondeu.
 *  `null` NUNCA vira lista vazia silenciosa nem cai de volta na tabela: a tela
 *  precisa poder dizer "não consegui ler", em vez de mostrar menos produto do
 *  que a corretora tem. */
export async function fetchCorridorCatalog(): Promise<CorridorFromCode[] | null> {
  if (catalogCache && Date.now() - catalogCache.at < CATALOG_TTL_MS) return catalogCache.corridors;

  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!internalKey) {
    console.error('[CORRIDORS] chave interna do backend não configurada');
    return null;
  }
  let backendUrl: string;
  try {
    backendUrl = getBackendUrl();
  } catch (error) {
    if (error instanceof BackendUrlError) {
      console.error('[CORRIDORS] backend não configurado');
      return null;
    }
    throw error;
  }

  try {
    const res = await fetch(`${backendUrl}${CATALOG_PATH}`, {
      headers: { 'X-AutoBrokers-Internal-Key': internalKey },
      cache: 'no-store',
    });
    if (!res.ok) {
      console.error(`[CORRIDORS] catálogo respondeu ${res.status}`);
      return null;
    }
    const body = await res.json().catch(() => ({}));
    const corridors = Array.isArray(body?.corridors) ? (body.corridors as CorridorFromCode[]) : null;
    if (!corridors || corridors.length === 0) return null;
    catalogCache = { at: Date.now(), corridors };
    return corridors;
  } catch (error) {
    console.error('[CORRIDORS] falha ao ler o catálogo:', error);
    return null;
  }
}

/** `corridor_id` → ids de `corridor_templates` que ancoram aquele corredor
 *  para ESTA corretora (a âncora nova e, quando houver, as linhas legadas). */
async function loadAnchors(supabase: SupabaseClient, companyId: string): Promise<Map<string, string[]>> {
  const byCorridor = new Map<string, string[]>();
  if (!UUID.test(companyId)) return byCorridor;
  const { data } = await supabase
    .from('corridor_templates')
    .select('id, corridor_key, scope, company_id')
    .or(`scope.eq.global,company_id.eq.${companyId}`);
  for (const row of (data ?? []) as Array<{ id: string; corridor_key: string | null }>) {
    const corridorId = corridorIdForTemplateKey(String(row.corridor_key ?? ''));
    if (!corridorId || !row.id) continue;
    const list = byCorridor.get(corridorId) ?? [];
    list.push(String(row.id));
    byCorridor.set(corridorId, list);
  }
  return byCorridor;
}

/** A linha de `corridor_templates` que dá um uuid a este corredor nesta
 *  corretora. Criada sob demanda e idempotente — é recibo de ativação, não
 *  catálogo. */
async function ensureCorridorAnchor(
  supabase: SupabaseClient,
  companyId: string,
  corridor: CorridorFromCode,
): Promise<string | null> {
  const found = await supabase
    .from('corridor_templates')
    .select('id')
    .eq('company_id', companyId)
    .eq('corridor_key', corridor.corridor_id)
    .limit(1)
    .maybeSingle();
  if (found.data?.id) return String(found.data.id);

  const created = await supabase
    .from('corridor_templates')
    .insert({
      company_id: companyId,
      scope: 'tenant',
      corridor_key: corridor.corridor_id,
      display_name: corridor.title,
      insurer_key: corridor.insurer_key,
      line_kind: corridor.line_kind,
      macro_service: 'assistencia_24h',
      channel_ref: corridor.channel,
      source_of_truth: 'backend/app/services/corridor_playbooks.py',
      metadata: { anchor_only: true, playbook_ref: corridor.playbook_ref },
    })
    .select('id')
    .maybeSingle();
  if (created.data?.id) return String(created.data.id);

  // Duas abas clicando junto: o índice único barra o segundo insert. Reler é a
  // resposta certa — criar uma segunda âncora daria dois recibos do mesmo fato.
  const again = await supabase
    .from('corridor_templates')
    .select('id')
    .eq('company_id', companyId)
    .eq('corridor_key', corridor.corridor_id)
    .limit(1)
    .maybeSingle();
  return again.data?.id ? String(again.data.id) : null;
}

export async function listTenantCorridors(supabase: SupabaseClient, companyId: string): Promise<{
  ok: boolean;
  error?: string;
  items: CorridorCatalogItem[];
  active: number;
}> {
  const corridors = await fetchCorridorCatalog();
  if (!corridors) return { ok: false, error: 'catalogo_indisponivel', items: [], active: 0 };

  const anchors = await loadAnchors(supabase, companyId);
  const { data: acts } = await supabase
    .from('tenant_corridors')
    .select('corridor_template_id, status')
    .eq('company_id', companyId);

  const statusByTemplate = new Map<string, string>();
  for (const a of (acts ?? []) as Array<{ corridor_template_id: string; status: string | null }>) {
    if (a?.corridor_template_id) statusByTemplate.set(String(a.corridor_template_id), String(a.status ?? 'active'));
  }

  const statusByCorridorId: Record<string, string | null> = {};
  for (const c of corridors) {
    const ids = anchors.get(c.corridor_id) ?? [];
    statusByCorridorId[c.corridor_id] = foldActivationStatus(ids.map((id) => statusByTemplate.get(id) ?? null));
  }

  const items = buildCorridorCatalog(corridors, statusByCorridorId);
  return { ok: true, items, active: items.filter((i) => i.status === 'active').length };
}

export async function setTenantCorridorStatus(
  supabase: SupabaseClient,
  companyId: string,
  corridorId: string,
  action: string,
  userId: string,
) {
  const status = nextCorridorStatus(action);
  if (!status) return { ok: false as const, error: 'acao_invalida' };
  if (!UUID.test(companyId)) return { ok: false as const, error: 'company_invalida' };

  // O corredor precisa EXISTIR no código. Sem catálogo não se grava nada: uma
  // ativação às cegas criaria âncora para um corredor que o motor não executa.
  const corridors = await fetchCorridorCatalog();
  if (!corridors) return { ok: false as const, error: 'catalogo_indisponivel' };
  const corridor = corridors.find((c) => c.corridor_id === corridorId);
  if (!corridor) return { ok: false as const, error: 'corredor_inexistente' };

  const anchorId = await ensureCorridorAnchor(supabase, companyId, corridor);
  if (!anchorId) return { ok: false as const, error: 'ancora_indisponivel' };

  const agora = new Date().toISOString();
  const { error } = await supabase.from('tenant_corridors').upsert({
    company_id: companyId,
    corridor_template_id: anchorId,
    status,
    installed_by: userId,
    updated_at: agora,
  }, { onConflict: 'company_id,corridor_template_id' });
  if (error) return { ok: false as const, error: 'persist_failed' };

  // As ativações LEGADAS do mesmo corredor vão junto. A corretora que ligou
  // "Allianz Residencial" e "Allianz Residencial — Eletricista" vê um card só;
  // pausar o card e deixar uma das linhas ativa seria mentir na próxima leitura.
  const anchors = await loadAnchors(supabase, companyId);
  const outros = (anchors.get(corridorId) ?? []).filter((id) => id !== anchorId);
  if (outros.length > 0) {
    await supabase
      .from('tenant_corridors')
      .update({ status, updated_at: agora })
      .eq('company_id', companyId)
      .in('corridor_template_id', outros);
  }

  return { ok: true as const, corridor_id: corridorId, status };
}
