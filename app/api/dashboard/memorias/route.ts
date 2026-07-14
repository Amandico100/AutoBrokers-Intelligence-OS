// SPEC-036 Etapa 3 — dados REAIS do Segundo Cérebro (aba Memórias).
// Camadas: GLOBAL (biblioteca AutoBrokers, empresa técnica GK) · CORRETORA
// (documentos do cofre) · PESSOAL (fatos que a IA aprendeu do usuário) ·
// CLIENTES (conversas recentes). Cada corretora só vê o que é dela.
import { NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';

const GK_COMPANY_ID = process.env.GLOBAL_KNOWLEDGE_COMPANY_ID || 'b1d308a5-2fe5-4bbe-9f3c-ef43acab3174';

export const dynamic = 'force-dynamic';

export async function GET() {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const sb = auth.supabase;
  const companyId = auth.ctx.companyId;

  const safe = async <T,>(p: PromiseLike<{ data: T | null }>): Promise<T | []> => {
    try { const { data } = await p; return (data as T) ?? ([] as unknown as T); } catch { return [] as unknown as T; }
  };

  const [docs, globalDocs, memories, convs] = await Promise.all([
    safe<any[]>(sb.from('documents').select('id, file_name, knowledge_class, created_at').eq('company_id', companyId).limit(150)),
    safe<any[]>(sb.from('documents').select('id, file_name, knowledge_class, created_at').eq('company_id', GK_COMPANY_ID).limit(200)),
    safe<any[]>(sb.from('user_memories').select('*').eq('company_id', companyId).limit(80)),
    safe<any[]>(sb.from('conversations').select('id, user_name, session_id, last_message_at').eq('company_id', companyId).order('last_message_at', { ascending: false }).limit(60)),
  ]);

  const memoryText = (m: any) =>
    String(m.fact || m.content || m.summary || m.memory || m.text || '').slice(0, 90) || 'Memória aprendida';

  // Humanização: arquivos técnicos (ex.: "infocap-policy-52ff76e0…pdf") viram
  // nomes legíveis — ninguém lê hash no segundo cérebro.
  let apoliceN = 0;
  const humanize = (raw: string): string => {
    const name = String(raw || '').replace(/\.(pdf|docx|txt|md|csv)$/i, '');
    if (/^infocap[-_ ]?policy/i.test(name)) { apoliceN += 1; return `Apólice do cliente · InfoCap #${apoliceN}`; }
    if (/^[0-9a-f-]{20,}$/i.test(name)) return 'Documento importado';
    return name.replace(/[-_]+/g, ' ').trim().slice(0, 60) || 'Documento';
  };

  const compRows = (await safe<any[]>(sb.from('companies').select('company_name').eq('id', companyId).limit(1))) as any[];
  const companyName = compRows[0]?.company_name || 'Sua corretora';

  return NextResponse.json({
    ok: true,
    company_name: companyName,
    global: (globalDocs as any[]).map((d) => ({ id: `g-${d.id}`, name: humanize(d.file_name), tema: d.knowledge_class || 'Biblioteca', at: d.created_at })),
    corretora: (docs as any[]).map((d) => ({ id: `c-${d.id}`, name: humanize(d.file_name), tema: d.knowledge_class || 'Documentos', at: d.created_at })),
    pessoal: (memories as any[]).map((m: any, i: number) => ({ id: `p-${m.id || i}`, name: memoryText(m), tema: 'Você', at: m.created_at })),
    clientes: (convs as any[])
      .filter((c) => !String(c.session_id || '').startsWith('dispatch:'))
      .map((c) => ({ id: `k-${c.id}`, name: c.user_name && c.user_name !== 'Usuário WhatsApp' ? c.user_name : 'Conversa no WhatsApp', tema: 'Clientes', at: c.last_message_at })),
  });
}
