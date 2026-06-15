import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { diagnoseInfocapConnection } from '@/lib/attendance/connectors/infocap-policy-lookup';

export const dynamic = 'force-dynamic';

/**
 * GET /api/attendance/connectors/infocap/diagnostics
 *
 * Diagnóstico SEGURO da conexão InfoCap da corretora logada (isolado por
 * company_id). Confirma se o cadastro no Vault está pronto para o lookup real,
 * SEM expor login/senha/token/encrypted_secret_ref/CPF/payload.
 */
export async function GET(_request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Empresa não encontrada' }, { status: 404 });

    const diag = await diagnoseInfocapConnection(companyId);

    console.log(
      `[INFOCAP DIAGNOSTICS] company=${companyId} template=${diag.template_found} conn=${diag.tenant_connection_found} status=${diag.status} ready=${diag.ready_for_real_lookup}`,
    );

    return NextResponse.json({ ok: true, ...diag });
  } catch (error: any) {
    console.error('[INFOCAP DIAGNOSTICS] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
