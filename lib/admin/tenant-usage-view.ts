// TA2-C + SPEC-131-0-B3 F4 — agregação PURA de uso/custos (testável). Só dados reais; nada inventado.
//
// Duas fontes, dois papéis:
//   credit_transactions  o RAZÃO: o único lugar de onde sai dinheiro (R$) para a tela.
//   token_usage_logs     o MEDIDOR: quantas vezes a IA trabalhou para a corretora, e quanto texto.
// ⛔ O custo do provedor (total_cost_usd) NUNCA vira reais aqui: converter seria PREÇO (CLAUDE.md §13.6).

// ── contrato antigo (mantido: agregação do razão em R$) ─────────────────────
export interface UsageRow { agent_label: string; model_name: string | null; cost_brl: number; tokens: number }
export interface UsageGroup { key: string; cost_brl: number; tokens: number }
export interface UsageView {
  balance_brl: number;
  alert_80: boolean;
  alert_100: boolean;
  period_total_brl: number;
  period_tokens: number;
  by_agent: UsageGroup[];
  by_model: UsageGroup[];
  has_data: boolean;
}

function round2(n: number): number { return Math.round(n * 100) / 100; }
const num = (v: unknown): number => { const n = Number(v); return Number.isFinite(n) ? n : 0; };

function group(rows: UsageRow[], pick: (r: UsageRow) => string): UsageGroup[] {
  const m = new Map<string, UsageGroup>();
  for (const r of rows) {
    const key = pick(r) || '—';
    const g = m.get(key) ?? { key, cost_brl: 0, tokens: 0 };
    g.cost_brl = round2(g.cost_brl + (Number.isFinite(r.cost_brl) ? r.cost_brl : 0));
    g.tokens += Number.isFinite(r.tokens) ? r.tokens : 0;
    m.set(key, g);
  }
  return Array.from(m.values()).sort((a, b) => b.cost_brl - a.cost_brl);
}

export function buildUsageView(input: { balance_brl: number; alert_80: boolean; alert_100: boolean; rows: UsageRow[] }): UsageView {
  const rows = input.rows ?? [];
  const period_total_brl = round2(rows.reduce((s, r) => s + (Number.isFinite(r.cost_brl) ? r.cost_brl : 0), 0));
  const period_tokens = rows.reduce((s, r) => s + (Number.isFinite(r.tokens) ? r.tokens : 0), 0);
  return {
    balance_brl: round2(input.balance_brl ?? 0),
    alert_80: Boolean(input.alert_80),
    alert_100: Boolean(input.alert_100),
    period_total_brl,
    period_tokens,
    by_agent: group(rows, (r) => r.agent_label),
    by_model: group(rows, (r) => r.model_name ?? '—'),
    has_data: rows.length > 0,
  };
}

// ── rótulos humanos ─────────────────────────────────────────────────────────
export interface AgentRow { id: string; name: string | null; agent_role: string | null; company_id: string | null }

/** O nome que o corretor reconhece. O central é sempre "AutoBrokers"; o de atendimento, o nome que a corretora deu. */
export function rotuloDoAssistente(agente: AgentRow | null | undefined): string {
  if (!agente) return 'Outros usos';
  const nome = String(agente.name ?? '').trim();
  if (agente.agent_role === 'core') return 'AutoBrokers';
  if (agente.agent_role === 'attendance') return nome || 'Atendimento';
  return nome || 'Assistente';
}

// Modelos medidos em token_usage_logs (📊 15/10/2026, 90 dias, `select distinct model_name`).
const MODELOS: Record<string, string> = {
  'gpt-6-luna': 'OpenAI · GPT-6 Luna',
  'gpt-6-sol': 'OpenAI · GPT-6 Sol',
  'gpt-6.1-sol': 'OpenAI · GPT-6.1 Sol',
  'gpt-6-astra': 'OpenAI · GPT-6 Astra',
  'gpt-5.6-terra': 'OpenAI · GPT-5.6 Terra',
  'gpt-4o': 'OpenAI · GPT-4o',
  'gpt-4o-mini': 'OpenAI · GPT-4o mini',
  'whisper-1': 'OpenAI · Transcrição de áudio',
  'claude-opus-5-5': 'Anthropic · Claude Opus 5.5',
  'claude-opus-5': 'Anthropic · Claude Opus 5',
  'claude-sonnet-5-5': 'Anthropic · Claude Sonnet 5.5',
  'claude-sonnet-5': 'Anthropic · Claude Sonnet 5',
  'claude-haiku-4-5': 'Anthropic · Claude Haiku 4.5',
};
const BUSCA = 'Busca no conhecimento';
const OUTRO = 'Outro modelo';

/** "OpenAI · GPT-6 Luna". Embeddings/rerank → "Busca no conhecimento". Desconhecido → provedor pelo prefixo + nome cru. */
export function rotuloDoModelo(modelo: string | null | undefined): string {
  const cru = String(modelo ?? '').trim();
  if (!cru) return OUTRO;
  const m = cru.toLowerCase();
  if (/embed|rerank/.test(m)) return BUSCA;
  const semData = m.replace(/-(\d{8}|\d{4}-\d{2}-\d{2})$/, '');
  if (MODELOS[semData]) return MODELOS[semData];
  if (/^(gpt-|o\d|whisper|dall-e|tts-)/.test(m)) return `OpenAI · ${cru}`;
  if (m.startsWith('claude')) return `Anthropic · ${cru}`;
  if (m.startsWith('gemini')) return `Google · ${cru}`;
  return OUTRO;
}

// ── volume de texto ─────────────────────────────────────────────────────────
// A IA lê e escreve em pedaços de texto; em média 1.000 pedaços ≈ 750 palavras
// (https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them).
const PALAVRAS_POR_PEDACO = 0.75;
const fmt = (n: number, casas = 0) => n.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: casas });

export function palavrasAproximadas(pedacos: number): string {
  const p = Math.round(num(pedacos) * PALAVRAS_POR_PEDACO);
  if (p <= 0) return 'nenhuma palavra';
  if (p < 1000) return `≈ ${fmt(p)} ${p === 1 ? 'palavra' : 'palavras'}`;
  if (p < 999_500) return `≈ ${fmt(Math.round(p / 1000))} mil palavras`;
  const mi = Math.round(p / 100_000) / 10;
  return `≈ ${fmt(mi, 1)} ${mi < 2 ? 'milhão' : 'milhões'} de palavras`;
}

// ── a visão da tela Custos ──────────────────────────────────────────────────
export interface LogRow {
  company_id: string | null;
  agent_id: string | null;
  model_name: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  details?: Record<string, unknown> | null;
}
export interface LedgerRow { company_id: string | null; agent_id: string | null; type: string | null; amount_brl: unknown; model_name?: string | null; created_at?: string }
export interface CreditsRow { balance_brl: unknown; alert_80_sent?: boolean | null; alert_100_sent?: boolean | null }
export interface PersonRow { id: string; nome: string }

export interface UsoGrupo { chave: string; rotulo: string; chamadas: number; palavras: string }
export interface UsoDaCorretora {
  saldo: { balance_brl: number; alert_80: boolean; alert_100: boolean } | null;
  cobranca: { comecou: boolean; total_brl: number; lancamentos: number };
  uso: { chamadas: number; palavras: string };
  por_assistente: UsoGrupo[];
  por_pessoa: UsoGrupo[];
  por_modelo: UsoGrupo[];
  has_data: boolean;
}

/** Débito de uso no razão (bônus e recarga não são cobrança). */
export function ehCobrancaDeUso(t: LedgerRow): boolean {
  const amt = num(t.amount_brl);
  return amt < 0 || (amt !== 0 && /usage|consumo|debit|token/i.test(String(t.type ?? '')) && !/bonus|recarga|topup|credit/i.test(String(t.type ?? '')));
}

function agrupar(logs: LogRow[], chave: (l: LogRow) => [string, string] | null): UsoGrupo[] {
  const m = new Map<string, { rotulo: string; chamadas: number; pedacos: number }>();
  for (const l of logs) {
    const k = chave(l);
    if (!k) continue;
    const g = m.get(k[0]) ?? { rotulo: k[1], chamadas: 0, pedacos: 0 };
    g.chamadas += 1;
    g.pedacos += num(l.input_tokens) + num(l.output_tokens);
    m.set(k[0], g);
  }
  return Array.from(m.entries())
    .map(([k, g]) => ({ chave: k, rotulo: g.rotulo, chamadas: g.chamadas, palavras: palavrasAproximadas(g.pedacos) }))
    .sort((a, b) => b.chamadas - a.chamadas);
}

/**
 * Tudo filtrado por `companyId` AQUI também (defesa em profundidade: o coletor já filtra no banco,
 * mas uma linha de outra corretora nunca é contada mesmo que chegue).
 */
export function buildUsoDaCorretora(input: {
  companyId: string;
  credits: CreditsRow | null;
  ledger: LedgerRow[];
  logs: LogRow[];
  agents: AgentRow[];
  people: PersonRow[];
  /** Já houve débito de uso no razão em qualquer data (consulta à parte). */
  cobrancaJaComecou?: boolean;
}): UsoDaCorretora {
  const cid = input.companyId;
  const logs = (input.logs ?? []).filter((l) => !!cid && l.company_id === cid);
  const agentes = new Map((input.agents ?? []).filter((a) => a.company_id === cid).map((a) => [a.id, a]));
  const debitos = (input.ledger ?? []).filter((t) => t.company_id === cid && ehCobrancaDeUso(t));

  // dinheiro: reaproveita a agregação do razão (uma só soma em R$).
  const razao = buildUsageView({
    balance_brl: num(input.credits?.balance_brl),
    alert_80: Boolean(input.credits?.alert_80_sent),
    alert_100: Boolean(input.credits?.alert_100_sent),
    rows: debitos.map((t) => ({ agent_label: rotuloDoAssistente(agentes.get(String(t.agent_id))), model_name: t.model_name ?? null, cost_brl: Math.abs(num(t.amount_brl)), tokens: 0 })),
  });

  const nomes = new Map((input.people ?? []).map((p) => [p.id, p.nome]));
  const pedacos = logs.reduce((s, l) => s + num(l.input_tokens) + num(l.output_tokens), 0);

  return {
    saldo: input.credits ? { balance_brl: razao.balance_brl, alert_80: razao.alert_80, alert_100: razao.alert_100 } : null,
    cobranca: { comecou: debitos.length > 0 || Boolean(input.cobrancaJaComecou), total_brl: razao.period_total_brl, lancamentos: debitos.length },
    uso: { chamadas: logs.length, palavras: palavrasAproximadas(pedacos) },
    por_assistente: agrupar(logs, (l) => {
      const a = l.agent_id ? agentes.get(l.agent_id) : undefined; // agente de outra corretora → "Outros usos"
      const r = rotuloDoAssistente(a ?? null); // agrupa pelo nome: dois "AutoBrokers" são um só para o corretor
      return [r, r];
    }),
    por_pessoa: agrupar(logs, (l) => {
      const uid = String((l.details ?? {})?.user_id ?? '');
      return uid ? [uid, nomes.get(uid) || 'Pessoa da equipe'] : null;
    }),
    por_modelo: agrupar(logs, (l) => { const r = rotuloDoModelo(l.model_name); return [r, r]; }),
    has_data: logs.length > 0 || debitos.length > 0,
  };
}
