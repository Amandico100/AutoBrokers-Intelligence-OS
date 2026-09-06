import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

// Service Role Client (bypassa RLS)
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

/**
 * 🔴 SPEC-098 · U4.a (E9) — ESTA ROTA ERA UM ORÁCULO PÚBLICO.
 *
 * 📊 Medido em 06/09/2026 (`leads/identify/route.ts:33-55`): sem sessão, sem
 * cookie e sem cabeçalho, com service role, ela recebia `{email, companyId}` e
 * devolvia `isNew` e o **nome** do lead. Não era só uma escrita: era LEITURA de
 * dado pessoal. Quem soubesse um UUID de corretora perguntava, um e-mail por
 * vez, quem é cliente dela — e recebia o nome da pessoa junto. Respondia 200,
 * não travava nada e não aparecia em log de erro nenhum.
 *
 * 🔴 CONSERTO 1 (red team B2) — E EXIGIR A CHAVE MATOU O FUNIL.
 *
 * 📊 O único chamador desta rota, em código-fonte, é
 * `app/embed/[agentId]/page.tsx:363` — e ele tem `'use client'`: é o NAVEGADOR
 * do visitante anônimo do site da corretora. Um navegador não pode carregar
 * segredo. Exigir `X-Internal-Key` devolvia **401**, e o widget mostrava
 * "Failed to identify lead": o formulário de entrada de leads morreu.
 *
 * A porta certa não é a chave; é **não deixar o corpo escolher a corretora**.
 * Sem chave, o visitante manda `{email, name, agentId}` — o `agentId` que já
 * está na URL do widget — e a corretora é **DERIVADA** da linha de `agents`.
 * É o mesmo padrão do modo widget do `DELETE /chat/session` (E5): quem sabe de
 * quem é a coisa é a LINHA, não o corpo do pedido.
 *
 * ⛔ `companyId` do corpo só é aceito COM a chave interna (o painel). Sem ela,
 * é ignorado — em silêncio, porque devolver "esse companyId não vale" já seria
 * responder uma pergunta que ninguém de fora pode fazer.
 *
 * ⛔ A resposta continua sendo **só o `leadId`**. Nem `name`, nem `isNew` — os
 * dois respondiam "esta pessoa é cliente de vocês?".
 */
function chaveInternaOk(req: NextRequest): boolean {
  const esperada = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!esperada) return false; // sem chave configurada, ninguém entra por aqui
  const recebida = req.headers.get('x-internal-key') || '';
  return recebida.length > 0 && recebida === esperada;
}

/**
 * Freio de porta aberta: 30 pedidos por minuto por IP, em memória.
 *
 * ⚠️ É um freio, não uma trava: em várias instâncias cada uma tem o seu mapa.
 * Serve para que a porta pública não seja um moedor de e-mails de graça.
 */
const _porIp = new Map<string, { n: number; ate: number }>();
function passouDoLimite(ip: string): boolean {
  const agora = Date.now();
  const atual = _porIp.get(ip);
  if (!atual || agora > atual.ate) {
    _porIp.set(ip, { n: 1, ate: agora + 60_000 });
    // ⚠️ `forEach` e não `for…of`: o `target` do projeto é ES5 e iterar um Map
    // direto exige `downlevelIteration` (TS2802). Não é estilo — é o que compila.
    if (_porIp.size > 5000) _porIp.forEach((v, k) => { if (agora > v.ate) _porIp.delete(k); });
    return false;
  }
  atual.n += 1;
  return atual.n > 30;
}

/**
 * A corretora do widget: DERIVADA do agente, nunca lida do corpo.
 */
async function empresaDoWidget(agentId: string): Promise<string | null> {
  const { data } = await supabaseAdmin
    .from('agents')
    .select('id, company_id, is_active')
    .eq('id', agentId)
    .maybeSingle();
  if (!data?.company_id) return null;
  if (data.is_active === false) return null;
  return data.company_id as string;
}

/**
 * POST /api/leads/identify
 *
 * Identifica ou cria um lead pelo e-mail e devolve **só** o identificador dele.
 */
export async function POST(req: NextRequest) {
  const comChave = chaveInternaOk(req);

  if (!comChave) {
    const ip =
      (req.headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
      req.headers.get('x-real-ip') ||
      'desconhecido';
    if (passouDoLimite(ip)) {
      return NextResponse.json({ error: 'Muitos pedidos. Tente de novo em um minuto.' }, { status: 429 });
    }
  }

  try {
    const { email, name, companyId: companyIdDoCorpo, agentId } = await req.json();

    if (!email) {
      return NextResponse.json({ error: 'E-mail é obrigatório' }, { status: 400 });
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json({ error: 'E-mail inválido' }, { status: 400 });
    }

    // 🔴 Com a chave (o painel), o corpo pode dizer a corretora — quem chamou
    // já resolveu a sessão. SEM a chave, o corpo NÃO TEM VOZ: vale o agente.
    let companyId: string | null = null;
    if (comChave && typeof companyIdDoCorpo === 'string' && companyIdDoCorpo) {
      companyId = companyIdDoCorpo;
    } else {
      if (!agentId || typeof agentId !== 'string') {
        return NextResponse.json({ error: 'Agente é obrigatório' }, { status: 400 });
      }
      companyId = await empresaDoWidget(agentId);
      if (!companyId) {
        return NextResponse.json({ error: 'Atendimento não encontrado' }, { status: 404 });
      }
    }

    // 1. Tenta encontrar lead existente
    const { data: existing } = await supabaseAdmin
      .from('leads')
      .select('id, name')
      .eq('company_id', companyId)
      .eq('email', email.toLowerCase().trim())
      .single();

    if (existing) {
      await supabaseAdmin
        .from('leads')
        .update({
          last_seen_at: new Date().toISOString(),
          name: name || existing.name,
        })
        .eq('id', existing.id);

      // 🔴 Só o id. Devolver `name`/`isNew` era responder de fora quem é cliente.
      return NextResponse.json({ leadId: existing.id });
    }

    // 2. Cria novo lead
    const { data: newLead, error } = await supabaseAdmin
      .from('leads')
      .insert({
        company_id: companyId,
        email: email.toLowerCase().trim(),
        name: name?.trim() || null,
        last_seen_at: new Date().toISOString(),
      })
      .select('id')
      .single();

    if (error) {
      console.error('[LEADS API] Insert error:', error);
      throw error;
    }

    return NextResponse.json({ leadId: newLead.id });
  } catch (error) {
    console.error('[LEADS API] Error identifying lead:', error);
    return NextResponse.json({ error: 'Falha ao processar identificação' }, { status: 500 });
  }
}
