// TA2-C — leituras read-only de Equipe e Conhecimento da corretora. Server-only.
// Sanitizado: nunca expõe hash, tokens, stripe, CPF ou IDs técnicos ao corretor.
import type { SupabaseClient } from '@supabase/supabase-js';

const ROLE_LABEL: Record<string, string> = {
  admin_company: 'Administrador', admin: 'Administrador', owner: 'Dono', member: 'Membro', master_admin: 'Master',
};

// SPEC-048: a equipe vem dos VÍNCULOS (company_members) — quem pertence a
// duas corretoras (donos) aparece nas duas; quem é de uma, só na sua. Papel e
// is_owner são os DO VÍNCULO desta empresa.
export async function getTeam(supabase: SupabaseClient, companyId: string) {
  const { data: mems } = await supabase.from('company_members')
    .select('user_id, role, is_owner, created_at')
    .eq('company_id', companyId).eq('status', 'active')
    .order('created_at', { ascending: true }).limit(500);
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
