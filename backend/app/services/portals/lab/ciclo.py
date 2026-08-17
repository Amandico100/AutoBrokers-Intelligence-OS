# -*- coding: utf-8 -*-
"""Ciclo de vida do endpoint e detector de drift — SPEC-077 Blocos 4 e 8.

O inferidor descobre. Este módulo decide **o que se pode fazer com o que foi
descoberto**, e avisa quando o portal muda por baixo.

🔴 A regra que dá sentido ao módulo inteiro
============================================
Descoberta automática, **sim**. Endpoint descoberto virar endpoint produtivo,
**não**.

    OBSERVED            o tráfego mostrou que existe
        ↓  (humano)
    CANDIDATE           alguém olhou e disse "parece útil"
        ↓  (replay verde)
    REPLAYED_READONLY   funciona contra fixture, sem tocar no portal
        ↓  (humano + canário read-only)
    APPROVED_READONLY   pode LER em produção
        ↓  (humano + canário transacional + guard nomeado)
    APPROVED_MATERIAL   pode ESCREVER

Cada seta com "(humano)" é uma pessoa decidindo. **Não existe função neste
módulo que atravesse duas setas de uma vez, e não existe caminho automático
para `APPROVED_MATERIAL`.** `promover()` recusa qualquer salto — e o teste
prova que recusa.

Por que o drift importa mais que parece
========================================
📊 Hoje, quando um portal muda, o AutoBrokers descobre por `element not found`
— no meio de um acionamento, com um segurado esperando. O detector compara o
contrato aprovado com o candidato novo e diz **o que** mudou, **antes** de a
journey quebrar.

E a classificação não é decorativa: mudança aditiva pode seguir; mudança que
quebra requisição ou resposta **fecha a capacidade** (fail-closed) em vez de
deixar a journey descobrir sozinha.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.portals.lab.inferir import (
    APPROVED_MATERIAL, APPROVED_READONLY, CANDIDATE, NEEDS_MORE_SAMPLES,
    OBSERVED, REJECTED, REPLAYED_READONLY,
)

# A escada, em ordem. Índice maior = mais poder.
ESCADA: Tuple[str, ...] = (
    OBSERVED, CANDIDATE, REPLAYED_READONLY, APPROVED_READONLY, APPROVED_MATERIAL,
)

# O que cada degrau exige para ser alcançado. Chaves de evidência, não frases:
# uma exigência escrita em prosa vira interpretação, e interpretação vira
# "acho que já dá".
EXIGENCIAS: Dict[str, Tuple[str, ...]] = {
    CANDIDATE: ("revisado_por_humano",),
    REPLAYED_READONLY: ("revisado_por_humano", "replay_verde"),
    APPROVED_READONLY: ("revisado_por_humano", "replay_verde",
                        "canario_readonly_verde", "host_allowlisted"),
    APPROVED_MATERIAL: ("revisado_por_humano", "replay_verde",
                        "canario_readonly_verde", "host_allowlisted",
                        "canario_transacional_verde", "guard_nomeado",
                        "idempotencia_definida", "aprovacao_do_founder"),
}


class SaltoProibido(Exception):
    """Tentativa de pular degrau da escada."""


@dataclass
class Promocao:
    permitida: bool
    de: str
    para: str
    motivo: str = ""
    faltam: List[str] = field(default_factory=list)


def promover(estado_atual: str, para: str,
             evidencias: Optional[Dict[str, Any]] = None) -> Promocao:
    """Pode este endpoint subir para `para`? `(permitida, motivo, faltam)`.

    Três recusas, e cada uma existe por um motivo diferente:

    **Salto de degrau.** Ir de `OBSERVED` direto a `APPROVED_MATERIAL` é o
    pedido que alguém faz numa sexta-feira à noite. A escada não é burocracia:
    cada degrau produz a evidência que o seguinte exige.

    **Evidência ausente.** Ausência de evidência conta como não provado, nunca
    como "provavelmente ok". É a mesma regra do `prontidao.py` da SPEC-075.

    **Descida.** Rebaixar é sempre permitido, e de propósito: quando o drift
    quebra um contrato, fechar a capacidade tem de ser barato.
    """
    evid = evidencias or {}
    if estado_atual not in ESCADA or para not in ESCADA:
        return Promocao(False, estado_atual, para,
                        motivo=f"estado desconhecido: {estado_atual} -> {para}")

    i_de, i_para = ESCADA.index(estado_atual), ESCADA.index(para)

    if i_para <= i_de:
        # Descer, ou ficar. Sempre permitido.
        return Promocao(True, estado_atual, para,
                        motivo="rebaixamento ou permanencia: sempre permitido")

    if i_para - i_de > 1:
        return Promocao(
            False, estado_atual, para,
            motivo=(f"salto proibido: de `{estado_atual}` so se sobe para "
                    f"`{ESCADA[i_de + 1]}`. Cada degrau produz a evidencia que "
                    "o seguinte exige"))

    faltam = [e for e in EXIGENCIAS.get(para, ()) if not evid.get(e)]
    if faltam:
        return Promocao(False, estado_atual, para,
                        motivo=f"faltam {len(faltam)} evidencia(s)", faltam=faltam)

    return Promocao(True, estado_atual, para, motivo="todas as evidencias presentes")


def pode_usar_em_producao(estado: str, *, para_escrever: bool = False) -> bool:
    """A pergunta que o adapter faz antes de chamar.

    Leitura exige `APPROVED_READONLY`. Escrita exige `APPROVED_MATERIAL` — e
    nada abaixo, nunca. Estado desconhecido é `False`: um endpoint que não se
    sabe classificar não se usa.
    """
    if para_escrever:
        return estado == APPROVED_MATERIAL
    return estado in (APPROVED_READONLY, APPROVED_MATERIAL)


# --------------------------------------------------------------------------
# Drift — SPEC-077 Bloco 8
# --------------------------------------------------------------------------
SEM_MUDANCA = "none"
ADITIVA = "additive"
QUEBRA_REQUISICAO = "breaking_request"
QUEBRA_RESPOSTA = "breaking_response"
AUTH_MUDOU = "auth_changed"
ENDPOINT_SUMIU = "endpoint_removed"
STATUS_MUDOU = "status_semantics_changed"
DESCONHECIDO = "unknown"

# Classes que FECHAM a capacidade. Ordem de gravidade crescente.
QUEBRAM: Tuple[str, ...] = (QUEBRA_REQUISICAO, QUEBRA_RESPOSTA, AUTH_MUDOU,
                            ENDPOINT_SUMIU, DESCONHECIDO)


@dataclass
class Drift:
    classe: str
    endpoint: str
    detalhes: List[str] = field(default_factory=list)

    @property
    def quebra(self) -> bool:
        return self.classe in QUEBRAM


def _propriedades(esquema: Any) -> Dict[str, Any]:
    if isinstance(esquema, dict):
        return esquema.get("properties") or {}
    return {}


def _obrigatorios(esquema: Any) -> Set[str]:
    if isinstance(esquema, dict):
        return set(esquema.get("required") or [])
    return set()


def _tipo(esquema: Any) -> Any:
    if isinstance(esquema, dict):
        return esquema.get("type")
    return None


def comparar_operacao(aprovada: Dict[str, Any],
                      nova: Dict[str, Any],
                      *, endpoint: str = "") -> Drift:
    """Compara a operação aprovada com a recém-observada.

    🔴 A assimetria é intencional e é o coração do detector:

    **Campo que SUMIU da resposta quebra.** A journey pode estar lendo ele.

    **Campo que APARECEU na resposta é aditivo.** Ninguém lê o que não sabia
    que existia.

    **Campo obrigatório NOVO na requisição quebra.** A journey não vai mandar.

    **Campo obrigatório que virou opcional é aditivo.** Mandar a mais não dói.

    Confundir esses quatro faria o detector gritar em toda evolução normal do
    portal — e um alarme que sempre toca é um alarme desligado.
    """
    detalhes: List[str] = []

    # -- autenticação -----------------------------------------------------
    auth_antes = {h for h in (aprovada.get("x-headers-auth") or [])}
    auth_agora = {h for h in (nova.get("x-headers-auth") or [])}
    if auth_antes and auth_agora and auth_antes != auth_agora:
        return Drift(AUTH_MUDOU, endpoint,
                     [f"cabecalho de autorizacao mudou: "
                      f"{sorted(auth_antes)} -> {sorted(auth_agora)}"])

    # -- requisição -------------------------------------------------------
    esq_req_antes = (((aprovada.get("requestBody") or {}).get("content") or {})
                     .get("application/json") or {}).get("schema") or {}
    esq_req_agora = (((nova.get("requestBody") or {}).get("content") or {})
                     .get("application/json") or {}).get("schema") or {}
    novos_obrigatorios = _obrigatorios(esq_req_agora) - _obrigatorios(esq_req_antes)
    if novos_obrigatorios:
        return Drift(QUEBRA_REQUISICAO, endpoint,
                     [f"campo obrigatorio novo na requisicao: {c}"
                      for c in sorted(novos_obrigatorios)])

    # -- resposta ---------------------------------------------------------
    resp_antes = aprovada.get("responses") or {}
    resp_agora = nova.get("responses") or {}

    sucesso_antes = {s for s in resp_antes if str(s).startswith("2")}
    sucesso_agora = {s for s in resp_agora if str(s).startswith("2")}
    if sucesso_antes and not sucesso_agora:
        return Drift(STATUS_MUDOU, endpoint,
                     [f"nao ha mais resposta de sucesso: antes {sorted(sucesso_antes)}, "
                      f"agora {sorted(resp_agora)}"])

    for status in sorted(sucesso_antes & sucesso_agora):
        e_antes = (((resp_antes[status] or {}).get("content") or {})
                   .get("application/json") or {}).get("schema") or {}
        e_agora = (((resp_agora[status] or {}).get("content") or {})
                   .get("application/json") or {}).get("schema") or {}
        if not e_antes or not e_agora:
            continue

        t_antes, t_agora = _tipo(e_antes), _tipo(e_agora)
        if t_antes and t_agora and t_antes != t_agora:
            return Drift(QUEBRA_RESPOSTA, endpoint,
                         [f"o tipo da resposta {status} mudou: {t_antes} -> {t_agora}"])

        sumiram = set(_propriedades(e_antes)) - set(_propriedades(e_agora))
        if sumiram:
            return Drift(QUEBRA_RESPOSTA, endpoint,
                         [f"campo sumiu da resposta {status}: {c}"
                          for c in sorted(sumiram)])

        apareceram = set(_propriedades(e_agora)) - set(_propriedades(e_antes))
        if apareceram:
            detalhes += [f"campo novo na resposta {status}: {c}"
                         for c in sorted(apareceram)]

    novos_status = set(resp_agora) - set(resp_antes)
    if novos_status:
        detalhes += [f"status novo observado: {s}" for s in sorted(novos_status)]

    return Drift(ADITIVA if detalhes else SEM_MUDANCA, endpoint, detalhes)


def comparar_contratos(aprovado: Dict[str, Any],
                       candidato: Dict[str, Any]) -> List[Drift]:
    """Compara dois documentos OpenAPI e devolve os drifts, os que quebram primeiro.

    Endpoint que sumiu é reportado, mas com uma ressalva honesta no detalhe: o
    tráfego novo pode simplesmente não ter passado por ele. Sumir do trace não
    é o mesmo que sumir do portal — e tratar os dois como iguais fecharia
    capacidade por causa de uma captura curta.
    """
    saida: List[Drift] = []
    paths_a = aprovado.get("paths") or {}
    paths_b = candidato.get("paths") or {}

    for caminho in sorted(paths_a):
        for metodo in sorted(paths_a[caminho] or {}):
            chave = f"{metodo.upper()} {caminho}"
            op_a = (paths_a[caminho] or {})[metodo]
            op_b = ((paths_b.get(caminho) or {}) or {}).get(metodo)
            if op_b is None:
                saida.append(Drift(
                    ENDPOINT_SUMIU, chave,
                    ["nao apareceu no trafego novo. ATENCAO: pode ser captura "
                     "curta, nao remocao — conferir antes de fechar a capacidade"]))
                continue
            saida.append(comparar_operacao(op_a, op_b, endpoint=chave))

    for caminho in sorted(paths_b):
        for metodo in sorted(paths_b[caminho] or {}):
            if metodo not in (paths_a.get(caminho) or {}):
                saida.append(Drift(ADITIVA, f"{metodo.upper()} {caminho}",
                                   ["endpoint novo, nunca aprovado"]))

    saida.sort(key=lambda d: (not d.quebra, d.endpoint))
    return saida


def veredito_de_drift(drifts: List[Drift]) -> Tuple[str, str]:
    """`(classe_pior, frase)` — o que fazer com o conjunto.

    Fail-closed: **um** drift que quebra fecha a capacidade, por mais aditivos
    que sejam os outros. Média de gravidade seria a forma mais elegante de
    ignorar o único que importa.
    """
    quebram = [d for d in drifts if d.quebra]
    if quebram:
        return (quebram[0].classe,
                f"🔴 {len(quebram)} mudanca(s) que QUEBRAM. A capacidade deve ser "
                f"fechada ate revisao: {quebram[0].endpoint} — "
                f"{'; '.join(quebram[0].detalhes[:2])}")
    aditivos = [d for d in drifts if d.classe == ADITIVA]
    if aditivos:
        return (ADITIVA,
                f"{len(aditivos)} mudanca(s) aditiva(s). Pode seguir; vale "
                "registrar para o proximo contrato")
    return SEM_MUDANCA, "nenhuma mudanca detectada"
