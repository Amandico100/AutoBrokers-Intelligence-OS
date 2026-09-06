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

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

/**
 * 🔴 SPEC-098 · U4.b-Next — A COBRANÇA É DA EMPRESA ATIVA, NÃO DA PRIMÁRIA.
 *
 * 📊 Medido em 06/09/2026: as sete rotas de cobrança liam `users_v2.company_id`
 * — a empresa PRIMÁRIA — e ignoravam o seletor de empresa. Quem tem vínculo em
 * duas corretoras via, e ALTERAVA (troca de plano, portal do Stripe), a
 * assinatura da OUTRA. O erro não travava nada: respondia 200 com a fatura errada.
 *
 * `resolveSessionCompany` (lib/auxiliaries/server.ts) é O resolvedor: a empresa
 * ativa do seletor vence, revalidada em `company_members` a cada requisição —
 * vínculo revogado cai na hora. Sem sessão de corretora, cai no painel
 * administrativo, que continua como estava.
 */
async function getCompanyIdFromSession(): Promise<string | null> {
  try {
    const daSessao = await resolveSessionCompany();
    if (daSessao?.companyId) return daSessao.companyId;

    const cookieStore = await cookies();
    const adminSession = await getIronSession<AdminSessionData>(cookieStore, adminSessionOptions);
    if (adminSession.companyId) {
      return adminSession.companyId;
    }
    if (adminSession.adminId) {
      const { data } = await supabaseAdmin
        .from('users_v2')
        .select('company_id')
        .eq('id', adminSession.adminId)
        .single();
      if (data?.company_id) {
        return data.company_id;
      }
    }
    return null;
  } catch (error) {
    console.error('[Billing] Erro ao resolver a empresa da sessão:', error);
    return null;
  }
}

export async function POST(request: NextRequest) {
  try {
    const companyId = await getCompanyIdFromSession();

    if (!companyId) {
      return NextResponse.json(
        { detail: 'Não autorizado. Faça login novamente.' },
        { status: 401 },
      );
    }

    const body = await request.json();

    const response = await fetch(
      `${BACKEND_URL}/api/billing/preview-change?company_id=${companyId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error: any) {
    console.error('[PreviewChange API] Error:', error);
    return NextResponse.json({ detail: error.message || 'Erro interno' }, { status: 500 });
  }
}
