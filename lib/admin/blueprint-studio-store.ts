// SPEC-013 Fase B Parte 2 — store do Blueprint Studio (server-only, master-only).
// Inicializa os Source Agents do Studio (motor real do Smith) e PERSISTE as releases
// globais reais. Idempotente. Nunca toca a Resulta; nunca compartilha agente entre tenants.
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT, CANONICAL_BLUEPRINTS, getCanonicalBlueprint, type CanonicalBlueprint,
} from '@/lib/admin/agent-blueprints-canonical';
import {
  buildArtifactFromCanonical, buildArtifactFromSourceAgent, assertReleasePublishable, hashArtifact, bumpSemanticVersion,
} from '@/lib/admin/blueprint-release';

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

// SPEC-013 P3 — localiza o Source Agent por blueprint_key (slug/blueprint_version → role).
async function findSourceAgent(supabase: SupabaseClient, studioId: string, bp: CanonicalBlueprint) {
  const fields = 'id, agent_system_prompt, llm_provider, llm_model';
  let { data } = await supabase.from('agents').select(fields).eq('company_id', studioId).eq('blueprint_version', bp.blueprint_key).limit(1).maybeSingle();
  if (!data?.id) { const r = await supabase.from('agents').select(fields).eq('company_id', studioId).eq('slug', SOURCE_SLUG[bp.blueprint_key] ?? bp.blueprint_key).limit(1).maybeSingle(); data = r.data; }
  if (!data?.id) { const r = await supabase.from('agents').select(fields).eq('company_id', studioId).eq('agent_role', bp.role).limit(1).maybeSingle(); data = r.data; }
  return data ?? null;
}

async function latestVersion(supabase: SupabaseClient, blueprintKey: string): Promise<string | null> {
  const { data } = await supabase.from('agent_blueprint_releases').select('semantic_version').eq('blueprint_key', blueprintKey).order('created_at', { ascending: false }).limit(50);
  if (!Array.isArray(data) || data.length === 0) return null;
  // ordena semanticamente
  const sorted = data.map((r: any) => String(r.semantic_version)).sort((a, b) => {
    const pa = a.split('.').map(Number); const pb = b.split('.').map(Number);
    return (pb[0] - pa[0]) || (pb[1] - pa[1]) || (pb[2] - pa[2]);
  });
  return sorted[0] ?? null;
}

// SPEC-013 B1 — cria um Source Agent de Auxiliar dentro do Studio (motor Smith).
// É de AUTORIA (inativo, sem chat/canal). Depois é publicado como Auxiliar Global.
const SLUG_RE_AUX = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export async function createSourceAuxiliary(supabase: SupabaseClient, input: { name: string; slug: string; description?: string }) {
  const name = (input.name || '').trim();
  const slug = (input.slug || '').trim().toLowerCase();
  if (!name) return { ok: false as const, error: 'nome_obrigatorio' };
  if (!slug || !SLUG_RE_AUX.test(slug)) return { ok: false as const, error: 'slug_invalido' };

  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: false as const, error: 'studio_company_missing' };

  // slug único dentro do Studio
  const { data: dup } = await supabase.from('agents').select('id').eq('company_id', studioId).eq('slug', slug).maybeSingle();
  if (dup?.id) return { ok: false as const, error: 'slug_em_uso' };

  const { data: created, error } = await supabase.from('agents').insert({
    company_id: studioId,
    name,
    slug,
    is_active: false,            // autoria, não operacional
    agent_enabled: true,
    agent_role: 'subagent',
    is_subagent: true,
    allow_direct_chat: false,
    studio_source_kind: 'global_auxiliary',
    blueprint_version: `aux-${slug}`,
    agent_system_prompt: input.description?.trim() || `Voce e o auxiliar ${name}.`,
    security_settings: { enabled: false },
  }).select('id, name, slug, studio_source_kind').single();
  if (error || !created?.id) return { ok: false as const, error: 'insert_failed', details: [error?.message ?? ''] };
  return { ok: true as const, source_agent: created };
}

export async function listStudioAuxiliarySources(supabase: SupabaseClient) {
  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: true as const, sources: [] };
  const { data } = await supabase.from('agents').select('id, name, slug, studio_source_kind').eq('company_id', studioId).eq('studio_source_kind', 'global_auxiliary').order('name');
  return { ok: true as const, sources: data ?? [], studio_company_id: studioId };
}

/** P3 — cria uma DRAFT de nova versão a partir do Source Agent EDITADO no Studio. */
export async function createReleaseDraftFromSourceAgent(supabase: SupabaseClient, blueprintKey: string, bumpKind: 'major' | 'minor' | 'patch' = 'minor') {
  const bp = getCanonicalBlueprint(blueprintKey);
  if (!bp) return { ok: false as const, error: 'blueprint_desconhecido' };
  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: false as const, error: 'studio_company_missing' };
  const src = await findSourceAgent(supabase, studioId, bp);
  if (!src?.id) return { ok: false as const, error: 'source_agent_missing' }; // publicação exige Source Agent

  const prev = await latestVersion(supabase, blueprintKey);
  let next = bumpSemanticVersion(prev ?? '1.0.0', bumpKind);
  // garante unicidade (se já existir, sobe de novo)
  for (let i = 0; i < 20; i++) {
    const { data: dup } = await supabase.from('agent_blueprint_releases').select('id').eq('blueprint_key', blueprintKey).eq('semantic_version', next).maybeSingle();
    if (!dup?.id) break;
    next = bumpSemanticVersion(next, 'patch');
  }

  const artifact = buildArtifactFromSourceAgent(bp, {
    agent_system_prompt: (src as any).agent_system_prompt,
    llm_provider: (src as any).llm_provider,
    llm_model: (src as any).llm_model,
    declared_capability_keys: [],
  });
  const check = assertReleasePublishable(artifact);
  if (!check.ok) return { ok: false as const, error: 'release_bloqueada', details: check.errors };

  const { data: created, error } = await supabase.from('agent_blueprint_releases').insert({
    blueprint_key: blueprintKey, semantic_version: next, status: 'draft',
    source_company_id: studioId, source_agent_id: src.id,
    artifact, artifact_hash: hashArtifact(artifact), schema_version: artifact.schema_version,
    changelog: `Draft v${next} derivado do Source Agent do Studio.`, risk_level: 'low', declared_capability_keys: [],
  }).select('id, semantic_version, status').single();
  if (error || !created) return { ok: false as const, error: 'draft_insert_failed' };
  return { ok: true as const, draft: created };
}

/** P3 — publica uma DRAFT (draft → published). Imutável depois. */
export async function publishReleaseDraft(supabase: SupabaseClient, releaseId: string) {
  const { data: rel } = await supabase.from('agent_blueprint_releases').select('id, status, artifact').eq('id', releaseId).maybeSingle();
  if (!rel?.id) return { ok: false as const, error: 'release_inexistente' };
  if (rel.status !== 'draft') return { ok: false as const, error: 'somente_draft_publica' };
  const check = assertReleasePublishable((rel as any).artifact);
  if (!check.ok) return { ok: false as const, error: 'release_bloqueada', details: check.errors };
  const { error } = await supabase.from('agent_blueprint_releases').update({ status: 'published', published_at: new Date().toISOString() }).eq('id', releaseId).eq('status', 'draft');
  if (error) return { ok: false as const, error: 'publish_failed' };
  return { ok: true as const, release_id: releaseId, status: 'published' };
}

/** Estado do Studio para a tela do Blueprint Center (read-only, sanitizado). */
export async function getStudioStatus(supabase: SupabaseClient) {
  const studioId = await getStudioCompanyId(supabase);
  if (!studioId) return { ok: true as const, studio_present: false, source_agents: [], releases: [] };

  const { data: agents } = await supabase.from('agents').select('id, name, agent_role, agent_audience, is_active, blueprint_version').eq('company_id', studioId);
  const { data: releases } = await supabase.from('agent_blueprint_releases').select('id, blueprint_key, semantic_version, status, artifact_hash, risk_level, published_at').order('blueprint_key');
  const rels = (releases ?? []).map((r: any) => ({ id: r.id, blueprint_key: r.blueprint_key, version: r.semantic_version, status: r.status, hash: r.artifact_hash, risk: r.risk_level, published_at: r.published_at }));
  // Readiness específico (não confiar em releases.length): Core e Even precisam ter release published.
  const publishedKeys = new Set(rels.filter((r) => r.status === 'published').map((r) => r.blueprint_key));
  return {
    ok: true as const,
    studio_present: true,
    studio_company_id: studioId,
    source_agents: (agents ?? []).map((a: any) => ({ id: a.id, name: a.name, role: a.agent_role, audience: a.agent_audience, is_active: a.is_active, blueprint_key: a.blueprint_version })),
    releases: rels,
    core_published: publishedKeys.has(AUTOBROKERS_CORE_BLUEPRINT.blueprint_key),
    even_published: publishedKeys.has(EVEN_ATTENDANCE_BLUEPRINT.blueprint_key),
    has_draft: rels.some((r) => r.status === 'draft'),
  };
}
