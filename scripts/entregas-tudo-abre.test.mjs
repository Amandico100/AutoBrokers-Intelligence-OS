// SPEC-078 F.4 — TODA linha de Entregas abre.
//
// A queixa literal do Founder em 17/08/2026 foi "não consigo acessar as coisas
// que ficam prontas". Medida, ela era isto:
//
//     📊 36 artifacts        href: null    não existia rota de visualização
//     📊 77 briefings        href errado   `/dashboard/auxiliares/checklist-6h`
//                                          cai na rota [slug] e renderiza o
//                                          CARTÃO DESCRITIVO, não o briefing
//     📊 135 agent_activities href: null   nenhum destino
//
// Um href errado é pior que um href faltando: o corretor clica, chega numa tela
// plausível, e conclui que o produto não guardou o trabalho dele.
//
// COMO ESTE TESTE FUNCIONA — sem rede e sem banco.
//
// Ele não relê a intenção do código nem procura strings: ele EXECUTA a rota de
// verdade. `app/api/dashboard/entregas/route.ts` é transpilado com o TypeScript
// que já está no projeto, carregado com um `require` falso, e chamado com um
// dublê de Supabase que devolve linhas fixas. O que sai é a mesma lista que o
// navegador receberia.
//
// Por isso ele pega o defeito de VERDADE: se alguém voltar a escrever
// `href: null`, ou concatenar `/dashboard/auxiliares/${slug}` à mão, a saída
// muda e o guarda acusa.
//
// E a LINHA DE CONTROLE (CLAUDE.md §9.2): cada guarda é rodado também contra
// uma entrada que ele DEVE reprovar. Um guarda que não tem como falhar não
// guarda nada — e um teste que não percorre nada passaria igual.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

const EMPRESA = '11111111-1111-1111-1111-111111111111';

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso.
// ─────────────────────────────────────────────────────────────────────────────

function carregarTS(caminhoRelativo, resolverImport) {
  const fonte = fs.readFileSync(path.join(RAIZ, caminhoRelativo), 'utf8');
  const js = ts.transpileModule(fonte, {
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

/** O catálogo é carregado DE VERDADE — o mapa de telas tem de ser o do produto. */
const catalogo = carregarTS('lib/auxiliaries/catalog.ts', (id) =>
  id === '@supabase/supabase-js' ? {} : undefined,
);

// ─────────────────────────────────────────────────────────────────────────────
// Dublê de Supabase: encadeamento igual ao do cliente real, linhas fixas.
// ─────────────────────────────────────────────────────────────────────────────

function dubleSupabase(linhasPorTabela, registro) {
  return {
    from(tabela) {
      const filtros = [];
      registro.push({ tabela, filtros });
      const cadeia = {};
      for (const m of ['select', 'order', 'limit', 'is', 'not', 'in', 'gte', 'lte', 'neq']) {
        cadeia[m] = () => cadeia;
      }
      cadeia.eq = (coluna, valor) => {
        filtros.push([coluna, valor]);
        return cadeia;
      };
      cadeia.then = (ok, erro) =>
        Promise.resolve({ data: linhasPorTabela[tabela] ?? [], error: null }).then(ok, erro);
      return cadeia;
    },
  };
}

/** Uma corretora com as cinco fontes povoadas, e todas com destino possível. */
const LINHAS = {
  artifacts: [
    {
      id: 'aaaaaaaa-0000-4000-8000-000000000001',
      title: 'Relatório executivo da semana',
      subtitle: 'Carteira e inadimplência',
      kind: 'report',
      status: 'ready',
      created_at: '2026-08-16T09:00:00Z',
    },
  ],
  briefing_publications: [
    // 📊 36 das 77 publicações reais têm artifact_id — o relatório daquele dia.
    {
      id: 'bbbbbbbb-0000-4000-8000-000000000001',
      headline: 'Checklist de 16/08',
      summary_text: 'Três renovações vencem hoje',
      briefing_type: 'daily_operational',
      published_at: '2026-08-16T09:05:00Z',
      created_at: '2026-08-16T09:05:00Z',
      delivery_status: 'sent',
      artifact_id: 'aaaaaaaa-0000-4000-8000-000000000001',
    },
    // 📊 e 41 não têm — essas precisam da TELA DE EXECUÇÃO do Auxiliar.
    {
      id: 'bbbbbbbb-0000-4000-8000-000000000002',
      headline: 'Checklist de 15/08',
      summary_text: null,
      briefing_type: 'daily_operational',
      published_at: '2026-08-15T09:05:00Z',
      created_at: '2026-08-15T09:05:00Z',
      delivery_status: 'sent',
      artifact_id: null,
    },
  ],
  auxiliary_runs: [
    {
      id: 'cccccccc-0000-4000-8000-000000000001',
      tenant_auxiliary_id: 'tttttttt-0000-4000-8000-000000000001',
      status: 'succeeded',
      run_type: 'scheduled',
      error_message: null,
      started_at: '2026-08-16T09:00:00Z',
      finished_at: '2026-08-16T09:04:00Z',
      created_at: '2026-08-16T09:00:00Z',
    },
    {
      id: 'cccccccc-0000-4000-8000-000000000002',
      tenant_auxiliary_id: 'tttttttt-0000-4000-8000-000000000002',
      status: 'failed',
      run_type: 'manual',
      error_message: 'portal fora do ar',
      started_at: '2026-08-16T06:00:00Z',
      finished_at: '2026-08-16T06:01:00Z',
      created_at: '2026-08-16T06:00:00Z',
    },
  ],
  conversations: [
    {
      id: 'dddddddd-0000-4000-8000-000000000001',
      session_id: 'sessao-1',
      title: 'Cotação para frota',
      channel: 'web',
      last_message_preview: 'Segue a cotação',
      updated_at: '2026-08-16T11:00:00Z',
      created_at: '2026-08-16T10:00:00Z',
    },
    {
      id: 'dddddddd-0000-4000-8000-000000000002',
      session_id: 'sessao-2',
      title: 'Atendimento WhatsApp',
      channel: 'whatsapp',
      last_message_preview: 'Obrigado!',
      updated_at: '2026-08-16T12:00:00Z',
      created_at: '2026-08-16T10:30:00Z',
    },
  ],
  // 📊 as três categorias que existem no banco em 17/08/2026.
  agent_activities: [
    {
      id: 'eeeeeeee-0000-4000-8000-000000000001',
      category: 'atendimentos',
      title: 'WhatsApp de atendimento desconectado',
      detail: 'Reconecte em Personalização',
      created_at: '2026-08-16T08:00:00Z',
    },
    {
      id: 'eeeeeeee-0000-4000-8000-000000000002',
      category: 'qualidade',
      title: 'Varredura de qualidade concluída — 3 conversa(s)',
      detail: null,
      created_at: '2026-08-16T07:00:00Z',
    },
    {
      id: 'eeeeeeee-0000-4000-8000-000000000003',
      category: 'auxiliares',
      title: 'Rotina executada — Cobrança de boletos atrasados',
      detail: null,
      created_at: '2026-08-16T06:30:00Z',
    },
  ],
  tenant_auxiliaries: [
    {
      id: 'tttttttt-0000-4000-8000-000000000001',
      name: 'Checklist das 6h',
      slug: 'checklist-6h',
    },
    {
      id: 'tttttttt-0000-4000-8000-000000000002',
      name: 'Auxiliar de Cobrança',
      slug: 'auxiliar-cobranca',
    },
  ],
};

async function rodarRota(linhas = LINHAS) {
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
    return undefined;
  });

  const resposta = await rota.GET({});
  return { itens: resposta.body.itens, contagem: resposta.body.contagem, registro };
}

// ─────────────────────────────────────────────────────────────────────────────
// Os guardas. Cada um devolve a lista de problemas — vazia é verde.
// ─────────────────────────────────────────────────────────────────────────────

/** Guarda 1 — nenhuma linha sem destino, e as cinco fontes presentes. */
function guardaTudoAbre(itens) {
  const problemas = [];
  const fontes = new Set(itens.map((i) => String(i.id).split(':')[0]));
  for (const esperada of ['artifact', 'briefing', 'run', 'conversa', 'atividade']) {
    if (!fontes.has(esperada)) problemas.push(`fonte ausente da lista: ${esperada}`);
  }
  for (const i of itens) {
    if (!i.href) problemas.push(`sem destino: ${i.id} — "${i.titulo}"`);
  }
  return problemas;
}

/**
 * Guarda 2 — o briefing NÃO leva ao cartão descritivo.
 *
 * O destino certo vem do mapa único de `lib/auxiliaries/catalog.ts`. O teste
 * compara com o valor REAL do mapa (carregado acima), não com uma string
 * copiada: se o endereço da tela mudar lá, este teste continua correto.
 */
function guardaBriefingVaiParaTelaCerta(itens) {
  const problemas = [];
  const telaCerta = catalogo.telaDeExecucao('checklist-6h');
  const cartao = '/dashboard/auxiliares/checklist-6h';

  if (!telaCerta) problemas.push('o mapa TELA_DE_EXECUCAO nao conhece checklist-6h');
  if (telaCerta === cartao) problemas.push('o mapa aponta para o proprio cartao descritivo');

  const briefings = itens.filter((i) => String(i.id).startsWith('briefing:'));
  if (briefings.length === 0) problemas.push('nenhum briefing na lista — o guarda nao percorreu nada');

  for (const b of briefings) {
    if (b.href === cartao) {
      problemas.push(`briefing ${b.id} leva ao CARTAO do Auxiliar, nao ao trabalho: ${b.href}`);
      continue;
    }
    const ehDocumento = /^\/dashboard\/entregas\/[0-9a-f-]{36}$/i.test(b.href || '');
    const ehTela = b.href === telaCerta;
    if (!ehDocumento && !ehTela) {
      problemas.push(`briefing ${b.id} com destino inesperado: ${b.href}`);
    }
  }
  return problemas;
}

/**
 * Guarda 2b — NENHUMA linha, de fonte nenhuma, leva ao cartão descritivo de um
 * Auxiliar que tem tela própria.
 *
 * O guarda 2 olha só os briefings. Este fecha o resto: a execução de auxiliar
 * também montava `/dashboard/auxiliares/${slug}` à mão, e um clique na execução
 * do Checklist caía na propaganda dele em vez do briefing que ele produziu.
 */
function guardaNinguemVaiParaOCartao(itens) {
  const problemas = [];
  const mapa = catalogo.TELA_DE_EXECUCAO;
  if (!mapa || Object.keys(mapa).length === 0) {
    problemas.push('o mapa TELA_DE_EXECUCAO nao foi exportado do catalogo');
    return problemas;
  }
  if (itens.length === 0) problemas.push('lista vazia — o guarda nao percorreu nada');
  for (const i of itens) {
    const m = /^\/dashboard\/auxiliares\/([^/?#]+)$/.exec(i.href || '');
    if (m && mapa[m[1]]) {
      problemas.push(
        `${i.id} leva ao cartao de "${m[1]}", que TEM tela propria (${mapa[m[1]]})`,
      );
    }
  }
  return problemas;
}

/** Guarda 3 — toda leitura da rota é filtrada por company_id (CLAUDE.md §7). */
function guardaEscopoPorEmpresa(registro) {
  const problemas = [];
  if (registro.length === 0) problemas.push('nenhuma consulta registrada — o guarda nao percorreu nada');
  for (const { tabela, filtros } of registro) {
    const temEmpresa = filtros.some(([coluna, valor]) => coluna === 'company_id' && valor === EMPRESA);
    if (!temEmpresa) problemas.push(`consulta a ${tabela} sem .eq('company_id', empresa)`);
  }
  return problemas;
}

/**
 * Guarda 4 — a rota nova de Artifact também filtra por empresa.
 *
 * Aqui a verificação é na FONTE e não em execução: são um Server Component e um
 * route handler que dependem de `cookies()` do Next. O que precisa ser provado
 * é estrutural — nenhuma das três tabelas do Artifact Hub é lida sem o filtro.
 * 🔴 O backend usa service role: RLS sem o filtro no código não protege nada.
 */
const TABELAS_DO_ARTIFACT = ['artifacts', 'artifact_versions', 'artifact_renders'];

function guardaEscopoNaFonte(fonte, nome) {
  const problemas = [];
  let achou = 0;
  for (const tabela of TABELAS_DO_ARTIFACT) {
    // Cada `.from('tabela')` e o trecho até o fim da cadeia (o `;` seguinte).
    const re = new RegExp(`\\.from\\(\\s*'${tabela}'\\s*\\)([\\s\\S]*?);`, 'g');
    let m;
    while ((m = re.exec(fonte)) !== null) {
      achou += 1;
      if (!/\.eq\(\s*'company_id'\s*,/.test(m[1])) {
        problemas.push(`${nome}: .from('${tabela}') sem .eq('company_id', …)`);
      }
    }
  }
  if (achou === 0) problemas.push(`${nome}: nenhuma leitura de artifact encontrada — o guarda nao percorreu nada`);
  return problemas;
}

/**
 * Guarda 5 — o `?tipo=` que os redirects MANDAM é o `?tipo=` que a tela ACEITA.
 *
 * 📊 17/08/2026: `/dashboard/historico` redireciona para
 * `/dashboard/entregas?tipo=conversa` e `/dashboard/auxiliares/execucoes` para
 * `?tipo=trabalho` — há semanas. A tela ignorava os dois e abria em "Tudo".
 *
 * Este guarda liga as duas pontas: quem manda um filtro e quem o recebe. Um
 * redirect novo com um tipo que a lista não reconhece cai aqui, em vez de virar
 * uma tela vazia que ninguém sabe explicar.
 */
function guardaFiltroDaUrl(clienteFonte, redirects) {
  const problemas = [];

  if (!/window\.location\.search/.test(clienteFonte) || !/get\('tipo'\)/.test(clienteFonte)) {
    problemas.push('EntregasClient nao le `?tipo=` da URL');
  }

  const lista = /const FILTROS_DA_URL[^=]*=\s*\[([^\]]*)\]/.exec(clienteFonte);
  if (!lista) {
    problemas.push('FILTROS_DA_URL nao encontrado em EntregasClient');
    return problemas;
  }
  const aceitos = [...lista[1].matchAll(/'([^']+)'/g)].map((m) => m[1]);

  if (redirects.length === 0) problemas.push('nenhum redirect com ?tipo= encontrado — o guarda nao percorreu nada');
  for (const { arquivo, tipo } of redirects) {
    if (!aceitos.includes(tipo)) {
      problemas.push(`${arquivo} manda ?tipo=${tipo}, que a tela nao aceita (aceita: ${aceitos.join(', ')})`);
    }
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
// Execução
// ─────────────────────────────────────────────────────────────────────────────

const falhas = [];
function checar(problemas, nome) {
  if (problemas.length === 0) {
    console.log(`  OK  ${nome}`);
  } else {
    falhas.push(nome);
    console.log(`  X   ${nome}`);
    for (const p of problemas) console.log(`        ${p}`);
  }
}

/** Controle: o guarda TEM de reprovar esta entrada. Se aprovar, ele é decorativo. */
function controle(problemas, nome) {
  if (problemas.length > 0) {
    console.log(`  OK  CONTROLE ${nome} — o guarda acusou (${problemas.length})`);
  } else {
    falhas.push(`CONTROLE ${nome}`);
    console.log(`  X   CONTROLE ${nome} — o guarda NAO acusou; ele nao guarda nada`);
  }
}

console.log('='.repeat(72));
console.log('ENTREGAS: TUDO QUE A LISTA MOSTRA TEM PARA ONDE IR  (SPEC-078 F.4)');
console.log('='.repeat(72));

const { itens, registro } = await rodarRota();

console.log(`\n[1] A rota devolveu ${itens.length} itens de 5 fontes`);
checar(guardaTudoAbre(itens), 'toda linha tem destino, e as 5 fontes aparecem');

console.log('\n[2] Os briefings levam ao trabalho, nao ao cartao');
console.log(`      mapa do catalogo: checklist-6h → ${catalogo.telaDeExecucao('checklist-6h')}`);
for (const b of itens.filter((i) => String(i.id).startsWith('briefing:'))) {
  console.log(`      ${b.titulo} → ${b.href}`);
}
checar(guardaBriefingVaiParaTelaCerta(itens), 'briefing aponta para a tela de execucao (ou para o documento)');
for (const r of itens.filter((i) => String(i.id).startsWith('run:'))) {
  console.log(`      ${r.titulo} → ${r.href}`);
}
checar(guardaNinguemVaiParaOCartao(itens), 'nenhuma linha leva ao cartao de um Auxiliar com tela propria');

console.log('\n[3] Multi-tenant: toda leitura filtrada por company_id');
console.log(`      ${registro.length} consultas registradas: ${registro.map((r) => r.tabela).join(', ')}`);
checar(guardaEscopoPorEmpresa(registro), 'nenhuma consulta da rota sem filtro de empresa');

console.log('\n[4] A rota nova de Artifact filtra por empresa na fonte');
const FONTES_DO_ARTIFACT = [
  'app/dashboard/entregas/[artifactId]/page.tsx',
  'app/dashboard/entregas/[artifactId]/arquivo/route.ts',
];
for (const rel of FONTES_DO_ARTIFACT) {
  const p = path.join(RAIZ, rel);
  if (!fs.existsSync(p)) {
    checar([`${rel} nao existe`], `${rel} existe`);
    continue;
  }
  checar(guardaEscopoNaFonte(fs.readFileSync(p, 'utf8'), rel), `${rel} — toda leitura com company_id`);
}

console.log('\n[5] O ?tipo= que os redirects mandam e o que a tela aceita');
const CLIENTE = fs.readFileSync(path.join(RAIZ, 'app/dashboard/entregas/EntregasClient.tsx'), 'utf8');
const REDIRECTS = redirectsComTipo();
for (const r of REDIRECTS) console.log(`      ${r.arquivo} → ?tipo=${r.tipo}`);
checar(guardaFiltroDaUrl(CLIENTE, REDIRECTS), 'a tela le ?tipo= e aceita todos os que sao enviados');

console.log('\n[6] LINHAS DE CONTROLE — cada guarda consegue ficar vermelho');

controle(
  guardaTudoAbre([...itens, { id: 'atividade:controle', titulo: 'linha injetada', href: null }]),
  'item com href null',
);
controle(
  guardaTudoAbre(itens.filter((i) => !String(i.id).startsWith('artifact:'))),
  'fonte inteira ausente',
);
controle(
  guardaBriefingVaiParaTelaCerta([
    { id: 'briefing:controle', titulo: 'briefing antigo', href: '/dashboard/auxiliares/checklist-6h' },
  ]),
  'briefing apontando para o cartao do Auxiliar',
);
controle(
  guardaNinguemVaiParaOCartao([
    { id: 'run:controle', titulo: 'Checklist das 6h rodou', href: '/dashboard/auxiliares/checklist-6h' },
  ]),
  'execucao apontando para o cartao do Auxiliar',
);
controle(
  guardaEscopoPorEmpresa([{ tabela: 'artifacts', filtros: [['status', 'ready']] }]),
  'consulta sem company_id',
);
controle(
  guardaEscopoNaFonte(
    "const x = await supabase.from('artifacts').select('id').eq('id', artifactId).maybeSingle();",
    'fonte-sintetica',
  ),
  'leitura de artifacts sem company_id na fonte',
);
controle(guardaEscopoNaFonte('// nada aqui', 'fonte-vazia'), 'fonte que nao le artifact nenhum');
controle(
  guardaFiltroDaUrl(CLIENTE, [{ arquivo: 'sintetico/page.tsx', tipo: 'pesquisa' }]),
  'redirect mandando um ?tipo= que a tela nao aceita',
);
controle(
  guardaFiltroDaUrl(
    "const FILTROS_DA_URL = ['tudo', 'documento', 'conversa', 'trabalho'];",
    REDIRECTS,
  ),
  'cliente que nao le a URL',
);

console.log(`\n${'='.repeat(72)}`);
if (falhas.length > 0) {
  console.log(`VERMELHO — ${falhas.length} falha(s):`);
  for (const f of falhas) console.log(`  - ${f}`);
  process.exit(1);
}
console.log('VERDE — toda linha de Entregas abre, e os guardas conseguem reprovar.');
