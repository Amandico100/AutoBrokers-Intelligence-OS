/**
 * Sanitization Proxy - List Jobs
 *
 * GET /api/sanitization/jobs?company_id=xxx
 * Validates iron-session, then fetches jobs from Python backend.
 */
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import {
    adminSessionOptions,
    AdminSessionData,
    sessionOptions,
    SessionData,
} from '@/lib/iron-session';
import { createClient } from '@supabase/supabase-js';
import { resolveSessionCompany } from '@/lib/auxiliaries/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
);

/**
 * 🔴 SPEC-098 · U4.a — o FastAPI passa a EXIGIR a chave interna nestas rotas.
 *
 * 📊 Medido em 06/09/2026: `GET …/api/sanitization/jobs?company_id=<uuid falso>`
 * respondia **200** direto na internet. O comentário do backend dizia
 * "company_id is provided by the Next.js proxy" e nada verificava que quem
 * chamava era o proxy. Esta proxy autentica a sessão (já autenticava) e agora
 * também se identifica: quem fala é o nosso servidor, não o navegador.
 */
function chaveInterna(): string {
    return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
}

async function resolveCompanyId(frontendCompanyId?: string | null): Promise<string | null> {
    try {
        const cookieStore = await cookies();

        const adminSession = await getIronSession<AdminSessionData>(cookieStore, adminSessionOptions);
        if (adminSession.adminId) {
            if (adminSession.role === 'master_admin') {
                if (frontendCompanyId) return frontendCompanyId;
                if (adminSession.companyId) return adminSession.companyId;
                return null;
            }
            if (adminSession.companyId) return adminSession.companyId;
            const { data } = await supabaseAdmin
                .from('users_v2')
                .select('company_id')
                .eq('id', adminSession.adminId)
                .single();
            if (data?.company_id) return data.company_id;
        }

        // 🔴 SPEC-098 · U4.b-Next — a empresa ATIVA vence a primária.
        // `resolveSessionCompany` revalida o vínculo em `company_members` a cada
        // requisição; `userSession.companyId` era o do login, congelado.
        const daSessao = await resolveSessionCompany();
        if (daSessao?.companyId) return daSessao.companyId;

        return null;
    } catch (error) {
        console.error('[Sanitization Jobs] Error resolving company_id:', error);
        return null;
    }
}

export async function GET(request: NextRequest) {
    try {
        const frontendCompanyId = request.nextUrl.searchParams.get('company_id');
        const companyId = await resolveCompanyId(frontendCompanyId);

        if (!companyId) {
            return NextResponse.json(
                { detail: 'Authentication required. Please log in.' },
                { status: 401 },
            );
        }

        const response = await fetch(
            `${BACKEND_URL}/api/sanitization/jobs?company_id=${companyId}`,
            { headers: { 'X-Internal-Key': chaveInterna() }, cache: 'no-store' },
        );

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        return NextResponse.json(data);
    } catch (error: any) {
        console.error('[Sanitization Jobs API] Error:', error);
        return NextResponse.json(
            { detail: error.message || 'Erro interno' },
            { status: 500 },
        );
    }
}
