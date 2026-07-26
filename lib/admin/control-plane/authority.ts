// SPEC-061 §5.1 e §8 — a autoridade administrativa, server-only.
//
// Por que este arquivo existe
// ---------------------------
// Hoje a proteção de rota do Admin acontece NO NAVEGADOR: `app/admin/layout.tsx`
// lê a sessão de `localStorage` e compara a rota atual com uma lista de
// "masterOnlyRoutes". Isso esconde a tela — e não protege a API.
//
// §8.4 é direta: "esconder botão é conveniência, não segurança". Quem quiser
// pular a tela chama a rota direto, e hoje ela responde.
//
// A partir daqui, quem decide é o servidor. O `localStorage` volta a ser o que
// o §7.2 permite: preferência de barra lateral, tema, densidade.
//
// Uma autoridade só
// -----------------
// A matriz de papéis vive no backend (`services/control_plane/rbac.py`). Este
// módulo NÃO a reimplementa: ele pergunta. Duas cópias da matriz divergiriam na
// primeira permission nova — alguém acrescenta a tela, o backend passa a cobrar
// `releases.rollout`, o front não conhece a chave, e o operador vê um botão que
// devolve 403.
//
// O custo é uma chamada interna por requisição administrativa, com cache curto
// em memória. O ganho é não ter como as duas respostas discordarem.
import 'server-only';
import { getAdminContext, supabaseService } from '@/lib/admin/admin-auth';

export type Autoridade = {
  userId: string;
  papeis: string[];
  papeisLegiveis: string[];
  permissions: Set<string>;
  temAcesso: boolean;
};

export type FalhaDeAutoridade = {
  ok: false;
  status: number;
  error: string;
  motivo: string;
};

function backend(): { url: string; key: string } | null {
  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) return null;
  return { url, key };
}

// Cache por processo, curto. A autoridade muda quando alguém concede ou revoga
// papel — evento raro — mas 30s é curto o bastante para que uma revogação
// tenha efeito quase imediato, que é o que o §8.4 exige ("role binding
// suspenso perde acesso imediatamente").
const CACHE_MS = 30_000;
const cache = new Map<string, { em: number; valor: Autoridade }>();

async function chamar(caminho: string, corpo: unknown): Promise<any | null> {
  const b = backend();
  if (!b) return null;
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      method: 'POST',
      headers: { 'X-Internal-Key': b.key, 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
      cache: 'no-store',
    });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

/**
 * Quem é e o que pode. `null` quando não há sessão administrativa válida.
 *
 * Falha de comunicação com o backend devolve autoridade VAZIA, nunca a
 * anterior em cache expirado: um backend fora do ar não pode conceder acesso.
 * O Admin fica inacessível por alguns segundos — problema visível, e portanto
 * consertável.
 */
export async function resolverAutoridade(): Promise<Autoridade | null> {
  const ctx = await getAdminContext();
  if (!ctx?.adminId) return null;

  const agora = Date.now();
  const emCache = cache.get(ctx.adminId);
  if (emCache && agora - emCache.em < CACHE_MS) return emCache.valor;

  // A sessão sozinha não basta: o principal precisa AINDA existir. É o mesmo
  // princípio do `adminPrincipalExists` já usado pelas rotas — remoção de
  // acesso tem efeito imediato.
  try {
    const supabase = supabaseService();
    const { data } = await supabase.from('admin_users').select('id').eq('id', ctx.adminId).maybeSingle();
    if (!data?.id) {
      cache.delete(ctx.adminId);
      return null;
    }
  } catch {
    return null;
  }

  const r = await chamar('/api/admin/control-plane/authority', {
    user_id: ctx.adminId,
    papel_legado: ctx.role ?? null,
  });

  const valor: Autoridade = {
    userId: ctx.adminId,
    papeis: Array.isArray(r?.papeis) ? r.papeis : [],
    papeisLegiveis: Array.isArray(r?.papeis_legiveis) ? r.papeis_legiveis : [],
    permissions: new Set<string>(Array.isArray(r?.permissions) ? r.permissions : []),
    temAcesso: Boolean(r?.tem_acesso),
  };

  // Só entra em cache o que veio do backend. Uma resposta vazia por falha de
  // rede não pode ficar guardada 30s — ela travaria o Admin de quem tem acesso.
  if (r?.ok) cache.set(ctx.adminId, { em: agora, valor });
  return valor;
}

/** Descarta o cache de uma pessoa. Chamado ao conceder ou revogar papel. */
export function esquecerAutoridade(userId: string): void {
  cache.delete(userId);
}

/**
 * O portão das rotas administrativas.
 *
 * ```ts
 * const auth = await exigirPermissao('work_runs.retry');
 * if (!auth.ok) return NextResponse.json(auth, { status: auth.status });
 * ```
 *
 * O corpo do 403 é estável e não conta ao curioso qual papel teria o poder —
 * isso seria mapa para quem sonda.
 */
export async function exigirPermissao(
  permissionKey: string,
): Promise<{ ok: true; autoridade: Autoridade } | FalhaDeAutoridade> {
  const autoridade = await resolverAutoridade();
  if (!autoridade) {
    return { ok: false, status: 401, error: 'no_admin_session', motivo: 'Faça login novamente.' };
  }
  if (!autoridade.temAcesso) {
    return {
      ok: false,
      status: 403,
      error: 'forbidden',
      motivo: 'Sua conta não tem papel administrativo ativo.',
    };
  }
  if (!autoridade.permissions.has(permissionKey)) {
    return {
      ok: false,
      status: 403,
      error: 'forbidden',
      motivo: 'Seu papel não inclui esta ação.',
    };
  }
  return { ok: true, autoridade };
}

/** Conveniência de leitura para montar tela. Não substitui `exigirPermissao`. */
export async function pode(permissionKey: string): Promise<boolean> {
  const a = await resolverAutoridade();
  return Boolean(a?.temAcesso && a.permissions.has(permissionKey));
}
