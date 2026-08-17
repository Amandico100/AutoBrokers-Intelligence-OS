import { NextRequest, NextResponse } from 'next/server';

import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { getSupabaseAdmin, resolveSessionCompany } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

const BACKEND_TIMEOUT_MS = 20_000;
const PURPOSE = 'observer';
const PROVIDER = 'evolution-go';

/**
 * SPEC-078 Bloco B — o que ESTE número faz, dito em português de corretor.
 *
 * 🔴 Por que o texto mora aqui e não na tela: o número pareado acumula três
 * papéis que se parecem e não são a mesma coisa, e a tela de conectores só
 * mostrava um deles. O corretor via "Observando em silêncio" e concluía, com
 * razão, que aquele WhatsApp não servia para mais nada — enquanto a cobrança
 * dele não saía por falta exatamente desse número.
 *
 * Os três papéis, e o que liga cada um:
 *   observar   ligado desde o pareamento, sempre mudo (não tem botão)
 *   enviar     só com autorização explícita aqui       (`permite_envio_de_auxiliar`)
 *   responder  outro botão, outro lugar                (Agente de Atendimento)
 *
 * Quem consome: `components/vault/WhatsAppChannelCard.tsx` (e, por ele,
 * `app/dashboard/personalizacao/conectores/page.tsx`). O parágrafo pronto vai
 * em `resumo` para a tela que só quer exibir o texto; os três itens vão
 * separados para a que quer desenhar o interruptor.
 */
const RESUMO_DOS_PAPEIS =
  'Este número observa as conversas e aprende (não responde sozinho). ' +
  'Autorize aqui se você também quer que seus Auxiliares — cobrança, ' +
  'relatórios — enviem por ele. Para ele RESPONDER os segurados, é outro ' +
  'botão: Ligar Agente de Atendimento.';

const PAPEIS_DO_NUMERO = {
  observa: {
    ativo: true,
    titulo: 'Observa e aprende',
    texto: 'Este número observa as conversas e aprende. Ele não responde sozinho.',
  },
  envia: {
    // `ativo` é preenchido em tempo de leitura com o valor real da coluna.
    ativo: false,
    titulo: 'Envia pelos seus Auxiliares',
    texto:
      'Autorize aqui se você também quer que seus Auxiliares — cobrança, ' +
      'relatórios — enviem por ele.',
    acao: 'set-auxiliary-authorization',
  },
  responde: {
    ativo: false,
    titulo: 'Responde os segurados',
    texto:
      'Para ele RESPONDER os segurados, é outro botão: Ligar Agente de Atendimento.',
  },
} as const;

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

function correlationId(req: NextRequest): string {
  return req.headers.get('X-Correlation-ID') || crypto.randomUUID();
}

async function backendRequest(
  path: string,
  key: string,
  correlation: string,
  init: RequestInit = {},
): Promise<NextResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BACKEND_TIMEOUT_MS);
  try {
    const backend = getBackendUrl();
    const res = await fetch(`${backend}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-AutoBrokers-Internal-Key': key,
        'X-Correlation-ID': correlation,
        ...(init.headers || {}),
      },
      cache: 'no-store',
      signal: controller.signal,
    });
    const json = await res.json().catch(() => ({ detail: `backend_http_${res.status}` }));
    return NextResponse.json(json, {
      status: res.status,
      headers: { 'X-Correlation-ID': correlation },
    });
  } catch (error) {
    if (error instanceof BackendUrlError) {
      return NextResponse.json(
        { detail: 'backend_not_configured', correlation_id: correlation },
        { status: 500, headers: { 'X-Correlation-ID': correlation } },
      );
    }
    if ((error as { name?: string })?.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'backend_timed_out', correlation_id: correlation },
        { status: 504, headers: { 'X-Correlation-ID': correlation } },
      );
    }
    return NextResponse.json(
      { detail: 'backend_unavailable', correlation_id: correlation },
      { status: 502, headers: { 'X-Correlation-ID': correlation } },
    );
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Lê os dois interruptores que a tela precisa mostrar, direto do banco.
 *
 * Filtro por `company_id` explícito em toda query — o service role ignora RLS,
 * então quem separa as corretoras é este filtro (CLAUDE.md §7).
 *
 * Nunca lança: se a leitura falhar (inclusive coluna ainda inexistente, na
 * janela entre o deploy e o APPLY da migration 20260817_02), devolve os dois
 * como `false`. Fail-closed — a tela dizer "não autorizado" quando não sabe é
 * melhor que dizer "autorizado" sobre um número que talvez não esteja.
 */
async function lerPapeis(companyId: string): Promise<{ envia: boolean; responde: boolean }> {
  const resultado = { envia: false, responde: false };
  try {
    const supabase = getSupabaseAdmin();
    const { data: integ } = await supabase
      .from('integrations')
      .select('permite_envio_de_auxiliar')
      .eq('company_id', companyId)
      .eq('provider', PROVIDER)
      .eq('purpose', PURPOSE)
      .eq('is_active', true)
      .limit(1)
      .maybeSingle();
    resultado.envia = integ?.permite_envio_de_auxiliar === true;

    const { data: agente } = await supabase
      .from('agents')
      .select('is_active')
      .eq('company_id', companyId)
      .eq('agent_role', 'attendance')
      .order('created_at')
      .limit(1)
      .maybeSingle();
    resultado.responde = agente?.is_active === true;
  } catch {
    // silêncio proposital: ver docstring.
  }
  return resultado;
}

/**
 * Acrescenta os três papéis ao corpo que o backend devolveu.
 *
 * O backend responde sobre o CANAL (pareado? conectado? qual número?). Os
 * papéis são leitura do banco do produto, não do provedor — por isso a junção
 * acontece aqui, na borda, em vez de virar campo novo numa rota de
 * infraestrutura que não sabe o que é um Auxiliar.
 */
async function comPapeis(resposta: NextResponse, companyId: string): Promise<NextResponse> {
  if (resposta.status >= 400) return resposta;
  let corpo: Record<string, unknown>;
  try {
    corpo = (await resposta.clone().json()) as Record<string, unknown>;
  } catch {
    return resposta;
  }
  const estado = await lerPapeis(companyId);
  const papeis = {
    resumo: RESUMO_DOS_PAPEIS,
    observa: { ...PAPEIS_DO_NUMERO.observa },
    envia: { ...PAPEIS_DO_NUMERO.envia, ativo: estado.envia },
    responde: { ...PAPEIS_DO_NUMERO.responde, ativo: estado.responde },
  };
  // Só o correlation id é repassado. Herdar o `headers` inteiro traria de volta
  // o `content-length` do corpo ANTERIOR — e o corpo acabou de crescer.
  const correlation = resposta.headers.get('X-Correlation-ID');
  return NextResponse.json(
    { ...corpo, papeis, permite_envio_de_auxiliar: estado.envia },
    {
      status: resposta.status,
      headers: correlation ? { 'X-Correlation-ID': correlation } : undefined,
    },
  );
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });
  const key = internalKey();
  if (!key) return NextResponse.json({ detail: 'internal_key_not_configured' }, { status: 500 });

  const correlation = correlationId(req);
  const action = req.nextUrl.searchParams.get('action') || 'status';
  const attemptId = req.nextUrl.searchParams.get('attempt_id');
  const company = encodeURIComponent(ctx.companyId);

  if (action === 'pairing' && attemptId) {
    return backendRequest(
      `/api/whatsapp-channel/pairing/${encodeURIComponent(attemptId)}?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  if (action === 'qr') {
    return backendRequest(
      `/api/whatsapp-channel/qr?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  if (action === 'diagnostics') {
    return backendRequest(
      `/api/admin/whatsapp-channel/diagnostics?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    );
  }
  // Só o `status` carrega os papéis: é o payload que a tela de conectores lê
  // para desenhar o cartão do número. QR e diagnóstico são outra conversa.
  return comPapeis(
    await backendRequest(
      `/api/whatsapp-channel/status?company_id=${company}&purpose=${PURPOSE}`,
      key,
      correlation,
    ),
    ctx.companyId,
  );
}

export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });
  const key = internalKey();
  if (!key) return NextResponse.json({ detail: 'internal_key_not_configured' }, { status: 500 });

  const correlation = correlationId(req);
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const action = String(body.action || 'pairing');
  const attemptId = typeof body.attempt_id === 'string' ? body.attempt_id : '';
  const alertNumber = typeof body.alert_number === 'string' ? body.alert_number.replace(/\D/g, '') : '';

  if (alertNumber && (alertNumber.length < 10 || alertNumber.length > 15)) {
    return NextResponse.json({ detail: 'numero_invalido' }, { status: 400 });
  }

  // 🔴 SPEC-078 Bloco B — o clique que autoriza os Auxiliares a enviar por aqui.
  //
  // Esta ação NÃO passa pelo backend, e a razão é a decisão de desenho: a
  // autorização é um fato do PRODUTO (a corretora consentiu), não um estado do
  // provedor de WhatsApp. As rotas de `/api/whatsapp-channel/*` falam com o
  // Evolution; esta escreve uma linha do nosso banco, com company_id explícito.
  //
  // O que ela NÃO faz, e a tela precisa dizer com todas as letras:
  //   · não faz o número responder segurado (isso é o Agente de Atendimento)
  //   · não libera envio de plataforma — alerta e follow-up seguem proibidos
  //     no observador (`get_platform_whatsapp_integration` não pede `auxiliar`)
  if (action === 'set-auxiliary-authorization') {
    if (typeof body.permitir !== 'boolean') {
      return NextResponse.json({ detail: 'permitir_deve_ser_booleano' }, { status: 400 });
    }
    try {
      const supabase = getSupabaseAdmin();
      const { data, error } = await supabase
        .from('integrations')
        .update({ permite_envio_de_auxiliar: body.permitir })
        .eq('company_id', ctx.companyId)
        .eq('provider', PROVIDER)
        .eq('purpose', PURPOSE)
        .eq('is_active', true)
        .select('id');
      if (error) {
        // Coluna ausente (migration 20260817_02 ainda não aplicada) cai aqui.
        // 503 e não 500: é indisponibilidade temporária de um recurso que já
        // está escrito, e a mensagem tem que dizer isso a quem for depurar.
        return NextResponse.json(
          { detail: 'autorizacao_indisponivel', erro: error.code || null, correlation_id: correlation },
          { status: 503, headers: { 'X-Correlation-ID': correlation } },
        );
      }
      if (!data || data.length === 0) {
        // Não há número pareado ativo. Autorizar o que não existe criaria uma
        // permissão órfã, que ligaria sozinha no dia em que alguém pareasse.
        return NextResponse.json(
          { detail: 'nenhum_numero_pareado', correlation_id: correlation },
          { status: 409, headers: { 'X-Correlation-ID': correlation } },
        );
      }
      return NextResponse.json(
        { ok: true, permite_envio_de_auxiliar: body.permitir, correlation_id: correlation },
        { headers: { 'X-Correlation-ID': correlation } },
      );
    } catch {
      return NextResponse.json(
        { detail: 'autorizacao_indisponivel', correlation_id: correlation },
        { status: 503, headers: { 'X-Correlation-ID': correlation } },
      );
    }
  }

  if (action === 'set-alert') {
    return backendRequest('/api/whatsapp-channel/set-alert', key, correlation, {
      method: 'POST',
      body: JSON.stringify({
        company_id: ctx.companyId,
        purpose: PURPOSE,
        mode: String(body.mode || ''),
        alert_number: alertNumber || null,
      }),
    });
  }

  if (action === 'disconnect') {
    return backendRequest('/api/whatsapp-channel/disconnect', key, correlation, {
      method: 'POST',
      body: JSON.stringify({ company_id: ctx.companyId, purpose: PURPOSE }),
    });
  }

  if ((action === 'retry' || action === 'cancel') && !attemptId) {
    return NextResponse.json({ detail: 'attempt_id_required' }, { status: 400 });
  }
  if (action === 'retry' || action === 'cancel') {
    return backendRequest(
      `/api/whatsapp-channel/pairing/${encodeURIComponent(attemptId)}/${action}`,
      key,
      correlation,
      {
        method: 'POST',
        body: JSON.stringify({
          company_id: ctx.companyId,
          purpose: PURPOSE,
          correlation_id: correlation,
        }),
      },
    );
  }

  const method = body.method === 'phone' ? 'phone' : 'qr';
  const phoneNumber = typeof body.phone_number === 'string' ? body.phone_number.replace(/\D/g, '') : '';
  if (method === 'phone' && (phoneNumber.length < 10 || phoneNumber.length > 15)) {
    return NextResponse.json({ detail: 'invalid_phone_number' }, { status: 400 });
  }
  return backendRequest('/api/whatsapp-channel/pairing', key, correlation, {
    method: 'POST',
    body: JSON.stringify({
      company_id: ctx.companyId,
      purpose: PURPOSE,
      method,
      phone_number: phoneNumber || null,
      correlation_id: correlation,
    }),
  });
}
