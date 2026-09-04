// SPEC-095 BLOCO C — o placar: o trabalho feito, sem dizer "trabalhamos muito"
// e sem contar o relógio da plataforma.
//
// 🔴 O DEFEITO QUE ESTA ROTA EXISTE PARA NÃO COMETER. 📊 04/09/2026:
//
//     work_runs da Resulta, na vida          1.229
//     source_type = 'system'                 1.214  (98,86%)
//     pedidos pela corretora (chat+routine)      14
//
// O `system` é o tick: `intelligence.detect_signals` 953 vezes para produzir 32
// sinais, `measure_outcomes` 160, `garimpo` 41, `daily_briefing` 40. As três
// corretoras têm ~1.210 cada porque o número é do RELÓGIO, não delas. Um placar
// ingênuo diria "1.229 trabalhos" e estaria errado por 87×  — e erraria para
// cima, que é a direção em que ninguém confere.
//
// A doc do Zapier (§3 ①) escreve o que NÃO conta como task: "triggers never use
// tasks… polls never use tasks". Aqui a regra é a mesma, e mora numa constante
// com nome.
//
// ⛔ O placar é LEITURA. Não cria tabela, nem contador, nem evento: sete
// contagens `head` sobre tabelas que já existem (📊 as consultas da lista custam
// ~1 ms cada).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

/**
 * 🔴 O que CONTA como trabalho pedido — uma lista de INCLUSÃO, nunca de exclusão.
 *
 * 📊 04/09/2026, o domínio inteiro de `work_runs.source_type` no banco:
 *     system 3.629 · chat 7 · routine 7
 *
 * Escrever `['chat','routine']` e escrever "tudo menos system" dão o mesmo
 * resultado HOJE e resultados opostos amanhã: um `source_type` novo — um
 * conector, uma integração, um robô de portal — entraria na conta por OMISSÃO
 * numa lista de exclusão, e o placar voltaria a inflar sem ninguém mexer nele.
 * Numa lista de inclusão, o valor novo fica de fora até alguém decidir que ele
 * é trabalho que a corretora pediu.
 *
 * As invocações de ferramenta também ficam fora (trava da §2): elas são o meio,
 * não o resultado.
 */
const CONTA_COMO_TRABALHO = ['chat', 'routine'];

/** As janelas, na ordem em que a tela as mostra. `tudo` não tem corte. */
const JANELAS = ['hoje', '7d', '30d', '365d', 'tudo'] as const;
type Janela = (typeof JANELAS)[number];

const DIA = 86_400_000;

/**
 * 00:00 de hoje no fuso da corretora.
 *
 * O contêiner roda em UTC; a corretora trabalha em São Paulo. Contar "hoje" a
 * partir da meia-noite UTC daria ao dono da corretora um dia que começa às 21h
 * da véspera — e o briefing das 08:00 cairia no dia errado três horas por dia.
 * 📊 São Paulo é UTC−03:00 o ano inteiro desde 2019 (o horário de verão acabou
 * pelo decreto 9.772/2019), então o deslocamento é constante e verificável.
 */
function inicioDeHoje(): Date {
  const agora = new Date();
  const [dia, mes, ano] = agora
    .toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' })
    .split('/');
  return new Date(`${ano}-${mes}-${dia}T00:00:00-03:00`);
}

/** O instante a partir do qual cada janela conta. `null` = desde o início. */
function desdeQuando(janela: Janela): string | null {
  const agora = Date.now();
  switch (janela) {
    case 'hoje':
      return inicioDeHoje().toISOString();
    case '7d':
      return new Date(agora - 7 * DIA).toISOString();
    case '30d':
      return new Date(agora - 30 * DIA).toISOString();
    case '365d':
      return new Date(agora - 365 * DIA).toISOString();
    case 'tudo':
    default:
      return null;
  }
}

/**
 * Uma contagem: tabela · coluna de data · corte da janela · o filtro extra.
 *
 * 🔴 Toda consulta leva `.eq('company_id', empresa)` NA FONTE. O backend usa
 * service role: a policy não protege contra um filtro esquecido (CLAUDE.md §7).
 * E todas são `{ count: 'exact', head: true }` — trazer linhas para contar no
 * navegador seria puxar 1.229 registros para imprimir o número 14.
 */
type Contador = (
  tabela: string,
  coluna: string,
  desde: string | null,
  extra?: (q: Consulta) => Consulta,
) => Promise<number>;

/** O encadeamento do supabase-js até o `count` — só os elos que esta rota usa. */
interface Consulta {
  eq(coluna: string, valor: string): Consulta;
  gte(coluna: string, valor: string): Consulta;
  is(coluna: string, valor: null): Consulta;
  in(coluna: string, valores: string[]): Consulta;
  not(coluna: string, operador: string, valor: string): Consulta;
  then(ok: (r: { count: number | null }) => void): void;
}

function criarContador(supabase: unknown, empresa: string): Contador {
  return async (tabela, coluna, desde, extra) => {
    // O cliente tipado do supabase-js não aceita nome de tabela dinâmico; o
    // contrato que importa está em `Consulta`, e é ele que o corpo usa.
    const cliente = supabase as { from(t: string): { select(c: string, o: object): Consulta } };
    let q = cliente
      .from(tabela)
      .select('id', { count: 'exact', head: true })
      .eq('company_id', empresa);
    if (desde) q = q.gte(coluna, desde);
    if (extra) q = extra(q);
    const { count } = (await q) as unknown as { count: number | null };
    return count ?? 0;
  };
}

/** As sete contagens de uma janela. */
async function contarJanela(contar: Contador, desde: string | null) {
  const [relatorios, conversas, deRotina, deAuxiliar, pesquisas, sinais, atividades, trabalhos] =
    await Promise.all([
      // 📊 Resulta: 79 peças na vida, 45 depois da limpeza do B.4. O placar
      // conta a BIBLIOTECA — o que foi arquivado saiu dela, e a peça de teste
      // nunca entrou.
      contar('artifacts', 'created_at', desde, (q) =>
        q.is('archived_at', null).not('tags', 'cs', '{canario}'),
      ),
      contar('conversations', 'created_at', desde),
      // 📊 `routine_runs` NÃO tem `created_at` — a coluna de data dela é
      // `started_at`. Contar pela coluna errada daria zero em silêncio.
      contar('routine_runs', 'started_at', desde),
      contar('auxiliary_runs', 'created_at', desde),
      contar('research_requests', 'created_at', desde),
      contar('intelligence_signals', 'created_at', desde),
      contar('agent_activities', 'created_at', desde),
      contar('work_runs', 'created_at', desde, (q) => q.in('source_type', CONTA_COMO_TRABALHO)),
    ]);

  // "Execuções" é uma palavra do corretor, não uma tabela: as duas formas de
  // uma coisa rodar sozinha somam na mesma linha.
  const contagens = {
    relatorios,
    conversas,
    execucoes: deRotina + deAuxiliar,
    pesquisas,
    sinais,
    atividades,
    trabalhos,
  };
  return {
    ...contagens,
    // A soma sai daqui e não da tela para que o número em destaque e as parcelas
    // que o sustentam venham do mesmo lugar.
    soma: Object.values(contagens).reduce((a, b) => a + b, 0),
  };
}

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const { supabase, ctx } = auth;
  const contar = criarContador(supabase, ctx.companyId);

  const resultados = await Promise.all(
    JANELAS.map((j) => contarJanela(contar, desdeQuando(j))),
  );

  const janelas = Object.fromEntries(
    JANELAS.map((j, i) => [j, resultados[i]]),
  ) as Record<Janela, (typeof resultados)[number]>;

  return NextResponse.json(
    {
      ok: true,
      janelas,
      // A regra viaja com o número. Quem ler a resposta crua — um teste, um
      // suporte, a próxima SPEC — não precisa abrir o código para saber por que
      // 14 e não 1.229.
      regra: 'o relógio da plataforma não conta',
    },
    { headers: { 'Cache-Control': 'no-store' } },
  );
}
