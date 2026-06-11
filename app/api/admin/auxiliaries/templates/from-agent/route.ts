import { NextRequest, NextResponse } from 'next/server';

import {
  getAdminSupabase,
  hasAdminCookie,
  getTableColumns,
  pickColumns,
  TEMPLATE_FALLBACK_COLS,
  TENANT_FALLBACK_COLS,
  SLUG_RE,
} from '@/lib/admin/factory';
import { fetchAgentViaBackend, extractBlueprintFromAgent } from '@/lib/admin/agent-blueprints';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * POST /api/admin/auxiliaries/templates/from-agent
 * Publica um Agent/Subagent existente como template de Auxiliar (blueprint sanitizado, sem segredos).
 * visibility: 'global' | 'exclusive'. installOriginal: vincula o agent ORIGINAL (não cria cópia).
 */
export async function POST(req: NextRequest) {
  if (!(await hasAdminCookie())) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const s = (k: string) => (typeof body[k] === 'string' ? (body[k] as string).trim() : '');
  const companyId = s('companyId');
  const agentId = s('agentId');
  const name = s('name');
  const slug = s('slug').toLowerCase();
  const visibility = s('visibility') === 'exclusive' ? 'exclusive' : 'global';
  const status = s('status') || 'active';
  const installOriginal = body.installOriginal === true;

  if (!companyId || !agentId) return NextResponse.json({ error: 'Empresa e Agent são obrigatórios.' }, { status: 400 });
  if (!name) return NextResponse.json({ error: 'Nome é obrigatório.' }, { status: 400 });
  if (!slug || !SLUG_RE.test(slug)) {
    return NextResponse.json({ error: 'Slug inválido (minúsculas e hífens).' }, { status: 400 });
  }

  const adminApiKey = process.env.ADMIN_API_KEY || process.env.BACKEND_INTERNAL_API_KEY || '';
  if (!adminApiKey) return NextResponse.json({ error: 'Chave admin do backend não configurada.' }, { status: 500 });
  let backendUrl: string;
  try {
    backendUrl = getBackendUrl(req);
  } catch (e) {
    if (e instanceof BackendUrlError) return NextResponse.json({ error: 'Backend não configurado.' }, { status: 500 });
    throw e;
  }

  const { agent, error: agentErr } = await fetchAgentViaBackend(backendUrl, adminApiKey, agentId);
  if (!agent) return NextResponse.json({ error: agentErr || 'Agent não encontrado.' }, { status: 404 });
  if (String(agent.company_id) !== companyId) {
    return NextResponse.json({ error: 'O Agent não pertence à corretora selecionada.' }, { status: 400 });
  }

  const blueprint = extractBlueprintFromAgent(agent);
  const defaultConfig = {
    runtime: { kind: 'smith_agent_blueprint', agent_blueprint: blueprint },
    visibility: visibility === 'exclusive' ? { type: 'private', company_id: companyId } : { type: 'global' },
  };

  const supabase = getAdminSupabase();

  const { data: existing } = await supabase.from('auxiliary_templates').select('id').eq('slug', slug).limit(1);
  if (existing && existing.length > 0) {
    return NextResponse.json({ error: 'Já existe um template com este slug.' }, { status: 409 });
  }

  const tplCandidate: Record<string, unknown> = {
    slug,
    name,
    description: s('description') || null,
    short_description: s('short_description') || null,
    category: s('category') || null,
    status,
    is_active: true,
    default_config: defaultConfig,
    version: 1,
  };
  const tplCols = await getTableColumns(supabase, 'auxiliary_templates', TEMPLATE_FALLBACK_COLS);
  const tplRecord = pickColumns(tplCandidate, tplCols);

  const { data: template, error: tplErr } = await supabase
    .from('auxiliary_templates')
    .insert([tplRecord])
    .select()
    .single();
  if (tplErr) {
    console.error('[ADMIN AUX from-agent] template', tplErr.message);
    return NextResponse.json({ error: `Erro ao criar template (${tplErr.code || 'db'}).` }, { status: 500 });
  }

  let installed: unknown = null;
  let already = false;
  if (installOriginal) {
    const { data: dup } = await supabase
      .from('tenant_auxiliaries')
      .select('id, status')
      .eq('company_id', companyId)
      .eq('slug', slug)
      .limit(1);
    if (dup && dup.length > 0) {
      installed = dup[0];
      already = true;
    } else {
      const tCols = await getTableColumns(supabase, 'tenant_auxiliaries', TENANT_FALLBACK_COLS);
      const tCandidate: Record<string, unknown> = {
        company_id: companyId,
        template_id: template.id,
        slug,
        name,
        display_name: name,
        status: 'active',
        // Vincula o AGENT ORIGINAL (não cria cópia).
        config: { runtime: { kind: 'smith_agent', agent_id: agentId, created_from_template: true, linked_original: true } },
        permissions: {},
      };
      const tRecord = pickColumns(tCandidate, tCols);
      const { data: inst, error: instErr } = await supabase.from('tenant_auxiliaries').insert([tRecord]).select().single();
      if (instErr) {
        console.error('[ADMIN AUX from-agent] install', instErr.message);
      } else {
        installed = inst;
      }
    }
  }

  return NextResponse.json({ template, installed, already, agent_linked: installOriginal ? agentId : null }, { status: 201 });
}
