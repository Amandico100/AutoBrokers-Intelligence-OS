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
 * Agora: só o nosso próprio servidor chama (chave interna), e a resposta é
 * apenas o identificador do lead. Nem `name`, nem `isNew` — os dois respondiam
 * à pergunta "esta pessoa é cliente de vocês?", que ninguém de fora pode fazer.
 * `companyId` continua vindo do corpo porque quem chama é o nosso BFF, que já
 * resolveu a corretora pela sessão; para o mundo, a porta está fechada.
 */
function chaveInternaOk(req: NextRequest): boolean {
  const esperada = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!esperada) return false; // sem chave configurada, ninguém entra
  const recebida = req.headers.get('x-internal-key') || '';
  return recebida.length > 0 && recebida === esperada;
}

/**
 * POST /api/leads/identify
 *
 * Identifica ou cria um lead pelo e-mail e devolve **só** o identificador dele.
 */
export async function POST(req: NextRequest) {
  if (!chaveInternaOk(req)) {
    return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  }

  try {
    const { email, name, companyId } = await req.json();

    if (!email || !companyId) {
      return NextResponse.json({ error: 'E-mail e empresa são obrigatórios' }, { status: 400 });
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json({ error: 'E-mail inválido' }, { status: 400 });
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
