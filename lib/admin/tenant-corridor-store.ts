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
import { decidirLoteDeAtivacao } from '@/lib/admin/corridor-bulk-decision';

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

/** A linha de âncora, como o banco a quer. Uma função só, para o lote e para
 *  o corredor único escreverem exatamente a mesma coisa. */
function linhaDeAncora(companyId: string, corridor: CorridorFromCode) {
  return {
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
  };
}

/**
 * As âncoras de N corredores, em **três idas ao banco** — não em 2N.
 *
 * 🔴 SPEC-093 BLOCO G.2 — E A DECISÃO DO EXECUTOR ESTÁ AQUI.
 *
 * 📊 Medido em 25/08/2026: a versão anterior fazia `SELECT + INSERT` **por
 * corredor**. Ligar tudo na primeira corretora eram **14 SELECTs + 14 INSERTs,
 * um a um**, antes do lote de status: 42 idas sequenciais ao Supabase num
 * botão que o Founder quer que pareça instantâneo.
 *
 * 📊 E `corridor_templates` tem **2 linhas, ambas `scope='global'` com
 * `company_id` NULO** — enquanto a busca filtrava `.eq('company_id', companyId)`.
 * Ela não achava nenhuma, e inseria uma âncora nova para cada corredor. O laço
 * era caro **e** não reaproveitava nada.
 *
 * ⚠️ A SPEC deixou a escolha em aberto: lotear, ou aceitar o laço e escrever
 * por que ele é retomável. **Loteia** — e o motivo é que lotear torna a
 * retomabilidade mais fácil de provar, não mais difícil: são três passos, cada
 * um idempotente sozinho.
 *
 * ## Por que INSERT dos que faltam, e não `upsert`
 *
 * 📊 O índice único de `corridor_templates` é uma EXPRESSÃO
 * (`COALESCE(company_id, …), corridor_key, COALESCE(subcorridor_key, …)`), e
 * `onConflict` do PostgREST precisa de colunas ou de um nome de constraint —
 * uma expressão não serve. Então: lê o que existe, insere só o que falta, e
 * **relê**. Duas abas clicando junto fazem o INSERT do segundo falhar inteiro;
 * a releitura devolve as âncoras que a primeira criou, que é a resposta certa.
 * Criar uma segunda âncora daria dois recibos do mesmo fato.
 */
async function ensureCorridorAnchors(
  supabase: SupabaseClient,
  companyId: string,
  corridors: CorridorFromCode[],
): Promise<Map<string, string>> {
  const porCorredor = new Map<string, string>();
  if (corridors.length === 0) return porCorredor;
  const chaves = corridors.map((c) => c.corridor_id);

  const ler = async () => {
    const { data } = await supabase
      .from('corridor_templates')
      .select('id, corridor_key')
      .eq('company_id', companyId)
      .in('corridor_key', chaves);
    for (const row of (data ?? []) as Array<{ id: string; corridor_key: string | null }>) {
      if (row?.id && row.corridor_key) porCorredor.set(String(row.corridor_key), String(row.id));
    }
  };

  await ler();
  const faltando = corridors.filter((c) => !porCorredor.has(c.corridor_id));
  if (faltando.length === 0) return porCorredor;

  const { error } = await supabase
    .from('corridor_templates')
    .insert(faltando.map((c) => linhaDeAncora(companyId, c)));
  // ⚠️ O erro NÃO interrompe: pode ser a corrida de duas abas, e a releitura
  // abaixo é quem decide. Interromper aqui devolveria "falhou" para um clique
  // que na verdade já tinha funcionado do outro lado.
  if (error) console.warn('[CORRIDORS] insert de âncoras em lote:', error.message);
  await ler();
  return porCorredor;
}

/** A âncora de UM corredor. Mesma implementação do lote, com um item — §5:
 *  duas cópias divergiriam na primeira correção que só uma recebesse. */
async function ensureCorridorAnchor(
  supabase: SupabaseClient,
  companyId: string,
  corridor: CorridorFromCode,
): Promise<string | null> {
  const mapa = await ensureCorridorAnchors(supabase, companyId, [corridor]);
  return mapa.get(corridor.corridor_id) ?? null;
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

/**
 * 🔴 SPEC-093 BLOCO G.1 — UM CLIQUE LIGA OS 14, EM VEZ DE CATORZE.
 *
 * > **Decisão do Founder, 25/08:** *"na hora que a corretora ligar o
 * > atendimento, tudo pode estar ligado automaticamente. Ela pode desligar no
 * > dashboard."*
 *
 * 📊 Medido em `build_corridor_catalog()`, que é a fonte da tela: **14 cartões**
 * (10 seguradoras · auto 10 + residencial 4) somando 73 subserviços. Os 73
 * aparecem como TEXTO dentro do cartão, nunca como coisa clicável — quem liga e
 * desliga é o corredor. **Ela clica no máximo 14, já hoje.**
 *
 * ## ⚠️ A ESCOLHA DELA VENCE, E É A PARTE QUE IMPORTA
 *
 * Um corredor que a corretora **pausou de propósito NÃO volta sozinho**. Sem
 * isso, o dashboard desfaz a escolha dela toda manhã — e ela não tem como
 * saber, porque o botão diz "ligar tudo" e faz exatamente isso.
 *
 * 🔴 A regra é por LINHA EXISTENTE, não por status calculado: só entra no lote
 * quem **não tem ativação nenhuma**. Quem já está `active` também fica de fora,
 * e é o que torna o botão idempotente de graça.
 *
 * ## ④ RETOMABILIDADE — três passos, cada um idempotente sozinho
 *
 * ```
 * 1. ler as âncoras + inserir as que faltam   (idempotente: relê e reaproveita)
 * 2. ler as ativações que já existem          (leitura pura)
 * 3. upsert do status, em UM lote             (idempotente: `onConflict`)
 * ```
 *
 * ⚠️ A conexão caindo entre 1 e 3 deixa âncoras órfãs — linhas de
 * `corridor_templates` sem ativação. Isso é **exatamente o estado de uma
 * corretora que nunca clicou**, e a rodada seguinte as reaproveita. **O fim é o
 * mesmo de uma rodada limpa**, que é o que o gate ④ cobra.
 */
export async function ativarTodosOsCorredores(
  supabase: SupabaseClient,
  companyId: string,
  userId: string,
): Promise<{
  ok: boolean; error?: string;
  ativados: number; respeitados: number; ja_ativos: number;
  /** 🔴 Corredores que ficaram SEM âncora — nenhuma ativação foi criada para eles. */
  sem_ancora: number;
}> {
  const vazio = { ativados: 0, respeitados: 0, ja_ativos: 0, sem_ancora: 0 };
  if (!UUID.test(companyId)) return { ok: false as const, error: 'company_invalida', ...vazio };

  // Sem catálogo não se grava nada — uma ativação às cegas criaria âncora para
  // um corredor que o motor não executa.
  const corridors = await fetchCorridorCatalog();
  if (!corridors) return { ok: false as const, error: 'catalogo_indisponivel', ...vazio };

  const ancoras = await ensureCorridorAnchors(supabase, companyId, corridors);

  // ② A ESCOLHA DA CORRETORA. Toda linha de ativação que já existe fica como
  // está — `paused` continua pausado, `active` continua ativo.
  const { data: existentes } = await supabase
    .from('tenant_corridors')
    .select('corridor_template_id, status')
    .eq('company_id', companyId);
  const statusPorAncora = new Map<string, string>();
  for (const a of (existentes ?? []) as Array<{ corridor_template_id: string; status: string | null }>) {
    if (a?.corridor_template_id) {
      statusPorAncora.set(String(a.corridor_template_id), String(a.status ?? 'active'));
    }
  }

  // ⚠️ As âncoras LEGADAS do mesmo corredor contam. A corretora que pausou
  // "Allianz Residencial" pelo cartão pausou as duas linhas (ver
  // `setTenantCorridorStatus`); ignorá-las aqui religaria uma delas, e a
  // próxima leitura mostraria o cartão ativo de novo — desfazendo a escolha
  // dela por um caminho que ninguém olha.
  const legado = await loadAnchors(supabase, companyId);

  // 🔴 A DECISÃO É PURA E MORA EM `corridor-bulk-decision.ts` — é ela que o
  // gate em `node` executa. Aqui só se traduz o lote em escrita.
  const lote = decidirLoteDeAtivacao(
    corridors.map((c) => ({
      corridorId: c.corridor_id,
      anchorId: ancoras.get(c.corridor_id) ?? null,
      legado: legado.get(c.corridor_id) ?? [],
    })),
    Object.fromEntries(statusPorAncora),
  );

  const agora = new Date().toISOString();
  const novas = lote.ativar.map((anchorId) => ({
    company_id: companyId,
    corridor_template_id: anchorId,
    status: 'active',
    installed_by: userId,
    updated_at: agora,
  }));
  const respeitados = lote.respeitados.length;
  const jaAtivos = lote.jaAtivos.length;

  if (novas.length > 0) {
    const { error } = await supabase
      .from('tenant_corridors')
      .upsert(novas, { onConflict: 'company_id,corridor_template_id' });
    if (error) {
      return {
        ok: false as const, error: 'persist_failed',
        ativados: 0, respeitados, ja_ativos: jaAtivos, sem_ancora: lote.semAncora.length,
      };
    }
  }

  // 🔴 "LIGOU TUDO" QUE LIGOU NADA TEM DE APARECER.
  //
  // ⚠️ O painel achou: quando o INSERT das âncoras falha inteiro, todos os
  // corredores caem em `semAncora`, `novas` fica vazio, o upsert é pulado — e a
  // função devolvia `{ok: true, ativados: 0}` com 200 na resposta. A corretora
  // ligava o atendimento, nenhum corredor era ativado, e **nem uma linha de log
  // dizia isso**.
  //
  // 🔴 `ok` continua `true`: nada quebrou, e falhar aqui não pode desfazer o
  // toggle. Mas o número sai, e o log GRITA quando ele é o total.
  if (lote.semAncora.length > 0) {
    console.error(
      `[CORRIDORS] ${lote.semAncora.length} de ${corridors.length} corredores ficaram `
      + `SEM âncora para a corretora ${companyId} — eles NÃO foram ativados: `
      + lote.semAncora.join(', '));
  }

  return {
    ok: true as const, ativados: novas.length, respeitados, ja_ativos: jaAtivos,
    sem_ancora: lote.semAncora.length,
  };
}
