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
  const { data: tpl } = await supabase.from('auxiliary_templates').select('id, slug, name, default_config').eq('id', templateId).maybeSingle();
  if (!tpl?.id) return { ok: false as const, error: 'template_inexistente' };

  // idempotente por (company, slug); reativa se estava desinstalado
  const { data: dup } = await supabase.from('tenant_auxiliaries').select('id, status').eq('company_id', companyId).eq('slug', tpl.slug).maybeSingle();
  if (dup?.id && dup.status !== 'uninstalled') return { ok: true as const, already: true, install_id: dup.id, status: dup.status };

  const runtime = parseRuntimeConfig((tpl as any).default_config, tpl.slug);
  let status = 'active';
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
    const { error } = await supabase.from('tenant_auxiliaries').update({ status, config: { runtime: configRuntime }, updated_at: new Date().toISOString() }).eq('id', dup.id);
    if (error) return { ok: false as const, error: 'reinstall_failed' };
    return { ok: true as const, install_id: dup.id, status, reinstalled: true };
  }

  const { data: created, error } = await supabase.from('tenant_auxiliaries').insert({
    company_id: companyId, template_id: tpl.id, slug: tpl.slug, name: tpl.name, display_name: tpl.name,
    status, config: { runtime: configRuntime }, permissions: {}, installed_by: byUser,
  }).select('id, status').single();
  if (error || !created) return { ok: false as const, error: 'install_failed', details: [error?.message ?? ''] };
  return { ok: true as const, install_id: created.id, status: created.status };
}

export async function changeTenantAuxiliaryStatus(supabase: SupabaseClient, companyId: string, templateId: string, action: TenantAuxAction) {
  const { data: tpl } = await supabase.from('auxiliary_templates').select('slug').eq('id', templateId).maybeSingle();
  if (!tpl?.slug) return { ok: false as const, error: 'template_inexistente' };
  const { data: inst } = await supabase.from('tenant_auxiliaries').select('id, status').eq('company_id', companyId).eq('slug', tpl.slug).maybeSingle();
  if (!inst?.id) return { ok: false as const, error: 'nao_instalado' };
  const next = nextTenantAuxStatus((inst.status ?? 'active') as any, action);
  if (!next) return { ok: false as const, error: 'acao_invalida' };
  const { error } = await supabase.from('tenant_auxiliaries').update({ status: next, updated_at: new Date().toISOString() }).eq('id', inst.id);
  if (error) return { ok: false as const, error: 'update_failed' };
  return { ok: true as const, install_id: inst.id, status: next };
}
