// SPEC-013 Fase B P4 — store de rollout de release → instância tenant. Server-only.
// Master-only (chamado por rota protegida). Preserva tenant_agent_config; nunca cruza tenant.
import type { SupabaseClient } from '@supabase/supabase-js';
import { computeAgentConfigUpdate, getCanonicalBlueprint } from '@/lib/admin/agent-blueprints-canonical';
import { artifactToBlueprint, extractSavedTenantInput } from '@/lib/admin/release-rollout';
import { isClientCompany } from '@/lib/admin/company-kind';
import { getCompanyKind } from '@/lib/admin/company-kind-store';

async function companyName(supabase: SupabaseClient, companyId: string): Promise<string> {
  const { data } = await supabase.from('companies').select('company_name').eq('id', companyId).maybeSingle();
  return data?.company_name ?? 'Corretora';
}

/** Aplica uma release publicada a uma corretora cliente (canário ou ampla, sempre manual). */
export async function applyRollout(supabase: SupabaseClient, releaseId: string, companyId: string, appliedBy: string) {
  // só corretora CLIENTE recebe rollout (Studio/Knowledge nunca)
  const kind = await getCompanyKind(supabase, companyId);
  if (!isClientCompany(kind)) return { ok: false as const, error: 'empresa_nao_cliente' };

  const { data: rel } = await supabase.from('agent_blueprint_releases')
    .select('id, blueprint_key, semantic_version, status, artifact').eq('id', releaseId).maybeSingle();
  if (!rel?.id) return { ok: false as const, error: 'release_inexistente' };
  if (rel.status !== 'published') return { ok: false as const, error: 'release_nao_publicada' };

  const bpMeta = getCanonicalBlueprint(rel.blueprint_key);
  if (!bpMeta) return { ok: false as const, error: 'blueprint_desconhecido' };

  // instância tenant correspondente (por role do blueprint)
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', bpMeta.role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'instancia_inexistente' };

  // materializa release + personalização local preservada
  const bp = artifactToBlueprint((rel as any).artifact, rel.semantic_version);
  const input = extractSavedTenantInput(agent.context_package);
  const name = await companyName(supabase, companyId);
  const upd = computeAgentConfigUpdate(bp, name, agent.context_package, input);

  const { error: upErr } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, blueprint_version: rel.blueprint_key, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (upErr) return { ok: false as const, error: 'apply_failed' };

  // registra rollout (previous = último ativo desta empresa/blueprint)
  let previousReleaseId: string | null = null;
  try {
    const { data: prev } = await supabase.from('agent_release_rollouts')
      .select('release_id').eq('company_id', companyId).eq('blueprint_key', rel.blueprint_key).eq('status', 'active').order('applied_at', { ascending: false }).limit(1).maybeSingle();
    previousReleaseId = prev?.release_id ?? null;
    if (previousReleaseId) await supabase.from('agent_release_rollouts').update({ status: 'paused' }).eq('company_id', companyId).eq('blueprint_key', rel.blueprint_key).eq('status', 'active');
  } catch { /* tabela pode não existir ainda pré-migration */ }

  try {
    const { error: insErr } = await supabase.from('agent_release_rollouts').insert({
      release_id: rel.id, blueprint_key: rel.blueprint_key, company_id: companyId, tenant_agent_id: agent.id,
      status: 'active', previous_release_id: previousReleaseId, applied_by: appliedBy, applied_at: new Date().toISOString(),
    });
    if (insErr) return { ok: true as const, applied: true, audit: false, reason: 'rollout_table_missing' };
  } catch { return { ok: true as const, applied: true, audit: false, reason: 'rollout_table_missing' }; }

  return { ok: true as const, applied: true, audit: true, release_id: rel.id, company_id: companyId, blueprint_key: rel.blueprint_key, version: rel.semantic_version };
}

/** Rollback: reaplica a release anterior registrada, preservando personalização. */
export async function rollbackRollout(supabase: SupabaseClient, companyId: string, blueprintKey: string, byUser: string) {
  const { data: current } = await supabase.from('agent_release_rollouts')
    .select('id, release_id, previous_release_id').eq('company_id', companyId).eq('blueprint_key', blueprintKey).eq('status', 'active').order('applied_at', { ascending: false }).limit(1).maybeSingle();
  if (!current?.id) return { ok: false as const, error: 'rollout_ativo_inexistente' };
  if (!current.previous_release_id) return { ok: false as const, error: 'sem_release_anterior' };

  const res = await applyRollout(supabase, current.previous_release_id, companyId, byUser);
  if (!res.ok) return res;
  try { await supabase.from('agent_release_rollouts').update({ status: 'rolled_back', rollback_at: new Date().toISOString(), rollback_by: byUser }).eq('id', current.id); } catch { /* best-effort */ }
  return { ok: true as const, rolled_back_to: current.previous_release_id, company_id: companyId, blueprint_key: blueprintKey };
}

export async function listRollouts(supabase: SupabaseClient, companyId?: string) {
  try {
    let q = supabase.from('agent_release_rollouts').select('id, release_id, blueprint_key, company_id, status, previous_release_id, applied_at, applied_by, rollback_at').order('applied_at', { ascending: false }).limit(200);
    if (companyId) q = q.eq('company_id', companyId) as any;
    const { data } = await q;
    return { ok: true as const, rollouts: data ?? [] };
  } catch { return { ok: true as const, rollouts: [] }; }
}
