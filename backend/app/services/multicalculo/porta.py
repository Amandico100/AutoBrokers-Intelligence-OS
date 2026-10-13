# -*- coding: utf-8 -*-
"""A PORTA do multicálculo — SPEC-129-B U2 (D-MC-37: `MulticalculoProvider`).

Qualquer parte do produto pede "calcule este pedido nas corretoras X e Y, padrão e econômica" e recebe o andamento por
eventos, sem saber qual login rodou. A porta NÃO calcula: autoriza, valida, cifra e ENFILEIRA em
`multicalculo_calculos`; o motor do `portal-worker` (F3) consome a fila; `consultar` devolve o que o motor gravou.

🔴 `company_id` é SEMPRE o 1º parâmetro nomeado (keyword-only) e é o SOLICITANTE — molde
`app/providers/policy_data_provider.py:PolicyDataProvider`. Nenhuma operação deduz tenant de contexto.

🔴 A AUTORIZAÇÃO (D-129B-05), antes de gravar qualquer linha:
    cada corretora pedida é uma empresa `client`, e
       corretora == solicitante, OU
       o solicitante é `platform_canal` E existe adesão ATIVA canal → corretora.
    Qualquer outra → `NaoAutorizado`. A mesma regra vale no `recalcular` e na LEITURA de ofertas/eventos de
    outra corretora no `consultar` (adesão desativada depois do pedido → o canal deixa de ver aquela corretora).

🔴 Comissão (G2): `comissao_percentual` só sai quando quem consulta É a corretora dona da oferta; o canal recebe None.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from portal_worker.multicalculo.contrato import RAMO_AUTO, TIPOS_DE_AJUSTE, TIPOS_DE_AJUSTE_RE, Ajuste

from app.services.multicalculo.pedido import CHAVE_DA_BASICA, RAMOS_RE, SERVICOS_EM_QUE_A_PLACA_SUPRE, PedidoDeCalculo
from portal_worker.multicalculo.presets import ORDEM_RE as _ORDEM_RE
from app.services.multicalculo.repositorio import RepositorioMulticalculo

logger = logging.getLogger(__name__)

#: as opções que a porta ACEITA — cada uma com preset em `portal_worker/multicalculo/presets.py` e na MESMA ordem de
#: `presets.ORDEM` (padrão abre o negócio; econômica e completa+ são versões dele). SPEC-130-A F4: a completa+
#: (D-MC-69 / D-130A-09). SPEC-130-A.1 F3: a mínima (a econômica sem carro reserva, D-130A1-05), a ÚLTIMA. O CHECK do
#: banco (migration 20261006_04, que alarga a 20261006_02) aceita exatamente estas.
OPCOES: Tuple[str, ...] = ("padrao", "economica", "completa_mais", "minima")
#: o que sai quando o chamador não escolhe: as duas da 129-B (a completa+ é PEDIDA, quando couber — D-MC-66). A carteira
#: NÃO gasta o cálculo da mínima (D-130A1-05)
OPCOES_PADRAO: Tuple[str, ...] = ("padrao", "economica")
#: o que o CANAL pede (D-130A1-05): as duas da 129-B + o "mínimo do mínimo" (a maior economia, nunca a recomendada)
OPCOES_DO_CANAL: Tuple[str, ...] = ("padrao", "economica", "minima")
#: SPEC-131-A (§4, F2 `presets.OPCOES_DA_RENOVACAO`): as opções da RENOVAÇÃO, na ordem do disparo (o `anterior` ABRE o
#: negócio). 🔴 `OPCOES` acima NÃO muda: é o gêmeo de `presets.ORDEM`/`PRESETS` (QCM e cotação) e da CHECK 20261006_04
#: (test_spec130a1_minima / test_spec130a_completa_mais conferem as três listas). A renovação tem a SUA lista; o banco
#: aceita a união (`TODAS_AS_OPCOES`, CHECK alargada pela migration 20261013_01 da F1). ⛔ econômica e mínima NUNCA
#: numa renovação (mutação 7)
OPCOES_DA_RENOVACAO: Tuple[str, ...] = ("anterior", "franquia_reduzida", "completa_mais")
PROIBIDAS_NA_RENOVACAO: Tuple[str, ...] = ("economica", "minima")
#: o que a porta ACEITA numa renovação, na ordem do disparo: as três da SPEC + a `padrao` da 131-0 A (o pedido que
#: chega sem a ficha da 130-B; `test_spec1310_f3_contas` a usa) — logo depois do `anterior`, que abre quando existe
OPCOES_DA_RENOVACAO_ACEITAS: Tuple[str, ...] = ("anterior", "padrao", "franquia_reduzida", "completa_mais")
TODAS_AS_OPCOES: Tuple[str, ...] = OPCOES + tuple(o for o in OPCOES_DA_RENOVACAO if o not in OPCOES)
ORIGENS: Tuple[str, ...] = ("auxiliar", "canal", "teste")
#: SPEC-129-C D-129C-03 — as opções de RE: "padrão" (as coberturas típicas do ramo) e "mais em conta" (as essenciais +
#: assistência básica), com os MESMOS nomes do auto (o CHECK do banco já as aceita) e na ordem do disparo dos presets
#: de RE (`presets.ORDEM_RE`, F1). A completa+ e a mínima são do carro.
OPCOES_POR_RAMO: Dict[int, Tuple[str, ...]] = {RAMO_AUTO: OPCOES, **{r: tuple(_ORDEM_RE) for r in RAMOS_RE}}
#: o canal comparador (QCM) continua SÓ AUTO nesta SPEC: RE é carteira (auxiliar) e canário (teste)
ORIGENS_DO_RE: Tuple[str, ...] = ("auxiliar", "teste")
#: SPEC-131-0 A · F3 (D-131-0-32): o SERVIÇO é coluna nova; a `origem` não muda (CHECK, prioridade, ~15 leitores) — ela
#: SAI do serviço: o Quem Cobra Menos é o canal; a cotação e a renovação são trabalho da corretora (prioridade menor)
SERVICOS: Tuple[str, ...] = ("qcm", "cotacao", "renovacao")
ORIGEM_DO_SERVICO: Dict[str, str] = {"qcm": "canal", "cotacao": "auxiliar", "renovacao": "auxiliar"}
#: os serviços que só a PRÓPRIA corretora pede para si (podem sair no Agger de uma pessoa dela — conserto red B2)
SERVICOS_DA_CORRETORA: Tuple[str, ...] = ("cotacao", "renovacao")
KIND_CANAL = "platform_canal"
KIND_CORRETORA = "client"
ENV_CANARIO = "AUTOBROKERS_CANARIO"
ENV_HMAC = "MULTICALCULO_HMAC_KEY"

#: D-129B-07 — a fila tem dono do tempo. 💭 valores: o canal tem alguém esperando no WhatsApp (prioridade 0, vence em
#: 10 min); o auxiliar trabalha de madrugada se precisar (5, vence em 24 h); o teste é o canário (0, 30 min).
PRIORIDADE: Dict[str, int] = {"canal": 0, "teste": 0, "auxiliar": 5}
VALIDADE: Dict[str, timedelta] = {"canal": timedelta(minutes=10), "teste": timedelta(minutes=30),
                                  "auxiliar": timedelta(hours=24)}
#: SPEC-131-A (laudo I1 §2.5, nota 85): a RENOVAÇÃO tem prioridade PRÓPRIA, abaixo da cotação (5) — a cotação pedida no
#: chat nunca espera uma madrugada que transbordou. Cotação e renovação têm a MESMA origem (`auxiliar`): a prioridade sai
#: do SERVIÇO. `prioridade=` de quem chama só pode pôr o pedido mais ATRÁS (≥ a do serviço), nunca na frente, e ≤ 9
PRIORIDADE_DO_SERVICO: Dict[str, int] = {"renovacao": 7}
PRIORIDADE_MAXIMA = 9
#: SPEC-131-A (D-131-03 revista): as políticas de sessão que um pedido pode levar — só a da madrugada, só na renovação
POLITICAS_DE_SESSAO: Tuple[str, ...] = ("madrugada",)

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# ---------------------------------------------------------------------------------------------------------------------
# As recusas — a mensagem leva NOMES de campo e motivos, nunca valores
# ---------------------------------------------------------------------------------------------------------------------
class NaoAutorizado(PermissionError):
    """O solicitante não pode calcular (ou ler) nesta corretora."""


class OrigemRecusada(PermissionError):
    """`origem='teste'` fora do canário (sem AUTOBROKERS_CANARIO=1), ou origem desconhecida (D-129B-04)."""


class PedidoIncompleto(ValueError):
    def __init__(self, campos: Sequence[str]):
        self.campos = list(campos)
        super().__init__("faltam campos obrigatórios: " + ", ".join(self.campos))


class PerfilIncompleto(ValueError):
    """No canal se PERGUNTA o perfil (D-MC-59): garagem, uso, km, jovem condutor."""

    def __init__(self, campos: Sequence[str]):
        self.campos = list(campos)
        super().__init__("o perfil precisa ser perguntado: " + ", ".join(self.campos))


class ChaveAusente(RuntimeError):
    """MULTICALCULO_HMAC_KEY ausente: a porta recusa calcular (fail-closed; nunca hash sem sal)."""


class NaoEncontrado(LookupError):
    """Pedido/cálculo inexistente PARA ESTE solicitante (não diz se existe noutro)."""


class PresetIndisponivel(RuntimeError):
    """Sem coberturas para a opção: nem explícitas nem preset. Nenhum cálculo sai sem coberturas."""


class RamoNaoSuportado(ValueError):
    """SPEC-129-C: o ramo não sai por este caminho — RE pelo canal (o QCM é só AUTO nesta SPEC) ou ramo sem motor."""


class ContaRecusada(PermissionError):
    """SPEC-131-0 A · F3: `qual_agger.decidir` recusou a conta (ex.: o Agger do dono recusou a senha e a apólice não
    vence logo). A mensagem é para quem pediu, em português de gente; NADA foi gravado.

    SPEC-131-A (P-1310-04): a recusa TRADUZIDA — `status` (o código estável que a renovação grava como motivo e uma
    rota devolve como 409), `frase` (para a tela, nunca 500 genérico) e `regra` (a da decisão)."""

    STATUS = "conta_recusada"
    HTTP = 409

    def __init__(self, frase: str = "", *, regra: Optional[str] = None):
        self.frase = str(frase or "O Agger desta conta recusou o cálculo.").strip()
        self.status = self.STATUS
        self.regra = regra
        super().__init__(self.frase)

    def para_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "frase": self.frase, "regra": self.regra}


# ---------------------------------------------------------------------------------------------------------------------
# O que volta
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PedidoAberto:
    pedido_id: str
    calculos: Tuple[Dict[str, str], ...]   # ({"id", "corretora_company_id", "opcao"}, ...)


@dataclass(frozen=True)
class Andamento:
    pedido_id: str
    status: str
    estados: Tuple[Dict[str, Any], ...]    # por cálculo: corretora × opção, status, posicao_na_fila
    ofertas: Tuple[Dict[str, Any], ...]    # menor prêmio primeiro
    eventos: Tuple[Dict[str, Any], ...]    # id > desde_evento, em ordem
    ultimo_evento: int


# ---------------------------------------------------------------------------------------------------------------------
# As peças pequenas
# ---------------------------------------------------------------------------------------------------------------------
def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _uuid(valor: Any, nome: str) -> str:
    texto = str(valor or "").strip()
    if not _UUID.match(texto):
        raise ValueError(f"{nome} precisa ser um uuid")
    return texto.lower()


def cpf_hmac(documento: str, *, chave: Optional[str] = None) -> str:
    """HMAC-SHA256(MULTICALCULO_HMAC_KEY, só os dígitos). Sem a chave → `ChaveAusente`."""
    segredo = chave if chave is not None else os.environ.get(ENV_HMAC, "")
    if not segredo:
        raise ChaveAusente(f"{ENV_HMAC} ausente — a porta não calcula sem ela")
    digitos = re.sub(r"\D", "", str(documento or ""))
    if not digitos:
        raise PedidoIncompleto(["segurado.cpf_cnpj"])
    return hmac.new(segredo.encode("utf-8"), digitos.encode("utf-8"), hashlib.sha256).hexdigest()


def _preset_padrao(opcao: str) -> Dict[str, Any]:
    """Os presets 💭 de `portal_worker/multicalculo/presets.py` (F2, D-129B-08): `PRESETS[opcao]` → dict.
    Ausente → `PresetIndisponivel` (fail-closed)."""
    try:
        from portal_worker.multicalculo import presets as _p
    except Exception as exc:  # noqa: BLE001
        raise PresetIndisponivel(f"presets indisponíveis ({type(exc).__name__})") from None
    tabela = getattr(_p, "PRESETS", None)
    if not isinstance(tabela, Mapping) or not isinstance(tabela.get(opcao), Mapping):
        raise PresetIndisponivel(f"sem preset para a opção {opcao}")
    return dict(tabela[opcao])


def extras_da_opcao_re(base_da_opcao: Mapping[str, Any], opcao: str, extras: Mapping[str, Any]) -> Dict[str, Any]:
    """🔴 Red P6 (conserto 129-C): as `extras` do pedido (a apólice anterior) VENCEM a opção — e na "mais em conta"
    isso a deixava quase igual à padrão (📊 empresarial: só `vidros 4000 → 0` mudava; o 2º calcularV2 saía repetido).
    Na "mais em conta" ficam só as extras que a PRÓPRIA opção cobre (`base_da_opcao` > 0: as essenciais do ramo + toda
    RC, `presets.coberturas_re` da econômica), com o valor da apólice; as acessórias saem. Na padrão, todas ficam."""
    from portal_worker.multicalculo.presets import ECONOMICA

    if opcao != ECONOMICA:
        return dict(extras or {})
    cobertas = {k for k, v in (base_da_opcao or {}).items()
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0}
    return {k: v for k, v in (extras or {}).items() if k in cobertas}


def _coberturas_re_padrao(ramo: int, opcao: str, valor_basica: Any, extras: Mapping[str, Any]) -> Dict[str, Any]:
    """As coberturas de UM cálculo de RE — o resolvedor dos presets (F1, `presets.coberturas_re`): todas as chaves do
    ramo, a Básica DO PEDIDO (D-129C-03), a assistência da opção e as `extras` do pedido (que vencem a opção)."""
    from portal_worker.multicalculo.presets import coberturas_re

    return dict(coberturas_re(ramo, opcao, valor_basica, extras))


def coberturas_de_re(base: Mapping[str, Any], pedido: PedidoDeCalculo) -> Dict[str, Any]:
    """As coberturas EXPLÍCITAS de quem chamou num cálculo de RE: valem como vieram, menos a Básica — que é SEMPRE a
    do pedido (D-129C-03), nunca a de quem chamou."""
    cob = dict(base or {})
    cob[CHAVE_DA_BASICA] = pedido.valor("risco", "valor_basica")
    return cob


def _ajuste_de_re(ajuste: Ajuste, ramo: int) -> Ajuste:
    """SPEC-129-C: o ajuste num cálculo de RE. Só `contrato.TIPOS_DE_AJUSTE_RE`; o rótulo vira o código pela tabela
    DE RE (`presets.VALORES_DO_AJUSTE_RE`, F1) — 📊 no RE a assistência é Não 0 · Básica 1 · Intermediária 2 ·
    Completa 3, DIFERENTE do auto (Completa 1 · Básica 4): o código do carro aqui seria um cálculo errado e calado
    (CLAUDE.md §9.5)."""
    if ajuste.tipo not in TIPOS_DE_AJUSTE_RE:
        raise ValueError(f"ajuste {ajuste.tipo} não existe no ramo {ramo} (aceitos: {', '.join(TIPOS_DE_AJUSTE_RE)})")
    valor = ajuste.valor
    if ajuste.tipo == "cobertura":
        if not isinstance(valor, Mapping) or not valor:
            raise ValueError("ajuste cobertura de RE: esperava {cobertura do Agger: valor}")
        _conferir_cobertura_do_ajuste_re(valor, ramo)
    elif isinstance(valor, str):
        texto = valor.strip()
        if texto.replace(".", "", 1).isdigit():
            valor = float(texto) if "." in texto else int(texto)
        else:
            from portal_worker.multicalculo.presets import VALORES_DO_AJUSTE_RE as tabela

            chave = unicodedata.normalize("NFKD", texto)
            chave = "".join(c for c in chave if not unicodedata.combining(c)).lower()
            valores = tabela.get(ajuste.tipo) or {}
            if chave not in valores:
                raise ValueError(f"ajuste {ajuste.tipo} do ramo {ramo}: rótulo sem código medido — mande o código")
            valor = valores[chave]
    elif isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"ajuste {ajuste.tipo} do ramo {ramo}: esperava um número")
    return Ajuste(tipo=ajuste.tipo, valor=valor, seguradora=ajuste.seguradora, ramo=ramo)


#: os nomes com que a BÁSICA pode chegar num ajuste (a chave do Agger, o nome do pedido, a palavra)
_NOMES_DA_BASICA = frozenset({CHAVE_DA_BASICA.lower(), "basica", "valor_basica", "cobertura_basica"})


def _conferir_cobertura_do_ajuste_re(valor: Mapping[str, Any], ramo: int) -> None:
    """🔴 Juiz B2 (conserto 129-C, decisão do gerente nota 88, D-129C-03): o ajuste NÃO muda a Básica — ela é a do
    PEDIDO; para outra Básica, um pedido novo. Antes a porta gravava a Básica antiga e o robô mandava a do ajuste: o
    banco mentia sobre o que foi calculado. Agora o que se grava é o que se envia: Básica no ajuste → recusa clara; e
    cobertura fora das do ramo (`presets.CHAVES_DE_COBERTURA_RE`, as que o robô aplica) → recusa, nunca gravada calada."""
    from portal_worker.multicalculo.presets import CHAVES_DE_COBERTURA_RE

    nomes = {str(k).strip().lower() for k in valor}
    if nomes & _NOMES_DA_BASICA:
        raise ValueError("o ajuste não muda a cobertura Básica (incêndio): ela vem do pedido — para outra Básica, "
                         "faça um pedido novo")
    validas = set(CHAVES_DE_COBERTURA_RE.get(int(ramo), ())) - {CHAVE_DA_BASICA}
    fora = sorted(str(k) for k in valor if k not in validas)
    if fora:
        raise ValueError(f"ajuste cobertura do ramo {ramo}: cobertura sem código no Agger: {', '.join(fora)}")
    for v in valor.values():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"ajuste cobertura do ramo {ramo}: cada cobertura precisa de um valor ≥ 0")


def _ajuste_codificado(ajuste: Ajuste) -> Ajuste:
    """F4 (costura): o rótulo do ajuste vira o CÓDIGO que o robô manda (`presets.VALORES_DO_AJUSTE`, medidos);
    rótulo sem código → `ValueError` na porta, nunca um recálculo recusado lá na frente."""
    from portal_worker.multicalculo.presets import VALORES_DO_AJUSTE

    valores = VALORES_DO_AJUSTE.get(ajuste.tipo)
    if valores is None or not isinstance(ajuste.valor, str):
        return ajuste
    texto = ajuste.valor.strip()
    if texto.isdigit():
        return Ajuste(tipo=ajuste.tipo, valor=int(texto), seguradora=ajuste.seguradora)
    chave = unicodedata.normalize("NFKD", texto)
    chave = "".join(c for c in chave if not unicodedata.combining(c)).lower()
    if chave not in valores:
        raise ValueError(f"ajuste {ajuste.tipo}: valor sem código medido (aceitos: {', '.join(sorted(valores))})")
    return Ajuste(tipo=ajuste.tipo, valor=valores[chave], seguradora=ajuste.seguradora)


def _aplicar_ajuste(coberturas: Mapping[str, Any], ajuste: Ajuste) -> Dict[str, Any]:
    """As coberturas da ORIGEM + o ajuste, nas chaves do AGGER (as de `calculos.coberturas`, que o montador aplica).
    `cobertura` com dict funde chave a chave; os outros tipos trocam a chave do item que o montador troca
    (`presets.CAMPO_DO_AJUSTE`, gêmeo do `montador.js`); `percentual_fipe` é do automóvel e não entra aqui.
    Ajuste de UMA seguradora não muda as coberturas gerais (o robô o aplica só no item dela)."""
    from portal_worker.multicalculo.presets import CAMPO_DO_AJUSTE

    novas = dict(coberturas or {})
    if ajuste.seguradora is not None:
        return novas
    if ajuste.tipo == "cobertura" and isinstance(ajuste.valor, Mapping):
        novas.update(dict(ajuste.valor))
    elif ajuste.tipo in CAMPO_DO_AJUSTE:
        novas[CAMPO_DO_AJUSTE[ajuste.tipo]] = ajuste.valor
    return novas


def _aplicar_ajuste_re(coberturas: Mapping[str, Any], ajuste: Ajuste) -> Dict[str, Any]:
    """O gêmeo de `_aplicar_ajuste` no RE: `cobertura` funde chave a chave em `configuracoes`; assistência/comissão/
    desconto trocam a chave do ramo (`presets.CAMPO_DO_AJUSTE_RE`, o gêmeo do `aplicarAjuste` do montador.js)."""
    from portal_worker.multicalculo.presets import CAMPO_DO_AJUSTE_RE

    novas = dict(coberturas or {})
    if ajuste.seguradora is not None:
        return novas
    if ajuste.tipo == "cobertura" and isinstance(ajuste.valor, Mapping):
        novas.update({k: v for k, v in ajuste.valor.items() if k != CHAVE_DA_BASICA})   # a Básica é a do pedido
    elif ajuste.tipo in CAMPO_DO_AJUSTE_RE:
        novas[CAMPO_DO_AJUSTE_RE[ajuste.tipo]] = ajuste.valor
    return novas


def comissao_re_valida(valor: Any, teto: float) -> bool:
    """Red P4 (conserto 129-C): a comissão EXPLÍCITA do item de RE é > 0 e ≤ o teto da config. 📊 o padrão do Agger no
    empresarial é 0 % (B0-a): um 0 escrito é exatamente o que a D-129C-05 evita; 500 % é erro de digitação."""
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)) and 0 < float(valor) <= float(teto)


def _erro_publico(erro: Any) -> Optional[str]:
    """O `erro` do cálculo como a corretora o lê: o motor já o gravou saneado; a porta saneia DE NOVO (URL, chave,
    PII) e corta — o banco não é confiado como única rede."""
    if not erro:
        return None
    from portal_worker.redaction import redigir_texto, sem_url_nem_chave

    return re.sub(r"\s+", " ", redigir_texto(sem_url_nem_chave(erro))).strip()[:200] or None


def _oferta_publica(linha: Mapping[str, Any], *, company_id: str) -> Dict[str, Any]:
    saida = {k: v for k, v in dict(linha).items() if k not in ("comissao_percentual", "pdf_path")}
    saida["corretora_company_id"] = str(linha.get("company_id"))
    saida.pop("company_id", None)
    # 🔴 G2: a comissão é INTERNA — só a corretora DONA da oferta a vê
    saida["comissao_percentual"] = (linha.get("comissao_percentual")
                                    if str(linha.get("company_id")) == str(company_id) else None)
    return saida


# ---------------------------------------------------------------------------------------------------------------------
# A PORTA
# ---------------------------------------------------------------------------------------------------------------------
class MulticalculoProvider:
    """A porta. `repositorio` e `cifrar` são injetáveis (testes: dublê em memória; produção: o cofre do smith-api)."""

    provider_key: str = "agger"

    def __init__(self, repositorio: Optional[RepositorioMulticalculo] = None, *,
                 cifrar: Optional[Callable[[str], str]] = None,
                 presets: Optional[Callable[[str], Mapping[str, Any]]] = None,
                 ambiente: Optional[Mapping[str, str]] = None,
                 agora: Callable[[], datetime] = _agora,
                 coberturas_re: Optional[Callable[..., Mapping[str, Any]]] = None):
        self.repo = repositorio or RepositorioMulticalculo()
        if cifrar is None:
            from app.services import portal_vault

            cifrar = portal_vault.encrypt
        self._cifrar = cifrar
        self._preset = presets or _preset_padrao
        self._coberturas_re = coberturas_re or _coberturas_re_padrao
        self._ambiente = ambiente
        self._agora = agora

    def _env(self, nome: str) -> str:
        fonte = self._ambiente if self._ambiente is not None else os.environ
        return str(fonte.get(nome, "") or "")

    # ------------------------------------------------------------------ capacidades
    def capacidades(self, ramo: int = RAMO_AUTO) -> Dict[str, Any]:
        if int(ramo) in RAMOS_RE:
            return {"ramo": int(ramo), "suportado": True, "portal": self.provider_key,
                    "opcoes": OPCOES_POR_RAMO[int(ramo)], "ajustes": TIPOS_DE_AJUSTE_RE, "origens": ORIGENS_DO_RE,
                    "canal": False, "renovacao": True, "entrega": "eventos (consultar com desde_evento)",
                    "pdf": "pdf(company_id, oferta_id) → bytes"}
        if int(ramo) != RAMO_AUTO:
            return {"ramo": int(ramo), "suportado": False,
                    "motivo": "calcula o AUTO (31) e o RE: condomínio (16), residencial (2), empresarial (18)"}
        return {"ramo": RAMO_AUTO, "suportado": True, "portal": self.provider_key, "opcoes": OPCOES,
                "ajustes": TIPOS_DE_AJUSTE, "origens": ORIGENS, "renovacao": True,
                "entrega": "eventos (consultar com desde_evento)", "pdf": "pdf(company_id, oferta_id) → bytes"}

    # ------------------------------------------------------------------ autorização
    async def _autorizar(self, *, company_id: str, corretoras: Sequence[str]) -> str:
        """Devolve o `company_kind` do solicitante, ou levanta `NaoAutorizado`. Nada é gravado antes disto."""
        tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id, *corretoras])
        kind = tipos.get(company_id)
        if not kind:
            raise NaoAutorizado("solicitante desconhecido")
        for c in corretoras:
            if tipos.get(c) != KIND_CORRETORA:
                raise NaoAutorizado("a corretora pedida não é uma corretora cliente")
        outras = [c for c in corretoras if c != company_id]
        if outras:
            if kind != KIND_CANAL:
                raise NaoAutorizado("só o canal calcula noutra corretora")
            aderidas = await asyncio.to_thread(self.repo.adesoes_ativas, canal_company_id=company_id,
                                               corretoras=outras)
            if set(outras) - aderidas:
                raise NaoAutorizado("o canal não tem adesão ativa com a corretora pedida")
        return kind

    def _conferir_origem(self, origem: str) -> None:
        if origem not in ORIGENS:
            raise OrigemRecusada(f"origem desconhecida: {origem!r}")
        if origem == "teste" and self._env(ENV_CANARIO) != "1":
            raise OrigemRecusada("origem 'teste' só no canário (AUTOBROKERS_CANARIO=1)")

    # ------------------------------------------------------------------ calcular
    async def calcular(self, *, company_id: str, pedido: PedidoDeCalculo,
                       corretoras: Optional[Iterable[str]] = None,
                       opcoes: Iterable[str] = OPCOES_PADRAO,
                       coberturas: Optional[Mapping[str, Mapping[str, Any]]] = None,
                       origem: Optional[str] = None, quadro_s: int = 60,
                       servico: Optional[str] = None, solicitante_user_id: Optional[str] = None,
                       dono_user_id: Optional[str] = None, vence_em_dias: Optional[int] = None,
                       prioridade: Optional[int] = None, politica_de_sessao: Optional[str] = None,
                       renovacao_id: Optional[str] = None,
                       forcar_corretora_motivo: Optional[str] = None) -> PedidoAberto:
        """SPEC-131-0 A · F3: com `servico` (qcm · cotacao · renovacao), a conta de CADA corretora é decidida por
        `qual_agger.decidir` ANTES de gravar e fica no cálculo (`conta_exigida_id` + regra + fallback + motivo); a
        `origem` sai do serviço (qcm → canal; cotação/renovação → auxiliar). `servico=None` = o legado (canário, testes):
        nada muda, byte a byte. `vence_em_dias` (renovação) libera o Agger da corretora quando o do dono recusou a senha e
        a apólice vence logo (`servicos.renovacao.conta_global_se_vence_em_dias`).

        SPEC-131-A (contrato §5): `prioridade` (None = a do serviço/origem: renovação 7, cotação 5, canal 0; maior = mais
        ATRÁS, nunca na frente) · `politica_de_sessao` (só None ou 'madrugada', só na renovação — quem a passa é
        `madrugada.py`) · `renovacao_id` (o item de `renovacoes`, só na renovação) · `forcar_corretora_motivo` (o desvio
        das 06:15: o Agger da corretora COM aviso nomeado, só na renovação). As colunas novas só são escritas quando
        vêm — o legado continua byte a byte."""
        company_id = _uuid(company_id, "company_id")
        prioridade, politica_de_sessao, renovacao_id = self._da_madrugada(
            servico=servico, prioridade=prioridade, politica_de_sessao=politica_de_sessao, renovacao_id=renovacao_id,
            forcar_corretora_motivo=forcar_corretora_motivo)
        if servico is not None:
            if servico not in SERVICOS:
                raise ValueError("serviços aceitos: " + ", ".join(SERVICOS))
            if origem is not None and origem != ORIGEM_DO_SERVICO[servico]:
                raise ValueError(f"o serviço {servico} sai pela origem {ORIGEM_DO_SERVICO[servico]!r}, não {origem!r}")
            origem = ORIGEM_DO_SERVICO[servico]
            solicitante_user_id = _uuid(solicitante_user_id, "solicitante_user_id") if solicitante_user_id else None
            dono_user_id = _uuid(dono_user_id, "dono_user_id") if dono_user_id else None
        elif solicitante_user_id or dono_user_id:
            raise ValueError("quem pediu e o dono só valem com o serviço (qcm, cotacao, renovacao)")
        if origem is None:
            raise ValueError("origem obrigatória (ou o serviço)")
        self._conferir_origem(origem)
        alvo: List[str] = []
        for c in (corretoras if corretoras is not None else [company_id]):
            u = _uuid(c, "corretora")
            if u not in alvo:
                alvo.append(u)
        if not alvo:
            raise ValueError("nenhuma corretora pedida")
        ramo = int(getattr(pedido, "ramo", RAMO_AUTO) or RAMO_AUTO)
        pedidas = set(opcoes)
        if servico == "renovacao":
            # SPEC-131-A §4: ⛔ econômica e mínima NUNCA numa renovação (mutação 7) — recusa ANTES de qualquer leitura
            proibidas = sorted(pedidas & set(PROIBIDAS_NA_RENOVACAO))
            if proibidas:
                raise ValueError("opção proibida numa renovação: " + ", ".join(proibidas))
            aceitas = OPCOES_DA_RENOVACAO_ACEITAS
            coberturas = self._coberturas_da_renovacao(pedido, coberturas)
            # a opção que o pedido CEDEU (F2: a franquia já era reduzida → "cede o lugar") não sai; o resto, na ordem
            cedidas = self._cedidas(pedido, pedidas)
            pedidas -= cedidas
        else:
            aceitas = OPCOES_POR_RAMO.get(ramo, OPCOES)
        escolhidas = [o for o in aceitas if o in pedidas]    # a ordem é a de OPCOES (a do disparo), nunca a do chamador
        if (pedidas - set(aceitas)) or not escolhidas:
            raise ValueError("opções aceitas: " + ", ".join(aceitas))
        quadro = int(quadro_s)
        if not 5 <= quadro <= 600:
            raise ValueError("quadro_s entre 5 e 600")
        if not isinstance(pedido, PedidoDeCalculo):
            raise TypeError("pedido precisa ser um PedidoDeCalculo")
        if ramo != RAMO_AUTO and (ramo not in RAMOS_RE or origem not in ORIGENS_DO_RE):
            # SPEC-129-C: o canal comparador (QCM) é SÓ AUTO nesta SPEC — recusa clara ANTES de qualquer leitura
            raise RamoNaoSuportado(f"o ramo {ramo} não sai pela origem {origem!r}: o canal calcula só o AUTO "
                                   f"({RAMO_AUTO}); o RE sai pela carteira da corretora")

        kind = await self._autorizar(company_id=company_id, corretoras=alvo)
        if servico in SERVICOS_DA_CORRETORA and (kind != KIND_CORRETORA or alvo != [company_id]):
            # 🔴 conserto 131-0 A (red B2): cotação e renovação são trabalho DA PRÓPRIA corretora (o Agger de uma pessoa
            # dela pode ser usado). Ninguém de fora — nem o canal com adesão — pede esses serviços: o filtro mora AQUI,
            # na porta, e não na confiança em quem chamou (CLAUDE.md §7). O canal calcula só o Quem Cobra Menos (`qcm`)
            raise NaoAutorizado(f"o serviço {servico} só é pedido pela própria corretora, para ela mesma")
        if ramo != RAMO_AUTO:
            if kind == KIND_CANAL:
                raise RamoNaoSuportado("o canal calcula só o AUTO nesta versão")
            # D-129C-05: a comissão EXPLÍCITA do ramo ANTES de validar — o contrato a exige. Red P4 (conserto 129-C):
            # a que o pedido TROUXE também passa pela régua da config (> 0 e ≤ `comissao.teto_pct`)
            comissao, teto = await self._comissao_re(company_id=company_id, ramo=ramo, servico=servico)
            pedido = pedido.com_comissao(comissao)
            if not comissao_re_valida(pedido.valor("comissao_desconto", "comissao_percentual"), teto):
                raise PedidoIncompleto(["comissao_desconto.comissao_percentual"])

        # F4 (costura): o que falta E o que veio sem código medido no Agger (o robô recusaria só no disparo)
        # SPEC-133-A D-133A-03: no canal a PLACA supre FIPE/ano/combustível (o robô preenche pela placa — ver
        # `pedido.CAMPOS_QUE_A_PLACA_SUPRE`, com a evidência no robô)
        # SPEC-131-A F5: e na RENOVAÇÃO (o serviço) — a apólice traz a placa (`pedido.SERVICOS_EM_QUE_A_PLACA_SUPRE`)
        ausentes = pedido.faltando(origem=origem, servico=servico)
        faltam = ausentes + [c for c in pedido.sem_codigo() if c not in ausentes]
        if faltam:
            raise PedidoIncompleto(faltam)
        if renovacao_id is not None:
            # SPEC-131-A costura F4: UM pedido aberto por renovação. A janela de crash entre a porta gravar e a madrugada
            # gravar o estado (F1) não duplica o cálculo — o pedido aberto que já existe é devolvido. O desvio das 06:15
            # (`forcar_corretora_motivo`) CANCELA o aberto antes de abrir o novo no Agger da corretora (nunca dois em voo)
            ja = await asyncio.to_thread(self._aberto_da_renovacao, company_id, renovacao_id,
                                         cancelar=forcar_corretora_motivo is not None)
            if ja is not None:
                logger.info("[MULTICALCULO] a renovação já tem pedido aberto: devolvido, nada gravado")
                return ja
        # SPEC-131-0 A · F3: QUAL AGGER, por corretora, antes de qualquer escrita — uma recusa não grava nada
        contas = await self._decidir_contas(alvo=alvo, servico=servico, solicitante_user_id=solicitante_user_id,
                                            dono_user_id=dono_user_id, vence_em_dias=vence_em_dias,
                                            forcar_corretora_motivo=forcar_corretora_motivo)
        quem = {"servico": servico, "solicitante_user_id": solicitante_user_id, "contas": contas,
                "prioridade": prioridade, "politica_de_sessao": politica_de_sessao, "renovacao_id": renovacao_id}
        if ramo != RAMO_AUTO:
            return await self._calcular_re(company_id=company_id, pedido=pedido, alvo=alvo, escolhidas=escolhidas,
                                           coberturas=coberturas, origem=origem, quadro=quadro, quem=quem)
        if origem == "canal":
            pedido = pedido.assumindo_pela_placa()
            perfil = pedido.perfil_faltando()
            if perfil:
                raise PerfilIncompleto(perfil)
        else:
            if servico in SERVICOS_EM_QUE_A_PLACA_SUPRE:
                pedido = pedido.assumindo_pela_placa(servico=servico)   # F5: "o Agger preenche pela placa", declarado
            pedido = pedido.assumindo_perfil()          # D-128-07: auxiliar (e o canário) assumem o padrão da tela

        hmac_doc = cpf_hmac(pedido.documento, chave=self._env(ENV_HMAC))   # fail-closed ANTES de gravar

        por_opcao: Dict[str, Dict[str, Any]] = {}
        for o in escolhidas:
            explicitas = (coberturas or {}).get(o)
            cob = dict(explicitas) if explicitas is not None else dict(self._preset(o) or {})
            if not cob:
                raise PresetIndisponivel(f"sem coberturas para a opção {o}")
            por_opcao[o] = cob

        return await self._gravar(company_id=company_id, dados=pedido.para_dict(), ramo=pedido.ramo,
                                  hmac_doc=hmac_doc, alvo=alvo, escolhidas=escolhidas, por_opcao=por_opcao,
                                  origem=origem, quadro=quadro, quem=quem)

    async def _decidir_contas(self, *, alvo: List[str], servico: Optional[str], solicitante_user_id: Optional[str],
                              dono_user_id: Optional[str], vence_em_dias: Optional[int],
                              forcar_corretora_motivo: Optional[str] = None) -> Dict[str, Any]:
        """{corretora: DecisaoDeConta} — vazio no legado (`servico=None`). Uma `recusa` → `ContaRecusada`."""
        if servico is None:
            return {}
        from app.services.multicalculo import qual_agger

        extra = {"forcar_corretora_motivo": forcar_corretora_motivo} if forcar_corretora_motivo is not None else {}
        decisoes: Dict[str, Any] = {}
        for corretora in alvo:
            d = await asyncio.to_thread(qual_agger.decidir, self.repo.db, company_id=corretora, servico=servico,
                                        solicitante_user_id=solicitante_user_id, dono_user_id=dono_user_id,
                                        vence_em_dias=vence_em_dias, **extra)
            if d.recusa:
                raise ContaRecusada(d.recusa, regra=d.regra)
            decisoes[corretora] = d
        return decisoes

    # ------------------------------------------------------------------ SPEC-131-A: a madrugada
    def _aberto_da_renovacao(self, company_id: str, renovacao_id: str, *, cancelar: bool) -> Optional[PedidoAberto]:
        """O pedido `aberto` DESTA corretora para a renovação (filtro `company_id` no banco E de novo aqui, §7).
        `cancelar=True` (o desvio): cancela os abertos e devolve None. Senão devolve o mais recente, com os cálculos."""
        db = self.repo.db
        linhas = [dict(x) for x in (db.table("multicalculo_pedidos").select("id, company_id, status, criado_em")
                                    .eq("company_id", company_id).eq("renovacao_id", renovacao_id)
                                    .eq("status", "aberto").execute().data or [])
                  if str(x.get("company_id")) == company_id and x.get("status") == "aberto"]
        if not linhas:
            return None
        if cancelar:
            for p in linhas:
                self.repo.cancelar(company_id=company_id, pedido_id=str(p["id"]))
            return None
        p = max(linhas, key=lambda x: str(x.get("criado_em") or ""))
        calcs = [c for c in (db.table("multicalculo_calculos").select("id, company_id, opcao, solicitante_company_id")
                             .eq("pedido_id", str(p["id"])).eq("solicitante_company_id", company_id).execute().data
                             or []) if str(c.get("solicitante_company_id")) == company_id]
        return PedidoAberto(pedido_id=str(p["id"]), calculos=tuple(
            {"id": str(c["id"]), "corretora_company_id": str(c["company_id"]), "opcao": str(c["opcao"])}
            for c in calcs))

    @staticmethod
    def _da_madrugada(*, servico: Optional[str], prioridade: Any, politica_de_sessao: Any, renovacao_id: Any,
                      forcar_corretora_motivo: Any) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """(prioridade, politica, renovacao_id) conferidos — ANTES de qualquer leitura. Recusa = `ValueError`."""
        if politica_de_sessao is not None:
            if politica_de_sessao not in POLITICAS_DE_SESSAO:
                raise ValueError("política de sessão aceita: " + ", ".join(POLITICAS_DE_SESSAO))
            if servico != "renovacao":
                raise ValueError("a política de sessão da madrugada só vale na renovação")
        if renovacao_id is not None:
            if servico != "renovacao":
                raise ValueError("renovacao_id só vale na renovação")
            renovacao_id = _uuid(renovacao_id, "renovacao_id")
        if forcar_corretora_motivo is not None:
            if servico != "renovacao":
                raise ValueError("forçar o Agger da corretora só vale na renovação")
            if not str(forcar_corretora_motivo).strip():
                raise ValueError("forçar o Agger da corretora exige o motivo (o aviso nunca sai calado)")
            if politica_de_sessao is not None:
                raise ValueError("o desvio para o Agger da corretora não leva a política de sessão da madrugada")
        if prioridade is not None:
            if isinstance(prioridade, bool) or not isinstance(prioridade, int):
                raise ValueError("prioridade precisa ser um inteiro")
            base = PRIORIDADE_DO_SERVICO.get(str(servico), PRIORIDADE.get(ORIGEM_DO_SERVICO.get(str(servico), ""), 0))
            if not base <= prioridade <= PRIORIDADE_MAXIMA:
                # 🔴 mutação 5 da SPEC: nenhuma renovação passa na frente da cotação (prioridade < 7 é recusada)
                raise ValueError(f"prioridade entre {base} e {PRIORIDADE_MAXIMA} para este serviço (maior = mais atrás)")
        return prioridade, politica_de_sessao, renovacao_id

    @staticmethod
    def _coberturas_da_renovacao(pedido: PedidoDeCalculo,
                                 coberturas: Optional[Mapping[str, Mapping[str, Any]]]
                                 ) -> Optional[Mapping[str, Mapping[str, Any]]]:
        """As coberturas de cada opção da renovação: as EXPLÍCITAS de quem chamou vencem; senão as que o PEDIDO montou
        da ficha (F2: `PedidoDeCalculo.coberturas_por_opcao`, o `anterior` é montado apólice a apólice)."""
        if coberturas is not None:
            return coberturas
        do_pedido = getattr(pedido, "coberturas_por_opcao", None)
        return dict(do_pedido) if isinstance(do_pedido, Mapping) and do_pedido else None

    @staticmethod
    def _cedidas(pedido: PedidoDeCalculo, pedidas: set) -> set:
        """As opções pedidas que o PEDIDO montou como cedidas (F2: a franquia já era reduzida → a `franquia_reduzida`
        CEDE o lugar). Só quando o pedido declara as suas opções; o resto é recusado como sempre."""
        do_pedido = tuple(getattr(pedido, "opcoes", ()) or ())
        if not do_pedido:
            return set()
        return {o for o in pedidas if o in OPCOES_DA_RENOVACAO and o not in do_pedido}

    async def _carregar_cfg(self, company_id: str, servico: Optional[str]) -> Dict[str, Any]:
        """SPEC-131-0 A (§5.3): a config da corretora ⊕ o manual do SERVIÇO do pedido. Sem serviço (legado) a chamada é
        a de sempre, byte a byte — `servico` só vai quando existe."""
        from app.services.multicalculo.config import carregar

        if servico is None:
            return await asyncio.to_thread(carregar, company_id, db=self.repo.db)
        return await asyncio.to_thread(carregar, company_id, db=self.repo.db, servico=servico)

    async def _comissao_re(self, *, company_id: str, ramo: int, servico: Optional[str] = None) -> Tuple[float, float]:
        """D-129C-05: (a comissão do item no ramo, o teto) da config da CORRETORA (no RE a corretora é a solicitante: o
        canal está fora). Banco fora → `ConfigIndisponivel` (nunca a comissão às cegas)."""
        from app.services.multicalculo.config import comissao_do_ramo, teto_da_comissao

        cfg = await self._carregar_cfg(company_id, servico)
        return comissao_do_ramo(cfg, ramo), teto_da_comissao(cfg)

    async def _calcular_re(self, *, company_id: str, pedido: PedidoDeCalculo, alvo: List[str],
                           escolhidas: List[str], coberturas: Optional[Mapping[str, Mapping[str, Any]]],
                           origem: str, quadro: int, quem: Optional[Mapping[str, Any]] = None) -> PedidoAberto:
        """SPEC-129-C: o pedido de RE (já validado pelo contrato e com a comissão do ramo) — as coberturas de cada
        opção pelo resolvedor dos presets (a Básica e as extras DO PEDIDO) ou as explícitas de quem chamou (com a
        Básica do pedido). Extra fora das coberturas do ramo já voltou como `PedidoIncompleto` (`sem_codigo`)."""
        hmac_doc = cpf_hmac(pedido.documento, chave=self._env(ENV_HMAC))   # fail-closed ANTES de gravar
        basica = pedido.valor("risco", "valor_basica")
        extras = dict(pedido.valor("risco", "extras") or {})
        por_opcao: Dict[str, Dict[str, Any]] = {}
        for o in escolhidas:
            explicitas = (coberturas or {}).get(o)
            if explicitas is not None:
                cob = coberturas_de_re(explicitas, pedido)
            elif o not in _ORDEM_RE:
                # SPEC-131-A: `anterior`/`franquia_reduzida`/`completa_mais` do RE são montadas da ficha (F2) — sem elas,
                # nunca a típica disfarçada de "igual ao ano passado"
                raise PresetIndisponivel(f"sem coberturas para a opção {o} do ramo {pedido.ramo}")
            else:
                base = dict(self._coberturas_re(pedido.ramo, o, basica, {}) or {})
                cob = dict(self._coberturas_re(pedido.ramo, o, basica, extras_da_opcao_re(base, o, extras)) or {})
            if not cob:
                raise PresetIndisponivel(f"sem coberturas para a opção {o} do ramo {pedido.ramo}")
            por_opcao[o] = cob
        return await self._gravar(company_id=company_id, dados=pedido.para_dict(), ramo=pedido.ramo,
                                  hmac_doc=hmac_doc, alvo=alvo, escolhidas=escolhidas, por_opcao=por_opcao,
                                  origem=origem, quadro=quadro, quem=quem)

    async def _gravar(self, *, company_id: str, dados: Mapping[str, Any], ramo: int, hmac_doc: str,
                      alvo: List[str], escolhidas: List[str], por_opcao: Mapping[str, Mapping[str, Any]],
                      origem: str, quadro: int, quem: Optional[Mapping[str, Any]] = None) -> PedidoAberto:
        cifrado = self._cifrar(json.dumps(dados, ensure_ascii=False, sort_keys=True))
        agora = self._agora()
        pedido_id = str(uuid.uuid4())
        servico = (quem or {}).get("servico")
        # SPEC-131-A: a prioridade do SERVIÇO (renovação 7) ou a que quem chamou pediu (já conferida: nunca na frente)
        prioridade = (quem or {}).get("prioridade")
        if prioridade is None:
            prioridade = PRIORIDADE_DO_SERVICO.get(str(servico), PRIORIDADE[origem])
        linha_pedido = {
            "id": pedido_id, "company_id": company_id, "origem": origem, "ramo": ramo,
            "opcoes": escolhidas, "corretoras": alvo, "pedido_cifrado": cifrado, "cpf_hmac": hmac_doc,
            "quadro_s": quadro, "status": "aberto",
        }
        linhas_calc = [{
            "id": str(uuid.uuid4()), "pedido_id": pedido_id, "solicitante_company_id": company_id,
            "company_id": corretora, "opcao": o, "coberturas": por_opcao[o], "status": "na_fila",
            "prioridade": int(prioridade), "expira_em": (agora + VALIDADE[origem]).isoformat(),
            "disponivel_em": agora.isoformat(),
        } for corretora in alvo for o in escolhidas]
        # SPEC-131-A: a política de sessão e o item da renovação (colunas da migration 20261013_01) — só quando vêm
        for coluna in ("politica_de_sessao", "renovacao_id"):
            if (quem or {}).get(coluna) is not None:
                linha_pedido[coluna] = (quem or {})[coluna]
        if servico is not None:
            # SPEC-131-0 A · F3: o pedido diz para QUAL serviço e QUEM pediu; cada cálculo, em QUAL conta (a da decisão
            # da corretora dele) e por quê. O legado (`servico=None`) não escreve nenhuma coluna nova
            linha_pedido["servico"] = servico
            linha_pedido["solicitante_user_id"] = (quem or {}).get("solicitante_user_id")
            contas = (quem or {}).get("contas") or {}
            for c in linhas_calc:
                d = contas[c["company_id"]]
                c.update({"conta_exigida_id": d.conta_id, "conta_regra": d.regra, "conta_fallback": bool(d.fallback),
                          "conta_motivo": d.texto_para_o_banco() or None})
        _p, gravados = await asyncio.to_thread(self.repo.gravar_pedido, linha_pedido, linhas_calc)
        logger.info("[MULTICALCULO] pedido enfileirado: %s cálculo(s), origem=%s", len(linhas_calc), origem)
        return PedidoAberto(pedido_id=pedido_id, calculos=tuple(
            {"id": str(c["id"]), "corretora_company_id": str(c["company_id"]), "opcao": str(c["opcao"])}
            for c in (gravados or linhas_calc)))

    # ------------------------------------------------------------------ consultar
    async def consultar(self, *, company_id: str, pedido_id: str, desde_evento: int = 0) -> Andamento:
        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=pedido_id)
        if not ped or str(ped.get("company_id")) != company_id:
            raise NaoEncontrado("pedido não encontrado")
        calculos = await asyncio.to_thread(self.repo.calculos_do_pedido, company_id=company_id, pedido_id=pedido_id)
        ofertas = await asyncio.to_thread(self.repo.ofertas_do_pedido, company_id=company_id, pedido_id=pedido_id)
        eventos = await asyncio.to_thread(self.repo.eventos_do_pedido, company_id=company_id,
                                          pedido_id=pedido_id, desde_evento=desde_evento)

        # a LEITURA de outra corretora exige o canal com adesão ATIVA agora (reconferida a cada consulta)
        corretoras = sorted({str(c.get("company_id")) for c in calculos} | {str(o.get("company_id")) for o in ofertas}
                            | {str(e.get("company_id")) for e in eventos})
        visiveis = {company_id}
        outras = [c for c in corretoras if c != company_id]
        if outras:
            tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id])
            if tipos.get(company_id) == KIND_CANAL:
                visiveis |= await asyncio.to_thread(self.repo.adesoes_ativas, canal_company_id=company_id,
                                                    corretoras=outras)

        fila = [c for c in calculos if c.get("status") == "na_fila"]
        a_frente = await asyncio.to_thread(self.repo.fila_a_frente) if fila else []
        estados = []
        for c in calculos:
            if str(c.get("company_id")) not in visiveis:
                continue
            posicao = None
            if c.get("status") == "na_fila":
                chave = (int(c.get("prioridade") or 0), str(c.get("disponivel_em") or ""))
                posicao = 1 + sum(1 for f in a_frente
                                  if (int(f.get("prioridade") or 0), str(f.get("disponivel_em") or "")) < chave)
            estados.append({"calculo_id": str(c["id"]), "corretora_company_id": str(c["company_id"]),
                            "opcao": c.get("opcao"), "status": c.get("status"), "posicao_na_fila": posicao,
                            "primeira_oferta_em": c.get("primeira_oferta_em"),
                            "quadro_pronto_em": c.get("quadro_pronto_em"), "fechado_em": c.get("fechado_em"),
                            "origem_calculo_id": c.get("origem_calculo_id"),
                            # conserto 129-B (juiz P4): o PORQUÊ do falhou/incerto/cancelado, saneado de novo
                            "erro": _erro_publico(c.get("erro"))})
            if int(ped.get("ramo") or RAMO_AUTO) != RAMO_AUTO:
                # conserto 129-C (red P2): a régua de RE compara cada oferta com o que o CÁLCULO PEDIU, não com o
                # quadro. Sem a margem (o ajuste de comissão/desconto a grava aqui) — G2, mesmo no RE sem canal
                estados[-1]["coberturas_pedidas"] = {
                    k: v for k, v in dict(c.get("coberturas") or {}).items()
                    if not str(k).lower().startswith(("perccomissao", "percdesconto"))}
        ofertas_v = sorted((_oferta_publica(o, company_id=company_id) for o in ofertas
                            if str(o.get("company_id")) in visiveis),
                           key=lambda o: float(o.get("premio_total") or 0))
        eventos_v = []
        for e in eventos:
            if str(e.get("company_id")) not in visiveis:
                continue
            item = {k: v for k, v in dict(e).items() if k != "company_id"}
            item["corretora_company_id"] = str(e.get("company_id"))
            eventos_v.append(item)
        ultimo = max([int(desde_evento or 0)] + [int(e.get("id") or 0) for e in eventos])
        return Andamento(pedido_id=pedido_id, status=str(ped.get("status")), estados=tuple(estados),
                         ofertas=tuple(ofertas_v), eventos=tuple(eventos_v), ultimo_evento=ultimo)

    # ------------------------------------------------------------------ recalcular
    async def recalcular(self, *, company_id: str, calculo_id: str, ajuste: Any) -> Dict[str, str]:
        """Nova versão do MESMO negócio, na MESMA corretora (D-MC-41), a partir da versão CERTA (a da origem)."""
        company_id = _uuid(company_id, "company_id")
        calculo_id = _uuid(calculo_id, "calculo_id")
        if isinstance(ajuste, Mapping):
            ajuste = Ajuste(tipo=str(ajuste.get("tipo")), valor=ajuste.get("valor"),
                            seguradora=ajuste.get("seguradora"))
        if not isinstance(ajuste, Ajuste):
            raise TypeError("ajuste precisa ser um contrato.Ajuste ou um dict {tipo, valor, seguradora}")
        ajuste_bruto = ajuste                         # SPEC-129-C: o RE recodifica pela tabela DO RAMO (abaixo)
        try:
            ajuste, erro_do_auto = _ajuste_codificado(ajuste), None
        except ValueError as exc:                     # rótulo sem código no AUTO — pode ter no RE ("intermediaria")
            erro_do_auto = exc
        origem = await asyncio.to_thread(self.repo.calculo, company_id=company_id, calculo_id=calculo_id)
        if not origem or str(origem.get("solicitante_company_id")) != company_id:
            raise NaoEncontrado("cálculo não encontrado")
        corretora = str(origem["company_id"])
        await self._autorizar(company_id=company_id, corretoras=[corretora])   # reconfere a adesão do canal
        if origem.get("negocio_ref") is None or origem.get("versao") is None:
            raise ValueError("o cálculo de origem ainda não tem negócio no portal — espere o disparo")
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=str(origem["pedido_id"]))
        if not ped:
            raise NaoEncontrado("pedido não encontrado")
        if ped.get("status") == "cancelado":
            raise ValueError("pedido cancelado")
        self._conferir_origem(str(ped.get("origem")))
        # SPEC-131-0 A · F3: o serviço do pedido e a conta em que a origem saiu (o recálculo herda as duas)
        do_pedido = await asyncio.to_thread(self.repo.servico_e_conta, company_id=company_id,
                                            pedido_id=str(origem["pedido_id"]), calculo_id=calculo_id)
        ramo = int(ped.get("ramo") or RAMO_AUTO)
        if ramo != RAMO_AUTO:
            ajuste = _ajuste_de_re(ajuste_bruto, ramo)      # nunca o código do CARRO num cálculo de RE
            if ajuste.tipo == "comissao":
                _c, teto = await self._comissao_re(company_id=company_id, ramo=ramo,
                                                   servico=do_pedido.get("servico"))
                if not comissao_re_valida(ajuste.valor, teto):
                    raise ValueError(f"ajuste comissao do ramo {ramo}: precisa ser maior que 0 e no máximo {teto:g} %")
        elif erro_do_auto is not None:
            raise erro_do_auto
        # 🔴 conserto 129-B (red P4): o clique duplo não vira 2º calcularV2 — o MESMO ajuste da MESMA origem ainda
        # na fila ou no robô é DEVOLVIDO (o motor também cancela o repetido que escapar desta conferência)
        em_curso = await asyncio.to_thread(self.repo.ajustes_em_curso, company_id=company_id,
                                           origem_calculo_id=calculo_id)
        pedido_igual = {"tipo": ajuste.tipo, "valor": ajuste.valor, "seguradora": ajuste.seguradora}
        for c in em_curso:
            aj = c.get("ajuste") if isinstance(c.get("ajuste"), Mapping) else {}
            if str(c.get("company_id")) == corretora and \
                    {k: aj.get(k) for k in ("tipo", "valor", "seguradora")} == pedido_igual:
                return {"id": str(c["id"]), "corretora_company_id": corretora, "opcao": "ajuste",
                        "origem_calculo_id": calculo_id, "repetido": True}
        # SPEC-131-0 A · F3: o recálculo HERDA a conta de origem (o negócio mora nela — V20). Só nos pedidos com serviço:
        # o legado não escreve coluna nova (o motor já o prende à conta do negócio por `_conta_do_grupo`)
        conta_herdada: Dict[str, Any] = {}
        if do_pedido.get("servico"):
            from app.services.multicalculo import qual_agger

            conta_de_origem = do_pedido.get("account_id") or do_pedido.get("conta_exigida_id")
            if not conta_de_origem:
                raise ValueError("o cálculo de origem ainda não tem conta do Agger — espere o disparo")
            d = await asyncio.to_thread(qual_agger.decidir, self.repo.db, company_id=corretora,
                                        servico=str(do_pedido["servico"]), conta_de_origem_id=str(conta_de_origem))
            if d.recusa:
                raise ContaRecusada(d.recusa, regra=d.regra)
            conta_herdada = {"conta_exigida_id": d.conta_id, "conta_regra": d.regra,
                             "conta_fallback": bool(d.fallback), "conta_motivo": d.texto_para_o_banco() or None}
        agora = self._agora()
        novo = {
            **conta_herdada,
            "id": str(uuid.uuid4()), "pedido_id": str(origem["pedido_id"]), "solicitante_company_id": company_id,
            "company_id": corretora, "opcao": "ajuste", "origem_calculo_id": calculo_id,
            "coberturas": (_aplicar_ajuste(origem.get("coberturas") or {}, ajuste) if ramo == RAMO_AUTO
                           else _aplicar_ajuste_re(origem.get("coberturas") or {}, ajuste)),
            "ajuste": {"tipo": ajuste.tipo, "valor": ajuste.valor, "seguradora": ajuste.seguradora,
                       "versao_base": int(origem["versao"]), "negocio_ref": str(origem["negocio_ref"])},
            # SPEC-131-A: o recálculo de uma renovação fica na prioridade DELA (7), atrás da cotação
            "status": "na_fila", "prioridade": PRIORIDADE_DO_SERVICO.get(str(do_pedido.get("servico")),
                                                                         PRIORIDADE.get(str(ped.get("origem")), 5)),
            "expira_em": (agora + VALIDADE.get(str(ped.get("origem")), timedelta(hours=24))).isoformat(),
            "disponivel_em": agora.isoformat(),
        }
        gravado = await asyncio.to_thread(self.repo.inserir_calculo, novo)
        # F4 (costura): o motor só serve pedido `aberto` — o recálculo de um pedido já fechado o reabre
        await asyncio.to_thread(self.repo.reabrir_pedido, company_id=company_id, pedido_id=str(origem["pedido_id"]))
        return {"id": str(gravado.get("id") or novo["id"]), "corretora_company_id": corretora, "opcao": "ajuste",
                "origem_calculo_id": calculo_id}

    # ------------------------------------------------------------------ o PDF
    async def pdf(self, *, company_id: str, oferta_id: str) -> Optional[bytes]:
        """O PDF da oferta (a FICHA: "baixa o PDF" — conserto 129-B, juiz B2), lido do NOSSO bucket privado, onde o
        motor o copiou (`multicalculo/{corretora}/{calculo}/{oferta}.pdf`). Nunca o link do fornecedor.

        Quem pode: o SOLICITANTE do pedido (se a oferta é de outra corretora, só o canal com adesão ATIVA agora —
        a mesma regra do `consultar`) ou a CORRETORA de registro (o login dela calculou). Qualquer outro →
        `NaoEncontrado` (não diz se existe). Sem PDF copiado → None."""
        company_id = _uuid(company_id, "company_id")
        oferta_id = _uuid(oferta_id, "oferta_id")
        oferta = await asyncio.to_thread(self.repo.oferta_do_solicitante, company_id=company_id, oferta_id=oferta_id)
        if oferta and str(oferta.get("solicitante_company_id")) == company_id:
            dona = str(oferta.get("company_id"))
            if dona != company_id:
                tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id])
                if tipos.get(company_id) != KIND_CANAL or dona not in await asyncio.to_thread(
                        self.repo.adesoes_ativas, canal_company_id=company_id, corretoras=[dona]):
                    raise NaoEncontrado("oferta não encontrada")
        else:
            oferta = await asyncio.to_thread(self.repo.oferta_da_corretora, company_id=company_id,
                                             oferta_id=oferta_id)
            if not oferta or str(oferta.get("company_id")) != company_id:
                raise NaoEncontrado("oferta não encontrada")
        caminho = str(oferta.get("pdf_path") or "")
        esperado = f"multicalculo/{oferta.get('company_id')}/{oferta.get('calculo_id')}/{oferta.get('id')}.pdf"
        if not caminho:
            return None
        if caminho != esperado:
            # o caminho gravado não é o que o motor escreve para ESTA oferta: nunca se lê outro arquivo do bucket
            logger.warning("[MULTICALCULO] pdf_path fora do padrão na oferta %s — recusado", oferta_id)
            return None
        try:
            dados = await asyncio.to_thread(self.repo.baixar_pdf, caminho)
        except Exception as exc:  # noqa: BLE001 — o storage fora não derruba quem chama
            logger.warning("[MULTICALCULO] baixar o PDF falhou (%s)", type(exc).__name__)
            return None
        if not dados or dados[:4] != b"%PDF":
            return None
        return dados

    # ------------------------------------------------------------------ cancelar
    async def cancelar(self, *, company_id: str, pedido_id: str) -> int:
        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=pedido_id)
        if not ped:
            raise NaoEncontrado("pedido não encontrado")
        return await asyncio.to_thread(self.repo.cancelar, company_id=company_id, pedido_id=pedido_id)

    # ------------------------------------------------------------------ SPEC-130-A U3: a negociação
    # 🔴 Só a corretora DONA negocia (D-MC-63): o canal recebe a comissão como None e não decide margem alheia →
    # `{"status": "so_a_corretora_negocia"}`, ANTES de qualquer leitura de oferta ou efeito. A decisão é PURA
    # (`negociacao.py`); a porta autoriza, lê pela `consultar` e ENFILEIRA pela `recalcular` (que já existe).
    async def _negociacao_da_dona(self, *, company_id: str) -> Optional[Dict[str, Any]]:
        tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id])
        kind = tipos.get(company_id)
        if kind == KIND_CANAL:
            return {"status": "so_a_corretora_negocia",
                    "motivo": "a margem é da corretora: só ela negocia comissão e desconto (D-MC-63)"}
        if kind != KIND_CORRETORA:
            raise NaoAutorizado("só uma corretora cliente negocia")
        return None

    async def _config_e_andamento(self, *, company_id: str, pedido_id: str) -> Tuple[Dict[str, Any], "Andamento"]:
        andamento = await self.consultar(company_id=company_id, pedido_id=pedido_id)
        # SPEC-131-0 A (§5.3): o manual do SERVIÇO do pedido (o legado lê a base, como sempre)
        servico = await asyncio.to_thread(self.repo.servico_do_pedido, company_id=company_id, pedido_id=pedido_id)
        cfg = await self._carregar_cfg(company_id, servico)
        return cfg, andamento

    async def ordem_do_mais_barato(self, *, company_id: str, oferta_ref: Mapping[str, Any],
                                   fechamento: bool = False) -> Dict[str, Any]:
        """Os `Ajuste`s, na ordem D-MC-67, que a seguradora da oferta OBEDECE (desconto onde ela ignora a comissão —
        a lista vem da config). `oferta_ref = {"pedido_id", "oferta_id"}`; a oferta tem de ser DESTA corretora.
        `fechamento=True` inclui os degraus da alavanca de fechamento (D-MC-68 corrigida: sem aprovação humana)."""
        from app.services.multicalculo import negociacao

        company_id = _uuid(company_id, "company_id")
        if not isinstance(oferta_ref, Mapping):
            raise TypeError("oferta_ref = {'pedido_id': …, 'oferta_id': …}")
        pedido_id = _uuid(oferta_ref.get("pedido_id"), "pedido_id")
        oferta_id = _uuid(oferta_ref.get("oferta_id"), "oferta_id")
        recusa = await self._negociacao_da_dona(company_id=company_id)
        if recusa:
            return recusa
        cfg, andamento = await self._config_e_andamento(company_id=company_id, pedido_id=pedido_id)
        oferta = next((o for o in andamento.ofertas if str(o.get("id")) == oferta_id
                       and str(o.get("corretora_company_id")) == company_id), None)
        if oferta is None:
            raise NaoEncontrado("oferta não encontrada")
        passos = negociacao.ordem_do_mais_barato(oferta, config=cfg, fechamento=fechamento)
        return {"status": "ok", "ajustes": [p.ajuste for p in passos], "passos": [p.para_dict() for p in passos]}

    async def _enfileirar(self, *, company_id: str, plano: Mapping[str, Any]) -> Dict[str, Any]:
        tentativas = list(plano.get("tentativas") or ())
        feitos = await asyncio.gather(*(self.recalcular(company_id=company_id, calculo_id=t["origem_calculo_id"],
                                                        ajuste=t["ajuste"]) for t in tentativas),
                                      return_exceptions=True)
        enfileiradas, falhas = [], []
        for t, r in zip(tentativas, feitos):
            publico = {k: v for k, v in t.items() if k != "ajuste"}
            if isinstance(r, BaseException):
                if isinstance(r, (NaoAutorizado, OrigemRecusada)):
                    raise r
                falhas.append({**publico, "erro": type(r).__name__})
                continue
            enfileiradas.append({**publico, "calculo_id": str(r.get("id")), "repetido": bool(r.get("repetido"))})
        saida = {"status": "em_andamento" if enfileiradas else "sem_caminho", "tentativas": enfileiradas,
                 "falhas": falhas, "fechamento_disponivel": bool(plano.get("fechamento_disponivel")),
                 "custo": "1 recálculo da corretora inteira por tentativa"}
        if plano.get("melhor_parcial"):
            saida["melhor_parcial"] = plano["melhor_parcial"]
        return saida

    async def cotacao_alvo(self, *, company_id: str, pedido_id: str, alvo: float, seguradora: Any = None,
                           fechamento: bool = False,
                           tentativas_anteriores: Optional[Sequence[Mapping[str, Any]]] = None) -> Dict[str, Any]:
        """D-MC-72 "fecha por R$ X?": planeja (puro) e ENFILEIRA as tentativas pela `recalcular`, em paralelo.
        Devolve `em_andamento` com os cálculos; quem chama lê depois com `avaliar_cotacao_alvo`. Com
        `tentativas_anteriores` (o que a avaliação devolveu como `proxima_etapa`), enfileira a etapa ENCADEADA.
        D-MC-68 corrigida: a margem desce passo a passo SEM aprovação humana; os degraus abaixo de
        `comissao.autonomo_minimo` (a alavanca de fechamento) só entram com `fechamento=True` — o cliente sinalizou
        que fecha se melhorar; nunca abaixo do piso. `fechamento_disponivel` diz se a alavanca ainda está guardada."""
        from app.services.multicalculo import negociacao
        from app.services.multicalculo.comparacao import comparar

        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        try:
            alvo = float(alvo)
        except (TypeError, ValueError):
            raise ValueError("alvo precisa ser um número") from None
        if alvo <= 0:
            raise ValueError("alvo precisa ser positivo")
        recusa = await self._negociacao_da_dona(company_id=company_id)
        if recusa:
            return recusa
        cfg, andamento = await self._config_e_andamento(company_id=company_id, pedido_id=pedido_id)
        if tentativas_anteriores:
            avaliacao = await self._avaliar(company_id=company_id, andamento=andamento, cfg=cfg, alvo=alvo,
                                            tentativas=tentativas_anteriores, fechamento=fechamento)
            if avaliacao["status"] != "proxima_etapa":
                return avaliacao
            return await self._enfileirar(company_id=company_id, plano=avaliacao)
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=pedido_id)
        quadro = comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg,
                          ramo=int((ped or {}).get("ramo") or RAMO_AUTO))
        por_id = {str(o.get("id")): o for o in andamento.ofertas}
        candidatas = [por_id[e["oferta_id"]] for e in quadro.ranking(quadro.opcao_completa, company_id)
                      if e["oferta_id"] in por_id]
        plano = negociacao.planejar(candidatas, alvo=alvo, config=cfg, seguradora=seguradora, fechamento=fechamento)
        if plano["status"] != "planejado":
            return dict(plano)
        return await self._enfileirar(company_id=company_id, plano=plano)

    async def avaliar_cotacao_alvo(self, *, company_id: str, pedido_id: str, alvo: float,
                                   tentativas: Sequence[Mapping[str, Any]],
                                   fechamento: bool = False) -> Dict[str, Any]:
        """Lê as tentativas pela `consultar` e DECIDE (sem efeito): `em_andamento` (ainda calculando) · `chegou`
        (a de MAIOR comissão, margem antes de cobertura, cortes listados e se recomenda) · `proxima_etapa` (o plano
        encadeado — enfileira-se com `cotacao_alvo(tentativas_anteriores=…)`) · `sem_caminho` ("não recomendo")."""
        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        alvo = float(alvo)
        recusa = await self._negociacao_da_dona(company_id=company_id)
        if recusa:
            return recusa
        cfg, andamento = await self._config_e_andamento(company_id=company_id, pedido_id=pedido_id)
        return await self._avaliar(company_id=company_id, andamento=andamento, cfg=cfg, alvo=alvo,
                                   tentativas=tentativas, fechamento=fechamento)

    async def _avaliar(self, *, company_id: str, andamento: "Andamento", cfg: Mapping[str, Any], alvo: float,
                       tentativas: Sequence[Mapping[str, Any]], fechamento: bool) -> Dict[str, Any]:
        from app.services.multicalculo import negociacao

        status = {str(e.get("calculo_id")): e.get("status") for e in andamento.estados}
        meus = [t for t in tentativas if str(t.get("calculo_id")) in status]
        if not meus:
            raise NaoEncontrado("nenhuma tentativa deste pedido")
        pendentes = [t for t in meus if status.get(str(t["calculo_id"])) in negociacao.STATUS_PENDENTES]
        if pendentes:
            return {"status": "em_andamento", "pendentes": len(pendentes), "total": len(meus)}
        resultados = [{**dict(t), "oferta": negociacao.resultado_da_tentativa(t, andamento.ofertas,
                                                                              company_id=company_id, config=cfg)}
                      for t in meus]
        etapa = negociacao.proxima_etapa(resultados, alvo=alvo, config=cfg, fechamento=fechamento)
        if isinstance(etapa.get("escolhida"), dict):
            etapa["escolhida"] = {k: v for k, v in etapa["escolhida"].items() if k != "_oferta"}
        return etapa
