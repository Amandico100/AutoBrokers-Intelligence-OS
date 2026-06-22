// SPEC-013 Fase B — releases globais de blueprint (PURO, testável).
// Uma release é um ARTEFATO SANITIZADO e IMUTÁVEL publicado a partir de um Source
// Agent do Studio (ou seed do blueprint de código). Nunca contém segredo. As
// instâncias das corretoras referenciam blueprint_key + versão. DI para testes .mjs.
import { createHash } from 'node:crypto';
import type { CanonicalBlueprint } from '@/lib/admin/agent-blueprints-canonical';

export type ReleaseStatus = 'draft' | 'published' | 'retired';
export const ARTIFACT_SCHEMA_VERSION = 'blueprint-artifact-v1';

export interface BlueprintArtifact {
  schema_version: string;
  blueprint_key: string;
  role: string;
  audience: string;
  brand_locked_name: string | null;
  default_display_name: string;
  display_name_template: string;
  allow_direct_chat: boolean;
  is_subagent: boolean;
  llm_provider: string;
  llm_model: string;
  system_prompt_template: string;
  variables: unknown;
  immutable_guardrails: string[];
  safe_override_fields: string[];
  default_active: boolean;
  // SPEC-013: tools/MCP entram SOMENTE como capability_keys homologadas (Fase C liga providers).
  declared_capability_keys: string[];
}

export interface SeededRelease {
  blueprint_key: string;
  semantic_version: string;
  status: ReleaseStatus;
  artifact: BlueprintArtifact;
  artifact_hash: string;
  declared_capability_keys: string[];
  risk_level: 'low' | 'medium' | 'high';
  changelog: string;
}

/** Monta o artefato sanitizado a partir do blueprint canônico (sem segredo, sem tools livres). */
export function buildArtifactFromCanonical(bp: CanonicalBlueprint): BlueprintArtifact {
  return {
    schema_version: ARTIFACT_SCHEMA_VERSION,
    blueprint_key: bp.blueprint_key,
    role: bp.role,
    audience: bp.audience,
    brand_locked_name: bp.brand_locked_name,
    default_display_name: bp.default_display_name,
    display_name_template: bp.display_name_template,
    allow_direct_chat: bp.allow_direct_chat,
    is_subagent: bp.is_subagent,
    llm_provider: bp.default_llm_provider,
    llm_model: bp.default_llm_model,
    system_prompt_template: bp.system_prompt_template,
    variables: bp.variables,
    immutable_guardrails: bp.immutable_guardrails,
    safe_override_fields: bp.safe_override_fields,
    default_active: bp.default_active,
    declared_capability_keys: [],
  };
}

// --- Varredura de segredos -----------------------------------------------------
// Nomes de campo que NUNCA podem aparecer numa release.
const SECRET_KEY_NAMES = [
  'token', 'access_token', 'refresh_token', 'api_key', 'apikey', 'secret', 'client_secret',
  'password', 'passwd', 'cookie', 'authorization', 'bearer', 'session_ref', 'sessionref',
  'storage_state', 'storagestate', 'connect_url', 'connecturl', 'private_key', 'x-api-key',
];
// Padrões de valor que denunciam segredo.
const SECRET_VALUE_PATTERNS: Array<{ re: RegExp; why: string }> = [
  { re: /\bsk-[A-Za-z0-9_-]{8,}/, why: 'openai_like_key' },
  { re: /\bBearer\s+[A-Za-z0-9._-]{8,}/i, why: 'bearer_token' },
  { re: /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+/, why: 'jwt' },
  { re: /\bAKIA[0-9A-Z]{16}\b/, why: 'aws_key' },
  { re: /\bxox[baprs]-[A-Za-z0-9-]{8,}/, why: 'slack_token' },
  { re: /https?:\/\/[^\s"']*[?&](access_token|api_key|apikey|token|key|secret)=/i, why: 'url_with_secret' },
];

/** Procura segredos recursivamente. Retorna lista de "caminho: motivo" (vazio = limpo). */
export function scanForSecrets(value: unknown, path = '$'): string[] {
  const found: string[] = [];
  const walk = (v: unknown, p: string) => {
    if (v == null) return;
    if (typeof v === 'string') {
      for (const { re, why } of SECRET_VALUE_PATTERNS) if (re.test(v)) found.push(`${p}: ${why}`);
      return;
    }
    if (Array.isArray(v)) { v.forEach((it, i) => walk(it, `${p}[${i}]`)); return; }
    if (typeof v === 'object') {
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (SECRET_KEY_NAMES.includes(k.toLowerCase())) found.push(`${p}.${k}: forbidden_secret_field`);
        walk(val, `${p}.${k}`);
      }
    }
  };
  walk(value, path);
  return found;
}

export interface PublishCheck { ok: boolean; errors: string[] }

/** Valida se um artefato pode ser publicado: estrutura + sem segredo + tools só por capability_key. */
export function assertReleasePublishable(artifact: BlueprintArtifact): PublishCheck {
  const errors: string[] = [];
  if (!artifact || typeof artifact !== 'object') return { ok: false, errors: ['artifact_invalido'] };
  if (artifact.schema_version !== ARTIFACT_SCHEMA_VERSION) errors.push('schema_version_invalida');
  for (const f of ['blueprint_key', 'role', 'audience', 'system_prompt_template'] as const) {
    if (!artifact[f] || typeof artifact[f] !== 'string') errors.push(`campo_obrigatorio:${f}`);
  }
  if (!Array.isArray(artifact.declared_capability_keys) || artifact.declared_capability_keys.some((k) => typeof k !== 'string' || !k.trim())) {
    errors.push('capability_keys_invalidas');
  }
  // tools/MCP livres NÃO podem entrar na release (só capability_key).
  const asRecord = artifact as unknown as Record<string, unknown>;
  for (const raw of ['tools', 'http_tools', 'mcp', 'mcp_connections', 'tool_refs']) {
    if (raw in asRecord) errors.push(`tool_mcp_livre_proibido:${raw}`);
  }
  const secrets = scanForSecrets(artifact);
  for (const s of secrets) errors.push(`segredo:${s}`);
  return { ok: errors.length === 0, errors };
}

// --- SPEC-013 Fase B P3: artefato derivado do SOURCE AGENT editado no Studio ----
// Estrutura travada (role/audience/marca/variáveis/guardrails) vem do blueprint;
// o conteúdo editável (prompt-base, modelo, capability_keys) vem do Source Agent.
export interface SourceAgentInput {
  agent_system_prompt?: string | null;   // prompt-base EDITADO no Studio
  llm_provider?: string | null;
  llm_model?: string | null;
  declared_capability_keys?: string[];    // capacidades homologadas (Fase C liga providers)
}

export function buildArtifactFromSourceAgent(bp: CanonicalBlueprint, src: SourceAgentInput): BlueprintArtifact {
  const editedPrompt = (typeof src.agent_system_prompt === 'string' && src.agent_system_prompt.trim())
    ? src.agent_system_prompt : bp.system_prompt_template;
  const caps = Array.isArray(src.declared_capability_keys)
    ? src.declared_capability_keys.filter((k) => typeof k === 'string' && k.trim()) : [];
  return {
    schema_version: ARTIFACT_SCHEMA_VERSION,
    blueprint_key: bp.blueprint_key,
    role: bp.role,            // TRAVADO (não muda por edição)
    audience: bp.audience,    // TRAVADO
    brand_locked_name: bp.brand_locked_name,
    default_display_name: bp.default_display_name,
    display_name_template: bp.display_name_template,
    allow_direct_chat: bp.allow_direct_chat,
    is_subagent: bp.is_subagent,
    llm_provider: (src.llm_provider && src.llm_provider.trim()) ? src.llm_provider.trim() : bp.default_llm_provider,
    llm_model: (src.llm_model && src.llm_model.trim()) ? src.llm_model.trim() : bp.default_llm_model,
    system_prompt_template: editedPrompt, // EDITÁVEL no Studio
    variables: bp.variables,              // governado pelo blueprint
    immutable_guardrails: bp.immutable_guardrails, // TRAVADO (não enfraquece)
    safe_override_fields: bp.safe_override_fields,
    default_active: bp.default_active,
    declared_capability_keys: caps,
  };
}

/** Próxima versão semântica (default minor). */
export function bumpSemanticVersion(prev: string, kind: 'major' | 'minor' | 'patch' = 'minor'): string {
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec((prev || '0.0.0').trim());
  let [maj, min, pat] = m ? [Number(m[1]), Number(m[2]), Number(m[3])] : [0, 0, 0];
  if (kind === 'major') { maj += 1; min = 0; pat = 0; }
  else if (kind === 'patch') { pat += 1; }
  else { min += 1; pat = 0; }
  return `${maj}.${min}.${pat}`;
}

/** Hash criptográfico determinístico do artefato (SHA-256) — base de imutabilidade. */
export function hashArtifact(artifact: unknown): string {
  return 'sha256_' + createHash('sha256').update(stableStringify(artifact)).digest('hex');
}
function stableStringify(v: unknown): string {
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(stableStringify).join(',') + ']';
  const keys = Object.keys(v as Record<string, unknown>).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + stableStringify((v as Record<string, unknown>)[k])).join(',') + '}';
}

/** Imutabilidade: só rascunho pode ser editado; publicada/aposentada são imutáveis. */
export function canEditRelease(status: ReleaseStatus): boolean { return status === 'draft'; }
/** Transições de status permitidas (resto é bloqueado). */
export function canTransitionRelease(from: ReleaseStatus, to: ReleaseStatus): boolean {
  if (from === 'draft' && to === 'published') return true;
  if (from === 'published' && to === 'retired') return true;
  return false;
}

/** Seed inicial v1.0.0 a partir dos blueprints canônicos de código (DI). */
export function seedReleasesFromCanonical(blueprints: CanonicalBlueprint[]): SeededRelease[] {
  return blueprints.map((bp) => {
    const artifact = buildArtifactFromCanonical(bp);
    return {
      blueprint_key: bp.blueprint_key,
      semantic_version: '1.0.0',
      status: 'published' as const,
      artifact,
      artifact_hash: hashArtifact(artifact),
      declared_capability_keys: [],
      risk_level: 'low' as const,
      changelog: 'Seed inicial v1.0.0 a partir do blueprint canônico de código (SPEC-013).',
    };
  });
}
