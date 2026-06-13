// Helpers (server-side) para a API de destinos humanos de suporte (handoff).
// Nunca retorna destination_ref cru; segredos/tokens vivem no Vault, não aqui.
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

export const DESTINATION_TYPES = [
  'whatsapp_group',
  'whatsapp_individual',
  'email',
  'internal_queue',
  'webhook',
] as const;

export const CHANNEL_PROVIDERS = ['zapi', 'evolution', 'meta_cloud', 'manual'] as const;

export const DESTINATION_COLUMNS =
  'id, name, destination_type, channel_provider, tenant_connection_id, destination_ref, display_ref, is_primary, priority_order, fallback_enabled, silence_minutes, active_hours, escalation_rules, metadata, is_active, created_at, updated_at';

export function getAdminClient(): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

export async function getCompanyId(supabaseAdmin: SupabaseClient, userId: string): Promise<string | null> {
  const { data, error } = await supabaseAdmin.from('users_v2').select('company_id').eq('id', userId).single();
  if (error || !data?.company_id) return null;
  return data.company_id as string;
}

function isPlainObject(v: unknown): boolean {
  return Boolean(v) && typeof v === 'object' && !Array.isArray(v);
}

function maskMiddle(s: string, keepStart: number, keepEnd: number): string {
  if (s.length <= keepStart + keepEnd) return s.replace(/.(?=.)/g, '*');
  return `${s.slice(0, keepStart)}****${s.slice(s.length - keepEnd)}`;
}

/** Gera um display_ref mascarado a partir do destination_ref (sem expor o valor completo). */
export function maskDestinationRef(ref: string, type?: string): string {
  const r = (ref || '').trim();
  if (!r) return 'destino configurado';

  // WhatsApp group JID (…@g.us)
  if (r.endsWith('@g.us')) {
    const local = r.slice(0, r.indexOf('@'));
    return `${maskMiddle(local, 6, 4)}@g.us`;
  }

  // E-mail
  const domain = r.includes('@') ? r.split('@')[1] || '' : '';
  if (type === 'email' || (r.includes('@') && /\.[a-z]{2,}$/i.test(domain))) {
    const local = r.split('@')[0] || '';
    return `${local.slice(0, 2)}****@${domain}`;
  }

  // URL / webhook
  if (/^https?:\/\//i.test(r)) {
    try {
      return `webhook: ${new URL(r).host}`;
    } catch {
      return 'webhook configurado';
    }
  }

  // Telefone (majoritariamente dígitos)
  const digits = r.replace(/\D/g, '');
  if (digits.length >= 8) return maskMiddle(r, 4, 4);

  if (r.length >= 8) return maskMiddle(r, 4, 4);
  return 'destino configurado';
}

/** Remove destination_ref cru da resposta; expõe apenas has_destination_ref. */
export function serializeDestination(row: any): Record<string, unknown> {
  if (!row) return row;
  const { destination_ref, ...rest } = row;
  return { ...rest, has_destination_ref: Boolean(destination_ref) };
}

/**
 * Valida e monta os campos permitidos. partial=true para PATCH (só os enviados).
 * Não valida ownership de tenant_connection_id (feito na rota).
 */
export function buildDestinationFields(
  body: Record<string, any>,
  opts: { partial: boolean },
): { fields?: Record<string, unknown>; error?: string } {
  const fields: Record<string, unknown> = {};
  const { partial } = opts;
  const has = (k: string) => k in body && body[k] !== undefined;

  if (has('name')) {
    if (typeof body.name !== 'string' || !body.name.trim()) return { error: 'name inválido.' };
    if (body.name.trim().length > 120) return { error: 'name muito longo (máx 120).' };
    fields.name = body.name.trim();
  } else if (!partial) {
    return { error: 'name é obrigatório.' };
  }

  if (has('destination_type')) {
    if (!(DESTINATION_TYPES as readonly string[]).includes(body.destination_type)) {
      return { error: 'destination_type inválido.' };
    }
    fields.destination_type = body.destination_type;
  } else if (!partial) {
    return { error: 'destination_type é obrigatório.' };
  }

  if (has('channel_provider')) {
    if (!(CHANNEL_PROVIDERS as readonly string[]).includes(body.channel_provider)) {
      return { error: 'channel_provider inválido.' };
    }
    fields.channel_provider = body.channel_provider;
  } else if (!partial) {
    fields.channel_provider = 'manual';
  }

  if (has('destination_ref')) {
    if (typeof body.destination_ref !== 'string' || !body.destination_ref.trim()) {
      return { error: 'destination_ref inválido.' };
    }
    if (body.destination_ref.trim().length > 500) return { error: 'destination_ref muito longo (máx 500).' };
    fields.destination_ref = body.destination_ref.trim();
  } else if (!partial) {
    return { error: 'destination_ref é obrigatório.' };
  }

  if (has('tenant_connection_id')) {
    const t = body.tenant_connection_id;
    if (t !== null && typeof t !== 'string') return { error: 'tenant_connection_id inválido.' };
    fields.tenant_connection_id = t || null;
  }

  for (const b of ['is_primary', 'fallback_enabled', 'is_active'] as const) {
    if (has(b)) {
      if (typeof body[b] !== 'boolean') return { error: `${b} deve ser boolean.` };
      fields[b] = body[b];
    }
  }

  for (const n of ['priority_order', 'silence_minutes'] as const) {
    if (has(n)) {
      if (!Number.isInteger(body[n]) || body[n] < 0) return { error: `${n} deve ser inteiro >= 0.` };
      fields[n] = body[n];
    }
  }

  if (has('active_hours')) {
    if (!isPlainObject(body.active_hours)) return { error: 'active_hours deve ser object.' };
    fields.active_hours = body.active_hours;
  }
  if (has('escalation_rules')) {
    if (!Array.isArray(body.escalation_rules)) return { error: 'escalation_rules deve ser array.' };
    fields.escalation_rules = body.escalation_rules;
  }
  if (has('metadata')) {
    if (!isPlainObject(body.metadata)) return { error: 'metadata deve ser object.' };
    fields.metadata = body.metadata;
  }

  return { fields };
}

/** Confirma que a tenant_connection pertence à mesma corretora. */
export async function tenantConnectionBelongsToCompany(
  supabaseAdmin: SupabaseClient,
  connectionId: string,
  companyId: string,
): Promise<boolean> {
  const { data, error } = await supabaseAdmin
    .from('tenant_connections')
    .select('id')
    .eq('id', connectionId)
    .eq('company_id', companyId)
    .maybeSingle();
  return !error && Boolean(data);
}

/** Desmarca primários ativos da corretora (exceto exceptId), liberando o índice único parcial. */
export async function demoteActivePrimaries(
  supabaseAdmin: SupabaseClient,
  companyId: string,
  exceptId?: string,
): Promise<void> {
  let q = supabaseAdmin
    .from('human_support_destinations')
    .update({ is_primary: false })
    .eq('company_id', companyId)
    .eq('is_primary', true)
    .eq('is_active', true);
  if (exceptId) q = q.neq('id', exceptId);
  await q;
}
