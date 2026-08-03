// Prova que o canal desta corretora consegue RESPONDER um formulário nativo —
// aquilo que o WhatsApp chama de "aplicativo dentro da conversa".
//
// Manda de verdade, de um número nosso para outro. Não é simulação: a coisa que
// pode estar errada só aparece no ar.
//
// A corretora vem da SESSÃO, no servidor. O navegador não escolhe por qual
// corretora quer enviar — se escolhesse, uma corretora poderia usar o canal da
// outra, que é o defeito que a SPEC-063 passou o dia fechando.
//
// A chave da instância nunca passa por aqui. Ela é aberta dentro do backend, no
// momento do envio, e não volta na resposta. Um teste que exija alguém colar uma
// chave em algum lugar não é teste — é vazamento com hora marcada.
import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';
import { resolveSessionCompany } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

// Folgado de propósito: o backend fala com o Evolution GO, que fala com o
// WhatsApp. O prazo tem de caber nos três, senão o erro que chega é o nosso
// relógio — e não o que de fato aconteceu lá.
const PRAZO_MS = 45_000;

export async function POST(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx?.companyId) {
    return NextResponse.json(
      { success: false, frase: 'Sessão sem corretora.' },
      { status: 401 },
    );
  }

  let para = '';
  try {
    const body = await req.json();
    para = String(body?.para ?? '').replace(/\D/g, '');
  } catch {
    para = '';
  }

  if (!para) {
    return NextResponse.json(
      { success: false, frase: 'Informe o número que vai RECEBER a prova.' },
      { status: 400 },
    );
  }

  try {
    const base = getBackendUrl();
    const r = await fetch(`${base}/api/whatsapp-integrations/prova-de-formulario`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-AutoBrokers-Internal-Key':
          process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '',
      },
      body: JSON.stringify({ company_id: ctx.companyId, para }),
      signal: AbortSignal.timeout(PRAZO_MS),
      cache: 'no-store',
    });
    // Devolve 200 mesmo quando o backend recusa: o corpo já diz o que houve, e
    // uma tela de diagnóstico que rebenta em erro de rede esconde justamente o
    // diagnóstico que se foi buscar.
    return NextResponse.json(await r.json(), { status: 200 });
  } catch (e) {
    return NextResponse.json({
      success: false,
      frase: 'Não consegui falar com o backend.',
      detalhe: e instanceof Error ? e.name : 'erro',
    });
  }
}
