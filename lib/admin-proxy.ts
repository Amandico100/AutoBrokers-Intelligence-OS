import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { NextRequest, NextResponse } from 'next/server';

import {
  adminSessionOptions,
  sessionOptions,
  type AdminSessionData,
  type SessionData,
} from '@/lib/iron-session';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || '';

/**
 * Quem está chamando? Só isso — não decide o que pode, decide se existe.
 *
 * O `middleware.ts` libera TODO `/api/` sem olhar sessão (a linha
 * `pathname.startsWith('/api/')` cai no ramo público). Isso é razoável para as
 * rotas que checam sessão por conta própria, e é uma porta aberta para as que
 * não checam.
 */
async function quemChama(): Promise<
  { tipo: 'plataforma' } | { tipo: 'corretora'; companyId: string | null } | null
> {
  const jar = await cookies();
  try {
    const admin = await getIronSession<AdminSessionData>(jar, adminSessionOptions);
    if (admin?.adminId) {
      return admin.role === 'company_admin'
        ? { tipo: 'corretora', companyId: admin.companyId ?? null }
        : { tipo: 'plataforma' };
    }
  } catch {
    /* cookie ilegível é o mesmo que cookie ausente */
  }
  try {
    const usuario = await getIronSession<SessionData>(jar, sessionOptions);
    if (usuario?.userId) {
      return {
        tipo: 'corretora',
        companyId: usuario.activeCompanyId ?? usuario.companyId ?? null,
      };
    }
  } catch {
    /* idem */
  }
  return null;
}

/**
 * Proxy autenticado: encaminha request ao backend com X-Admin-API-Key.
 *
 * ATENÇÃO ao nome: "authenticated" aqui sempre significou autenticar-se PERANTE
 * o backend — carimbar a chave de plataforma no cabeçalho. Nunca significou
 * conferir quem estava chamando.
 *
 * O efeito disso, medido em produção em 27/07/2026 sem cookie nenhum:
 *
 *   GET /dashboard                                  -> 307 para /login
 *   GET /admin/companies                            -> 307 para /admin/login
 *   GET /api/admin/proxy/agents/company/<id>/...    -> 200 com o prompt da corretora
 *
 * As duas primeiras linhas são a prova de que a proteção existe e funciona; a
 * terceira, de que ela não passava por aqui. O proxy pegava a requisição de
 * qualquer pessoa na internet, carimbava a chave de master e entregava ao
 * backend, que via uma chave válida e obedecia — GET, PUT e DELETE.
 *
 * Isto veio no primeiro commit do repositório (`6274293`, 04/06/2026), junto
 * com o código original. Não é regressão de nenhuma SPEC; é dívida que nunca
 * foi olhada porque a rota funcionava.
 *
 * A REGRA, e por que ela pode ser tão simples
 * -------------------------------------------
 * **Só sessão de PLATAFORMA passa.** Sem sessão -> 401. Sessão de corretora ->
 * 403, qualquer que seja o caminho.
 *
 * A primeira versão desta correção era mais frouxa: deixava a corretora passar
 * e só barrava quando o endereço trazia `company/<id>` de outra. Aquilo cobria
 * `agents/company/<id>/...` e deixava `agents/<agent_id>` em aberto — o UUID do
 * agente não diz de quem ele é, então quem soubesse o número alcançava o agente
 * alheio. Ficou registrado como P0 em aberto.
 *
 * O que fechou o P0 não foi mais código aqui: foi o dashboard parar de precisar
 * deste proxy. As telas de agente, equipe, conhecimento e custos que eu havia
 * duplicado na raiz do `/dashboard` viraram redirecionamentos para a
 * Personalização — que fala com `/api/dashboard/*`, com escopo por sessão.
 *
 * Depois disso, TODOS os chamadores de `/api/admin/proxy/*` vivem em `/admin`:
 *
 *   app/admin/companies/[companyId]/agents/page.tsx
 *   app/admin/blueprint-center/page.tsx        (AgentConfigModal)
 *   app/admin/companies/page.tsx               (DocumentManagementModal)
 *   app/admin/knowledge-base/page.tsx          (DocumentManagementModal)
 *
 * Nenhum no `/dashboard`. Então não há caso legítimo de corretora aqui, e a
 * regra não precisa adivinhar dono de UUID: ela recusa a corretora inteira.
 *
 * Isso é melhor que a versão com escopo por dois motivos. Não depende de o
 * caminho carregar a empresa — vale para qualquer rota, inclusive as que ainda
 * não existem. E falha do lado seguro: uma rota nova mal desenhada vira um 403
 * visível em desenvolvimento, não um vazamento silencioso em produção.
 */
export async function authenticatedProxy(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  try {
    const chamador = await quemChama();

    if (!chamador) {
      return NextResponse.json(
        { error: 'Sessão não encontrada.' },
        { status: 401 },
      );
    }

    if (chamador.tipo !== 'plataforma') {
      // 403 e não 404 de propósito: 404 aqui viraria oráculo de existência de
      // UUID — quem chutasse números descobriria quais recursos existem.
      return NextResponse.json(
        { error: 'Esta área é da plataforma.' },
        { status: 403 },
      );
    }

    // 1. Construir URL do backend preservando query params
    const url = new URL(backendPath, BACKEND_URL);
    request.nextUrl.searchParams.forEach((value, key) => {
      url.searchParams.set(key, value);
    });

    // 2. Preparar headers (mesmo padrão das rotas existentes)
    const headers: Record<string, string> = {
      'X-Admin-API-Key': ADMIN_API_KEY,
    };

    const contentType = request.headers.get('content-type');
    if (contentType && !contentType.includes('multipart/form-data')) {
      headers['Content-Type'] = contentType;
    }

    // 3. Preparar body
    let body: any = undefined;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      if (contentType?.includes('multipart/form-data')) {
        body = await request.formData();
      } else {
        body = await request.text();
      }
    }

    // 4. Forward ao backend
    const backendResponse = await fetch(url.toString(), {
      method: request.method,
      headers,
      body,
    });

    // 5. Retornar response
    const responseBody = await backendResponse.text();
    return new NextResponse(responseBody, {
      status: backendResponse.status,
      headers: {
        'Content-Type': backendResponse.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error: any) {
    console.error('[ADMIN PROXY] Backend error:', error.message);
    return NextResponse.json({ error: 'Erro ao conectar com backend' }, { status: 502 });
  }
}
