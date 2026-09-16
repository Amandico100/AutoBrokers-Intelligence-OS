// SPEC-EXTRA-001.3 — BLOCO B · os números que o agente nunca atende.
//
// 🔴 **NASCE NO PADRÃO NOVO.** Uma rota criada nesta SPEC com o padrão velho
// (`resolveSessionCompany`, sem origem, sem auditoria) reprova o BLOCO G — a
// tranca não vale se a porta do lado nasce aberta.
//
// D-PILOTO-09 é lei: a lista mora no card **Equipe**, não no card Agente e não
// num card próprio (nota 88 × 62 × 71). ⛔ Não se reabre.
//
// GET    → { numeros: [...], membros: [...] }   — membros em modo LEITURA
// POST   → cria { phone, label, kind }
// DELETE → ?id=<uuid>
import { NextRequest, NextResponse } from 'next/server';

import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { porteiroDeConfiguracao, registrarNaAuditoria } from '@/lib/admin/porteiro-de-configuracao';

export const dynamic = 'force-dynamic';

const TABELA = 'company_internal_numbers';
const TIPOS = new Set(['fixo', 'comercial', 'socio', 'membro', 'outro']);

const digitos = (v: unknown) => String(v ?? '').replace(/\D/g, '');

/**
 * A máscara da exibição — o mesmo critério de `maskDestinationRef`.
 * ⚠️ A tela não é lugar de imprimir número inteiro sem necessidade.
 */
function mascarar(phone: string): string {
  const d = digitos(phone);
  if (d.length <= 4) return d;
  return `…${d.slice(-4)}`;
}

export async function GET() {
  // ⚠️ LER a lista não é privilégio administrativo: quem só confere precisa
  // ver. Escrever é que exige papel — e é por isso que o GET usa o resolvedor
  // simples e o POST/DELETE usam o porteiro.
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const { data: numeros } = await auth.supabase
    .from(TABELA)
    .select('id, phone, label, kind, created_at')
    .eq('company_id', auth.ctx.companyId) // 🔴 CLAUDE.md §7
    .order('created_at', { ascending: true })
    .limit(500);

  // Os telefones dos MEMBROS, em modo leitura, com a origem escrita.
  const { data: vinculos } = await auth.supabase
    .from('company_members')
    .select('user_id')
    .eq('company_id', auth.ctx.companyId)
    .eq('status', 'active')
    .limit(500);
  const ids = (vinculos || []).map((v: any) => String(v.user_id)).filter(Boolean);
  let membros: any[] = [];
  if (ids.length) {
    const { data: pessoas } = await auth.supabase
      .from('users_v2')
      .select('id, first_name, last_name, phone')
      .in('id', ids)
      .limit(500);
    membros = (pessoas || [])
      .filter((p: any) => digitos(p.phone))
      .map((p: any) => ({
        id: String(p.id),
        nome: [p.first_name, p.last_name].filter(Boolean).join(' ').trim(),
        phone_mascarado: mascarar(p.phone),
      }));
  }

  return NextResponse.json({
    ok: true,
    numeros: (numeros || []).map((n: any) => ({
      id: n.id,
      label: n.label,
      kind: n.kind,
      phone_mascarado: mascarar(n.phone),
    })),
    membros,
    can_manage: true,
  });
}

export async function POST(req: NextRequest) {
  const porteiro = await porteiroDeConfiguracao(req);
  if (porteiro instanceof NextResponse) return porteiro;

  const body = await req.json().catch(() => ({}));
  const phone = digitos((body as any).phone);
  const label = String((body as any).label || '').trim();
  const kind = TIPOS.has(String((body as any).kind)) ? String((body as any).kind) : 'outro';

  // ⚠️ 10 dígitos (DDD + 8) é o piso e 13 (55 + DDD + 9) é o teto. Fora disso
  // não é telefone brasileiro, e gravar lixo aqui calaria um segurado por
  // coincidência de dígitos.
  if (phone.length < 10 || phone.length > 13) {
    return NextResponse.json(
      { ok: false, error: 'Informe o número com DDD. Exemplo: 47 99999-0001.' },
      { status: 400 },
    );
  }
  if (!label) {
    return NextResponse.json(
      { ok: false, error: 'Dê um nome a este número — "fixo da loja", "comercial".' },
      { status: 400 },
    );
  }

  const { data, error } = await porteiro.supabase
    .from(TABELA)
    .insert({
      company_id: porteiro.companyId, // 🔴 nunca o `company_id` do corpo
      phone,
      label: label.slice(0, 80),
      kind,
      created_by: porteiro.userId,
    })
    .select('id, label, kind')
    .maybeSingle();

  if (error) {
    // 23505 = o índice único por (company_id, phone). ⚠️ Não é erro do sistema:
    // é a pessoa cadastrando duas vezes o mesmo número.
    if ((error as any).code === '23505') {
      return NextResponse.json(
        { ok: false, error: 'Este número já está na lista desta corretora.' },
        { status: 409 },
      );
    }
    console.error('[INTERNAL NUMBERS] create error:', error.message);
    return NextResponse.json({ ok: false, error: 'Não consegui salvar agora.' }, { status: 500 });
  }

  await registrarNaAuditoria(porteiro, {
    evento: 'company_internal_number.write',
    acao: 'create',
    // ⛔ nunca o número: só o rótulo e o tipo.
    metadata: { id: data?.id, kind, label: label.slice(0, 40) },
  });
  await invalidarCache(porteiro.companyId);

  return NextResponse.json({ ok: true, numero: data }, { status: 201 });
}

export async function DELETE(req: NextRequest) {
  const porteiro = await porteiroDeConfiguracao(req);
  if (porteiro instanceof NextResponse) return porteiro;

  const id = req.nextUrl.searchParams.get('id') || '';
  if (!id) return NextResponse.json({ ok: false, error: 'id ausente' }, { status: 400 });

  const { data, error } = await porteiro.supabase
    .from(TABELA)
    .delete()
    .eq('id', id)
    .eq('company_id', porteiro.companyId) // 🔴 CLAUDE.md §7 — o filtro é a proteção real
    .select('id')
    .maybeSingle();

  if (error) {
    console.error('[INTERNAL NUMBERS] delete error:', error.message);
    return NextResponse.json({ ok: false, error: 'Não consegui remover agora.' }, { status: 500 });
  }
  if (!data) return NextResponse.json({ ok: false, error: 'Número não encontrado' }, { status: 404 });

  await registrarNaAuditoria(porteiro, {
    evento: 'company_internal_number.write',
    acao: 'delete',
    metadata: { id },
  });
  await invalidarCache(porteiro.companyId);

  return NextResponse.json({ ok: true });
}

/**
 * O cache do backend tem TTL de 60 s; invalidar na escrita é o que faz a lista
 * valer na próxima mensagem em vez de no próximo minuto.
 *
 * ⛔ Best-effort: falhar em invalidar não pode desfazer um cadastro que já
 * aconteceu. O pior caso é a lista valer 60 s depois.
 */
async function invalidarCache(companyId: string): Promise<void> {
  try {
    const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
    if (!key) return;
    const { getBackendUrl } = await import('@/lib/backend-url');
    await fetch(
      `${getBackendUrl()}/api/atendimento/esquecer-numeros-da-casa?company_id=${encodeURIComponent(companyId)}`,
      { method: 'POST', headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
    );
  } catch (e) {
    console.warn('[INTERNAL NUMBERS] cache não invalidado', e);
  }
}
