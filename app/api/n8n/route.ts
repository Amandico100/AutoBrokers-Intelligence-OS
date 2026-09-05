import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient } from '@supabase/supabase-js';
import { logSystemAction, getClientInfo } from '@/lib/logger';
import { sessionOptions, SessionData } from '@/lib/iron-session';

export const dynamic = 'force-dynamic';

// Service Role Client
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

export async function POST(request: NextRequest) {
  console.log('[N8N API] ========== REQUISIÇÃO RECEBIDA ==========');
  const { ipAddress, userAgent } = getClientInfo(request);

  try {
    // Ler sessão do cookie criptografado
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);

    const body = await request.json();
    // console.log('[N8N API] Body recebido (chaves):', Object.keys(body));

    // 🔴 SPEC-096 S.4/R12 — A CORRETORA VEM DA SESSÃO, E SÓ DELA.
    //
    // 📊 Medido em 04/09/2026 (`n8n/route.ts:31`): era
    // `body.companyId || session.companyId` — o CORPO vencia. A voz do
    // corretor saía pelo webhook da corretora que o browser escolhesse, e a
    // resposta era 200. Sem sessão, o corpo até supria a empresa inteira: um
    // POST sem cookie nenhum falava por qualquer corretora.
    //
    // Agora o corpo não tem voz sobre identidade, e sem sessão é 401 — nunca
    // 400, porque o problema não é o pedido, é quem pede.
    if (!session?.userId || !session?.companyId) {
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const targetCompanyId = session.companyId;

    console.log('[N8N API] Usando Company ID:', targetCompanyId);

    // Buscar informações da company
    const { data: company } = await supabaseAdmin
      .from('companies')
      .select('webhook_url, use_langchain')
      .eq('id', targetCompanyId)
      .maybeSingle();

    if (!company) {
      console.error(`[N8N API] Company ${targetCompanyId} não encontrada no banco.`);
      return NextResponse.json({ error: 'Empresa não encontrada' }, { status: 400 });
    }

    const useLangChain = company.use_langchain || false;

    let targetUrl: string;
    let targetType: string;

    if (useLangChain) {
      targetUrl = process.env.NEXT_PUBLIC_LANGCHAIN_API_URL || 'http://localhost:8000/chat';
      targetType = 'LangChain (FastAPI)';
    } else {
      const webhookUrl = company.webhook_url;
      if (!webhookUrl) {
        return NextResponse.json({ error: 'Webhook não configurado' }, { status: 400 });
      }
      targetUrl = webhookUrl;
      targetType = 'N8N Webhook';
    }

    console.log(`[N8N API] Roteando para: ${targetType} (${targetUrl})`);

    // Payload final para o Backend/N8N
    const enrichedBody = {
      ...body,
      companyId: targetCompanyId, // da SESSÃO — sobrescreve o que veio no corpo
      userId: session.userId, // idem: o corpo não escolhe por quem se fala
    };

    const apiResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(enrichedBody),
    });

    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      console.error(`[N8N API] Erro no destino (${apiResponse.status}):`, errorText);
      return NextResponse.json(
        { error: 'Upstream Error', details: errorText },
        { status: apiResponse.status },
      );
    }

    const responseData = await apiResponse.json();
    return NextResponse.json(responseData);
  } catch (error) {
    console.error('[N8N API] Erro fatal:', error);
    return NextResponse.json(
      { error: 'Internal Server Error', details: String(error) },
      { status: 500 },
    );
  }
}
