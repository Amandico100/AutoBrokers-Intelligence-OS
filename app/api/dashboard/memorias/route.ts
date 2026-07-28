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

  const [docs, globalDocs, memories, convs, rotas, playbooks, cartas] = await Promise.all([
    safe<any[]>(sb.from('documents').select('id, file_name, knowledge_class, created_at').eq('company_id', companyId).limit(150)),
    safe<any[]>(sb.from('documents').select('id, knowledge_class').eq('company_id', GK_COMPANY_ID).limit(200)),
    safe<any[]>(sb.from('user_memories').select('*').eq('company_id', companyId).limit(80)),
    safe<any[]>(sb.from('conversations').select('id, user_name, session_id, last_message_at').eq('company_id', companyId).order('last_message_at', { ascending: false }).limit(60)),
    // INTELIGÊNCIA GLOBAL — só o que dá para CONTAR. Nunca `map`, nunca
    // `card_text`. O que sai daqui é nome de pasta e quantidade.
    safe<any[]>(sb.from('ura_maps').select('insurer_key, status').neq('status', 'superseded').limit(400)),
    // Playbooks de conduta: como o melhor atendimento humano é conduzido, por
    // ramo e serviço. Hoje são zero — a síntese estava quebrada e foi
    // corrigida — mas a pasta precisa existir para aparecer no dia em que
    // nascerem, sem ninguém lembrar de mexer aqui de novo.
    safe<any[]>(sb.from('conduct_playbooks').select('ramo, servico, status').limit(400)),
    // Paginado, não `limit(4000)`: o PostgREST devolve no máximo 1.000 linhas
    // por consulta e NÃO avisa. São 926 cartas hoje — cabe. Na semana que vem
    // não cabe, e o cérebro pararia de crescer na tela sem ninguém notar. Foi
    // exatamente esse silêncio que construiu o mapa da Allianz sobre 40% do
    // material em 28/07/2026.
    (async () => {
      const tudo: any[] = [];
      for (let inicio = 0; inicio < 20000; inicio += 1000) {
        const lote = await safe<any[]>(
          // `in_` e não `neq`: existem QUATRO status e só dois são
          // conhecimento vivo. `superseded` são quase-cópias que a curadoria
          // juntou e `rejected_*` foram barradas — contá-las incharia o
          // número sem o cérebro saber nada a mais.
          sb.from('knowledge_cards').select('ramo').in('status', ['pending_review', 'published'])
            .order('created_at', { ascending: true }).range(inicio, inicio + 999));
        tudo.push(...(lote as any[]));
        if ((lote as any[]).length < 1000) break;
      }
      return tudo;
    })(),
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

  // SEGURANÇA (founder 14/07 e 28/07): a camada GLOBAL é a INTELIGÊNCIA da
  // AutoBrokers. A corretora VÊ as pastas e o volume — é o que mostra que
  // existe um cérebro grande operando por trás — e NUNCA vê o conteúdo.
  //
  // Até 28/07/2026 esta camada lia só `documents` da empresa técnica global,
  // que está VAZIA. O resultado é o que o Founder viu na tela: nenhum nó
  // global. Enquanto isso a inteligência real existia e era invisível —
  // 926 cartas de procedimento em curadoria e 9 mapas de rota ativos.
  //
  // O que sai daqui é NOME DE PASTA e QUANTIDADE. Nada mais:
  //   - de `ura_maps`, só `insurer_key` — nunca o `map`;
  //   - de `knowledge_cards`, só `ramo` — nunca o `card_text`;
  //   - de `documents` do acervo global, só `knowledge_class` — nem o
  //     `file_name`, que já é conteúdo.
  //
  // As cartas `rejected_pii` ficam fora inteiras: foram barradas por conter
  // dado de pessoa e não entram nem na contagem.
  const RAMO_LABEL: Record<string, string> = {
    auto: 'Auto', residencial: 'Residencial', vida: 'Vida',
    empresarial: 'Empresarial', outro: 'Outros ramos',
  };
  const pastasGlobais: { tema: string; total: number }[] = [];

  // Uma pasta por seguradora mapeada. `insurer_key` é vocabulário controlado;
  // chaves sujas de importação (`technical__hdi`, `porto/tokio/resulta`) ficam
  // de fora — o nome de uma corretora jamais pode aparecer como pasta global.
  const porSeguradora = new Map<string, number>();
  for (const r of rotas as any[]) {
    const k = String(r?.insurer_key || '').trim().toLowerCase();
    if (!k || k.includes('__') || k.includes('/')) continue;
    porSeguradora.set(k, (porSeguradora.get(k) || 0) + 1);
  }
  for (const [k, n] of Array.from(porSeguradora.entries()).sort((a, b) => b[1] - a[1])) {
    pastasGlobais.push({ tema: `Rotas · ${k.charAt(0).toUpperCase()}${k.slice(1)}`, total: n });
  }

  const porRamo = new Map<string, number>();
  for (const c of cartas as any[]) {
    const r = String(c?.ramo || 'outro').trim().toLowerCase();
    porRamo.set(r, (porRamo.get(r) || 0) + 1);
  }
  for (const [r, n] of Array.from(porRamo.entries()).sort((a, b) => b[1] - a[1])) {
    pastasGlobais.push({ tema: `Procedimentos · ${RAMO_LABEL[r] || 'Outros ramos'}`, total: n });
  }

  const porServico = new Map<string, number>();
  for (const p of playbooks as any[]) {
    const r = String(p?.ramo || '').trim();
    const sv = String(p?.servico || '').trim();
    if (!r || !sv) continue;
    const k = `${RAMO_LABEL[r.toLowerCase()] || r} · ${sv}`;
    porServico.set(k, (porServico.get(k) || 0) + 1);
  }
  for (const [k, n] of Array.from(porServico.entries()).sort((a, b) => b[1] - a[1])) {
    pastasGlobais.push({ tema: `Conduta · ${k}`, total: n });
  }

  const porClasse = new Map<string, number>();
  for (const d of globalDocs as any[]) {
    const c = String(d?.knowledge_class || 'Biblioteca').trim();
    porClasse.set(c, (porClasse.get(c) || 0) + 1);
  }
  for (const [c, n] of Array.from(porClasse.entries()).sort((a, b) => b[1] - a[1])) {
    pastasGlobais.push({ tema: `Biblioteca · ${c}`, total: n });
  }

  // O grafo é uma simulação de forças O(n²) por quadro: desenhar as 935
  // unidades faria a tela travar no notebook do corretor. Cada pasta rende no
  // máximo 24 estrelas, e o total VERDADEIRO viaja em `global_total` para o
  // cabeçalho não mentir para menos.
  const MAX_POR_PASTA = 24;
  const globalMasked: any[] = [];
  let globalTotal = 0;
  for (const p of pastasGlobais) {
    globalTotal += p.total;
    for (let i = 0; i < Math.min(p.total, MAX_POR_PASTA); i++) {
      globalMasked.push({ id: `g-${p.tema}-${i}`, name: `${p.tema} · ${i + 1}`, tema: p.tema, at: null, locked: true });
    }
  }

  return NextResponse.json({
    ok: true,
    company_name: companyName,
    global: globalMasked,
    global_total: globalTotal,
    global_pastas: pastasGlobais.length,
    corretora: (docs as any[]).map((d) => ({ id: `c-${d.id}`, name: humanize(d.file_name), tema: d.knowledge_class || 'Documentos', at: d.created_at })),
    pessoal: (memories as any[]).map((m: any, i: number) => ({ id: `p-${m.id || i}`, name: memoryText(m), tema: 'Você', at: m.created_at })),
    clientes: (convs as any[])
      .filter((c) => !String(c.session_id || '').startsWith('dispatch:'))
      .map((c) => ({ id: `k-${c.id}`, name: c.user_name && c.user_name !== 'Usuário WhatsApp' ? c.user_name : 'Conversa no WhatsApp', tema: 'Clientes', at: c.last_message_at })),
  });
}
