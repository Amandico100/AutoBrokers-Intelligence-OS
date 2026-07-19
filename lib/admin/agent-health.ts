// SPEC-013 FB-2 (close) — saúde + divergências dos agentes de uma corretora (PURO, testável).
// Alimenta o painel de Diagnóstico & manutenção (sem página nova; folded na tela de Agentes).

export interface AgentLite { id: string; name: string | null; agent_role: string | null; is_active: boolean | null }

export type DivergenceKind =
  | 'missing_core' | 'missing_attendance'
  | 'duplicate_core' | 'duplicate_attendance' | 'legacy_test_agent';

export interface Divergence { kind: DivergenceKind; agent_id?: string; label: string; action?: 'archive_agent' }

const TEST_NAME_RE = /\b(teste|test|sandbox|dummy|fixture|tmp|temp)\b/i;

/** Detecta divergências canônicas a partir da lista de agentes da empresa. */
export function buildAgentDivergences(agents: AgentLite[]): Divergence[] {
  const out: Divergence[] = [];
  const core = agents.filter((a) => a.agent_role === 'core');
  const attendance = agents.filter((a) => a.agent_role === 'attendance');

  if (core.length === 0) out.push({ kind: 'missing_core', label: 'AutoBrokers (Core) ausente — provisionar.' });
  if (attendance.length === 0) out.push({ kind: 'missing_attendance', label: 'Agente de Atendimento ausente — provisionar.' });
  if (core.length > 1) out.push({ kind: 'duplicate_core', label: `${core.length} agentes Core — manter 1 canônico.` });
  if (attendance.length > 1) out.push({ kind: 'duplicate_attendance', label: `${attendance.length} agentes de Atendimento — manter 1 canônico.` });

  // SPEC-039 F3: o NOME do atendimento é de cada corretora ("Even" é só o da
  // Resulta). O sistema NUNCA força um nome — só exige que o agente exista.

  // Agentes customizados que parecem dados de teste → oferecer arquivar.
  for (const a of agents) {
    if (a.agent_role === 'core' || a.agent_role === 'attendance') continue;
    if (TEST_NAME_RE.test(a.name || '')) {
      out.push({ kind: 'legacy_test_agent', agent_id: a.id, label: `Agente de teste/legado: "${a.name ?? '—'}" → arquivar.`, action: 'archive_agent' });
    }
  }
  return out;
}

export function isHealthy(divs: Divergence[]): boolean {
  // Saúde canônica = sem ausências/duplicatas (nome/teste são higiene, não bloqueiam).
  return !divs.some((d) => ['missing_core', 'missing_attendance', 'duplicate_core', 'duplicate_attendance'].includes(d.kind));
}

/** Espelha a política de modelo do Core (informativo na UI; runtime real é o backend). */
const ECONOMY = ['gpt-4o-mini', 'gpt-4o-mini-2024-07-18', 'gpt-3.5-turbo', 'gpt-4.1-mini'];
export function effectiveCoreModel(storedModel: string | null | undefined): string {
  const m = (storedModel || '').trim();
  if (!m || ECONOMY.includes(m)) return 'gpt-4o';
  return m;
}
