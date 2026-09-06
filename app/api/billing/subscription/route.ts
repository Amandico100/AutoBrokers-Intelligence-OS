import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import {
  sessionOptions,
  adminSessionOptions,
  SessionData,
  AdminSessionData,
} from '@/lib/iron-session';
import { createClient } from '@supabase/supabase-js';
import { resolveSessionCompany } from '@/lib/auxiliaries/server';

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

export async function GET(request: NextRequest) {
  try {
    const companyId = await getCompanyIdFromSession();

    if (!companyId) {
      console.log('[Billing] No company_id found in session');
      return NextResponse.json({
        has_subscription: false,
        plan: null,
        balance_brl: 0,
        credits_display: { remaining: 0, used: 0, total: 0, percentage: 0 },
        usage: { agents: { used: 0, limit: 0 }, knowledge_bases: { used: 0, limit: 0 } },
        current_period_end: null,
      });
    }

    // ========================================
    // Busca direta no Supabase (sem Python backend)
    // A sessão já foi validada pelo Iron Session
    // ========================================

    // 1. Buscar subscription ativa ou past_due com dados do plano
    const { data: subscription, error: subError } = await supabaseAdmin
      .from('subscriptions')
      .select('*, plans(*)')
      .eq('company_id', companyId)
      .in('status', ['active', 'past_due'])
      .limit(1)
      .single();

    if (subError || !subscription) {
      return NextResponse.json({
        has_subscription: false,
        status: null,
        plan: null,
        balance_brl: 0,
        credits_display: { remaining: 0, used: 0, total: 0, percentage: 0 },
        usage: { agents: { used: 0, limit: 0 }, knowledge_bases: { used: 0, limit: 0 } },
        current_period_end: null,
      });
    }

    const plan = subscription.plans || {};

    // 2. Buscar saldo de créditos
    const { data: credits } = await supabaseAdmin
      .from('company_credits')
      .select('balance_brl')
      .eq('company_id', companyId)
      .single();

    const balanceBrl = parseFloat(credits?.balance_brl || '0');

    // 3. Calcular créditos proporcionais
    const planPrice = parseFloat(plan.price_brl || plan.monthly_price || '0');
    const displayCredits = plan.display_credits || plan.credits_limit || 0;

    let creditsPercentage = 0;
    let creditsRemaining = 0;
    let creditsUsed = 0;

    if (planPrice > 0) {
      creditsPercentage = (balanceBrl / planPrice) * 100;
      creditsRemaining = Math.floor((balanceBrl / planPrice) * displayCredits);
      creditsUsed = displayCredits - creditsRemaining;
    }

    // 4. Contar agentes ativos
    const { count: agentsUsed } = await supabaseAdmin
      .from('agents')
      .select('id', { count: 'exact', head: true })
      .eq('company_id', companyId)
      .eq('is_active', true);

    // 5. Contar documentos (bases de conhecimento)
    const { count: kbsUsed } = await supabaseAdmin
      .from('documents')
      .select('id', { count: 'exact', head: true })
      .eq('company_id', companyId);

    // 6. Limites do plano
    const maxAgents = plan.max_agents || 3;
    const maxKbs = plan.max_knowledge_bases || 5;

    // 7. Normalizar features
    let features = plan.features || [];
    if (Array.isArray(features) && features.length > 0 && typeof features[0] === 'string') {
      features = features.map((f: string) => ({ name: f, included: true }));
    }

    return NextResponse.json({
      has_subscription: true,
      status: subscription.status, // 'active' or 'past_due'
      plan: {
        id: plan.id,
        name: plan.name,
        price_brl: planPrice,
        display_credits: displayCredits,
        features: features,
      },
      balance_brl: balanceBrl,
      credits_display: {
        remaining: Math.max(0, creditsRemaining),
        used: Math.max(0, creditsUsed),
        total: displayCredits,
        percentage: Math.round(Math.min(100, Math.max(0, creditsPercentage)) * 10) / 10,
      },
      usage: {
        agents: { used: agentsUsed || 0, limit: maxAgents },
        knowledge_bases: { used: kbsUsed || 0, limit: maxKbs },
      },
      current_period_end: subscription.current_period_end,
      cancel_at: subscription.cancel_at,
    });
  } catch (error) {
    console.error('[Billing API] Error:', error);
    return NextResponse.json({
      has_subscription: false,
      status: null,
      plan: null,
      balance_brl: 0,
      credits_display: { remaining: 0, used: 0, total: 0, percentage: 0 },
      usage: { agents: { used: 0, limit: 0 }, knowledge_bases: { used: 0, limit: 0 } },
      current_period_end: null,
    });
  }
}
