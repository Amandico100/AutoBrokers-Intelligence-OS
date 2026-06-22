// SPEC-013 Fase B Parte 2 — store do Blueprint Studio (server-only, master-only).
// Inicializa os Source Agents do Studio (motor real do Smith) e PERSISTE as releases
// globais reais. Idempotente. Nunca toca a Resulta; nunca compartilha agente entre tenants.
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT, CANONICAL_BLUEPRINTS, type CanonicalBlueprint,
} from '@/lib/admin/agent-blueprints-canonical';
import { buildArtifactFromCanonical, assertReleasePublishable, hashArtifact } from '@/lib/admin/blueprint-release';

const STUDIO_KIND = 'platform_blueprint_studio';
const SOURCE_SLUG: Record<string, string> = {
  'autobrokers-core-v1': 'autobrokers-global-core',
  'even-attendance-v1': 'even-global-attendance',
};

export async function getStudioCompanyId(supabase: SupabaseClient): Promise<string | null> {
  try {
    const { data } = await supabase.from('companies').select('id').eq('company_kind', STUDIO_KIND).order('created_at', { ascending: true }).limit(1).maybeSingle();
    return data?.id ?? null;
  } catch { return null; }
}

function sourceAgentPayload(studioId: string, bp: CanonicalBlueprint) {
  return {
    company_id: studioId,
    name: bp.brand_locked_name ?? bp.default_display_name,
    slug: SOURCE_SLUG[bp.blueprint_key] ?? bp.blueprint_key,
    is_active: false,            // Source Agent é de AUTORIA, não opera com clientes
    agent_enabled: true,
    llm_provider: bp.default_llm_provider,
    llm_model: bp.default_llm_model,
    agent_system_prompt: bp.system_prompt_template, // template de autoria (com {{variáveis}})
    is_subagent: bp.is_subagent,
    allow_direct_chat: bp.allow_direct_chat,
    agent_role: bp.role,
    agent_audience: bp.audience,
    blueprint_version: bp.blueprint_key,
    security_settings: { enabled: false },
  };
}

async function ensureSourceAgent(supabase: SupabaseClient, studioId: string, bp: CanonicalBlueprint) {
  const { data: existing } = await supabase.from('agents').select('id').eq('company_id', studioId).eq('agent_role', bp.role).limit(1).maybeSingle();
  if (existing?.id) return { id: existing.id, action: 'exists' as const };
  const { data: created, error } = await supabase.from('agents').insert(sourceAgentPayload(studioId, bp)).select('id').single();
  if (error || !created?.id) return { id: null, action: 'error' as const, reason: error?.code ?? 'insert_failed' };
  return { id: created.id, action: 'created' as const };
}

/** Inicialização idempotente do Studio: garante 1 Source Agent por blueprint (Core + Even). */
export async function initializeStudio(supabase: SupabaseClient) {
  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: false as const, error: 'studio_company_missing' };
  const core = await ensureSourceAgent(supabase, studioId, AUTOBROKERS_CORE_BLUEPRINT);
  const even = await ensureSourceAgent(supabase, studioId, EVEN_ATTENDANCE_BLUEPRINT);
  return { ok: core.action !== 'error' && even.action !== 'error', studio_company_id: studioId, core, even };
}

/** Publica/persiste as releases reais v1.0.0 a partir dos Source Agents. Idempotente. */
export async function publishSeedReleases(supabase: SupabaseClient) {
  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: false as const, error: 'studio_company_missing' };

  const results: Array<{ blueprint_key: string; version: string; action: string; reason?: string }> = [];
  for (const bp of CANONICAL_BLUEPRINTS) {
    const version = '1.0.0';
    // já existe essa chave/versão?
    const { data: exists } = await supabase.from('agent_blueprint_releases').select('id').eq('blueprint_key', bp.blueprint_key).eq('semantic_version', version).maybeSingle();
    if (exists?.id) { results.push({ blueprint_key: bp.blueprint_key, version, action: 'exists' }); continue; }

    const { data: srcAgent } = await supabase.from('agents').select('id').eq('company_id', studioId).eq('agent_role', bp.role).limit(1).maybeSingle();
    const artifact = buildArtifactFromCanonical(bp);
    const check = assertReleasePublishable(artifact);
    if (!check.ok) { results.push({ blueprint_key: bp.blueprint_key, version, action: 'blocked', reason: check.errors.join(',') }); continue; }

    const { error } = await supabase.from('agent_blueprint_releases').insert({
      blueprint_key: bp.blueprint_key,
      semantic_version: version,
      status: 'published',
      source_company_id: studioId,
      source_agent_id: srcAgent?.id ?? null,
      artifact,
      artifact_hash: hashArtifact(artifact),
      schema_version: artifact.schema_version,
      changelog: 'Seed inicial v1.0.0 a partir do blueprint canônico (SPEC-013 Fase B).',
      risk_level: 'low',
      declared_capability_keys: [],
      published_at: new Date().toISOString(),
    });
    if (error) { results.push({ blueprint_key: bp.blueprint_key, version, action: 'error', reason: error.code ?? 'insert_failed' }); continue; }
    results.push({ blueprint_key: bp.blueprint_key, version, action: 'published' });
  }
  return { ok: results.every((r) => r.action !== 'error' && r.action !== 'blocked'), studio_company_id: studioId, releases: results };
}

/** Estado do Studio para a tela do Blueprint Center (read-only, sanitizado). */
export async function getStudioStatus(supabase: SupabaseClient) {
  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: true as const, studio_present: false, source_agents: [], releases: [] };

  const { data: agents } = await supabase.from('agents').select('id, name, agent_role, agent_audience, is_active, blueprint_version').eq('company_id', studioId);
  const { data: releases } = await supabase.from('agent_blueprint_releases').select('blueprint_key, semantic_version, status, artifact_hash, risk_level, published_at').order('blueprint_key');
  return {
    ok: true as const,
    studio_present: true,
    studio_company_id: studioId,
    source_agents: (agents ?? []).map((a: any) => ({ id: a.id, name: a.name, role: a.agent_role, audience: a.agent_audience, is_active: a.is_active, blueprint_key: a.blueprint_version })),
    releases: (releases ?? []).map((r: any) => ({ blueprint_key: r.blueprint_key, version: r.semantic_version, status: r.status, hash: r.artifact_hash, risk: r.risk_level, published_at: r.published_at })),
  };
}
