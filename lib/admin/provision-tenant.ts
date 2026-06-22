// Tenant Activation 1 — provisionamento canônico de empresa (Core + Even).
// Server-only. Idempotente: garante 1 Core (AutoBrokers, ativo) + 1 Attendance
// (Even, INATIVA) por company, a partir dos blueprints canônicos. Não instala
// corredores/auxiliares (ficam globais/galeria). Reusa a tabela `agents` (Smith);
// NÃO cria estrutura paralela. Não sobrescreve agente existente do mesmo role.
import type { SupabaseClient } from '@supabase/supabase-js';
import { AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT, resolveEffectiveConfig, type CanonicalBlueprint } from '@/lib/admin/agent-blueprints-canonical';
import { getCompanyKind } from '@/lib/admin/company-kind-store';
import { isPlatformCompany } from '@/lib/admin/company-kind';

export interface ProvisionResult {
  ok: boolean;
  company_id: string;
  core: { id: string | null; action: 'exists' | 'created' | 'error'; reason?: string };
  attendance: { id: string | null; action: 'exists' | 'created' | 'error'; reason?: string };
}

function agentPayloadFromBlueprint(companyId: string, companyName: string, bp: CanonicalBlueprint, slug: string) {
  const eff = resolveEffectiveConfig({ blueprint: bp, company_name: companyName });
  return {
    company_id: companyId,
    name: bp.brand_locked_name ?? bp.default_display_name, // armazenado canônico; apresentação dinâmica vem do prompt/runtime
    slug,
    is_active: bp.default_active,
    agent_enabled: true,
    llm_provider: eff.llm_provider,
    llm_model: eff.llm_model,
    agent_system_prompt: eff.system_prompt,
    is_subagent: bp.is_subagent,
    allow_direct_chat: bp.allow_direct_chat,
    agent_role: bp.role,
    agent_audience: bp.audience,
    blueprint_version: bp.blueprint_key,
    allow_vision: bp.role === 'attendance',
    security_settings: { enabled: false },
  };
}

async function ensureAgentByRole(
  supabase: SupabaseClient, companyId: string, companyName: string, bp: CanonicalBlueprint, slug: string,
): Promise<{ id: string | null; action: 'exists' | 'created' | 'error'; reason?: string }> {
  try {
    const { data: existing, error: lookupErr } = await supabase
      .from('agents').select('id').eq('company_id', companyId).eq('agent_role', bp.role).limit(1).maybeSingle();
    if (lookupErr) return { id: null, action: 'error', reason: lookupErr.code ?? 'lookup_failed' };
    if (existing?.id) return { id: existing.id, action: 'exists' };

    // slug único por sufixo se já houver colisão de slug.
    let useSlug = slug;
    const { data: slugHit } = await supabase.from('agents').select('id').eq('company_id', companyId).eq('slug', slug).maybeSingle();
    if (slugHit?.id) useSlug = `${slug}-${Date.now().toString(36).slice(-4)}`;

    const { data, error } = await supabase.from('agents').insert(agentPayloadFromBlueprint(companyId, companyName, bp, useSlug)).select('id').single();
    if (error || !data) return { id: null, action: 'error', reason: error?.message ?? 'insert_failed' };
    return { id: data.id, action: 'created' };
  } catch (e: any) {
    return { id: null, action: 'error', reason: String(e?.message ?? 'exception').slice(0, 60) };
  }
}

/** Garante Core + Even para a empresa. Idempotente. Não instala corredores/auxiliares. */
export async function provisionTenant(supabase: SupabaseClient, companyId: string): Promise<ProvisionResult> {
  // SPEC-013 — empresas-plataforma (Studio/Knowledge) NÃO recebem provisionamento
  // comercial. Seus Source Agents são autorados no Blueprint Center, não aqui.
  const kind = await getCompanyKind(supabase, companyId);
  if (isPlatformCompany(kind)) {
    return {
      ok: true, company_id: companyId,
      core: { id: null, action: 'exists', reason: 'platform_company_skipped' },
      attendance: { id: null, action: 'exists', reason: 'platform_company_skipped' },
    };
  }
  const { data: company } = await supabase.from('companies').select('id, company_name').eq('id', companyId).maybeSingle();
  const companyName = company?.company_name ?? 'Corretora';
  const core = await ensureAgentByRole(supabase, companyId, companyName, AUTOBROKERS_CORE_BLUEPRINT, 'autobrokers');
  const attendance = await ensureAgentByRole(supabase, companyId, companyName, EVEN_ATTENDANCE_BLUEPRINT, 'even-atendimento');
  return { ok: core.action !== 'error' && attendance.action !== 'error', company_id: companyId, core, attendance };
}
