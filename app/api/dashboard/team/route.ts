// TA2-C / SPEC-048 — equipe da corretora ATIVA, gerida pelo próprio dono/admin
// no dashboard (sem portal admin, sem confirmação de e-mail).
// GET: membros (via company_members). POST: adicionar. PATCH: editar.
// DELETE: remover o vínculo. Escritas exigem papel administrativo DA empresa
// ativa; um membro comum só enxerga a lista.
// SPEC-131-0 A · F1: `funcoes` (comercial · calculista · negociador) no GET/POST/PATCH; o PATCH de papel espelha em
// `users_v2.role` quando esta é a empresa primária; o DELETE desliga o Agger pessoal pelo backend.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { canWriteTenantConfig, lerFuncoes, papelNoCadastroLegado, papelQueAEquipeDa } from '@/lib/admin/admin-auth-policy';
import { getTeam } from '@/lib/admin/tenant-overview-store';
import { hashPassword } from '@/lib/auth';
import { randomBytes } from 'crypto';
import { recusaDaSenhaDoMembro } from '@/lib/admin/senha-do-membro';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

// 🔴 `attendant` ENTRA NA LISTA DE PAPÉIS, senão a permissão da SPEC-093 não tem
// como ser concedida a ninguém.
//
// 📊 Achado em 26/08/2026: o BLOCO A da SPEC-093 criou o papel na política de
// autorização (`admin-auth-policy.ts`) — o papel que liga o agente de
// atendimento **e mais nada**. Mas a lista desta rota tinha só dois valores, e
// um papel fora dela virava `member` **em silêncio**.
//
// 🔴 É a §9.3 numa forma nova: não é um guarda que falha, é uma permissão que
// ninguém consegue dar. A capacidade existia e era inalcançável.
//
// 🔴 SPEC-131-0 A · F1 — a lista mora numa fonte só: `PAPEIS_QUE_A_EQUIPE_DA` ⊂ `PAPEIS_DE_ACESSO` (na política, a
// mesma do CHECK `ck_company_members_role`), lida por `papelQueAEquipeDa`. Papel desconhecido agora é RECUSADO
// (400), nunca trocado calado. As FUNÇÕES (`FUNCOES_DE_TRABALHO`, lidas por `lerFuncoes`) idem — e não dão acesso.
const PAPEL_INVALIDO = 'Papel desconhecido. Os papéis são Administrador, Membro e Atendente.';

const digits = (v: unknown) => String(v || '').replace(/\D/g, '');

function backendHeaders(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

/**
 * SPEC-131-0 A · F1 × F3 (§5.2) — quem sai da equipe tem o Agger PESSOAL desligado (pausa + a senha apagada) pelo
 * ÚNICO escritor, `conta_do_robo.desligar_do_membro`, atrás do endpoint interno do backend. ⛔ Esta rota NUNCA
 * escreve a tabela das contas de portal. Se a chamada falhar, o vínculo já saiu e a conta já é inelegível (o motor
 * reconfere o vínculo ativo); a resposta diz `agger_pendente: true` para a tela avisar.
 */
async function desligarAggerDoMembro(companyId: string, userId: string): Promise<boolean> {
  try {
    const res = await fetch(`${getBackendUrl()}/api/portal/aggers-da-equipe/desligar-membro`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({ company_id: companyId, user_id: userId }),
      signal: AbortSignal.timeout(10_000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getTeam(auth.supabase, auth.ctx.companyId);
  return NextResponse.json({
    ...out,
    can_manage: canWriteTenantConfig({ role: auth.ctx.role, isOwner: auth.ctx.isOwner }),
    me: auth.ctx.userId,
  });
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));

  const email = String(body.email || '').trim().toLowerCase();
  const firstName = String(body.first_name || '').trim();
  const lastName = String(body.last_name || '').trim();
  const phone = digits(body.phone);
  // sem papel no pedido = Membro; papel desconhecido = 400 (nunca troca calada)
  const role = body.role == null || body.role === '' ? 'member' : papelQueAEquipeDa(body.role);
  if (!role) return NextResponse.json({ ok: false, error: PAPEL_INVALIDO }, { status: 400 });
  const lidas = body.funcoes == null ? { ok: true as const, funcoes: [] } : lerFuncoes(body.funcoes);
  if (!lidas.ok) return NextResponse.json({ ok: false, error: lidas.erro }, { status: 400 });
  // 🔴 SPEC-133-A.1: nunca mais uma senha padrão conhecida ("mudar123"); sem senha no pedido → aleatória, devolvida UMA vez
  const senhaGerada = !body.password;
  const password = String(body.password || randomBytes(12).toString('base64url'));
  if (!email || !email.includes('@')) return NextResponse.json({ ok: false, error: 'E-mail inválido.' }, { status: 400 });
  if (!firstName) return NextResponse.json({ ok: false, error: 'Informe o nome.' }, { status: 400 });
  // 🔴 conserto 133-A.1 (juiz P3-4): nunca "mudar123", mínimo 10 — a MESMA regra do PATCH
  const recusa = recusaDaSenhaDoMembro(password);
  if (recusa) return NextResponse.json({ ok: false, error: recusa }, { status: 400 });

  const supabase = auth.supabase;
  const { data: existing } = await supabase.from('users_v2')
    .select('id, company_id').eq('email', email).is('deleted_at', null).maybeSingle();

  let userId = existing?.id as string | undefined;
  if (userId) {
    // ⚠️ quem JÁ está na equipe não é "adicionado" de novo: o upsert abaixo reescreveria papel e is_owner do vínculo
    // (um administrador rebaixaria o dono re-adicionando o e-mail dele). Editar é pelo PATCH.
    const { data: jaNaEquipe } = await supabase.from('company_members')
      .select('id').eq('user_id', userId).eq('company_id', auth.ctx.companyId).eq('status', 'active').maybeSingle();
    if (jaNaEquipe) {
      return NextResponse.json({ ok: false, error: 'Essa pessoa já está na equipe — abra o nome dela para editar.' }, { status: 409 });
    }
  }
  if (!userId) {
    // Usuário novo: nasce com esta empresa como primária. CPF placeholder único
    // (o membro completa depois em Configurações); sem confirmação de e-mail.
    const cpfPlaceholder = `p${Date.now().toString().slice(-12)}`;
    const { data: created, error } = await supabase.from('users_v2').insert({
      email,
      password_hash: await hashPassword(password),
      first_name: firstName,
      last_name: lastName || '',
      cpf: cpfPlaceholder,
      phone: phone || '0',
      birth_date: '1990-01-01',
      company_id: auth.ctx.companyId,
      status: 'active',
      // espelho legado: o banco só aceita admin_company|member em users_v2.role (`users_v2_role_check`) — `attendant`
      // vira `member`. 📊 Antes, adicionar uma Atendente nova batia nesse CHECK e devolvia 500.
      role: papelNoCadastroLegado(role),
      is_owner: false,
      terms_accepted_at: new Date().toISOString(),
      privacy_policy_accepted_at: new Date().toISOString(),
    }).select('id').single();
    if (error || !created?.id) {
      console.error('[TEAM] create user error:', error?.message);
      return NextResponse.json({ ok: false, error: 'Não foi possível criar o usuário.' }, { status: 500 });
    }
    userId = created.id;
  }

  const { error: memberErr } = await supabase.from('company_members').upsert(
    { user_id: userId, company_id: auth.ctx.companyId, role, is_owner: false, status: 'active', funcoes: lidas.funcoes },
    { onConflict: 'user_id,company_id' },
  );
  if (memberErr) {
    console.error('[TEAM] membership error:', memberErr.message);
    return NextResponse.json({ ok: false, error: 'Não foi possível vincular à empresa.' }, { status: 500 });
  }
  return NextResponse.json({ ok: true, user_id: userId, existed: Boolean(existing),
    ...(senhaGerada && !existing ? { senha_provisoria: password } : {}) });
}

export async function PATCH(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const userId = String(body.user_id || '').trim();
  if (!userId) return NextResponse.json({ ok: false, error: 'user_id obrigatório' }, { status: 400 });
  const supabase = auth.supabase;

  const { data: member } = await supabase.from('company_members')
    .select('id, role, is_owner').eq('user_id', userId)
    .eq('company_id', auth.ctx.companyId).eq('status', 'active').maybeSingle();
  if (!member) return NextResponse.json({ ok: false, error: 'Membro não encontrado nesta empresa.' }, { status: 404 });
  // Dono só é editado por outro dono (nunca rebaixado por um gestor).
  if (member.is_owner && !auth.ctx.isOwner) {
    return NextResponse.json({ ok: false, error: 'Só o dono pode editar outro dono.' }, { status: 403 });
  }
  // valida TUDO antes de gravar qualquer coisa: um pedido com papel ou função errados não salva nada pela metade
  // (o papel que a pessoa JÁ tem volta igual da tela — inclusive o do dono, que a tela não deixa trocar)
  const pedePapel = body.role != null && body.role !== member.role;
  const novoPapel = pedePapel ? papelQueAEquipeDa(body.role) : null;
  if (pedePapel && !novoPapel) return NextResponse.json({ ok: false, error: PAPEL_INVALIDO }, { status: 400 });
  const lidas = body.funcoes == null ? null : lerFuncoes(body.funcoes);
  if (lidas && !lidas.ok) return NextResponse.json({ ok: false, error: lidas.erro }, { status: 400 });

  const userUpd: Record<string, unknown> = {};
  if (typeof body.first_name === 'string' && body.first_name.trim()) userUpd.first_name = body.first_name.trim();
  if (typeof body.last_name === 'string') userUpd.last_name = body.last_name.trim();
  if (body.phone != null) userUpd.phone = digits(body.phone) || '0';
  if (typeof body.password === 'string' && body.password) {
    const recusa = recusaDaSenhaDoMembro(body.password);
    if (recusa) return NextResponse.json({ ok: false, error: recusa }, { status: 400 });
    userUpd.password_hash = await hashPassword(body.password);
  }
  if (Object.keys(userUpd).length) {
    userUpd.updated_at = new Date().toISOString();
    const { error } = await supabase.from('users_v2').update(userUpd).eq('id', userId);
    if (error) return NextResponse.json({ ok: false, error: 'Não foi possível atualizar os dados.' }, { status: 500 });
  }

  const vinculoUpd: Record<string, unknown> = {};
  const mudaPapel = Boolean(novoPapel && novoPapel !== member.role && !member.is_owner);
  if (mudaPapel) vinculoUpd.role = novoPapel;
  if (lidas && lidas.ok) vinculoUpd.funcoes = lidas.funcoes;
  if (Object.keys(vinculoUpd).length) {
    // 🔴 o vínculo é a ÚNICA fonte do papel (`requireCompanyMember` lê só ele) — sempre filtrado pela corretora da sessão
    const { error } = await supabase.from('company_members').update(vinculoUpd)
      .eq('id', member.id).eq('company_id', auth.ctx.companyId);
    if (error) return NextResponse.json({ ok: false, error: 'Não foi possível salvar o papel ou as funções.' }, { status: 500 });
  }
  if (mudaPapel) {
    // cinto e suspensório: o espelho legado `users_v2.role` acompanha — mas SÓ quando esta corretora é a primária da
    // pessoa. O filtro `company_id` está NA escrita: se a primária for outra, nada muda lá.
    const { error } = await supabase.from('users_v2')
      .update({ role: papelNoCadastroLegado(novoPapel), updated_at: new Date().toISOString() })
      .eq('id', userId).eq('company_id', auth.ctx.companyId);
    if (error) console.error('[TEAM] espelho do papel em users_v2 falhou:', error.message);
  }
  return NextResponse.json({ ok: true });
}

export async function DELETE(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const userId = String(body.user_id || '').trim();
  if (!userId) return NextResponse.json({ ok: false, error: 'user_id obrigatório' }, { status: 400 });
  if (userId === auth.ctx.userId) {
    return NextResponse.json({ ok: false, error: 'Você não pode remover a si mesmo.' }, { status: 400 });
  }
  const supabase = auth.supabase;
  const { data: member } = await supabase.from('company_members')
    .select('id, is_owner').eq('user_id', userId)
    .eq('company_id', auth.ctx.companyId).eq('status', 'active').maybeSingle();
  if (!member) return NextResponse.json({ ok: false, error: 'Membro não encontrado nesta empresa.' }, { status: 404 });
  if (member.is_owner) {
    return NextResponse.json({ ok: false, error: 'Donos não podem ser removidos por aqui.' }, { status: 403 });
  }
  // Remove o VÍNCULO com esta empresa — a conta continua existindo (a pessoa
  // pode pertencer a outra corretora).
  const { error } = await supabase.from('company_members').delete().eq('id', member.id).eq('company_id', auth.ctx.companyId);
  if (error) return NextResponse.json({ ok: false, error: 'Não foi possível remover.' }, { status: 500 });
  // o Agger PESSOAL dela NESTA corretora é desligado pelo backend (F3); falhou → o vínculo já saiu mesmo assim
  const desligou = await desligarAggerDoMembro(auth.ctx.companyId, userId);
  return NextResponse.json({ ok: true, agger_pendente: !desligou });
}
