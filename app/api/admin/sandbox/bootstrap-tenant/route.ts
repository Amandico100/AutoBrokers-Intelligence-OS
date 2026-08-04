import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createClient } from '@supabase/supabase-js';
import { conferirPromptGravado } from '@/lib/admin/provision-tenant';

export const dynamic = 'force-dynamic';

const SANDBOX_AGENT_SLUG = 'autobrokers-sandbox';
const SANDBOX_MIN_BALANCE_BRL = 25;
const SANDBOX_AGENT_PROMPT =
  'Você é o AutoBrokers Sandbox, copiloto operacional interno da corretora. Responda de forma curta, clara e diga que ainda está em modo sandbox.';

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
 * - active direct-chat agent: AutoBrokers Sandbox
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

    // Tenant Activation 1: NÃO-DESTRUTIVO. Se já existe um Core canônico
    // (agent_role='core'), NUNCA sobrescrever com o agente Sandbox.
    const { data: existingCore } = await supabaseAdmin
      .from('agents')
      .select('id, name')
      .eq('company_id', companyId)
      .eq('agent_role', 'core')
      .limit(1)
      .maybeSingle();

    if (existingCore?.id) {
      actions.push('core_exists_skip_sandbox');
      return NextResponse.json({
        success: true,
        company: { id: company.id, name: company.company_name, status: company.status },
        agent: existingCore,
        note: 'Core canônico já existe; bootstrap sandbox não sobrescreve. Use /api/admin/provision-tenant.',
        actions,
      });
    }

    const { data: existingAgent, error: agentLookupError } = await supabaseAdmin
      .from('agents')
      .select('id, name, slug, is_active, llm_provider, llm_model, agent_role, agent_system_prompt')
      .eq('company_id', companyId)
      .eq('slug', SANDBOX_AGENT_SLUG)
      .maybeSingle();

    if (agentLookupError) {
      console.error('[SANDBOX BOOTSTRAP] Agent lookup failed:', agentLookupError.message);
      return NextResponse.json({ error: 'Error checking sandbox agent' }, { status: 500 });
    }

    const agentPayload = {
      company_id: companyId,
      name: 'AutoBrokers Sandbox',
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

    // O prompt é USADO aqui e NUNCA sai na resposta (CLAUDE.md §13.3: presença
    // e medida, jamais o conteúdo). Por isso a ficha que viaja é esta forma,
    // sem a coluna de texto.
    type FichaDoAgente = {
      id: string; name: string | null; slug: string | null; is_active: boolean | null;
      llm_provider: string | null; llm_model: string | null; agent_role: string | null;
    };
    const semTexto = (linha: Record<string, unknown> | null): FichaDoAgente | null => {
      if (!linha) return null;
      const { agent_system_prompt: _texto, ...ficha } = linha;
      return ficha as FichaDoAgente;
    };
    const SELECT_FICHA = 'id, name, slug, is_active, llm_provider, llm_model, agent_role, agent_system_prompt';

    /**
     * A releitura pós-escrita, nas DUAS pernas — e ela é a MESMA de todo mundo.
     *
     * A primeira versão deste conserto reimplementou a checagem aqui dentro
     * (`gravado.trim()` + um update de desligamento). Passava nos testes e era
     * um SEGUNDO portão (CLAUDE.md §5): media `.trim()`, enquanto o portão de
     * verdade mede `estadoDaVoz` — que também reprova a casca de guardrails,
     * ~560 caracteres de moldura sem uma instrução dentro. Dois portões que
     * medem coisas diferentes são pior que um portão só, porque cada lado passa
     * a acreditar no seu.
     *
     * `conferirPromptGravado` relê do banco e desliga. Devolve a resposta de
     * erro quando desligou, ou `null` quando está tudo certo.
     */
    const desligarSeFicouMudo = async (agentId: string) => {
      const conferido = await conferirPromptGravado(
        supabaseAdmin, companyId, agentId, 'sandbox_bootstrap',
      );
      if (conferido.ok) return null;
      return NextResponse.json(
        { error: conferido.reason ?? 'prompt_vazio_apos_escrita' },
        { status: 500 },
      );
    };

    let agent: FichaDoAgente | null = semTexto(existingAgent as Record<string, unknown> | null);
    if (existingAgent?.id) {
      // P-38 — REPROVISIONAR NÃO PODE APAGAR TEXTO DE GENTE.
      //
      // Esta rota casava por SLUG e mandava o `agentPayload` inteiro por cima,
      // inclusive `agent_system_prompt: SANDBOX_AGENT_PROMPT` — 145 caracteres
      // que dizem "ainda estou em modo sandbox". Se alguém tivesse escrito um
      // prompt de verdade neste agente (ou se uma release tivesse descido nele),
      // rodar o bootstrap de novo o substituía por essa frase, em silêncio.
      //
      // A mesma regra dura da herança em `provision-tenant.ts`:
      //     preenche o que está VAZIO · não toca no que está PREENCHIDO
      //
      // O resto do payload continua sendo reaplicado — é disso que o bootstrap
      // vive (modelo, limites, canais). O que passa a ser intocável é a VOZ.
      const promptAtual = String(
        (existingAgent as { agent_system_prompt?: string | null }).agent_system_prompt ?? '',
      );
      const { agent_system_prompt: promptDoSandbox, ...semPrompt } = agentPayload;
      const patch: Record<string, unknown> = promptAtual.trim()
        ? semPrompt
        : { ...semPrompt, agent_system_prompt: promptDoSandbox };
      if (promptAtual.trim()) actions.push('sandbox_prompt_preservado');

      const { data, error } = await supabaseAdmin
        .from('agents')
        .update(patch)
        .eq('id', existingAgent.id)
        .eq('company_id', companyId)
        .select(SELECT_FICHA)
        .single();

      if (error) {
        console.error('[SANDBOX BOOTSTRAP] Agent update failed:', error.message);
        return NextResponse.json({ error: 'Error updating sandbox agent' }, { status: 500 });
      }

      const desligado = await desligarSeFicouMudo(existingAgent.id);
      if (desligado) return desligado;

      agent = semTexto(data as Record<string, unknown>);
      actions.push('sandbox_agent_updated');
    } else {
      const { data, error } = await supabaseAdmin
        .from('agents')
        .insert(agentPayload)
        .select(SELECT_FICHA)
        .single();

      if (error) {
        console.error('[SANDBOX BOOTSTRAP] Agent insert failed:', error.message);
        return NextResponse.json({ error: 'Error creating sandbox agent' }, { status: 500 });
      }

      const desligado = await desligarSeFicouMudo(String((data as { id: string }).id));
      if (desligado) return desligado;

      agent = semTexto(data as Record<string, unknown>);
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
