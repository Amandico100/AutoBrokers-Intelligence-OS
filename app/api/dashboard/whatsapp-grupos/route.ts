// Os grupos do WhatsApp pareado da corretora — para escolher numa lista em vez
// de copiar `120363422850006552@g.us` da barra de endereços do WhatsApp Web.
//
// A empresa vem da SESSÃO, no servidor. O navegador não escolhe de qual
// corretora quer ver os grupos.
import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';
import { resolveSessionCompany } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

// Um pouco mais que o prazo do backend (8s), para que o erro que chega seja o
// DELE — com a frase explicando o que fazer — e não um timeout genérico daqui.
const PRAZO_MS = 11_000;

export async function GET(_req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx?.companyId) {
    return NextResponse.json(
      { ok: false, grupos: [], frase: 'Sessão sem corretora.' },
      { status: 401 },
    );
  }

  try {
    const base = getBackendUrl();
    const url = `${base}/api/whatsapp-channel/grupos?company_id=${encodeURIComponent(ctx.companyId)}`;
    const r = await fetch(url, {
      // Mesma ordem da rota de pareamento: a chave interna dedicada, e o
      // ADMIN_API_KEY como reserva. Trocar a ordem faria esta rota parar de
      // funcionar no dia em que a chave dedicada for configurada.
      headers: {
        'X-AutoBrokers-Internal-Key':
          process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '',
      },
      signal: AbortSignal.timeout(PRAZO_MS),
      cache: 'no-store',
    });
    return NextResponse.json(await r.json(), { status: r.ok ? 200 : 200 });
  } catch {
    // Tela de configuração que trava é pior que tela que diz "não consegui".
    return NextResponse.json({
      ok: false,
      grupos: [],
      frase: 'Não consegui falar com o WhatsApp agora. Você pode colar o ID do grupo manualmente.',
    });
  }
}
