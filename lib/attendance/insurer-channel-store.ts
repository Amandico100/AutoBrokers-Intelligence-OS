// 42X3 — Persistência (sem schema novo) das configs de canal de acionamento.
// Armazena em tenant_connections.connection_config.insurer_action_channels[]
// (modelo Vault). Defensivo: se as tabelas do Vault não existirem no ambiente,
// lança 'vault_not_available' para o chamador degradar com clareza.
import type { SupabaseClient } from '@supabase/supabase-js';
import type { InsurerActionChannelConfig } from '@/lib/attendance/insurer-channel-registry';

const CONN_NAME = 'autobrokers_insurer_action_channels';

interface ConnRow {
  id: string;
  connection_config: Record<string, any> | null;
}

async function getOrCreateConnection(supabase: SupabaseClient, companyId: string): Promise<ConnRow> {
  const { data: existing, error: selErr } = await supabase
    .from('tenant_connections')
    .select('id, connection_config')
    .eq('company_id', companyId)
    .eq('name', CONN_NAME)
    .maybeSingle();
  if (selErr) throw new Error('vault_not_available');
  if (existing) return existing as ConnRow;

  const { data: tpl } = await supabase
    .from('connector_templates')
    .select('id')
    .eq('slug', 'whatsapp_zapi')
    .maybeSingle();
  if (!tpl?.id) throw new Error('connector_template_missing');

  const { data: created, error: insErr } = await supabase
    .from('tenant_connections')
    .insert({
      company_id: companyId,
      connector_template_id: tpl.id,
      name: CONN_NAME,
      status: 'draft',
      connection_config: { insurer_action_channels: [] },
      metadata: { purpose: 'insurer_action_channels_42x3' },
    })
    .select('id, connection_config')
    .single();
  if (insErr || !created) throw new Error('vault_not_available');
  return created as ConnRow;
}

function readConfigs(conn: ConnRow): InsurerActionChannelConfig[] {
  const cfg = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
  const arr = cfg.insurer_action_channels;
  return Array.isArray(arr) ? (arr as InsurerActionChannelConfig[]) : [];
}

export async function listChannelConfigs(supabase: SupabaseClient, companyId: string): Promise<InsurerActionChannelConfig[]> {
  const { data, error } = await supabase
    .from('tenant_connections')
    .select('connection_config')
    .eq('company_id', companyId)
    .eq('name', CONN_NAME)
    .maybeSingle();
  if (error) throw new Error('vault_not_available');
  if (!data) return [];
  return readConfigs({ id: '', connection_config: data.connection_config });
}

export async function saveChannelConfig(
  supabase: SupabaseClient,
  companyId: string,
  config: InsurerActionChannelConfig,
): Promise<InsurerActionChannelConfig[]> {
  const conn = await getOrCreateConnection(supabase, companyId);
  const configs = readConfigs(conn);
  const idx = configs.findIndex((c) => c.config_id === config.config_id);
  if (idx >= 0) configs[idx] = config;
  else configs.push(config);
  const baseCfg = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
  const { error } = await supabase
    .from('tenant_connections')
    .update({ connection_config: { ...baseCfg, insurer_action_channels: configs }, updated_at: new Date().toISOString() })
    .eq('id', conn.id)
    .eq('company_id', companyId);
  if (error) throw new Error('vault_not_available');
  return configs;
}

export async function removeChannelConfig(
  supabase: SupabaseClient,
  companyId: string,
  configId: string,
): Promise<InsurerActionChannelConfig[]> {
  const conn = await getOrCreateConnection(supabase, companyId);
  const configs = readConfigs(conn).filter((c) => c.config_id !== configId);
  const baseCfg = conn.connection_config && typeof conn.connection_config === 'object' ? conn.connection_config : {};
  const { error } = await supabase
    .from('tenant_connections')
    .update({ connection_config: { ...baseCfg, insurer_action_channels: configs }, updated_at: new Date().toISOString() })
    .eq('id', conn.id)
    .eq('company_id', companyId);
  if (error) throw new Error('vault_not_available');
  return configs;
}
