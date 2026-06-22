// TA2-C — coleta real de uso/custos (últimos 30 dias). Server-only. Sem custo fictício.
import type { SupabaseClient } from '@supabase/supabase-js';
import { buildUsageView, type UsageRow } from '@/lib/admin/tenant-usage-view';

export async function gatherUsage(supabase: SupabaseClient, companyId: string) {
  const sinceISO = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  let balance_brl = 0, alert_80 = false, alert_100 = false;
  try {
    const { data } = await supabase.from('company_credits').select('balance_brl, alert_80_sent, alert_100_sent').eq('company_id', companyId).maybeSingle();
    balance_brl = Number(data?.balance_brl ?? 0);
    alert_80 = Boolean(data?.alert_80_sent); alert_100 = Boolean(data?.alert_100_sent);
  } catch { /* honest zero */ }

  // mapa agent_id → rótulo humano (core/even); demais por nome real.
  const agentLabel = new Map<string, string>();
  try {
    const { data: agents } = await supabase.from('agents').select('id, name, agent_role').eq('company_id', companyId);
    for (const a of agents ?? []) {
      const role = (a as any).agent_role;
      agentLabel.set((a as any).id, role === 'core' ? 'AutoBrokers' : role === 'attendance' ? 'Even' : ((a as any).name ?? 'Agente'));
    }
  } catch { /* segue */ }

  const rows: UsageRow[] = [];
  try {
    // credit_transactions = consumo já precificado em BRL (fonte canônica de custo).
    const { data: txns } = await supabase.from('credit_transactions')
      .select('agent_id, type, amount_brl, model_name, tokens_input, tokens_output, created_at')
      .eq('company_id', companyId).gte('created_at', sinceISO).limit(5000);
    for (const t of txns ?? []) {
      const amt = Number((t as any).amount_brl ?? 0);
      // consumo = débito (amount negativo) ou type de uso.
      const isUsage = amt < 0 || /usage|consumo|debit|token/i.test(String((t as any).type ?? ''));
      if (!isUsage) continue;
      rows.push({
        agent_label: agentLabel.get((t as any).agent_id) ?? 'Geral',
        model_name: (t as any).model_name ?? null,
        cost_brl: Math.abs(amt),
        tokens: Number((t as any).tokens_input ?? 0) + Number((t as any).tokens_output ?? 0),
      });
    }
  } catch { /* segue */ }

  return buildUsageView({ balance_brl, alert_80, alert_100, rows });
}
