# -*- coding: utf-8 -*-
"""Os tipos do cálculo multisseguradora — SPEC-128 U2 (D-MC-37).

🔴 O cálculo NÃO usa o nome em inglês no código (D-MC-37): é CÁLCULO, RODADA, OFERTA.

Todo tipo carrega `ramo`. 📊 31 = auto no Agger (`cotacao.ramo` do `calcularV2`
nas duas gravações de 18/09). A v1 implementa o AUTO; o residencial (E13) entra
como mapa quando for medido.

O que este módulo NUNCA carrega numa `Oferta`: login, senha, loginWs, senhaWs,
URL ou caminho de PDF. A comissão vem em campo separado, `comissao_percentual`,
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
# 16 campos, `e3_validacao.json` no rascunho do gerente) · False = a tela aceitou vazio · None = não medido.
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
SEGURADORA_RECUSOU = "seguradora_recusou"
CONJUNTO_FECHADO = "conjunto_fechado"


@dataclass(frozen=True)
class Evento:
    tipo: str
    t_s: Optional[float]
    seguradora: Optional[str] = None
    seguradora_codigo: Optional[int] = None
    familia: Optional[str] = None
    oferta: Optional[Oferta] = None
    ramo: int = RAMO_AUTO
