import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { sessionOptions, adminSessionOptions, SessionData, AdminSessionData } from '@/lib/iron-session';

export const dynamic = 'force-dynamic';

/** Quantas mensagens uma página traz (R10/D.2). */
const PAGINA = 60;

/**
 * O cursor do histórico é `<created_at>|<id>` (R10). O `id` é o desempate: sem
 * ele, duas mensagens do mesmo instante decidem no acaso quem fica de fora.
 * Um cursor sem `|` continua valendo (só o relógio) — cursores antigos que
 * ainda estejam na mão de uma aba aberta não podem quebrar.
 */
function lerCursor(before: string | null): { antesDe: string | null; antesDoId: string | null } {
  if (!before) return { antesDe: null, antesDoId: null };
  const corte = before.indexOf('|');
  if (corte === -1) return { antesDe: before, antesDoId: null };
  return {
    antesDe: before.slice(0, corte),
    antesDoId: before.slice(corte + 1) || null,
  };
}

/** Um `id` do banco é uuid. Qualquer outra coisa é entrada de terceiro. */
const UUID = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

/**
 * 🔴 R14 — o cursor vem da URL, e URL é entrada de terceiro.
 *
 * 📊 `?before=amanha` ia cru para o `.lt('created_at', …)`, o Postgres
 * recusava a comparação e a rota devolvia **500**. Um 500 num parâmetro
 * malformado é o produto dizendo "eu quebrei" quando quem errou foi o pedido —
 * e, pior, é ruído que esconde as quebras de verdade no log.
 */
function cursorValido(antesDe: string | null, antesDoId: string | null): boolean {
  if (antesDe !== null && !Number.isFinite(Date.parse(antesDe))) return false;
  if (antesDoId !== null && !UUID.test(antesDoId)) return false;
  return true;
}

/** O cursor que a tela devolve no "carregar anteriores" seguinte. */
function montarCursor(mensagem: { created_at: string; id: string }): string {
  return `${mensagem.created_at}|${mensagem.id}`;
}

/**
 * SPEC-096 · S.3 — QUEM É O DONO DESTA CONVERSA
 *
 * 🔴 📊 Medido em 04/09/2026 (`messages/route.ts:16-21`): esta rota testava a
 * PRESENÇA do cookie — `if (!userCookie && !adminCookie) 401` — e depois lia
 * `messages` por `conversation_id` cru. Qualquer pessoa logada, de qualquer
 * corretora, lia a conversa de qualquer outra passando o id. É IDOR
 * autenticado: responde 200, não trava nada, e nunca aparece num log de erro.
 *
 * Agora: a conversa é resolvida ANTES, com `user_id = sessão`. Conversa que não
 * é sua responde **404**, nunca 403 — um 403 confirmaria que o id existe.
 */
type Identidade =
  | { tipo: 'usuario'; userId: string }
  | { tipo: 'admin'; adminId: string; companyId?: string | null; role?: string }
  | { tipo: 'negado' };

async function identificar(): Promise<Identidade> {
  const cookieStore = await cookies();

  const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (session?.userId) return { tipo: 'usuario', userId: session.userId };

  // 🔴 A presença do cookie de admin NÃO é autenticação: o cookie é assinado,
  // e só a sessão DECIFRADA prova quem é. Cookie presente + sessão inválida
  // (expirada, adulterada, de outro segredo) = 401.
  const adminSession = await getIronSession<AdminSessionData>(cookieStore, adminSessionOptions);
  if (adminSession?.adminId) {
    return {
      tipo: 'admin',
      adminId: adminSession.adminId,
      companyId: adminSession.companyId ?? null,
      role: adminSession.role,
    };
  }

  return { tipo: 'negado' };
}

function clienteAdmin() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

/**
 * Resolve a conversa CONFERINDO O DONO. Devolve `null` quando ela não existe
 * ou não é de quem pediu — os dois casos são o mesmo 404 para o cliente.
 */
async function conversaDoDono(
  supabaseAdmin: ReturnType<typeof clienteAdmin>,
  conversationId: string,
  quem: Identidade,
) {
  let consulta = supabaseAdmin
    .from('conversations')
    .select('id, user_id, company_id')
    .eq('id', conversationId);

  if (quem.tipo === 'usuario') {
    consulta = consulta.eq('user_id', quem.userId);
  } else if (quem.tipo === 'admin' && quem.role !== 'master_admin' && quem.companyId) {
    // O admin de uma corretora não atravessa para outra (CLAUDE.md §7).
    consulta = consulta.eq('company_id', quem.companyId);
  }

  const { data } = await consulta.maybeSingle();
  return (data as any) || null;
}

/**
 * POST /api/messages
 *
 * Só a PERGUNTA do próprio dono. A resposta do assistente é gravada pelo
 * servidor no turno (SPEC-096 A.2) — o browser não fala pelo agente (R5).
 */
export async function POST(request: NextRequest) {
  try {
    const quem = await identificar();
    if (quem.tipo === 'negado') {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const body = await request.json();
    const { conversation_id, role, content, type, audio_url, image_url, metadata, payload } = body || {};

    if (!conversation_id) {
      return NextResponse.json({ error: 'conversation_id é obrigatório' }, { status: 400 });
    }
    if (!role || !content) {
      return NextResponse.json({ error: 'role e content são obrigatórios' }, { status: 400 });
    }
    // 🔴 R5: só `user`. Quem responde é o backend, dentro do turno.
    if (role !== 'user') {
      return NextResponse.json(
        { error: 'Apenas a mensagem do usuário pode ser enviada por aqui.' },
        { status: 400 },
      );
    }

    const supabaseAdmin = clienteAdmin();
    const conversa = await conversaDoDono(supabaseAdmin, conversation_id, quem);
    if (!conversa) {
      return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 });
    }

    const { data, error } = await supabaseAdmin
      .from('messages')
      .insert({
        conversation_id,
        role,
        content,
        type: type || 'text',
        audio_url: audio_url || metadata?.audio_url || null,
        image_url: image_url || metadata?.image_url || null,
        payload: payload || null,
      })
      .select()
      .single();

    if (error) {
      console.error('[MESSAGES API] Error creating message:', error);
      return NextResponse.json({ error: 'Erro ao criar mensagem' }, { status: 500 });
    }

    await supabaseAdmin
      .from('conversations')
      .update({ updated_at: new Date().toISOString() })
      .eq('id', conversation_id);

    return NextResponse.json({ message: data }, { status: 201 });
  } catch (error: any) {
    console.error('[MESSAGES API] Error:', error);
    return NextResponse.json({ error: 'Erro interno ao criar mensagem' }, { status: 500 });
  }
}

/**
 * GET /api/messages?conversation_id=…&before=<created_at>&limit=60
 *
 * D.2 — "carregar anteriores" pagina por CURSOR (`lt(created_at, before)`),
 * nunca por OFFSET. 📊 §1.6: a conversa maior tem 1.326 mensagens; um OFFSET
 * relê tudo o que já passou a cada página.
 */
export async function GET(request: NextRequest) {
  try {
    const quem = await identificar();
    if (quem.tipo === 'negado') {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const conversationId = searchParams.get('conversation_id');
    const before = searchParams.get('before');
    const limiteBruto = parseInt(searchParams.get('limit') || String(PAGINA), 10);
    const limite = Number.isFinite(limiteBruto)
      ? Math.min(Math.max(limiteBruto, 1), PAGINA)
      : PAGINA;

    if (!conversationId) {
      return NextResponse.json({ error: 'conversation_id é obrigatório' }, { status: 400 });
    }

    const supabaseAdmin = clienteAdmin();
    const conversa = await conversaDoDono(supabaseAdmin, conversationId, quem);
    if (!conversa) {
      return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 });
    }

    // 🔴 F4/R10 — o cursor é o PAR (created_at, id), não só o relógio.
    //
    // Duas mensagens gravadas no mesmo instante (a pergunta e o eco, um
    // disparo de rotina) empatam em `created_at`. Um cursor só de relógio
    // resolve o empate na sorte: ou repete uma mensagem na página seguinte,
    // ou pula uma — e some para sempre, porque ninguém volta a olhar.
    const { antesDe, antesDoId } = lerCursor(before);
    if (!cursorValido(antesDe, antesDoId)) {
      return NextResponse.json(
        { error: 'before inválido', message: 'O cursor deve ser <created_at ISO>|<id>.' },
        { status: 400 },
      );
    }

    const projecao = `
                *,
                sender:sender_user_id (
                    first_name,
                    last_name,
                    avatar_url
                )
            `;

    // Uma a mais que a página: é assim que se sabe se há "carregar anteriores"
    // sem uma segunda consulta de contagem.
    let consulta = supabaseAdmin
      .from('messages')
      .select(projecao)
      .eq('conversation_id', conversationId);

    if (antesDe) {
      consulta = consulta.lt('created_at', antesDe);
    }

    const { data, error } = await consulta
      .order('created_at', { ascending: false })
      .limit(limite + 1);

    if (error) {
      console.error('[MESSAGES API] Error fetching messages:', error);
      return NextResponse.json({ error: 'Erro ao buscar mensagens' }, { status: 500 });
    }

    // O desempate mora numa consulta própria, sobre o MESMO instante do
    // cursor. ⛔ Não é `.or(...)`: o PostgREST aceitaria, mas a metade
    // interessante do filtro ficaria escondida dentro de uma string que
    // ninguém consegue inspecionar — e o guarda deixaria de ver o cursor.
    // Duas condições legíveis valem mais que uma string esperta.
    let empatados: any[] = [];
    if (antesDe && antesDoId) {
      const { data: doMesmoInstante } = await supabaseAdmin
        .from('messages')
        .select(projecao)
        .eq('conversation_id', conversationId)
        .eq('created_at', antesDe)
        .lt('id', antesDoId)
        .order('id', { ascending: false })
        .limit(limite + 1);
      empatados = (doMesmoInstante as any[]) || [];
    }

    // Os empatados são do instante do cursor — mais NOVOS que tudo o que a
    // consulta principal trouxe (ela é estritamente `<`), então vêm antes na
    // ordem decrescente.
    const descendentes = [...empatados, ...((data as any[]) || [])];
    const temMais = descendentes.length > limite;
    const pagina = temMais ? descendentes.slice(0, limite) : descendentes;
    const mensagens = [...pagina].reverse();

    return NextResponse.json({
      messages: mensagens,
      has_more: temMais,
      cursor: mensagens.length > 0 ? montarCursor(mensagens[0]) : null,
    });
  } catch (error: any) {
    console.error('[MESSAGES API] Error:', error);
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 });
  }
}
