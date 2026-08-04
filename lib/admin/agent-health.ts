// SPEC-013 FB-2 (close) — saúde + divergências dos agentes de uma corretora (PURO, testável).
// Alimenta o painel de Diagnóstico & manutenção (sem página nova; folded na tela de Agentes).

export interface AgentLite {
  id: string; name: string | null; agent_role: string | null; is_active: boolean | null;
  /** P-37: sem esta coluna, o diagnóstico é cego ao agente MUDO. */
  agent_system_prompt?: string | null;
}

export type DivergenceKind =
  | 'missing_core' | 'missing_attendance'
  | 'duplicate_core' | 'duplicate_attendance' | 'legacy_test_agent'
  | 'mute_core' | 'mute_attendance';

export interface Divergence { kind: DivergenceKind; agent_id?: string; label: string; action?: 'archive_agent' }

const TEST_NAME_RE = /\b(teste|test|sandbox|dummy|fixture|tmp|temp)\b/i;

// ---------------------------------------------------------------------------
// P-37 — O AGENTE MUDO
// ---------------------------------------------------------------------------
//
// Este diagnóstico detectava agente AUSENTE e agente DUPLICADO. Não detectava o
// estado que a AutoFleet realmente teve, e por isso ninguém percebeu:
//
// 📊 02/08/2026, banco de produção (auditoria do Bloco 0,
// `docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md`, Parte C.6):
//
//     corretora    papel   blueprint              prompt
//     Resulta      core    autobrokers-core-v1    650 chars
//     AutoFleet    core    autobrokers-core-v1        0     <- ATIVO
//     Amandus      core    core-v1                7.914 chars
//
// O agente ESTAVA lá, era ÚNICO, e estava ATIVO. Passava em todas as
// checagens — e não tinha uma linha de instrução. Presente, único e mudo: a
// tela dizia "saudável".
//
// E há um segundo jeito de ser mudo, que "prompt não vazio" não pega.
// `composeSystemPromptWithGuardrails('')` devolve ~560 caracteres de cabeçalho
// e regras imutáveis, e NENHUMA instrução sobre o que o agente é ou faz. Um
// agente com essa casca tem prompt longo e continua mudo na prática. Por isso a
// medida aqui é a PERSONALIZAÇÃO — o que está acima do bloco de regras — e não
// o comprimento do texto inteiro.

const CABECALHO_PERSONALIZACAO = '=== PERSONALIZACAO DA CORRETORA';
const CABECALHO_GUARDRAILS = '=== REGRAS IMUTAVEIS DO AUTOBROKERS';

/** O que a corretora efetivamente instruiu — sem o bloco de regras imutáveis. */
export function personalizacaoDoPrompt(prompt: string | null | undefined): string {
  const texto = String(prompt ?? '');
  const fimDaPersonalizacao = texto.indexOf(CABECALHO_GUARDRAILS);
  const acima = fimDaPersonalizacao >= 0 ? texto.slice(0, fimDaPersonalizacao) : texto;
  const inicio = acima.indexOf(CABECALHO_PERSONALIZACAO);
  if (inicio < 0) return acima.trim(); // prompt escrito à mão, sem a moldura
  const quebra = acima.indexOf('\n', inicio);
  return quebra < 0 ? '' : acima.slice(quebra + 1).trim();
}

export type EstadoDaVoz = 'ok' | 'vazio' | 'so_guardrails';

/**
 * `vazio` = a coluna está em branco. `so_guardrails` = há texto, e nele não há
 * nenhuma instrução da corretora: só a moldura e as regras. Os dois são MUDO.
 */
export function estadoDaVoz(prompt: string | null | undefined): EstadoDaVoz {
  if (!String(prompt ?? '').trim()) return 'vazio';
  return personalizacaoDoPrompt(prompt) ? 'ok' : 'so_guardrails';
}

export function isMute(a: AgentLite): boolean {
  // Ausência da coluna na consulta NÃO é prova de mudez. Quem não pediu
  // `agent_system_prompt` no select recebe silêncio, não um alarme falso.
  if (a.agent_system_prompt === undefined) return false;
  return estadoDaVoz(a.agent_system_prompt) !== 'ok';
}

/** Detecta divergências canônicas a partir da lista de agentes da empresa. */
export function buildAgentDivergences(agents: AgentLite[]): Divergence[] {
  const out: Divergence[] = [];
  const core = agents.filter((a) => a.agent_role === 'core');
  const attendance = agents.filter((a) => a.agent_role === 'attendance');

  if (core.length === 0) out.push({ kind: 'missing_core', label: 'AutoBrokers (Core) ausente — provisionar.' });
  if (attendance.length === 0) out.push({ kind: 'missing_attendance', label: 'Agente de Atendimento ausente — provisionar.' });
  if (core.length > 1) out.push({ kind: 'duplicate_core', label: `${core.length} agentes Core — manter 1 canônico.` });
  if (attendance.length > 1) out.push({ kind: 'duplicate_attendance', label: `${attendance.length} agentes de Atendimento — manter 1 canônico.` });

  // P-37 — MUDO. Presente, único e sem uma linha de instrução.
  // Ativo é AGRAVANTE, não requisito: um agente mudo e desligado é o estado
  // fail-closed em que o portão de provisionamento o deixa, e ele continua
  // precisando de conserto. Ativo e mudo é o que responde ao corretor (Core) ou
  // ao segurado (Atendimento) sem instrução e sem nenhuma trava.
  for (const [lista, kind, quem] of [
    [core, 'mute_core', 'AutoBrokers (Core)'],
    [attendance, 'mute_attendance', 'Agente de Atendimento'],
  ] as Array<[AgentLite[], DivergenceKind, string]>) {
    for (const a of lista) {
      if (!isMute(a)) continue;
      const como = estadoDaVoz(a.agent_system_prompt) === 'vazio'
        ? 'prompt vazio'
        : 'só as regras imutáveis, sem instrução da corretora';
      out.push({
        kind, agent_id: a.id,
        label: a.is_active
          ? `${quem} está ATIVO e MUDO (${como}) — responde sem instrução e sem trava. Reprovisionar.`
          : `${quem} está mudo (${como}) e por isso desligado — reprovisionar para devolver a voz.`,
      });
    }
  }

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
  // Saúde canônica = sem ausências/duplicatas/mudez (nome/teste são higiene).
  //
  // `mute_*` entra aqui, e não na higiene, porque foi exatamente isso que
  // faltou: a AutoFleet tinha um core presente, único e de ZERO caracteres, e
  // esta função respondia `true`. Um agente sem voz não é uma imperfeição de
  // cadastro — é um agente que não trabalha.
  return !divs.some((d) => [
    'missing_core', 'missing_attendance',
    'duplicate_core', 'duplicate_attendance',
    'mute_core', 'mute_attendance',
  ].includes(d.kind));
}

/** Espelha a política de modelo do Core (informativo na UI; runtime real é o backend). */
const ECONOMY = ['gpt-4o-mini', 'gpt-4o-mini-2024-07-18', 'gpt-3.5-turbo', 'gpt-4.1-mini'];
export function effectiveCoreModel(storedModel: string | null | undefined): string {
  const m = (storedModel || '').trim();
  if (!m || ECONOMY.includes(m)) return 'gpt-4o';
  return m;
}
