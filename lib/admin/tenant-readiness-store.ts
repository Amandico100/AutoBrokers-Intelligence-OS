// TA2-B — coleta de estado real para o checklist de prontidão. Server-only.
// Defensivo: cada consulta isolada; ausência → item fica "pendente" (honesto).
import type { SupabaseClient } from '@supabase/supabase-js';
import { buildReadiness, type ReadinessInput } from '@/lib/admin/tenant-readiness';

const DEFAULT_HANDOFF = 'um atendente humano da corretora';

function hasTenantConfig(cp: any): boolean {
  return Boolean(cp && typeof cp === 'object' && cp.tenant_agent_config && typeof cp.tenant_agent_config === 'object');
}

export async function gatherReadiness(supabase: SupabaseClient, companyId: string) {
  const input: ReadinessInput = {};

  try { const { data } = await supabase.from('companies').select('company_name').eq('id', companyId).maybeSingle(); input.company_name = data?.company_name ?? null; } catch { /* pendente */ }

  try {
    const { data: agents } = await supabase.from('agents').select('agent_role, is_active, context_package').eq('company_id', companyId);
    const core = (agents ?? []).find((a: any) => a.agent_role === 'core');
    const even = (agents ?? []).find((a: any) => a.agent_role === 'attendance');
    input.core_provisioned = Boolean(core);
    input.even_provisioned = Boolean(even);
    input.core_personalized = hasTenantConfig(core?.context_package);
    input.even_personalized = hasTenantConfig(even?.context_package);
    input.even_active = Boolean(even?.is_active);
    const handoff = even?.context_package?.tenant_agent_config?.variables?.handoff_target;
    input.handoff_defined = typeof handoff === 'string' && handoff.trim().length > 0 && handoff.trim() !== DEFAULT_HANDOFF;
  } catch { /* pendente */ }

  try { const { count } = await supabase.from('users_v2').select('id', { count: 'exact', head: true }).eq('company_id', companyId); input.team_count = count ?? 0; } catch { /* pendente */ }
  try { const { count } = await supabase.from('tenant_corridors').select('id', { count: 'exact', head: true }).eq('company_id', companyId).eq('status', 'active'); input.active_corridors = count ?? 0; } catch { /* pendente */ }
  try { const { count } = await supabase.from('tenant_auxiliaries').select('id', { count: 'exact', head: true }).eq('company_id', companyId); input.installed_auxiliaries = count ?? 0; } catch { /* pendente */ }

  try {
    const { data } = await supabase.from('tenant_connections').select('status, connector_templates(category, connector_kind, provider)').eq('company_id', companyId);
    input.whatsapp_connected = (data ?? []).some((r: any) => {
      const t = r.connector_templates || {};
      const isWa = /whats|zapi|evolution/i.test(`${t.category ?? ''} ${t.connector_kind ?? ''} ${t.provider ?? ''}`);
      const connected = ['connected', 'active', 'ready'].includes(String(r.status ?? '').toLowerCase());
      return isWa && connected;
    });
  } catch { /* pendente */ }

  return buildReadiness(input);
}
