// Server-only helpers para a Fábrica de Auxiliares (Admin Global).
// Resiliente ao schema: descobre as colunas reais em runtime (select * limit 1) e grava
// apenas a interseção, evitando "column does not exist" sem nunca alterar o schema.
import { cookies } from 'next/headers';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

export const TEMPLATE_FALLBACK_COLS = [
  'id',
  'slug',
  'name',
  'description',
  'category',
  'is_active',
  'created_at',
  'updated_at',
];

export const TENANT_FALLBACK_COLS = [
  'id',
  'company_id',
  'template_id',
  'slug',
  'status',
  'created_at',
];

/** Supabase com SERVICE ROLE (somente server). Nunca expor ao client. */
export function getAdminSupabase(): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

/** Guard mínimo do Admin Global (mesmo padrão das rotas /api/admin existentes). */
export async function hasAdminCookie(): Promise<boolean> {
  const store = await cookies();
  return Boolean(store.get('smith_admin_session'));
}

/** Colunas reais de uma tabela (via amostra). Cai para `fallback` se vazia/erro. */
export async function getTableColumns(
  supabase: SupabaseClient,
  table: string,
  fallback: string[],
): Promise<Set<string>> {
  try {
    const { data } = await supabase.from(table).select('*').limit(1);
    if (data && data.length > 0) return new Set(Object.keys(data[0] as Record<string, unknown>));
  } catch {
    /* ignore — usa fallback */
  }
  return new Set(fallback);
}

/** Mantém só as chaves que existem como coluna e não são undefined. */
export function pickColumns(
  candidate: Record<string, unknown>,
  cols: Set<string>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(candidate)) {
    if (cols.has(k) && v !== undefined) out[k] = v;
  }
  return out;
}

/** Valida/normaliza um campo JSON (textarea). '' → undefined. Inválido → erro. */
export function parseJsonField(raw: unknown, field: string): { value?: unknown; error?: string } {
  if (raw === undefined || raw === null || raw === '') return { value: undefined };
  if (typeof raw === 'object') return { value: raw };
  if (typeof raw !== 'string') return { error: `Campo ${field} inválido.` };
  try {
    return { value: JSON.parse(raw) };
  } catch {
    return { error: `JSON inválido em "${field}".` };
  }
}

export const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
