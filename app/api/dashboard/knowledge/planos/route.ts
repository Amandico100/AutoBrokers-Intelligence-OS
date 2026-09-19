// SPEC-EXTRA-001.5 · BLOCO D — o que a base de planos cobre, e a fila de curadoria.
//
// 🔴 A BASE É GLOBAL (D-PILOTO-01): o que a apólice da HDI cobre é o mesmo para
// todas as corretoras. Por isso — e ao contrário de TODA rota vizinha deste
// diretório — este arquivo NÃO manda `company_id` para lugar nenhum. A sessão é
// validada (quem não é da casa não entra), mas o dado não é escopado por
// corretora: dois usuários de corretoras diferentes leem a mesma resposta, e é
// isso que o GATE D prova.
//
// 🔴 SPEC-EXTRA-001.5.1 (E19) — CURADORIA É DE ADMINISTRADOR DA PLATAFORMA.
//
// Até 19/09/2026 publicar/rejeitar exigia `write: true` — papel administrativo
// DA CORRETORA. Dito de outro modo: um admin de UMA corretora publicava a
// afirmação "o Essencial da HDI não inclui vidros" para TODAS as outras, e
// respondia por ela sem saber. A base é global (D-PILOTO-01); quem publica nela
// tem de ser global também.
//
// ⚠️ A corretora comum NÃO perde a leitura: ela continua vendo o que as apólices
// cobrem, em modo leitura, com a frase que diz de onde aquilo vem. O que ela
// deixa de ver é a FILA — que é ferramenta de quem cura, não informação de quem
// consulta — e o que ela deixa de poder é escrever.
//
// O revisor gravado continua vindo da SESSÃO, nunca do corpo: é o nome de quem
// responde por "guincho até 200 km".
import { NextRequest, NextResponse } from 'next/server';
import { assertSameOrigin, requireCompanyMember, requireMasterAdmin } from '@/lib/admin/admin-auth';

//: A frase, em português de gente, que explica por que esta parte da tela não
//: tem botão. ⚠️ Ela é do PRODUTO, não do teste: o guarda a lê daqui.
const AVISO_DE_LEITURA =
  'Este conhecimento é de todas as corretoras e é mantido pela AutoBrokers.';

export const dynamic = 'force-dynamic';

function backend(): { url: string; key: string } | null {
  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) return null;
  return { url, key };
}

// 🔴 SPEC-EXTRA-001.5.1 (D2) — `r.ok` É O QUE FALTAVA, E CUSTOU O PRODUTO.
//
// 📊 18–19/09/2026: `/api/assistance-plans/fila` respondia **500** em produção.
// Esta função fazia `return await r.json()` sem olhar o status, e o `catch`
// devolvia `{ok:false, error}` — um objeto SEM `itens`. Lá na frente,
// `fila.itens || []` transformava os dois casos numa lista vazia, e a tela
// escrevia "Nada esperando revisão" com o contador do topo dizendo 60.
//
// ⚠️ A tela mentindo é pior que a tela quebrada: quem lê "nada esperando"
// fecha a aba e vai embora; quem lê "não consegui carregar" chama alguém.
//
// ⛔ O CORPO DO ERRO NÃO VIAJA. Só o status. Um 500 de FastAPI pode trazer
// traceback, e traceback em tela é vazamento (CLAUDE.md §7, §13.3).
async function chamar(caminho: string, init?: RequestInit) {
  const b = backend();
  if (!b) return { ok: false, error: 'indisponivel' };
  try {
    const r = await fetch(`${b.url}${caminho}`, {
      ...init,
      headers: {
        'X-Internal-Key': b.key,
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      },
      cache: 'no-store',
    });
    if (!r.ok) return { ok: false, status: r.status, error: 'servico_com_erro' };
    const j = await r.json().catch(() => null);
    if (!j || typeof j !== 'object') {
      return { ok: false, status: r.status, error: 'resposta_ilegivel' };
    }
    return j;
  } catch {
    return { ok: false, error: 'indisponivel' };
  }
}

export async function GET(req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  // 🔴 E19: a FILA e a PÁGINA do documento são ferramenta de curadoria — só
  // administrador da plataforma. A COBERTURA é leitura, e é de todos.
  const curador = await requireMasterAdmin();
  const podeCurar = curador.ok === true;

  // 🔴 SPEC-EXTRA-001.5.1 (D5) — A PÁGINA VEM SOB DEMANDA, NA MESMA SESSÃO.
  //
  // 📊 A fila baixava 24 PDFs em série para montar a tela: 65,3 s em produção.
  // Agora ela devolve só as linhas, e a página de UMA linha é pedida quando a
  // pessoa abre aquela linha. É a MESMA rota e a MESMA autorização das vizinhas
  // — uma rota nova só para a página teria de repetir a sessão, a origem e a
  // chave interna, e é assim que uma delas acaba esquecida.
  const servicoId = (req.nextUrl.searchParams.get('servico_id') || '').trim();
  if (servicoId && !podeCurar) {
    return NextResponse.json({ ok: false, error: 'master_required' }, { status: 403 });
  }
  if (servicoId) {
    // ⛔ O id é repassado por `URLSearchParams`, nunca concatenado: um id com
    // `&` ou `?` viraria outro parâmetro na chamada ao backend.
    const q = new URLSearchParams({ servico_id: servicoId }).toString();
    const pagina = await chamar(`/api/assistance-plans/pagina?${q}`);
    return NextResponse.json(pagina);
  }

  const [cobertura, fila] = await Promise.all([
    chamar('/api/assistance-plans/cobertura'),
    // ⛔ Sem papel de plataforma a fila nem é PEDIDA: devolvê-la e esconder no
    // front deixaria o dado trafegar para quem não pode agir sobre ele.
    podeCurar ? chamar('/api/assistance-plans/fila') : Promise.resolve(null),
  ]);
  return NextResponse.json({
    ok: true,
    cobertura,
    fila,
    curadoria_permitida: podeCurar,
    aviso: AVISO_DE_LEITURA,
  });
}

export async function POST(req: NextRequest) {
  const mesmaOrigem = assertSameOrigin(req);
  if (mesmaOrigem) return NextResponse.json(mesmaOrigem, { status: mesmaOrigem.status });
  // 🔴 E19: PUBLICAR e REJEITAR são atos de PLATAFORMA. Era `requireCompanyMember
  // ({ write: true })` — papel da própria corretora — e isso dava a uma
  // corretora o poder de publicar o que vale para todas.
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const corpo = await req.json().catch(() => ({}));
  const out = await chamar('/api/assistance-plans/curadoria', {
    method: 'POST',
    body: JSON.stringify({
      id: corpo?.id,
      acao: corpo?.acao,
      motivo: corpo?.motivo,
      revisado_por: auth.ctx.adminId, // 🔴 da SESSÃO de plataforma, nunca do corpo
    }),
  });
  return NextResponse.json(out);
}
