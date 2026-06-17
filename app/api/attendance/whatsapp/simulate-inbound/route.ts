import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { invokeRuntimeHandler } from '@/lib/attendance/runtime-invoke';
import { classifyInboundEvent } from '@/lib/attendance/whatsapp-inbound';
import { POST as bridgeHandler } from '@/app/api/attendance/whatsapp/inbound/route';

export const dynamic = 'force-dynamic';

/**
 * POST /api/attendance/whatsapp/simulate-inbound  (admin/teste, sessão)
 *
 * Simula um inbound de WhatsApp SEM depender da Z-API real: cria/reusa uma
 * conversa de teste e delega ao MESMO bridge (case routing + runtime + dry-run).
 * NUNCA envia provider real. Reaproveita o bridge — não duplica o fluxo.
 *
 * Body: { agent_id?, connected_phone?, from_phone, from_name?, text, message_id? }
 */
export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Empresa não encontrada' }, { status: 404 });

    const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
    if (!internalKey) return NextResponse.json({ ok: false, error: 'internal_key_missing' }, { status: 500 });

    let body: Record<string, any> = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }
    const fromPhone = typeof body.from_phone === 'string' ? body.from_phone.trim() : '';
    const text = typeof body.text === 'string' ? body.text : '';
    const fromName = typeof body.from_name === 'string' ? body.from_name.trim() : 'Cliente Teste';
    const connectedPhone = typeof body.connected_phone === 'string' ? body.connected_phone.trim() : 'sim-connected';
    if (!fromPhone) return NextResponse.json({ ok: false, error: 'from_phone obrigatório' }, { status: 400 });

    // Agente de atendimento (passado ou resolvido).
    let agentId: string | null = typeof body.agent_id === 'string' ? body.agent_id : null;
    if (!agentId) {
      const { data: agents } = await supabaseAdmin
        .from('agents')
        .select('id')
        .eq('company_id', companyId)
        .eq('is_active', true)
        .eq('agent_role', 'attendance')
        .limit(1);
      agentId = agents?.[0]?.id ?? null;
    }

    // Conversa de teste estável por (company, phone) — permite E2E multi-mensagem.
    const digits = fromPhone.replace(/\D/g, '');
    const sessionKey = `wa-sim:${companyId}:${digits}`;
    let conversationId: string | null = null;
    const { data: existingConv } = await supabaseAdmin
      .from('conversations')
      .select('id')
      .eq('company_id', companyId)
      .eq('session_id', sessionKey)
      .limit(1)
      .maybeSingle();
    if (existingConv?.id) {
      conversationId = existingConv.id;
    } else {
      const { data: conv, error: convErr } = await supabaseAdmin
        .from('conversations')
        .insert({
          company_id: companyId,
          user_id: session.userId, // simulador: usa o usuário logado como dono da conversa
          agent_id: agentId,
          session_id: sessionKey,
          channel: 'whatsapp',
          status: 'open',
          user_name: fromName,
          user_phone: fromPhone,
        })
        .select('id')
        .single();
      if (convErr || !conv) {
        console.error('[WA SIMULATE] conversation error:', convErr?.message);
        return NextResponse.json({ ok: false, error: 'conversation_create_failed' }, { status: 500 });
      }
      conversationId = conv.id;
    }

    // 42M0: aceita mídia (audio/image/document/location) via url/base64/location.
    const mediaUrl = typeof body.media_url === 'string' ? body.media_url : null;
    const mediaBase64 = typeof body.media_base64 === 'string' ? body.media_base64 : null;
    const mimeType = typeof body.mime_type === 'string' ? body.mime_type : null;
    const location = body.location && typeof body.location === 'object' ? body.location : null;
    const declaredMediaKind = typeof body.media_kind === 'string' ? body.media_kind : null;
    const mediaKind = declaredMediaKind || (text ? 'text' : classifyInboundEvent(body));

    // Delega ao MESMO bridge IN-PROCESS (sem self-fetch; ver runtime-invoke).
    const bridge = await invokeRuntimeHandler(bridgeHandler, {
      internalKey,
      body: {
        company_id: companyId,
        agent_id: agentId,
        user_id: session.userId,
        conversation_id: conversationId,
        phone: fromPhone,
        connected_phone: connectedPhone,
        sender_name: fromName,
        message_id: typeof body.message_id === 'string' ? body.message_id : `sim-${Date.now()}`,
        text,
        media_kind: mediaKind,
        media_url: mediaUrl,
        media_base64: mediaBase64,
        mime_type: mimeType,
        location,
      },
    });

    return NextResponse.json({
      ok: bridge.ok && bridge.json?.ok === true,
      simulated: true,
      conversation_id: conversationId,
      ...bridge.json,
    });
  } catch (error: any) {
    console.error('[WA SIMULATE] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
