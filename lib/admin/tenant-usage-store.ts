// TA2-C + SPEC-131-0-B3 F4 — coleta real de uso/custos (últimos 30 dias). Server-only. Sem custo fictício.
// 🔴 Toda consulta filtra `company_id` no código (CLAUDE.md §7: o backend usa service role; RLS não protege).
// ⛔ Só leitura. Dinheiro só do razão (credit_transactions); o custo do provedor nem é lido.
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  buildUsoDaCorretora,
  type AgentRow, type CreditsRow, type LedgerRow, type LogRow, type PersonRow, type UsoDaCorretora,
} from '@/lib/admin/tenant-usage-view';

const PAGINA = 1000;      // o PostgREST devolve no máximo 1.000 linhas por pedido
const MAX_PAGINAS = 50;   // teto de 50 mil chamadas em 30 dias por corretora

export async function gatherUsage(supabase: SupabaseClient, companyId: string): Promise<UsoDaCorretora> {
  const sinceISO = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  let credits: CreditsRow | null = null;
  try {
    const { data } = await supabase.from('company_credits')
      .select('balance_brl, alert_80_sent, alert_100_sent')
      .eq('company_id', companyId).maybeSingle();
    credits = (data as CreditsRow | null) ?? null; // sem linha → sem cartão de saldo (nunca um R$ 0,00 que parece real)
  } catch { /* honesto: sem saldo */ }

  let agents: AgentRow[] = [];
  try {
    const { data } = await supabase.from('agents').select('id, name, agent_role, company_id').eq('company_id', companyId);
    agents = (data ?? []) as AgentRow[];
  } catch { /* segue: tudo vira "Outros usos" */ }

  let ledger: LedgerRow[] = [];
  let cobrancaJaComecou = false;
  try {
    const { data } = await supabase.from('credit_transactions')
      .select('company_id, agent_id, type, amount_brl, model_name, created_at')
      .eq('company_id', companyId).gte('created_at', sinceISO).limit(5000);
    ledger = (data ?? []) as LedgerRow[];
    // houve débito de uso em QUALQUER data? (então "R$ 0,00 nos 30 dias" é verdade, e a frase não)
    const { data: algum } = await supabase.from('credit_transactions')
      .select('id').eq('company_id', companyId).lt('amount_brl', 0).limit(1);
    cobrancaJaComecou = (algum ?? []).length > 0;
  } catch { /* honesto: cobrança não começou */ }

  const logs: LogRow[] = [];
  try {
    for (let p = 0; p < MAX_PAGINAS; p++) {
      const de = p * PAGINA;
      const { data, error } = await supabase.from('token_usage_logs')
        .select('company_id, agent_id, model_name, input_tokens, output_tokens, details')
        .eq('company_id', companyId).gte('created_at', sinceISO)
        .order('created_at', { ascending: true }).order('id', { ascending: true })
        .range(de, de + PAGINA - 1);
      if (error) break;
      const lote = (data ?? []) as LogRow[];
      logs.push(...lote);
      if (lote.length < PAGINA) break;
    }
  } catch { /* honesto: o que veio até aqui */ }

  // quebra POR PESSOA: só quando o medidor gravou details.user_id (SPEC-044).
  const people: PersonRow[] = [];
  const ids = Array.from(new Set(logs.map((l) => String((l.details ?? {})?.user_id ?? '')).filter(Boolean)));
  if (ids.length) {
    try {
      const { data: users } = await supabase.from('users_v2').select('id, first_name, last_name').in('id', ids);
      for (const u of (users ?? []) as { id: string; first_name: string | null; last_name: string | null }[]) {
        people.push({ id: u.id, nome: `${u.first_name ?? ''} ${u.last_name ?? ''}`.trim() });
      }
    } catch { /* segue: "Pessoa da equipe" */ }
  }

  return buildUsoDaCorretora({ companyId, credits, ledger, logs, agents, people, cobrancaJaComecou });
}
