// SPEC-095 — RELATÓRIOS QUE O CORRETOR ENTENDE. O guarda do lado da TELA,
// escrito ANTES do código (protocolo AAA v11.2 §4: quem faz a prova não faz a
// resposta).
//
// 🔴 ESTE ARQUIVO NASCE VERMELHO, E É PARA NASCER. Em `b054b5c` ele imprime o
// GATE ZERO (i) e nove blocos devendo — cada um com a mensagem do que falta. O
// que ele NÃO faz é passar por conveniência: um guarda que nasce verde não
// mediu nada (CLAUDE.md §9.3).
//
// ─────────────────────────────────────────────────────────────────────────────
// O QUE ELE GUARDA — a queixa do Founder de 04/09/2026, medida
// ─────────────────────────────────────────────────────────────────────────────
//
// 📊 SPEC-095 §1, projeto dcajcvlzcjbmyapmklil, 04/09/2026:
//
//     40 pares duplicados na lista da Resulta   o briefing entra DUAS vezes:
//                                               `briefing:` e `artifact:`, mesmo
//                                               href, 3 s de diferença
//     79 peças · 16 títulos distintos           79,7% dos títulos se repetem
//     35 relatórios de teste na biblioteca      100% dos "do chat" são canário
//                                               de execução de SPEC
//    136/136 versões com `data_as_of = now()`   e a tela afirma "Dados de …"
//     25,7% das peças abrem sem produtor        `AUXILIAR_DO_TEMPLATE` conhece
//                                               3 chaves de 7
//
// Nenhum desses defeitos trava nada. Todos respondem 200. É o CLAUDE.md §9.5 na
// tela: **um card que responde errado é silencioso e chega ao corretor.**
//
// ─────────────────────────────────────────────────────────────────────────────
// COMO ELE FUNCIONA — sem rede e sem banco
// ─────────────────────────────────────────────────────────────────────────────
//
// Mesma forma dos dois guardas da SPEC-078 (`entregas-tudo-abre.test.mjs` e
// `entregas-mostra-o-historico.test.mjs`), que continuam valendo e NÃO foram
// alterados: a rota é transpilada com o TypeScript do projeto, carregada com um
// `require` falso e chamada com um dublê de Supabase.
//
// 🔴 E o dublê daqui APLICA OS FILTROS, em vez de só registrá-los. É a
// diferença entre provar que a rota escreveu `.not('tags','cs','{canario}')` e
// provar que o relatório de teste SUMIU da lista. Filtro registrado e não
// aplicado deixaria o bloco [3] verde com a peça de canário na tela.
//
// ⚠️ E ele projeta as colunas como o PostgREST projeta: `select('payload->
// findings')` volta como `{ findings: … }`, pelo ÚLTIMO segmento — nunca como
// `{ payload: { findings: … } }`. 📊 supabase-js 2.58 / postgrest-js 1.21. Sem
// isso o BLOCO E ficaria vazio em silêncio na tela e verde no guarda.
//
// O que não dá para executar (Server Component que depende de `cookies()`, e
// componente de cliente) é conferido na FONTE — e cada guarda de fonte tem uma
// linha de controle sintética provando que ele consegue reprovar.
//
// ─────────────────────────────────────────────────────────────────────────────
// OS BLOCOS, E O QUE CADA UM MATA
// ─────────────────────────────────────────────────────────────────────────────
//
//  [1]  GATE ZERO (i) · A.4a   a publicação COM artifact vira UM card, não dois
//  [2]  A.4a (ramo que fica)   a publicação SEM artifact continua `briefing:`
//  [3]  A.4b/A.4c              canário fora; `?arquivados=1` só os arquivados
//  [4]  A.2/A.3 + E3           tipoHumano · produtor · período · versões · teste
//                              e as 5 colunas novas no SELECT
//  [5]  A.1                    o menu diz "Relatórios"; 6 pilares; key e href iguais
//  [6]  §7 multi-tenant        toda consulta com company_id; nada da corretora B
//  [7]  A.1 + E1               `?tipo=` e a lente padrão; o 4º redirect manda `?tipo=tudo`
//  [8]  BLOCO C + E9           o placar conta o que a corretora PEDIU; nunca o relógio
//  [9]  BLOCO E + E10          o chat PRÉ-PREENCHE, nunca envia sozinho
// [10]  BLOCO E                `?versao=` honrado; a frase "Dados de" some
// [11]  BLOCO E + E5           `payload` só pelo caminho `payload->findings`
// [12]  CONTROLE               cada guarda acima consegue ficar VERMELHO
//
// ─────────────────────────────────────────────────────────────────────────────
// 🔴 MUTAÇÕES — por CÓPIA, e por que elas NÃO rodam sozinhas aqui
// ─────────────────────────────────────────────────────────────────────────────
//
// ⛔ Este guarda NÃO escreve em arquivo de produto. Ele nasceu enquanto DOIS
// builders escreviam `app/`, `lib/` e `components/` no mesmo diretório: mutar
// em disco e restaurar por cópia apagaria a edição de quem estivesse salvando
// naquele segundo. Toda linha de controle aqui é SINTÉTICA e mora em memória —
// mesma superfície, veredito oposto (protocolo §5).
//
// A lista abaixo é para o BUILDER e para a confirmação mecânica, depois que a
// árvore parar. Cada linha: arquivo · o que trocar · qual asserção fica
// vermelha. Uma mutação que não deixa nada vermelho não é mutação: é edição.
//
//   MUTAÇÕES:
//   1. app/api/dashboard/entregas/route.ts
//      tirar `.not('tags', 'cs', '{canario}')` da consulta de `artifacts`
//      → [3] VERMELHO ("a peça de canário está na lista")
//   2. app/api/dashboard/entregas/route.ts
//      tirar `template_key` (ou `subject_ref`, `current_version`, `tags`,
//      `origin`) do `.select(...)` de `artifacts`
//      → [4] VERMELHO (a coluna que sustenta o campo não foi trazida)
//   3. app/api/dashboard/entregas/route.ts
//      voltar a empurrar um card `briefing:` para publicação COM artifact, COM o
//      href do artifact (as DUAS metades do estado de 04/09: só tirar o
//      `continue` deixa o card apontando para a tela do Auxiliar, e o guarda
//      casa por `artifact:{id}` OU por href — 📊 o builder da tela mediu que a
//      metade sozinha fica VERDE)
//      → [1] VERMELHO (dois cards para o mesmo artifact)
//   4. app/api/dashboard/relatorios/placar/route.ts
//      trocar `CONTA_COMO_TRABALHO = ['chat','routine']` por `['chat','routine','system']`
//      → [8] VERMELHO (1.003 em vez de 3)
//   5. app/api/dashboard/relatorios/placar/route.ts
//      tirar o `.gte(coluna, desde)` de uma janela que não é "tudo"
//      → [8] VERMELHO (janela sem corte conta a vida inteira)
//   6. app/dashboard/entregas/[artifactId]/arquivo/route.ts
//      ignorar `searchParams.get('versao')` e sempre pegar a última versão
//      → [10] VERMELHO (`?versao=` não é honrado)
//   7. app/dashboard/entregas/[artifactId]/page.tsx
//      devolver a string `Dados de ` ao JSX
//      → [10] VERMELHO (afirmação de frescor que o sistema não sustenta)
//   8. app/dashboard/entregas/[artifactId]/page.tsx
//      trocar `.select('id, payload->findings')` por `.select('id, payload')`
//      → [11] VERMELHO (o payload inteiro carrega `rotulos_de_produtor`)
//   9. app/dashboard/entregas/[artifactId]/page.tsx
//      trocar `versao.findings` por `versao.payload?.findings`
//      → [11] VERMELHO (o PostgREST projeta pelo ÚLTIMO segmento — E5)
//  10. lib/navigation.ts
//      devolver `label: 'Entregas'` ao item `entregas`
//      → [5] VERMELHO
//  11. app/dashboard/atividades/page.tsx
//      devolver `redirect('/dashboard/entregas')` sem `?tipo=`
//      → [7] VERMELHO (E1 — o 4º redirect herdaria a lente Relatórios e
//        esconderia as atividades de quem salvou o link)
//  12. app/dashboard/chat/page.tsx
//      tirar o zeramento de `textoInicial` de dentro do efeito que espelha a URL
//      → [9] VERMELHO (E10 — o composer é REMONTADO ao primeiro envio e
//        re-semearia a pergunta)
//
// ─────────────────────────────────────────────────────────────────────────────
// ⛔ SEGURANÇA
// ─────────────────────────────────────────────────────────────────────────────
//   · Sem rede, sem banco, sem escrita: o dublê é memória pura.
//   · NENHUM nome de pessoa, CPF, telefone, apólice ou placa nas fixtures. Os
//     rótulos são sentinelas óbvias ("Seguradora Sentinela", "Corretora
//     Vizinha") — se um deles aparecer num lugar onde não devia, o vazamento se
//     lê pelo nome.
//   · Duas corretoras SEMPRE: A é a do teste, B existe para provar que nada
//     dela atravessa (CLAUDE.md §7 — o backend usa service role, e é o filtro
//     no código que protege, não a policy).
//
// Rodar:  npm run test:relatorios
//         node scripts/relatorios-dizem-o-que-sao.test.mjs

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

const EMPRESA = '11111111-1111-1111-1111-111111111111';
const VIZINHA = '22222222-2222-2222-2222-222222222222';

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso.
// ─────────────────────────────────────────────────────────────────────────────

function existe(rel) {
  return fs.existsSync(path.join(RAIZ, rel));
}

function fonte(rel) {
  return fs.readFileSync(path.join(RAIZ, rel), 'utf8');
}

function carregarTS(caminhoRelativo, resolverImport) {
  const js = ts.transpileModule(fonte(caminhoRelativo), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: caminhoRelativo,
  }).outputText;

  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

/**
 * `@/x/y` → o arquivo real, transpilado.
 *
 * 🔴 O resolvedor é GENÉRICO de propósito. O BLOCO A cria `lib/relatorios/
 * tipos.ts` e a rota vai importá-lo; um resolvedor com lista fechada faria o
 * guarda estourar com "import nao previsto" — que é vermelho por endereço
 * errado, não por defeito. Cada módulo resolvido assim é IMPRESSO, para que
 * ninguém confunda "o guarda carregou o mapa real" com "o guarda inventou um".
 */
const CARREGADOS_POR_CAMINHO = [];
function resolverArroba(id) {
  if (!id.startsWith('@/')) return undefined;
  const base = id.slice(2);
  for (const ext of ['.ts', '.tsx', '/index.ts', '/index.tsx']) {
    if (existe(base + ext)) {
      CARREGADOS_POR_CAMINHO.push(base + ext);
      return carregarTS(base + ext, (x) =>
        x === '@supabase/supabase-js' ? {} : resolverArroba(x));
    }
  }
  return undefined;
}

/** O catálogo é carregado DE VERDADE — o mapa de telas tem de ser o do produto. */
const catalogo = carregarTS('lib/auxiliaries/catalog.ts', (id) =>
  id === '@supabase/supabase-js' ? {} : undefined,
);

// ─────────────────────────────────────────────────────────────────────────────
// Dublê de Supabase — encadeamento igual ao do cliente real, e os filtros
// APLICADOS. Registra tabela, colunas, opções e todo predicado.
// ─────────────────────────────────────────────────────────────────────────────

/** `subject_ref->>id` e `payload->evidence_pack->>pack_id` navegam o objeto. */
function valorDe(linha, coluna) {
  if (!/->/.test(coluna)) return linha[coluna];
  const partes = coluna.split(/->>|->/).map((s) => s.replace(/^'|'$/g, ''));
  let v = linha;
  for (const p of partes) {
    if (v == null) return undefined;
    v = v[p];
  }
  return v;
}

/** `'{canario}'` → `['canario']`. É a forma que o PostgREST aceita em `cs`. */
function conjunto(texto) {
  return String(texto ?? '')
    .replace(/^\{|\}$/g, '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function aplicaUm(linha, p) {
  const v = valorDe(linha, p.coluna);
  switch (p.op) {
    case 'eq':
      return String(v) === String(p.valor);
    case 'neq':
      return String(v) !== String(p.valor);
    case 'is':
      return p.valor === null ? v == null : v === p.valor;
    case 'gte':
      return v != null && String(v) >= String(p.valor);
    case 'lte':
      return v != null && String(v) <= String(p.valor);
    case 'in':
      return (p.valor ?? []).map(String).includes(String(v));
    case 'cs':
      return conjunto(p.valor).every((x) => (Array.isArray(v) ? v : []).includes(x));
    case 'not':
      return !aplicaUm(linha, { op: p.sub, coluna: p.coluna, valor: p.valor });
    default:
      return true;
  }
}

/** Projeta como o PostgREST projeta: a coluna vem pelo ÚLTIMO segmento (E4/E5). */
function projetar(linhas, colunas) {
  const lista = String(colunas || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  if (lista.length === 0 || lista.includes('*')) return linhas.map((l) => ({ ...l }));
  return linhas.map((linha) => {
    const saida = {};
    for (const c of lista) {
      const nome = c.split(/->>|->/).pop().replace(/^'|'$/g, '');
      saida[nome] = valorDe(linha, c);
    }
    return saida;
  });
}

function dubleSupabase(linhasPorTabela, registro) {
  return {
    from(tabela) {
      const consulta = { tabela, colunas: '', opcoes: {}, predicados: [], ordem: null, limite: null };
      registro.push(consulta);
      const cadeia = {};
      cadeia.select = (colunas, opcoes) => {
        consulta.colunas = String(colunas ?? '');
        consulta.opcoes = opcoes ?? {};
        return cadeia;
      };
      for (const op of ['eq', 'neq', 'gte', 'lte', 'in', 'is']) {
        cadeia[op] = (coluna, valor) => {
          consulta.predicados.push({ op, coluna, valor });
          return cadeia;
        };
      }
      cadeia.not = (coluna, sub, valor) => {
        consulta.predicados.push({ op: 'not', sub, coluna, valor });
        return cadeia;
      };
      cadeia.order = (coluna, opcoes) => {
        consulta.ordem = { coluna, ascendente: opcoes?.ascending !== false };
        return cadeia;
      };
      cadeia.limit = (n) => {
        consulta.limite = n;
        return cadeia;
      };

      const resolver = () => {
        let linhas = (linhasPorTabela[tabela] ?? []).filter((l) =>
          consulta.predicados.every((p) => aplicaUm(l, p)),
        );
        if (consulta.ordem) {
          const { coluna, ascendente } = consulta.ordem;
          linhas = [...linhas].sort((a, b) => {
            const r = String(a[coluna] ?? '').localeCompare(String(b[coluna] ?? ''));
            return ascendente ? r : -r;
          });
        }
        if (consulta.limite != null) linhas = linhas.slice(0, consulta.limite);
        return linhas;
      };

      cadeia.maybeSingle = () => {
        const l = resolver();
        return Promise.resolve({ data: projetar(l, consulta.colunas)[0] ?? null, error: null });
      };
      cadeia.single = cadeia.maybeSingle;
      cadeia.then = (ok, erro) => {
        const linhas = resolver();
        const o = consulta.opcoes || {};
        // `{ count: 'exact', head: true }` NÃO devolve linha: devolve o número.
        const corpo = o.head
          ? { data: null, count: linhas.length, error: null }
          : {
              data: projetar(linhas, consulta.colunas),
              count: o.count ? linhas.length : null,
              error: null,
            };
        return Promise.resolve(corpo).then(ok, erro);
      };
      return cadeia;
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// A corretora do teste — e a VIZINHA, que existe para não aparecer.
//
// ⛔ Nomes fictícios e óbvios. Nenhum dado de pessoa em lugar nenhum.
// ─────────────────────────────────────────────────────────────────────────────

const A_PULSO = 'aaaaaaaa-0000-4000-8000-000000000001';   // 3 versões
const A_BRIEF = 'aaaaaaaa-0000-4000-8000-000000000002';   // o do briefing de hoje
const A_CANARIO = 'aaaaaaaa-0000-4000-8000-000000000003'; // tags:['canario'] — some
const A_ARQUIVADO = 'aaaaaaaa-0000-4000-8000-000000000004'; // arquivado + canário
const A_SEMANAL = 'aaaaaaaa-0000-4000-8000-000000000005'; // entrega PARCIAL
const A_LEGADO = 'aaaaaaaa-0000-4000-8000-000000000006';  // sem subject_ref → inferido
const A_VIZINHA = 'bbbbbbbb-0000-4000-8000-000000000001'; // 🔴 nunca pode aparecer

const P_HOJE = 'cccccccc-0000-4000-8000-000000000001';    // publicação COM artifact
const P_ONTEM = 'cccccccc-0000-4000-8000-000000000002';   // publicação SEM artifact
const P_SEMANAL = 'cccccccc-0000-4000-8000-000000000003'; // COM artifact, partial

const AUX_CHECKLIST = 'dddddddd-0000-4000-8000-000000000001';

function artifact(extra) {
  return {
    company_id: EMPRESA,
    kind: 'report',
    status: 'ready',
    archived_at: null,
    tags: [],
    subject_ref: {},
    current_version: 1,
    origin: 'chat',
    template_key: null,
    subtitle: null,
    summary: null,
    ...extra,
  };
}

const LINHAS = {
  artifacts: [
    artifact({
      id: A_PULSO,
      // 🔴 O TÍTULO É O ACHADO (BLOCO D). Nada de "Pulso 360 · 2026".
      title: 'Seguradora Sentinela concentra 46,8% da comissão de 2026',
      subtitle: 'Pulso 360 · 2026 · dados lidos em 04/09 02:54',
      template_key: 'executive.pulse360',
      origin: 'chat',
      current_version: 3,
      subject_ref: { kind: 'periodo', id: '2026', label: '2026', produtor: 'autobrokers.chat' },
      created_at: '2026-09-04T02:54:00Z',
    }),
    artifact({
      id: A_BRIEF,
      title: 'Fila acumulada',
      subtitle: '61 atendimentos parados há mais de 24h · e mais 3 pontos',
      template_key: 'briefing.daily_operational',
      origin: 'routine',
      subject_ref: { kind: 'periodo', id: '2026-09-04', label: '04/09', produtor: 'checklist-6h' },
      created_at: '2026-09-04T08:05:00Z',
    }),
    artifact({
      id: A_CANARIO,
      title: 'Raio-X Comercial · 2025',
      subtitle: 'peça gerada por um teste do produto',
      template_key: 'commercial.pipeline',
      origin: 'chat',
      tags: ['canario'],
      subject_ref: { kind: 'periodo', id: '2025', label: '2025' },
      created_at: '2026-09-04T03:10:00Z',
    }),
    artifact({
      id: A_ARQUIVADO,
      title: 'Radar de Renovações · próximos 90 dias',
      subtitle: 'arquivado pela limpeza do B.4',
      template_key: 'renewals.radar',
      origin: 'chat',
      tags: ['canario'],
      archived_at: '2026-09-04T09:00:00Z',
      created_at: '2026-08-18T05:42:00Z',
    }),
    artifact({
      id: A_SEMANAL,
      title: 'Dois pontos de decisão na semana',
      subtitle: 'Resumo da semana · 01/09 a 04/09',
      template_key: 'briefing.weekly_executive',
      origin: 'routine',
      subject_ref: { kind: 'periodo', id: '2026-W36', label: 'semana 36', produtor: 'checklist-6h' },
      created_at: '2026-09-01T08:05:00Z',
    }),
    artifact({
      id: A_LEGADO,
      // 📊 25,7% das peças de hoje abrem sem produtor. Esta é uma delas: sem
      // `subject_ref.produtor`, o mapa infere pelo template e a resposta
      // precisa DIZER que inferiu (`produtorOrigem: 'inferido'`).
      title: 'Cobrança de boletos atrasados',
      subtitle: 'varredura de 2 portais',
      template_key: 'financial.billing_collection',
      origin: 'routine',
      subject_ref: {},
      created_at: '2026-08-30T06:00:00Z',
    }),
    artifact({
      id: A_VIZINHA,
      company_id: VIZINHA,
      title: 'PECA DA CORRETORA VIZINHA — nao pode aparecer',
      template_key: 'executive.pulse360',
      created_at: '2026-09-04T02:00:00Z',
    }),
  ],

  briefing_publications: [
    {
      // 📊 40 pares duplicados hoje. Esta linha é metade de um deles.
      id: P_HOJE,
      company_id: EMPRESA,
      headline: '4 item(ns) esperando você hoje',
      summary_text: 'Nada crítico. 4 pontos para olhar quando puder.',
      briefing_type: 'daily_operational',
      published_at: '2026-09-04T08:05:03Z',
      created_at: '2026-09-04T08:05:03Z',
      delivery_status: 'sent',
      critical_count: 0,
      recommendation_count: 4,
      artifact_id: A_BRIEF,
    },
    {
      // 📊 e 6 das 46 não têm artifact — esse ramo continua vivo (078 F.2).
      id: P_ONTEM,
      company_id: EMPRESA,
      headline: 'Checklist de 03/09',
      summary_text: null,
      briefing_type: 'daily_operational',
      published_at: '2026-09-03T08:05:00Z',
      created_at: '2026-09-03T08:05:00Z',
      delivery_status: 'sent',
      critical_count: 0,
      recommendation_count: 0,
      artifact_id: null,
    },
    {
      id: P_SEMANAL,
      company_id: EMPRESA,
      headline: '2 ponto(s) de decisão e 20 trabalho(s) entregue(s)',
      summary_text: 'A semana fechou com 20 trabalho(s) concluído(s).',
      briefing_type: 'weekly_executive',
      published_at: '2026-09-01T08:05:02Z',
      created_at: '2026-09-01T08:05:02Z',
      // 🔴 O estado vira ETIQUETA; o RESUMO fica (A.3). Hoje
      // `estadoDaEntrega()` SUBSTITUI o resumo — é o defeito que [4] mede.
      delivery_status: 'partial',
      critical_count: 0,
      recommendation_count: 2,
      artifact_id: A_SEMANAL,
    },
    {
      id: 'cccccccc-0000-4000-8000-000000000009',
      company_id: VIZINHA,
      headline: 'BRIEFING DA VIZINHA — nao pode aparecer',
      summary_text: null,
      briefing_type: 'daily_operational',
      published_at: '2026-09-04T08:05:00Z',
      created_at: '2026-09-04T08:05:00Z',
      delivery_status: 'sent',
      artifact_id: null,
    },
  ],

  auxiliary_runs: [
    {
      id: 'eeeeeeee-0000-4000-8000-000000000001',
      company_id: EMPRESA,
      tenant_auxiliary_id: AUX_CHECKLIST,
      status: 'succeeded',
      run_type: 'scheduled',
      error_message: null,
      started_at: '2026-09-04T08:00:00Z',
      finished_at: '2026-09-04T08:04:00Z',
      created_at: '2026-09-04T08:00:00Z',
    },
  ],

  conversations: [
    {
      id: 'ffffffff-0000-4000-8000-000000000001',
      company_id: EMPRESA,
      session_id: 'sessao-sentinela',
      title: 'Como está a Seguradora Sentinela contra o mercado?',
      channel: 'web',
      last_message_preview: 'Segue o comparativo',
      updated_at: '2026-09-04T11:00:00Z',
      created_at: '2026-09-04T10:00:00Z',
    },
    {
      id: 'ffffffff-0000-4000-8000-000000000002',
      company_id: VIZINHA,
      session_id: 'sessao-vizinha',
      title: 'CONVERSA DA VIZINHA — nao pode aparecer',
      channel: 'web',
      last_message_preview: null,
      updated_at: '2026-09-04T11:00:00Z',
      created_at: '2026-09-04T10:00:00Z',
    },
  ],

  agent_activities: [
    {
      id: '99999999-0000-4000-8000-000000000001',
      company_id: EMPRESA,
      category: 'qualidade',
      title: 'Varredura de qualidade concluída — 3 conversa(s)',
      detail: null,
      created_at: '2026-09-04T07:00:00Z',
    },
  ],

  tenant_auxiliaries: [
    { id: AUX_CHECKLIST, company_id: EMPRESA, name: 'Checklist das 6h', slug: 'checklist-6h' },
  ],

  routines: [
    { id: '88888888-0000-4000-8000-000000000001', company_id: EMPRESA, name: 'Cobranca de boletos atrasados', tenant_auxiliary_id: AUX_CHECKLIST },
  ],

  routine_runs: [
    {
      id: '77777777-0000-4000-8000-000000000001',
      company_id: EMPRESA,
      routine_id: '88888888-0000-4000-8000-000000000001',
      status: 'succeeded',
      output_preview: 'Auxiliar de Cobranca — Cobranca de boletos atrasados\nPortais varridos: 2',
      error: null,
      started_at: '2026-09-04T06:00:00Z',
      finished_at: '2026-09-04T06:02:00Z',
    },
  ],
};

// ─────────────────────────────────────────────────────────────────────────────
// Executar a rota da lista
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Um `NextRequest` suficiente. O HEAD ignora o argumento (`_req`); o BLOCO A
 * passa a ler `?arquivados=1` — as duas formas (`nextUrl` e `url`) vão juntas
 * porque a rota pode usar qualquer uma, e adivinhar qual seria vermelho por
 * endereço errado.
 */
function pedido(query = '') {
  const url = `https://teste.local/api/dashboard/entregas${query ? `?${query}` : ''}`;
  return { url, nextUrl: new URL(url) };
}

async function rodarRota(query = '', linhas = LINHAS) {
  const registro = [];
  const supabase = dubleSupabase(linhas, registro);

  const rota = carregarTS('app/api/dashboard/entregas/route.ts', (id) => {
    if (id === 'next/server') {
      return {
        NextResponse: { json: (body, init) => ({ body, status: init?.status ?? 200 }) },
      };
    }
    if (id === '@/lib/admin/admin-auth') {
      return {
        requireCompanyMember: async () => ({
          ok: true,
          ctx: { userId: 'u1', companyId: EMPRESA, role: 'owner', isOwner: true },
          supabase,
        }),
      };
    }
    if (id === '@/lib/auxiliaries/catalog') return catalogo;
    return resolverArroba(id);
  });

  const resposta = await rota.GET(pedido(query));
  return { itens: resposta.body.itens ?? [], corpo: resposta.body, registro };
}

/** O placar (rota NOVA do BLOCO C). Devolve `null` enquanto ela não existir. */
const ROTA_DO_PLACAR = 'app/api/dashboard/relatorios/placar/route.ts';

async function rodarPlacar(linhas) {
  if (!existe(ROTA_DO_PLACAR)) return null;
  const registro = [];
  const supabase = dubleSupabase(linhas, registro);
  const rota = carregarTS(ROTA_DO_PLACAR, (id) => {
    if (id === 'next/server') {
      return {
        NextResponse: { json: (body, init) => ({ body, status: init?.status ?? 200 }) },
      };
    }
    if (id === '@/lib/admin/admin-auth') {
      return {
        requireCompanyMember: async () => ({
          ok: true,
          ctx: { userId: 'u1', companyId: EMPRESA, role: 'owner', isOwner: true },
          supabase,
        }),
      };
    }
    return resolverArroba(id);
  });
  const resposta = await rota.GET(pedido(''));
  return { corpo: resposta.body, registro };
}

// ─────────────────────────────────────────────────────────────────────────────
// Os guardas. Cada um devolve a lista de problemas — vazia é verde.
// ─────────────────────────────────────────────────────────────────────────────

const cardsDeArtifact = (itens) => itens.filter((i) => String(i.id).startsWith('artifact:'));
const acharPorArtifact = (itens, id) =>
  itens.filter((i) => i.id === `artifact:${id}` || i.href === `/dashboard/entregas/${id}`);

/**
 * [1] · GATE ZERO (i) — a publicação COM artifact vira UM card.
 *
 * 📊 04/09/2026: 40 pares na lista da Resulta, 9,8% dela e 32,0% da lente
 * "Documentos". A regra de colapso é a chave DECLARADA do §3 ③: `(artifact_id)`.
 *
 * 🔴 As duas metades importam. "Nada duas vezes" sozinho ficaria verde se
 * alguém apagasse o card do artifact e deixasse o do briefing — que troca um
 * defeito por outro pior: o título do achado desapareceria da lista.
 */
function guardaNadaDuasVezes(itens, publicacoes) {
  const problemas = [];
  const comArtifact = publicacoes.filter((p) => p.company_id === EMPRESA && p.artifact_id);
  if (comArtifact.length === 0) {
    problemas.push('nenhuma publicação COM artifact na fixture — o guarda não percorreu nada');
    return problemas;
  }
  for (const p of comArtifact) {
    const cards = acharPorArtifact(itens, p.artifact_id);
    if (cards.length > 1) {
      problemas.push(
        `o artifact ${String(p.artifact_id).slice(0, 8)} aparece ${cards.length}× na lista ` +
          `(${cards.map((c) => c.id).join(' + ')}) — a publicação ${String(p.id).slice(0, 8)} ` +
          'deveria estar DOBRADA no card do artifact',
      );
      continue;
    }
    if (cards.length === 0) {
      problemas.push(`o artifact ${String(p.artifact_id).slice(0, 8)} sumiu da lista`);
      continue;
    }
    const [card] = cards;
    if (!String(card.id).startsWith('artifact:')) {
      problemas.push(`o card que sobrou é ${card.id} — o que fica é o do ARTIFACT (o título é o achado)`);
    }
    if (card.href !== `/dashboard/entregas/${p.artifact_id}`) {
      problemas.push(`${card.id} não abre o artifact: ${card.href}`);
    }
  }
  // A publicação dobrada leva o produtor dela para o card (A.4a).
  const doBriefing = acharPorArtifact(itens, A_BRIEF)[0];
  if (doBriefing && doBriefing.produtor !== 'Checklist das 6h') {
    problemas.push(
      `o card do briefing perdeu o produtor da publicação: produtor=${JSON.stringify(doBriefing.produtor)}`,
    );
  }
  return problemas;
}

/**
 * [2] · A publicação SEM artifact continua sendo card `briefing:` (078 F.2 migra).
 *
 * 🔴 O guarda olha SÓ as publicações sem `artifact_id`. As que TÊM são assunto
 * do bloco [1] — e misturar as duas populações aqui daria vermelho em `b054b5c`
 * por um defeito que já tem dono, o que é acusar duas vezes o mesmo fato e
 * esconder a regressão de verdade que este bloco existe para pegar: o A.4a
 * apagar o ramo inteiro em vez de dobrar só metade dele.
 */
function guardaBriefingSemArtifactSobrevive(itens, publicacoes) {
  const problemas = [];
  const telaCerta = catalogo.telaDeExecucao('checklist-6h');
  const cartao = '/dashboard/auxiliares/checklist-6h';
  const semArtifact = (publicacoes ?? []).filter((p) => p.company_id === EMPRESA && !p.artifact_id);
  if (semArtifact.length === 0) {
    problemas.push('nenhuma publicação SEM artifact na fixture — o guarda não percorreu nada');
    return problemas;
  }
  for (const p of semArtifact) {
    const card = itens.find((i) => i.id === `briefing:${p.id}`);
    if (!card) {
      problemas.push(
        `a publicação ${String(p.id).slice(0, 8)} não tem artifact e sumiu da lista — ` +
          'o A.4a dobra só a que TEM artifact (078 F.2)',
      );
      continue;
    }
    if (card.href === cartao) {
      problemas.push(`${card.id} leva ao CARTÃO do Auxiliar, não ao trabalho: ${card.href}`);
    } else if (card.href !== telaCerta) {
      problemas.push(`${card.id} com destino inesperado: ${card.href} (esperado ${telaCerta})`);
    }
  }
  return problemas;
}

/** [3] · Canário fora da biblioteca; arquivado só em `?arquivados=1`. */
function guardaNadaDeTeste(itens) {
  const problemas = [];
  if (cardsDeArtifact(itens).length === 0) {
    problemas.push('nenhum card de artifact — o guarda não percorreu nada');
  }
  for (const [id, porque] of [
    [A_CANARIO, 'tem tags @> {canario}: é peça de teste do produto'],
    [A_ARQUIVADO, 'está arquivado'],
  ]) {
    if (acharPorArtifact(itens, id).length > 0) {
      problemas.push(`${String(id).slice(0, 8)} está na biblioteca da corretora e ${porque}`);
    }
  }
  return problemas;
}

function guardaModoArquivados(itens) {
  const problemas = [];
  const arquivado = acharPorArtifact(itens, A_ARQUIVADO)[0];
  if (!arquivado) {
    problemas.push(
      '`?arquivados=1` não devolveu a peça arquivada — sem ela o Founder não tem como ' +
        'olhar (nem desfazer) a limpeza do B.4',
    );
  } else if (arquivado.etiqueta !== 'arquivado') {
    problemas.push(`a peça arquivada veio sem a etiqueta "arquivado": ${JSON.stringify(arquivado.etiqueta)}`);
  }
  // O modo arquivados lista SÓ arquivados (A.4c) — nada de conversa nem trabalho.
  for (const i of itens) {
    if (!String(i.id).startsWith('artifact:')) {
      problemas.push(`\`?arquivados=1\` trouxe ${i.id}, que não é peça arquivável`);
    }
  }
  if (acharPorArtifact(itens, A_PULSO).length > 0) {
    problemas.push('`?arquivados=1` trouxe uma peça VIVA (o Pulso) — o modo lista só os arquivados');
  }
  return problemas;
}

/**
 * [4] · O card diz O QUE É, DE QUEM É, DE QUANDO É — e quantas versões tem.
 *
 * 📊 Hoje `origem` é `a.kind` cru ("report", em inglês) e `AUXILIAR_DO_TEMPLATE`
 * conhece 3 de 7 chaves: 25,7% das peças abrem sem produtor.
 */
const ESPERADO_POR_ARTIFACT = {
  [A_PULSO]: { tipoHumano: 'Pulso 360', versoes: 3, produtorOrigem: 'declarado' },
  [A_BRIEF]: { tipoHumano: 'Briefing do dia', versoes: 1, produtorOrigem: 'declarado', produtor: 'Checklist das 6h' },
  [A_SEMANAL]: { tipoHumano: 'Resumo da semana', versoes: 1, produtorOrigem: 'declarado' },
  [A_LEGADO]: { tipoHumano: 'Cobrança', versoes: 1, produtorOrigem: 'inferido' },
};

function guardaOCardDizOQueE(itens) {
  const problemas = [];
  const cards = cardsDeArtifact(itens);
  if (cards.length === 0) {
    problemas.push('nenhum card de artifact — o guarda não percorreu nada');
    return problemas;
  }
  for (const c of cards) {
    for (const campo of ['tipoHumano', 'produtor', 'periodo']) {
      if (!c[campo] || String(c[campo]).trim() === '') {
        problemas.push(`${c.id} sem ${campo} (é ${JSON.stringify(c[campo])})`);
      }
    }
    if (typeof c.versoes !== 'number') problemas.push(`${c.id} sem \`versoes\` numérico`);
    if (typeof c.teste !== 'boolean') problemas.push(`${c.id} sem \`teste\` booleano`);
    if (!['declarado', 'inferido'].includes(c.produtorOrigem)) {
      problemas.push(
        `${c.id} com produtorOrigem=${JSON.stringify(c.produtorOrigem)} — ` +
          'produtor inferido tem de se declarar inferido (A.2, `legacy_inferred`)',
      );
    }
  }
  for (const [id, esperado] of Object.entries(ESPERADO_POR_ARTIFACT)) {
    const card = acharPorArtifact(itens, id)[0];
    if (!card) {
      problemas.push(`${String(id).slice(0, 8)} não está na lista`);
      continue;
    }
    for (const [campo, valor] of Object.entries(esperado)) {
      if (card[campo] !== valor) {
        problemas.push(
          `${String(id).slice(0, 8)}: ${campo}=${JSON.stringify(card[campo])}, esperado ${JSON.stringify(valor)}`,
        );
      }
    }
  }
  // 🔴 O estado da entrega vira ETIQUETA; o resumo FICA (A.3). Hoje
  // `estadoDaEntrega()` substitui o resumo — e o corretor perde a única linha
  // que dizia o que a peça achou.
  const semanal = acharPorArtifact(itens, A_SEMANAL)[0];
  if (semanal) {
    if (semanal.etiqueta !== 'entrega parcial') {
      problemas.push(`o card de entrega parcial veio com etiqueta ${JSON.stringify(semanal.etiqueta)}`);
    }
    if (semanal.detalhe !== 'Resumo da semana · 01/09 a 04/09') {
      problemas.push(
        `o card de entrega parcial teve o RESUMO substituído pelo estado: ${JSON.stringify(semanal.detalhe)}`,
      );
    }
  }
  // Etiqueta que aparece sempre é etiqueta que ninguém lê (A.3).
  const pulso = acharPorArtifact(itens, A_PULSO)[0];
  if (pulso && pulso.etiqueta) {
    problemas.push(`o Pulso, que está em ordem, ganhou a etiqueta ${JSON.stringify(pulso.etiqueta)}`);
  }
  return problemas;
}

/** [4b] · E3 — as cinco colunas novas no SELECT de `artifacts`. */
const COLUNAS_QUE_SUSTENTAM_O_CARD = ['template_key', 'subject_ref', 'current_version', 'tags', 'origin'];

function guardaSelectDeArtifacts(registro) {
  const problemas = [];
  const consultas = registro.filter((c) => c.tabela === 'artifacts');
  if (consultas.length === 0) {
    problemas.push('a rota não consultou `artifacts` — o guarda não percorreu nada');
    return problemas;
  }
  for (const c of consultas) {
    const colunas = c.colunas.split(',').map((s) => s.trim());
    for (const col of COLUNAS_QUE_SUSTENTAM_O_CARD) {
      if (!colunas.includes(col)) {
        problemas.push(
          `select de artifacts sem \`${col}\` — o campo do card que ela sustenta viria vazio ` +
            `(select atual: ${c.colunas})`,
        );
      }
    }
  }
  return problemas;
}

/** [5] · O menu. A URL, a key e o ícone NÃO mudam; muda o LABEL. */
function guardaOMenuDizRelatorios(navFonte) {
  const problemas = [];
  const bloco = /export const PILLARS[^=]*=\s*\[([\s\S]*?)\n\];/.exec(navFonte);
  if (!bloco) {
    problemas.push('PILLARS não encontrado em lib/navigation.ts');
    return problemas;
  }
  const itens = [...bloco[1].matchAll(/\{\s*key:\s*'([^']+)'[\s\S]*?\}/g)];
  if (itens.length !== 6) {
    problemas.push(`o menu tem ${itens.length} pilares — são 6 (test_menu_nao_cresce.py)`);
  }
  const entregas = itens.map((m) => m[0]).find((s) => /key:\s*'entregas'/.test(s));
  if (!entregas) {
    problemas.push("o pilar `entregas` sumiu do menu — a KEY não muda (§2 das travas)");
    return problemas;
  }
  if (!/href:\s*'\/dashboard\/entregas'/.test(entregas)) {
    problemas.push('a URL /dashboard/entregas mudou — 4 redirects, o `_link()` do chat e 2 guardas apontam para ela');
  }
  if (!/label:\s*'Relatórios'/.test(entregas)) {
    problemas.push(
      `o menu ainda não diz "Relatórios": ${(/label:\s*'([^']*)'/.exec(entregas) || [])[0]}`,
    );
  }
  return problemas;
}

/** [6] · Toda leitura da rota é filtrada por company_id (CLAUDE.md §7). */
function guardaEscopoPorEmpresa(registro) {
  const problemas = [];
  if (registro.length === 0) problemas.push('nenhuma consulta registrada — o guarda não percorreu nada');
  for (const { tabela, predicados } of registro) {
    const tem = (predicados ?? []).some(
      (p) => p.op === 'eq' && p.coluna === 'company_id' && p.valor === EMPRESA,
    );
    if (!tem) problemas.push(`consulta a ${tabela} sem .eq('company_id', empresa)`);
  }
  return problemas;
}

/** [6b] · E nada da corretora VIZINHA atravessou. O filtro é a prova, o dado é a prova final. */
const SENTINELAS_DA_VIZINHA = ['VIZINHA'];

function guardaNadaDaVizinha(corpo) {
  const problemas = [];
  const texto = JSON.stringify(corpo ?? {});
  if (texto.length < 50) problemas.push('resposta vazia — o guarda não percorreu nada');
  for (const marca of SENTINELAS_DA_VIZINHA) {
    if (texto.includes(marca)) {
      problemas.push(`a resposta carrega a sentinela "${marca}" — dado de outra corretora atravessou`);
    }
  }
  if (texto.includes(VIZINHA)) problemas.push('o company_id da corretora vizinha está na resposta');
  return problemas;
}

/** [7] · A lente. `?tipo=` continua valendo, e o padrão passa a ser Relatórios. */
function guardaLenteEFiltros(clienteFonte, redirects) {
  const problemas = [];

  if (!/window\.location\.search/.test(clienteFonte) || !/get\('tipo'\)/.test(clienteFonte)) {
    problemas.push('EntregasClient não lê `?tipo=` da URL');
  }
  const lista = /const FILTROS_DA_URL[^=]*=\s*\[([^\]]*)\]/.exec(clienteFonte);
  if (!lista) {
    problemas.push('FILTROS_DA_URL não encontrado em EntregasClient');
  } else {
    const aceitos = [...lista[1].matchAll(/'([^']+)'/g)].map((m) => m[1]);
    for (const t of ['tudo', 'documento', 'conversa', 'trabalho']) {
      if (!aceitos.includes(t)) problemas.push(`a tela deixou de aceitar ?tipo=${t}`);
    }
    if (redirects.length === 0) problemas.push('nenhum redirect com ?tipo= — o guarda não percorreu nada');
    for (const { arquivo, tipo } of redirects) {
      if (!aceitos.includes(tipo)) {
        problemas.push(`${arquivo} manda ?tipo=${tipo}, que a tela não aceita (aceita: ${aceitos.join(', ')})`);
      }
    }
  }

  // A lente padrão passa a ser Relatórios (A.1 — a queixa é a MISTURA).
  const inicial = /useState<Tipo \| 'tudo'>\('([^']+)'\)/.exec(clienteFonte);
  if (!inicial) {
    problemas.push('não achei o estado inicial do filtro em EntregasClient');
  } else if (inicial[1] !== 'documento') {
    problemas.push(`a lente padrão ainda é '${inicial[1]}' — sem ?tipo= a tela abre em Relatórios`);
  }

  // O chip Pesquisas fica: é o ÚNICO caminho para /dashboard/entregas/pesquisas
  // (test_navegacao_sem_pagina_orfa.py:90).
  if (!clienteFonte.includes('/dashboard/entregas/pesquisas')) {
    problemas.push('o chip "Pesquisas" sumiu — a tela de pesquisas ficaria órfã');
  }
  return problemas;
}

/**
 * [7b] · E1 — o quarto redirect. Ele é o único que NÃO manda `?tipo=`.
 *
 * 📊 `app/dashboard/atividades/page.tsx:17` → `/dashboard/entregas`. Com a
 * lente padrão virando Relatórios, quem salvou o link de Atividades passaria a
 * cair numa lista onde as atividades (`tipo: 'trabalho'`) não aparecem.
 */
function guardaAtividadesMandaTudo(atividadesFonte) {
  const problemas = [];
  const m = /redirect\('([^']*)'\)/.exec(atividadesFonte);
  if (!m) {
    problemas.push('app/dashboard/atividades/page.tsx não redireciona mais');
    return problemas;
  }
  if (m[1] !== '/dashboard/entregas?tipo=tudo') {
    problemas.push(
      `atividades redireciona para '${m[1]}' — sem ?tipo=tudo ele herda a lente Relatórios ` +
        'e esconde exatamente o que a tela absorvida mostrava',
    );
  }
  return problemas;
}

/**
 * [8] · O PLACAR — E9. A constante é de INCLUSÃO, e o dublê prova o número.
 *
 * 📊 04/09/2026, domínio inteiro de `work_runs.source_type`:
 *     system 3.629 · chat 7 · routine 7
 * Um `source_type` novo entraria por OMISSÃO numa lista de exclusão. Por isso
 * `CONTA_COMO_TRABALHO = ('chat','routine')` — e o guarda lê a fonte para
 * garantir que ninguém a inverta.
 */
const JANELAS = ['hoje', '7d', '30d', '365d', 'tudo'];
const CONTAGENS = ['relatorios', 'conversas', 'execucoes', 'pesquisas', 'sinais', 'atividades', 'trabalhos'];

function guardaPlacarNaoContaORelogio(placar) {
  const problemas = [];
  if (!placar) {
    problemas.push(`${ROTA_DO_PLACAR} não existe — o placar do BLOCO C ainda não foi escrito`);
    return problemas;
  }
  const janelas = placar.corpo?.janelas ?? {};
  for (const j of JANELAS) {
    if (!janelas[j]) {
      problemas.push(`a resposta não tem a janela "${j}"`);
      continue;
    }
    for (const c of CONTAGENS) {
      if (typeof janelas[j][c] !== 'number') {
        problemas.push(`janela ${j} sem a contagem "${c}" como número (é ${JSON.stringify(janelas[j][c])})`);
      }
    }
  }
  // 🔴 O número. 1.000 `system` + 3 `chat` + 3 da vizinha → 3.
  const tudo = janelas.tudo ?? {};
  if (tudo.trabalhos !== 3) {
    problemas.push(
      `trabalhos pedidos = ${JSON.stringify(tudo.trabalhos)}, esperado 3. ` +
        'O dublê tem 1.000 execuções `system` (o relógio da plataforma), 3 `chat` da ' +
        'corretora e 3 de outra. 1.003 = o `system` voltou; 6 = o filtro de empresa caiu.',
    );
  }
  // 📊 O esperado sai da FIXTURE, não de um número decorado: o builder da tela
  // mediu que o dublê tem 4 peças vivas e não-canário da EMPRESA (o "2" que
  // estava aqui descrevia uma fixture antiga). Um esperado que se calcula não
  // envelhece quando alguém acrescenta uma linha ao dublê.
  const esperadoRelatorios = (LINHAS.artifacts || []).filter(
    (a) => a.company_id === EMPRESA && !a.archived_at && !(a.tags || []).includes('canario'),
  ).length;
  if (tudo.relatorios !== esperadoRelatorios) {
    problemas.push(
      `relatórios = ${JSON.stringify(tudo.relatorios)}, esperado ${esperadoRelatorios} — o placar ` +
        'não conta canário nem arquivado (só as peças vivas e não-canário da EMPRESA)',
    );
  }
  return problemas;
}

function guardaTodaContagemTemEmpresaEJanela(placar) {
  const problemas = [];
  if (!placar) {
    problemas.push(`${ROTA_DO_PLACAR} não existe — nenhuma consulta para conferir`);
    return problemas;
  }
  const registro = placar.registro;
  if (registro.length === 0) problemas.push('nenhuma consulta registrada — o guarda não percorreu nada');
  let comCorte = 0;
  for (const c of registro) {
    const tem = (p) => (c.predicados ?? []).some(p);
    if (!tem((p) => p.op === 'eq' && p.coluna === 'company_id' && p.valor === EMPRESA)) {
      problemas.push(`contagem em ${c.tabela} sem .eq('company_id', empresa)`);
    }
    if (!c.opcoes?.head || c.opcoes?.count !== 'exact') {
      problemas.push(
        `contagem em ${c.tabela} sem { count: 'exact', head: true } — ela estaria trazendo ` +
          'LINHAS de volta para contar no navegador',
      );
    }
    if (tem((p) => p.op === 'gte')) comCorte += 1;
  }
  // 4 janelas de 5 têm corte; "tudo" não tem, e é por isso que a conta é essa.
  const tabelasDistintas = new Set(registro.map((c) => c.tabela)).size;
  if (comCorte < tabelasDistintas * 4) {
    problemas.push(
      `só ${comCorte} das ${registro.length} consultas têm \`.gte(coluna, desde)\` — ` +
        `são ${tabelasDistintas} tabelas × 4 janelas com corte (a janela "tudo" não tem)`,
    );
  }
  return problemas;
}

function guardaConstanteDeInclusao(placarFonte) {
  const problemas = [];
  const m = /CONTA_COMO_TRABALHO[^=]*=\s*\[([^\]]*)\]/.exec(placarFonte);
  if (!m) {
    problemas.push('a constante CONTA_COMO_TRABALHO não existe na rota do placar');
    return problemas;
  }
  const valores = [...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1]).sort();
  if (JSON.stringify(valores) !== JSON.stringify(['chat', 'routine'])) {
    problemas.push(`CONTA_COMO_TRABALHO = [${valores.join(', ')}] — o esperado é ['chat','routine']`);
  }
  if (/\.neq\(\s*'source_type'|!==?\s*'system'|not\(\s*'source_type'/.test(placarFonte)) {
    problemas.push(
      'a rota exclui `system` em vez de INCLUIR chat/routine — um source_type novo entraria ' +
        'na conta por omissão (§3 ① do Zapier)',
    );
  }
  if (/tool_invocations/.test(placarFonte)) {
    problemas.push('o placar lê `tool_invocations` — está fora (trava da §2)');
  }
  return problemas;
}

/** [8c] · O cliente do placar LÊ a rota; não calcula. */
function guardaPlacarNaoCalculaNaTela(placarTsx) {
  const problemas = [];
  if (placarTsx === null) {
    problemas.push('components/relatorios/Placar.tsx não existe');
    return problemas;
  }
  if (/\.from\(/.test(placarTsx)) {
    problemas.push('Placar.tsx consulta o banco direto (`.from(`) — a conta é da rota, não da tela');
  }
  if (!/fetch\(/.test(placarTsx)) {
    problemas.push('Placar.tsx não chama a rota do placar');
  }
  return problemas;
}

/**
 * [9] · O gancho do chat — E10. PRÉ-PREENCHE, nunca envia.
 *
 * 📊 Um Pulso custa 162 s de InfoCap e uma versão nova. Um efeito que "só
 * manda a pergunta" gastaria isso a cada montagem.
 *
 * 🔴 E o composer é REMONTADO: `page.tsx` monta `const composer` e o renderiza
 * em DUAS posições da árvore. Ao enviar a primeira mensagem o `InputArea`
 * desmonta, remonta e re-semearia a pergunta — por isso o estado "já consumi"
 * mora ACIMA da fronteira de remontagem, no `page.tsx`.
 */
function guardaOChatSoPrePreenche(chatFonte, inputFonte) {
  const problemas = [];

  if (!/get\('pergunta'\)/.test(chatFonte)) {
    problemas.push('app/dashboard/chat/page.tsx não lê `?pergunta=` da URL');
  }
  // Inicializador SÍNCRONO, no molde do `sessionId` — nunca um efeito.
  const inicializador = /useState\(\(\)\s*=>\s*\{[\s\S]*?get\('pergunta'\)[\s\S]*?\}\)/.test(chatFonte);
  if (!inicializador) {
    problemas.push(
      '`?pergunta=` não é lido num inicializador `useState(() => …)` — um efeito chega tarde, ' +
        'depois de o InputArea já ter nascido com texto vazio',
    );
  }
  // ⛔ NENHUM efeito novo envia sozinho.
  for (const m of chatFonte.matchAll(/useEffect\(\s*\(\)\s*=>\s*\{([\s\S]*?)\n  \}/g)) {
    if (/handleSendMessage\s*\(/.test(m[1])) {
      problemas.push('há um useEffect que chama handleSendMessage — o chat NUNCA envia sozinho');
    }
  }
  // O zeramento mora no efeito que já espelha a URL.
  const efeitoDaUrl = /useEffect\(\(\) => \{[\s\S]*?searchParams[\s\S]*?\}, \[[^\]]*\]\);/.exec(chatFonte);
  if (!efeitoDaUrl) {
    problemas.push('não achei o efeito que espelha a URL em app/dashboard/chat/page.tsx');
  } else if (!/setTextoInicial\(\s*''\s*\)|setTextoInicial\(null\)/.test(efeitoDaUrl[0])) {
    problemas.push(
      '`textoInicial` não é zerado dentro do efeito que espelha a URL — no primeiro envio o ' +
        'composer remonta e a pergunta volta sozinha para o campo',
    );
  }
  if (!/initialText/.test(chatFonte)) {
    problemas.push('page.tsx não passa `initialText` ao InputArea');
  }
  if (!/initialText/.test(inputFonte)) {
    problemas.push('components/InputArea/index.tsx não tem a prop `initialText`');
  } else if (!/useState\(\s*initialText\s*\?\?\s*''\s*\)/.test(inputFonte)) {
    problemas.push(
      'InputArea não semeia `initialText` no inicializador do `useState` — semear por efeito ' +
        'apagaria o que o corretor já tivesse digitado',
    );
  }
  return problemas;
}

/** [10] · `?versao=` honrado; e a frase de frescor só quando há frescor. */
function guardaVersaoNoArquivo(arquivoFonte) {
  const problemas = [];
  if (!/searchParams\.get\('versao'\)/.test(arquivoFonte)) {
    problemas.push(
      "arquivo/route.ts não lê `?versao=` — o botão Baixar de uma versão antiga entregaria a ÚLTIMA",
    );
    return problemas;
  }
  const consulta = /\.from\('artifact_versions'\)([\s\S]*?);/.exec(arquivoFonte);
  if (!consulta) {
    problemas.push("arquivo/route.ts não lê `artifact_versions`");
  } else if (!/\.eq\('company_id'/.test(consulta[1])) {
    problemas.push("a consulta de versão em arquivo/route.ts não filtra company_id — `?versao=` de outra corretora abriria");
  }
  return problemas;
}

function guardaSemAfirmacaoDeFrescor(paginaFonte) {
  const problemas = [];
  if (/Dados de /.test(paginaFonte)) {
    problemas.push(
      'a página ainda imprime "Dados de …". 📊 `data_as_of` é `now()` em 136/136 versões, e ' +
        '30 delas estão no FUTURO do próprio `created_at`: é uma afirmação de frescor que o ' +
        'sistema não tem como sustentar',
    );
  }
  const temRotulo = /dados lidos em|gerado em/i.test(paginaFonte);
  if (!temRotulo) {
    problemas.push(
      'a página não tem o rótulo honesto ("dados lidos em" / "período" / "gerado em") — ' +
        'tirar a frase errada sem pôr a certa deixa o corretor sem saber de quando é o número',
    );
  }
  return problemas;
}

/**
 * [11] · O payload é lido pelo caminho, nunca inteiro — e a linha volta pelo
 * ÚLTIMO segmento (E5).
 *
 * 📊 64.246 bytes por versão, 5.890 deles em `rotulos_de_produtor` — o nome do
 * produtor, que não pode sair do Artifact do tenant (SPEC-094 M16).
 */
function guardaPayloadPeloCaminho(paginaFonte) {
  const problemas = [];
  const selects = [...paginaFonte.matchAll(/\.select\(\s*'([^']*payload[^']*)'\s*\)/g)].map((m) => m[1]);
  if (selects.length === 0) {
    problemas.push(
      'a página não lê `payload->findings` — a seção "Próximos passos" do BLOCO E não tem de onde sair',
    );
    return problemas;
  }
  for (const s of selects) {
    for (const col of s.split(',').map((x) => x.trim())) {
      if (col === 'payload') {
        problemas.push(
          `select('${s}') traz o payload INTEIRO — 64 KB por versão, com \`rotulos_de_produtor\` dentro`,
        );
      } else if (col.startsWith('payload') && !/^payload->findings$/.test(col)) {
        problemas.push(`select('${s}') lê \`${col}\`; o único caminho autorizado é \`payload->findings\``);
      }
    }
  }
  if (/\.payload\s*\??\.\s*findings|payload\.findings/.test(paginaFonte)) {
    problemas.push(
      'a página lê `.payload.findings`. ⚠️ 📊 supabase-js 2.58 / postgrest-js 1.21 devolvem a ' +
        'coluna pelo ÚLTIMO segmento: a linha chega como `{ id, findings }`. O caminho errado é ' +
        '`undefined` e a seção fica vazia EM SILÊNCIO',
    );
  }
  return problemas;
}

/** Todo `/dashboard/entregas?tipo=X` escrito em app/. */
function redirectsComTipo(dir = path.join(RAIZ, 'app')) {
  const achados = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      achados.push(...redirectsComTipo(p));
    } else if (/\.(tsx?|jsx?)$/.test(e.name)) {
      const s = fs.readFileSync(p, 'utf8');
      for (const m of s.matchAll(/\/dashboard\/entregas\?tipo=([a-z_-]+)/g)) {
        achados.push({ arquivo: path.relative(RAIZ, p).replace(/\\/g, '/'), tipo: m[1] });
      }
    }
  }
  return achados;
}

// ─────────────────────────────────────────────────────────────────────────────
// O placar do guarda
//
// 🔴 Três verbos, e a diferença entre eles é o que impede tanto o carimbo
// quanto o alarme falso:
//
//   checar()   asserção de verdade. Vermelho aqui é DEFEITO, e o exit code é 1.
//   devendo()  a SPEC-095 ainda não entregou este bloco. Imprime VERMELHO
//              ESPERADO com o item do GATE ZERO ao lado, CONTA, e o gate final
//              da SPEC só fecha com esta lista VAZIA. O exit code NÃO é 1 —
//              porque dois builders rodam a suíte inteira o tempo todo, em
//              paralelo, e um vermelho permanente apagaria a diferença entre
//              "a SPEC ainda deve o BLOCO C" e "alguém quebrou o produto"
//              (é a mesma decisão, e a mesma razão, de
//              `backend/tests/test_a_fabrica_de_relatorios.py`).
//   controle() a entrada que o guarda TEM de reprovar. Verde aqui é o guarda
//              anunciando que não guarda nada (CLAUDE.md §9.3).
// ─────────────────────────────────────────────────────────────────────────────

const falhas = [];
const esperados = [];
const jaPodemVirar = [];

function checar(problemas, nome) {
  if (problemas.length === 0) {
    console.log(`  OK  ${nome}`);
  } else {
    falhas.push(nome);
    console.log(`  X   ${nome}`);
    for (const p of problemas) console.log(`        ${p}`);
  }
}

function devendo(problemas, nome, bloco) {
  if (problemas.length === 0) {
    console.log(`  OK  ${nome}`);
    jaPodemVirar.push(`${nome}   [era devendo('${bloco}')]`);
  } else {
    esperados.push(`${nome}   (esperado ate ${bloco})`);
    console.log(`  VERMELHO-ESPERADO  ${nome}   (ate ${bloco})`);
    for (const p of problemas) console.log(`        ${p}`);
  }
}

function controle(problemas, nome) {
  if (problemas.length > 0) {
    console.log(`  OK  CONTROLE ${nome} — o guarda acusou (${problemas.length})`);
  } else {
    falhas.push(`CONTROLE ${nome}`);
    console.log(`  X   CONTROLE ${nome} — o guarda NAO acusou; ele nao guarda nada`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Execução
// ─────────────────────────────────────────────────────────────────────────────

console.log('='.repeat(78));
console.log('RELATORIOS DIZEM O QUE SAO — o card, o placar e o detalhe  (SPEC-095)');
console.log('='.repeat(78));

const { itens, corpo, registro } = await rodarRota();
console.log(
  `\nA rota devolveu ${itens.length} itens · ${registro.length} consultas · ` +
    `${cardsDeArtifact(itens).length} cards de artifact`,
);
for (const i of itens.filter((x) => /^(artifact|briefing):/.test(String(x.id)))) {
  console.log(`      ${i.id}  →  ${i.href}`);
}

console.log('\n[1] GATE ZERO (i) — a publicacao COM artifact vira UM card, nao dois');
checar(
  guardaNadaDuasVezes(itens, LINHAS.briefing_publications),
  'o briefing de hoje aparece UMA vez, no card do artifact');

console.log('\n[2] A publicacao SEM artifact continua sendo card `briefing:`  (078 F.2 migra)');
checar(
  guardaBriefingSemArtifactSobrevive(itens, LINHAS.briefing_publications),
  'briefing sem artifact aponta para a tela de execucao do Auxiliar',
);

console.log('\n[3] Nada de teste, nada de arquivado — e `?arquivados=1` mostra o que foi limpo');
checar(guardaNadaDeTeste(itens), 'peca de canario e peca arquivada fora da biblioteca');
const arquivados = await rodarRota('arquivados=1');
checar(
  guardaModoArquivados(arquivados.itens),
  '`?arquivados=1` lista SO os arquivados, com etiqueta');

console.log('\n[4] O card diz o que e, de quem e, de quando e — e quantas versoes tem');
checar(guardaOCardDizOQueE(itens), 'tipoHumano · produtor · periodo · versoes · teste · etiqueta');
checar(
  guardaSelectDeArtifacts(registro),
  'o SELECT de artifacts traz as 5 colunas que sustentam o card');

console.log('\n[5] O menu diz "Relatorios" — e a URL, a key e os 6 pilares nao mudam');
const NAV = fonte('lib/navigation.ts');
checar(guardaOMenuDizRelatorios(NAV), 'lib/navigation.ts: label Relatorios, key entregas, 6 pilares');

console.log('\n[6] Multi-tenant: toda consulta com company_id, e nada da corretora vizinha');
console.log(`      ${registro.length} consultas: ${registro.map((r) => r.tabela).join(', ')}`);
checar(guardaEscopoPorEmpresa(registro), 'nenhuma consulta da rota sem filtro de empresa');
checar(guardaNadaDaVizinha(corpo), 'nenhuma linha da corretora vizinha na resposta');
checar(guardaNadaDaVizinha(arquivados.corpo), 'nem no modo arquivados');

console.log('\n[7] A lente: `?tipo=` continua valendo e o padrao passa a ser Relatorios');
const CLIENTE = fonte('app/dashboard/entregas/EntregasClient.tsx');
const REDIRECTS = redirectsComTipo();
for (const r of REDIRECTS) console.log(`      ${r.arquivo} → ?tipo=${r.tipo}`);
checar(guardaLenteEFiltros(CLIENTE, REDIRECTS), 'a tela le ?tipo=, aceita os 4, e abre em Relatorios');
checar(
  guardaAtividadesMandaTudo(fonte('app/dashboard/atividades/page.tsx')),
  'o 4o redirect manda ?tipo=tudo (E1)');

console.log('\n[8] O placar conta o que a corretora PEDIU — nunca o relogio da plataforma');
// 📊 04/09/2026: `work_runs.source_type` no domínio inteiro = system 3.629 ·
// chat 7 · routine 7. O dublê exagera a proporção de propósito: se o `system`
// voltar, o número salta de 3 para 1.003 e ninguém consegue não ver.
const RELOGIO = Array.from({ length: 1000 }, (_, n) => ({
  id: `sys-${n}`,
  company_id: EMPRESA,
  source_type: 'system',
  created_at: '2026-09-04T02:00:00Z',
}));
const PEDIDOS = [
  { id: 'w1', company_id: EMPRESA, source_type: 'chat', created_at: '2026-09-04T09:00:00Z' },
  { id: 'w2', company_id: EMPRESA, source_type: 'chat', created_at: '2026-09-03T09:00:00Z' },
  { id: 'w3', company_id: EMPRESA, source_type: 'routine', created_at: '2026-08-20T09:00:00Z' },
  { id: 'w4', company_id: VIZINHA, source_type: 'chat', created_at: '2026-09-04T09:00:00Z' },
  { id: 'w5', company_id: VIZINHA, source_type: 'chat', created_at: '2026-09-04T09:00:00Z' },
  { id: 'w6', company_id: VIZINHA, source_type: 'routine', created_at: '2026-09-04T09:00:00Z' },
];
const LINHAS_DO_PLACAR = {
  ...LINHAS,
  work_runs: [...RELOGIO, ...PEDIDOS],
  research_requests: [{ id: 'p1', company_id: EMPRESA, created_at: '2026-09-01T09:00:00Z' }],
  intelligence_signals: [{ id: 's1', company_id: EMPRESA, created_at: '2026-09-04T09:00:00Z' }],
};
const placar = await rodarPlacar(LINHAS_DO_PLACAR);
console.log(`      ${ROTA_DO_PLACAR}: ${placar ? 'existe' : 'AINDA NAO EXISTE'}`);
if (placar) console.log(`      ${placar.registro.length} consultas de contagem`);
checar(guardaPlacarNaoContaORelogio(placar), '5 janelas × 7 contagens, e trabalhos pedidos = 3');
checar(guardaTodaContagemTemEmpresaEJanela(placar), 'toda contagem com company_id, count exact e janela');
checar(
  guardaConstanteDeInclusao(existe(ROTA_DO_PLACAR) ? fonte(ROTA_DO_PLACAR) : ''),
  "CONTA_COMO_TRABALHO = ['chat','routine'] — inclusao, nunca exclusao (E9)");
checar(
  guardaPlacarNaoCalculaNaTela(existe('components/relatorios/Placar.tsx') ? fonte('components/relatorios/Placar.tsx') : null),
  'Placar.tsx le a rota e nao calcula nada');

console.log('\n[9] O chat PRE-PREENCHE a pergunta — e nunca envia sozinho  (E10)');
checar(
  guardaOChatSoPrePreenche(fonte('app/dashboard/chat/page.tsx'), fonte('components/InputArea/index.tsx')),
  'inicializador sincrono, zeramento no efeito da URL, prop initialText, zero envio automatico');

console.log('\n[10] O detalhe: `?versao=` honrado, e a data do dado e a do dado');
const PAGINA = fonte('app/dashboard/entregas/[artifactId]/page.tsx');
const ARQUIVO = fonte('app/dashboard/entregas/[artifactId]/arquivo/route.ts');
checar(guardaVersaoNoArquivo(ARQUIVO), 'arquivo/route.ts baixa a VERSAO pedida, com company_id');
checar(guardaSemAfirmacaoDeFrescor(PAGINA), 'a pagina nao afirma "Dados de" sem ter a data do dado');

console.log('\n[11] O payload so pelo caminho `payload->findings` — e lido pelo ultimo segmento');
checar(guardaPayloadPeloCaminho(PAGINA), "select('id, payload->findings') e leitura por `.findings`");

console.log('\n[12] LINHAS DE CONTROLE — cada guarda acima consegue ficar VERMELHO');

const CARD_BOM = {
  id: `artifact:${A_BRIEF}`,
  href: `/dashboard/entregas/${A_BRIEF}`,
  produtor: 'Checklist das 6h',
  tipoHumano: 'Briefing do dia',
  periodo: '04/09',
  versoes: 1,
  teste: false,
  produtorOrigem: 'declarado',
  detalhe: 'x',
};

controle(
  guardaNadaDuasVezes(
    [CARD_BOM, { id: `briefing:${P_HOJE}`, href: `/dashboard/entregas/${A_BRIEF}` }],
    LINHAS.briefing_publications,
  ),
  'o mesmo artifact com dois cards (o defeito de hoje)',
);
controle(
  guardaNadaDuasVezes([{ id: `briefing:${P_HOJE}`, href: `/dashboard/entregas/${A_BRIEF}` }], LINHAS.briefing_publications),
  'o card que sobrou e o do briefing, nao o do artifact',
);
controle(guardaNadaDuasVezes([], LINHAS.briefing_publications), 'lista vazia');
controle(
  guardaBriefingSemArtifactSobrevive(
    [{ id: `briefing:${P_ONTEM}`, href: '/dashboard/auxiliares/checklist-6h' }],
    LINHAS.briefing_publications,
  ),
  'briefing apontando para o cartao do Auxiliar',
);
controle(
  guardaBriefingSemArtifactSobrevive([CARD_BOM], LINHAS.briefing_publications),
  'o ramo `briefing:` desapareceu da lista',
);
controle(
  guardaBriefingSemArtifactSobrevive(itens, LINHAS.briefing_publications.filter((p) => p.artifact_id)),
  'fixture sem nenhuma publicacao SEM artifact — o guarda nao percorreria nada',
);
controle(
  guardaNadaDeTeste([{ id: `artifact:${A_CANARIO}`, href: `/dashboard/entregas/${A_CANARIO}` }]),
  'peca de canario na biblioteca da corretora',
);
controle(guardaModoArquivados([]), 'modo arquivados sem a peca arquivada');
controle(
  guardaModoArquivados([{ id: `artifact:${A_ARQUIVADO}`, href: `/dashboard/entregas/${A_ARQUIVADO}` }]),
  'peca arquivada sem a etiqueta "arquivado"',
);
controle(
  guardaModoArquivados([
    { id: `artifact:${A_ARQUIVADO}`, href: `/dashboard/entregas/${A_ARQUIVADO}`, etiqueta: 'arquivado' },
    { id: 'conversa:x', href: '/dashboard/chat' },
  ]),
  'modo arquivados trazendo conversa junto',
);
controle(guardaOCardDizOQueE([{ ...CARD_BOM, tipoHumano: '' }]), 'card com tipoHumano vazio');
controle(guardaOCardDizOQueE([{ ...CARD_BOM, produtorOrigem: undefined }]), 'card sem produtorOrigem');
controle(
  guardaOCardDizOQueE([
    { ...CARD_BOM, id: `artifact:${A_SEMANAL}`, href: `/dashboard/entregas/${A_SEMANAL}`, etiqueta: 'entrega parcial', detalhe: 'Entregue em parte — um dos canais falhou' },
  ]),
  'o estado da entrega SUBSTITUINDO o resumo (o defeito de hoje)',
);
controle(guardaOCardDizOQueE([]), 'nenhum card');
controle(
  guardaSelectDeArtifacts([
    { tabela: 'artifacts', colunas: 'id, title, subtitle, kind, status, created_at', predicados: [] },
  ]),
  'select de artifacts sem as colunas novas (o de hoje)',
);
controle(guardaSelectDeArtifacts([]), 'rota que nao consulta artifacts');
controle(
  guardaOMenuDizRelatorios(NAV.replace(/label: 'Relatórios'/, "label: 'Entregas'")),
  'o menu voltando a dizer "Entregas"',
);
controle(
  guardaOMenuDizRelatorios(
    NAV.replace(
      /\n\];/,
      "\n  { key: 'novo', label: 'Novo', href: '/dashboard/novo', icon: 'x' },\n];",
    ),
  ),
  'um setimo pilar no menu',
);
controle(
  guardaEscopoPorEmpresa([{ tabela: 'artifacts', predicados: [{ op: 'eq', coluna: 'status', valor: 'ready' }] }]),
  'consulta sem company_id',
);
controle(guardaEscopoPorEmpresa([]), 'rota que nao consultou nada');
controle(
  guardaNadaDaVizinha({ itens: [{ titulo: 'PECA DA CORRETORA VIZINHA — nao pode aparecer' }], enchimento: 'x'.repeat(60) }),
  'linha de outra corretora na resposta',
);
controle(
  guardaLenteEFiltros("const FILTROS_DA_URL = ['tudo','documento','conversa','trabalho'];", REDIRECTS),
  'cliente que nao le a URL',
);
controle(
  guardaLenteEFiltros(CLIENTE, [{ arquivo: 'sintetico/page.tsx', tipo: 'pesquisa' }]),
  'redirect mandando um ?tipo= que a tela nao aceita',
);
controle(guardaAtividadesMandaTudo("redirect('/dashboard/entregas');"), 'atividades redirecionando sem ?tipo=');
controle(guardaAtividadesMandaTudo('// nada aqui'), 'atividades sem redirect nenhum');
controle(guardaPlacarNaoContaORelogio(null), 'placar inexistente');
controle(
  guardaPlacarNaoContaORelogio({
    corpo: {
      janelas: Object.fromEntries(
        JANELAS.map((j) => [j, Object.fromEntries(CONTAGENS.map((c) => [c, c === 'trabalhos' ? 1003 : 2]))]),
      ),
    },
    registro: [],
  }),
  'placar contando o relogio da plataforma (1.003 em vez de 3)',
);
controle(
  guardaPlacarNaoContaORelogio({
    corpo: { janelas: { hoje: Object.fromEntries(CONTAGENS.map((c) => [c, 0])) } },
    registro: [],
  }),
  'placar com uma janela so',
);
controle(
  guardaTodaContagemTemEmpresaEJanela({
    registro: [{ tabela: 'work_runs', opcoes: { count: 'exact', head: true }, predicados: [{ op: 'gte', coluna: 'created_at', valor: 'x' }] }],
  }),
  'contagem sem company_id',
);
controle(
  guardaTodaContagemTemEmpresaEJanela({
    registro: [{ tabela: 'work_runs', opcoes: {}, predicados: [{ op: 'eq', coluna: 'company_id', valor: EMPRESA }] }],
  }),
  'contagem que traz linhas em vez de count exact',
);
controle(guardaConstanteDeInclusao("const CONTA_COMO_TRABALHO = ['chat','routine','system'];"), '`system` de volta na constante');
controle(
  guardaConstanteDeInclusao("const CONTA_COMO_TRABALHO = ['chat','routine'];\nq.neq('source_type', 'system');"),
  'lista de EXCLUSAO em vez de inclusao',
);
controle(guardaConstanteDeInclusao('// rota sem constante nenhuma'), 'rota sem a constante');
controle(guardaPlacarNaoCalculaNaTela(null), 'Placar.tsx inexistente');
controle(
  guardaPlacarNaoCalculaNaTela("const { data } = await supabase.from('work_runs').select('id');"),
  'Placar.tsx consultando o banco direto',
);
controle(
  guardaOChatSoPrePreenche(
    "const [p] = useState(() => { new URLSearchParams(x).get('pergunta'); });\n" +
      '  useEffect(() => {\n    handleSendMessage(p);\n  }, []);\n' +
      '  useEffect(() => { const url = new URL(location.href); url.searchParams.set("session", s); }, [s]);\n' +
      '  initialText={p}',
    "const [message, setMessage] = useState(initialText ?? '');\ninitialText",
  ),
  'um efeito do chat que ENVIA a pergunta sozinho',
);
controle(
  guardaOChatSoPrePreenche(
    "const [p] = useState(() => { new URLSearchParams(x).get('pergunta'); });\n" +
      '  useEffect(() => { const url = new URL(location.href); url.searchParams.set("session", s); }, [s]);\n' +
      '  initialText={p}',
    "const [message, setMessage] = useState(initialText ?? '');\ninitialText",
  ),
  'chat sem o zeramento de textoInicial no efeito da URL',
);
controle(
  guardaOChatSoPrePreenche('// chat que nao le a URL', "useState(initialText ?? '')\ninitialText"),
  'chat que nao le ?pergunta=',
);
controle(
  guardaVersaoNoArquivo("const { data } = await supabase.from('artifact_versions').select('id').order('version');"),
  'arquivo/route.ts ignorando ?versao= (o de hoje)',
);
controle(
  guardaVersaoNoArquivo(
    "const v = req.nextUrl.searchParams.get('versao');\n" +
      "const { data } = await supabase.from('artifact_versions').select('id').eq('id', v);",
  ),
  'consulta de versao sem company_id',
);
controle(guardaSemAfirmacaoDeFrescor('<p>Dados de {dataLonga(v.data_as_of)}.</p>'), 'a string "Dados de" de volta');
controle(guardaSemAfirmacaoDeFrescor('<p>{versao.version}</p>'), 'pagina sem nenhum rotulo de data');
controle(
  guardaPayloadPeloCaminho("await supabase.from('artifact_versions').select('id, payload').eq('id', v);"),
  "select('payload') inteiro",
);
controle(
  guardaPayloadPeloCaminho(
    "await supabase.from('artifact_versions').select('id, payload->findings');\nconst f = versao.payload?.findings;",
  ),
  'leitura por `.payload.findings` (o caminho que o PostgREST nao devolve)',
);
controle(guardaPayloadPeloCaminho('// pagina que nao le payload nenhum'), 'pagina sem a secao de proximos passos');

if (CARREGADOS_POR_CAMINHO.length > 0) {
  console.log(`\n      modulos do produto carregados pelo resolvedor: ${[...new Set(CARREGADOS_POR_CAMINHO)].join(', ')}`);
}

console.log(`\n${'='.repeat(78)}`);
console.log(
  `  ${falhas.length} falha(s) de verdade · ${esperados.length} VERMELHO ESPERADO · ` +
    `${jaPodemVirar.length} ja podem virar`,
);
if (esperados.length > 0) {
  console.log('\n  🔴 VERMELHO ESPERADO — a SPEC-095 PREVE estes ate o bloco citado.');
  console.log('     O GATE ZERO desta SPEC e exatamente esta lista em `b054b5c`.');
  for (const x of esperados) console.log(`     · ${x}`);
}
if (jaPodemVirar.length > 0) {
  console.log('\n  ✅ ESTES JA FICARAM VERDES. O integrador troca `devendo(...)` por `checar(...)`');
  console.log('     e apaga o argumento do bloco — senao o guarda passa a guardar verdade');
  console.log('     vencida (CLAUDE.md §9.3):');
  for (const x of jaPodemVirar) console.log(`     · ${x}`);
}
if (falhas.length > 0) {
  console.log(`\n  ⛔ ${falhas.length} VERMELHO DE VERDADE:`);
  for (const f of falhas) console.log(`     - ${f}`);
  process.exit(1);
}
if (esperados.length > 0) {
  console.log(
    `\n  (exit 0 com ${esperados.length} VERMELHO ESPERADO e 0 de verdade: o gate FINAL da\n` +
      '   SPEC-095 so fecha com a lista acima VAZIA — protocolo v11.2, opcao B)',
  );
} else {
  console.log('\nVERDE — o card diz o que e, o placar nao conta o relogio, e o detalhe nao mente a data.');
}
