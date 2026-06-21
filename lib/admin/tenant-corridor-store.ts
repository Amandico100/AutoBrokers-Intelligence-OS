// TA2-B — store de corredores por tenant (catálogo + ativar/pausar/retomar).
// Reusa corridor_templates (catálogo) + tenant_corridors (estado). Server-only.
// NÃO executa ação externa, NÃO liga canal, NÃO abre portal: só estado de config.
import type { SupabaseClient } from '@supabase/supabase-js';
import { buildCorridorCatalog, nextCorridorStatus, type CorridorTemplateRow, type TenantCorridorRow } from '@/lib/admin/tenant-corridor-catalog';

const TEMPLATE_SELECT = 'id, scope, corridor_key, subcorridor_key, display_name, insurer_key, line_kind, macro_service, service_type, readiness, requires_action_engine, requires_dispatch_packet, allowed_channels, is_active, company_id';

export async function listTenantCorridors(supabase: SupabaseClient, companyId: string) {
  // catálogo: globais ativos + corredores próprios da corretora.
  const { data: templates } = await supabase.from('corridor_templates').select(TEMPLATE_SELECT)
    .or(`scope.eq.global,company_id.eq.${companyId}`);
  const { data: acts } = await supabase.from('tenant_corridors').select('corridor_template_id, status').eq('company_id', companyId);
  const items = buildCorridorCatalog(
    (templates ?? []) as unknown as CorridorTemplateRow[],
    (acts ?? []) as unknown as TenantCorridorRow[],
  );
  return { ok: true as const, items, active: items.filter((i) => i.status === 'active').length };
}

export async function setTenantCorridorStatus(
  supabase: SupabaseClient, companyId: string, templateId: string, action: string, userId: string,
) {
  const status = nextCorridorStatus(action);
  if (!status) return { ok: false as const, error: 'acao_invalida' };

  // valida que o template existe e é global ou da própria corretora (não cruza tenant).
  const { data: tpl } = await supabase.from('corridor_templates').select('id, scope, company_id, is_active').eq('id', templateId).maybeSingle();
  if (!tpl?.id) return { ok: false as const, error: 'template_inexistente' };
  const isGlobal = tpl.scope === 'global';
  const isOwn = tpl.company_id === companyId;
  if (!isGlobal && !isOwn) return { ok: false as const, error: 'template_fora_de_escopo' };
  if (tpl.is_active === false) return { ok: false as const, error: 'template_inativo' };

  const { error } = await supabase.from('tenant_corridors').upsert({
    company_id: companyId, corridor_template_id: templateId, status,
    installed_by: userId, updated_at: new Date().toISOString(),
  }, { onConflict: 'company_id,corridor_template_id' });
  if (error) return { ok: false as const, error: 'persist_failed' };

  return { ok: true as const, template_id: templateId, status };
}
