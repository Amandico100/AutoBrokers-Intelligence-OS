import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

const SANDBOX_AGENT_SLUG = 'jarvys-sandbox';
const SANDBOX_MIN_BALANCE_BRL = 25;
const SANDBOX_AGENT_PROMPT =
  'Você é o JARVYS Sandbox, assistente interno da corretora. Responda de forma curta, clara e diga que ainda está em modo sandbox.';

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '',
  process.env.SUPABASE_SERVICE_ROLE_KEY || '',
  { auth: { persistSession: false } },
);

function toNumber(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * POST /api/admin/sandbox/bootstrap-tenant
 *
 * Idempotently prepares a sandbox tenant for the first chat smoke test:
 * - active direct-chat agent: JARVYS Sandbox
 * - minimum low-value sandbox credit balance
 */
export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const adminCookie = cookieStore.get('smith_admin_session');

    if (!adminCookie) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json().catch(() => ({}));
    const companyId = body.companyId;

    if (!companyId || typeof companyId !== 'string') {
      return NextResponse.json({ error: 'companyId is required' }, { status: 400 });
    }

    const { data: company, error: companyError } = await supabaseAdmin
      .from('companies')
      .select('id, company_name, status')
      .eq('id', companyId)
      .single();

    if (companyError || !company) {
      console.error('[SANDBOX BOOTSTRAP] Company lookup failed:', companyError?.message);
      return NextResponse.json({ error: 'Company not found' }, { status: 404 });
    }

    const actions: string[] = [];

    const { data: existingAgent, error: agentLookupError } = await supabaseAdmin
      .from('agents')
      .select('id, name, slug, is_active, llm_provider, llm_model')
      .eq('company_id', companyId)
      .eq('slug', SANDBOX_AGENT_SLUG)
      .maybeSingle();

    if (agentLookupError) {
      console.error('[SANDBOX BOOTSTRAP] Agent lookup failed:', agentLookupError.message);
      return NextResponse.json({ error: 'Error checking sandbox agent' }, { status: 500 });
    }

    const agentPayload = {
      company_id: companyId,
      name: 'JARVYS Sandbox',
      slug: SANDBOX_AGENT_SLUG,
      is_active: true,
      llm_provider: 'openai',
      llm_model: 'gpt-4o-mini',
      llm_temperature: 0.4,
      llm_max_tokens: 1200,
      llm_top_p: 1,
      llm_top_k: 40,
      llm_frequency_penalty: 0,
      llm_presence_penalty: 0,
      agent_system_prompt: SANDBOX_AGENT_PROMPT,
      agent_enabled: true,
      use_langchain: true,
      allow_web_search: false,
      allow_vision: false,
      is_hyde_enabled: false,
      tools_config: {},
      widget_config: {},
      security_settings: { enabled: false },
      reasoning_effort: 'low',
      verbosity: 'low',
      is_subagent: false,
      allow_direct_chat: true,
    };

    let agent = existingAgent;
    if (existingAgent?.id) {
      const { data, error } = await supabaseAdmin
        .from('agents')
        .update(agentPayload)
        .eq('id', existingAgent.id)
        .select('id, name, slug, is_active, llm_provider, llm_model')
        .single();

      if (error) {
        console.error('[SANDBOX BOOTSTRAP] Agent update failed:', error.message);
        return NextResponse.json({ error: 'Error updating sandbox agent' }, { status: 500 });
      }

      agent = data;
      actions.push('sandbox_agent_updated');
    } else {
      const { data, error } = await supabaseAdmin
        .from('agents')
        .insert(agentPayload)
        .select('id, name, slug, is_active, llm_provider, llm_model')
        .single();

      if (error) {
        console.error('[SANDBOX BOOTSTRAP] Agent insert failed:', error.message);
        return NextResponse.json({ error: 'Error creating sandbox agent' }, { status: 500 });
      }

      agent = data;
      actions.push('sandbox_agent_created');
    }

    const { data: existingCredits, error: creditsLookupError } = await supabaseAdmin
      .from('company_credits')
      .select('id, balance_brl')
      .eq('company_id', companyId)
      .maybeSingle();

    if (creditsLookupError) {
      console.error('[SANDBOX BOOTSTRAP] Credits lookup failed:', creditsLookupError.message);
      return NextResponse.json({ error: 'Error checking company credits' }, { status: 500 });
    }

    const currentBalance = toNumber(existingCredits?.balance_brl);
    const targetBalance = Math.max(currentBalance, SANDBOX_MIN_BALANCE_BRL);
    const topUpAmount = Number((targetBalance - currentBalance).toFixed(4));

    if (!existingCredits?.id || topUpAmount > 0) {
      const { data: credits, error: creditsError } = await supabaseAdmin
        .from('company_credits')
        .upsert(
          {
            company_id: companyId,
            balance_brl: targetBalance,
            alert_80_sent: false,
            alert_100_sent: false,
            updated_at: new Date().toISOString(),
          },
          { onConflict: 'company_id' },
        )
        .select('id, balance_brl')
        .single();

      if (creditsError) {
        console.error('[SANDBOX BOOTSTRAP] Credits upsert failed:', creditsError.message);
        return NextResponse.json({ error: 'Error configuring company credits' }, { status: 500 });
      }

      if (topUpAmount > 0) {
        const { error: transactionError } = await supabaseAdmin.from('credit_transactions').insert({
          company_id: companyId,
          agent_id: agent?.id || null,
          type: 'bonus',
          amount_brl: topUpAmount,
          balance_after: toNumber(credits.balance_brl),
          description: 'Sandbox bootstrap credit for first tenant chat smoke test',
        });

        if (transactionError) {
          console.error(
            '[SANDBOX BOOTSTRAP] Credit transaction insert failed:',
            transactionError.message,
          );
          return NextResponse.json({ error: 'Error recording sandbox credit transaction' }, { status: 500 });
        }
      }

      actions.push(topUpAmount > 0 ? 'sandbox_credits_topped_up' : 'sandbox_credits_created');
    } else {
      actions.push('sandbox_credits_already_sufficient');
    }

    return NextResponse.json({
      success: true,
      company: {
        id: company.id,
        name: company.company_name,
        status: company.status,
      },
      agent,
      credits: {
        previousBalanceBrl: currentBalance,
        balanceBrl: targetBalance,
        minimumBalanceBrl: SANDBOX_MIN_BALANCE_BRL,
        topUpAmountBrl: topUpAmount,
      },
      actions,
    });
  } catch (error: any) {
    console.error('[SANDBOX BOOTSTRAP] Unexpected error:', error?.message || error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
