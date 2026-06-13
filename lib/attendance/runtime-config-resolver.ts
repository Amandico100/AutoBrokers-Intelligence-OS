// Runtime Config Resolver (42B5D).
//
// Resolve a configuração de runtime de um caso a partir do corridor_template /
// corridor_run quando disponíveis, com fallback seguro para o MVP Allianz/Eletricista.
// Objetivo: tirar o runtime da dependência hardcoded de "Eletricista" e permitir
// dezenas de corredores/subcorredores sem reescrever o motor.
//
// NÃO faz I/O (recebe template/run/case já carregados). NÃO envia nada,
// NÃO valida apólice, NÃO consulta InfoCap.
import { RUNTIME_ENGINE } from './corridor-runtime';
import { ELECTRICIAN_SLOT_PRIORITY, SLOT_CATALOG, type SlotDefinition } from './runtime-slot-catalog';

export interface RuntimeConfig {
  engine: string;
  corridor_key: string | null;
  subcorridor_key: string | null;
  slot_priority: readonly string[];
  slot_catalog: Record<string, SlotDefinition>;
  /** De onde veio a ordem dos slots (para auditoria/diagnostics). */
  slot_priority_source: 'template_metadata' | 'template_config' | 'fallback_electrician';
}

function asStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const arr = value.filter((x): x is string => typeof x === 'string' && x.trim().length > 0);
  return arr.length > 0 ? arr : null;
}

/**
 * Mantém apenas slots conhecidos pelo catálogo (ignora chaves desconhecidas) e
 * hoista os slots de segurança (raisesRisk) para o início — risco físico antes
 * de dados administrativos — preservando a ordem relativa do resto.
 */
function sanitizeSlotPriority(keys: string[]): string[] {
  const known = keys.filter((k) => Boolean(SLOT_CATALOG[k]));
  const seen = new Set<string>();
  const deduped = known.filter((k) => (seen.has(k) ? false : (seen.add(k), true)));
  const safety = deduped.filter((k) => SLOT_CATALOG[k]?.safety?.raisesRisk);
  const rest = deduped.filter((k) => !SLOT_CATALOG[k]?.safety?.raisesRisk);
  return [...safety, ...rest];
}

/**
 * Resolve slot_priority.
 *
 * Decisão de design (42B5D): a ordem bruta de `required_slots` do template NÃO é
 * usada como prioridade de runtime, porque ela é ordenada para o contrato de
 * dispatch (problem_description/contato/elétrico primeiro) e não para a conversa
 * segura (risco antes de dados administrativos). Por isso só uma prioridade de
 * runtime declarada explicitamente sobrescreve o fallback:
 *   1. template.metadata.runtime_slot_priority
 *   2. template.config.slot_priority  (ou template.metadata.config.slot_priority)
 *   3. fallback ELECTRICIAN_SLOT_PRIORITY  (comportamento atual preservado)
 * Em todos os casos aplicamos sanitização + hoist de segurança.
 */
function resolveSlotPriority(corridorTemplate: any): {
  priority: readonly string[];
  source: RuntimeConfig['slot_priority_source'];
} {
  const metadata = corridorTemplate?.metadata;
  const fromMetadata = asStringArray(metadata?.runtime_slot_priority);
  if (fromMetadata) {
    const sanitized = sanitizeSlotPriority(fromMetadata);
    if (sanitized.length > 0) return { priority: sanitized, source: 'template_metadata' };
  }

  const fromConfig =
    asStringArray(corridorTemplate?.config?.slot_priority) ?? asStringArray(metadata?.config?.slot_priority);
  if (fromConfig) {
    const sanitized = sanitizeSlotPriority(fromConfig);
    if (sanitized.length > 0) return { priority: sanitized, source: 'template_config' };
  }

  return { priority: ELECTRICIAN_SLOT_PRIORITY, source: 'fallback_electrician' };
}

/**
 * Resolve a configuração de runtime. Nunca lança: sem template, usa fallback seguro.
 */
export function resolveRuntimeConfig(input: {
  corridorTemplate?: any;
  corridorRun?: any;
  caseRow?: any;
}): RuntimeConfig {
  const { corridorTemplate, caseRow } = input;
  const { priority, source } = resolveSlotPriority(corridorTemplate);

  const corridorKey =
    (caseRow && typeof caseRow.selected_corridor_key === 'string' && caseRow.selected_corridor_key) ||
    (corridorTemplate && typeof corridorTemplate.corridor_key === 'string' && corridorTemplate.corridor_key) ||
    null;
  const subcorridorKey =
    (caseRow && typeof caseRow.selected_subcorridor_key === 'string' && caseRow.selected_subcorridor_key) ||
    (corridorTemplate && typeof corridorTemplate.subcorridor_key === 'string' && corridorTemplate.subcorridor_key) ||
    null;

  return {
    engine: RUNTIME_ENGINE,
    corridor_key: corridorKey,
    subcorridor_key: subcorridorKey,
    slot_priority: priority,
    slot_catalog: SLOT_CATALOG,
    slot_priority_source: source,
  };
}
