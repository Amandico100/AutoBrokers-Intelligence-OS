// TA2-C — leituras read-only de Equipe e Conhecimento da corretora. Server-only.
// Sanitizado: nunca expõe hash, tokens, stripe, CPF ou IDs técnicos ao corretor.
import type { SupabaseClient } from '@supabase/supabase-js';

const ROLE_LABEL: Record<string, string> = {
  admin_company: 'Administrador', admin: 'Administrador', owner: 'Dono', member: 'Membro', master_admin: 'Master',
};

export async function getTeam(supabase: SupabaseClient, companyId: string) {
  const { data } = await supabase.from('users_v2')
    .select('first_name, last_name, email, role, is_owner, status, last_login_at')
    .eq('company_id', companyId).is('deleted_at', null).order('created_at', { ascending: true }).limit(500);
  const members = (data ?? []).map((u: any) => ({
    name: [u.first_name, u.last_name].filter(Boolean).join(' ').trim() || (u.email ?? 'Sem nome'),
    email: u.email ?? null,
    role_label: ROLE_LABEL[u.role] ?? (u.role ?? 'Membro'),
    is_owner: Boolean(u.is_owner),
    status: u.status ?? null,
    last_login_at: u.last_login_at ?? null,
  }));
  return { ok: true as const, members, total: members.length };
}

export async function getKnowledge(supabase: SupabaseClient, companyId: string) {
  const { data } = await supabase.from('documents')
    .select('file_name, file_type, status, scope, knowledge_class, visibility, chunks_count, created_at')
    .eq('company_id', companyId).order('created_at', { ascending: false }).limit(500);
  const docs = (data ?? []).map((d: any) => ({
    file_name: d.file_name ?? 'Documento',
    file_type: d.file_type ?? null,
    status: d.status ?? 'desconhecido',
    scope: d.scope ?? 'private',
    knowledge_class: d.knowledge_class ?? null,
    visibility: d.visibility ?? null,
    chunks: d.chunks_count ?? 0,
    created_at: d.created_at ?? null,
  }));
  const ready = docs.filter((d) => /ready|done|completed|processed|ingested/i.test(d.status)).length;
  return { ok: true as const, documents: docs, total: docs.length, ready };
}
