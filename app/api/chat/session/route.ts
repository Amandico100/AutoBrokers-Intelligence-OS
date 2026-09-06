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
 * 🔴 CONSERTO 1 (red team B2) — E EXIGIR A SESSÃO MATOU O WIDGET.
 *
 * 📊 O único chamador desta rota é `app/embed/[agentId]/page.tsx:97` — o
 * navegador do VISITANTE anônimo, que não tem sessão de corretor e nunca terá.
 * Exigir `resolveSessionCompany()` devolvia **401** e a memória da sessão
 * expirada deixava de ser apagada.
 *
 * 📊 E havia um segundo efeito: o backend ganhou um "modo widget" cuidadoso
 * (`backend/app/api/chat.py:1289-1300`, E5) que, SEM chave, deriva a corretora
 * da linha de `conversations` achada por `session_id` (que tem UNIQUE). Esse
 * modo ficou INALCANÇÁVEL, porque a única porta que leva até ele sempre exigia
 * sessão e sempre carimbava a chave. O caminho seguro existia e não tinha quem
 * o usasse.
 *
 * Agora são DOIS modos, e em nenhum deles o corpo escolhe a corretora:
 *
 *   painel  · com sessão de corretor → chave interna + `companyId` DA SESSÃO.
 *   widget  · sem sessão → repassa **só o `sessionId`**, SEM chave. O backend
 *             deriva a corretora da linha. O `companyId` do corpo é descartado
 *             nos dois casos.
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

    try {
        const body = await request.json().catch(() => ({} as any));
        const sessionId = body?.sessionId;

        if (!sessionId) {
            return NextResponse.json({ error: 'sessionId é obrigatório' }, { status: 400 });
        }

        const chave = chaveInterna();
        if (sessao && !chave) {
            return NextResponse.json(
                { error: 'Serviço de conversas não configurado.' },
                { status: 503 },
            );
        }

        // 🔴 Modo PAINEL: a chave e o `companyId` DA SESSÃO.
        //    Modo WIDGET: sem chave e sem corretora — quem diz de quem é a
        //    sessão é a linha de `conversations`, no backend (E5).
        const cabecalhos: Record<string, string> = { 'Content-Type': 'application/json' };
        if (sessao && chave) cabecalhos['X-Internal-Key'] = chave;

        const response = await fetch(`${BACKEND_URL}/chat/session`, {
            method: 'DELETE',
            headers: cabecalhos,
            // ⛔ O `companyId` do corpo NUNCA viaja: no painel vale o da sessão,
            //    no widget vale o derivado da linha.
            body: JSON.stringify(
                sessao && chave ? { sessionId, companyId: sessao.companyId } : { sessionId },
            ),
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
