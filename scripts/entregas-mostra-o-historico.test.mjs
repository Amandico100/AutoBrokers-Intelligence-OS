// SPEC-078 F.3/F.4/F.5/F.7 — o histórico da rotina chega em Entregas, o
// relatório vai INTEIRO, e nada disso vaza CPF.
//
// 📊 MEDIDO EM 17/08/2026, projeto dcajcvlzcjbmyapmklil:
//
//     routine_runs                        32 linhas   INVISIVEIS em Entregas
//     auxiliary_runs                        4 linhas   visiveis
//     routine_runs.company_id            nao existia   por isso nao dava para ler
//     runs com output_preview de 500ch          29     o teto: 91% truncadas
//     tamanho real do relatorio          ate 4000ch
//     ocorrencias de "artifact" na cobranca      0
//
// Oito vezes mais trabalho registrado do lado de fora da lista do que dentro.
// E o unico lugar que mostrava `routine_runs` era `/dashboard/auxiliares/
// rotinas`, a pagina que a SPEC-078 C.4 transforma em redirect. Por isso F.3 e
// PRE-REQUISITO de C.4: sem ele, o comentario "conteudo absorvido" seria falso.
//
// COMO ESTE TESTE FUNCIONA — sem rede e sem banco.
//
// Mesma forma de `entregas-tudo-abre.test.mjs`: a rota e transpilada com o
// TypeScript do projeto, carregada com um `require` falso e chamada com um
// duble de Supabase que devolve linhas fixas. O que sai e a mesma lista que o
// navegador receberia — entao um `href: null` de volta muda a saida e o guarda
// acusa. O que nao da para executar (Server Component que depende de
// `cookies()`, e Python) e conferido na FONTE, e cada guarda de fonte tem uma
// linha de controle sintetica provando que ele consegue reprovar.
//
// LINHA DE CONTROLE (CLAUDE.md §9.2): todo guarda e rodado tambem contra uma
// entrada que ele DEVE reprovar. Um guarda que nao tem como falhar nao guarda
// nada — e um guarda que percorre zero itens passa igual.

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

const catalogo = carregarTS('lib/auxiliaries/catalog.ts', (id) =>
  id === '@supabase/supabase-js' ? {} : undefined,
);

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

// ─────────────────────────────────────────────────────────────────────────────
// A corretora do teste. O relatorio abaixo e a FORMA REAL de `_format_report`
// (`billing_collection.py:1069`): o cabecalho nas primeiras linhas, e o CPF e o
// telefone do segurado bem depois — que e exatamente o motivo de a lista nao
// poder despejar o preview inteiro numa tela de varredura.
// ─────────────────────────────────────────────────────────────────────────────

const RELATORIO_COM_PII = [
  'Auxiliar de Cobranca - Cobranca de boletos atrasados',
  'Portais varridos: allianz_corretor',
  'Jobs: 1 | inadimplentes: 2 | boletos baixados: 1',
  'PRECISA DE VOCE - 1 parcela(s) em atraso SEM boleto:',
  '- Joao Lima | apolice 77 | parcela 3 | vcto 2026-08-01 -> converter no portal',
  'Clientes encontrados:',
  '- Maria Souza | CPF/CNPJ 123.456.789-01 | vcto 2026-07-30 | R$ 431,90 | WhatsApp: 5547999990000',
].join('\n');

const ID_DA_EXECUCAO = 'ffffffff-0000-4000-8000-000000000001';

const LINHAS = {
  artifacts: [{
    id: 'aaaaaaaa-0000-4000-8000-000000000001',
    title: 'Cobranca de 16/08/2026', subtitle: 'Allianz', kind: 'report',
    status: 'ready', created_at: '2026-08-16T09:00:00Z',
  }],
  briefing_publications: [{
    id: 'bbbbbbbb-0000-4000-8000-000000000001',
    headline: 'Checklist de 16/08', summary_text: null,
    briefing_type: 'daily_operational', published_at: '2026-08-16T09:05:00Z',
    created_at: '2026-08-16T09:05:00Z', delivery_status: 'sent', artifact_id: null,
  }],
  auxiliary_runs: [{
    id: 'cccccccc-0000-4000-8000-000000000001',
    tenant_auxiliary_id: 'tttttttt-0000-4000-8000-000000000001',
    status: 'succeeded', run_type: 'scheduled', error_message: null,
    started_at: '2026-08-16T09:00:00Z', finished_at: '2026-08-16T09:04:00Z',
    created_at: '2026-08-16T09:00:00Z',
  }],
  conversations: [{
    id: 'dddddddd-0000-4000-8000-000000000001', session_id: 'sessao-1',
    title: 'Cotacao para frota', channel: 'web', last_message_preview: 'Segue',
    updated_at: '2026-08-16T11:00:00Z', created_at: '2026-08-16T10:00:00Z',
  }],
  agent_activities: [{
    id: 'eeeeeeee-0000-4000-8000-000000000001', category: 'auxiliares',
    title: 'Rotina executada', detail: null, created_at: '2026-08-16T06:30:00Z',
  }],
  tenant_auxiliaries: [
    { id: 'tttttttt-0000-4000-8000-000000000001', name: 'Checklist das 6h', slug: 'checklist-6h' },
    { id: 'tttttttt-0000-4000-8000-000000000002', name: 'Cobranca Feita', slug: 'cobranca-feita' },
  ],
  // 📊 as duas rotinas reais do banco em 17/08/2026 se chamam a MESMA coisa.
  // E por isso que o titulo da linha usa o nome do Auxiliar, nao o da rotina.
  routines: [{
    id: 'rrrrrrrr-0000-4000-8000-000000000001',
    name: 'Cobranca de boletos atrasados',
    tenant_auxiliary_id: 'tttttttt-0000-4000-8000-000000000002',
  }],
  routine_runs: [
    {
      id: ID_DA_EXECUCAO,
      routine_id: 'rrrrrrrr-0000-4000-8000-000000000001',
      status: 'ok', output_preview: RELATORIO_COM_PII.slice(0, 500), error: null,
      started_at: '2026-08-16T06:00:00Z', finished_at: '2026-08-16T06:12:00Z',
    },
    {
      id: 'ffffffff-0000-4000-8000-000000000002',
      routine_id: 'rrrrrrrr-0000-4000-8000-000000000001',
      status: 'error', output_preview: null,
      error: 'RuntimeError: entrega falhou: corretora sem canal WhatsApp que possa ENVIAR',
      started_at: '2026-08-15T06:00:00Z', finished_at: '2026-08-15T06:01:00Z',
    },
  ],
};

async function rodarRota(linhas = LINHAS) {
  const registro = [];
  const supabase = dubleSupabase(linhas, registro);

  const rota = carregarTS('app/api/dashboard/entregas/route.ts', (id) => {
    if (id === 'next/server') {
      return { NextResponse: { json: (body, init) => ({ body, status: init?.status ?? 200 }) } };
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
// Os guardas. Cada um devolve a lista de problemas — vazia e verde.
// ─────────────────────────────────────────────────────────────────────────────

const PAGINA_DA_EXECUCAO = 'app/dashboard/entregas/rotina/[runId]/page.tsx';
const ROTA_DE_ENTREGAS = 'app/api/dashboard/entregas/route.ts';
const COBRANCA_PY = 'backend/app/services/billing_collection.py';
const MOTOR_PY = 'backend/app/services/routine_engine.py';

/**
 * Guarda 1 (F.3) — a execucao de rotina APARECE, e cada uma tem destino.
 *
 * O destino tem de ser a pagina da propria execucao. Levar ao cartao do
 * Auxiliar seria o mesmo defeito que F.2 acabou de consertar nos briefings:
 * clicar no trabalho e receber a propaganda do trabalhador.
 */
const DESTINO_DA_EXECUCAO = /^\/dashboard\/entregas\/rotina\/[0-9a-f-]{36}$/i;

function guardaHistoricoDeRotinaAparece(itens) {
  const problemas = [];
  const daRotina = itens.filter((i) => String(i.id).startsWith('rotina:'));
  if (daRotina.length === 0) {
    problemas.push('nenhuma execucao de rotina na lista — routine_runs continua invisivel');
    return problemas;
  }
  for (const i of daRotina) {
    if (!i.href) problemas.push(`${i.id} sem destino`);
    else if (!DESTINO_DA_EXECUCAO.test(i.href)) {
      problemas.push(`${i.id} nao abre a execucao: ${i.href}`);
    }
    if (i.tipo !== 'trabalho') problemas.push(`${i.id} com tipo "${i.tipo}", esperado "trabalho"`);
    // O corretor tem de saber de QUAL Auxiliar e a execucao. So e possivel
    // porque routines.tenant_auxiliary_id virou NOT NULL na 20260817_03.
    if (!i.origem) problemas.push(`${i.id} nao diz de qual Auxiliar e`);
  }
  return problemas;
}

/** Guarda 2 (F.3) — o titulo nomeia o Auxiliar dono, nao o id da execucao. */
function guardaExecucaoTemDono(itens) {
  const problemas = [];
  const daRotina = itens.filter((i) => String(i.id).startsWith('rotina:'));
  if (daRotina.length === 0) problemas.push('nenhuma execucao — o guarda nao percorreu nada');
  for (const i of daRotina) {
    if (!/Cobranca Feita/.test(String(i.titulo))) {
      problemas.push(`${i.id} nao nomeia o Auxiliar dono no titulo: "${i.titulo}"`);
    }
  }
  return problemas;
}

/**
 * Guarda 3 (F.4) — NENHUMA linha da lista carrega dado de segurado.
 *
 * O preview guardado tem 500 caracteres e a partir de "Clientes encontrados"
 * ele traz CPF/CNPJ e telefone. Despejar isso numa tela de varredura poria
 * documento de terceiro onde ninguem foi ler documento nenhum. So a primeira
 * linha entra, e cortada.
 */
const CPF_OU_CNPJ = /\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}\b|\b\d{11,14}\b/;
const TELEFONE_BR = /\b55\d{10,11}\b/;

function guardaListaSemPII(itens) {
  const problemas = [];
  if (itens.length === 0) problemas.push('lista vazia — o guarda nao percorreu nada');
  for (const i of itens) {
    const texto = `${i.titulo ?? ''} ${i.detalhe ?? ''}`;
    if (CPF_OU_CNPJ.test(texto)) problemas.push(`${i.id} carrega CPF/CNPJ na lista: "${i.detalhe}"`);
    if (TELEFONE_BR.test(texto)) problemas.push(`${i.id} carrega telefone na lista: "${i.detalhe}"`);
  }
  return problemas;
}

/** Guarda 4 (F.3) — toda leitura da rota e filtrada por company_id (CLAUDE.md §7). */
function guardaEscopoPorEmpresa(registro, tabelasObrigatorias = []) {
  const problemas = [];
  if (registro.length === 0) problemas.push('nenhuma consulta registrada — o guarda nao percorreu nada');
  for (const { tabela, filtros } of registro) {
    const temEmpresa = filtros.some(([c, v]) => c === 'company_id' && v === EMPRESA);
    if (!temEmpresa) problemas.push(`consulta a ${tabela} sem .eq('company_id', empresa)`);
  }
  const lidas = new Set(registro.map((r) => r.tabela));
  for (const t of tabelasObrigatorias) {
    if (!lidas.has(t)) problemas.push(`a rota nao le ${t}`);
  }
  return problemas;
}

/**
 * Guarda 5 (F.4) — a pagina da execucao le o texto COMPLETO, e com filtro.
 *
 * Verificacao na fonte porque e Server Component com `cookies()`. O que precisa
 * ser provado e estrutural: le `output_full`, e nenhuma das tres tabelas e
 * lida sem `.eq('company_id', …)`. 🔴 O backend usa service role — RLS sem o
 * filtro no codigo nao protege nada.
 */
const TABELAS_DA_PAGINA = ['routine_runs', 'routines', 'tenant_auxiliaries'];

function guardaPaginaDaExecucao(fonte, nome) {
  const problemas = [];
  if (!/output_full/.test(fonte)) {
    problemas.push(`${nome}: nao le output_full — o relatorio completo continua inacessivel`);
  }
  let achou = 0;
  for (const tabela of TABELAS_DA_PAGINA) {
    const re = new RegExp(`\\.from\\(\\s*'${tabela}'\\s*\\)([\\s\\S]*?);`, 'g');
    let m;
    while ((m = re.exec(fonte)) !== null) {
      achou += 1;
      if (!/\.eq\(\s*'company_id'\s*,/.test(m[1])) {
        problemas.push(`${nome}: .from('${tabela}') sem .eq('company_id', …)`);
      }
    }
  }
  if (achou === 0) problemas.push(`${nome}: nenhuma leitura encontrada — o guarda nao percorreu nada`);
  return problemas;
}

/** Guarda 6 (F.4) — o motor grava o texto inteiro, e nao o joga no log. */
function guardaMotorGravaOTextoInteiro(fonte, nome) {
  const problemas = [];
  if (!/"output_full":/.test(fonte)) {
    problemas.push(`${nome}: o update de routine_runs nao grava output_full`);
  }
  if (!/"company_id":\s*str\(routine\["company_id"\]\)/.test(fonte)) {
    problemas.push(`${nome}: o insert de routine_runs nao grava company_id`);
  }
  // O relatorio nao pode ir para log em hipotese nenhuma: log sai do tenant.
  for (const m of fonte.matchAll(/logger\.\w+\(([^\n]*)\)/g)) {
    if (/\boutput_full\b|\boutput\b(?!_)/.test(m[1])) {
      problemas.push(`${nome}: logger recebe o relatorio — ${m[1].slice(0, 70)}`);
    }
  }
  return problemas;
}

/**
 * Guarda 7 (F.5) — a cobranca usa o Artifact Hub que JA EXISTE.
 *
 * 📊 Zero ocorrencias de "artifact" neste arquivo antes da SPEC-078. O risco ao
 * consertar isso nao era esquecer: era construir um segundo publisher ao lado
 * do da SPEC-057 (CLAUDE.md §5). Este guarda exige o caminho do Checklist das
 * 6h — criar/renderizar/publicar — e recusa tabela de artifact escrita a mao.
 */
function guardaCobrancaUsaOHub(fonte, nome) {
  const problemas = [];
  if (!/ArtifactService/.test(fonte)) problemas.push(`${nome}: nao usa ArtifactService`);
  for (const passo of ['criar', 'renderizar', 'publicar']) {
    if (!new RegExp(`servico\\.${passo}\\(`).test(fonte)) {
      problemas.push(`${nome}: nao chama servico.${passo}() — o caminho do Hub esta incompleto`);
    }
  }
  // Publisher paralelo: escrever nas tabelas do Hub sem passar pelo servico.
  for (const tabela of ['artifacts', 'artifact_versions', 'artifact_renders']) {
    if (new RegExp(`table\\(["']${tabela}["']\\)`).test(fonte)) {
      problemas.push(`${nome}: escreve em ${tabela} direto — publisher paralelo (CLAUDE.md §5)`);
    }
  }
  return problemas;
}

/**
 * Guarda 8 (F.5) — a peca nao carrega CPF nem telefone.
 *
 * Um artifact pode virar `artifact_shares`: link publico com 30 dias de
 * validade. Documento de segurado com CPF atras de um token de URL e vazamento
 * com prazo. O documento inteiro so existe em `routine_runs.output_full`.
 */
function guardaPecaSemDocumento(fonte, nome) {
  const problemas = [];
  const bloco = /def compor_peca_da_cobranca\([\s\S]*?\n    return blocos/.exec(fonte);
  if (!bloco) {
    problemas.push(`${nome}: compor_peca_da_cobranca nao encontrada — o guarda nao percorreu nada`);
    return problemas;
  }
  const corpo = bloco[0];
  if (!/_mascarar_documento\(/.test(corpo)) {
    problemas.push(`${nome}: a peca nao mascara o documento`);
  }
  for (const m of corpo.matchAll(/\.get\(["'](cpf_cnpj|whatsapp)["']\)/g)) {
    // Dentro de `_mascarar_documento(...)` e o uso legitimo; solto, nao.
    const antes = corpo.slice(Math.max(0, m.index - 40), m.index);
    if (!/_mascarar_documento\(\s*i?t?e?m?\.?$|_mascarar_documento\([^)]*$/.test(antes)) {
      problemas.push(`${nome}: a peca le "${m[1]}" cru — isso vai para link publico`);
    }
  }
  return problemas;
}

/**
 * Guarda 9 (F.7) — a purga existe, e nasce DESLIGADA.
 *
 * 📊 62 objetos em `portal-evidence`, o mais antigo de 11/07/2026, sem nenhuma
 * rotina de descarte. A SPEC nao apaga nada: escreve a politica, instrumenta a
 * contagem e deixa a purga pronta e desligada. Ligar e decisao do Founder.
 *
 * O guarda existe para os dois lados: se a purga sumir, acusa; se ela nascer
 * LIGADA, acusa tambem — e essa e a metade que importa.
 */
function guardaPurgaEscritaEDesligada(fonte, nome) {
  const problemas = [];
  if (!/def purgar_evidencias_antigas\(/.test(fonte)) {
    problemas.push(`${nome}: a purga nao foi escrita`);
  }
  if (!/def contar_evidencias_por_idade\(/.test(fonte)) {
    problemas.push(`${nome}: a contagem por idade nao foi escrita`);
  }
  const flag = /def evidence_purge_enabled\([\s\S]*?\n    return ([^\n]+)/.exec(fonte);
  if (!flag) {
    problemas.push(`${nome}: nao ha interruptor evidence_purge_enabled`);
  } else if (!/get\(\s*["']PORTAL_EVIDENCE_PURGE_ENABLED["']\s*,\s*["']{2}\s*\)/.test(flag[1])) {
    // O default TEM de ser vazio: variavel ausente e "nao apague".
    problemas.push(`${nome}: o interruptor nao tem "desligado" como padrao — ${flag[1].trim()}`);
  }
  if (!/dry_run: bool = True/.test(fonte)) {
    problemas.push(`${nome}: a purga nao nasce em dry_run`);
  }
  // A trava real: nao pode existir chamada de remocao fora da guarda.
  const remove = /\.remove\(alvos\)/.exec(fonte);
  if (!remove) {
    problemas.push(`${nome}: a purga nao chega a remover nada — funcao decorativa`);
  } else if (!/if not ligada or dry_run or not alvos:[\s\S]{0,600}?\.remove\(alvos\)/.test(fonte)) {
    problemas.push(`${nome}: a remocao nao esta atras da guarda "not ligada or dry_run"`);
  }
  return problemas;
}

// ─────────────────────────────────────────────────────────────────────────────
// Execucao
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

function controle(problemas, nome) {
  if (problemas.length > 0) {
    console.log(`  OK  CONTROLE ${nome} — o guarda acusou (${problemas.length})`);
  } else {
    falhas.push(`CONTROLE ${nome}`);
    console.log(`  X   CONTROLE ${nome} — o guarda NAO acusou; ele nao guarda nada`);
  }
}

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');

console.log('='.repeat(72));
console.log('ENTREGAS MOSTRA O HISTORICO DA ROTINA  (SPEC-078 F.3 / F.4 / F.5 / F.7)');
console.log('='.repeat(72));

const { itens, registro } = await rodarRota();

console.log(`\n[1] A rota devolveu ${itens.length} itens de 6 fontes`);
for (const i of itens.filter((x) => String(x.id).startsWith('rotina:'))) {
  console.log(`      ${i.titulo} -> ${i.href}`);
  console.log(`        detalhe: ${JSON.stringify(i.detalhe)}`);
}
checar(guardaHistoricoDeRotinaAparece(itens), 'F.3 execucao de rotina aparece, com href que abre');
checar(guardaExecucaoTemDono(itens), 'F.3 a linha diz de qual Auxiliar e');

console.log('\n[2] Nada de dado de segurado na lista');
checar(guardaListaSemPII(itens), 'F.4 nem CPF/CNPJ nem telefone chegam a lista');

console.log('\n[3] Multi-tenant: toda leitura filtrada por company_id');
console.log(`      ${registro.length} consultas: ${registro.map((r) => r.tabela).join(', ')}`);
checar(
  guardaEscopoPorEmpresa(registro, ['routine_runs', 'routines']),
  'F.3 nenhuma consulta da rota sem filtro de empresa, e as duas novas existem',
);

console.log('\n[4] A pagina da execucao recupera o relatorio inteiro');
checar(guardaPaginaDaExecucao(ler(PAGINA_DA_EXECUCAO), PAGINA_DA_EXECUCAO),
  'F.4 le output_full, e toda tabela com company_id');
checar(guardaMotorGravaOTextoInteiro(ler(MOTOR_PY), MOTOR_PY),
  'F.4 o motor grava output_full e company_id, e nao loga o relatorio');

console.log('\n[5] A cobranca usa o Artifact Hub que ja existe');
checar(guardaCobrancaUsaOHub(ler(COBRANCA_PY), COBRANCA_PY),
  'F.5 criar/renderizar/publicar pelo servico, sem publisher paralelo');
checar(guardaPecaSemDocumento(ler(COBRANCA_PY), COBRANCA_PY),
  'F.5 a peca sai sem CPF/CNPJ e sem telefone');

console.log('\n[6] Os boletos ganharam prazo — e a purga esta DESLIGADA');
checar(guardaPurgaEscritaEDesligada(ler(COBRANCA_PY), COBRANCA_PY),
  'F.7 politica escrita, contagem instrumentada, purga desligada por padrao');

console.log('\n[7] LINHAS DE CONTROLE — cada guarda consegue ficar vermelho');

// F.3 — a fonte inteira somindo (o estado de ontem: 32 execucoes invisiveis)
const semRotina = await rodarRota({ ...LINHAS, routine_runs: [] });
controle(guardaHistoricoDeRotinaAparece(semRotina.itens), 'routine_runs vazio: a fonte some da lista');
controle(
  guardaHistoricoDeRotinaAparece([{ id: 'rotina:x', tipo: 'trabalho', titulo: 'x', origem: 'y', href: null }]),
  'execucao com href null',
);
controle(
  guardaHistoricoDeRotinaAparece([{
    id: 'rotina:x', tipo: 'trabalho', titulo: 'x', origem: 'y',
    href: '/dashboard/auxiliares/cobranca-feita',
  }]),
  'execucao apontando para o cartao do Auxiliar',
);

// F.3 — a rotina sem dono: o titulo perde o nome do Auxiliar
const semDono = await rodarRota({
  ...LINHAS,
  routines: [{ ...LINHAS.routines[0], tenant_auxiliary_id: null }],
});
controle(guardaExecucaoTemDono(semDono.itens), 'rotina orfa: a linha nao sabe dizer de quem e');

// F.4 — o preview inteiro caindo na lista, como seria se o corte nao existisse
controle(
  guardaListaSemPII([{ id: 'rotina:x', titulo: 'Cobranca Feita rodou', detalhe: RELATORIO_COM_PII }]),
  'preview inteiro na lista: CPF e telefone vazam',
);
controle(guardaListaSemPII([]), 'lista vazia: o guarda nao percorreu nada');

// F.3 — consulta sem o filtro de empresa
controle(
  guardaEscopoPorEmpresa([{ tabela: 'routine_runs', filtros: [['status', 'ok']] }]),
  'consulta a routine_runs sem company_id',
);
controle(guardaEscopoPorEmpresa(registro, ['tabela_que_nao_existe']), 'fonte obrigatoria ausente');

// F.4 — pagina sintetica que le a execucao de qualquer corretora
controle(
  guardaPaginaDaExecucao(
    "const x = await supabase.from('routine_runs').select('output_full').eq('id', runId).maybeSingle();",
    'fonte-sintetica',
  ),
  'pagina que le routine_runs sem company_id',
);
controle(
  guardaPaginaDaExecucao(
    "const x = await supabase.from('routine_runs').select('output_preview').eq('id', r).eq('company_id', e);",
    'fonte-sem-output-full',
  ),
  'pagina que so le o preview truncado',
);
controle(guardaPaginaDaExecucao('// nada aqui', 'fonte-vazia'), 'fonte que nao le nada');

// F.4 — motor sintetico que volta a truncar e que loga o relatorio
controle(
  guardaMotorGravaOTextoInteiro('"output_preview": output_preview or None,', 'motor-sintetico'),
  'motor que grava so o preview',
);
controle(
  guardaMotorGravaOTextoInteiro(
    '"output_full": x,\n"company_id": str(routine["company_id"]),\nlogger.info(f"rodou {output_full}")',
    'motor-que-loga',
  ),
  'motor que manda o relatorio para o log',
);

// F.5 — publisher paralelo e caminho incompleto
controle(
  guardaCobrancaUsaOHub(
    'from app.services.artifacts.service import ArtifactService\n'
    + 'servico.criar(...)\nservico.renderizar(...)\nservico.publicar(...)\n'
    + 'client.table("artifact_renders").insert({"inline_content": html})',
    'cobranca-sintetica',
  ),
  'publisher paralelo escrevendo em artifact_renders',
);
controle(
  guardaCobrancaUsaOHub('servico = ArtifactService(db)\nservico.criar(...)', 'cobranca-incompleta'),
  'peca criada e nunca publicada',
);

// F.5 — peca sintetica com o CPF cru
controle(
  guardaPecaSemDocumento(
    'def compor_peca_da_cobranca(x):\n'
    + '    blocos = [{"doc": i.get("cpf_cnpj"), "tel": i.get("whatsapp")}]\n'
    + '    return blocos\n',
    'peca-sintetica',
  ),
  'peca montando a tabela com o CPF cru',
);
controle(guardaPecaSemDocumento('# sem peca nenhuma', 'peca-ausente'), 'peca que nao existe');

// F.7 — purga que nasce ligada, e purga que nao existe
controle(
  guardaPurgaEscritaEDesligada(
    'def purgar_evidencias_antigas(x, dry_run: bool = True):\n'
    + '    if not ligada or dry_run or not alvos:\n        return r\n'
    + '    client.storage.from_(B).remove(alvos)\n'
    + 'def contar_evidencias_por_idade(x):\n    return []\n'
    + 'def evidence_purge_enabled(env=None):\n'
    + '    return str(fonte.get("PORTAL_EVIDENCE_PURGE_ENABLED", "true")).lower() in {"1"}\n',
    'purga-ligada',
  ),
  'purga com o padrao LIGADO',
);
controle(
  guardaPurgaEscritaEDesligada('# nenhuma politica de retencao', 'purga-ausente'),
  'bucket sem politica de descarte (o estado de 17/08)',
);

console.log(`\n${'='.repeat(72)}`);
if (falhas.length > 0) {
  console.log(`VERMELHO — ${falhas.length} falha(s):`);
  for (const f of falhas) console.log(`  - ${f}`);
  process.exit(1);
}
console.log('VERDE — o historico da rotina chega em Entregas, o relatorio abre inteiro,');
console.log('        a cobranca produz peca sem CPF, e a purga esta pronta e desligada.');
