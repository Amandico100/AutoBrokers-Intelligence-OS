// TA2-C — leituras read-only de Equipe e Conhecimento da corretora. Server-only.
// Sanitizado: nunca expõe hash, tokens, stripe, CPF ou IDs técnicos ao corretor.
import type { SupabaseClient } from '@supabase/supabase-js';

// 🔴 09/09/2026 — `attendant` faltava aqui e a tela mostrava a palavra crua
// "attendant" para quem tem o papel.
// 🔴 SPEC-131-0 A · F1 — o rótulo diz QUEM a pessoa é (Administrador · Membro · Atendente · Dono); o que cada papel
// PODE a tela diz ao lado (`O_QUE_O_PAPEL_PODE`). ⚠️ Este mapa é cópia VIGIADA de `ROTULO_DO_PAPEL`
// (lib/admin/admin-auth-policy.ts): `scripts/spec1310-membros.test.mjs` chama `getTeam` e compara. Ele fica aqui,
// sem importar a política, porque este arquivo é carregado sem resolvedor de imports por outros testes.
const ROLE_LABEL: Record<string, string> = {
  owner: 'Dono', admin_company: 'Administrador', member: 'Membro', attendant: 'Atendente',
  admin: 'Administrador', master_admin: 'Master',
};

/** As funções de trabalho como vieram do banco (o CHECK `ck_company_members_funcoes` já garante a lista fechada). */
function funcoesDoVinculo(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

// 📊 PGRST204/42703 = a coluna `funcoes` ainda não existe (o código subiu antes da migration 20261011_02).
function faltaAColunaFuncoes(error: { code?: string; message?: string } | null): boolean {
  if (!error) return false;
  return error.code === '42703' || error.code === 'PGRST204' || /funcoes/.test(String(error.message || ''));
}

// SPEC-048: a equipe vem dos VÍNCULOS (company_members) — quem pertence a
// duas corretoras (donos) aparece nas duas; quem é de uma, só na sua. Papel,
// is_owner e funções são os DO VÍNCULO desta empresa.
export async function getTeam(supabase: SupabaseClient, companyId: string) {
  const consulta = (colunas: string) => supabase.from('company_members')
    .select(colunas)
    .eq('company_id', companyId).eq('status', 'active')
    .order('created_at', { ascending: true }).limit(500);
  let { data: mems, error } = await consulta('user_id, role, is_owner, funcoes, created_at');
  // ⚠️ a lista da equipe NUNCA some porque a coluna nova ainda não chegou: lê sem ela (todos ficam sem função).
  if (faltaAColunaFuncoes(error)) ({ data: mems, error } = await consulta('user_id, role, is_owner, created_at'));
  const ids = (mems ?? []).map((m: any) => m.user_id);
  if (!ids.length) return { ok: true as const, members: [], total: 0 };
  const { data: users } = await supabase.from('users_v2')
    .select('id, first_name, last_name, email, phone, status, last_login_at')
    .in('id', ids).is('deleted_at', null);
  const byId = new Map((users ?? []).map((u: any) => [u.id, u]));
  const members = (mems ?? [])
    .filter((m: any) => byId.has(m.user_id))
    .map((m: any) => {
      const u = byId.get(m.user_id) as any;
      const funcoes = funcoesDoVinculo(m.funcoes);
      return {
        user_id: m.user_id,
        name: [u.first_name, u.last_name].filter(Boolean).join(' ').trim() || (u.email ?? 'Sem nome'),
        first_name: u.first_name ?? '',
        last_name: u.last_name ?? '',
        email: u.email ?? null,
        phone: u.phone ?? null,
        role: m.role ?? 'member',
        role_label: ROLE_LABEL[m.role] ?? (m.role ?? 'Membro'),
        is_owner: Boolean(m.is_owner),
        funcoes,
        status: u.status ?? null,
        last_login_at: u.last_login_at ?? null,
      };
    });
  return { ok: true as const, members, total: members.length };
}

export async function getKnowledge(supabase: SupabaseClient, companyId: string, viewerUserId?: string) {
  const { data } = await supabase.from('documents')
    .select('file_name, file_type, status, scope, knowledge_class, visibility, chunks_count, created_at, owner_user_id')
    .eq('company_id', companyId).order('created_at', { ascending: false }).limit(500);
  const docs = (data ?? [])
    // SPEC-044: documento PESSOAL só aparece para o dono — nem o nome vaza.
    .filter((d: any) => d.scope !== 'personal' || (viewerUserId && d.owner_user_id === viewerUserId))
    .map((d: any) => ({
      file_name: d.file_name ?? 'Documento',
      file_type: d.file_type ?? null,
      status: d.status ?? 'desconhecido',
      scope: d.scope ?? 'private',
      mine: d.scope === 'personal',
      knowledge_class: d.knowledge_class ?? null,
      visibility: d.visibility ?? null,
      chunks: d.chunks_count ?? 0,
      created_at: d.created_at ?? null,
    }));
  const ready = docs.filter((d) => /ready|done|completed|processed|ingested/i.test(d.status)).length;
  return { ok: true as const, documents: docs, total: docs.length, ready };
}
