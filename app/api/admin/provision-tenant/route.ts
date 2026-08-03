// SPEC-063 Bloco P — a corretora nasce completa, e o global chega em quem já existe.
//
// Duas ações, no mesmo lugar de sempre (não há rota nova, não há segundo
// provisionador):
//
//   provisionar  (padrão)  garante agentes com prompt NÃO-VAZIO, config de
//                          memória, entitlements, perfis de briefing e confere
//                          o catálogo global. Idempotente; cura prompt vazio.
//
//   reaplicar              leva o blueprint global a uma corretora que já
//                          existe. Preenche o vazio; PRESERVA o que está
//                          preenchido. Sobrescrever exige `sobrescrever:true`
//                          E um `motivo` escrito — e mesmo assim só depois de
//                          o texto anterior estar versionado no banco.
//
// Master admin validado na fonte canônica (`admin_users`), same-origin.
import { NextRequest, NextResponse } from 'next/server';
import { provisionTenant, reaplicarBlueprintGlobal } from '@/lib/admin/provision-tenant';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const xo = assertSameOrigin(request);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  // TA2-C — master de plataforma validado na fonte canônica (admin_users), não só cookie.
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const supabase = auth.supabase;

  const body = await request.json().catch(() => ({}));
  const companyId = typeof body.companyId === 'string' ? body.companyId : (typeof body.company_id === 'string' ? body.company_id : '');
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });

  const { data: company } = await supabase.from('companies').select('id').eq('id', companyId).maybeSingle();
  if (!company?.id) return NextResponse.json({ ok: false, error: 'company_not_found' }, { status: 404 });

  const acao = typeof body.acao === 'string' ? body.acao : 'provisionar';

  if (acao === 'reaplicar') {
    const sobrescrever = body.sobrescrever === true;
    const motivo = typeof body.motivo === 'string' ? body.motivo.trim() : '';
    // "Nunca sobrescreve sem registro" começa aqui: sem motivo escrito, a
    // requisição é recusada ANTES de chegar perto do prompt de alguém.
    if (sobrescrever && motivo.length < 8) {
      return NextResponse.json(
        { ok: false, error: 'motivo_obrigatorio_para_sobrescrever', detail: 'Escreva por que o texto local está sendo substituído (mín. 8 caracteres).' },
        { status: 400 },
      );
    }
    const result = await reaplicarBlueprintGlobal(supabase, companyId, { sobrescrever, motivo: motivo || undefined });
    return NextResponse.json({ ...result, acao, real_action_allowed: false });
  }

  if (acao !== 'provisionar') {
    return NextResponse.json({ ok: false, error: 'acao_invalida', detail: "use 'provisionar' ou 'reaplicar'" }, { status: 400 });
  }

  const result = await provisionTenant(supabase, companyId);
  // 409 quando o provisionamento não fechou: o chamador não pode confundir
  // "respondeu 200" com "a corretora está completa".
  return NextResponse.json({ ...result, acao, real_action_allowed: false }, { status: result.ok ? 200 : 409 });
}
