# -*- coding: utf-8 -*-
"""O ROBÔ do Agger — SPEC-129-B U3 (interface §6.4).

    disparar(sessao, pedido, coberturas, negocio_ref=None) → Disparo      POST calcularV2 (negócio novo ou versão)
    acompanhar(sessao, disparo, ao_evento=..., anterior=...) → Rodada     GET calculos/{negocio}/{versao}
    recalcular(sessao, negocio_ref, versao_base=..., ajuste=...) → Disparo nova versão a partir da versão CERTA
    pessoa_mexeu_recentemente(sessao, negocio_ref, versoes_do_robo=...)   a regra D-MC-47 (§4.1)
    copiar_pdfs(sessao, disparo) → {(seguradora, pacote, tipo): bytes}     baixado DENTRO da página

🔴 D-129B-02: TODA leitura e montagem acontece DENTRO da página (`Sessao.avaliar`, montador.js). O que volta ao
Python já passou pela lista branca do endpoint em JS (`window.__abM.filtrar`) e é conferido DE NOVO aqui:
caminho fora da lista, marca de PDF trocada, URL/chave em texto (`redaction.tem_url_ou_chave`) ou chave proibida
(`contrato.CHAVES_PROIBIDAS_NA_OFERTA`) → o item é DESCARTADO e sai um evento `erro_de_leitura`.

O tempo (`t_s` das rodadas e eventos) = segundos desde `Disparo.t0` (época, `time.time()`): cresce entre
processos, então a rodada de uma retomada nunca é "atrasada" para o leitor.
⛔ Nada aqui loga pedido, corpo, token ou resposta. Exceções carregam só códigos e nomes de campo.
"""
from __future__ import annotations

import asyncio
import base64
import dataclasses
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Set, Tuple

from ..redaction import redigir_texto, sem_url_nem_chave, tem_url_ou_chave
from .atividade_empresarial import escolher_atividades, termos_de_busca
from .contrato import (
    CAMPO_DO_RAMO_NA_RENOVACAO, CAMPOS_DO_PEDIDO_RE, CHAVES_PROIBIDAS_NA_OFERTA, DADO, RAMO_AUTO, RAMO_CONDOMINIO,
    RAMO_EMPRESARIAL, RAMO_RESIDENCIAL, RAMOS_RE, SEGURADORAS_DO_RAMO, SEGURADORAS_FORA_DO_RE, SEM_ATIVIDADE_COMPATIVEL, Ajuste, Evento,
    MOTIVO_SEM_ATIVIDADE, SEM_ATIVIDADE, RodadaDoCalculo, chave_no_corpo, problemas_do_pedido_re, tipo_do_campo_re,
    FORA_POR_COMISSAO, FORA_POR_PROFISSAO, MOTIVO_DE_FORA_DA_VIDA, RAMO_VIDA, codigo_de_vida, problemas_do_pedido_vida,
)
from .leitor_agger import (
    LISTA_BRANCA_POR_ENDPOINT, caminho_permitido, caminhos_de, endpoint_de_calculos, eventos_entre, ler_resposta,
    ler_rodada,
)
from .presets import (CAPITAL_DA_VIDA, CHAVE_DA_BASICA, CHAVES_DE_COBERTURA, CHAVES_DE_COBERTURA_RE,
                      CHAVES_DO_AJUSTE_RE, configuracoes_de_vida)

logger = logging.getLogger("portal_worker.multicalculo")

# 🔴 A MARCA do robô (D-MC-47, §4.1): o negócio do Agger não tem observação/etiqueta (📊 0 em 24 leituras), mas o
# `correlationId` que o cliente gera volta GRAVADO na versão e no negócio (📊 15/15 na 128; 8/8 em 05/10). O robô
# gera todo correlationId com este prefixo — "pessoa mexeu" = versão SEM ele. Hex, para o id continuar com cara de
# UUID (o app manda UUID). ⚠️ Não é pesquisável (📊 busca/v2?textoBusca=ab0b → 0): serve para LER, não para achar.
PREFIXO_DA_MARCA = "ab0b"

ERRO_DE_LEITURA = "erro_de_leitura"
LISTA_CALCULOS = list(LISTA_BRANCA_POR_ENDPOINT["cotacao_calculos"])
LISTA_CALCULOS_RE = list(LISTA_BRANCA_POR_ENDPOINT["cotacao_calculos_re"])
LISTA_RESPOSTA = list(LISTA_BRANCA_POR_ENDPOINT["calcularV2_resposta"])
LISTA_ATIVIDADES = list(LISTA_BRANCA_POR_ENDPOINT["atividades_por_seguradora"])
LISTA_CALCULOS_VIDA = list(LISTA_BRANCA_POR_ENDPOINT["cotacao_calculos_vida"])
LISTA_PROFISSOES = list(LISTA_BRANCA_POR_ENDPOINT["profissoes_por_seguradora"])


def lista_de_calculos(ramo: int) -> List[str]:
    if ramo == RAMO_VIDA:
        return LISTA_CALCULOS_VIDA
    return LISTA_CALCULOS if ramo == RAMO_AUTO else LISTA_CALCULOS_RE
# O que a página troca por MARCA. As de PDF são conferidas à letra (a URL do PDF é segredo: leva assinatura/caminho
# do arquivo). O nº de cálculo da seguradora não é segredo — o JS o marca por economia; aqui só se exige que não
# traga URL/chave (as fixtures da 128 o trazem pseudonimizado, "<calculo#0009>").
MARCAS_PERMITIDAS = {"pathPdf": "<removido:pdf>", "pdfFileNameAgger": "<removido:pdf>"}
POST_TIMEOUT_S = 60
PDF_MAX_BYTES = 15 * 1024 * 1024
# 💭 10 leituras seguidas sem resposta válida (≈ 30 s com o intervalo de 3 s): um soluço de rede passa; uma sessão
# ou página morta para em 30 s, não nos 480 s do teto (conserto 129-B, juiz B1). 401/403 param NA HORA.
LEITURAS_FALHAS_MAX = 10
STATUS_SESSAO_MORTA = (401, 403)


_RE_ESPACOS = re.compile(r"\s+")

# Os códigos que a página devolve no preparo, em português de gente (o `erro` que a corretora lê pela porta).
MOTIVOS_LEGIVEIS = {
    "veiculo_sem_fipe_ou_ano": "o veículo não tem FIPE ou ano reconhecidos pelo Agger",
    "veiculo_sem_combustivel": "o combustível do veículo não veio e a FIPE do modelo não o diz ao Agger",
    "nenhuma_seguradora": "nenhuma seguradora ativa na conta do Agger para este cálculo",
    "seguradora_anterior_desconhecida": "a seguradora anterior da renovação não existe no Agger",
    "seguradora_anterior_ambigua": "a seguradora anterior da renovação casa com mais de uma no Agger",
    "versao_base_inexistente": "a versão de origem do recálculo não existe mais no Agger",
    "ajuste_sem_alvo": "o ajuste não tem seguradora onde ser aplicado",
    "sem_resposta": "a página do Agger não respondeu ao preparo",
    "sem_comissao": "o pedido de RE não trouxe a comissão (ela vai explícita em cada seguradora)",
    "sem_atividade_compativel": "nenhuma seguradora tem uma atividade que case sem dúvida com a do pedido",
    # o código vai NA FRENTE de propósito: a madrugada lê a cabeça "veiculo_…" como recusa DEFINITIVA (não recalcula
    # toda noite) — moto é SPEC própria (D-131-28)
    "veiculo_moto": "veiculo_moto — a placa é de uma moto e o formulário de carro do Agger não cota moto",
    # SPEC-129-D — o CÓDIGO vai NA FRENTE (como o da moto): a madrugada (V2) lê a cabeça e pergunta ao comercial
    # (`profissao_sem_casamento` → falta_dado `segurado.profissao_texto`); nenhum dos dois se resolve recalculando
    "profissao_sem_casamento": "profissao_sem_casamento — nenhuma seguradora de vida tem uma profissão igual à do pedido",
    "comissao_de_vida_nao_configurada": "comissao_de_vida_nao_configurada — a comissão de vida é 0 na conta do Agger "
                                        "e o pedido não trouxe outra",
    "profissao_busca_falhou": "profissao_busca_falhou — a busca de profissão do Agger não respondeu",
    "recalculo_de_vida": "o recálculo de vida não existe nesta versão",
}


def motivo_curto(texto: Any, limite: int = 160) -> str:
    """O motivo que pode ir ao banco: sem URL, sem chave, sem PII, numa linha, curto (conserto 129-B, juiz P4)."""
    s = redigir_texto(sem_url_nem_chave(texto))
    return _RE_ESPACOS.sub(" ", s).strip()[:limite]


class DisparoIncerto(Exception):
    """O POST PODE ter saído (timeout, rede, 5xx): nunca repetir."""


class DisparoRecusado(Exception):
    """Nada saiu, ou o servidor recusou com resposta clara. `.motivo` = texto CURTO e saneado (vai ao `erro`)."""

    sessao_morta = False
    # costura 129-C: no empresarial em que NENHUMA seguradora casou a atividade, quem saiu: ((código, nome), ...) — o
    # motor as grava como `SEM_ATIVIDADE_COMPATIVEL` antes de encerrar (nunca somem caladas)
    sem_atividade: Tuple[Tuple[int, str], ...] = ()
    # SPEC-129-D: na vida em que NENHUMA seguradora ficou, quem saiu e por quê: ((código, nome, "profissao"|"comissao"), …)
    fora_da_vida: Tuple[Tuple[int, str, str], ...] = ()

    def __init__(self, motivo: Any = "") -> None:
        self.motivo = motivo_curto(motivo)
        super().__init__(self.motivo)


class SessaoMorta(DisparoRecusado):
    """O Agger respondeu 401/403 ANTES de qualquer cálculo sair: a sessão do robô morreu (token vencido, alguém
    entrou com o login). Nada saiu — o motor DESCARTA a sessão e devolve o cálculo à fila (conserto 129-B, juiz B1)."""

    sessao_morta = True


class LeituraImpossivel(Exception):
    """O acompanhamento NÃO conseguiu ler o resultado (conserto 129-B, juiz B1): 401/403 (sessão morta), página
    fechada, ou `LEITURAS_FALHAS_MAX` leituras seguidas sem resposta válida, ou o teto sem NENHUMA leitura válida.
    `leu` = houve ao menos uma leitura 200 · `quadro_saiu` = o `ao_quadro` já foi chamado · `rodada` = a última lida."""

    def __init__(self, motivo: str, *, sessao_morta: bool = False, leu: bool = False, quadro_saiu: bool = False,
                 rodada: Optional[RodadaDoCalculo] = None, pagina_fechada: bool = False) -> None:
        self.motivo = motivo_curto(motivo)
        self.sessao_morta = bool(sessao_morta)
        # conserto 129-B: a PÁGINA fechou (o nosso navegador, não o Agger) — o motor deixa para a retomada
        self.pagina_fechada = bool(pagina_fechada)
        self.leu = bool(leu)
        self.quadro_saiu = bool(quadro_saiu)
        self.rodada = rodada
        super().__init__(self.motivo)


@dataclass(frozen=True)
class Disparo:
    negocio_ref: str
    versao: int
    t0: float
    # SPEC-129-C: o ramo do negócio (o leitor usa a lista branca e as famílias DO RAMO) e, no empresarial, as
    # seguradoras que SAÍRAM por não ter atividade compatível: ((código, nome), ...) — `acompanhar` as narra uma vez.
    # A retomada do motor reconstrói o Disparo com (negocio_ref, versao, t0) e, no RE, `ramo=` lido de
    # `multicalculo_pedidos.ramo` (costura 129-C, motor._trabalho); `sem_atividade` o motor já gravou no checkpoint.
    ramo: int = RAMO_AUTO
    sem_atividade: Tuple[Tuple[int, str], ...] = ()
    # SPEC-129-D: na vida, as seguradoras que SAÍRAM antes do POST — sem profissão igual, ou sem comissão de vida:
    # ((código, nome, "profissao"|"comissao"), …) — `acompanhar` as narra uma vez, com o motivo de cada uma.
    # ⚠️ Fora de `sem_atividade` de propósito: o motor grava aquela lista com o motivo da ATIVIDADE (motor._gravar_sem_atividade)
    fora_da_vida: Tuple[Tuple[int, str, str], ...] = ()


# ======================================================================================================================
# O pedido (dict decifrado pelo motor, `PedidoDeCalculo.para_dict()`) → a cotação, SEM credencial nenhuma
# ======================================================================================================================
def correlation_id() -> str:
    u = uuid.uuid4().hex
    return f"{PREFIXO_DA_MARCA}{u[4:8]}-{u[8:12]}-4{u[13:16]}-a{u[17:20]}-{u[20:32]}"


def _iso(d: Any) -> Optional[str]:
    """'AAAA-MM-DD' → '…T03:00:00.000Z' (📊 15/15 corpos da tela: meia-noite de Brasília em UTC)."""
    if d in (None, ""):
        return None
    s = str(d)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return f"{s}T03:00:00.000Z"
    return s


def _int(v: Any, campo: str) -> Optional[int]:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        raise DisparoRecusado(f"campo {campo}: código esperado")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    raise DisparoRecusado(f"campo {campo}: sem código medido para o valor recebido")


_SEXO = {"m": "M", "masculino": "M", "f": "F", "feminino": "F"}
# 📊 relacComSegurado = 1 em 15/15 corpos de condutor = o próprio segurado ("Próprio" é a 2ª opção da tela,
# índice 1). Os outros códigos não foram medidos: chegam como código ou o disparo é recusado ANTES do POST.
_RELACAO = {"proprio": 1, "próprio": 1}
# 📊 Os padrões do questionário que a TELA manda quando ninguém responde (15/15 corpos da 128).
PADROES_DO_QUESTIONARIO = {"kmAnual": 6000, "tpUso": 1, "garagemResidencia": "2", "garagemTrabalho": "0",
                           "garagemEstudo": "0", "rastreador": "0", "antiFurto": "0", "periodoUso": "0",
                           "pctAjuste": 100, "tpResidencia": 1}


def _cotacao_do_pedido_auto(pedido: Dict[str, Any], *, agora: Optional[datetime] = None) -> Dict[str, Any]:
    """PURA. O que a página completa depois: veículo (buscaPlaca/fipeModelo), endereço (cep), seguradora anterior
    (seguradorasRenovacao) e o `calculos[]` (config + coberturas). Levanta `DisparoRecusado` antes de qualquer rede."""
    seg = dict(pedido.get("segurado") or {})
    vei = dict(pedido.get("veiculo") or {})
    per = dict(pedido.get("pernoite") or {})
    con = dict(pedido.get("condutor") or {})
    ren = dict(pedido.get("renovacao") or {})
    que = dict(pedido.get("questionario") or {})
    faltam = [c for c, v in (("segurado.cpf_cnpj", seg.get("cpf_cnpj")), ("segurado.nome", seg.get("nome")),
                             ("segurado.cep", seg.get("cep"))) if not v]
    if not (vei.get("placa") or vei.get("fipe")):
        faltam.append("veiculo.placa|veiculo.fipe")
    if faltam:
        raise DisparoRecusado("pedido sem: " + ", ".join(faltam))
    doc = re.sub(r"\D", "", str(seg.get("cpf_cnpj")))
    sexo = _SEXO.get(str(seg.get("sexo") or "").strip().lower(), seg.get("sexo"))
    segurado = {
        "nome": seg.get("nome"), "tipoPessoa": seg.get("tipo_pessoa") or ("J" if len(doc) == 14 else "F"),
        "cpfCnpj": doc, "estadoCivil": _int(seg.get("estado_civil"), "segurado.estado_civil"),
        "dataNasc": _iso(seg.get("nascimento")), "sexo": sexo, "fone1": seg.get("telefone") or "",
        "cep": re.sub(r"\D", "", str(seg.get("cep"))), "email": seg.get("email") or "",
        "residLogradouro": None, "residNumero": None, "residBairro": None, "residCidade": None, "residUF": None,
        "isPCD": bool(seg.get("pcd")) if seg.get("pcd") is not None else False,
    }
    hoje = (agora or datetime.now(timezone.utc)).date()
    tempo = _int(con.get("tempo_habilitacao"), "condutor.tempo_habilitacao")
    prim = None
    if tempo is not None:
        try:
            prim = hoje.replace(year=hoje.year - tempo).isoformat()
        except ValueError:
            prim = hoje.replace(year=hoje.year - tempo, day=28).isoformat()
    relacao = con.get("relacao_com_segurado")
    relacao = _RELACAO.get(str(relacao).strip().lower(), relacao) if isinstance(relacao, str) else relacao
    condutor = {
        "relacComSegurado": _int(relacao, "condutor.relacao_com_segurado") or 1,
        "tpResidencia": PADROES_DO_QUESTIONARIO["tpResidencia"], "dataPrimHabil": _iso(prim), "principal": True,
        "cpfCnpj": re.sub(r"\D", "", str(con.get("cpf") or doc)), "nome": con.get("nome") or seg.get("nome"),
        "dataNasc": _iso(con.get("nascimento") or seg.get("nascimento")),
        "sexo": _SEXO.get(str(con.get("sexo") or "").strip().lower(), con.get("sexo") or sexo),
        "estadoCivil": _int(con.get("estado_civil", seg.get("estado_civil")), "condutor.estado_civil"),
        "tempoHabilitacao": tempo,
    }
    km = que.get("km_mensal")
    km_anual = (int(km) * 12) if isinstance(km, (int, float)) and not isinstance(km, bool) else None
    jovem = con.get("jovem_condutor")
    automovel = {
        "descricao": vei.get("modelo"), "fabricante": _int(vei.get("fabricante"), "veiculo.fabricante"),
        "anoFabricacao": _int(vei.get("ano_fabricacao"), "veiculo.ano_fabricacao"),
        "anoModelo": _int(vei.get("ano_modelo"), "veiculo.ano_modelo"),
        "combustivel": _int(vei.get("combustivel"), "veiculo.combustivel"),
        "fipe": (re.sub(r"\D", "", str(vei["fipe"])) or None) if vei.get("fipe") else None,
        "chassi": vei.get("chassi"), "placa": vei.get("placa"),
        "pctAjuste": _int(vei.get("percentual_fipe"), "veiculo.percentual_fipe") or PADROES_DO_QUESTIONARIO["pctAjuste"],
        "financiado": None, "cepCirculacao": None,
        "cepPernoite": re.sub(r"\D", "", str(per.get("cep_pernoite") or seg.get("cep"))),
        "tpLocalPernoite": None, "kmAnual": km_anual or PADROES_DO_QUESTIONARIO["kmAnual"], "passageiros": None,
        "portas": None, "jovemSexo": None, "zeroKm": bool(vei.get("zero_km")), "jovemCondutor": bool(jovem),
        "jovemIdade": None, "tpUso": _int(vei.get("uso"), "veiculo.uso") or PADROES_DO_QUESTIONARIO["tpUso"],
        "gasInstalValor": 0, "tipoIsencao": 0, "tipo": "v", "condutores": [condutor],
        "blindado": bool(vei.get("blindado")), "alienado": bool(vei.get("alienado")), "kitGas": bool(vei.get("kit_gas")),
        "rastreador": PADROES_DO_QUESTIONARIO["rastreador"], "antiFurto": PADROES_DO_QUESTIONARIO["antiFurto"],
        "valReferenciado": None,
        "garagemResidencia": str(per["garagem_residencia"]) if per.get("garagem_residencia") is not None else PADROES_DO_QUESTIONARIO["garagemResidencia"],
        "garagemTrabalho": str(per["garagem_trabalho"]) if per.get("garagem_trabalho") is not None else PADROES_DO_QUESTIONARIO["garagemTrabalho"],
        "garagemEstudo": str(per["garagem_estudo"]) if per.get("garagem_estudo") is not None else PADROES_DO_QUESTIONARIO["garagemEstudo"],
        "associado": False, "periodoUso": PADROES_DO_QUESTIONARIO["periodoUso"],
    }
    renovacao = ren.get("renovacao") is True
    agora_utc = (agora or datetime.now(timezone.utc)).replace(microsecond=0)
    vig_ini = _iso(ren.get("vigencia_inicio")) or agora_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    vig_fim = _iso(ren.get("vigencia_fim"))
    if not vig_fim:
        try:
            vig_fim = agora_utc.replace(year=agora_utc.year + 1).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            vig_fim = (agora_utc + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    cid = correlation_id()
    cot = {
        "segurado": segurado, "automoveis": [automovel],
        "results": {k: {"errors": [], "successes": []} for k in ("main", "alternatives", "all", "porAssinatura", "ofertaCruzada")},
        "loaded": False, "isClearDraft": False, "tipo": 5, "integracaoInfo": 1,
        "vigenciaIni": vig_ini, "vigenciaFim": vig_fim,
        "renovacao": renovacao, "renovacaoGarantida": False,
        "bonusAnterior": (_int(ren.get("bonus_anterior"), "renovacao.bonus_anterior") or 0) if renovacao else 0,
        "sinistrosAnterior": (_int(ren.get("sinistros_anterior"), "renovacao.sinistros_anterior") or 0) if renovacao else 0,
        "numeroRenovacao": (str(ren["numero_apolice_anterior"]) if renovacao and ren.get("numero_apolice_anterior") else None),
        "seguradoraAnteriorId": None,   # a página resolve pelo `seguradorasRenovacao` (o id é do Agger)
        "vigFimAnterior": _iso(ren.get("fim_vigencia_anterior")) if renovacao else None,
        "CI": None, "tpCobertura": 1, "ramo": RAMO_AUTO, "correlationId": cid,
    }
    if renovacao and not ren.get("seguradora_anterior"):
        raise DisparoRecusado("pedido sem: renovacao.seguradora_anterior")
    return {"cotacao": cot, "seguradora_anterior": str(ren.get("seguradora_anterior")) if renovacao else None,
            "seguradoras": [int(s) for s in (pedido.get("seguradoras") or [])],
            "comissao": (pedido.get("comissao_desconto") or {}).get("comissao_percentual"),
            "desconto": (pedido.get("comissao_desconto") or {}).get("desconto_percentual")}


def cotacao_do_pedido(pedido: Dict[str, Any], *, agora: Optional[datetime] = None,
                      coberturas: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """PURA. Despacha pelo ramo do pedido: o AUTO (31) é o de sempre (byte a byte); o RE (16 · 2 · 18) monta segurado
    + `configuracoes` (endereço do risco, o bem, as COBERTURAS) + vigência/renovação. Levanta `DisparoRecusado` antes de
    qualquer rede."""
    ramo = pedido.get("ramo", RAMO_AUTO) if isinstance(pedido, dict) else RAMO_AUTO
    if ramo in (None, RAMO_AUTO):
        return _cotacao_do_pedido_auto(pedido, agora=agora)
    if ramo == RAMO_VIDA:
        return _cotacao_do_pedido_vida(pedido, coberturas or {}, agora=agora)
    if ramo not in RAMOS_RE:
        raise DisparoRecusado(f"ramo {ramo} não implementado")
    return _cotacao_do_pedido_re(pedido, int(ramo), coberturas or {}, agora=agora)


# ----------------------------------------------------------------------------------------------------------------------
# SPEC-129-C — a montagem do RE. 🔴 A FORMA vem das gravações reais (tests/fixtures/agger_ramos/gravacao_<ramo>_1.json,
# `versao`): o molde de `configuracoes` de cada ramo é o corpo gravado com os VALORES neutralizados (as chaves e os
# padrões ficam; endereço, bem e coberturas vêm do pedido). As chaves `*Txt`/`*TxtRS` do empresarial gravado (rótulos de
# TELA, ex. "R$ 1.500.000,00") ficam fora: 💭 texto de exibição; o canário (F3) confirma que o Agger não as exige.
# ----------------------------------------------------------------------------------------------------------------------
_FUNERAL = {"tipo": 0, "valor": 0}
_MOLDE_CONFIGURACOES: Dict[int, Dict[str, Any]] = {
    # 📊 gravacao_condominio_1.versao.configuracoes (62 chaves — conserto 129-C: o texto dizia 65; padrões do app: sisProtecaoIncendRoubo [1], Vertical 1,
    # 1 bloco/1 pavimento como TEXTO, 0 elevador, valorDeNovo 1)
    RAMO_CONDOMINIO: {
        "imovelLogradouro": None, "imovelNumero": None, "imovelComplemento": "", "imovelBairro": None,
        "imovelCidade": None, "imovelUF": None, "imovelUso": None, "imovelCep": None, "imovelAlarme": None,
        "imovelTipoResidencia": None, "imovelConstrucao": None, "imovelOcupacao": None, "imovelObjetoSegurado": None,
        "imovelAtividadeProfissionalLocal": None, "imovelPossuiAlarme": None, "imovelPossuiVigilancia24hs": None,
        "responsabilidadeCivil": None, "isDanosMateriais": None, "despesaFixa": None, "fidelidade": None,
        "funeral": _FUNERAL, "sisProtecaoIncendRoubo": [1], "condPossuiAreaComercial": False, "imovelAtividade": 1,
        "anoFundacao": None, "estruturaCondominio": 1, "qtdElevadores": 0, "qtdBlocos": "1", "pavimentos": "1",
        "qtdFuncionarios": "", "areaConstruida": "", "imovelPatrimonioHistorico": False, "desmoronamento": False,
        "modalidade": None, "valorDeNovo": 1,
    },
    # 📊 gravacao_residencial_1.versao.configuracoes (51 chaves; padrões do app: Sólida 1, Casa 1, Habitual 1,
    # Prédio+Conteúdo 3, "segurado é o proprietário" marcado)
    RAMO_RESIDENCIAL: {
        "imovelLogradouro": None, "imovelNumero": None, "imovelComplemento": "", "imovelBairro": None,
        "imovelCidade": None, "imovelUF": None, "imovelUso": 1, "imovelCep": None, "imovelAlarme": None,
        "imovelTipoResidencia": 1, "imovelConstrucao": 1, "imovelOcupacao": 1, "imovelObjetoSegurado": 3,
        "imovelAtividadeProfissionalLocal": False, "imovelPossuiAlarme": False, "imovelPossuiVigilancia24hs": False,
        "rouboCondomino": None, "isDanosMateriais": 0, "despesaFixa": 0, "fidelidade": 0, "funeral": _FUNERAL,
        "sisProtecaoIncendRoubo": None, "imovelAtividade": False, "imovelPossuiGrades": False,
        "imovelPossuiCercaEletrica": False, "imovelPossuiAlarmeMonitorado": False,
        "imovelPossuiPorteiroEletronico": False, "imovelPossuiCircuitoFechado": False, "valorDeNovo": 1,
        "imovelPatrimonioHistorico": False, "seguradoProprietario": True, "areaRisco": False, "zonaRural": False,
    },
    # 📊 gravacao_empresarial_1.versao.configuracoes (sem os *Txt; padrões do app: Térreo "0", Outros "0", Sólida 1,
    # Prédio+Conteúdo 3, `isGuardaVeiculo` objeto)
    RAMO_EMPRESARIAL: {
        "imovelLogradouro": None, "imovelNumero": None, "imovelComplemento": "", "imovelBairro": None,
        "imovelCidade": None, "imovelUF": None, "imovelUso": False, "imovelCep": None, "imovelAlarme": None,
        "imovelConstrucao": 1, "imovelOcupacao": 1, "imovelObjetoSegurado": 3, "imovelPossuiAlarme": False,
        "imovelPossuiVigilancia24hs": False, "rouboCondomino": None, "isDanosMateriais": 0, "despesaFixa": 0,
        "funeral": _FUNERAL, "sisProtecaoIncendRoubo": None, "imovelLocalizacao": None, "imovelPossuiHidrante": False,
        "imovelPavimentacao": "0", "imovelLocalEstabelecimento": "0", "anoConstrucao": None,
        "imovelPossuiExtintor": False, "imovelPossuiSprinkler": False, "imovelPossuiBrigadaIncendio": False,
        "imovelPossuiDetectorFumaca": False, "imovelPossuiAlarmeMonitorado": False, "imovelPossuiCircuitoFechado": False,
        "imovelPossuiGradesEFechaduraTetra": False, "imovelPossuiSensorInfravermelho": False,
        "imovelUtilizadoDeposito": False, "imovelDivisaTerronoBaldio": False, "imovelPatrimonioHistorico": False,
        "imovelTelhaEstruturaMetalica": False, "imovelCaixaEletronico": False, "imovelPossuiIsopainel": False,
        "imovelConstrucaoReforma": False, "valorDeNovo": 1,
        "isGuardaVeiculo": {"franquia": None, "vagas": None, "valor": 0},
    },
}
# 📊 o `segurado` gravado: condomínio (gravacao_condominio_1) sem `fone`; residencial/empresarial com `fone` e sexo "M"
# (informacoesDefault {segurado:{sexo:"M"}}); estadoCivil 1 nos 3 (6/6 recentes).
_ESTATICOS_DO_RASCUNHO: Dict[int, Dict[str, Any]] = {
    # 📊 formulario_<ramo>.json `valores_fixos_do_corpo_no_js.valoresEstaticosDraft` + o topo das versões gravadas
    RAMO_CONDOMINIO: {"tipoSeguro": 1, "origem": 1, "integracaoID": None, "codigoInterno": None},
    RAMO_RESIDENCIAL: {"tipoSeguro": 1, "usuarioCriado": "", "usuarioCriadorNome": "", "origem": 1, "versaoAtual": 1,
                       "integracaoID": None, "corretora": {}, "calculosEnviados": 1, "calculosRecebidos": 0},
    RAMO_EMPRESARIAL: {"tipoSeguro": 1, "usuarioCriado": "", "usuarioCriadorNome": "", "origem": 1, "versaoAtual": 1,
                       "integracaoID": None, "corretora": {}, "calculosEnviados": 1, "calculosRecebidos": 0},
}


def _valor_do_risco(grupo: str, nome: str, v: Any) -> Any:
    tipo = tipo_do_campo_re(grupo, nome)
    if tipo == "digitos":
        return re.sub(r"\D", "", str(v))
    if nome in ("ano_fundacao", "blocos", "pavimentos", "area_construida", "funcionarios"):
        return str(v)                        # 📊 TEXTO no corpo gravado ("2005", "4", "5", "")
    if tipo == "inteiro":
        return _int(v, f"{grupo}.{nome}")
    if nome == "valor_de_novo":
        return 1 if v else 0                 # 📊 valorDeNovo Não 0 · Sim 1
    if tipo == "lista_de_codigos":
        return [int(x) for x in v]
    return v


def _cotacao_do_pedido_re(pedido: Dict[str, Any], ramo: int, coberturas: Dict[str, Any], *,
                          agora: Optional[datetime] = None) -> Dict[str, Any]:
    problemas = problemas_do_pedido_re(pedido)
    if problemas:
        raise DisparoRecusado("pedido sem: " + ", ".join(problemas))
    seg = dict(pedido.get("segurado") or {})
    risco = dict(pedido.get("risco") or {})
    ren = dict(pedido.get("renovacao") or {})
    com = dict(pedido.get("comissao_desconto") or {})
    doc = re.sub(r"\D", "", str(seg.get("cpf_cnpj")))
    segurado: Dict[str, Any] = {
        "nome": seg.get("nome"),
        # 📊 condomínio: o app FORÇA "J" (valoresEstaticosDraftSegurado); os outros pelo tamanho do documento
        "tipoPessoa": "J" if ramo == RAMO_CONDOMINIO else ("J" if len(doc) == 14 else "F"),
        "cpfCnpj": doc, "estadoCivil": _int(seg.get("estado_civil"), "segurado.estado_civil") or 1,
        "dataNasc": _iso(seg.get("nascimento")) if seg.get("nascimento") else None, "dataPrimHabil": None,
        "sexo": None if ramo == RAMO_CONDOMINIO else (_SEXO.get(str(seg.get("sexo") or "").strip().lower()) or "M"),
        "fone1": re.sub(r"\D", "", str(seg.get("telefone") or "")), "cep": None, "residLogradouro": None,
        "residNumero": None, "residBairro": None, "residCidade": None, "residUF": None,
        "email": seg.get("email") or "",
    }
    if ramo != RAMO_CONDOMINIO:
        segurado["fone"] = segurado["fone1"]
    cfg: Dict[str, Any] = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
                           for k, v in _MOLDE_CONFIGURACOES[ramo].items()}
    for k in CHAVES_DE_COBERTURA_RE[ramo]:
        cfg[k] = 0
    for k, v in (coberturas or {}).items():          # as da OPÇÃO (presets.coberturas_re, resolvidas pela porta)
        if k in CHAVES_DE_COBERTURA_RE[ramo]:
            cfg[k] = v
    for nome, _caminho, _obr in CAMPOS_DO_PEDIDO_RE[ramo]["risco"]:
        chave = chave_no_corpo(ramo, "risco", nome)
        if chave is None or risco.get(nome) in (None, ""):
            continue
        cfg[chave] = _valor_do_risco("risco", nome, risco[nome])
    for k, v in (risco.get("extras") or {}).items():  # o pedido VENCE a opção
        if k not in CHAVES_DE_COBERTURA_RE[ramo] or k == "assist24hs":
            raise DisparoRecusado(f"pedido sem: risco.extras.{k}:desconhecido")
        cfg[k] = v
    cfg[CHAVE_DA_BASICA] = risco["valor_basica"]     # 🔴 a Básica é SEMPRE a do pedido (D-129C-03)
    if ramo == RAMO_EMPRESARIAL:
        # 📊 "RC Operações": `responsabilidadeCivil` e `responsabilidadeCivilOperacoes` sempre iguais nos gravados — por
        # isso a que o PEDIDO não disse acompanha a que ele disse. 🔴 Conserto 129-C (red P5): o pedido que diz AS DUAS
        # leva cada uma com o seu valor (antes a RC sobrescrevia a RC Operações: 100 mil + 300 mil saíam 100 mil + 100 mil).
        extras = risco.get("extras") or {}
        rc, rcop = "responsabilidadeCivil", "responsabilidadeCivilOperacoes"
        if rc in extras and rcop not in extras:
            cfg[rcop] = cfg[rc]
        elif rcop in extras and rc not in extras:
            cfg[rc] = cfg[rcop]
        elif rc not in extras and rcop not in extras:
            cfg[rcop] = cfg.get(rc) or cfg.get(rcop) or 0
            cfg[rc] = cfg[rcop]
    renovacao = ren.get("renovacao") is True
    agora_utc = (agora or datetime.now(timezone.utc)).replace(microsecond=0)
    vig_ini = _iso(ren.get("vigencia_inicio")) or agora_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    vig_fim = _iso(ren.get("vigencia_fim"))
    if not vig_fim:
        try:
            vig_fim = agora_utc.replace(year=agora_utc.year + 1).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            vig_fim = (agora_utc + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    sin = _int(ren.get("sinistros_anterior"), "renovacao.sinistros_anterior") if renovacao else 0
    cot: Dict[str, Any] = {
        "segurado": segurado, "configuracoes": cfg,
        "results": {k: {"errors": [], "successes": []} for k in ("main", "alternatives", "all", "porAssinatura", "ofertaCruzada")},
        "loaded": False, "tipo": 5, "integracaoInfo": 1, "ramo": ramo, **_ESTATICOS_DO_RASCUNHO[ramo],
        "vigenciaIni": vig_ini, "vigenciaFim": vig_fim, "renovacao": renovacao,
        # 📊 bonusAnterior inteiro (5) na renovação, null fora dela; sinistrosAnterior TEXTO "0"/"1"
        # (📊 6/9 gravações em texto; as 3 migradas — *_3 — têm int 0: o Agger aceitou as duas formas; o robô manda texto)
        "bonusAnterior": (_int(ren.get("bonus_anterior"), "renovacao.bonus_anterior") or 0) if renovacao else None,
        "sinistrosAnterior": str(sin or 0),
        "numeroRenovacao": (str(ren["numero_apolice_anterior"]) if renovacao and ren.get("numero_apolice_anterior") else None),
        "seguradoraAnteriorId": None,   # a página resolve pelo `seguradorasRenovacao` (o id é do Agger)
        "vigFimAnterior": (_iso(ren.get("fim_vigencia_anterior")) or "") if renovacao else "",
        "correlationId": correlation_id(),
    }
    if ramo != RAMO_CONDOMINIO:
        cot["dataCriacao"] = agora_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"cotacao": cot, "seguradora_anterior": str(ren.get("seguradora_anterior")) if renovacao else None,
            "seguradoras": [int(s) for s in (pedido.get("seguradoras") or [])],
            "comissao": com.get("comissao_percentual"), "desconto": com.get("desconto_percentual"),
            "ramo": ramo, "atividade": risco.get("atividade"), "cnae": risco.get("cnae"),
            "pavimento": risco.get("pavimento")}


# ----------------------------------------------------------------------------------------------------------------------
# SPEC-129-D — a montagem da VIDA (91). 🔴 A FORMA é a do corpo GRAVADO ao vivo (📊 vida_calcularV2_corpo.json, BLOCO 0
# M6 16/10): a `cotacao` tem EXATAMENTE configuracoes · segurado · calculos · tipo · integracaoInfo · ramo · vigenciaIni ·
# correlationId (sem vigenciaFim, sem results/loaded); o `segurado` não leva profissão; fumante e esporte moram em
# `configuracoes`; a renda é NÚMERO no segurado.
# ----------------------------------------------------------------------------------------------------------------------
#: 📊 os restos de RE que a tela de vida manda NULOS em `configuracoes` (o corpo gravado tem os 4): vão iguais
_RESTOS_DE_RE_NA_VIDA = ("imovelCep", "imovelAlarme", "rouboCondomino", "sisProtecaoIncendRoubo")
#: 📊 "Pratica esportes radicais": 0 = "Não contratado" (o padrão da tela; o corpo gravado leva 0). 🔴 Os outros 49 são
#: ESPORTES (o `value` de cada um) — o pedido diz só sim/não: "sim" não tem código (o robô recusa; nunca um esporte por palpite)
ESPORTE_RADICAL_NAO = 0


def _numero_do_corpo(v: Any) -> Any:
    """R$ como o corpo gravado leva (📊 `rendaMensal 8000`: inteiro quando é inteiro)."""
    f = float(v)
    return int(f) if f.is_integer() else round(f, 2)


def _cotacao_do_pedido_vida(pedido: Dict[str, Any], coberturas: Dict[str, Any], *,
                            agora: Optional[datetime] = None) -> Dict[str, Any]:
    """PURA. A cotação de vida SEM credencial: a página completa o endereço (pelo CEP) e o `calculos[]` (config da conta
    + comissão + profissão por seguradora). Levanta `DisparoRecusado` antes de qualquer rede — com NOMES, nunca valores."""
    problemas = problemas_do_pedido_vida(pedido)
    if problemas:
        raise DisparoRecusado("pedido sem: " + ", ".join(problemas))
    seg = dict(pedido.get("segurado") or {})
    vida = dict(pedido.get("vida") or {})
    com = dict(pedido.get("comissao_desconto") or {})
    if vida["esporte_radical"] is not False:
        raise DisparoRecusado("pedido sem: vida.esporte_radical:qual_esporte — o Agger pede QUAL esporte radical")
    capital = vida["capital_morte"]
    cob = dict(coberturas or {})
    # 🔴 o capital é SEMPRE o do pedido (a porta já o força): uma opção com outro capital é recusada, nunca "corrigida"
    if cob.get(CAPITAL_DA_VIDA, capital) != capital:
        raise DisparoRecusado("coberturas: o capital da opção difere do capital do pedido")
    cob[CAPITAL_DA_VIDA] = capital
    try:
        coberturas_cfg = configuracoes_de_vida(cob)
    except ValueError as e:
        raise DisparoRecusado(f"coberturas: {e}") from None
    configuracoes: Dict[str, Any] = {k: None for k in _RESTOS_DE_RE_NA_VIDA}
    configuracoes["fumante"] = vida["fumante"]                       # 📊 bool (False no corpo gravado)
    configuracoes["praticaEsporteRadical"] = ESPORTE_RADICAL_NAO
    configuracoes.update(coberturas_cfg)
    segurado: Dict[str, Any] = {
        "nome": seg["nome"], "cpfCnpj": re.sub(r"\D", "", str(seg["cpf"])),
        "estadoCivil": codigo_de_vida("estado_civil", seg["estado_civil"]),   # 📊 NÚMERO (2 = Casado(a))
        "dataNasc": _iso(seg["data_nascimento"]),
        "sexo": codigo_de_vida("sexo", seg["sexo"]),                        # 📊 "M"/"F"
        "fone1": "", "cep": re.sub(r"\D", "", str(seg["cep"])), "email": "",
        # a página completa pelo CEP (`calculo/cep`), como a tela (📊 uf/cidade/bairro/logradouro "do CEP" no gravado)
        "uf": None, "cidade": None, "bairro": None, "logradouro": None,
        "fone": "", "altura": None, "peso": None,
        "rendaMensal": _numero_do_corpo(vida["renda_mensal"]),
    }
    cot: Dict[str, Any] = {
        "configuracoes": configuracoes, "segurado": segurado, "tipo": 5, "integracaoInfo": 1, "ramo": RAMO_VIDA,
        "vigenciaIni": _iso(vida["vigencia_inicio"]), "correlationId": correlation_id(),
    }
    return {"cotacao": cot, "seguradoras": [int(s) for s in (pedido.get("seguradoras") or [])],
            "comissao": com.get("comissao_percentual"), "agenciamento": com.get("agenciamento_percentual"),
            "ramo": RAMO_VIDA, "profissao": str(seg["profissao_texto"])}


# ======================================================================================================================
# O JavaScript (roda em `Sessao.avaliar`; `window.__abM` = montador.js)
# ======================================================================================================================
_JS_COMUM = """
  const M = window.__abM;
  const pegar = async (u, a) => { try { const r = await fetch(u, {headers: {Authorization: a}});
      const t = await r.text(); let d = null; try { d = JSON.parse(t) } catch (e) {} return [r.status, d]; }
    catch (e) { return [0, null]; } };
  const norm = s => String(s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
"""

# PREPARA o corpo (window.__abCorpo). Nada sai ainda. Devolve só o resumo (códigos de seguradora, contagem).
JS_PREPARAR = """async (a) => {""" + _JS_COMUM + """
  const [s1, segs] = await pegar(a.api + '/calculo/seguradoras', a.tApi);
  if (s1 !== 200 || !Array.isArray(segs)) return {erro: 'seguradoras_http_' + s1};
  window.__abSegredos = M.coletarSegredos(segs, window.__abSegredos);   // as credenciais: para REDIGIR o que volta
  const cot = a.cot;
  let negocio = null;
  let ids = null;
  if (a.negocio_ref) {
    const [sv, vs] = await pegar(a.pdocs + '/calculo/cotacao/versoes/' + encodeURIComponent(a.negocio_ref), a.tPdocs);
    if (sv !== 200 || !Array.isArray(vs) || !vs.length) return {erro: 'versoes_http_' + sv};
    let v = null;
    if (a.versao_base != null) v = vs.find(x => x && x.versao === a.versao_base);
    else v = vs.reduce((m, x) => (x && (!m || x.versao > m.versao)) ? x : m, null);
    if (!v) return {erro: 'versao_base_inexistente'};
    if (a.da_versao && v.ramo === 91) return {erro: 'recalculo_de_vida'};   // SPEC-129-D: não existe nesta versão
    if (a.da_versao) {           // RECÁLCULO: a cotação da versão-base (sem os campos do servidor)
      const FORA = new Set(['aplicacaoId', 'corretoraId', 'customerId', 'customerIp', 'customerName', 'dataCriacao',
        'createdAt', 'updatedAt', 'usuario', 'usuarioId', 'status', 'textoBusca', 'ofertasCruzadas', 'versaoAtual',
        'versaoOrigem', 'numeroRenovacaoTxt', 'vigenciaFimTxt', 'vigenciaIniTxt', 'isAgger', 'calculos', 'correlationId']);
      for (const k of Object.keys(cot)) if (!['results', 'loaded', 'isClearDraft', 'correlationId'].includes(k)) delete cot[k];
      for (const [k, x] of Object.entries(v)) if (!FORA.has(k)) cot[k] = x;
      cot.calculos = M.montarDaVersao(segs, v, {status: (a.status_por_ramo || {})[v.ramo], fora: a.fora_do_re});
    }
    cot.id = v.id; cot.negocioId = v.negocioId; cot.idIntegracao = v.idIntegracao; cot.versao = v.versao;
    negocio = {id: v.negocioId};
    // os 4 ids do negócio, como o Agger os deu para ESTE negocio_ref: a guarda só deixa o POST passar com eles
    ids = {ref: v.idIntegracao == null ? null : String(v.idIntegracao),
           negocio: v.negocioId == null ? null : String(v.negocioId), versao: v.id == null ? null : String(v.id)};
  }
  let semAtividade = [];
  let foraVida = [];
  if (!a.da_versao && a.ramo === 91) {
    // SPEC-129-D — VIDA: o CEP completa só o que falta do endereço do SEGURADO (📊 uf/cidade/bairro/logradouro no gravado)
    const sg = cot.segurado;
    if (sg.cep && (!sg.logradouro || !sg.cidade || !sg.bairro || !sg.uf)) {
      const [sc, ce] = await pegar(a.pdocs + '/calculo/cep?cep=' + encodeURIComponent(sg.cep), a.tPdocs);
      if (sc === 200 && ce) for (const k of ['uf', 'cidade', 'bairro', 'logradouro']) if (!sg[k] && ce[k] != null) sg[k] = ce[k];
    }
    const r = M.montarCalculosVida(segs, {status: a.status, fora: a.fora_do_re, comissao: a.comissao,
                                          agenciamento: a.agenciamento, profissoes: a.profissoes, comBloco: a.com_bloco});
    let calc = r.calculos, semP = r.semProfissao, semC = r.semComissao;
    if (a.seguradoras && a.seguradoras.length) {
      const so = x => a.seguradoras.includes(x[0]);
      calc = calc.filter(c => a.seguradoras.includes(c.seguradora)); semP = semP.filter(so); semC = semC.filter(so);
    }
    cot.calculos = calc;
    foraVida = semC.map(x => [x[0], x[1], 'comissao']).concat(semP.map(x => [x[0], x[1], 'profissao']));
    // a comissão é conferida ANTES da profissão: sobrou alguém com comissão e sem profissão → o que falta é a profissão
    if (!calc.length && (semP.length || semC.length))
      return {erro: semP.length ? 'profissao_sem_casamento' : 'comissao_de_vida_nao_configurada', fora_vida: foraVida};
  } else if (!a.da_versao && a.ramo && a.ramo !== 31) {
    // SPEC-129-C — RE: sem placa/FIPE; o CEP completa só o que o pedido não trouxe do ENDEREÇO DO RISCO
    const cfg = cot.configuracoes;
    if (cfg.imovelCep && (!cfg.imovelLogradouro || !cfg.imovelCidade || !cfg.imovelBairro || !cfg.imovelUF)) {
      const [sc, ce] = await pegar(a.pdocs + '/calculo/cep?cep=' + encodeURIComponent(cfg.imovelCep), a.tPdocs);
      const DE = {logradouro: 'imovelLogradouro', cidade: 'imovelCidade', bairro: 'imovelBairro', uf: 'imovelUF'};
      if (sc === 200 && ce) for (const [k, c] of Object.entries(DE)) if (!cfg[c] && ce[k] != null) cfg[c] = ce[k];
    }
    if (cot.renovacao) {
      const [sr, rs] = await pegar(a.pdocs + '/calculo/seguradorasRenovacao', a.tPdocs);
      if (sr !== 200 || !Array.isArray(rs)) return {erro: 'seguradoras_renovacao_http_' + sr};
      const alvo = norm(a.seguradora_anterior);
      let achou = rs.filter(x => x && String(x.id) === String(a.seguradora_anterior));
      if (!achou.length) achou = rs.filter(x => x && x[a.campo_renovacao] !== false && (norm(x.nome) === alvo || norm(x.nome).startsWith(alvo + ' ')));
      if (achou.length !== 1) return {erro: achou.length ? 'seguradora_anterior_ambigua' : 'seguradora_anterior_desconhecida'};
      cot.seguradoraAnteriorId = String(achou[0].id);
    }
    const r = M.montarCalculosRE(segs, a.ramo, a.comissao, a.desconto, {status: a.status, fora: a.fora_do_re,
                                                                        atividades: a.atividades});
    if (r.erro) return {erro: r.erro};
    let calc = r.calculos;
    semAtividade = r.semAtividade;
    if (a.seguradoras && a.seguradoras.length) {
      calc = calc.filter(c => a.seguradoras.includes(c.seguradora));
      semAtividade = semAtividade.filter(x => a.seguradoras.includes(x[0]));
    }
    cot.calculos = calc;
    if (!calc.length && semAtividade.length) return {erro: 'sem_atividade_compativel', sem_atividade: semAtividade};
  } else if (!a.da_versao) {
    const auto = cot.automoveis[0];
    let bp = null, fm = null;
    if (auto.placa) {
      const [sp, d] = await pegar(a.pdocs + '/calculo/buscaPlaca?placa=' + encodeURIComponent(auto.placa), a.tPdocs);
      if (sp === 200 && d && d.fipe) bp = d;
    }
    // SPEC-131-A conserto (juiz B2): o tipo que o PRÓPRIO Agger devolve pela placa — 📊 bundle do app:
    // tipoVeiculo={carro:"v",motocicleta:"m",caminhao:"c"}. Moto mandada no formulário de carro só volta recusa
    // ("NUM PORTAS INVALIDO PARA MOTOCICLETAS", 📊 16 seguradoras × 2 no canário de 13/10) — recusa ANTES de enviar.
    if (bp && /^m$/i.test(String(bp.tipoVeic || ''))) return {erro: 'veiculo_moto'};
    const fipe = auto.fipe || (bp && bp.fipe);
    const ano = auto.anoModelo || (bp && bp.anoMod);
    if (!fipe || !ano) return {erro: 'veiculo_sem_fipe_ou_ano'};
    const f = String(fipe); const fipeFmt = f.slice(0, f.length - 1) + '-' + f.slice(-1);
    const [sf, d2] = await pegar(a.pdocs + '/calculo/fipeModelo?ano=' + ano + '&fipe=' + fipeFmt + '&zero=' + (!!auto.zeroKm), a.tPdocs);
    if (sf !== 200 || !Array.isArray(d2) || !d2.length) return {erro: 'fipe_modelo_http_' + sf};
    fm = d2;
    cot.automoveis = [M.montarAutomovel(auto, bp, fm)];
    // SPEC-131-A F6: sem combustível (o pedido não trouxe e a FIPE não tem rótulo que a tela conheça) NADA sai — 📊 13/10
    // o calcularV2 sem ele voltou 64/64 "É necessário informar o tipo de combustível."
    if (cot.automoveis[0].combustivel == null) return {erro: 'veiculo_sem_combustivel'};
    const [sc, ce] = await pegar(a.pdocs + '/calculo/cep?cep=' + encodeURIComponent(cot.segurado.cep), a.tPdocs);
    if (sc === 200 && ce) for (const k of ['logradouro', 'cidade', 'bairro', 'uf']) if (ce[k] != null) cot.segurado[k] = ce[k];
    if (cot.renovacao) {
      const [sr, rs] = await pegar(a.pdocs + '/calculo/seguradorasRenovacao', a.tPdocs);
      if (sr !== 200 || !Array.isArray(rs)) return {erro: 'seguradoras_renovacao_http_' + sr};
      const alvo = norm(a.seguradora_anterior);
      let achou = rs.filter(x => x && String(x.id) === String(a.seguradora_anterior));
      if (!achou.length) achou = rs.filter(x => x && x.auto !== false && (norm(x.nome) === alvo || norm(x.nome).startsWith(alvo + ' ')));
      if (achou.length !== 1) return {erro: achou.length ? 'seguradora_anterior_ambigua' : 'seguradora_anterior_desconhecida'};
      cot.seguradoraAnteriorId = String(achou[0].id); cot.seguradoraSelectedId = String(achou[0].id);
    }
    let calc = M.montarCalculos(segs, a.cob, a.comissao, a.desconto);
    if (a.seguradoras && a.seguradoras.length) calc = calc.filter(c => a.seguradoras.includes(c.seguradora));
    cot.calculos = calc;
  }
  if (a.ajuste) { if (!M.aplicarAjuste(cot, a.ajuste, {chaves: a.chaves_re})) return {erro: 'ajuste_sem_alvo'}; }
  if (!cot.calculos || !cot.calculos.length) return {erro: 'nenhuma_seguradora'};
  window.__abCorpo = {cotacao: cot, negocio: negocio, correlationId: cot.correlationId};
  return {ok: true, seguradoras: cot.calculos.map(c => c.seguradora), ids: ids, ramo: cot.ramo == null ? 31 : cot.ramo,
          sem_atividade: semAtividade, fora_vida: foraVida};
}"""

# SPEC-129-D: a PROFISSÃO de vida, POR SEGURADORA — o MESMO endpoint que a tela chama na "Busca por profissão" (📊 BLOCO 0
# M6 16/10: `GET pdocs/calculo/getOptionsBySegFull?executionType=9&filterText=…`, 13 blocos `{seguradora, KeyValue[]}`).
# Só leitura; o que volta passa pela lista branca `profissoes_por_seguradora` (seguradora + Key/Value/Description).
JS_PROFISSOES = """async (a) => {""" + _JS_COMUM + """
  const [s, d] = await pegar(a.pdocs + '/calculo/getOptionsBySegFull?executionType=9&filterText=' + encodeURIComponent(a.termo), a.tPdocs);
  return [{termo: a.termo, status: s, opcoes: (s === 200 && Array.isArray(d)) ? M.filtrar(d, a.lista) : null}];
}"""

# SPEC-129-C D-129C-04: a atividade do empresarial, POR SEGURADORA — o MESMO endpoint que a tela chama no "Buscar por
# atividade" (📊 B0-a 11/10: `GET pdocs/calculo/getOptionsBySegFull?executionType=10&filterText=…`). Só leitura; o que
# volta passa pela lista branca `atividades_por_seguradora` (seguradora + Key/Value/Description).
JS_ATIVIDADES = """async (a) => {""" + _JS_COMUM + """
  const out = [];
  for (const termo of a.termos) {
    const [s, d] = await pegar(a.pdocs + '/calculo/getOptionsBySegFull?executionType=10&filterText=' + encodeURIComponent(termo), a.tPdocs);
    out.push({termo: termo, status: s, opcoes: (s === 200 && Array.isArray(d)) ? M.filtrar(d, a.lista) : null});
  }
  return out;
}"""

# ENVIA o corpo preparado. Devolve só o status e o que a lista branca de `calcularV2_resposta` deixa.
JS_ENVIAR = """async (a) => {
  const M = window.__abM; const corpo = window.__abCorpo; window.__abCorpo = null;
  if (!corpo) return {fase: 'antes', erro: 'sem_corpo'};
  let r;
  try {
    r = await fetch(a.api + '/calculo/calcularV2', {method: 'POST', body: JSON.stringify(corpo),
      headers: {Authorization: a.tApi, 'Content-Type': 'application/json', Accept: 'application/json, text/plain, */*'}});
  } catch (e) { return {fase: 'post', erro: 'rede'}; }
  const t = await r.text(); let d = null; try { d = JSON.parse(t) } catch (e) {}
  // as credenciais que ESTE corpo levou (e as da config): nenhuma volta ao Python, nem dentro de um texto
  const segredos = M.coletarSegredos(corpo, window.__abSegredos);
  let msg = null;
  if (r.status >= 400 && d && typeof d === 'object') {
    const m = d.message || d.mensagem || d.error;
    if (typeof m === 'string') msg = M.redigirSegredos(m.slice(0, 160), segredos);
  }
  return {fase: 'post', status: r.status,
          resposta: d && typeof d === 'object' ? M.redigirSegredos(M.filtrar(d, a.lista), segredos) : null, mensagem: msg};
}"""

# A leitura: lista branca do endpoint E, depois dela, toda string que CONTÉM uma credencial (da config ou da própria
# resposta crua) vira `<redacted:credencial>` — 📊 red team 05/10: uma seguradora que ecoa "usuario X senha Y" num
# alerta levava 13 alertas com a senha ao banco (conserto 129-B, red B3).
JS_LER_CALCULOS = """async (a) => {""" + _JS_COMUM + """
  const [s, d] = await pegar(a.pdocs + '/calculo/cotacao/calculos/' + encodeURIComponent(a.ref) + '/' + a.versao, a.tPdocs);
  if (s !== 200 || !Array.isArray(d)) return {status: s, corpo: null};
  const segredos = M.coletarSegredos(d, window.__abSegredos);
  return {status: s, corpo: M.redigirSegredos(M.filtrar(d, a.lista), segredos)};
}"""

JS_PESSOA_MEXEU = """async (a) => {""" + _JS_COMUM + """
  const [s, vs] = await pegar(a.pdocs + '/calculo/cotacao/versoes/' + encodeURIComponent(a.ref), a.tPdocs);
  if (s !== 200 || !Array.isArray(vs)) return {erro: 'versoes_http_' + s};
  const limite = Date.now() - a.horas * 3600 * 1000;
  const doRobo = new Set(a.versoes_do_robo);
  const marcada = v => String(v.correlationId || '').toLowerCase().startsWith(a.prefixo);
  let usuarios = new Set(vs.filter(v => v && doRobo.has(v.versao)).map(v => v.usuarioId).filter(x => x != null));
  if (!usuarios.size) usuarios = new Set(vs.filter(v => v && marcada(v)).map(v => v.usuarioId).filter(x => x != null));
  let recentes = 0, semMarca = 0, outroUsuario = 0;
  for (const v of vs) {
    if (!v) continue;
    const t = Date.parse(v.createdAt || v.dataCriacao || v.updatedAt || '');
    if (!isNaN(t) && t < limite) continue;      // sem data = conta como recente (na dúvida, a pessoa mexeu)
    recentes++;
    if (!marcada(v)) semMarca++;
    else if (a.conta_ativa && usuarios.size && !usuarios.has(v.usuarioId)) outroUsuario++;
  }
  return {recentes, semMarca, outroUsuario};
}"""

JS_PDFS = """async (a) => {""" + _JS_COMUM + """
  const [s, d] = await pegar(a.pdocs + '/calculo/cotacao/calculos/' + encodeURIComponent(a.ref) + '/' + a.versao, a.tPdocs);
  if (s !== 200 || !Array.isArray(d)) return {erro: 'calculos_http_' + s, pdfs: []};
  const out = []; let falhas = 0;
  // conserto 129-C (canário #7: 📊 6 de 6 PDFs de RE com `pathPdf` "não copiados", e 0 de 128 do auto com `pdf_path`):
  // o PORQUÊ de cada falha, por CLASSE — nunca a URL. http_<status> · rede (fetch lançou: CORS/rede) · nao_pdf · grande
  // · so_nome (a oferta só tem `pdfFileNameAgger`, sem `pathPdf`: nada para baixar).
  const motivos = {}; const conta = k => { motivos[k] = (motivos[k] || 0) + 1; };
  for (const it of d) {
    for (const r of (it && it.resultados) || []) {
      if (!r || !(Number(r.premio) > 0)) continue;
      if (!r.pathPdf) { if (r.pdfFileNameAgger) conta('so_nome'); continue; }
      try {
        const resp = await fetch(r.pathPdf);
        if (!resp.ok) { falhas++; conta('http_' + (Number(resp.status) || 0)); continue; }
        const buf = new Uint8Array(await resp.arrayBuffer());
        if (buf.length > a.max) { falhas++; conta('grande'); continue; }
        if (!(buf[0] === 0x25 && buf[1] === 0x50 && buf[2] === 0x44 && buf[3] === 0x46)) { falhas++; conta('nao_pdf'); continue; }
        let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
        out.push([it.seguradora, r.identificacao || '', r.packageType == null ? null : r.packageType, btoa(bin)]);
      } catch (e) { falhas++; conta('rede'); }
    }
  }
  return {pdfs: out, falhas, motivos};
}"""


# ======================================================================================================================
# A 2ª rede em Python
# ======================================================================================================================
def _limpo_da_lista(valor: Any, endpoint: str) -> bool:
    """Todo caminho do retorno está na lista branca do endpoint, e toda MARCA de PDF/nº de cálculo é a marca."""
    lista = frozenset(LISTA_BRANCA_POR_ENDPOINT[endpoint])
    if not all(caminho_permitido(c, lista) for c in caminhos_de(valor)):
        return False

    def anda(x: Any) -> bool:
        if isinstance(x, dict):
            for k, v in x.items():
                if str(k).lower() in CHAVES_PROIBIDAS_NA_OFERTA and k not in MARCAS_PERMITIDAS:
                    return False
                if k in MARCAS_PERMITIDAS and v not in (None, "", False, MARCAS_PERMITIDAS[k]):
                    return False
                if k == "nroCalculo" and tem_url_ou_chave(v):
                    return False
                if not anda(v):
                    return False
        elif isinstance(x, list):
            return all(anda(i) for i in x)
        return True
    return anda(valor)


def _textos_da_resposta(resp: Any) -> Iterable[str]:
    yield resp.seguradora
    yield from resp.mensagens
    for o in resp.ofertas:
        yield o.seguradora
        yield o.pacote
        yield o.franquia_tipo or ""
        yield from o.alertas
        for _, v in o.coberturas:
            if isinstance(v, str):
                yield v


def _oferta_sem_proibida(o: Any) -> bool:
    nomes = {f.name.lower() for f in dataclasses.fields(o)}
    return not (nomes & set(CHAVES_PROIBIDAS_NA_OFERTA)) and not any(
        str(k).lower() in CHAVES_PROIBIDAS_NA_OFERTA for k, _ in o.coberturas)


# O texto LIVRE de um item (o que a seguradora escreve): a 2ª rede o passa pelo redator de PII além do de URL/chave
# (conserto 129-B, red B3). Só estes caminhos: nome, pacote, códigos e prêmios são a IDENTIDADE da oferta e ficam.
_TEXTO_LIVRE_DO_ITEM = ("retornoErro", "erros", "alertas")
_TEXTO_LIVRE_DO_RESULTADO = ("erros", "alertas", "observacoes")


def _redigir_livre(valor: Any) -> Any:
    if isinstance(valor, str):
        return redigir_texto(sem_url_nem_chave(valor))
    if isinstance(valor, list):
        return [_redigir_livre(v) for v in valor]
    return valor


def _item_com_texto_livre_redigido(item: dict) -> dict:
    novo = dict(item)
    for k in _TEXTO_LIVRE_DO_ITEM:
        if k in novo:
            novo[k] = _redigir_livre(novo[k])
    if isinstance(novo.get("resultados"), list):
        res = []
        for r in novo["resultados"]:
            if isinstance(r, dict):
                r = dict(r)
                for k in _TEXTO_LIVRE_DO_RESULTADO:
                    if k in r:
                        r[k] = _redigir_livre(r[k])
            res.append(r)
        novo["resultados"] = res
    return novo


def separar_itens(corpo: Any, ramo: int = RAMO_AUTO) -> Tuple[List[dict], List[Tuple[Any, Optional[int]]]]:
    """(itens limpos, [(seguradora, código) descartados]). Pura — o G5 a usa com a mutação.
    O item limpo sai com o texto LIVRE (erros, alertas, observações) já redigido (PII, URL, chave)."""
    limpos: List[dict] = []
    sujos: List[Tuple[Any, Optional[int]]] = []
    for item in corpo if isinstance(corpo, list) else []:
        if not isinstance(item, dict):
            continue
        cod = item.get("seguradora") if isinstance(item.get("seguradora"), int) else None
        ok = _limpo_da_lista([item], endpoint_de_calculos(ramo))
        if ok:
            r = ler_resposta(item, ramo)
            ok = all(not tem_url_ou_chave(t) for t in _textos_da_resposta(r)) and all(
                _oferta_sem_proibida(o) for o in r.ofertas)
        if ok:
            limpos.append(_item_com_texto_livre_redigido(item))
        else:
            sujos.append((sem_url_nem_chave(item.get("seguradoraTxt") or item.get("nomeSeguradora") or ""), cod))
    return limpos, sujos


# ======================================================================================================================
# A interface §6.4
# ======================================================================================================================
def _args_base(sessao: Any) -> Dict[str, Any]:
    return {"api": sessao.bases["api"], "pdocs": sessao.bases["pdocs"], "tApi": sessao.token("api"),
            "tPdocs": sessao.token("pdocs")}


_RE_HTTP_MORTO = re.compile(r"_http_(401|403)$")


def _recusa_do_preparo(codigo: Any) -> DisparoRecusado:
    codigo = str(codigo or "sem_resposta")
    if _RE_HTTP_MORTO.search(codigo):
        return SessaoMorta(f"a sessão do robô no Agger caiu antes do cálculo ({codigo})")
    return DisparoRecusado(MOTIVOS_LEGIVEIS.get(codigo, f"preparo: {codigo}"))


def _sem_atividade_de(prep: Dict[str, Any]) -> Tuple[Tuple[int, str], ...]:
    """As seguradoras que saíram por atividade (o `[código, nome]` do JS), saneadas — nome sem URL nem chave."""
    fora = prep.get("sem_atividade") if isinstance(prep, dict) else None
    return tuple((int(x[0]), sem_url_nem_chave(x[1] or "")) for x in (fora or ())
                 if isinstance(x, (list, tuple)) and len(x) == 2 and isinstance(x[0], int) and not isinstance(x[0], bool))


def _fora_da_vida_de(prep: Dict[str, Any]) -> Tuple[Tuple[int, str, str], ...]:
    """SPEC-129-D: as seguradoras de vida que saíram antes do POST (o `[código, nome, por quê]` do JS), saneadas — nome
    sem URL nem chave, e o porquê só da lista fechada."""
    fora = prep.get("fora_vida") if isinstance(prep, dict) else None
    return tuple((int(x[0]), sem_url_nem_chave(x[1] or ""), str(x[2])) for x in (fora or ())
                 if isinstance(x, (list, tuple)) and len(x) == 3 and isinstance(x[0], int) and not isinstance(x[0], bool)
                 and x[2] in (FORA_POR_PROFISSAO, FORA_POR_COMISSAO))


async def _preparar_e_enviar(sessao: Any, args: Dict[str, Any]) -> Disparo:
    await sessao.garantir_token()
    try:
        prep = await sessao.avaliar(JS_PREPARAR, {**_args_base(sessao), **args})
    except Exception as e:  # noqa: BLE001 — nada saiu
        raise DisparoRecusado(f"preparo falhou ({type(e).__name__})") from None
    if not isinstance(prep, dict) or not prep.get("ok"):
        recusa = _recusa_do_preparo(prep.get("erro") if isinstance(prep, dict) else None)
        if isinstance(prep, dict) and prep.get("erro") == "sem_atividade_compativel":
            recusa.sem_atividade = _sem_atividade_de(prep)
        if isinstance(prep, dict) and prep.get("fora_vida"):
            recusa.fora_da_vida = _fora_da_vida_de(prep)
        raise recusa
    ids = prep.get("ids")
    pedido_ref = args.get("negocio_ref")
    if pedido_ref and isinstance(ids, dict) and ids.get("ref") is not None and str(ids["ref"]) == str(pedido_ref):
        # 🔴 a guarda passa a conhecer os 4 ids DESTE negócio (red P1/juiz P1): o POST só passa com eles coerentes
        registrar = getattr(sessao, "registrar_ids_do_negocio", None)
        if registrar is not None:
            registrar(str(pedido_ref), negocio_id=ids.get("negocio"), versao_id=ids.get("versao"))
    antes = sessao.contagem_de_escritas()["calcularV2"]
    t0 = time.time()
    try:
        r = await asyncio.wait_for(sessao.avaliar(JS_ENVIAR, {**_args_base(sessao), "lista": LISTA_RESPOSTA}),
                                   timeout=POST_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001
        if sessao.contagem_de_escritas()["calcularV2"] == antes and not isinstance(e, asyncio.TimeoutError):
            raise DisparoRecusado(f"o POST não saiu ({type(e).__name__})") from None
        raise DisparoIncerto(f"o POST pode ter saído ({type(e).__name__})") from None
    saiu = sessao.contagem_de_escritas()["calcularV2"] > antes
    if not isinstance(r, dict) or r.get("fase") != "post":
        raise DisparoRecusado("o corpo preparado sumiu")
    if r.get("erro") == "rede":
        if not saiu:
            raise DisparoRecusado("o POST foi barrado antes de sair (guarda)")
        raise DisparoIncerto("rede caiu durante o POST")
    status = int(r.get("status") or 0)
    resp = r.get("resposta")
    if 200 <= status < 300:
        if not (isinstance(resp, dict) and _limpo_da_lista(resp, "calcularV2_resposta")
                and resp.get("idIntegracao") and isinstance(resp.get("versao"), int)):
            raise DisparoIncerto(f"HTTP {status} sem idIntegracao/versão legíveis")
        ref = str(resp["idIntegracao"])
        sessao.registrar_negocio(ref)
        ramo = prep.get("ramo") if isinstance(prep.get("ramo"), int) and not isinstance(prep.get("ramo"), bool) else RAMO_AUTO
        return Disparo(negocio_ref=ref, versao=int(resp["versao"]), t0=t0, ramo=ramo,
                       sem_atividade=_sem_atividade_de(prep), fora_da_vida=_fora_da_vida_de(prep))
    if status in STATUS_SESSAO_MORTA:
        # 401/403 = o servidor não autenticou: nada foi criado, a sessão morreu
        raise SessaoMorta(f"a sessão do robô no Agger caiu (HTTP {status})")
    if 400 <= status < 500:
        msg = sem_url_nem_chave(r.get("mensagem") or "")
        raise DisparoRecusado(f"HTTP {status}" + (f": {msg}" if msg else ""))
    raise DisparoIncerto(f"HTTP {status}")


async def disparar(sessao: Any, pedido: Dict[str, Any], coberturas: Dict[str, Any], *,
                   negocio_ref: Optional[str] = None) -> Disparo:
    """Negócio NOVO (negocio_ref=None) ou nova VERSÃO do negócio do robô (a econômica, D-129B-03).
    RE (SPEC-129-C): as `coberturas` da opção vão em `cotacao.configuracoes` (montadas aqui, em Python — não têm
    credencial); no empresarial a atividade de CADA seguradora é lida na página antes do preparo (D-129C-04)."""
    ramo = pedido.get("ramo", RAMO_AUTO) if isinstance(pedido, dict) else RAMO_AUTO
    if ramo in RAMOS_RE:
        return await _disparar_re(sessao, pedido, coberturas, negocio_ref=negocio_ref)
    if ramo == RAMO_VIDA:
        return await _disparar_vida(sessao, pedido, coberturas, negocio_ref=negocio_ref)
    base = cotacao_do_pedido(pedido)
    cob = {k: v for k, v in (coberturas or {}).items() if k in CHAVES_DE_COBERTURA}
    # ⛔ NÃO registra `negocio_ref` aqui: a guarda só deixa a versão passar se o negócio JÁ é do robô (registrado
    # pelo disparo da padrão, ou por `Sessoes.obter(negocios_do_robo=...)` na retomada).
    return await _preparar_e_enviar(sessao, {
        "cot": base["cotacao"], "cob": cob, "comissao": base["comissao"], "desconto": base["desconto"],
        "seguradoras": base["seguradoras"], "seguradora_anterior": base["seguradora_anterior"],
        "negocio_ref": negocio_ref, "versao_base": None, "da_versao": False, "ajuste": None})


def _limpo_de_atividades(respostas: Any) -> bool:
    if not isinstance(respostas, list):
        return False
    return all(isinstance(r, dict) and (r.get("opcoes") is None or _limpo_da_lista(r.get("opcoes"),
                                                                                    "atividades_por_seguradora"))
               for r in respostas)


async def ler_atividades(sessao: Any, termos: Iterable[str]) -> List[dict]:
    """GET `getOptionsBySegFull` NA PÁGINA para cada termo; o que volta já passou pela lista branca (JS e Python)."""
    await sessao.garantir_token()
    try:
        r = await sessao.avaliar(JS_ATIVIDADES, {**_args_base(sessao), "termos": list(termos), "lista": LISTA_ATIVIDADES})
    except Exception as e:  # noqa: BLE001 — nada saiu (só leitura)
        raise DisparoRecusado(f"leitura das atividades falhou ({type(e).__name__})") from None
    if isinstance(r, list) and any(isinstance(x, dict) and x.get("status") in STATUS_SESSAO_MORTA for x in r):
        raise SessaoMorta("a sessão do robô no Agger caiu antes do cálculo (atividades)")
    if not _limpo_de_atividades(r):
        raise DisparoRecusado("a lista de atividades do Agger voltou fora da forma esperada")
    return r


async def _disparar_re(sessao: Any, pedido: Dict[str, Any], coberturas: Dict[str, Any], *,
                       negocio_ref: Optional[str]) -> Disparo:
    base = cotacao_do_pedido(pedido, coberturas={k: v for k, v in (coberturas or {}).items()
                                                 if k in CHAVES_DE_COBERTURA_RE[int(pedido["ramo"])]})
    ramo = base["ramo"]
    atividades: Dict[str, dict] = {}
    if ramo == RAMO_EMPRESARIAL:
        respostas = await ler_atividades(sessao, termos_de_busca(base["atividade"], base["cnae"]))
        escolhidas, _fora = escolher_atividades(respostas, base["atividade"], cnae=base["cnae"],
                                                pavimento=base["pavimento"])
        atividades = {str(k): v for k, v in escolhidas.items()}
    return await _preparar_e_enviar(sessao, {
        "cot": base["cotacao"], "cob": {}, "comissao": base["comissao"], "desconto": base["desconto"],
        "seguradoras": base["seguradoras"], "seguradora_anterior": base["seguradora_anterior"],
        "negocio_ref": negocio_ref, "versao_base": None, "da_versao": False, "ajuste": None,
        "ramo": ramo, "status": list(SEGURADORAS_DO_RAMO[ramo]), "fora_do_re": list(SEGURADORAS_FORA_DO_RE),
        "atividades": atividades, "campo_renovacao": CAMPO_DO_RAMO_NA_RENOVACAO[ramo]})


# ----------------------------------------------------------------------------------------------------------------------
# SPEC-129-D — a PROFISSÃO de vida por seguradora e o disparo de vida
# ----------------------------------------------------------------------------------------------------------------------
def normalizar_profissao(texto: Any) -> str:
    """Sem acento, minúsculas, espaços colapsados — a ÚNICA transformação antes da igualdade."""
    import unicodedata

    s = "".join(c for c in unicodedata.normalize("NFKD", str(texto or "")) if not unicodedata.combining(c))
    return _RE_ESPACOS.sub(" ", s.lower()).strip()


def escolher_profissoes(respostas: Any, texto: Any) -> Tuple[Dict[int, dict], List[int], List[int]]:
    """(escolhidas {seguradora: {Key, Value, Description}}, seguradoras COM bloco na busca, ambíguas).

    🔴 Só vale a IGUALDADE do texto normalizado (D-129D-06 revista pelo ao vivo): 📊 16/10, a busca por "Analista de
    sistemas" devolveu UMA opção em Allianz, Tokio, Yelum e Zurich — e era OUTRA profissão ("Analista de sistemas de
    automação"). "Única opção" não é "mesma profissão": declarar a profissão errada à seguradora é declaração inexata.
    Duas opções IGUAIS com códigos diferentes no mesmo bloco → ambígua, nenhuma escolhida. Seguradora com bloco e sem
    opção igual SAI (o montador a lista); seguradora SEM bloco (📊 Bradesco) não pede profissão."""
    alvo = normalizar_profissao(texto)
    escolhidas: Dict[int, dict] = {}
    com_bloco: List[int] = []
    ambiguas: List[int] = []
    for resp in respostas if isinstance(respostas, list) else []:
        if not isinstance(resp, dict) or resp.get("status") != 200 or not isinstance(resp.get("opcoes"), list):
            continue
        for bloco in resp["opcoes"]:
            cod = bloco.get("seguradora") if isinstance(bloco, dict) else None
            if not isinstance(cod, int) or isinstance(cod, bool):
                continue
            if cod not in com_bloco:
                com_bloco.append(cod)
            iguais: Dict[str, dict] = {}
            for kv in bloco.get("KeyValue") or []:
                if isinstance(kv, dict) and kv.get("Key") not in (None, "") and alvo \
                        and normalizar_profissao(kv.get("Value")) == alvo:
                    iguais[str(kv["Key"])] = {"Key": str(kv["Key"]), "Value": kv.get("Value"),
                                             "Description": kv.get("Description")}
            if len(iguais) == 1:
                escolhidas[cod] = next(iter(iguais.values()))
            elif len(iguais) > 1 and cod not in ambiguas:
                ambiguas.append(cod)
    return escolhidas, com_bloco, ambiguas


def _limpo_de_profissoes(respostas: Any) -> bool:
    if not isinstance(respostas, list):
        return False
    return all(isinstance(r, dict) and (r.get("opcoes") is None or _limpo_da_lista(r.get("opcoes"),
                                                                                    "profissoes_por_seguradora"))
               for r in respostas)


async def ler_profissoes(sessao: Any, termo: str) -> List[dict]:
    """GET `getOptionsBySegFull?executionType=9` NA PÁGINA; o que volta já passou pela lista branca (JS e Python).
    🔴 Sem UMA resposta 200 legível, nada sai: sem saber quem pede profissão, o robô mandaria seguradora sem ela."""
    await sessao.garantir_token()
    try:
        r = await sessao.avaliar(JS_PROFISSOES, {**_args_base(sessao), "termo": str(termo), "lista": LISTA_PROFISSOES})
    except Exception as e:  # noqa: BLE001 — nada saiu (só leitura)
        raise DisparoRecusado(f"{MOTIVOS_LEGIVEIS['profissao_busca_falhou']} ({type(e).__name__})") from None
    if isinstance(r, list) and any(isinstance(x, dict) and x.get("status") in STATUS_SESSAO_MORTA for x in r):
        raise SessaoMorta("a sessão do robô no Agger caiu antes do cálculo (profissão)")
    if not _limpo_de_profissoes(r):
        raise DisparoRecusado("a lista de profissões do Agger voltou fora da forma esperada")
    if not any(isinstance(x, dict) and x.get("status") == 200 and isinstance(x.get("opcoes"), list) for x in r):
        raise DisparoRecusado(MOTIVOS_LEGIVEIS["profissao_busca_falhou"])
    return r


async def _disparar_vida(sessao: Any, pedido: Dict[str, Any], coberturas: Dict[str, Any], *,
                         negocio_ref: Optional[str]) -> Disparo:
    base = cotacao_do_pedido(pedido, coberturas=coberturas or {})
    # 📊 a tela só busca com 3+ letras ("texto ≥ 3"): menos que isso não tem casamento possível
    if len(normalizar_profissao(base["profissao"])) < 3:
        raise DisparoRecusado(MOTIVOS_LEGIVEIS["profissao_sem_casamento"])
    respostas = await ler_profissoes(sessao, base["profissao"])
    escolhidas, com_bloco, _ambiguas = escolher_profissoes(respostas, base["profissao"])
    return await _preparar_e_enviar(sessao, {
        "cot": base["cotacao"], "cob": {}, "comissao": base["comissao"], "agenciamento": base["agenciamento"],
        "desconto": None, "seguradoras": base["seguradoras"], "seguradora_anterior": None,
        "negocio_ref": negocio_ref, "versao_base": None, "da_versao": False, "ajuste": None,
        "ramo": RAMO_VIDA, "status": list(SEGURADORAS_DO_RAMO[RAMO_VIDA]), "fora_do_re": list(SEGURADORAS_FORA_DO_RE),
        "profissoes": {str(k): v for k, v in escolhidas.items()}, "com_bloco": list(com_bloco)})


async def recalcular(sessao: Any, negocio_ref: str, *, versao_base: int, ajuste: Ajuste) -> Disparo:
    """Nova versão do MESMO negócio partindo da `versao_base` (as coberturas e a comissão DELA), mais o ajuste.
    O ramo vem da própria versão (RE: as coberturas em `configuracoes`, a comissão e a atividade de cada item)."""
    aj = {"tipo": ajuste.tipo, "valor": ajuste.valor, "seguradora": ajuste.seguradora}
    return await _preparar_e_enviar(sessao, {
        "cot": {"results": {k: {"errors": [], "successes": []} for k in ("main", "alternatives", "all", "porAssinatura", "ofertaCruzada")},
                "loaded": False, "isClearDraft": False, "correlationId": correlation_id()},
        "negocio_ref": negocio_ref, "versao_base": int(versao_base), "da_versao": True, "ajuste": aj,
        "status_por_ramo": {str(r): list(s) for r, s in SEGURADORAS_DO_RAMO.items()},
        "fora_do_re": list(SEGURADORAS_FORA_DO_RE),
        # 🔴 conserto 129-C (juiz B2): a Básica NÃO está entre as chaves que o ajuste muda (D-129C-03)
        "chaves_re": {str(r): list(k) for r, k in CHAVES_DO_AJUSTE_RE.items()}})


async def acompanhar(sessao: Any, disparo: Disparo, *, ao_evento: Callable[[Evento], Awaitable[Any]],
                     anterior: Optional[RodadaDoCalculo] = None, quadro_s: float = 60, teto_s: float = 480,
                     intervalo_s: float = 3, ao_quadro: Optional[Callable[[], Awaitable[Any]]] = None) -> RodadaDoCalculo:
    """Lê `calculos/{negocio}/{versao}` aos poucos (📊 184 KB constante × 373 KB das versões). Cada rodada → o
    leitor PURO → `eventos_entre(anterior, nova)` → `ao_evento`. Fecha quando tudo respondeu ou no teto.

    🔴 Conserto 129-B (juiz B1): "não consegui ler" NUNCA vira uma rodada vazia. 401/403 (sessão morta), página
    fechada, `LEITURAS_FALHAS_MAX` leituras seguidas sem resposta válida, ou o teto sem NENHUMA leitura válida →
    `LeituraImpossivel` (com `leu`/`quadro_saiu`/`rodada`, para o motor decidir entre `fechado` e `falhou`)."""
    atual = anterior
    quadro = False
    leu = False
    falhas = 0
    descartadas: Set[Any] = set()
    ramo = getattr(disparo, "ramo", RAMO_AUTO)
    lista = lista_de_calculos(ramo)
    if anterior is None:
        # SPEC-129-C D-129C-04: a seguradora que saiu por não ter atividade compatível é NARRADA (nunca some calada)
        for cod, nome in getattr(disparo, "sem_atividade", ()) or ():
            # conserto 129-C: a família é o NOME do tipo (a mesma da comparação), e o motivo vai junto
            await ao_evento(Evento(SEM_ATIVIDADE_COMPATIVEL, 0.0, nome or None, cod, SEM_ATIVIDADE, None, ramo,
                                   motivo=MOTIVO_SEM_ATIVIDADE))
        # SPEC-129-D: na vida, quem saiu antes do POST (sem profissão igual / sem comissão de vida) — o MESMO evento de
        # "saiu por não ter código compatível", com o motivo DELE (nunca o texto da atividade)
        for cod, nome, por in getattr(disparo, "fora_da_vida", ()) or ():
            await ao_evento(Evento(SEM_ATIVIDADE_COMPATIVEL, 0.0, nome or None, cod, SEM_ATIVIDADE, None, ramo,
                                   motivo=MOTIVO_DE_FORA_DA_VIDA.get(por)))

    def impossivel(motivo: str, *, morta: bool, pagina_fechada: bool = False) -> LeituraImpossivel:
        return LeituraImpossivel(motivo, sessao_morta=morta, leu=leu, quadro_saiu=quadro, rodada=atual,
                                 pagina_fechada=pagina_fechada)

    while True:
        await sessao.garantir_token()
        t = time.time() - disparo.t0
        try:
            r = await sessao.avaliar(JS_LER_CALCULOS, {**_args_base(sessao), "ref": disparo.negocio_ref,
                                                       "versao": int(disparo.versao), "lista": lista})
        except Exception as e:  # noqa: BLE001
            logger.warning("multicalculo.robo leitura falhou (%s)", type(e).__name__)
            r = None
            pagina = getattr(sessao, "pagina", None)
            fechada = False
            try:
                fechada = bool(pagina is not None and pagina.is_closed())
            except Exception:  # noqa: BLE001
                fechada = True
            if fechada:
                raise impossivel("a página do robô fechou durante a leitura", morta=True, pagina_fechada=True) from None
        status = r.get("status") if isinstance(r, dict) else None
        if status in STATUS_SESSAO_MORTA:
            raise impossivel(f"o Agger recusou a leitura (HTTP {status}): a sessão do robô caiu", morta=True)
        nova = None
        if isinstance(r, dict) and status == 200 and isinstance(r.get("corpo"), list):
            leu = True
            falhas = 0
            limpos, sujos = separar_itens(r["corpo"], ramo)
            for nome, cod in sujos:
                chave = cod if cod is not None else nome
                if chave not in descartadas:
                    descartadas.add(chave)
                    await ao_evento(Evento(ERRO_DE_LEITURA, t, nome or None, cod, ramo=ramo))
            nova = ler_rodada(limpos, t_s=t, ramo=ramo)
            if limpos or not r["corpo"]:
                for e in eventos_entre(atual, nova):
                    await ao_evento(e)
                atual = nova
        else:
            falhas += 1
            if falhas >= LEITURAS_FALHAS_MAX:
                raise impossivel(f"{falhas} leituras seguidas sem resposta do Agger", morta=False)
        fechado = bool(atual is not None and atual.fechado)
        if ao_quadro is not None and not quadro and leu and (t >= quadro_s or fechado):
            # 🔴 o quadro só "sai" com algo LIDO: sem leitura, não há quadro a mostrar
            quadro = True
            await ao_quadro()
        if fechado or t >= teto_s:
            if not leu:
                raise impossivel("o prazo acabou sem nenhuma leitura válida do Agger", morta=False)
            return atual if atual is not None else RodadaDoCalculo(t_s=t, respostas=(), fechado=False)
        await asyncio.sleep(intervalo_s)


async def pessoa_mexeu_recentemente(sessao: Any, negocio_ref: str, *, horas: int = 24,
                                    versoes_do_robo: Set[int]) -> bool:
    """D-MC-47 (§4.1): existe versão nas últimas `horas` cujo correlationId NÃO tem a marca do robô, OU (conta
    `ativo`) cujo usuarioId ≠ o do robô. Falha de leitura → True (na dúvida, não se recalcula por cima da pessoa)."""
    try:
        r = await sessao.avaliar(JS_PESSOA_MEXEU, {
            **_args_base(sessao), "ref": negocio_ref, "horas": horas, "prefixo": PREFIXO_DA_MARCA,
            "versoes_do_robo": sorted(int(v) for v in versoes_do_robo or ()),
            "conta_ativa": getattr(sessao, "robo_estado", None) == "ativo"})
    except Exception as e:  # noqa: BLE001
        logger.warning("multicalculo.robo pessoa_mexeu: leitura falhou (%s) → assume que sim", type(e).__name__)
        return True
    if not isinstance(r, dict) or "erro" in r:
        return True
    return bool(int(r.get("semMarca") or 0) or int(r.get("outroUsuario") or 0))


async def copiar_pdfs(sessao: Any, disparo: Disparo) -> Dict[tuple, bytes]:
    """O PDF de cada oferta, baixado DENTRO da página: a URL nunca sai; só os bytes (e só se for PDF)."""
    r = await sessao.avaliar(JS_PDFS, {**_args_base(sessao), "ref": disparo.negocio_ref,
                                       "versao": int(disparo.versao), "max": PDF_MAX_BYTES})
    saida: Dict[tuple, bytes] = {}
    for cod, pacote, tipo, b64 in (r or {}).get("pdfs") or []:
        chave = (int(cod) if isinstance(cod, int) else cod, sem_url_nem_chave(pacote), tipo)
        if chave in saida:
            continue
        dados = base64.b64decode(b64)
        if dados[:4] == b"%PDF" and len(dados) <= PDF_MAX_BYTES:
            saida[chave] = dados
    motivos = motivos_dos_pdfs(r)
    if (r or {}).get("falhas") or motivos:
        logger.info("multicalculo.robo pdfs: %s não copiados %s", int((r or {}).get("falhas") or 0), motivos)
    return saida


_RE_MOTIVO_PDF = re.compile(r"^(http_\d{1,3}|rede|nao_pdf|grande|so_nome)$")


def motivos_dos_pdfs(r: Any) -> Dict[str, int]:
    """As CLASSES de falha que a página contou (conserto 129-C, canário #7). Só nomes da lista e inteiros: o que não
    for isso não chega ao log (a página nunca devolve URL por aqui)."""
    m = (r or {}).get("motivos") if isinstance(r, dict) else None
    if not isinstance(m, dict):
        return {}
    return {k: int(v) for k, v in sorted(m.items())
            if isinstance(k, str) and _RE_MOTIVO_PDF.match(k) and isinstance(v, int) and not isinstance(v, bool)}
