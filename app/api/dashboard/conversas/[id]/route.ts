import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { ehAnotacao } from '@/lib/atendimento/a-nota-da-atendente';

// 🔴 O prefixo que separa uma ANOTAÇÃO de uma fala ao cliente, no `content`.
//
// ⛔ NÃO EXPORTAR. Arquivo de rota do Next.js só aceita os exports que o
// framework conhece (GET, POST, dynamic, …). 📊 Exportar isto derruba o `tsc`
// com `TS2344: Property 'PREFIXO_DA_NOTA' is incompatible with index
// signature` — e o `next build` junto. É a mesma família do defeito que
// deixou o produto 1h40 no chão em 02/08 (`CLAUDE.md` §9.1): o arquivo parece
// certo, e o build explode.
//
// ⚠️ Constante e não literal solto mesmo assim: o guarda lê o FONTE e casa
// contra esta linha. Dois literais iguais em lugares diferentes divergem em
// silêncio no dia em que alguém mexe num só.
const PREFIXO_DA_NOTA = '\u{1F4DD} [nota interna] ';

export const dynamic = 'force-dynamic';

/**
 * Uma conversa do atendimento (SPEC-017 S17-13).
 *
 * GET  → { conversation, messages }
 * POST → { action: 'claim' | 'release' | 'close' | 'send', text? }
 *   - claim:   assume o atendimento (atômico — 409 se outro humano já assumiu).
 *              status vira HUMAN_REQUESTED (IA pausa; webhook já respeita).
 *   - release: solta o claim. 🔴 Com handoff ABERTO volta para HUMAN_REQUESTED
 *              (a fila), não para `open` — senão o pedido da IA some da Fila e
 *              do Vigia, e o segurado vira problema de ninguém (SPEC-085 E.4).
 *   - close:   encerra a conversa.
 *   - send:    envia como humano (persiste + entrega no WhatsApp). Auto-claim
 *              se ninguém assumiu; 409 se OUTRO humano é o dono.
 */

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

async function loadScoped(supabase: ReturnType<typeof getSupabaseAdmin>, id: string, companyId: string) {
  const { data } = await supabase
    .from('conversations')
    .select('id, company_id, session_id, channel, status, user_phone, user_name, claimed_by, claimed_by_name, human_handoff_reason, resolvido_em')
    .eq('id', id)
    .eq('company_id', companyId)
    .maybeSingle();
  return data || null;
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const { id } = await params;
  const supabase = getSupabaseAdmin();

  const conversation = await loadScoped(supabase, id, ctx.companyId);
  if (!conversation) return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 });

  const { data: messages, error } = await supabase
    .from('messages')
    .select('id, role, content, type, image_url, audio_url, sender_user_id, created_at')
    .eq('conversation_id', id)
    .order('created_at', { ascending: true })
    .limit(500);
  if (error) {
    console.error('[CONVERSAS] messages error:', error.message);
    return NextResponse.json({ error: 'Erro ao carregar mensagens' }, { status: 500 });
  }

  // Zera não-lidas ao abrir (melhor esforço).
  supabase.from('conversations').update({ unread_count: 0 }).eq('id', id).then(() => {});

  return NextResponse.json({ conversation, messages: messages || [] });
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const { id } = await params;
  const supabase = getSupabaseAdmin();

  const conversation = await loadScoped(supabase, id, ctx.companyId);
  if (!conversation) return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const action = String(body.action || '');

  const { data: meRow } = await supabase.from('users_v2').select('name, email').eq('id', ctx.userId).maybeSingle();
  const myName = String(meRow?.name || meRow?.email || 'Atendente humano');

  if (action === 'claim') {
    // Atômico: só assume se ninguém (ou eu mesmo) for o dono.
    const { data: updated, error } = await supabase
      .from('conversations')
      .update({ status: 'HUMAN_REQUESTED', claimed_by: ctx.userId, claimed_by_name: myName, claimed_at: new Date().toISOString() })
      .eq('id', id)
      .eq('company_id', ctx.companyId)
      .or(`claimed_by.is.null,claimed_by.eq.${ctx.userId}`)
      .select('id, status, claimed_by, claimed_by_name')
      .maybeSingle();
    if (error) {
      console.error('[CONVERSAS] claim error:', error.message);
      return NextResponse.json({ error: 'Erro ao assumir (a migration de claim já foi aplicada?)' }, { status: 500 });
    }
    if (!updated) {
      const cur = await loadScoped(supabase, id, ctx.companyId);
      return NextResponse.json(
        { error: `Já assumida por ${cur?.claimed_by_name || 'outro atendente'}.` },
        { status: 409 },
      );
    }
    return NextResponse.json({ ok: true, conversation: updated });
  }

  if (action === 'release') {
    // 🔴 SPEC-085 BLOCO E.4 / F.3 — O `release` DEIXA DE APAGAR O PEDIDO.
    //
    // Ele devolvia SEMPRE para `open`. Quando a IA tinha pedido um humano e a
    // pessoa devolvia sem resolver, o pedido sumia: a conversa saía do filtro
    // `precisa_de_voce` da Fila **e** do select do Vigia, que procura
    // `status = 'HUMAN_REQUESTED'`. O segurado voltava a ser problema de
    // ninguém, e nenhum alarme sabia disso.
    //
    // ⚠️ E era o que tornava MENTIRA a última mensagem do Vigia: *"ela continua
    // na Fila do painel — de lá ninguém a tira sozinho."* Tirava.
    //
    // 🔴 A regra é por DADO, não por estado novo (§F.1, saída (b)):
    //
    //   handoff ABERTO   (`human_handoff_reason` e sem `resolvido_em`)
    //        → volta para HUMAN_REQUESTED **com `claimed_by` nulo**, que é
    //          exatamente "a IA pediu e ninguém assumiu" — a fila de novo.
    //   sem handoff aberto
    //        → `open`, como sempre. Uma pessoa que só entrou para dar um oi
    //          não deve criar um pedido de atendimento ao sair.
    const handoffAberto = Boolean(conversation.human_handoff_reason) && !conversation.resolvido_em;
    const { error } = await supabase
      .from('conversations')
      .update({
        status: handoffAberto ? 'HUMAN_REQUESTED' : 'open',
        claimed_by: null,
        claimed_by_name: null,
        claimed_at: null,
      })
      .eq('id', id)
      .eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao devolver ao atendente IA' }, { status: 500 });
    return NextResponse.json({ ok: true, volta_para_a_fila: handoffAberto });
  }

  if (action === 'close') {
    // 🔴 SPEC-086 BLOCO A — ENCERRAR PASSA A DEIXAR MARCA.
    //
    // 📊 Medido em 26/08: `conversations.resolvido_em` tinha **0 linhas em
    // 671**. Este botão gravava `status='closed'` e mais nada — então
    // *"a atendente encerrou"* e *"o cliente desistiu e foi embora"* eram, para
    // o banco, o mesmo estado, e a pergunta da sexta-feira não tinha resposta.
    //
    // ⚠️ `fechado_por_humano` é um dos CINCO valores do
    // `ck_conversations_resolucao_motivo`. Gravar fora da lista é um UPDATE que
    // o Postgres RECUSA — e o `error` abaixo já trata.
    //
    // 🔴 `resolvido_em` e `resolucao_motivo` andam JUNTOS (há CHECK): uma
    // conversa que acabou "por um motivo, em momento nenhum" sumiria de toda
    // consulta por período.
    //
    // ⛔ `.is('resolvido_em', null)` — quem já terminou não termina de novo, e o
    // primeiro motivo é o que vale. Sem isto, fechar na tela um atendimento que
    // o robô já concluiu apagaria o desfecho REAL.
    const agora = new Date().toISOString();
    const { error } = await supabase
      .from('conversations')
      .update({
        status: 'closed', claimed_by: null, claimed_by_name: null, claimed_at: null,
        resolvido_em: agora, resolucao_motivo: 'fechado_por_humano',
      })
      .eq('id', id)
      .eq('company_id', ctx.companyId)
      .is('resolvido_em', null);
    if (error) return NextResponse.json({ error: 'Erro ao encerrar' }, { status: 500 });

    // ⚠️ Se a conversa JÁ estava resolvida, o update acima não casou nada — e o
    // `status` também não mudou. Este segundo update fecha só o status, sem
    // tocar no motivo que já existe.
    const { error: erroStatus } = await supabase
      .from('conversations')
      .update({ status: 'closed', claimed_by: null, claimed_by_name: null, claimed_at: null })
      .eq('id', id)
      .eq('company_id', ctx.companyId)
      .not('resolvido_em', 'is', null);
    if (erroStatus) return NextResponse.json({ error: 'Erro ao encerrar' }, { status: 500 });

    return NextResponse.json({ ok: true });
  }

  if (action === 'send') {
    const text = String(body.text || '').trim();
    if (!text) return NextResponse.json({ error: 'Mensagem vazia' }, { status: 400 });
    if (conversation.claimed_by && conversation.claimed_by !== ctx.userId) {
      return NextResponse.json(
        { error: `Conversa assumida por ${conversation.claimed_by_name || 'outro atendente'}.` },
        { status: 409 },
      );
    }

    // 🔴 SPEC-090 BLOCO C — A ANOTAÇÃO NÃO ASSUME A CONVERSA.
    //
    // ⚠️ O auto-claim logo abaixo **pausa a IA** e marca o dono. Sem esta
    // linha, escrever `#nota o robô perguntou a placa duas vezes` no painel
    // pararia o atendimento — que é exatamente o *"anotar viraria assumir"*
    // que o BLOCO C existe para impedir.
    //
    // 📊 E era o pior lugar possível para o defeito: o painel é o ÚNICO
    // caminho em que o produto consegue garantir que a nota **não sai** para
    // o segurado — no WhatsApp, `fromMe` é o eco de uma mensagem que já foi
    // entregue (`evolution_inbound.py:847`). É no painel que a Regina e a
    // Saionara devem escrever, e era ali que anotar assumia.
    //
    // ⚠️ A regra do prefixo mora no backend
    // (`a_nota_da_atendente.py`); a cópia daqui existe porque este proxy
    // escreve DUAS vezes antes de chamá-lo. As duas são comparadas por
    // `scripts/spec090-a-regra-do-prefixo-e-uma-so.test.mjs`.
    const ehNota = ehAnotacao(text);

    // Auto-claim: enviar como humano pausa a IA e marca o dono.
    const { error: claimErr } = ehNota ? { error: null } : await supabase
      .from('conversations')
      .update({
        status: 'HUMAN_REQUESTED',
        claimed_by: ctx.userId,
        claimed_by_name: myName,
        claimed_at: new Date().toISOString(),
        last_message_preview: text.substring(0, 100),
        last_message_at: new Date().toISOString(),
      })
      .eq('id', id)
      .eq('company_id', ctx.companyId);
    if (claimErr) {
      console.error('[CONVERSAS] send/claim error:', claimErr.message);
      return NextResponse.json({ error: 'Erro ao assumir a conversa (migration de claim aplicada?)' }, { status: 500 });
    }

    const { data: newMessage, error: insertErr } = await supabase
      .from('messages')
      .insert({
        conversation_id: id,
        role: 'assistant',
        // 🔴 A MARCA VAI NO `content`, E NÃO SÓ NO `payload`.
        //
        // 📊 Achado em 26/08/2026 por auditoria externa: `nota_interna` no
        // `payload` tinha **ZERO leitores** no repositório inteiro — e os
        // quatro consumidores de `messages` selecionam `role, content` e
        // **nunca `payload`**:
        //
        //     conversation_auditor · garimpo_v3 · memory_fabric · broker_insights
        //
        // ⚠️ Nem a thread deste mesmo arquivo lê: o `select` acima pede
        // `id, role, content, type, image_url, audio_url, sender_user_id,
        // created_at`. **Nem a atendente distinguia a própria nota de uma
        // fala enviada ao cliente.**
        //
        // 🔴 O comentário abaixo já dizia a intenção — *"sem a marca, uma
        // nota vira uma fala da corretora ao cliente"* — e a marca estava no
        // lugar que ninguém lê. É `CLAUDE.md` §9.3: a frase não tinha código
        // atrás dela.
        //
        // O prefixo resolve os dois de uma vez, sem migration e sem tocar em
        // quatro consumidores: quem lê `content` vê que é nota.
        // ⚠️ `payload.nota_interna` FICA — é a versão legível por máquina,
        // para quem acrescentar filtro depois (P-265).
        content: ehNota ? PREFIXO_DA_NOTA + text : text,
        type: 'text',
        sender_user_id: ctx.userId,
        // `origem: 'dashboard'` é o que impede a resposta de aparecer DUAS vezes.
        //
        // Esta mensagem vai ao WhatsApp e VOLTA pelo webhook como `fromMe`. O
        // espelho (`espelho_chat._eco_do_dashboard`) reconhece o eco por
        // conversa + texto + esta marca + janela de 2 minutos, e não grava de
        // novo. A marca restringe a comparação ao que o dashboard mandou —
        // assim a atendente que digita a mesma palavra duas vezes NO CELULAR
        // não perde a segunda.
        //
        // O ideal seria comparar o id do WhatsApp, mas `send-message` devolve
        // `{"status":"sent"}`: `whatsapp_service.send_message` retorna booleano,
        // e fazer o id subir por aquela cadeia mexeria em caminho quente.
        // 🔴 SPEC-090: `nota_interna` diz que esta linha NÃO foi para o
        //    segurado. Sem a marca, uma nota vira, no histórico, uma fala da
        //    corretora ao cliente — e é desse histórico que o produto aprende.
        payload: { origem: 'dashboard', nota_interna: ehNota, wa_message_id: null },
      })
      .select()
      .single();
    if (insertErr) {
      console.error('[CONVERSAS] send insert error:', insertErr.message);
      return NextResponse.json({ error: 'Erro ao salvar mensagem' }, { status: 500 });
    }

    // Entrega no WhatsApp pela integração da corretora (mesmo seam do Admin).
    let delivered = false;
    const key = internalKey();
    if (conversation.channel === 'whatsapp' && conversation.user_phone && key) {
      try {
        const backend = getBackendUrl();
        const res = await fetch(`${backend}/api/webhook/send-message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Admin-API-Key': key },
          body: JSON.stringify({ session_id: conversation.session_id, phone: conversation.user_phone, message: text }),
        });
        // 🔴 UMA NOTA NUNCA FOI "ENTREGUE". O backend responde
        //    `{"status":"anotada","enviada":false}` e não chama
        //    `send_message` em caminho nenhum.
        //
        // ⚠️ Se a tela disser "entregue", a atendente vai achar que o
        //    cliente leu a anotação — e o susto dela custa mais que o defeito.
        delivered = res.ok && !ehNota;
        if (!res.ok) console.error('[CONVERSAS] whatsapp delivery failed:', res.status);
      } catch (e) {
        if (!(e instanceof BackendUrlError)) console.error('[CONVERSAS] whatsapp delivery error');
      }
    }

    // ⚠️ `anotada` é o que permite à tela mostrar "anotação registrada"
    //    em vez de um balão de mensagem enviada.
    return NextResponse.json({ ok: true, message: newMessage, delivered,
                              anotada: ehNota });
  }

  return NextResponse.json({ error: 'Ação inválida' }, { status: 400 });
}
