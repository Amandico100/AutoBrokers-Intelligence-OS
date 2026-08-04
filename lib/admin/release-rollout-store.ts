// SPEC-013 Fase B (hardening) — rollout/rollback ATÔMICO via RPC Postgres. Server-only.
// A materialização (prompt/colunas) é calculada em TS (computeAgentConfigUpdate) e
// aplicada junto com snapshot + pausa do anterior + auditoria numa ÚNICA transação no
// banco (apply_release_rollout). Rollback restaura o snapshot pré-rollout (seguro até no 1º).
// Fail-closed: se a migration de hardening faltar, NÃO executa rollout parcial.
import type { SupabaseClient } from '@supabase/supabase-js';
import { computeAgentConfigUpdate, getCanonicalBlueprint } from '@/lib/admin/agent-blueprints-canonical';
import { artifactToBlueprint, extractSavedTenantInput, captureAgentSnapshot } from '@/lib/admin/release-rollout';
import { scanForSecrets } from '@/lib/admin/blueprint-release';
import { isClientCompany } from '@/lib/admin/company-kind';
import { getCompanyKind } from '@/lib/admin/company-kind-store';
import { problemasDoUpdate, conferirPromptGravado } from '@/lib/admin/provision-tenant';

const AGENT_SNAPSHOT_FIELDS = 'id, name, avatar_url, llm_temperature, agent_system_prompt, context_package, blueprint_version, agent_role';
const RPC_MISSING = ['42883', 'PGRST202']; // função inexistente (pré-migration)

async function companyName(supabase: SupabaseClient, companyId: string): Promise<string> {
  const { data } = await supabase.from('companies').select('company_name').eq('id', companyId).maybeSingle();
  return data?.company_name ?? 'Corretora';
}

export async function applyRollout(supabase: SupabaseClient, releaseId: string, companyId: string, appliedBy: string) {
  const kind = await getCompanyKind(supabase, companyId);
  if (!isClientCompany(kind)) return { ok: false as const, error: 'empresa_nao_cliente' };

  const { data: rel } = await supabase.from('agent_blueprint_releases')
    .select('id, blueprint_key, semantic_version, status, artifact').eq('id', releaseId).maybeSingle();
  if (!rel?.id) return { ok: false as const, error: 'release_inexistente' };
  if (rel.status !== 'published') return { ok: false as const, error: 'release_nao_publicada' };

  const bpMeta = getCanonicalBlueprint(rel.blueprint_key);
  if (!bpMeta) return { ok: false as const, error: 'blueprint_desconhecido' };

  const { data: agent } = await supabase.from('agents').select(AGENT_SNAPSHOT_FIELDS).eq('company_id', companyId).eq('agent_role', bpMeta.role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'instancia_inexistente' };

  // materializa release + personalização local preservada
  const bp = artifactToBlueprint((rel as any).artifact, rel.semantic_version);
  const input = extractSavedTenantInput((agent as any).context_package);
  const name = await companyName(supabase, companyId);
  const upd = computeAgentConfigUpdate(bp, name, (agent as any).context_package, input);

  // P-36 — O PORTÃO, antes de qualquer escrita.
  //
  // Este é o caminho de maior alcance dos três: o blueprint aqui NÃO é o
  // canônico do código, é o que veio dentro do artefato da release
  // (`artifactToBlueprint`). Uma release publicada com `system_prompt_template`
  // vazio materializa a casca de guardrails — ~560 caracteres e nenhuma
  // instrução — e a desce sobre o agente da corretora, que continua ATIVO.
  // Era exatamente esse o estado da AutoFleet em 02/08/2026.
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) return { ok: false as const, error: 'prompt_invalido', details: problemas };

  // snapshot do estado ATUAL (para rollback seguro, inclusive 1º rollout)
  const snapshot = captureAgentSnapshot(agent as any);

  // novo estado do agente a aplicar (só chaves presentes)
  const newAgent: Record<string, unknown> = {
    agent_system_prompt: upd.columns.agent_system_prompt,
    context_package: upd.context_package,
    blueprint_version: rel.blueprint_key,
  };
  if ('name' in upd.columns) newAgent.name = upd.columns.name;
  if ('avatar_url' in upd.columns) newAgent.avatar_url = upd.columns.avatar_url;
  if ('llm_temperature' in upd.columns) newAgent.llm_temperature = upd.columns.llm_temperature;

  // segredo nunca entra em snapshot nem no novo estado
  const secrets = [...scanForSecrets(snapshot, '$.snapshot'), ...scanForSecrets(newAgent, '$.new')];
  if (secrets.length > 0) return { ok: false as const, error: 'segredo_detectado', details: secrets };

  const { data, error } = await supabase.rpc('apply_release_rollout', {
    p_release_id: rel.id, p_company_id: companyId, p_agent_id: agent.id,
    p_new_agent: newAgent, p_snapshot: snapshot, p_blueprint_key: rel.blueprint_key, p_applied_by: appliedBy,
  });
  if (error) {
    if (RPC_MISSING.includes(error.code ?? '')) return { ok: false as const, error: 'rollout_migration_required' };
    return { ok: false as const, error: 'apply_failed', details: [error.message] };
  }

  // Quem escreve é uma RPC no Postgres: o que ela realmente gravou não está em
  // nenhuma variável daqui. Sem esta releitura, "apliquei" seria afirmação
  // sobre uma requisição enviada, não sobre um fato no banco — e o agente
  // mudo seguiria ativo até alguém abrir a conversa de um segurado.
  const conferido = await conferirPromptGravado(supabase, companyId, agent.id, 'apply_release_rollout');
  if (!conferido.ok) return { ok: false as const, error: conferido.reason ?? 'prompt_vazio_apos_escrita', details: [rel.blueprint_key] };

  return { ok: true as const, rollout_id: data, release_id: rel.id, company_id: companyId, blueprint_key: rel.blueprint_key, version: rel.semantic_version };
}

export async function rollbackRollout(supabase: SupabaseClient, companyId: string, blueprintKey: string, byUser: string) {
  const { data, error } = await supabase.rpc('rollback_release_rollout', {
    p_company_id: companyId, p_blueprint_key: blueprintKey, p_by: byUser,
  });
  if (error) {
    if (RPC_MISSING.includes(error.code ?? '')) return { ok: false as const, error: 'rollout_migration_required' };
    return { ok: false as const, error: 'rollback_failed', details: [error.message] };
  }
  return { ok: true as const, rollout_id: data, company_id: companyId, blueprint_key: blueprintKey };
}

export async function listRollouts(supabase: SupabaseClient, companyId?: string) {
  try {
    let q = supabase.from('agent_release_rollouts').select('id, release_id, blueprint_key, company_id, status, previous_release_id, applied_at, applied_by, rollback_at').order('applied_at', { ascending: false }).limit(200);
    if (companyId) q = q.eq('company_id', companyId) as any;
    const { data } = await q;
    return { ok: true as const, rollouts: data ?? [] };
  } catch { return { ok: true as const, rollouts: [] }; }
}
