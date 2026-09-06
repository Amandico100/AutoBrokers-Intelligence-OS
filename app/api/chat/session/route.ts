/**
 * DELETE /api/chat/session — apaga a memória de uma sessão de chat expirada.
 *
 * 🔴 SPEC-098 · U4.a — A CORRETORA VEM DA SESSÃO, NUNCA DO CORPO.
 *
 * 📊 Medido em 06/09/2026 (`chat/session/route.ts`, 44 linhas): esta rota não
 * tinha autenticação nenhuma. Recebia `{sessionId, companyId}` do navegador e
 * repassava os dois ao FastAPI — que também não conferia nada. Qualquer pessoa
 * na internet apagava a memória de qualquer conversa de qualquer corretora, e a
 * resposta era 200. É o irmão do P0 da SPEC-096: quem grita não é o erro, é o
 * silêncio.
 *
 * Agora: exige a sessão do corretor, manda o `company_id` DA SESSÃO (o do corpo
 * é descartado) e carimba a chave interna, para que o backend saiba que quem
 * fala é o nosso próprio servidor e não o navegador de alguém.
 */
import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionCompany } from '@/lib/auxiliaries/server';
import { assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

const BACKEND_URL = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    'http://localhost:8000'
).replace(/\/+$/, '');

function chaveInterna(): string {
    return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
}

export async function DELETE(request: NextRequest) {
    const xo = assertSameOrigin(request);
    if (xo) return NextResponse.json({ error: 'Pedido bloqueado.' }, { status: xo.status });

    const sessao = await resolveSessionCompany();
    if (!sessao) {
        return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    try {
        const body = await request.json().catch(() => ({} as any));
        const sessionId = body?.sessionId;

        if (!sessionId) {
            return NextResponse.json({ error: 'sessionId é obrigatório' }, { status: 400 });
        }

        const chave = chaveInterna();
        if (!chave) {
            return NextResponse.json(
                { error: 'Serviço de conversas não configurado.' },
                { status: 503 },
            );
        }

        const response = await fetch(`${BACKEND_URL}/chat/session`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-Internal-Key': chave,
            },
            // 🔴 O `companyId` é o da SESSÃO. O que veio no corpo não tem voz.
            body: JSON.stringify({ sessionId, companyId: sessao.companyId }),
            cache: 'no-store',
        });

        const data = await response.json().catch(() => ({}));
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('[API] Erro ao apagar a memória da sessão:', error);
        return NextResponse.json(
            { error: 'Não foi possível apagar a memória desta conversa.' },
            { status: 500 },
        );
    }
}
