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

  // ===================================================================================================================
  // SPEC-129-C — o RE (Condomínio 16 · Residencial 2 · Empresarial 18). O auto acima NÃO muda (byte a byte).
  // 📊 As 9 gravações reais (tests/fixtures/agger_ramos/gravacao_*): o MESMO envelope e o MESMO calcularV2, mas
  //   · as COBERTURAS moram em `cotacao.configuracoes` (uma vez) — 0 chaves de cobertura nos itens (o Python as põe lá);
  //   · cada item = a config da seguradora + `percComissao` (a comissão EFETIVA: 📊 20·22·25·30·40 no item, ecoada em
  //     `resultados[].coberturas.percComissao`; o `percComissao<Ramo>` da config fica 10/0 e NÃO é a usada);
  //   · empresarial: + `valoresAjusteSeguradora.imovelAtividadeProfissionalLocal = {Key, Value, Description}`.
  // ===================================================================================================================
  const RAMO_AUTO = 31;
  // 📊 `nome` dos itens de RE gravados: 'HDI', 'CHUBB', 'Yelum', 'Porto Seguro', 'Tokio', 'Axa'… (o NOME do auto + Chubb,
  //    que o auto não manda)
  const NOME_RE = Object.assign({}, NOME, {32: 'CHUBB'});
  // No RE só `id`/`usuario` ficam fora do item: 📊 os itens gravados de RE trazem TODOS os percComissao*/percDesconto*
  // (BLOCO0-GRAVACAO §2). 💭 o conjunto exato que o cliente manda só um POST interceptado dirá (canário F3).
  const SO_SEG_RE = new Set(['id', 'usuario']);
  // O DESCONTO padrão do ramo que a tela aplica (`setComissaoDefault`: percDesconto ← percDesconto<Ramo>) — 📊 Allianz
  // percDesconto 25 = percDescontoCond 25 no item do condomínio (gravacao_condominio_1/2). A COMISSÃO nunca cai no
  // padrão da conta (📊 percComissaoEmpres = 0 nas 10): ela vem do pedido, explícita (D-129C-05) — sem ela, nada sai.
  const DESCONTO_DO_RAMO = {16: 'percDescontoCond', 2: 'percDescontoResid', 18: 'percDescontoEmpres'};

  // segs = `calculo/seguradoras` · opcoes = {status: [códigos do ramo], fora: [10, 22], atividades: {cod: {Key,Value,…}}}
  // → {calculos, semAtividade: [[cod, nome]]}. Sem comissão → {erro: 'sem_comissao'} (nada é montado).
  function montarCalculosRE(segs, ramo, comissao, desconto, opcoes) {
    opcoes = opcoes || {};
    if (comissao == null) return {erro: 'sem_comissao', calculos: [], semAtividade: []};
    const status = new Set(opcoes.status || []);
    const fora = new Set(opcoes.fora || [10, 22]);
    const atividades = opcoes.atividades || {};
    const S = {};
    for (const s of segs || []) if (s && s.ativo) S[s.seguradora] = s;          // só as ATIVAS na conta
    const alvo = Object.keys(S).map(Number).filter(k => status.has(k) && !fora.has(k)).sort((a, b) => a - b);
    const out = [];
    const semAtividade = [];
    for (const k of alvo) {
      const base = S[k];
      let atividade = null;
      if (ramo === 18) {
        atividade = atividades[k] || atividades[String(k)] || null;
        if (!atividade) { semAtividade.push([k, NOME_RE[k] || base.nomeSeguradora || '']); continue; }
      }
      const it = {};
      for (const [kk, vv] of Object.entries(base)) if (!SO_SEG_RE.has(kk)) it[kk] = vv;
      it.seguradora = k;
      it.nome = NOME_RE[k] || it.nomeSeguradora;
      it.idIntegracaoCfg = base.idIntegracao; it.idIntegracaoCfgSeg = base.idIntegracao;   // 📊 nos itens gravados
      if (!('libertyCodigoEstabelecimento' in it)) it.libertyCodigoEstabelecimento = null;  // 📊 null nos gravados
      it.libertyDescontoRegional = 1;                                                       // 📊 1 nos gravados
      it.percComissao = comissao;                                                           // 🔴 D-129C-05
      const dRamo = base[DESCONTO_DO_RAMO[ramo]];
      it.percDesconto = desconto != null ? desconto : (dRamo == null ? null : dRamo);
      // ⚠️ SEM a cópia "3" da Porto: 📊 no RE a Porto leva percComissao3 da config (0/ausente), não a da comissão
      if (atividade) {
        it.valoresAjusteSeguradora = {imovelAtividadeProfissionalLocal: {Key: atividade.Key, Value: atividade.Value,
          Description: atividade.Description == null ? null : atividade.Description}};
      }
      out.push(it);
    }
    return {calculos: out, semAtividade};
  }

  // Recálculo de RE a partir de UMA versão: a config ATUAL + a comissão/desconto e a atividade do item da MESMA
  // seguradora na versão-base (as coberturas já vêm em `configuracoes` da versão).
  function montarDaVersaoRE(segs, versao, opcoes) {
    const base = {};
    for (const c of (versao && versao.calculos) || []) if (c && c.seguradora != null) base[c.seguradora] = c;
    const atividades = {};
    for (const [k, c] of Object.entries(base)) {
      const a = c.valoresAjusteSeguradora && c.valoresAjusteSeguradora.imovelAtividadeProfissionalLocal;
      if (a) atividades[k] = a;
    }
    const r = montarCalculosRE(segs, versao.ramo, 0, null, {status: (opcoes || {}).status, fora: (opcoes || {}).fora,
                                                            atividades});
    const out = [];
    for (const it of r.calculos) {
      const b = base[it.seguradora];
      if (!b) continue;
      it.percComissao = b.percComissao;
      if ('percDesconto' in b) it.percDesconto = b.percDesconto;
      out.push(it);
    }
    return out;
  }

  // Ajuste no RE: comissão/desconto no ITEM; assistência e cobertura em `configuracoes` (a cobertura do RE é do
  // negócio, não da seguradora: ajuste de cobertura POR seguradora não tem onde morar → 0, "ajuste sem alvo").
  // 🔴 GÊMEO de `presets.CAMPO_DO_AJUSTE_RE`.
  const CAMPO_DO_AJUSTE_RE = {comissao: 'percComissao', desconto: 'percDesconto', assistencia: 'assist24hs'};
  const CHAVE_DA_BASICA_RE = 'isDanosIncendioRaioExplosao';   // 🔴 GÊMEO de `presets.CHAVE_DA_BASICA`
  function aplicarAjusteRE(cot, ajuste, opcoes) {
    const chaves = new Set(((opcoes || {}).chaves || {})[cot.ramo] || []);
    const cfg = cot.configuracoes || (cot.configuracoes = {});
    if (ajuste.tipo === 'assistencia') {
      if (ajuste.seguradora != null) return 0;
      cfg.assist24hs = ajuste.valor; return 1;
    }
    if (ajuste.tipo === 'cobertura') {
      if (ajuste.seguradora != null || !ajuste.valor || typeof ajuste.valor !== 'object') return 0;
      let n = 0;
      // 🔴 conserto 129-C (juiz B2, D-129C-03): a Básica vem SÓ do pedido — o ajuste nunca a muda, nem se vier na lista
      for (const [k, v] of Object.entries(ajuste.valor)) if (chaves.has(k) && k !== CHAVE_DA_BASICA_RE) { cfg[k] = v; n++; }
      return n;
    }
    if (ajuste.tipo === 'comissao' || ajuste.tipo === 'desconto') {
      let n = 0;
      for (const it of cot.calculos || []) {
        if (ajuste.seguradora != null && it.seguradora !== ajuste.seguradora) continue;
        it[CAMPO_DO_AJUSTE_RE[ajuste.tipo]] = ajuste.valor; n++;
      }
      return n;
    }
    return 0;
  }

  // Recálculo a partir de UMA versão: as escolhas do app (DO_APP) vêm do item da MESMA seguradora na versão-base;
  // as credenciais vêm da config ATUAL (montarCalculos). Seguradora que não estava na base fica de fora.
  function montarDaVersao(segs, versao, opcoes) {
    if (versao && versao.ramo != null && versao.ramo !== RAMO_AUTO) return montarDaVersaoRE(segs, versao, opcoes);
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
  function aplicarAjuste(cotacao, ajuste, opcoes) {
    if (!ajuste) return 0;
    if (cotacao && cotacao.ramo != null && cotacao.ramo !== RAMO_AUTO) return aplicarAjusteRE(cotacao, ajuste, opcoes);
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
  // O COMBUSTÍVEL pela regra da TELA (SPEC-131-A F6). 📊 13/10, lido no bundle do app do Agger: a lista do campo
  // Combustível (`static combustivel=[{value,viewValue}]`, nesta ORDEM) e o `setaCombustivel` — o rótulo da FIPE do
  // modelo, sem acento e maiúsculo, escolhe a 1ª opção cujo rótulo o CONTÉM; rótulo vazio não escolhe nada.
  // CONTROLE: FLEX = 6 nos 18/18 corpos gravados. Espelho em `contrato.CODIGOS_MEDIDOS` (o teste do perfil confere).
  const COMBUSTIVEL = [['ALCOOL', 2], ['DIESEL', 3], ['ELETRICO', 5], ['FLEX', 6], ['GASOLINA', 1], ['HIBRIDO', 11],
                       ['TETRAFUEL', 10]];
  function codigoDoCombustivel(rotulo) {
    const r = String(rotulo == null ? '' : rotulo).normalize('NFD').replace(/\p{M}/gu, '').toUpperCase().trim();
    if (!r) return null;
    const achou = COMBUSTIVEL.find(([v]) => v.includes(r));
    return achou ? achou[1] : null;
  }
  function montarAutomovel(parcial, bp, fm) {
    const a = Object.assign({}, parcial);
    bp = bp || {};
    const m = (Array.isArray(fm) && fm[0]) || {};
    const vs = m.fipeValores || [];
    const ult = vs.reduce((acc, v) => Math.max(acc, v.anoVersaoTabela * 100 + v.mesVersaoTabela), 0);
    const atuais = vs.filter(v => v.anoVersaoTabela * 100 + v.mesVersaoTabela === ult);
    const esc = atuais.find(v => codigoDoCombustivel(v.combustivel) === a.combustivel) || atuais.find(v => v.combustivel === 'Flex') || atuais[0] || {};
    if (a.fabricante == null) a.fabricante = bp.codFabr;
    if (a.anoModelo == null) a.anoModelo = bp.anoMod != null ? Number(bp.anoMod) : null;
    if (a.anoFabricacao == null) a.anoFabricacao = Number(bp.anoFab || bp.anoMod) || a.anoModelo;
    if (!a.fipe) a.fipe = bp.fipe;
    if (!a.chassi) a.chassi = bp.chassi || null;
    if (!a.placa) a.placa = bp.placa || null;
    a.descricao = m.modelo || a.descricao || bp.modelo || null;
    a.valReferenciado = esc.valor != null ? esc.valor : (a.valReferenciado != null ? a.valReferenciado : null);
    if (a.combustivel == null) a.combustivel = codigoDoCombustivel(esc.combustivel);
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

  // 🔴 Conserto 129-B (red B3): a lista branca deixa passar TEXTO LIVRE (alertas, erros, observações) — e uma
  // seguradora que ecoa "usuario X senha Y" num alerta levava a senha ao banco. A credencial é conhecida AQUI (a
  // config `segs`, o corpo do POST, a resposta crua): toda string devolvida ao Python que CONTENHA um desses valores
  // vira '<redacted:credencial>'. Chave sensível = nome que casa RE_CHAVE_SECRETA; valor com 4+ caracteres.
  const RE_CHAVE_SECRETA = /senha|password|passwd|secret|token|login|usuario|apikey|api_key|codigocorretor|codcorretor|corretorcod|susep/i;
  const TRIVIAIS = new Set(['null', 'true', 'false', 'undefined', 'none']);
  const MARCA_CREDENCIAL = '<redacted:credencial>';
  function coletarSegredos(valor, acumulado) {
    const acc = new Set(acumulado || []);
    const anda = (v, k, prof) => {
      if (prof > 12) return;
      if (Array.isArray(v)) { for (const x of v) anda(x, k, prof + 1); return; }
      if (v && typeof v === 'object') { for (const [kk, x] of Object.entries(v)) anda(x, kk, prof + 1); return; }
      if (k && RE_CHAVE_SECRETA.test(k) && (typeof v === 'string' || typeof v === 'number')) {
        const s = String(v).trim();
        if (s.length >= 4 && !TRIVIAIS.has(s.toLowerCase())) acc.add(s);
      }
    };
    anda(valor, null, 0);
    return acc;
  }
  function redigirSegredos(valor, segredos) {
    const lista = [...(segredos || [])].filter(s => typeof s === 'string' && s.length >= 4);
    if (!lista.length) return valor;
    const anda = v => {
      if (Array.isArray(v)) return v.map(anda);
      if (v && typeof v === 'object') { const o = {}; for (const [k, x] of Object.entries(v)) o[k] = anda(x); return o; }
      if (typeof v === 'string' && lista.some(s => v.includes(s))) return MARCA_CREDENCIAL;
      return v;
    };
    return anda(valor);
  }

  window.__abM = {montarCalculos, montarDaVersao, aplicarAjuste, montarAutomovel, codigoDoCombustivel, filtrar, coletarSegredos,
                  redigirSegredos, DO_APP, montarCalculosRE, CAMPO_DO_AJUSTE_RE};
})();
