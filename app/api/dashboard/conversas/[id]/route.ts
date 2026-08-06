import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

/**
 * Uma conversa do atendimento (SPEC-017 S17-13).
 *
 * GET  → { conversation, messages }
 * POST → { action: 'claim' | 'release' | 'close' | 'send', text? }
 *   - claim:   assume o atendimento (atômico — 409 se outro humano já assumiu).
 *              status vira HUMAN_REQUESTED (IA pausa; webhook já respeita).
 *   - release: devolve ao atendente IA (status open, claim limpo).
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
    .select('id, company_id, session_id, channel, status, user_phone, user_name, claimed_by, claimed_by_name')
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
    const { error } = await supabase
      .from('conversations')
      .update({ status: 'open', claimed_by: null, claimed_by_name: null, claimed_at: null })
      .eq('id', id)
      .eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao devolver ao atendente IA' }, { status: 500 });
    return NextResponse.json({ ok: true });
  }

  if (action === 'close') {
    const { error } = await supabase
      .from('conversations')
      .update({ status: 'closed', claimed_by: null, claimed_by_name: null, claimed_at: null })
      .eq('id', id)
      .eq('company_id', ctx.companyId);
    if (error) return NextResponse.json({ error: 'Erro ao encerrar' }, { status: 500 });
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

    // Auto-claim: enviar como humano pausa a IA e marca o dono.
    const { error: claimErr } = await supabase
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
        content: text,
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
        payload: { origem: 'dashboard', wa_message_id: null },
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
        delivered = res.ok;
        if (!res.ok) console.error('[CONVERSAS] whatsapp delivery failed:', res.status);
      } catch (e) {
        if (!(e instanceof BackendUrlError)) console.error('[CONVERSAS] whatsapp delivery error');
      }
    }

    return NextResponse.json({ ok: true, message: newMessage, delivered });
  }

  return NextResponse.json({ error: 'Ação inválida' }, { status: 400 });
}
