// SPEC-013 B1 — galeria + lifecycle de Auxiliares por corretora. Server-only.
// REUSA o motor existente (SPEC-002): runtime smith_agent_blueprint cria um Agent Smith
// ISOLADO na corretora (createAgentViaBackend). Lifecycle (pausar/retomar/desinstalar) é
// status em tenant_auxiliaries. Nada de provider externo / ação externa na instalação.
import type { SupabaseClient } from '@supabase/supabase-js';
import { parseRuntimeConfig } from '@/lib/admin/auxiliary-runtime';
import { buildAgentCreatePayload, createAgentViaBackend } from '@/lib/admin/agent-blueprints';
import { nextTenantAuxStatus, type TenantAuxAction } from '@/lib/admin/auxiliary-publish';

function visibilityOf(defaultConfig: any): { type: string; company_id?: string } {
  const v = defaultConfig?.visibility;
  return v && typeof v === 'object' ? v : { type: 'global' };
}

/**
 * SPEC-060 §37 — Auxiliar cuja instalação tem efeito no backend.
 *
 * O Radar precisa CRIAR os monitores no momento em que é instalado. Sem isso a
 * corretora instala, vê o card "ativo" e nunca recebe aviso — que é pior do
 * que não instalar, porque parece que está funcionando.
 *
 * O template declara o serviço em `default_config.instalacao`; aqui só
 * traduzimos essa declaração numa chamada. Falha não desfaz a instalação: o
 * status vira `awaiting_runtime`, do mesmo jeito que já acontece quando um
 * Agent não pôde ser criado.
 */
const INSTALACAO_NO_BACKEND: Record<string, string> = {
  'radar-mercado-regulacao': '/api/research/radar/install',
};

async function instalarNoBackend(
  slug: string, companyId: string, byUser: string,
  backend?: { url: string; apiKey: string },
): Promise<{ ok: boolean; detalhe?: string }> {
  const caminho = INSTALACAO_NO_BACKEND[slug];
  if (!caminho) return { ok: true };
  if (!backend?.url || !backend.apiKey) {
    return { ok: false, detalhe: 'serviço de pesquisa não configurado' };
  }
  try {
    const r = await fetch(`${backend.url.replace(/\/+$/, '')}${caminho}`, {
      method: 'POST',
      headers: { 'X-Internal-Key': backend.apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_id: companyId, user_id: byUser }),
      cache: 'no-store',
    });
    if (!r.ok) return { ok: false, detalhe: `backend respondeu ${r.status}` };
    const j = await r.json().catch(() => ({}));
    return { ok: j?.ok !== false, detalhe: j?.mensagem || j?.erro };
  } catch {
    return { ok: false, detalhe: 'não foi possível falar com o serviço' };
  }
}

/** Galeria do tenant: templates globais (ou exclusivos da empresa) + status de instalação. */
export async function listTenantAuxiliaries(supabase: SupabaseClient, companyId: string) {
  const { data: templates } = await supabase.from('auxiliary_templates')
    .select('id, slug, name, short_description, description, category, default_config, is_active').eq('is_active', true);
  const { data: installs } = await supabase.from('tenant_auxiliaries')
    .select('id, template_id, slug, status, config, last_run_at').eq('company_id', companyId);

  const installBySlug = new Map<string, any>();
  for (const i of installs ?? []) installBySlug.set(i.slug, i);

  const items = (templates ?? [])
    .filter((t: any) => {
      const vis = visibilityOf(t.default_config);
      return vis.type !== 'private' || vis.company_id === companyId;
    })
    .map((t: any) => {
      const inst = installBySlug.get(t.slug);
      const runtime = parseRuntimeConfig(t.default_config, t.slug);
      return {
        template_id: t.id, slug: t.slug, name: t.name,
        description: t.short_description ?? t.description ?? null, category: t.category ?? null,
        runtime_kind: runtime.kind,
        installed: Boolean(inst) && inst.status !== 'uninstalled',
        status: inst?.status ?? 'available',
        last_run_at: inst?.last_run_at ?? null,
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
  return { ok: true as const, items };
}

export async function installTenantAuxiliary(
  supabase: SupabaseClient, companyId: string, templateId: string, byUser: string,
  backend?: { url: string; apiKey: string },
) {
  const { data: tpl } = await supabase.from('auxiliary_templates')
    .select('id, slug, name, default_config, catalog_state, required_connectors, missing_for_launch')
    .eq('id', templateId).maybeSingle();
  if (!tpl?.id) return { ok: false as const, error: 'template_inexistente' };

  // SPEC-064 D.1 — "em breve" aparece no catálogo e NÃO liga.
  //
  // A trava vive aqui, e não só no botão da tela. Botão desabilitado é
  // conveniência; quem impede de verdade é o servidor. Sem isso, um POST
  // direto instalaria um Auxiliar cujo runtime é `none` — e a corretora
  // ficaria com um card "ligado" que nunca faz nada, que é pior do que não
  // ter ligado, porque parece que está trabalhando.
  if ((tpl as any).catalog_state === 'coming_soon') {
    return {
      ok: false as const,
      error: 'ainda_nao_disponivel',
      detalhe: (tpl as any).missing_for_launch || 'Este Auxiliar ainda está em construção.',
    };
  }

  // SPEC-064 + decisão do Founder de 02/08 — a conexão é da CORRETORA.
  //
  // Se ela já conectou o portal da seguradora para outro Auxiliar, este aqui
  // usa a mesma conexão: ninguém reconecta nada. O que não pode é ligar um
  // Auxiliar cuja conexão não existe — ele rodaria e falharia em silêncio.
  const exigidos: string[] = Array.isArray((tpl as any).required_connectors)
    ? (tpl as any).required_connectors : [];
  if (exigidos.length > 0) {
    const { conexoesDaCorretora } = await import('@/lib/auxiliaries/catalog');
    const prontos = await conexoesDaCorretora(supabase, companyId);
    const faltando = exigidos.filter((s) => !prontos.has(s));
    if (faltando.length > 0) {
      return { ok: false as const, error: 'falta_conectar', faltando };
    }
  }

  // idempotente por (company, slug); reativa se estava desinstalado
  //
  // ⚠️ `.maybeSingle()` devolve `data: null` E um erro (`PGRST116`) quando há
  // MAIS DE UMA linha. O erro é descartado aqui de propósito — se houver
  // duplicata, o INSERT abaixo bate na unique `(company_id, slug)` e a
  // mensagem chega no `details`. Trocar por `.limit(1)` esconderia a
  // duplicata em vez de expô-la.
  const { data: dup } = await supabase.from('tenant_auxiliaries').select('id, status').eq('company_id', companyId).eq('slug', tpl.slug).maybeSingle();
  // 🔴 `REMOVIDOS` tem DOIS valores. `uninstalled` é o que o TypeScript pensa;
  // `archived` é o que o banco de fato guarda (ver `statusValidoNoBanco`).
  // Testar só o primeiro faria um Auxiliar removido responder "já instalado" e
  // nunca mais voltar.
  if (dup?.id && !REMOVIDOS.has(String(dup.status))) {
    return { ok: true as const, already: true, install_id: dup.id, status: dup.status };
  }

  const runtime = parseRuntimeConfig((tpl as any).default_config, tpl.slug);
  let status = 'active';
  // (ver `statusValidoNoBanco` no fim do arquivo — o TypeScript e o CHECK do
  // banco falam vocabulários diferentes, e o banco vence)
  let configRuntime: Record<string, unknown> = { kind: runtime.kind };

  if (runtime.kind === 'smith_agent_blueprint') {
    if (backend?.url && backend.apiKey) {
      try {
        const payload = buildAgentCreatePayload(companyId, (runtime.agent_blueprint || { name: tpl.name, slug: tpl.slug }) as Record<string, unknown>);
        const r = await createAgentViaBackend(backend.url, backend.apiKey, payload);
        if (r.agentId) configRuntime = { kind: 'smith_agent', agent_id: r.agentId, created_from_template: true };
        else { status = 'awaiting_runtime'; configRuntime = { kind: 'smith_agent_blueprint', pending: true, agent_error: r.error || 'falha' }; }
      } catch { status = 'awaiting_runtime'; configRuntime = { kind: 'smith_agent_blueprint', pending: true }; }
    } else { status = 'awaiting_runtime'; configRuntime = { kind: 'smith_agent_blueprint', pending: true }; }
  } else if (runtime.kind === 'specific_executor') {
    configRuntime = { kind: 'specific_executor', executor: runtime.executor || tpl.slug };
  } else if (runtime.kind === 'workflow') {
    configRuntime = { kind: 'workflow', workflow: runtime.workflow };
  }

  // Efeito real da instalação, quando o template declara um. Precisa vir ANTES
  // de gravar o status: instalar "ativo" e só depois descobrir que o backend
  // recusou deixaria a corretora com um Auxiliar que não faz nada.
  const efeito = await instalarNoBackend(tpl.slug, companyId, byUser, backend);
  if (!efeito.ok) {
    status = 'awaiting_runtime';
    configRuntime = { ...configRuntime, pending: true, install_error: efeito.detalhe };
  } else if (efeito.detalhe) {
    configRuntime = { ...configRuntime, install_note: efeito.detalhe };
  }

  if (dup?.id) {
    // Mesmo tradutor do INSERT: reinstalar não pode gravar um status que o
    // CHECK recusa.
    const gravavel = statusValidoNoBanco(status);
    const { error } = await supabase.from('tenant_auxiliaries').update({ status: gravavel, config: { runtime: configRuntime }, updated_at: new Date().toISOString() }).eq('id', dup.id);
    if (error) {
      console.error('[AUX reinstall]', tpl.slug, companyId, error.message);
      return { ok: false as const, error: 'reinstall_failed', details: [error.message] };
    }
    return { ok: true as const, install_id: dup.id, status: gravavel, reinstalled: true };
  }

  const { data: created, error } = await supabase.from('tenant_auxiliaries').insert({
    company_id: companyId, template_id: tpl.id, slug: tpl.slug, name: tpl.name,
    // 🔴 `display_name` NÃO entra aqui. A coluna não existe em
    // `tenant_auxiliaries`, e mandá-la fazia o PostgREST recusar o INSERT
    // inteiro com `PGRST204` — que a tela mostrava como o slug cru
    // `install_failed`, sem dizer por quê.
    //
    // 📊 Medido em 17/08/2026: o Founder não conseguia instalar a Cobrança
    // Feita na AutoFleet, e a tela só dizia `install_failed`. Duas telas
    // adiante do problema real.
    //
    // A ausência da coluna já era conhecida — está escrita em
    // `docs/canon/design/2026-06-claude-design/42A7.1-...md` e num comentário
    // de `backend/app/agents/auxiliary_context.py` ("NÃO seleciona
    // display_name (não existe na tabela) — causa do bug 42A7"). A rota
    // ADMIN irmã até se protege com `pickColumns`. A lição existia em três
    // lugares e não chegou nesta linha.
    status: statusValidoNoBanco(status),
    config: { runtime: configRuntime }, permissions: {}, installed_by: byUser,
  }).select('id, status').single();
  if (error || !created) {
    // 🔴 O erro real vai no `details`, e a tela precisa saber lê-lo. Ver o
    // comentário em `AuxiliarDetalheClient`: dizer só `install_failed` é
    // esconder a única informação útil que existe.
    console.error('[AUX install]', tpl.slug, companyId, error?.message ?? '(sem mensagem)');
    return { ok: false as const, error: 'install_failed', details: [error?.message ?? ''] };
  }
  return { ok: true as const, install_id: created.id, status: created.status };
}

/**
 * O status que o BANCO aceita, e não o que o TypeScript gostaria de escrever.
 *
 * 🔴 As duas camadas falam vocabulários diferentes, e isso é uma bomba armada:
 *
 *   CHECK do banco   inactive · active · paused · disabled · archived
 *   TypeScript       active · paused · awaiting_runtime · uninstalled · error
 *
 * 📊 Medido em 17/08/2026 direto no Supabase (`tenant_auxiliaries_status_check`).
 *
 * Três valores do TS — `awaiting_runtime`, `uninstalled`, `error` — **não
 * existem para o banco**. Um Auxiliar cujo runtime não sobe cai em
 * `awaiting_runtime` (linhas 140–142 e 154) e o INSERT é recusado com `23514`,
 * que a tela mostraria como o mesmo `install_failed` opaco — um segundo bug
 * escondido atrás do primeiro.
 *
 * A tradução é para o valor mais próximo que **preserva o significado**:
 * `awaiting_runtime` é um Auxiliar instalado que ainda não pode trabalhar, e
 * `inactive` é exatamente isso do ponto de vista do banco. O detalhe do porquê
 * não se perde — ele vive em `config.runtime.pending` e `install_error`.
 *
 * A alternativa seria acrescentar os valores ao CHECK. Não fiz: mudar
 * constraint de tabela viva por causa de um caminho de UI é desproporcional, e
 * a tradução resolve sem tocar no schema. Fica registrado como escolha.
 */
/**
 * 📊 O CHECK `tenant_auxiliaries_status_check`, lido do banco vivo em
 * 17/08/2026 (projeto `dcajcvlzcjbmyapmklil`):
 *
 *   CHECK (status = ANY (ARRAY['inactive','active','paused','disabled','archived']))
 *
 * Está aqui e não numa migration porque **não existe migration deste CHECK no
 * repositório** — ele é uma das 9 versões aplicadas sem arquivo que a
 * `MIGRATIONS-AUTHORITY` §4 documenta. Um teste que lesse o repo para
 * descobrir o CHECK leria o vazio e passaria por engano.
 */
export const STATUS_ACEITOS_PELO_BANCO = ['inactive', 'active', 'paused', 'disabled', 'archived'] as const;

/** O que conta como "não está mais instalado", nos dois vocabulários. */
export const REMOVIDOS = new Set(['uninstalled', 'archived']);

export function statusValidoNoBanco(status: string): string {
  if ((STATUS_ACEITOS_PELO_BANCO as readonly string[]).includes(status)) return status;
  const TRADUCAO: Record<string, string> = {
    awaiting_runtime: 'inactive',   // instalado, ainda não pode trabalhar
    uninstalled: 'archived',        // saiu de cena, sem apagar histórico
    error: 'disabled',              // não deve rodar até alguém olhar
  };
  return TRADUCAO[status] ?? 'inactive';  // desconhecido nunca nasce ligado
}

export async function changeTenantAuxiliaryStatus(supabase: SupabaseClient, companyId: string, templateId: string, action: TenantAuxAction) {
  const { data: tpl } = await supabase.from('auxiliary_templates').select('slug').eq('id', templateId).maybeSingle();
  if (!tpl?.slug) return { ok: false as const, error: 'template_inexistente' };
  const { data: inst } = await supabase.from('tenant_auxiliaries').select('id, status').eq('company_id', companyId).eq('slug', tpl.slug).maybeSingle();
  if (!inst?.id) return { ok: false as const, error: 'nao_instalado' };
  const next = nextTenantAuxStatus((inst.status ?? 'active') as any, action);
  if (!next) return { ok: false as const, error: 'acao_invalida' };
  // 🔴 Mesma bomba do INSERT, no UPDATE: `uninstall` produz `'uninstalled'`,
  // que o CHECK do banco recusa. O botão "Remover" devolvia `update_failed`
  // sem dizer por quê. `archived` é o valor que o banco tem para isto — e
  // `catalogoDaCorretora` já o trata como removido.
  const gravavel = statusValidoNoBanco(next);
  const { error } = await supabase.from('tenant_auxiliaries').update({ status: gravavel, updated_at: new Date().toISOString() }).eq('id', inst.id);
  if (error) {
    console.error('[AUX status]', tpl.slug, companyId, action, error.message);
    return { ok: false as const, error: 'update_failed', details: [error.message] };
  }
  return { ok: true as const, install_id: inst.id, status: gravavel };
}
