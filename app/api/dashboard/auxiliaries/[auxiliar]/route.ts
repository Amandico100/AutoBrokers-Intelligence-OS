// SPEC-013 B1 — lifecycle de Auxiliar da corretora: install / pause / resume / uninstall.
// Instalar cria runtime Smith ISOLADO no tenant (reusa o motor existente). Nada externo.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { installTenantAuxiliary, changeTenantAuxiliaryStatus } from '@/lib/admin/tenant-auxiliary-store';
import { getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

// O segmento chama-se `[auxiliar]` — e não `[templateId]` — porque o Next.js
// exige UM nome de parâmetro por posição, e a rota irmã `config/` identifica o
// Auxiliar por SLUG. Dois nomes na mesma posição não é preferência de estilo:
// derruba a montagem da tabela de rotas e o servidor inteiro passa a devolver
// 500 (02/08/2026 — o site ficou 1h40 fora do ar por causa disso).
//
// Cada handler renomeia localmente para o que ELE recebe, e o nome do segmento
// não mente sobre nenhum dos dois.
export async function POST(req: NextRequest, { params }: { params: Promise<{ auxiliar: string }> }) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const { auxiliar: templateId } = await params;
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const action = typeof body.action === 'string' ? body.action : 'install';

  if (action === 'install') {
    let backend: { url: string; apiKey: string } | undefined;
    const apiKey = process.env.ADMIN_API_KEY || process.env.BACKEND_INTERNAL_API_KEY || '';
    try { const url = getBackendUrl(req); if (url && apiKey) backend = { url, apiKey }; } catch { /* runtime fica awaiting */ }
    const out = await installTenantAuxiliary(auth.supabase, auth.ctx.companyId, templateId, auth.ctx.userId, backend);
    return NextResponse.json(out, { status: out.ok ? 200 : 400 });
  }
  if (action === 'pause' || action === 'resume' || action === 'uninstall') {
    const out = await changeTenantAuxiliaryStatus(auth.supabase, auth.ctx.companyId, templateId, action);
    return NextResponse.json(out, { status: out.ok ? 200 : 400 });
  }
  return NextResponse.json({ ok: false, error: 'acao_invalida' }, { status: 400 });
}
