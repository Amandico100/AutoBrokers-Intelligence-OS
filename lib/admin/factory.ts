// Server-only helpers para a Fábrica de Auxiliares (Admin Global).
// Resiliente ao schema: descobre as colunas reais em runtime (select * limit 1) e grava
// apenas a interseção, evitando "column does not exist" sem nunca alterar o schema.
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { assertSameOrigin, requireMasterAdmin, type AuthFail } from '@/lib/admin/admin-auth';

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

/**
 * SPEC-064 Bloco I.1 — o guard da Fábrica.
 *
 * Aqui existia `hasAdminCookie()`, que devolvia `true` para QUALQUER cookie
 * chamado `smith_admin_session`, com qualquer valor. Sem assinatura, sem
 * expiração, sem conferir se o admin ainda existe.
 *
 * Ele guardava oito rotas — entre elas **criar template global** e **instalar
 * auxiliar em qualquer corretora**. Na prática, quem conseguisse escrever um
 * cookie com aquele nome instalava software na corretora de outra pessoa.
 *
 * A correção não inventa padrão novo: usa `requireMasterAdmin()`, que decodifica
 * a sessão iron-session, valida o papel e confirma no banco que o admin não foi
 * revogado — o mesmo caminho que as rotas novas já usam. Mutação também exige
 * same-origin, por defesa em profundidade.
 */
export async function requireFactoryAdmin(
  req?: { headers: { get(name: string): string | null } },
): Promise<{ ok: true; supabase: SupabaseClient } | AuthFail> {
  if (req) {
    const crossOrigin = assertSameOrigin(req);
    if (crossOrigin) return crossOrigin;
  }
  const auth = await requireMasterAdmin();
  if (!auth.ok) return auth;
  return { ok: true, supabase: auth.supabase };
}

/** Resposta padrão de recusa, para as rotas não repetirem o formato. */
export function factoryAuthResponse(fail: AuthFail): Response {
  return Response.json({ error: fail.error }, { status: fail.status });
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
