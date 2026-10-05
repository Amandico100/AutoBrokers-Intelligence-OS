# -*- coding: utf-8 -*-
"""Os tipos do cálculo multisseguradora — SPEC-128 U2 (D-MC-37).

🔴 O cálculo NÃO usa o nome em inglês no código (D-MC-37): é CÁLCULO, RODADA, OFERTA.

Todo tipo carrega `ramo`. 📊 31 = auto no Agger (`cotacao.ramo` do `calcularV2`
nas duas gravações de 18/09). A v1 implementa o AUTO; o residencial (E13) entra
como mapa quando for medido.

O que este módulo NUNCA carrega numa `Oferta`: login, senha, loginWs, senhaWs,
URL ou caminho de PDF. As CHAVES são conferidas por `CHAVES_PROIBIDAS_NA_OFERTA`; URL e
chave de API DENTRO de texto (mensagem, alerta, rótulo) o leitor troca por
`<removido:url>`/`<redacted:...>` (`redaction.sem_url_nem_chave`, conserto B1). A comissão vem em campo separado, `comissao_percentual`,
marcado INTERNO — nunca vai para o cliente (o adaptador da 129-B corta).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

RAMO_AUTO = 31

# --------------------------------------------------------------------------
# As famílias de resposta de uma seguradora (E10)
# --------------------------------------------------------------------------
OFERTA = "OFERTA"                # ao menos um item de `resultados[]` com prêmio > 0
CREDENCIAL = "CREDENCIAL"        # login/senha da corretora na seguradora
PERMISSAO = "PERMISSAO"          # o usuário existe mas não tem permissão
ACEITACAO = "ACEITACAO"          # a seguradora não aceita ESTE risco
COMERCIAL = "COMERCIAL"          # acordo comercial: a oferta não é dada ao parceiro
INSTABILIDADE = "INSTABILIDADE"  # a seguradora caiu; tentar de novo pode resolver
DADO = "DADO"                    # o PEDIDO precisa de correção: dado inválido, cobertura obrigatória que
                                 # faltou, ou "calcule como renovação" (📊 vivo 04/10 + gravacao_r2) — o
                                 # corretor/motor conserta e recalcula; não é recusa do risco
PENDENTE = "PENDENTE"            # ainda não respondeu nesta rodada
DESCONHECIDA = "DESCONHECIDA"    # respondeu, sem oferta, e nenhuma regra reconheceu

FAMILIAS: Tuple[str, ...] = (
    OFERTA, CREDENCIAL, PERMISSAO, ACEITACAO, COMERCIAL,
    INSTABILIDADE, DADO, PENDENTE, DESCONHECIDA,
)

# --------------------------------------------------------------------------
# Ajuste — o que o corretor muda e o motor recalcula
# --------------------------------------------------------------------------
TIPOS_DE_AJUSTE: Tuple[str, ...] = (
    "comissao", "desconto", "assistencia", "carro_reserva", "vidros",
    "franquia", "percentual_fipe", "cobertura",
)

# Chaves que uma Oferta NUNCA tem — o teste do contrato confere por máquina.
CHAVES_PROIBIDAS_NA_OFERTA: Tuple[str, ...] = (
    "login", "senha", "loginws", "senhaws", "pathpdf", "url", "pdf_url",
    "pdffilenameagger", "authorization", "token",
)


@dataclass(frozen=True)
class Ajuste:
    tipo: str
    valor: Any
    seguradora: Optional[int] = None  # None = vale para todas
    ramo: int = RAMO_AUTO

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_DE_AJUSTE:
            raise ValueError(f"tipo de ajuste desconhecido: {self.tipo!r}")


# --------------------------------------------------------------------------
# O pedido — os campos do `calcularV2` agrupados
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Campo:
    """Um campo do formulário. `obrigatorio=None` = a SPEC-128 ainda não mediu
    (F3 preenche com a E3: só os VALORES de `obrigatorio` mudam)."""
    nome: str
    caminho: str            # caminho no corpo do `calcularV2`
    obrigatorio: Optional[bool] = None
    valor: Any = None


# grupo → ((nome, caminho no calcularV2, obrigatorio), ...)
# 📊 caminhos lidos do `calcularV2` das gravações R1/R2 de 18/09 (fixtures
# `gravacao_r1.json`/`gravacao_r2.json`, chave `pedido.corpo`).
# `obrigatorio` MEDIDO na SPEC-128 E3 (📊 04/10 18:59, conta_a: "Calcular" com o formulário vazio → a tela recusou
# 15 campos, `e3_validacao.json` no rascunho do gerente; o 16º, tempo de habilitação, a tela só exige DEPOIS, no
# fluxo do condutor — observado, não contado no formulário vazio) · False = a tela aceitou vazio · None = não medido.
# Os 16 obrigatórios não dizem tudo: o questionário (garagem, uso, km) vem com PADRÕES da tela e o cálculo sai com eles.
CAMPOS_DO_PEDIDO_AUTO: dict = {
    "segurado": (
        ("tipo_pessoa", "cotacao.segurado.tipoPessoa", None),
        ("cpf_cnpj", "cotacao.segurado.cpfCnpj", True),
        ("nome", "cotacao.segurado.nome", True),
        ("nascimento", "cotacao.segurado.dataNasc", True),
        ("sexo", "cotacao.segurado.sexo", True),
        ("estado_civil", "cotacao.segurado.estadoCivil", True),
        ("cep", "cotacao.segurado.cep", True),
        ("telefone", "cotacao.segurado.fone1", False),
        ("email", "cotacao.segurado.email", False),
        ("pcd", "cotacao.segurado.isPCD", None),
    ),
    "veiculo": (
        ("fipe", "cotacao.automoveis[].fipe", True),
        ("modelo", "cotacao.automoveis[].descricao", None),
        ("fabricante", "cotacao.automoveis[].fabricante", None),
        ("ano_fabricacao", "cotacao.automoveis[].anoFabricacao", True),
        ("ano_modelo", "cotacao.automoveis[].anoModelo", None),
        ("combustivel", "cotacao.automoveis[].combustivel", True),
        ("placa", "cotacao.automoveis[].placa", False),
        ("chassi", "cotacao.automoveis[].chassi", False),
        ("zero_km", "cotacao.automoveis[].zeroKm", None),
        ("blindado", "cotacao.automoveis[].blindado", None),
        ("kit_gas", "cotacao.automoveis[].kitGas", None),
        ("alienado", "cotacao.automoveis[].alienado", None),
        ("uso", "cotacao.automoveis[].tpUso", None),
        ("percentual_fipe", "cotacao.automoveis[].pctAjuste", None),
    ),
    "pernoite": (
        ("cep_pernoite", "cotacao.automoveis[].cepPernoite", True),
        ("garagem_residencia", "cotacao.automoveis[].garagemResidencia", None),
        ("garagem_trabalho", "cotacao.automoveis[].garagemTrabalho", None),
        ("garagem_estudo", "cotacao.automoveis[].garagemEstudo", None),
    ),
    "condutor": (
        ("relacao_com_segurado", "cotacao.automoveis[].condutores[].relacComSegurado", None),
        ("cpf", "cotacao.automoveis[].condutores[].cpfCnpj", True),
        ("nome", "cotacao.automoveis[].condutores[].nome", True),
        ("nascimento", "cotacao.automoveis[].condutores[].dataNasc", True),
        ("sexo", "cotacao.automoveis[].condutores[].sexo", True),
        ("estado_civil", "cotacao.automoveis[].condutores[].estadoCivil", True),
        ("tempo_habilitacao", "cotacao.automoveis[].condutores[].tempoHabilitacao", True),
        ("jovem_condutor", "cotacao.automoveis[].jovemCondutor", None),
    ),
    "renovacao": (
        ("renovacao", "cotacao.renovacao", None),
        ("bonus_anterior", "cotacao.bonusAnterior", None),
        ("sinistros_anterior", "cotacao.sinistrosAnterior", None),
        ("numero_apolice_anterior", "cotacao.numeroRenovacao", None),
        ("seguradora_anterior", "cotacao.seguradoraAnteriorId", None),
        ("fim_vigencia_anterior", "cotacao.vigFimAnterior", None),
        ("vigencia_inicio", "cotacao.vigenciaIni", None),
        ("vigencia_fim", "cotacao.vigenciaFim", None),
    ),
    "coberturas": (
        ("tipo_cobertura", "cotacao.calculos[].tipoCobertura", None),
        ("tipo_franquia", "cotacao.calculos[].tipoFranquia", None),
        ("danos_materiais", "cotacao.calculos[].isDanosMateriais", None),
        ("danos_corporais", "cotacao.calculos[].isDanosCorporais", None),
        ("danos_morais", "cotacao.calculos[].isDanosMorais", None),
        ("app_morte", "cotacao.calculos[].isAppMorte", None),
        ("assistencia", "cotacao.calculos[].assist24hs", None),
        ("carro_reserva", "cotacao.calculos[].carroReserva", None),
        ("vidros", "cotacao.calculos[].vidros", None),
        ("valor_de_novo", "cotacao.calculos[].valorDeNovo", None),
    ),
    # 📊 o `calcularV2` das gravações NÃO traz campo de pacote: `packageType`
    # só aparece na RESPOSTA. O caminho do pedido é medido na E20 (F3).
    "pacotes": (
        ("tipo_de_pacote", "a medir (E20)", None),
    ),
    "comissao_desconto": (
        ("comissao_percentual", "cotacao.calculos[].percComissao", None),
        ("desconto_percentual", "cotacao.calculos[].percDesconto", None),
    ),
}


# --------------------------------------------------------------------------
# Os CÓDIGOS dos campos de lista do Agger — SPEC-129-B F4 (a costura porta × robô)
# --------------------------------------------------------------------------
# O robô (`agger_robo.cotacao_do_pedido`) manda CÓDIGO nos campos de lista; texto sem código medido o robô recusa
# só no disparo, lá na frente. A PORTA traduz com ESTA tabela e recusa o resto como `PedidoIncompleto` (nunca um
# disparo recusado depois de o pedido entrar na fila). 🔴 Só entra aqui texto→código MEDIDO (CLAUDE.md §9.5):
#   📊 sexo "M"/"F" ............ 18/18 corpos do `calcularV2` das fixtures (gravacao_r1/r2, vivo_conta_a/b)
#   📊 combustível Flex = 6 .... 18/18 corpos (e `montador.js` COMBUSTIVEL)
#   📊 relação "próprio" = 1 ... 17/18 condutores (o 18º, código 14, não tem rótulo medido)
# Estado civil (📊 códigos 1, 2 e 4 nas fixtures), uso, garagem, fabricante: o RÓTULO de cada código NÃO foi
# medido — só o código entra (P-129B-05: medir a lista de opções da tela e acrescentar aqui).
CODIGOS_MEDIDOS: dict = {
    ("segurado", "sexo"): {"m": "M", "masculino": "M", "f": "F", "feminino": "F"},
    ("condutor", "sexo"): {"m": "M", "masculino": "M", "f": "F", "feminino": "F"},
    ("segurado", "tipo_pessoa"): {"f": "F", "fisica": "F", "j": "J", "juridica": "J"},
    ("veiculo", "combustivel"): {"flex": 6},
    ("condutor", "relacao_com_segurado"): {"proprio": 1},
}
#: campos que o robô manda como NÚMERO inteiro (`agger_robo._int`): código de lista ou quantidade
CAMPOS_DE_CODIGO_INTEIRO: Tuple[Tuple[str, str], ...] = (
    ("segurado", "estado_civil"), ("condutor", "estado_civil"), ("condutor", "relacao_com_segurado"),
    ("condutor", "tempo_habilitacao"), ("veiculo", "fabricante"), ("veiculo", "ano_fabricacao"),
    ("veiculo", "ano_modelo"), ("veiculo", "combustivel"), ("veiculo", "uso"), ("veiculo", "percentual_fipe"),
    ("renovacao", "bonus_anterior"), ("renovacao", "sinistros_anterior"), ("questionario", "km_mensal"),
)
#: campos que o robô manda como TEXTO de dígitos (📊 `garagemResidencia: "2"` em 18/18 corpos)
CAMPOS_DE_CODIGO_TEXTO: Tuple[Tuple[str, str], ...] = (
    ("pernoite", "garagem_residencia"), ("pernoite", "garagem_trabalho"), ("pernoite", "garagem_estudo"),
)
#: campos sim/não (o robô faz `bool(valor)`: o texto "não" viraria VERDADEIRO — a porta converte ou recusa)
CAMPOS_SIM_NAO: Tuple[Tuple[str, str], ...] = (
    ("segurado", "pcd"), ("veiculo", "zero_km"), ("veiculo", "blindado"), ("veiculo", "kit_gas"),
    ("veiculo", "alienado"), ("condutor", "jovem_condutor"), ("renovacao", "renovacao"),
)

# A SEGURADORA ANTERIOR da renovação: o robô a acha em `calculo/seguradorasRenovacao` pelo NOME (o id é do Agger).
# A ficha da InfoCap dá o `coenti` (SUSEP, `susep_ses_provider.coenti_de`); esta tabela leva o coenti ao nome
# EXATO da lista do Agger. 📊 nomes: `gravacao_r1.json` `seguradoras_renovacao` (69 itens, 05/10); 📊 coenti:
# `mapa_de_seguradoras()` (15 chaves). Cada linha diz por que é a mesma empresa (§9.5).
# ⛔ Fora daqui (a porta recusa como `PedidoIncompleto`): SulAmérica (coenti UNKNOWN no mapa e DUAS entradas no
# Agger) · Unimed (`auto=false` no Agger).
SEGURADORA_ANTERIOR_NO_AGGER: dict = {
    "05177": "Allianz",                               # única Allianz da lista
    "05355": "Azul Companhia de Seguros Gerais",      # o MESMO nome da SUSEP (AZUL COMPANHIA DE SEGUROS GERAIS)
    "05312": "Bradesco Auto/RE Cia de Seg.",          # BRADESCO AUTO/RE COMPANHIA DE SEGUROS, abreviado
    "06572": "HDI",                                   # única HDI
    "06238": "Mapfre Vera Cruz Seguradora S/A",       # única Mapfre da lista
    "05886": "Porto Seguro Cia Seg. Gerais",          # PORTO SEGURO COMPANHIA DE SEGUROS GERAIS, abreviado
    "04952": "Suhai Seguradora",                      # única Suhai
    "06751": "Seguro Sura S.A.",                      # única Sura
    "06190": "Tokio Marine Seguradora S.A",           # TOKIO MARINE SEGURADORA S.A.
    "05185": "Yelum Seguradora",                      # YELUM SEGUROS S.A. (a ex-Liberty; única Yelum)
    "05495": "Zurich - Minas Brasil",                 # ZURICH MINAS BRASIL SEGUROS S.A.
    "06467": "Alfa Seguros e Previdência S.A.",       # única Alfa da lista
    "05720": "Sompo Seguros",                         # SOMPO SEGUROS S.A. (a outra, "Sompo Consumer", não)
}


@dataclass(frozen=True)
class PedidoDeCalculoAuto:
    ramo: int = RAMO_AUTO
    segurado: Tuple[Campo, ...] = ()
    veiculo: Tuple[Campo, ...] = ()
    pernoite: Tuple[Campo, ...] = ()
    condutor: Tuple[Campo, ...] = ()
    renovacao: Tuple[Campo, ...] = ()
    coberturas: Tuple[Campo, ...] = ()
    pacotes: Tuple[Campo, ...] = ()
    comissao_desconto: Tuple[Campo, ...] = ()
    seguradoras: Tuple[int, ...] = ()   # códigos das seguradoras pedidas


# --------------------------------------------------------------------------
# O resultado
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Parcelamento:
    parcelas: Optional[int]
    tipo_pagamento: Optional[int]
    primeira_parcela: Optional[float]
    demais_parcelas: Optional[float]


@dataclass(frozen=True)
class Oferta:
    seguradora: str
    seguradora_codigo: Optional[int]
    pacote: str                         # `resultados[].identificacao`
    tipo_de_pacote: Optional[int]       # `resultados[].packageType`
    premio_total: float
    premio_mensal: Optional[float]
    franquia_valor: Optional[float]
    franquia_tipo: Optional[str]
    coberturas: Tuple[Tuple[str, Any], ...] = ()   # só a lista branca
    parcelamentos: Tuple[Parcelamento, ...] = ()
    tem_pdf: bool = False
    numero_calculo_presente: bool = False
    alertas: Tuple[str, ...] = ()
    # 🔴 INTERNO: nunca vai para o cliente. O adaptador da 129-B corta.
    comissao_percentual: Optional[float] = field(default=None, metadata={"interno": True})
    ramo: int = RAMO_AUTO


@dataclass(frozen=True)
class RespostaDaSeguradora:
    seguradora: str
    seguradora_codigo: Optional[int]
    familia: str
    ofertas: Tuple[Oferta, ...] = ()
    mensagens: Tuple[str, ...] = ()
    credenciais_validas: Optional[bool] = None
    tempo_resposta_ms: Optional[int] = None
    ramo: int = RAMO_AUTO


@dataclass(frozen=True)
class RodadaDoCalculo:
    t_s: Optional[float]
    respostas: Tuple[RespostaDaSeguradora, ...]
    fechado: bool
    ramo: int = RAMO_AUTO

    @property
    def ofertas(self) -> Tuple[Oferta, ...]:
        return tuple(o for r in self.respostas for o in r.ofertas)

    def por_familia(self) -> dict:
        saida: dict = {}
        for r in self.respostas:
            saida[r.familia] = saida.get(r.familia, 0) + 1
        return saida


# --------------------------------------------------------------------------
# Evento — a narração ao vivo (D-MC-50) só pode nascer daqui
# --------------------------------------------------------------------------
NOVA_OFERTA = "nova_oferta"
# a MESMA oferta (seguradora, pacote, tipo de pacote) voltou com outro prêmio: a narração
# TROCA o preço, não soma uma oferta. 📊 0 casos nas 5 fixtures (04/10) — o tipo existe para
# que o caso, quando vier, não vire uma segunda "nova_oferta" do mesmo pacote.
OFERTA_ATUALIZADA = "oferta_atualizada"
SEGURADORA_RECUSOU = "seguradora_recusou"
CONJUNTO_FECHADO = "conjunto_fechado"   # UMA vez por cálculo (leitor_agger.eventos_do_calculo)


@dataclass(frozen=True)
class Evento:
    tipo: str
    t_s: Optional[float]
    seguradora: Optional[str] = None
    seguradora_codigo: Optional[int] = None
    familia: Optional[str] = None
    oferta: Optional[Oferta] = None
    ramo: int = RAMO_AUTO
