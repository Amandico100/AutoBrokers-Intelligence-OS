// TA2-C — agregação PURA de uso/custos (testável). Só dados reais; nada inventado.
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
