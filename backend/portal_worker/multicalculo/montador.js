// O MONTADOR do robô do Agger — SPEC-129-B U3 (D-129B-02). Roda DENTRO da página do Agger.
//
// 🔴 Por que JavaScript e não Python: o corpo do `calcularV2` leva, item a item, as CREDENCIAIS de cada seguradora
// (login, senha, loginWs, senhaWs, códigos de corretor — 📊 82 das 111 chaves vêm da config, LAUDO-M0-M3 §M0a).
// Montado aqui, nenhuma senha de seguradora entra no Python: o que volta ao Python já passou pela LISTA BRANCA
// do endpoint (`filtrar`), e o Python confere de novo (agger_robo).
//
// Provado: o `calculos[]` montado só com `GET api-prod/calculo/seguradoras` + coberturas + comissão bate com o
// corpo feito pela TELA — 📊 786/786 chaves (conta A, 16 seguradoras) e 657/657 (conta B, 12) — e AO VIVO
// (05/10 M1: 201, 13 seguradoras com oferta, menor preço igual ao da tela em 11 de 13).
//
// Carregado por `agger_robo` com `(0, eval)(fonte)`; expõe `window.__abM`. Nada aqui faz rede.
(function () {
  // Itens que NÃO têm config própria e herdam a de outra seguradora (📊 M0a, 30/30 e 26/26 chaves iguais):
  //   Itaú (9), Azul (10) e Mitsui (13) usam a config da Porto (8); Aliro (22) usa a da Liberty Site/Yelum (12).
  const GRUPO = {9: 8, 10: 8, 13: 8, 22: 12};
  // Configs que a tela NÃO manda no automóvel (📊 M0a): Darwin (46) na conta A; Sompo (6), SulAmérica (17),
  // Alfa (18), Chubb (32), MetLife (34), Axa (35) na conta B (sem automóvel no app). A Mitsui (13) sai da
  // lista "própria" porque entra pelo GRUPO (da Porto), levando a config dela em `mitsuiCfg`.
  const EXCLUI = new Set([46, 6, 17, 18, 32, 34, 35, 13]);
  // `nome` = o nome COMERCIAL que a tela manda (📊 corpo da tela: "Yelum" ao lado de nomeSeguradora "Liberty Site").
  const NOME = {4: 'HDI', 12: 'Yelum', 45: 'Azul por Assinatura', 8: 'Porto Seguro', 9: 'Itaú', 10: 'Azul', 13: 'Mitsui', 22: 'Aliro'};
  // `nomeSeguradora` dos itens herdados (senão levariam o nome da config-base).
  const NOMESEG = {9: 'Itaú', 10: 'Azul', 13: 'Mitsui', 22: 'Aliro'};
  // Chaves que existem SÓ na config de origem e a tela NÃO copia para o item (📊 M0a: o corpo da tela não as tem).
  const SO_SEG = new Set(['id', 'usuario', 'mitsuiCodigoCorretor', 'mitsuiFiliais', 'mitsuiFilialLista', 'mitsuiFilialNome',
    'percComissaoEmpres', 'percComissaoResid', 'percComissaoVida', 'percDescontoEmpres', 'percDescontoResid', 'percDescontoVida',
    'alfaCodigoCorretor', 'sompoCodigoCorretor', 'sompoUnidadeNome', 'sompoUnidades', 'sulAmericaAcaoApoio', 'sulAmericaCodUnidOper',
    'sulAmericaConvenio', 'sulAmericaEstrApoio', 'sulAmericaEstrVenda', 'sulAmericaKitPath', 'sulAmericaSucursal', 'unidadesSompoLista']);
  // As chaves que o APP escolhe por cálculo (📊 M0a: 23 só existem no pedido; estas são as de cobertura + comissão/desconto).
  const DO_APP = ['tipoCobertura', 'tipoFranquia', 'isDanosMateriais', 'isDanosCorporais', 'isDanosMorais', 'isAppMorte',
    'isBlindagemValor', 'carroReserva', 'carroReservaAr', 'vidros', 'assist24hs', 'despesasExtra', 'protecaoPneuRodas',
    'reparoRapido', 'valorDeNovo', 'percComissao', 'percDesconto'];

  // segs = `calculo/seguradoras` (config achatada) · cob = coberturas · comissao/desconto = null mantém o da config.
  function montarCalculos(segs, cob, comissao, desconto) {
    const S = {};
    for (const s of segs || []) if (s && s.ativo) S[s.seguradora] = s;          // só as ATIVAS na conta
    const alvo = new Set(Object.keys(S).map(Number).filter(k => !EXCLUI.has(k)));
    for (const [item, base] of Object.entries(GRUPO)) if (S[base]) alvo.add(Number(item));   // herdeiros da base ativa
    const out = [];
    for (const k of [...alvo].sort((a, b) => a - b)) {                          // a tela ordena pelo código
      const base = S[GRUPO[k] || k];
      const it = {};
      for (const [kk, vv] of Object.entries(base)) if (!SO_SEG.has(kk)) it[kk] = vv;
      it.seguradora = k;
      if (NOMESEG[k]) it.nomeSeguradora = NOMESEG[k];
      it.nome = NOME[k] || it.nomeSeguradora;
      // 📊 12/12 dos não agrupados: idIntegracaoCfg = idIntegracaoCfgSeg = idIntegracao da config-base.
      it.idIntegracaoCfg = base.idIntegracao; it.idIntegracaoCfgSeg = base.idIntegracao;
      if (!('libertyCodigoEstabelecimento' in it)) it.libertyCodigoEstabelecimento = null;   // a tela manda null
      if (k === 9 || k === 22) it.percDesconto = 0;                             // 📊 Itaú e Aliro: a tela manda 0
      if (k === 13) {                                                           // Mitsui: desconto da base (null→0) e a config própria em mitsuiCfg (id→ID)
        it.percDesconto = (base.percDesconto == null ? 0 : base.percDesconto);
        if (S[13]) { const m = {}; for (const [kk, vv] of Object.entries(S[13])) m[kk === 'id' ? 'ID' : kk] = vv; it.mitsuiCfg = m; }
      }
      if (!('percDesconto' in it)) it.percDesconto = null;
      Object.assign(it, cob || {});
      it.libertyDescontoRegional = 1;                                           // 📊 a tela manda 1 em todos
      if (k === 45) { it.percComissao = null; it.percDesconto = null; it.segSemComDesc = true; }   // Azul por Assinatura: sem comissão/desconto
      else {
        if (comissao != null) it.percComissao = comissao;                       // a "comissão padrão" da tela SOBRESCREVE a config (📊 82 de 208)
        if (desconto != null && it.percDesconto != null) it.percDesconto = desconto;
      }
      if (k === 8) { it.percComissao3 = it.percComissao; it.percDesconto3 = it.percDesconto; }   // 📊 Porto leva a cópia "3"
      out.push(it);
    }
    return out;
  }

  // Recálculo a partir de UMA versão: as escolhas do app (DO_APP) vêm do item da MESMA seguradora na versão-base;
  // as credenciais vêm da config ATUAL (montarCalculos). Seguradora que não estava na base fica de fora.
  function montarDaVersao(segs, versao) {
    const base = {};
    for (const c of (versao && versao.calculos) || []) if (c && c.seguradora != null) base[c.seguradora] = c;
    const out = [];
    for (const it of montarCalculos(segs, {}, null, null)) {
      const b = base[it.seguradora];
      if (!b) continue;
      for (const k of DO_APP) if (k in b) it[k] = b[k];
      if (it.seguradora === 8) { it.percComissao3 = it.percComissao; it.percDesconto3 = it.percDesconto; }
      out.push(it);
    }
    return out;
  }

  // Ajuste do corretor (contrato.Ajuste): campo do item → valor; seguradora null = todas.
  const CAMPO_DO_AJUSTE = {comissao: 'percComissao', desconto: 'percDesconto', assistencia: 'assist24hs',
    carro_reserva: 'carroReserva', vidros: 'vidros', franquia: 'tipoFranquia', cobertura: 'tipoCobertura'};
  function aplicarAjuste(cotacao, ajuste) {
    if (!ajuste) return 0;
    let n = 0;
    if (ajuste.tipo === 'percentual_fipe') {
      for (const a of cotacao.automoveis || []) { a.pctAjuste = ajuste.valor; n++; }
      return n;
    }
    for (const it of cotacao.calculos || []) {
      if (ajuste.seguradora != null && it.seguradora !== ajuste.seguradora) continue;
      if (ajuste.tipo === 'cobertura' && ajuste.valor && typeof ajuste.valor === 'object') {
        for (const [k, v] of Object.entries(ajuste.valor)) if (DO_APP.includes(k)) it[k] = v;
      } else if (CAMPO_DO_AJUSTE[ajuste.tipo]) {
        it[CAMPO_DO_AJUSTE[ajuste.tipo]] = ajuste.valor;
      } else continue;
      if (it.seguradora === 8) { it.percComissao3 = it.percComissao; it.percDesconto3 = it.percDesconto; }
      n++;
    }
    return n;
  }

  // O automóvel a partir de `buscaPlaca` + `fipeModelo` + o que o pedido trouxe (o pedido VENCE; os GETs preenchem).
  // 📊 M1: 0 campos diferentes da tela depois de 2 regras — descricao = fipeModelo[0].modelo e fipeTxt = a STRING 'null'.
  const COMBUSTIVEL = {Flex: 6};   // 📊 só o Flex foi medido (6); os outros ficam com o código do pedido
  function montarAutomovel(parcial, bp, fm) {
    const a = Object.assign({}, parcial);
    bp = bp || {};
    const m = (Array.isArray(fm) && fm[0]) || {};
    const vs = m.fipeValores || [];
    const ult = vs.reduce((acc, v) => Math.max(acc, v.anoVersaoTabela * 100 + v.mesVersaoTabela), 0);
    const atuais = vs.filter(v => v.anoVersaoTabela * 100 + v.mesVersaoTabela === ult);
    const esc = atuais.find(v => COMBUSTIVEL[v.combustivel] === a.combustivel) || atuais.find(v => v.combustivel === 'Flex') || atuais[0] || {};
    if (a.fabricante == null) a.fabricante = bp.codFabr;
    if (a.anoModelo == null) a.anoModelo = bp.anoMod != null ? Number(bp.anoMod) : null;
    if (a.anoFabricacao == null) a.anoFabricacao = Number(bp.anoFab || bp.anoMod) || a.anoModelo;
    if (!a.fipe) a.fipe = bp.fipe;
    if (!a.chassi) a.chassi = bp.chassi || null;
    if (!a.placa) a.placa = bp.placa || null;
    a.descricao = m.modelo || a.descricao || bp.modelo || null;
    a.valReferenciado = esc.valor != null ? esc.valor : (a.valReferenciado != null ? a.valReferenciado : null);
    if (a.combustivel == null) a.combustivel = COMBUSTIVEL[esc.combustivel] != null ? COMBUSTIVEL[esc.combustivel] : null;
    a.fipeTxt = 'null';   // 📊 o app manda a STRING 'null'
    return a;
  }

  // A LISTA BRANCA em JS: só os caminhos de `leitor_agger.LISTA_BRANCA_POR_ENDPOINT[endpoint]` sobrevivem.
  // Notação igual à do leitor: `a.b` chave · `a[]` item de lista. PDF e nº de cálculo viram MARCA (o leitor só
  // precisa saber que EXISTEM): a URL do PDF nunca sai da página.
  const MARCA = {pathPdf: '<removido:pdf>', pdfFileNameAgger: '<removido:pdf>', nroCalculo: '<presente>'};
  function filtrar(valor, lista) {
    const ok = new Set(lista);
    const prefixos = new Set();
    for (const p of lista) { let s = ''; for (const parte of p.split(/(?=\.)|(?=\[\])/)) { s += parte; prefixos.add(s); } }
    const junta = (pre, k) => pre ? pre + '.' + k : k;
    function anda(v, caminho, chave) {
      if (Array.isArray(v)) {
        const c = caminho + '[]';
        if (!prefixos.has(c) && !ok.has(c)) return undefined;
        const out = [];
        for (const x of v) { const y = anda(x, c, null); if (y !== undefined) out.push(y); }
        return out;
      }
      if (v && typeof v === 'object') {
        const out = {};
        for (const [k, x] of Object.entries(v)) {
          const c = junta(caminho, k);
          if (!ok.has(c) && !prefixos.has(c)) continue;
          const y = anda(x, c, k);
          if (y !== undefined) out[k] = y;
        }
        // objeto onde a lista espera FOLHA (ex.: um erro que veio como objeto): some inteiro, não vira `{}` órfão
        if (!Object.keys(out).length && Object.keys(v).length) return undefined;
        return out;
      }
      if (!ok.has(caminho)) return undefined;
      if (chave && MARCA[chave] && v) return MARCA[chave];
      return v;
    }
    return anda(valor, '', null);
  }

  window.__abM = {montarCalculos, montarDaVersao, aplicarAjuste, montarAutomovel, filtrar, DO_APP};
})();
