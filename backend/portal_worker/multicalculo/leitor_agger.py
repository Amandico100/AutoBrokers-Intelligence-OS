# -*- coding: utf-8 -*-
"""O leitor das respostas do Agger — SPEC-128 U2.

    ler_rodada(json)        → RodadaDoCalculo
    eventos_entre(a, b)     → [Evento]   (nova oferta · oferta atualizada · seguradora recusou · conjunto fechado)
    eventos_do_calculo(rs)  → [Evento]   (as rodadas em ordem de t_s, sem duplicar; conjunto fechado UMA vez)
    pedido_de_calcularv2(c) → PedidoDeCalculoAuto

A entrada é a resposta CRUA de `GET .../calculo/cotacao/calculos/{id}/{versao}`
(📊 hoje em `pdocs.aggilizador.com.br`; nas gravações de 18/09 em
`api.multicalculo.net`): uma LISTA, um item por seguradora consultada. As
fixtures saneadas têm a MESMA forma (um subconjunto das chaves), então o leitor
lê fixture e resposta ao vivo pelo mesmo caminho.

🔴 OFERTA = item de `resultados[]` com prêmio > 0. 📊 Na última rodada da R1 há
27 itens em `resultados` e 22 ofertas (BLOCO 0 #3): item ≠ oferta.

A LISTA BRANCA mora aqui porque ela é exatamente o que o leitor conhece do
Agger. O gerador de fixtures (`backend/scripts/agger_fixtures_saneadas.py`) e o
guarda G1 importam daqui — um lugar só.

🔴 TODA string que sai daqui (mensagem, alerta, observação, rótulo, nome) passa por
`redaction.sem_url_nem_chave`: 📊 04/10 uma seguradora devolveu, no texto do erro, a URL
interna com `?key=` e uma chave de API (conserto B1). O adaptador da 129-B recebe a
resposta CRUA — o leitor é a última porta antes dele.

Puro: sem rede, sem banco, sem `app.*`.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..redaction import sem_url_nem_chave
from .contrato import (
    ACEITACAO, CAMPOS_DO_PEDIDO_AUTO, COMERCIAL, CONJUNTO_FECHADO, CREDENCIAL,
    DADO, DESCONHECIDA, INSTABILIDADE, NOVA_OFERTA, OFERTA, OFERTA_ATUALIZADA,
    PENDENTE, PERMISSAO, RAMO_AUTO, SEGURADORA_RECUSOU, Campo, Evento, Oferta,
    Parcelamento, PedidoDeCalculoAuto, RespostaDaSeguradora, RodadaDoCalculo,
)

# ==========================================================================
# A LISTA BRANCA — por CAMINHO COMPLETO até a folha, por endpoint
# ==========================================================================
# Notação: `a.b` = chave dentro de objeto · `a[]` = item de lista.
# Caminho fora da lista = DESCARTADO pelo gerador e REPROVADO pelo G1.

# coberturas de um item de `resultados[]` que a Oferta carrega
COBERTURAS_DA_OFERTA: Tuple[str, ...] = (
    "tipo", "tipoPadronizado", "assist24hs", "carroReserva", "vidros", "casco",
    "isDanosMateriais", "isDanosCorporais", "isDanosMorais", "isAppMorte",
    "isAppInvalidez", "isBlindagemValor", "despesasExtra", "protecaoPneuRodas",
    "reparoRapido", "franquiaPadronizado", "franquiaPadronizadoPercentual",
    "tipoFranquia", "modeloSelecionado",
)

# um item por seguradora (rodada, `versoes[].calculos[]`, pedido `cotacao.calculos[]`)
ITEM_DA_SEGURADORA: Tuple[str, ...] = (
    "seguradora", "seguradoraTxt", "nomeSeguradora", "ativo",
    # `nome` = o nome COMERCIAL da seguradora no pedido (📊 vivo 04/10: "Yelum", "HDI", "Azul por
    # Assinatura" ao lado de nomeSeguradora "Liberty Site", "Hdi", "Azul Assinatura"). Não é pessoa:
    # o diferencial do gerador o acusou por ter sido DESCARTADO e reaparecer em texto de erro.
    "nome",
    "credenciaisValidas", "retorno", "retornoErro", "erros[]", "alertas[]",
    "premio", "premioMensal", "valorFranquia", "tipoFranquia", "tipoCobertura",
    "tempoResposta", "packageType", "selected",
    "percComissao", "percDesconto",                      # → valores CANÔNICOS
    "assist24hs", "carroReserva", "carroReservaAr", "vidros", "isDanosMateriais",
    "isDanosCorporais", "isDanosMorais", "isAppMorte", "isBlindagemValor",
    "valorDeNovo", "despesasExtra", "protecaoPneuRodas", "reparoRapido",
    "resultados[].premio", "resultados[].premioMensal", "resultados[].franquia",
    "resultados[].identificacao", "resultados[].packageType",
    "resultados[].principal", "resultados[].selected",
    "resultados[].renovacaoGarantida",
    "resultados[].nroCalculo",                           # → pseudônimo
    "resultados[].pathPdf", "resultados[].pdfFileNameAgger",  # → "<removido:pdf>"
    "resultados[].erros[]", "resultados[].alertas[]", "resultados[].observacoes[]",
    "resultados[].parcelamentos[].parcelas",
    "resultados[].parcelamentos[].tipoPag",
    "resultados[].parcelamentos[].premioPrimeiraParc",
    "resultados[].parcelamentos[].premioDemaisParc",
    "resultados[].parcelamentos[].valorIof",
    "resultados[].coberturas.percComissao",              # → CANÔNICO
    "resultados[].coberturas.percDesconto",              # → CANÔNICO
) + tuple(f"resultados[].coberturas.{c}" for c in COBERTURAS_DA_OFERTA)

# o objeto `cotacao` (pedido `calcularV2`, `versoes[]`, `negocio/{id}`)
COTACAO: Tuple[str, ...] = (
    "segurado.tipoPessoa", "segurado.cpfCnpj", "segurado.nome",
    "segurado.estadoCivil", "segurado.dataNasc", "segurado.sexo",
    "segurado.fone1", "segurado.email", "segurado.cep", "segurado.uf",
    "segurado.cidade", "segurado.bairro", "segurado.logradouro",
    "segurado.residLogradouro", "segurado.residNumero", "segurado.residBairro",
    "segurado.residCidade", "segurado.residUF", "segurado.isPCD",
    "automoveis[].descricao", "automoveis[].fabricante",
    "automoveis[].anoFabricacao", "automoveis[].anoModelo",
    "automoveis[].combustivel", "automoveis[].fipe", "automoveis[].fipeTxt",
    "automoveis[].chassi", "automoveis[].placa", "automoveis[].pctAjuste",
    "automoveis[].financiado", "automoveis[].cepCirculacao",
    "automoveis[].cepPernoite", "automoveis[].tpLocalPernoite",
    "automoveis[].kmAnual", "automoveis[].passageiros", "automoveis[].portas",
    "automoveis[].zeroKm", "automoveis[].jovemCondutor",
    "automoveis[].jovemIdade", "automoveis[].jovemSexo", "automoveis[].tpUso",
    "automoveis[].gasInstalValor", "automoveis[].tipoIsencao",
    "automoveis[].tipo", "automoveis[].blindado", "automoveis[].alienado",
    "automoveis[].kitGas", "automoveis[].rastreador", "automoveis[].antiFurto",
    "automoveis[].valReferenciado", "automoveis[].garagemResidencia",
    "automoveis[].garagemTrabalho", "automoveis[].garagemEstudo",
    "automoveis[].associado", "automoveis[].periodoUso",
    "automoveis[].condutores[].relacComSegurado",
    "automoveis[].condutores[].tpResidencia",
    "automoveis[].condutores[].dataPrimHabil",
    "automoveis[].condutores[].principal", "automoveis[].condutores[].cpfCnpj",
    "automoveis[].condutores[].nome", "automoveis[].condutores[].dataNasc",
    "automoveis[].condutores[].sexo", "automoveis[].condutores[].estadoCivil",
    "automoveis[].condutores[].tempoHabilitacao",
    "tipo", "integracaoInfo", "vigenciaIni", "vigenciaFim", "renovacao",
    "renovacaoGarantida", "bonusAnterior", "sinistrosAnterior",
    "numeroRenovacao", "seguradoraAnteriorId", "vigFimAnterior", "CI",
    "seguradoraSelectedId", "tpCobertura", "ramo", "negocioId", "versao",
    "tpFranquiaTxt", "tpCoberturaCalcTxt", "isAgger",
) + tuple(f"calculos[].{p}" for p in ITEM_DA_SEGURADORA)

# corpo de cada endpoint, relativo ao `corpo` do envelope da fixture
LISTA_BRANCA_POR_ENDPOINT: Dict[str, Tuple[str, ...]] = {
    "calcularV2": tuple(f"cotacao.{p}" for p in COTACAO) + ("negocio.id",),
    "calcularV2_resposta": ("idIntegracao", "versao"),
    "cotacao_calculos": tuple(f"[].{p}" for p in ITEM_DA_SEGURADORA),
    "cotacao_versoes": tuple(f"[].{p}" for p in COTACAO),
    "negocio": COTACAO,
    # busca/v2: SÓ contagens (derivadas pelo gerador)
    "negocio_busca_v2": ("qtd_linhas", "qtd_negocios", "por_ramo[].ramo",
                         "por_ramo[].qtd", "por_status[].status", "por_status[].qtd"),
    # config: seguradora, ativo e QUAIS campos de código existem (só os nomes)
    "cfg_seguradora_config": ("[].seguradora", "[].nomeSeguradora", "[].ativo",
                              "[].credenciaisValidas", "[].campos_de_codigo[]"),
    "seguradoras_renovacao": ("[].nome", "[].auto", "[].residencial",
                              "[].condominio", "[].empresarial", "[].aluguel",
                              "[].bike"),
    "fipe_modelo": ("[].modelo", "[].tipo", "[].fipeFabricante.nome",
                    "[].fipeValores[].anoVersaoTabela",
                    "[].fipeValores[].mesVersaoTabela",
                    "[].fipeValores[].valor", "[].fipeValores[].combustivel"),
}

# o envelope da fixture: seção → (endpoint do corpo, chaves do envelope)
SECOES_DA_FIXTURE: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "calculos[].pedido": ("calcularV2", ("t_s",)),
    "calculos[].resposta_pedido": ("calcularV2_resposta", ("t_s",)),
    "calculos[].rodadas[]": ("cotacao_calculos", ("t_s", "versao", "status")),
    "versoes[]": ("cotacao_versoes", ("t_s",)),
    "negocio[]": ("negocio", ("t_s",)),
    "busca_v2[]": ("negocio_busca_v2", ("t_s",)),
    "config[]": ("cfg_seguradora_config", ("t_s",)),
    "seguradoras_renovacao[]": ("seguradoras_renovacao", ("t_s",)),
    "fipe_modelo[]": ("fipe_modelo", ("t_s",)),
}
TOPO_DA_FIXTURE: Tuple[str, ...] = ("formato", "rotulo", "conta", "calculos[].id")


def _junta(prefixo: str, caminho: str) -> str:
    if not prefixo:
        return caminho
    if caminho.startswith("[]"):
        return prefixo + caminho
    return prefixo + "." + caminho


def lista_branca_do_arquivo() -> frozenset:
    """Todo caminho de folha permitido num arquivo de fixture do Agger."""
    caminhos = set(TOPO_DA_FIXTURE)
    for secao, (endpoint, envelope) in SECOES_DA_FIXTURE.items():
        for e in envelope:
            caminhos.add(_junta(secao, e))
        for p in LISTA_BRANCA_POR_ENDPOINT[endpoint]:
            caminhos.add(_junta(_junta(secao, "corpo"), p))
    return frozenset(caminhos)


def caminhos_de(valor: Any, prefixo: str = "") -> List[str]:
    """Todo caminho de folha (e de contêiner VAZIO, que não deixa folha)."""
    saida: List[str] = []
    if isinstance(valor, dict):
        if not valor and prefixo:
            saida.append(prefixo + "{}")
        for k, v in valor.items():
            saida.extend(caminhos_de(v, _junta(prefixo, str(k))))
    elif isinstance(valor, list):
        if not valor:
            saida.append(prefixo + "[]")
        for v in valor:
            saida.extend(caminhos_de(v, prefixo + "[]"))
    else:
        saida.append(prefixo)
    return saida


def caminho_permitido(caminho: str, lista: Iterable[str]) -> bool:
    lista = lista if isinstance(lista, (set, frozenset)) else frozenset(lista)
    if caminho in lista:
        return True
    if caminho.endswith("[]") or caminho.endswith("{}"):
        base = caminho[:-2]
        return any(w == base + "[]" or w.startswith(base + "[]") or
                   w.startswith(base + ".") for w in lista)
    return False


# ==========================================================================
# As famílias de resposta (E10) — cada regra cita a mensagem REAL
# ==========================================================================
def dobra(texto: str) -> str:
    """minúscula, sem acento, MESMO comprimento (posição a posição)."""
    saida = []
    for c in str(texto):
        d = unicodedata.normalize("NFKD", c)
        base = "".join(ch for ch in d if not unicodedata.combining(ch)).lower()
        saida.append(base[:1] if base else "?")
    return "".join(saida)


# (família, padrão sobre o texto DOBRADO, a fixture que a justifica)
REGRAS_DE_FAMILIA: Tuple[Tuple[str, "re.Pattern[str]", str], ...] = (
    # gravacao_r1/r2: "Login ou senha incorreta. Confira suas credenciais de acesso."
    (CREDENCIAL, re.compile(r"login ou senha incorret|confira suas credenciais|credenciais invalid"),
     "gravacao_r1 · gravacao_r2 (erros[])"),
    # gravacao_r1/r2: "Usuário não possui permissão a funcionalidade. Por favor, verifique suas permissões no site da seguradora."
    (PERMISSAO, re.compile(r"nao possui permiss|verifique suas permiss"),
     "gravacao_r1 · gravacao_r2 (erros[])"),
    # gravacao_r1/r2: "Oferta não disponibilizada ao Parceiro."
    (COMERCIAL, re.compile(r"nao disponibilizada ao parceiro"),
     "gravacao_r1 · gravacao_r2 (erros[])"),
    # vivo_conta_b (11×): "DESCONTO X COMISSÃO FORA DA ABRANGÊNCIA — O desconto aplicado não pode ser concedido…"
    (COMERCIAL, re.compile(r"desconto x comissao fora da abrangencia|desconto aplicado nao pode ser concedido"),
     "vivo_conta_b (erros[])"),
    # A COBERTURA pedida a corrigir (DADO) — duas formas, uma regra:
    #   vivo_conta_a (12×, ao lado de oferta): "COBERTURA CASCO FORA DO PERMITIDO"
    #   📊 ao vivo 05/10 (SPEC-129-B BLOCO 0, LAUDO-M0-M3 §M2, HDI nas duas contas, intermitente; AINDA NÃO está em
    #   fixture — pendência da 129-B): "Cobertura HDI Auto Vidros não pode ser contratada. Favor, recalcular".
    # 🔴 Vem ANTES das regras de INSTABILIDADE de propósito: 📊 o leitor dava INSTABILIDADE quando o texto dos vidros
    # chegava junto do "Read terminated" — e INSTABILIDADE convida a repetir o MESMO pedido, que falha de novo.
    (DADO, re.compile(r"cobertura \w+ fora do permitido|cobertura .{0,80}nao pode ser contratada"),
     "vivo_conta_a (erros[]) · LAUDO-M0-M3 §M2 (ao vivo 05/10, a 2ª forma)"),
    # gravacao_r1/r2: "A seguradora está apresentando instabilidade no momento. Por favor, tente novamente mais tarde."
    (INSTABILIDADE, re.compile(r"instabilidade|tente novamente mais tarde"),
     "gravacao_r1 · gravacao_r2 (erros[], rodadas intermediárias)"),
    # gravacao_r2 (versoes[], 8×): "Auto - Cotação indisponível, tente mais tarde realizando cópia da cotação e,
    # caso o problema persista, entre em contato…" — a regra de cima exige "tente NOVAMENTE mais tarde"
    (INSTABILIDADE, re.compile(r"cotacao indisponivel|tente mais tarde"),
     "gravacao_r2 (versoes[])"),
    # vivo_conta_b: "Erro ao executar servico: 105 - Read terminated …" · "… Erro ao inicializar planos …"
    (INSTABILIDADE, re.compile(r"read terminated|erro ao inicializar planos|erro ao executar servico"),
     "vivo_conta_b (erros[])"),
    # gravacao_r2: "O Código de Identificação informado para essa renovação é inválido." ·
    # vivo_conta_b (9×): "Apólice em período de renovação. Calcule como Renovação …" ·
    # vivo_conta_a: "CONTRATACAO DE DMO OBRIGATORIA" · "Favor contratar LMI RCF DM e LMI RCF DC …"
    (DADO, re.compile(r"codigo de identificacao informado para essa renovacao|calcule como renovacao|"
                      r"periodo de renovacao|contratacao de \w+ obrigatoria|favor contratar"),
     "gravacao_r2 · vivo_conta_a · vivo_conta_b (erros[])"),
    # gravacao_r2 (versoes[], 4×): "Os dados do condutor principal devem ser preenchidos." — falta dado no pedido
    (DADO, re.compile(r"dados do condutor principal devem ser preenchidos|devem ser preenchidos"),
     "gravacao_r2 (versoes[])"),
    # gravacao_r1/r2: "Não oferecemos seguro para os dados enviados no momento" ·
    # "O valor do veículo (R$ …) está abaixo do limite mínimo de R$ … aceito por esta seguradora." ·
    # "<produto> disponível apenas para pessoa física."
    (ACEITACAO, re.compile(r"nao oferecemos seguro|abaixo do limite minimo|acima do limite maximo|"
                           r"disponivel apenas para pessoa"),
     "gravacao_r1 · gravacao_r2 (erros[])"),
    # gravacao_r2 (versoes[], 4×): "A opção selecionada para vínculo do segurado do item 1 não possui aceitação para
    # este produto. Cote na <seguradora>…" — a seguradora não aceita este risco neste produto
    # 📊 ao vivo 05/10 (LAUDO-M0-M3 §M2, renovação, Aliro e Yelum nas duas contas): "Risco sem aceitação para este
    # cenário nesta seguradora" — antes DESCONHECIDA. MEDICOES E10 traz a mesma forma ("Veículo sem aceitação", Ezze).
    (ACEITACAO, re.compile(r"nao possui aceitacao|sem aceitacao"),
     "gravacao_r2 (versoes[]) · LAUDO-M0-M3 §M2 (ao vivo 05/10)"),
)
# A mensagem da renovação inválida (antes DESCONHECIDA) ganhou a família DADO — decisão do gerente
# (D-128-02, nota 85 × ACEITACAO 50: não é recusa do risco, é pedido a corrigir).


def classificar_mensagens(mensagens: Sequence[str]) -> Optional[str]:
    """A família da 1ª regra (em ordem de prioridade) que casa alguma mensagem."""
    dobradas = [dobra(m) for m in mensagens if isinstance(m, str) and m.strip()]
    for familia, padrao, _fonte in REGRAS_DE_FAMILIA:
        if any(padrao.search(m) for m in dobradas):
            return familia
    return None


# ==========================================================================
# Leitura
# ==========================================================================
_RE_DECIMAL = re.compile(r"-?\d+(?:\.\d+)?")
_RE_MILHAR_BR = re.compile(r"-?[1-9]\d{0,2}(?:\.\d{3})+")       # "1.234" · "1.234.567"
_RE_MILHAR_US = re.compile(r"-?[1-9]\d{0,2}(?:,\d{3}){2,}")       # "1,234,567"


def numero(valor: Any) -> Optional[float]:
    """prêmio/franquia → float FINITO, ou None. Nunca levanta.

        1234.56 · "1234.56" · "1.234,56" · "1,234.56" · "R$ 1.234,56" → 1234.56
        "1.234" (milhar BR) → 1234.0 · "0,00" → 0.0
        NaN · inf · 1e400 · "NaN" · "inf" · "1e400" · "abc" · "" · True · None → None
    O separador DECIMAL é o último que aparece; com um só tipo, vírgula é decimal (BR) e
    ponto seguido de grupos de exatamente 3 dígitos é MILHAR (BR)."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        try:
            f = float(valor)
        except (OverflowError, ValueError):
            return None
        return f if math.isfinite(f) else None
    if not isinstance(valor, str):
        return None
    s = valor.strip().replace("R$", "").replace(" ", "").replace("\u00a0", "")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")      # 1.234,56
        else:
            s = s.replace(",", "")                        # 1,234.56
    elif "," in s:
        s = s.replace(",", "") if _RE_MILHAR_US.fullmatch(s) else s.replace(",", ".")
    elif _RE_MILHAR_BR.fullmatch(s):
        s = s.replace(".", "")                            # 1.234 → 1234
    if not _RE_DECIMAL.fullmatch(s):                      # "abc" · "NaN" · "inf" · "1e400"
        return None
    f = float(s)
    return f if math.isfinite(f) else None


def _inteiro(valor: Any) -> Optional[int]:
    """Nunca levanta: `numero` só devolve finito."""
    n = numero(valor)
    return int(n) if n is not None else None


def _limpo(valor: Any) -> str:
    """Toda string que sai do leitor: sem URL nem chave (B1)."""
    return sem_url_nem_chave(valor)


def _textos(lista: Any) -> List[str]:
    if not isinstance(lista, list):
        return []
    return [_limpo(x) for x in lista if isinstance(x, str) and x.strip()]


def _oferta(item: Dict[str, Any], r: Dict[str, Any], ramo: int) -> Optional[Oferta]:
    premio = numero(r.get("premio"))
    if premio is None or premio <= 0:
        return None
    cob = r.get("coberturas") if isinstance(r.get("coberturas"), dict) else {}
    cob = {k: (_limpo(v) if isinstance(v, str) else v) for k, v in cob.items()}
    parcelas = []
    for p in r.get("parcelamentos") or []:
        if isinstance(p, dict):
            parcelas.append(Parcelamento(
                parcelas=_inteiro(p.get("parcelas")),
                tipo_pagamento=_inteiro(p.get("tipoPag")),
                primeira_parcela=numero(p.get("premioPrimeiraParc")),
                demais_parcelas=numero(p.get("premioDemaisParc")),
            ))
    return Oferta(
        seguradora=_limpo(item.get("seguradoraTxt") or item.get("nomeSeguradora") or ""),
        seguradora_codigo=_inteiro(item.get("seguradora")),
        pacote=_limpo(r.get("identificacao") or ""),
        tipo_de_pacote=_inteiro(r.get("packageType")),
        premio_total=premio,
        premio_mensal=numero(r.get("premioMensal")),
        franquia_valor=numero(r.get("franquia")),
        franquia_tipo=(str(cob.get("tipoFranquia")) if cob.get("tipoFranquia") is not None else None),
        coberturas=tuple((k, cob[k]) for k in COBERTURAS_DA_OFERTA if k in cob),
        parcelamentos=tuple(parcelas),
        tem_pdf=bool(r.get("pathPdf") or r.get("pdfFileNameAgger")),
        numero_calculo_presente=bool(r.get("nroCalculo")),
        alertas=tuple(_textos(r.get("alertas")) + _textos(r.get("observacoes"))),
        comissao_percentual=numero(cob.get("percComissao")),
        ramo=ramo,
    )


def ler_resposta(item: Dict[str, Any], ramo: int = RAMO_AUTO) -> RespostaDaSeguradora:
    resultados = item.get("resultados")
    resultados = [r for r in resultados if isinstance(r, dict)] if isinstance(resultados, list) else []
    ofertas = tuple(o for o in (_oferta(item, r, ramo) for r in resultados) if o is not None)
    mensagens = _textos(item.get("erros"))
    for r in resultados:
        mensagens += [m for m in _textos(r.get("erros")) if m not in mensagens]
    if ofertas:
        familia = OFERTA
    else:
        familia = classificar_mensagens(mensagens)
        if familia is None:
            if item.get("credenciaisValidas") is False:
                familia = CREDENCIAL
            elif item.get("retorno") is not True and not mensagens:
                # 📊 gravacao_r1/r2: nas rodadas iniciais as seguradoras que
                # ainda não responderam vêm com `retorno: false`.
                familia = PENDENTE
            else:
                familia = DESCONHECIDA
    return RespostaDaSeguradora(
        seguradora=_limpo(item.get("seguradoraTxt") or item.get("nomeSeguradora") or ""),
        seguradora_codigo=_inteiro(item.get("seguradora")),
        familia=familia,
        ofertas=ofertas,
        mensagens=tuple(mensagens),
        credenciais_validas=item.get("credenciaisValidas") if isinstance(item.get("credenciaisValidas"), bool) else None,
        tempo_resposta_ms=_inteiro(item.get("tempoResposta")),
        ramo=ramo,
    )


def ler_rodada(json: Any, *, t_s: Optional[float] = None, ramo: int = RAMO_AUTO) -> RodadaDoCalculo:
    """Aceita a resposta crua (lista), o envelope da fixture (`{"t_s", "corpo"}`)
    ou um objeto com `calculos` (uma versão). Lixo vira rodada vazia, nunca exceção."""
    corpo = json
    if isinstance(json, dict):
        if t_s is None and isinstance(json.get("t_s"), (int, float)) and not isinstance(json.get("t_s"), bool):
            t_s = numero(json["t_s"])                     # NaN/inf → None, nunca exceção
        if "corpo" in json:
            corpo = json.get("corpo")
        elif "calculos" in json:
            corpo = json.get("calculos")
        if isinstance(json.get("ramo"), int) and not isinstance(json.get("ramo"), bool):
            ramo = json["ramo"]
    itens = [i for i in corpo if isinstance(i, dict)] if isinstance(corpo, list) else []
    respostas = tuple(ler_resposta(i, ramo) for i in itens)
    fechado = bool(respostas) and all(r.familia != PENDENTE for r in respostas)
    return RodadaDoCalculo(t_s=t_s, respostas=respostas, fechado=fechado, ramo=ramo)


def _chave_seg(r: RespostaDaSeguradora) -> Any:
    return r.seguradora_codigo if r.seguradora_codigo is not None else r.seguradora


def _identidades(rodada: Optional[RodadaDoCalculo]) -> Dict[Tuple[Any, ...], Tuple[Oferta, Any]]:
    """Cada oferta da rodada pela IDENTIDADE (seguradora, pacote, tipo de pacote, ordem entre
    as iguais) → (oferta, prêmio arredondado). A ordem separa dois itens IGUAIS da mesma
    seguradora na mesma rodada (franquias diferentes): os dois são ofertas, não uma atualização."""
    saida: Dict[Tuple[Any, ...], Tuple[Oferta, Any]] = {}
    contagem: Dict[Tuple[Any, ...], int] = {}
    for o in (rodada.ofertas if rodada else ()):
        base = (o.seguradora_codigo if o.seguradora_codigo is not None else o.seguradora,
                o.pacote, o.tipo_de_pacote)
        n = contagem.get(base, 0)
        contagem[base] = n + 1
        saida[base + (n,)] = (o, round(o.premio_total, 2))
    return saida


def _familia_consolidada(respostas: Sequence[RespostaDaSeguradora]) -> str:
    """A família de UMA seguradora numa rodada, mesmo que ela venha em mais de um item
    (📊 E20: 31 itens; o motor pode mandar um item por pacote). Oferta em qualquer item
    vence; senão a 1ª família que não é PENDENTE/DESCONHECIDA; senão DESCONHECIDA; senão PENDENTE."""
    fams = [r.familia for r in respostas]
    if OFERTA in fams:
        return OFERTA
    for f in fams:
        if f not in (PENDENTE, DESCONHECIDA):
            return f
    return DESCONHECIDA if DESCONHECIDA in fams else PENDENTE


def _por_seguradora(rodada: Optional[RodadaDoCalculo]) -> Dict[Any, List[RespostaDaSeguradora]]:
    grupos: Dict[Any, List[RespostaDaSeguradora]] = {}
    for r in (rodada.respostas if rodada else ()):
        grupos.setdefault(_chave_seg(r), []).append(r)
    return grupos


def eventos_entre(anterior: Optional[RodadaDoCalculo], nova: RodadaDoCalculo) -> List[Evento]:
    """O que MUDOU de `anterior` para `nova`. Rodadas iguais → []. Rodada
    atrasada (t_s menor que o da anterior) → [] — não se narra o passado.

    · NOVA_OFERTA: uma identidade de oferta que a anterior não tinha.
    · OFERTA_ATUALIZADA: a MESMA identidade (seguradora, pacote, tipo) com prêmio diferente —
      o evento carrega a oferta NOVA; a narração troca o preço, não soma uma oferta.
    · SEGURADORA_RECUSOU: uma por seguradora, sobre a família CONSOLIDADA dos itens dela —
      seguradora com oferta em um item e erro em outro NÃO recusou.
    · CONJUNTO_FECHADO: a rodada fechou e a anterior não (UMA vez por cálculo:
      `eventos_do_calculo` garante)."""
    if (anterior is not None and anterior.t_s is not None and nova.t_s is not None
            and nova.t_s < anterior.t_s):
        return []
    antes = _identidades(anterior)
    agora = _identidades(nova)
    familia_antes = {k: _familia_consolidada(rs) for k, rs in _por_seguradora(anterior).items()}
    eventos: List[Evento] = []
    for k, rs in _por_seguradora(nova).items():
        primeiro = rs[0]
        for ident, (o, premio) in agora.items():
            if ident[0] != k:
                continue
            if ident not in antes:
                eventos.append(Evento(NOVA_OFERTA, nova.t_s, primeiro.seguradora, primeiro.seguradora_codigo,
                                      OFERTA, o, nova.ramo))
            elif antes[ident][1] != premio:
                eventos.append(Evento(OFERTA_ATUALIZADA, nova.t_s, primeiro.seguradora,
                                      primeiro.seguradora_codigo, OFERTA, o, nova.ramo))
        fam = _familia_consolidada(rs)
        if fam not in (OFERTA, PENDENTE) and familia_antes.get(k) != fam:
            eventos.append(Evento(SEGURADORA_RECUSOU, nova.t_s, primeiro.seguradora, primeiro.seguradora_codigo,
                                  fam, None, nova.ramo))
    if nova.fechado and not (anterior is not None and anterior.fechado):
        eventos.append(Evento(CONJUNTO_FECHADO, nova.t_s, ramo=nova.ramo))
    return eventos


def eventos_do_calculo(rodadas: Iterable[RodadaDoCalculo]) -> List[Evento]:
    """As rodadas em ordem de t_s (as sem t_s, na ordem dada, depois).

    🔴 CONJUNTO_FECHADO sai UMA vez por cálculo: o fechado é medido sobre as seguradoras
    PRESENTES na rodada; se uma seguradora aparece só depois (a rodada "reabre"), a chegada
    dela é narrada como NOVA_OFERTA/SEGURADORA_RECUSOU — o conjunto não "fecha de novo"."""
    lista = list(rodadas)
    ordenadas = sorted(
        (r for r in lista if r.t_s is not None), key=lambda r: r.t_s
    ) + [r for r in lista if r.t_s is None]
    eventos: List[Evento] = []
    anterior: Optional[RodadaDoCalculo] = None
    ja_fechou = False
    for r in ordenadas:
        for e in eventos_entre(anterior, r):
            if e.tipo == CONJUNTO_FECHADO:
                if ja_fechou:
                    continue
                ja_fechou = True
            eventos.append(e)
        anterior = r
    return eventos


# ==========================================================================
# O pedido
# ==========================================================================
def _valores_no_caminho(obj: Any, caminho: str) -> List[Any]:
    atuais = [obj]
    for parte in caminho.split("."):
        lista = parte.endswith("[]")
        chave = parte[:-2] if lista else parte
        prox = []
        for a in atuais:
            if not isinstance(a, dict) or chave not in a:
                continue
            v = a[chave]
            if lista:
                prox.extend(v if isinstance(v, list) else [])
            else:
                prox.append(v)
        atuais = prox
    return atuais


def pedido_de_calcularv2(corpo: Dict[str, Any]) -> PedidoDeCalculoAuto:
    """O corpo do `calcularV2` (cru ou da fixture) → PedidoDeCalculoAuto."""
    if isinstance(corpo, dict) and "corpo" in corpo and "cotacao" not in corpo:
        corpo = corpo.get("corpo") or {}
    corpo = corpo if isinstance(corpo, dict) else {}
    grupos: Dict[str, Tuple[Campo, ...]] = {}
    for grupo, campos in CAMPOS_DO_PEDIDO_AUTO.items():
        saida = []
        for nome, caminho, obrigatorio in campos:
            valores = _valores_no_caminho(corpo, caminho) if "." in caminho else []
            valor = valores[0] if len(valores) == 1 else (tuple(valores) if valores else None)
            saida.append(Campo(nome, caminho, obrigatorio, valor))
        grupos[grupo] = tuple(saida)
    cot = corpo.get("cotacao") if isinstance(corpo.get("cotacao"), dict) else {}
    ramo = cot.get("ramo") if isinstance(cot.get("ramo"), int) else RAMO_AUTO
    segs = tuple(
        s for s in (_inteiro(c.get("seguradora")) for c in (cot.get("calculos") or []) if isinstance(c, dict))
        if s is not None
    )
    return PedidoDeCalculoAuto(ramo=ramo, seguradoras=segs, **grupos)
