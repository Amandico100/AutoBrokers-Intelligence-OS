import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { resolveSessionCompany } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

/**
 * GET /api/user/company-data
 *
 * Devolve a empresa ATIVA de quem está logado e as opções dela.
 *
 * 🔴 SPEC-098 · U4.b-Next (fecha P-096-COMPANY-DATA-IGNORA-ATIVA).
 *
 * 📊 Medido em 06/09/2026: esta rota lia `users_v2.company_id` — a empresa
 * PRIMÁRIA — e por isso continuava respondendo pela corretora antiga depois que
 * o corretor trocava de empresa no seletor. Quem consome esta resposta (o topo
 * da tela, o nome que aparece ao lado do usuário) mostrava um nome e a tela ao
 * lado mostrava outro.
 *
 * `resolveSessionCompany` é O resolvedor (lib/auxiliaries/server.ts): a ativa
 * vence e é revalidada em `company_members` a cada requisição.
 */
export async function GET(_request: NextRequest) {
  try {
    const sessao = await resolveSessionCompany();
    if (!sessao) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const supabaseAdmin = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      { auth: { persistSession: false } },
    );

    const { data: companyData, error: companyError } = await supabaseAdmin
      .from('companies')
      .select('id, company_name, allow_web_search')
      .eq('id', sessao.companyId)
      .single();

    if (companyError) {
      return NextResponse.json({ error: 'Erro ao buscar dados da empresa' }, { status: 500 });
    }

    return NextResponse.json({
      companyId: sessao.companyId,
      companyName: companyData?.company_name || null,
      allowWebSearch: companyData?.allow_web_search || false,
    });
  } catch (error: any) {
    console.error('[USER COMPANY DATA] Error:', error);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
