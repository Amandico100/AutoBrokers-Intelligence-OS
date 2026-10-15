// SPEC-131-B · G1 — a loja e a casca: o que o card, o cabeçalho, as abas e o "Como começar" DIZEM, e o isolamento
// entre corretoras do número que o card mostra.
//
// Roda com: node components/aplicativos/casca/a-loja-e-a-casca.test.mjs
//
// COMO FUNCIONA — sem rede e sem banco (o molde de scripts/entregas-tudo-abre.test.mjs): `lib/auxiliaries/catalog.ts`
// é transpilado com o TypeScript do projeto e carregado com um `require` falso; as funções puras são chamadas de
// verdade, e `catalogoDaCorretora` roda contra um DUBLÊ de Supabase que APLICA os filtros (eq/in/gte/not) sobre um
// banco falso com DUAS corretoras. Se o código esquecer o `company_id`, a vizinha entra na conta e o guarda acusa.
//
// LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): cada guarda roda também contra uma entrada que ele DEVE reprovar.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const ts = require('typescript');

let falhas = 0;
function checar(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else {
    falhas += 1;
    console.log(`  X   ${nome}${detalhe ? `  — ${detalhe}` : ''}`);
  }
}

function carregarTS(rel, resolver) {
  // `path.resolve`: aceita também um caminho ABSOLUTO (a cópia mutada da régua, fora da árvore)
  const fonte = fs.readFileSync(path.resolve(RAIZ, rel), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolver(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const CAT = process.env.CATALOGO_SOB_TESTE || 'lib/auxiliaries/catalog.ts';
const C = carregarTS(CAT, (id) => (id === '@supabase/supabase-js' ? {} : undefined));

const AGORA = new Date('2026-10-13T12:00:00Z');
const base = {
  slug: 'cobranca-feita', estado: 'disponivel', conectores_pendentes: [], falta_para_existir: null, sem_rotina: false,
  prova: { execucoes: 0, ultima_execucao: null, renovacoes_no_mes: null },
};

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] O selo de estado — e "Disponível" não tem selo');
checar(C.seloDoEstado('ligado')?.rotulo === 'Ligado' && C.seloDoEstado('ligado')?.tom === 'success', 'ligado → Ligado (success)');
checar(C.seloDoEstado('pausado')?.rotulo === 'Desligado', 'pausado → Desligado');
checar(C.seloDoEstado('falta_conectar')?.tom === 'warning', 'falta conectar → warning');
checar(C.seloDoEstado('em_breve')?.rotulo === 'Em breve', 'em breve → Em breve');
checar(C.seloDoEstado('disponivel') === null, 'CONTROLE: disponível → sem selo');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] A prova do card: número REAL ou o estado em palavras — nunca "0 execuções", nunca estrela');
const p = (x) => C.provaDoCard({ ...base, ...x, prova: { ...base.prova, ...(x.prova || {}) } }, AGORA);
checar(p({ slug: 'renovacao', estado: 'ligado', prova: { renovacoes_no_mes: 12 } }) === '12 renovações calculadas este mês', 'renovação: 12 calculadas este mês');
checar(p({ slug: 'renovacao', estado: 'ligado', prova: { renovacoes_no_mes: 1 } }) === '1 renovação calculada este mês', 'singular');
checar(p({ estado: 'pausado', prova: { execucoes: 18, ultima_execucao: '2026-10-11T09:00:00Z' } }) === '18 execuções · última há 2 dias', 'execuções + última', p({ estado: 'pausado', prova: { execucoes: 18, ultima_execucao: '2026-10-11T09:00:00Z' } }));
const zero = p({ estado: 'ligado' });
checar(zero === 'Ligado · ainda não rodou' && !/\b0\b/.test(zero), 'ligado sem execução → estado, não "0 execuções"', zero);
checar(p({ estado: 'falta_conectar', conectores_pendentes: [{ slug: 'infocap', nome: 'InfoCap', onde: '/x' }] }) === 'Falta conectar InfoCap', 'falta conectar diz QUAL (nome humano)');
checar(p({ slug: 'cotacao', sem_rotina: true }) === 'Configure as regras', 'sem rotina → Configure as regras');
checar(p({ estado: 'em_breve', prova: { execucoes: 9 } }) === 'Em breve', 'em breve nunca mostra número');
checar(p({ estado: 'disponivel' }) === 'Pronto para ligar', 'disponível → Pronto para ligar');
const todas = [12, 1, 0].map((n) => p({ slug: 'renovacao', estado: 'ligado', prova: { renovacoes_no_mes: n, execucoes: n } })).join(' ');
checar(!/[★⭐]|estrela/i.test(todas), 'nenhuma estrela em nenhuma prova');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] O botão principal por estado (instalar ≠ ligar; na Renovação instalar JÁ liga e pede confirmação)');
const b = (x) => C.botaoPrincipal({ ...base, ...x });
const bRen = b({ slug: 'renovacao' });
checar(bRen.tipo === 'acao' && bRen.rotulo === 'Ligar' && bRen.acao === 'install' && bRen.confirmar, 'renovação disponível → "Ligar" (install) COM confirmação', JSON.stringify(bRen));
const bOutro = b({});
checar(bOutro.tipo === 'acao' && bOutro.rotulo === 'Instalar' && !bOutro.confirmar, 'CONTROLE: outro disponível → "Instalar"');
const bPaus = b({ estado: 'pausado' });
checar(bPaus.tipo === 'acao' && bPaus.acao === 'resume' && bPaus.confirmar, 'desligado → Ligar (resume) com confirmação');
const bLig = b({ estado: 'ligado' });
checar(bLig.tipo === 'acao' && bLig.acao === 'pause' && bLig.fantasma, 'ligado → Desligar fantasma');
const bFalta = b({ estado: 'falta_conectar', conectores_pendentes: [{ slug: 'infocap', nome: 'InfoCap', onde: '/dashboard/personalizacao/conectores' }] });
checar(bFalta.tipo === 'link' && bFalta.rotulo === 'Conectar InfoCap', 'falta conectar → "Conectar InfoCap"');
const bBreve = b({ estado: 'em_breve', falta_para_existir: 'falta X' });
checar(bBreve.tipo === 'desabilitado' && bBreve.motivo === 'falta X', 'em breve → desabilitado, com o que falta');
const bCot = b({ slug: 'cotacao', sem_rotina: true });
checar(bCot.tipo === 'link' && bCot.href === '/dashboard/auxiliares/cotacao?aba=configurar', 'cotação (sem rotina) → Configurar');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[4] As abas por ?aba= — inválida vira Início; cada aplicativo só mostra o que tem');
const faq = [{ pergunta: 'p', resposta: 'r' }];
const abasRen = C.abasDoAplicativo({ slug: 'renovacao', faq, estado: 'disponivel', instalado: false, sem_rotina: false });
checar(abasRen.map((a) => a.id).join(',') === 'inicio,configurar,renovacoes,duvidas', 'Renovação: Início · Configurar · Renovações · Dúvidas', abasRen.map((a) => a.id).join(','));
checar(abasRen.find((a) => a.id === 'renovacoes')?.componente === 'renovacao/AbaRenovacoes', 'Renovações = components/aplicativos/renovacao/AbaRenovacoes (G2)');
checar(abasRen.find((a) => a.id === 'configurar')?.componente === 'renovacao/AbaConfigurar', 'Configurar = components/aplicativos/renovacao/AbaConfigurar (G3)');
checar(C.abaValida(abasRen, 'renovacoes') === 'renovacoes', '?aba=renovacoes abre direto');
checar(C.abaValida(abasRen, 'xpto') === 'inicio' && C.abaValida(abasRen, null) === 'inicio', 'aba inválida ou ausente → Início');
// SPEC-132-B · B3 — a Cotação Rápida tão completa quanto a Renovação (era Início · Configurar · Dúvidas: verdade vencida, §9.3)
const abasCot = C.abasDoAplicativo({ slug: 'cotacao', faq, estado: 'disponivel', instalado: false, sem_rotina: true });
checar(abasCot.map((a) => a.id).join(',') === 'inicio,configurar,cotacoes,duvidas', 'Cotação Rápida: Início · Configurar · Cotações · Dúvidas', abasCot.map((a) => a.id).join(','));
checar(abasCot.find((a) => a.id === 'cotacoes')?.componente === 'cotacao/AbaCotacoes' && abasCot.find((a) => a.id === 'cotacoes')?.rotulo === 'Cotações',
  'Cotações = components/aplicativos/cotacao/AbaCotacoes (B3)');
checar(C.abaValida(abasCot, 'cotacoes') === 'cotacoes' && C.abasLargas(abasCot).join(',') === 'cotacoes', '?aba=cotacoes abre direto e ganha largura');
checar(fs.existsSync(path.join(RAIZ, 'components/aplicativos/cotacao/AbaCotacoes.tsx')), 'o arquivo da aba Cotações existe (senão a casca diria "sendo preparada")');
// SPEC-139 (§9.3 — verdade vencida migrada): a Cobrança SAIU do modal. Antes: "não instalado → só Início" e "instalado:
// Configurar = o painel (componente null)". Agora: Início · Configurar (o formulário extraído, L2) · Cobranças · Dúvidas;
// a lição que fica: o Configurar dela continua exigindo a instalação (a regra é uma rotina DA instalação).
const abasCob = C.abasDoAplicativo({ slug: 'cobranca-feita', faq: [], estado: 'disponivel', instalado: false, sem_rotina: false });
checar(abasCob.map((a) => a.id).join(',') === 'inicio,cobrancas', 'Cobrança não instalada, sem dúvidas: Início · Cobranças (o Configurar exige instalar)', abasCob.map((a) => a.id).join(','));
const abasCobInst = C.abasDoAplicativo({ slug: 'cobranca-feita', faq, estado: 'pausado', instalado: true, sem_rotina: false });
checar(abasCobInst.map((a) => a.id).join(',') === 'inicio,configurar,cobrancas,duvidas', 'Cobrança instalada: Início · Configurar · Cobranças · Dúvidas', abasCobInst.map((a) => a.id).join(','));
checar(abasCobInst.find((a) => a.id === 'configurar')?.componente === 'cobranca-feita/AbaConfigurar' &&
  abasCobInst.find((a) => a.id === 'cobrancas')?.componente === 'cobranca-feita/AbaCobrancas' &&
  abasCobInst.find((a) => a.id === 'cobrancas')?.rotulo === 'Cobranças',
  'o Configurar da Cobrança é o PRÓPRIO (cobranca-feita/AbaConfigurar — nunca o painel com o modal) e "Cobranças" é cobranca-feita/AbaCobrancas (a pasta é o slug)');
checar(C.abasLargas(abasCobInst).join(',') === 'cobrancas', '"Cobranças" é lista: ganha largura');
checar(C.abaValida(abasCob, 'renovacoes') === 'inicio', 'CONTROLE: ?aba=renovacoes num aplicativo sem a aba → Início');
const abasBreve = C.abasDoAplicativo({ slug: 'caca-comissao', faq, estado: 'em_breve', instalado: false, sem_rotina: false });
checar(!abasBreve.some((a) => a.id === 'configurar'), 'em breve: sem Configurar');

// SPEC-139 · L3 (P-16): as três telas que funcionavam viram a aba do trabalho. O Checklist tem Configurar PRÓPRIO
// (o perfil do briefing é da corretora: aparece mesmo sem instalar); Follow-up e Resumo são sob demanda e NÃO têm
// Configurar (D-139-L4-02 — 📊 0 rotinas; o painel seria vazio)
const TRABALHO_L3 = {
  'checklist-6h': ['hoje', 'Hoje', 'checklist-6h/AbaHoje', 'checklist-6h/AbaConfigurar'],
  'follow-up-whatsapp': ['follow-ups', 'Follow-ups', 'follow-up-whatsapp/AbaFollowUps', null],
  'resumo-atendimentos': ['resumos', 'Resumos', 'resumo-atendimentos/AbaResumos', null],
};
for (const [slug, [id, rotulo, componente, configurar]] of Object.entries(TRABALHO_L3)) {
  const inst = C.abasDoAplicativo({ slug, faq, estado: 'ligado', instalado: true, sem_rotina: false });
  const esperadas = configurar ? `inicio,${id},configurar,duvidas` : `inicio,${id},duvidas`;
  checar(inst.map((a) => a.id).join(',') === esperadas, `${slug}: ${esperadas}`, inst.map((a) => a.id).join(','));
  const aba = inst.find((a) => a.id === id);
  checar(aba?.componente === componente && aba?.rotulo === rotulo, `${slug}: a aba "${rotulo}" = components/aplicativos/${componente}.tsx (L3)`);
  if (configurar) checar(inst.find((a) => a.id === 'configurar')?.componente === configurar, `${slug}: Configurar = ${configurar} (L3)`);
  const nao = C.abasDoAplicativo({ slug, faq: [], estado: 'disponivel', instalado: false, sem_rotina: false });
  const esperadasNao = configurar ? `inicio,${id},configurar` : `inicio,${id}`;
  checar(nao.map((a) => a.id).join(',') === esperadasNao, `${slug} não instalado: ${esperadasNao}`, nao.map((a) => a.id).join(','));
  if (!configurar) {
    const ps = C.passosDoComoComecar({ slug, estado: 'ligado', instalado: true, rotinas: 0, sem_rotina: false, conexoes: [] }, { prontidao: null, meuAgger: null });
    checar(ps.map((x) => x.chave).join(',') === 'usar,ligar' && ps[0].link === `/dashboard/auxiliares/${slug}?aba=${id}` && C.abaValida(inst, id) === id,
      `${slug} (sob demanda): o "Como começar" leva à aba ${rotulo} — nunca a um Configurar que não existe`, JSON.stringify(ps.map((x) => [x.chave, x.link])));
  }
  // o endereço que Entregas e o "Abrir agora" usam abre ESTA aba, na casa do aplicativo (nunca galeria/ nem /hoje)
  const tela = C.telaDeExecucao(slug);
  const m = /^\/dashboard\/auxiliares\/([a-z0-9-]+)\?aba=([a-z0-9-]+)$/.exec(tela || '');
  checar(Boolean(m) && m[1] === slug && C.abaValida(inst, m[2]) === m[2] && m[2] === id,
    `${slug}: TELA_DE_EXECUCAO → ${tela} (a aba existe; sem o salto do 307)`);
}
checar(!Object.values(C.TELA_DE_EXECUCAO).some((h) => /galeria\/|\/hoje(\?|$)/.test(h)), 'nenhuma tela de execução aponta para o endereço antigo');
checar(C.abaValida(C.abasDoAplicativo({ slug: 'checklist-6h', faq, estado: 'ligado', instalado: true, sem_rotina: false }), 'resumos') === 'inicio',
  'CONTROLE: a aba de outro aplicativo (?aba=resumos no Checklist) → Início');

// O contrato do import dinâmico (SPEC §5): cada componente é `<pasta>/Aba<Nome>` que o `webpackInclude` da casca enxerga.
// Um arquivo que ainda não existe NÃO quebra o build (contexto do webpack: o que não está no disco não entra) — a aba diz
// "sendo preparada". Os que L2/L3 escreveram ficaram em PENDENTES_DA_COSTURA até chegarem — 🧵 a COSTURA (L6) os trouxe e
// a lista ficou VAZIA: daqui em diante todo componente registrado TEM de existir no disco.
const PENDENTES_DA_COSTURA = new Set([]);
const INCLUIR = new RegExp(/webpackInclude:\s*\/(.+?)\/\s*\*\//.exec(
  fs.readFileSync(path.join(RAIZ, 'components/aplicativos/casca/AbasDoAplicativo.tsx'), 'utf8'))[1]);
const faltando = [];
for (const [slug, abas] of Object.entries(C.ABAS_DO_APLICATIVO)) {
  for (const a of abas.filter((x) => x.componente)) {
    const forma = /^([a-z0-9-]+)\/Aba([A-Za-z0-9]+)$/.test(a.componente) && INCLUIR.test(`./${a.componente}.tsx`);
    checar(forma, `${slug}/${a.id}: "${a.componente}" tem a forma que a casca carrega`);
    const existe = fs.existsSync(path.join(RAIZ, `components/aplicativos/${a.componente}.tsx`));
    if (!existe) faltando.push(a.componente);
    checar(existe || PENDENTES_DA_COSTURA.has(a.componente), `${a.componente}.tsx existe (ou é da L2/L3, pendente da costura)`);
  }
}
if (faltando.length) console.log(`      🧵 ainda não estão nesta árvore (a costura traz): ${faltando.join(', ')}`);
checar(!INCLUIR.test('./cobranca/a-cobranca-na-casca.test.mjs') && !/^([a-z0-9-]+)\/Aba([A-Za-z0-9]+)$/.test('../casca/AbaInicio'),
  'CONTROLE: o contexto não aceita teste nem caminho com ".."');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[5] "Como começar": passos com estado e link, "N de M prontos" — e o que não deu para ler NUNCA conta como pronto');
const itemRen = { slug: 'renovacao', estado: 'disponivel', instalado: false, rotinas: 0, sem_rotina: false,
  conexoes: [{ slug: 'infocap', nome: 'InfoCap', pronto: true, onde: '/c' }] };
const fontes = {
  prontidao: [
    { chave: 'sistema_de_gestao', estado: 'pronto', detalhe: 'ok' },
    { chave: 'agger_da_corretora', estado: 'falta', detalhe: 'falta' },
    { chave: 'equipe', estado: 'em_parte', detalhe: '1 de 2' },
    { chave: 'servicos', estado: 'falta' },
  ],
  meuAgger: true,
};
const pr = C.passosDoComoComecar(itemRen, fontes);
checar(pr.map((x) => x.chave).join(',') === 'sistema_de_gestao,agger_da_corretora,meu_agger,equipe,servicos,ligar', 'Renovação: gestão → Agger da corretora → seu Agger → equipe → regras → Ligar', pr.map((x) => x.chave).join(','));
checar(pr.find((x) => x.chave === 'servicos')?.link === '/dashboard/auxiliares/renovacao?aba=configurar', 'as regras levam DIRETO à aba Configurar (sem o redirect de Serviços)');
checar(pr.every((x) => x.chave === 'ligar' || x.link), 'todo passo (menos Ligar) tem link');
checar(pr.find((x) => x.chave === 'meu_agger')?.link === C.LINK_MEU_PERFIL, '"seu Agger" leva ao Meu perfil');
checar(pr.find((x) => x.chave === 'equipe')?.estado === 'atencao', 'equipe em parte → atenção');
const n1 = C.contagemDosPassos(pr);
checar(n1.prontos === 2 && n1.total === 6, '"2 de 6 prontos" confere (gestão + seu Agger)', JSON.stringify(n1));
const cego = C.passosDoComoComecar(itemRen, { prontidao: null, meuAgger: null });
const nCego = C.contagemDosPassos(cego);
checar(nCego.prontos === 1 && cego.find((x) => x.chave === 'agger_da_corretora')?.estado === 'nao_sei',
  'sem leitura do backend: Agger e equipe "não deu para conferir", nunca pronto (só a InfoCap, que o catálogo leu)', JSON.stringify(nCego));
const ligadoRen = C.contagemDosPassos(C.passosDoComoComecar({ ...itemRen, estado: 'ligado' }, fontes));
checar(ligadoRen.prontos === 3, 'CONTROLE: ligado → o passo Ligar vira pronto (3 de 6)');
// SPEC-132-B · B3 — o Como começar da Cotação Rápida: Agger da corretora → o SEU Agger → as regras, cada um com estado real
const itemCot = { slug: 'cotacao', estado: 'disponivel', instalado: false, rotinas: 0, sem_rotina: true, conexoes: [] };
const fontesCot = (porServico) => ({
  prontidao: [{ chave: 'agger_da_corretora', estado: 'pronto', detalhe: 'ok' }, { chave: 'servicos', estado: 'pronto', ...(porServico ? { por_servico: porServico } : {}) }],
  meuAgger: false,
});
const pc = C.passosDoComoComecar(itemCot, fontesCot({ cotacao: false, renovacao: true }));
checar(pc.map((x) => x.chave).join(',') === 'agger_da_corretora,meu_agger,servicos', 'Cotação: Agger da corretora → seu Agger → regras', pc.map((x) => x.chave).join(','));
checar(pc[1].estado === 'falta' && pc[1].link === C.LINK_MEU_PERFIL && /Agger da corretora/.test(pc[1].detalhe), 'sem o seu Agger: falta, com o link do Meu perfil e o aviso de que sai no da corretora');
checar(pc[2].estado === 'falta' && pc[2].link === '/dashboard/auxiliares/cotacao?aba=configurar',
  'a regra da RENOVAÇÃO não conta como regra da cotação (por_servico.cotacao = false → falta), e leva ao Configurar da cotação');
const pcPronto = C.passosDoComoComecar(itemCot, { ...fontesCot({ cotacao: true, renovacao: false }), meuAgger: true });
checar(C.contagemDosPassos(pcPronto).prontos === 3, 'CONTROLE: Agger da corretora + seu Agger + regras da cotação → 3 de 3');
checar(C.passosDoComoComecar(itemCot, { prontidao: null, meuAgger: null }).every((x) => x.estado === 'nao_sei'),
  'sem leitura do backend: os 3 passos "não deu para conferir", nunca pronto');
const pg = C.passosDoComoComecar({ slug: 'cobranca-feita', estado: 'falta_conectar', instalado: false, rotinas: 0, sem_rotina: false,
  conexoes: [{ slug: 'insurance_portal', nome: 'Portal da Seguradora', pronto: false, onde: '/p' }, { slug: 'whatsapp_zapi', nome: 'WhatsApp', pronto: true, onde: '/w' }] },
  { prontidao: null, meuAgger: null });
checar(pg.map((x) => x.chave).join(',') === 'conexao:insurance_portal,conexao:whatsapp_zapi,configurar,ligar', 'outros: as conexões da corretora → configurar → ligar');
checar(pg.every((x) => !/insurance_portal|whatsapp_zapi/.test(x.titulo + x.detalhe)), 'nenhum slug cru no texto do passo');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[6] O mês da prova é o de São Paulo');
checar(C.inicioDoMesEmSaoPaulo(new Date('2026-10-01T02:00:00Z')) === '2026-09-01T00:00:00-03:00', '01/10 02:00 UTC ainda é setembro em São Paulo');
checar(C.inicioDoMesEmSaoPaulo(new Date('2026-10-13T12:00:00Z')) === '2026-10-01T00:00:00-03:00', 'CONTROLE: 13/10 → outubro');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O DUBLÊ — um banco falso com DUAS corretoras; aplica os filtros como o PostgREST
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
const A = 'aaaaaaaa-0000-0000-0000-000000000001';
const B = 'bbbbbbbb-0000-0000-0000-000000000002';

function bancoFalso(extra = {}) {
  const T = {
    auxiliary_templates: [
      { id: 't-cob', slug: 'cobranca-feita', name: 'Cobrança Feita', headline: 'O boleto chega antes', categories: ['tempo_livre'], catalog_state: 'available',
        required_connectors: ['insurance_portal', 'whatsapp_zapi'], status: 'active', is_active: true, icon: 'ReceiptText', what_it_does: [], data_sources: [] },
      { id: 't-ren', slug: 'renovacao', name: 'Renovação Automática', headline: 'As renovações amanhecem calculadas', categories: ['cliente_blindado'], catalog_state: 'available',
        required_connectors: ['infocap'], status: 'active', is_active: true, icon: 'RefreshCcwDot', featured_rank: 1,
        faq: [{ pergunta: 'Quando?', resposta: 'Antes das 7h.' }], cover_url: null, what_it_does: [], data_sources: [] },
      { id: 't-velha', slug: 'renovacao-maxima', name: 'Renovação Máxima', headline: 'x', categories: [], catalog_state: 'coming_soon',
        required_connectors: [], status: 'active', is_active: false, icon: 'RefreshCcwDot' },
    ],
    tenant_auxiliaries: [
      { id: 'ia-cob', company_id: A, slug: 'cobranca-feita', status: 'paused', last_run_at: null },
      { id: 'ia-ren', company_id: A, slug: 'renovacao', status: 'active', last_run_at: null },
      { id: 'ib-cob', company_id: B, slug: 'cobranca-feita', status: 'active', last_run_at: null },
      { id: 'ib-ren', company_id: B, slug: 'renovacao', status: 'active', last_run_at: null },
    ],
    connector_templates: [
      { slug: 'insurance_portal', name: 'Portal da Seguradora', scope: 'company', is_active: true },
      { slug: 'whatsapp_zapi', name: 'WhatsApp', scope: 'company', is_active: true },
      { slug: 'infocap', name: 'InfoCap', scope: 'company', is_active: true },
      { slug: 'firecrawl', name: 'Firecrawl', scope: 'platform', is_active: true },
    ],
    tenant_connections: [
      { company_id: A, status: 'connected', connector_templates: { slug: 'infocap' } },
      { company_id: B, status: 'connected', connector_templates: { slug: 'infocap' } },
    ],
    portal_accounts: [{ company_id: B, portal_key: 'allianz', health: 'ok' }],
    integrations: [{ company_id: A, provider: 'zapi', is_active: true }, { company_id: B, provider: 'zapi', is_active: true }],
    routines: [
      { id: 'ra1', company_id: A, tenant_auxiliary_id: 'ia-cob' },
      { id: 'rb1', company_id: B, tenant_auxiliary_id: 'ib-cob' },
    ],
    routine_runs: [
      ...Array.from({ length: 3 }, (_, i) => ({ id: `xa${i}`, company_id: A, routine_id: 'ra1', started_at: `2026-10-0${i + 1}T10:00:00Z`, status: 'ok' })),
      ...Array.from({ length: 5 }, (_, i) => ({ id: `xb${i}`, company_id: B, routine_id: 'rb1', started_at: `2026-10-1${i}T10:00:00Z`, status: 'error' })),
      // a armadilha: uma execução da B apontando para a rotina da A (só o filtro company_id a tira da conta)
      { id: 'xbA', company_id: B, routine_id: 'ra1', started_at: '2026-10-12T23:00:00Z', status: 'ok' },
    ],
    renovacao_eventos: [
      ...Array.from({ length: 4 }, (_, i) => ({ id: `ea${i}`, company_id: A, para: 'calculada', criado_em: `2026-10-0${i + 2}T05:00:00Z` })),
      { id: 'ea-velho', company_id: A, para: 'calculada', criado_em: '2026-09-20T05:00:00Z' },
      { id: 'ea-outro', company_id: A, para: 'enviada', criado_em: '2026-10-05T05:00:00Z' },
      ...Array.from({ length: 7 }, (_, i) => ({ id: `eb${i}`, company_id: B, para: 'calculada', criado_em: `2026-10-0${i + 2}T05:00:00Z` })),
    ],
    renovacao_dias: [
      { company_id: A, dia: '2026-10-12', esperadas: 10, calculadas: 9, pendentes: 1, falharam: 0, faltaram: 0 },
      { company_id: B, dia: '2026-10-13', esperadas: 40, calculadas: 40, pendentes: 0, falharam: 0, faltaram: 0 },
    ],
  };
  // SPEC-139: linhas a mais por caso (ex.: um "Em breve" instalado-pausado) — somadas às do banco base
  for (const [tabela, linhas] of Object.entries(extra)) T[tabela] = [...(T[tabela] || []), ...linhas];
  const consultas = [];
  return {
    consultas,
    from(tabela) {
      const q = { tabela, filtros: [], cols: '', head: false, contar: false, ordem: null, lim: null };
      consultas.push(q);
      const api = {
        select(cols, opts) { q.cols = cols || ''; q.head = Boolean(opts?.head); q.contar = opts?.count === 'exact'; return api; },
        eq(c, v) { q.filtros.push(['eq', c, v]); return api; },
        in(c, v) { q.filtros.push(['in', c, v]); return api; },
        gte(c, v) { q.filtros.push(['gte', c, v]); return api; },
        not(c, op, v) { q.filtros.push(['not', c, v]); return api; },
        order(c, o) { q.ordem = [c, o?.ascending !== false]; return api; },
        limit(n) { q.lim = n; return api; },
        then(ok, erro) {
          try {
            if (process.env.DUBLE_SEM_COLUNAS_NOVAS && tabela === 'auxiliary_templates' && /cover_url/.test(q.cols)) {
              return Promise.resolve({ data: null, error: { code: '42703', message: 'column cover_url does not exist' } }).then(ok, erro);
            }
            let linhas = (T[tabela] || []).slice();
            for (const [op, c, v] of q.filtros) {
              if (op === 'eq') linhas = linhas.filter((l) => l[c] === v);
              if (op === 'in') linhas = linhas.filter((l) => v.includes(l[c]));
              if (op === 'gte') linhas = linhas.filter((l) => new Date(l[c]) >= new Date(v));
              if (op === 'not') linhas = linhas.filter((l) => l[c] !== null && l[c] !== undefined);
            }
            if (q.ordem) {
              const [c, asc] = q.ordem;
              linhas.sort((x, y) => (x[c] < y[c] ? -1 : x[c] > y[c] ? 1 : 0) * (asc ? 1 : -1));
            }
            if (q.lim) linhas = linhas.slice(0, q.lim);
            if (tabela === 'auxiliary_templates' && q.cols) {
              // projeta as colunas pedidas, como o PostgREST (o que não foi pedido não volta)
              const pedidas = q.cols.split(',').map((x) => x.trim()).filter(Boolean);
              linhas = linhas.map((l) => Object.fromEntries(pedidas.filter((c) => c in l).map((c) => [c, l[c]])));
            }
            const r = { data: q.head ? null : linhas, error: null, count: q.contar ? linhas.length : null };
            return Promise.resolve(r).then(ok, erro);
          } catch (e) {
            return Promise.reject(e).then(ok, erro);
          }
        },
      };
      return api;
    },
  };
}

const DA_CORRETORA = new Set(['tenant_auxiliaries', 'tenant_connections', 'portal_accounts', 'integrations', 'routines',
  'routine_runs', 'renovacao_eventos', 'renovacao_dias']);

async function catalogoDe(empresa) {
  const db = bancoFalso();
  const { itens } = await C.catalogoDaCorretora(db, empresa);
  return { itens, db };
}

console.log('\n[7] O número do card é DESTA corretora — duas corretoras reais no dublê');
const { itens: daA, db: dbA } = await catalogoDe(A);
const cobA = daA.find((i) => i.slug === 'cobranca-feita');
const renA = daA.find((i) => i.slug === 'renovacao');
checar(cobA?.prova.execucoes === 3, 'A: 3 execuções da Cobrança (não as 5 da B, nem a armadilha da B na rotina da A)', String(cobA?.prova.execucoes));
checar(cobA?.prova.ultima_execucao === '2026-10-03T10:00:00Z', 'A: a última execução é da A', String(cobA?.prova.ultima_execucao));
checar(renA?.prova.renovacoes_no_mes === 4, 'A: 4 renovações calculadas este mês (nem a de setembro, nem a "enviada", nem as 7 da B)', String(renA?.prova.renovacoes_no_mes));
const semFiltro = dbA.consultas.filter((q) => DA_CORRETORA.has(q.tabela) && !q.filtros.some(([op, c, v]) => op === 'eq' && c === 'company_id' && v === A));
checar(semFiltro.length === 0, 'toda consulta a tabela da corretora filtra company_id da sessão', semFiltro.map((q) => q.tabela).join(','));
const { itens: daB } = await catalogoDe(B);
checar(daB.find((i) => i.slug === 'cobranca-feita')?.prova.execucoes === 5 && daB.find((i) => i.slug === 'renovacao')?.prova.renovacoes_no_mes === 7,
  'CONTROLE: a B vê os números DELA (5 execuções, 7 renovações)');
checar(!daA.some((i) => i.slug === 'renovacao-maxima'), 'a vitrine antiga (is_active=false) não aparece');
checar(renA?.icone === 'RefreshCcwDot' && renA?.destaque === 1 && renA?.faq.length === 1, 'renovação: ícone, destaque e dúvidas lidos do catálogo');
checar(cobA?.conexoes.every((c) => c.nome && !/_/.test(c.nome)), '"Funciona com" com nome humano, nunca slug', JSON.stringify(cobA?.conexoes));
checar(cobA?.conectores_pendentes[0]?.nome === 'Portal da Seguradora' && cobA?.conexoes.find((c) => c.slug === 'insurance_portal')?.pronto === false,
  'A sem portal: a Cobrança diz que falta o "Portal da Seguradora" (a B tem portal; não vaza)');
checar(daB.find((i) => i.slug === 'cobranca-feita')?.conexoes.find((c) => c.slug === 'insurance_portal')?.pronto === true,
  'CONTROLE: a B, com portal, vê o portal pronto');

console.log('\n[8] Atividade recente: a fonte REAL (madrugadas; execuções), por corretora');
const atvRen = await C.atividadeRecente(bancoFalso(), A, { slug: 'renovacao', install_id: 'ia-ren' });
checar(atvRen.length === 1 && /9 de 10 calculadas · 1 pendente/.test(atvRen[0].texto), 'Renovação da A: a madrugada da A (não a da B)', JSON.stringify(atvRen));
const atvCob = await C.atividadeRecente(bancoFalso(), A, { slug: 'cobranca-feita', install_id: 'ia-cob' });
checar(atvCob.length === 3 && atvCob.every((x) => x.texto === 'Execução concluída'), 'Cobrança da A: as 3 execuções da A (nenhuma "não concluiu" da B)', JSON.stringify(atvCob.map((x) => x.texto)));

console.log('\n[9] Código antes da migration: a loja abre (sem capa/dúvidas/destaque), nunca VAZIA');
process.env.DUBLE_SEM_COLUNAS_NOVAS = '1';
const { itens: semCols } = await catalogoDe(A);
delete process.env.DUBLE_SEM_COLUNAS_NOVAS;
checar(semCols.length === 2 && semCols.every((i) => i.destaque === null && i.faq.length === 0), 'sem as colunas novas: 2 aplicativos, sem destaque nem dúvidas', String(semCols.length));

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[10] A tela nova: sem emoji, sem cor crua, sem texto miúdo, sem `faint` informativo (checklist do juiz 1, 14, 15)');
const ARQS = [
  'app/dashboard/auxiliares/AuxiliaresClient.tsx',
  'app/dashboard/auxiliares/[slug]/page.tsx',
  'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx',
  'lib/auxiliaries/catalog.ts',
  ...fs.readdirSync(path.join(RAIZ, 'components/aplicativos/casca')).filter((f) => /\.tsx?$/.test(f)).map((f) => `components/aplicativos/casca/${f}`),
  // SPEC-132-B · B3 — a aba Cotações e as regras do cálculo passam pela MESMA régua
  ...fs.readdirSync(path.join(RAIZ, 'components/aplicativos/cotacao')).filter((f) => /\.tsx?$/.test(f)).map((f) => `components/aplicativos/cotacao/${f}`),
];
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B50}\u{FE0F}]/u;
for (const rel of ARQS) {
  const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  const semComentario = fonte.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  checar(!EMOJI.test(semComentario), `${rel}: sem emoji`);
  checar(!/emerald-|amber-/.test(semComentario), `${rel}: sem emerald/amber cru`);
  checar(!/text-\[1[01]px\]/.test(semComentario), `${rel}: sem text-[10px]/[11px]`);
  checar(!/\btext-faint\b/.test(semComentario), `${rel}: sem text-faint`);
}
checar(EMOJI.test('💰') && /emerald-/.test('text-emerald-600'), 'CONTROLE: os detectores acham emoji e cor crua quando existem');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[11] Conserto K2 (juiz de design 3, 4, 10): um botão primário só, selo legível, confirmação da casa, busca fora da URL');
const listar = (dir) => fs.readdirSync(path.join(RAIZ, dir)).filter((f) => /\.tsx?$/.test(f)).map((f) => `${dir}/${f}`);
const TELAS_131B = [
  ...listar('components/aplicativos/casca'),
  ...listar('components/aplicativos/configurar'),
  ...listar('components/aplicativos/renovacao'),
  ...listar('components/aplicativos/cotacao'),
  'components/aplicativos/QuadroOuLista.tsx',
  ...listar('components/perfil'),
  'app/dashboard/auxiliares/AuxiliaresClient.tsx',
  'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx',
  'app/dashboard/configuracoes/page.tsx',
];
function defeitosDeDesign(fonte) {
  const c = fonte.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const d = [];
  // branco sobre `primary` no claro = 4,38:1 (reprova); o primário é `BOTAO_PRIMARIO` (foreground/background no claro)
  if (/(^|[\s'"`])bg-primary(?![\w/-])[\s\S]{0,200}?text-primary-foreground/.test(c)) d.push('bg-primary como botão (use BOTAO_PRIMARIO)');
  // `text-primary` como TEXTO no claro = 4,10–4,38:1; só vale com `dark:` na frente
  if (/(^|[\s'"`])text-primary(?![\w/-])/.test(c)) d.push('text-primary sem dark: (use text-foreground dark:text-primary)');
  // o StatusPill cru sai em font-mono 11 px e com o texto na cor do tom (reprova AA no claro): use o `Selo` da casca
  if (/<StatusPill\b/.test(c)) d.push('StatusPill cru (use o Selo da casca)');
  if (/(^|[^\w.])confirm\(/.test(c)) d.push('confirm() do navegador (use o Confirmar da casca)');
  return d;
}
for (const rel of TELAS_131B) {
  const d = defeitosDeDesign(fs.readFileSync(path.join(RAIZ, rel), 'utf8'));
  checar(d.length === 0, `${rel}: botão, link, selo e confirmação da casa`, d.join(' | '));
}
checar(
  defeitosDeDesign(`<button className="h-11 bg-primary text-primary-foreground">x</button>`).length === 1 &&
    defeitosDeDesign(`<a className="font-medium text-primary hover:underline">x</a>`).length === 1 &&
    defeitosDeDesign(`<StatusPill tone="warning" label="x" />`).length === 1 &&
    defeitosDeDesign(`if (!confirm('Apagar?')) return;`).length === 1 &&
    defeitosDeDesign(`<a className="text-foreground dark:text-primary bg-primary/60 dark:bg-primary dark:text-primary-foreground">x</a>`).length === 0 &&
    defeitosDeDesign(`<span className="h-2 w-2 rounded-full bg-primary" />`).length === 0,
  'CONTROLE: cada detector acha o defeito histórico e aceita a forma consertada',
);
// o import dinâmico das abas só enxerga `<pasta>/Aba<Nome>.tsx` — sem isso, um `*.test.mjs` com `node:child_process`
// dentro de components/aplicativos derrubava a compilação da página do aplicativo (📊 13/10, `next dev`)
const incluir = (fonte) => {
  const m = /webpackInclude:\s*\/(.+?)\/\s*\*\//.exec(fonte);
  if (!m) return null;
  const re = new RegExp(m[1]);
  return re.test('./renovacao/AbaRenovacoes.tsx') && re.test('./casca/AbaInicio.tsx') &&
    !re.test('./renovacao/a-busca-nao-vai-na-url.test.mjs') && !re.test('./casca/a-loja-e-a-casca.test.mjs');
};
const ABAS_FONTE = fs.readFileSync(path.join(RAIZ, 'components/aplicativos/casca/AbasDoAplicativo.tsx'), 'utf8');
checar(incluir(ABAS_FONTE) === true, 'o contexto do import dinâmico só inclui Aba*.tsx (nenhum teste vai ao navegador)');
checar(incluir(ABAS_FONTE.replace(/\/\*\s*webpackInclude:[^*]*\*\//, '')) !== true, 'CONTROLE: sem o webpackInclude o guarda fica VERMELHO');
const SELO = fs.readFileSync(path.join(RAIZ, 'components/aplicativos/casca/Selo.tsx'), 'utf8');
checar(/font-sans text-xs/.test(SELO) && !/font-mono|text-\[1[01]px\]/.test(SELO.replace(/^\s*\/\/.*$/gm, '')) && /text-foreground-2 dark:text-warning/.test(SELO),
  'o Selo: 12 px, sem mono, no claro texto escuro (a cor no ponto)');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[12] Conserto K3 (juiz de design 1 e 8): toda classe `min-h-N` do projeto GERA CSS; confirm() fora também do cofre');
// 📊 13/10: no Tailwind 3.3.3 `min-h-11` não gerava nada (o alvo de 44 px era no-op). O guarda resolve o config REAL
// (o mesmo `resolveConfig` que o Tailwind usa) e exige que cada `min-h-<chave>` escrito no código exista no tema.
const resolveConfig = require('tailwindcss/resolveConfig');
const TW_FONTE = fs.readFileSync(path.join(RAIZ, 'tailwind.config.ts'), 'utf8');
function temaDeMinHeight(fonte) {
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  }).outputText;
  const mod = { exports: {} };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(require, mod, mod.exports);
  return resolveConfig(mod.exports.default || mod.exports).theme.minHeight;
}
function classesMinH(dirs) {
  const achadas = new Map(); // chave -> primeiro arquivo
  const varrer = (d) => {
    for (const e of fs.readdirSync(path.join(RAIZ, d), { withFileTypes: true })) {
      const rel = `${d}/${e.name}`;
      if (e.isDirectory()) { if (!/node_modules|\.next/.test(e.name)) varrer(rel); continue; }
      if (!/\.(tsx?|jsx?)$/.test(e.name) || /\.test\./.test(e.name)) continue;
      const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
      for (const m of fonte.matchAll(/(?<![\w-])(?:[a-z]+:)*min-h-([a-z0-9.]+)(?![\w-]|\.\d|\[)/g)) {
        if (!achadas.has(m[1])) achadas.set(m[1], rel);
      }
    }
  };
  dirs.forEach(varrer);
  return achadas;
}
const MIN_H = temaDeMinHeight(TW_FONTE);
const usadas = classesMinH(['app', 'components', 'lib']);
const semCss = [...usadas].filter(([k]) => !(k in MIN_H)).map(([k, rel]) => `min-h-${k} (${rel})`);
checar(usadas.has('11') && semCss.length === 0, `toda min-h-N usada gera CSS (${usadas.size} chaves: ${[...usadas.keys()].join(', ')})`, semCss.join(' | '));
checar(MIN_H['11'] === '2.75rem' && MIN_H['0'] === '0px' && MIN_H.screen === '100vh' && MIN_H.full === '100%',
  'min-h-11 = 44 px; as que já existiam saem iguais (0 = 0px, screen, full)', JSON.stringify({ 11: MIN_H['11'], 0: MIN_H['0'] }));
const MIN_H_33 = temaDeMinHeight(TW_FONTE.replace(/^\s*minHeight:.*$/m, ''));
checar(!('11' in MIN_H_33) && [...usadas].some(([k]) => !(k in MIN_H_33)),
  'CONTROLE: sem o `minHeight` do config (o 3.3 puro), o guarda fica VERMELHO (min-h-11 não existe)');

const listarFundo = (dir) => fs.readdirSync(path.join(RAIZ, dir)).filter((f) => /\.tsx?$/.test(f)).map((f) => `${dir}/${f}`);
for (const rel of listarFundo('components/vault')) {
  const c = fs.readFileSync(path.join(RAIZ, rel), 'utf8').split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  checar(!/(^|[^\w.])confirm\(/.test(c), `${rel}: sem confirm() do navegador`);
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[13] SPEC-139 · mutação 6 — o "Em breve" é HONESTO: nunca Ligar, nunca Instalar, nunca passo de ligar');
// todas as combinações que um "Em breve" pode ter (até a da Renovação, em que instalar JÁ liga)
const combos = [];
for (const slug of ['renovacao', 'cobranca-feita', 'caca-comissao', 'cotacao']) {
  for (const sem_rotina of [false, true]) {
    for (const conectores_pendentes of [[], [{ slug: 'infocap', nome: 'InfoCap', onde: '/c' }]]) {
      combos.push({ ...base, slug, sem_rotina, conectores_pendentes, estado: 'em_breve', falta_para_existir: 'Falta X.' });
    }
  }
}
const botoesBreve = combos.map((x) => C.botaoPrincipal(x));
const comAcao = botoesBreve.filter((bb) => bb.tipo !== 'desabilitado' || /Ligar|Instalar/.test(bb.rotulo));
checar(comAcao.length === 0 && botoesBreve.every((bb) => bb.rotulo === 'Em breve' && bb.motivo === 'Falta X.'),
  `em breve (${combos.length} combinações): botão "Em breve" desabilitado, com o que falta — nunca Ligar/Instalar`, JSON.stringify(comAcao[0] ?? ''));
checar(combos.every((x) => C.passosDoComoComecar({ ...x, instalado: false, rotinas: 0, conexoes: [{ slug: 'infocap', nome: 'InfoCap', pronto: false, onde: '/c' }] },
  { prontidao: null, meuAgger: null }).length === 0), 'em breve: nenhum passo no "Como começar" (nem "Ligar")');
const abasBreveRegistrado = C.abasDoAplicativo({ slug: 'cobranca-feita', faq, estado: 'em_breve', instalado: true, sem_rotina: false });
checar(abasBreveRegistrado.map((a) => a.id).join(',') === 'inicio,duvidas', 'em breve: só Início e Dúvidas — mesmo um aplicativo com abas de trabalho registradas', abasBreveRegistrado.map((a) => a.id).join(','));
checar(C.abasDoAplicativo({ slug: 'caca-comissao', faq: [], estado: 'em_breve', instalado: false, sem_rotina: false }).map((a) => a.id).join(',') === 'inicio',
  'em breve sem dúvida escrita: só Início');
// a ponta de cima do fio: um "Em breve" que a corretora tinha instalado (pausado) continua "Em breve" no catálogo dela
// (a armadilha: instalação ≠ existir — se a regra "pausado → Ligar" vier antes do "coming_soon", o Ligar aparece)
{
  const { itens } = await C.catalogoDaCorretora(bancoFalso({
    auxiliary_templates: [{ id: 't-caca', slug: 'caca-comissao', name: 'Caça-Comissão', headline: 'x', categories: [], catalog_state: 'coming_soon',
      required_connectors: [], missing_for_launch: 'Falta a InfoCap.', what_it_does: [], data_sources: [], icon: 'HandCoins',
      status: 'active', is_active: true }],
    tenant_auxiliaries: [{ id: 'ia-caca', company_id: A, slug: 'caca-comissao', status: 'paused', last_run_at: null }],
  }), A);
  const caca = itens.find((i) => i.slug === 'caca-comissao');
  const bCaca = caca ? C.botaoPrincipal(caca) : null;
  checar(caca?.estado === 'em_breve' && bCaca?.tipo === 'desabilitado' && bCaca?.motivo === 'Falta a InfoCap.',
    'catálogo: "Em breve" instalado-pausado na corretora continua "Em breve" — botão desabilitado (nunca "Ligar" de pausado)', JSON.stringify({ e: caca?.estado, b: bCaca }));
  checar(C.provaDoCard(caca ?? { ...base, estado: 'x' }) === 'Em breve', 'catálogo: a prova do "Em breve" é "Em breve" (nenhum número)');
}
checar(C.botaoPrincipal({ ...base, slug: 'renovacao', estado: 'disponivel' }).rotulo === 'Ligar' &&
  C.botaoPrincipal({ ...base, estado: 'pausado' }).rotulo === 'Ligar',
  'CONTROLE: fora do "Em breve" o Ligar existe (o guarda CONSEGUE ver um Ligar)');
const INICIO = fs.readFileSync(path.join(RAIZ, 'components/aplicativos/casca/AbaInicio.tsx'), 'utf8');
checar(/emBreve \? 'O que ele vai fazer' : 'O que faz'/.test(INICIO) && /emBreve \? \(\s*<Bloco titulo="Ainda não está pronto">/.test(INICIO),
  'o Início do "Em breve" diz "O que ele vai fazer" e "Ainda não está pronto" (no lugar do Como começar)');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[14] SPEC-139 §4.2 — o "Como começar" da Cobrança: portal · número que envia · regras · ligar ("N de M prontos")');
const itemCob = { slug: 'cobranca-feita', estado: 'pausado', instalado: true, rotinas: 0, sem_rotina: false,
  conexoes: [{ slug: 'insurance_portal', nome: 'Portal da Seguradora', pronto: true, onde: '/p' }, { slug: 'whatsapp_zapi', nome: 'WhatsApp', pronto: false, onde: '/w' }] };
const pCob = C.passosDoComoComecar(itemCob, { prontidao: null, meuAgger: null });
checar(pCob.map((x) => x.chave).join(',') === 'conexao:insurance_portal,conexao:whatsapp_zapi,configurar,ligar', 'a ordem: portal → número que envia → regras → ligar', pCob.map((x) => x.chave).join(','));
checar(pCob[0].titulo === 'Conectar o portal da seguradora' && pCob[1].titulo === 'Conectar o número que envia' && pCob[2].titulo === 'Escolher as regras da cobrança',
  'cada passo diz o que a conexão É para a Cobrança', pCob.map((x) => x.titulo).join(' | '));
checar(pCob[2].link === '/dashboard/auxiliares/cobranca-feita?aba=configurar' && pCob[1].link === '/w',
  'as regras levam à aba Configurar (o modal saiu); o número, a onde se conecta');
const nCob = C.contagemDosPassos(pCob);
checar(nCob.prontos === 1 && nCob.total === 4, '"1 de 4 prontos" (só o portal)', JSON.stringify(nCob));
const pCobNao = C.passosDoComoComecar({ ...itemCob, instalado: false, estado: 'disponivel' }, { prontidao: null, meuAgger: null });
checar(pCobNao[2].link === null && /Instalar/.test(pCobNao[2].titulo), 'não instalada: "Instalar e escolher as regras" (o botão Instalar abre o Configurar)');
checar(C.passosDoComoComecar({ ...itemCob, slug: 'checklist-6h' }, { prontidao: null, meuAgger: null })[0].titulo === 'Conectar Portal da Seguradora',
  'CONTROLE: os outros aplicativos seguem "Conectar <nome>"');
const DETALHE = fs.readFileSync(path.join(RAIZ, 'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx'), 'utf8');
checar(/configurarDaCasca = abas\.some\(\(a\) => a\.id === 'configurar' && a\.componente === null\)/.test(DETALHE) &&
  /instalado && configurarDaCasca \?/.test(DETALHE),
  'o painel com o modal só monta quando o Configurar é da casca — na Cobrança, nunca (o botão leva à aba Configurar)');
checar(/router\.push\(`\/dashboard\/auxiliares\/\$\{item\.slug\}\?aba=configurar`/.test(DETALHE), 'Instalar leva direto à aba Configurar');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[15] SPEC-139 · L4 × L1 — a cor do tile tem UM ponto de leitura (`estiloDoTile`); nenhum import de arquivo que não existe');
const CARD = fs.readFileSync(path.join(RAIZ, 'components/aplicativos/casca/CardDoAplicativo.tsx'), 'utf8');
checar(/export function estiloDoTile\(/.test(CARD) && /style=\{estiloDoTile\(\{ slug, matiz \}\)\}/.test(CARD), 'TileDoIcone lê a cor SÓ de estiloDoTile');
const casca = listar('components/aplicativos/casca');
const outrosCalculam = casca.filter((rel) => {
  const c = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  return rel !== 'components/aplicativos/casca/CardDoAplicativo.tsx' && rel !== 'components/aplicativos/casca/CapaGerada.tsx' &&
    /icone-aplicativo|--app-h/.test(c.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n'));
});
checar(outrosCalculam.length === 0, 'nenhum outro arquivo da casca calcula a cor do tile (o cabeçalho passa por TileDoIcone)', outrosCalculam.join(','));
const MEUS_L4 = ['components/aplicativos/casca/CardDoAplicativo.tsx', 'components/aplicativos/casca/AbaInicio.tsx',
  'components/aplicativos/casca/ComoComecar.tsx', 'app/dashboard/auxiliares/AuxiliaresClient.tsx', 'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx'];
const quebrados = [];
for (const rel of MEUS_L4) {
  const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  for (const m of fonte.matchAll(/from '(\.\/[^']+|@\/[^']+)'/g)) {
    const alvo = m[1].startsWith('@/') ? path.join(RAIZ, m[1].slice(2)) : path.join(path.dirname(path.join(RAIZ, rel)), m[1]);
    if (!['.ts', '.tsx', '/index.ts', '/index.tsx'].some((ext) => fs.existsSync(alvo + ext)) && !fs.existsSync(alvo)) quebrados.push(`${rel} → ${m[1]}`);
  }
}
checar(quebrados.length === 0, 'todo import estático dos arquivos da L4 existe nesta árvore (a paleta da L1 entra pela costura)', quebrados.join(' | '));

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[16] SPEC-139 · a migration de conteúdo: só texto global, idempotente, dúvidas bem formadas, sem jargão');
const MIG = fs.readFileSync(path.join(RAIZ, 'backend/supabase/migrations/20261016_01_spec139_conteudo_dos_aplicativos.sql'), 'utf8');
const MIG_SQL = MIG.split('\n').filter((l) => !/^\s*--/.test(l)).join('\n');
checar(/-- APPLY/.test(MIG) && /-- VERIFY/.test(MIG) && /-- ROLLBACK/.test(MIG), 'APPLY · VERIFY · ROLLBACK escritos');
const tabelas = [...MIG_SQL.matchAll(/\bupdate\s+public\.([a-z_]+)/gi)].map((m) => m[1]);
checar(tabelas.length > 0 && tabelas.every((t) => t === 'auxiliary_templates') && !/\b(alter|create|drop|insert|delete|truncate|grant)\b/i.test(MIG_SQL),
  'só UPDATE em auxiliary_templates (nenhum DDL, nenhum dado de corretora)', tabelas.join(','));
checar(!/catalog_state\s*=/.test(MIG_SQL) && !/\b(is_active|status)\s*=/.test(MIG_SQL.replace(/where[\s\S]*?;/g, ';')),
  'não muda catalog_state, is_active nem status (o "Em breve" é decisão, não conteúdo)');
const blocosJson = [...MIG_SQL.matchAll(/'(\[[\s\S]*?\])'::jsonb/g)].map((m) => m[1].replace(/''/g, "'"));
let jsonOk = blocosJson.length >= 16;
let nDuvidas = 0;
for (const bj of blocosJson) {
  try {
    const arr = JSON.parse(bj);
    for (const d of arr) {
      if (d.pergunta !== undefined) { nDuvidas += 1; if (typeof d.pergunta !== 'string' || typeof d.resposta !== 'string' || !d.pergunta.endsWith('?')) jsonOk = false; }
      else if (typeof d.tarefa !== 'string' || typeof d.frequencia !== 'string') jsonOk = false;
    }
  } catch { jsonOk = false; }
}
checar(jsonOk, `todo jsonb é JSON válido: ${blocosJson.length} listas, ${nDuvidas} dúvidas com pergunta (?) e resposta`);
const faqSlugs = [...MIG_SQL.matchAll(/\('([a-z0-9-]+)', '\[/g)].map((m) => m[1]);
checar(faqSlugs.length === 15 && !faqSlugs.includes('quem-cobra-menos') && !faqSlugs.includes('renovacao') && !faqSlugs.includes('cotacao'),
  '15 aplicativos ganham dúvidas; Renovação, Cotação e QCM intocados', faqSlugs.join(','));
checar(/and \(t\.faq is null or t\.faq = '\[\]'::jsonb\)/.test(MIG_SQL), 'a dúvida já escrita por alguém nunca é sobrescrita (idempotente)');
const updates = MIG_SQL.split(/;\s*\n/).filter((s) => /\bupdate\b/i.test(s));
checar(updates.every((u) => /\bwhere\b[\s\S]*(like|=|is null|jsonb_typeof)/i.test(u)), `cada UPDATE (${updates.length}) só casa o texto ANTIGO (rodar de novo não muda nada)`);
const textoNovo = blocosJson.join(' ') + ' ' + [...MIG_SQL.matchAll(/=\s*E?'((?:[^']|'')*)'/g)].map((m) => m[1]).join(' ') +
  ' ' + [...MIG_SQL.matchAll(/,\s*\n\s*'((?:[^']|'')+)'\)/g)].map((m) => m[1]).join(' ');
const JARGAO = /\b(auxiliar(es)?|rotinas?|payload|dry-run|read-only|MVP|Founder|endpoint|espelho)\b/i;
const jargaoNovo = textoNovo.replace(/Este auxiliar|Auxiliar que analisa%|Auxiliar read-only%|Cada uma vira uma rotina com horário próprio|Precisa[^']*|Depende de decisão do Founder[^']*/g, '');
checar(!JARGAO.test(jargaoNovo), 'o texto NOVO fala de gente: sem "auxiliar", "rotina", "Founder", "endpoint", "espelho"…', (jargaoNovo.match(JARGAO) || [''])[0]);
checar(JARGAO.test('Precisa do espelho da carteira e de decisão do Founder'), 'CONTROLE: o detector acha o jargão de antes');
checar(!/(Resulta|AutoFleet|Amandus)/i.test(MIG), 'nenhum nome de corretora (CLAUDE.md §13.9)');
checar(!/\b\d+\s*%|\b\d+\s*(execuções|boletos|clientes)/.test(blocosJson.join(' ')), 'nenhum número inventado nas dúvidas (D-131-26)');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[17] SPEC-139 · a galeria (laudo §2.2–§2.3): destaque no topo, "Em breve" em linha compacta só com ícone');
const GAL = fs.readFileSync(path.join(RAIZ, 'app/dashboard/auxiliares/AuxiliaresClient.tsx'), 'utf8');
checar(GAL.indexOf('<DestaqueDoAplicativo') > -1 && GAL.indexOf('<DestaqueDoAplicativo') < GAL.indexOf('<ToggleGroup'), 'o destaque vem antes da barra (topo)');
checar(/i\.destaque !== null && i\.estado !== 'em_breve'/.test(GAL), 'o destaque nunca é um "Em breve"');
checar(/emBreve \? \([\s\S]{0,200}<LinhaEmBreve/.test(GAL), 'o grupo "Em breve" usa a linha compacta');
const linha = /export function LinhaEmBreve[\s\S]*?\r?\n}\r?\n/.exec(CARD)?.[0] ?? '';
checar(linha.length > 0 && !/<CapaGerada/.test(linha) && /<TileDoIcone[^>]*apagado/.test(linha) && !/provaDoCard|Ligar|Instalar/.test(linha),
  'a linha do "Em breve": só o ícone apagado, nome, frase e o selo — sem capa, sem prova, sem Ligar');
checar(/<CapaGerada/.test('export function LinhaEmBreve() { return <CapaGerada /> }'), 'CONTROLE: o detector de capa acha a capa quando ela existe');

console.log(falhas === 0 ? '\nA LOJA E A CASCA: TODOS OS GUARDAS VERDES\n' : `\n${falhas} GUARDA(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
