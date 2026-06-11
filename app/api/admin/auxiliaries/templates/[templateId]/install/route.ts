import { NextRequest, NextResponse } from 'next/server';

import {
  getAdminSupabase,
  hasAdminCookie,
  getTableColumns,
  pickColumns,
  parseJsonField,
  TENANT_FALLBACK_COLS,
} from '@/lib/admin/factory';
import { parseRuntimeConfig, type RuntimeConfig } from '@/lib/admin/auxiliary-runtime';
import { buildAgentCreatePayload, createAgentViaBackend } from '@/lib/admin/agent-blueprints';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

type TemplateRow = { id: string; slug: string; name: string; default_config?: unknown };

/** Resolve o vínculo de runtime (cria agent Smith se blueprint). Best-effort, nunca lança. */
async function resolveRuntimeBinding(
  runtime: RuntimeConfig,
  template: TemplateRow,
  companyId: string,
  req: NextRequest,
): Promise<{ configRuntime: Record<string, unknown>; note?: string }> {
  if (runtime.kind === 'specific_executor') {
    return { configRuntime: { kind: 'specific_executor', executor: runtime.executor || template.slug } };
  }
  if (runtime.kind === 'workflow') {
    return { configRuntime: { kind: 'workflow', workflow: runtime.workflow ?? null } };
  }
  if (runtime.kind !== 'smith_agent_blueprint') {
    return { configRuntime: { kind: 'none' } };
  }

  const adminApiKey = process.env.ADMIN_API_KEY || process.env.BACKEND_INTERNAL_API_KEY || '';
  if (!adminApiKey) {
    return {
      configRuntime: { kind: 'smith_agent_blueprint', created_from_template: false, agent_error: 'admin_key_missing' },
      note: 'Agent não criado: chave admin ausente.',
    };
  }
  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (e) {
    if (e instanceof BackendUrlError) {
      return {
        configRuntime: { kind: 'smith_agent_blueprint', created_from_template: false, agent_error: 'backend_not_configured' },
        note: 'Agent não criado: backend não configurado.',
      };
    }
    throw e;
  }

  const blueprint = (runtime.agent_blueprint || { name: template.name, slug: template.slug }) as Record<string, unknown>;
  const payload = buildAgentCreatePayload(companyId, blueprint);
  const r = await createAgentViaBackend(backendUrl, adminApiKey, payload);
  if (r.agentId) {
    return {
      configRuntime: {
        kind: 'smith_agent',
        agent_id: r.agentId,
        created_from_template: true,
        template_runtime_kind: 'smith_agent_blueprint',
      },
    };
  }
  return {
    configRuntime: { kind: 'smith_agent_blueprint', created_from_template: false, agent_error: r.error || 'falha' },
    note: `Agent não criado: ${r.error || 'falha'}.`,
  };
}

/**
 * POST /api/admin/auxiliaries/templates/[templateId]/install
 * Cria tenant_auxiliaries (idempotente por company+slug) e, se o template tiver runtime
 * smith_agent_blueprint, cria/vincula um Agent Smith da corretora (canônico, SPEC-002).
 */
export async function POST(req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { templateId } = await params;

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const companyId = typeof body.companyId === 'string' ? body.companyId.trim() : '';
  if (!companyId) return NextResponse.json({ error: 'Selecione uma corretora.' }, { status: 400 });

  const cfg = parseJsonField(body.config, 'config');
  if (cfg.error) return NextResponse.json({ error: cfg.error }, { status: 400 });
  const perms = parseJsonField(body.permissions, 'permissions');
  if (perms.error) return NextResponse.json({ error: perms.error }, { status: 400 });

  const supabase = getAdminSupabase();

  const { data: template } = await supabase
    .from('auxiliary_templates')
    .select('*')
    .eq('id', templateId)
    .maybeSingle();
  if (!template) return NextResponse.json({ error: 'Template não encontrado' }, { status: 404 });

  const { data: company } = await supabase
    .from('companies')
    .select('id, company_name')
    .eq('id', companyId)
    .maybeSingle();
  if (!company) return NextResponse.json({ error: 'Corretora não encontrada' }, { status: 404 });

  const tRow: TemplateRow = {
    id: template.id,
    slug: template.slug,
    name: template.name,
    default_config: template.default_config,
  };
  const runtime = parseRuntimeConfig(template.default_config, template.slug);

  const cols = await getTableColumns(supabase, 'tenant_auxiliaries', TENANT_FALLBACK_COLS);
  const hasConfigCol = cols.has('config');

  // Dedupe por (company_id, slug).
  const { data: dup } = await supabase
    .from('tenant_auxiliaries')
    .select('id, status, config')
    .eq('company_id', companyId)
    .eq('slug', template.slug)
    .limit(1);

  if (dup && dup.length > 0) {
    const row = dup[0];
    const existingRuntime =
      row.config && typeof row.config === 'object'
        ? ((row.config as Record<string, unknown>).runtime as Record<string, unknown> | undefined)
        : undefined;
    // Vincula agent só se faltar e o template tiver blueprint.
    if (hasConfigCol && runtime.kind === 'smith_agent_blueprint' && !existingRuntime?.agent_id) {
      const { configRuntime, note } = await resolveRuntimeBinding(runtime, tRow, companyId, req);
      const nextConfig = { ...((row.config as Record<string, unknown>) || {}), runtime: configRuntime };
      await supabase.from('tenant_auxiliaries').update({ config: nextConfig }).eq('id', row.id);
      return NextResponse.json({ installed: { ...row, config: nextConfig }, already: true, bound: true, note });
    }
    return NextResponse.json({ installed: row, already: true });
  }

  const { configRuntime, note } = hasConfigCol
    ? await resolveRuntimeBinding(runtime, tRow, companyId, req)
    : { configRuntime: undefined as Record<string, unknown> | undefined, note: 'Coluna config ausente: runtime não persistido.' };

  const displayName = (typeof body.name === 'string' && body.name.trim()) || template.name;
  const baseConfig = (cfg.value as Record<string, unknown>) || {};
  const candidate: Record<string, unknown> = {
    company_id: companyId,
    template_id: templateId,
    slug: template.slug,
    name: displayName,
    display_name: displayName,
    status: typeof body.status === 'string' && body.status.trim() ? body.status.trim() : 'active',
    config: hasConfigCol ? { ...baseConfig, runtime: configRuntime } : baseConfig,
    permissions: perms.value ?? {},
  };

  const record = pickColumns(candidate, cols);
  const { data, error } = await supabase.from('tenant_auxiliaries').insert([record]).select().single();
  if (error) {
    console.error('[ADMIN AUX install]', error.message);
    return NextResponse.json({ error: `Erro ao instalar (${error.code || 'db'}).` }, { status: 500 });
  }
  return NextResponse.json({ installed: data, already: false, runtime: configRuntime, note }, { status: 201 });
}
