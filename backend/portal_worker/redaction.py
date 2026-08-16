# -*- coding: utf-8 -*-
"""O redator único do Portal Worker — SPEC-073 Bloco H.

Existe UM sanitizador porque a alternativa já foi tentada em outros lugares do
produto: cada peça com a sua regrinha, e o dia em que alguém acrescenta um
campo novo só uma das cópias aprende. Profiler, evidence, trace, log e fixture
passam por aqui.

O que ele mascara
=================
    segredo ....... Authorization · Cookie · Set-Cookie · JWT · api key ·
                    senha · token de sessão · secret · proxy credential
    PII ........... CPF · CNPJ · telefone · e-mail · placa · CEP ·
                    linha digitável · cartão

O que ele NÃO faz
=================
Ele não apaga a informação de que o campo existia. `Authorization` vira
`"<redacted:authorization>"`, não some — porque um artefato que esconde a
própria existência do header ensina o leitor errado a procurar no lugar errado.

Para depuração, prefira a FORMA ao conteúdo
===========================================
`shape_of()` devolve `{"cpf": "<string:11>", "itens": "<array:21>"}`. Isso é o
suficiente para entender um contrato de API e insuficiente para identificar
alguém — que é exatamente o ponto de equilíbrio que a SPEC-073 D3 pede.

🔴 A regra que decide os casos difíceis: **na dúvida, mascare.** Um artefato de
diagnóstico com uma placa a menos continua servindo para diagnosticar. Um
artefato com uma placa a mais é um vazamento que ninguém revisa depois.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List

# --------------------------------------------------------------------------
# Cabeçalhos e chaves cujo VALOR nunca é persistido, em nenhum modo.
# --------------------------------------------------------------------------
# Comparação por substring em minúsculas: `x-amz-security-token` casa `token`,
# `proxy-authorization` casa `authorization`. Lista curta de propósito — o que
# pega o resto é o casamento por substring, não o tamanho da lista.
CHAVES_SENSIVEIS: tuple[str, ...] = (
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "apikey",
    "api_key",
    "proxy-authorization",
    "client-secret",
    "client_secret",
    "access-token",
    "access_token",
    "refresh-token",
    "refresh_token",
    "id_token",
    "bearer",
    "jwt",
    "senha",
    "password",
    "passwd",
    "secret",
    "credential",
    "storage_state",
    "session_storage",
    "x-csrf-token",
    "x-xsrf-token",
    "token_autorizacao",
)

MARCA = "<redacted:{}>"

# --------------------------------------------------------------------------
# Padrões de PII. Ordem importa: o mais específico primeiro, senão o genérico
# come o específico (a linha digitável vira "vários números soltos").
# --------------------------------------------------------------------------
_PADROES: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    # linha digitável de boleto: 47-48 dígitos, com ou sem separador
    ("linha_digitavel", re.compile(r"\b(?:\d[\s.]?){47,48}\b")),
    # JWT — três blocos base64url separados por ponto
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")),
    # cartão: 13 a 19 dígitos em grupos de 4
    ("cartao", re.compile(r"\b(?:\d{4}[\s.-]?){3,4}\d{1,4}\b")),
    ("cnpj", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")),
    ("cpf", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # telefone BR com DDD, com ou sem +55, 8 ou 9 dígitos
    ("telefone", re.compile(r"(?:\+?55[\s-]?)?\(?\b\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}\b")),
    # placa Mercosul (ABC1D23) e antiga (ABC-1234 / ABC1234)
    ("placa", re.compile(r"\b[A-Z]{3}[\s-]?\d[A-Z0-9]\d{2}\b", re.IGNORECASE)),
    ("cep", re.compile(r"\b\d{5}-?\d{3}\b")),
)


def digest(valor: str) -> str:
    """8 hex do sha256 — estável entre execuções, inútil para reidentificar.

    Serve ao caso real de depuração: *"o CPF que entrou no passo 3 é o mesmo que
    saiu no passo 5?"* se responde comparando dois hashes, sem nunca escrever o
    número. O profiler usa a mesma função para a assinatura de tela, para que
    exista **um** jeito de encurtar identidade no worker inteiro.
    """
    return hashlib.sha256(valor.encode("utf-8", "ignore")).hexdigest()[:8]


# Nome antigo, mantido enquanto houver chamador interno.
_digest = digest


def chave_e_sensivel(chave: Any) -> bool:
    """`Authorization`, `authorization` e `X-Proxy-Authorization` são a mesma coisa."""
    k = str(chave or "").strip().lower()
    if not k:
        return False
    return any(s in k for s in CHAVES_SENSIVEIS)


def redigir_texto(texto: Any, *, com_hash: bool = False) -> str:
    """Mascara PII dentro de uma string livre.

    `com_hash=True` acrescenta o digest ao rótulo — `<cpf:9f2a1c04>` — para o
    caso em que se precisa saber se dois valores mascarados são o MESMO valor.
    """
    if texto is None:
        return ""
    s = str(texto)
    if not s:
        return s
    for nome, padrao in _PADROES:
        def _troca(m: "re.Match[str]", _n: str = nome) -> str:
            bruto = m.group(0)
            if com_hash:
                return f"<{_n}:{_digest(bruto)}>"
            return MARCA.format(_n)
        s = padrao.sub(_troca, s)
    return s


def redigir(valor: Any, *, com_hash: bool = False, _prof: int = 0) -> Any:
    """Percorre dict/list/str e devolve a mesma forma, sem segredo nem PII.

    Chave sensível some pelo VALOR, não pela chave: quem lê o artefato continua
    sabendo que havia um `Authorization` ali.
    """
    if _prof > 12:  # laço de estrutura patológica não derruba o worker
        return "<profundidade_excedida>"
    if isinstance(valor, dict):
        saida: Dict[str, Any] = {}
        for k, v in valor.items():
            # 🔴 Booleano não carrega segredo. `{"password": true}` é um
            # diagnóstico ("o campo de senha existe na tela"), não uma senha —
            # e mascará-lo custava informação sem proteger nada. Medido no
            # canário P-186: `login_fields_found.password` virou
            # `<redacted:password>` e o operador perdeu o diagnóstico.
            if chave_e_sensivel(k) and not isinstance(v, bool):
                saida[str(k)] = MARCA.format(str(k).strip().lower())
            else:
                saida[str(k)] = redigir(v, com_hash=com_hash, _prof=_prof + 1)
        return saida
    if isinstance(valor, (list, tuple)):
        return [redigir(v, com_hash=com_hash, _prof=_prof + 1) for v in valor]
    if isinstance(valor, str):
        return redigir_texto(valor, com_hash=com_hash)
    if isinstance(valor, (int, float, bool)) or valor is None:
        return valor
    return redigir_texto(str(valor), com_hash=com_hash)


def redigir_headers(headers: Any) -> Dict[str, str]:
    """Headers de rede: mantém o nome, nunca o valor sensível."""
    if not isinstance(headers, dict):
        return {}
    saida: Dict[str, str] = {}
    for k, v in headers.items():
        nome = str(k)
        if chave_e_sensivel(nome):
            saida[nome] = MARCA.format(nome.strip().lower())
        else:
            saida[nome] = redigir_texto(v)
    return saida


def shape_of(valor: Any, *, _prof: int = 0) -> Any:
    """A FORMA do payload, sem um único dado real — SPEC-073 D3.

    `{"cpf": "12345678901", "itens": [1,2,3]}`
        vira
    `{"cpf": "<string:11>", "itens": "<array:3>"}`

    É o que permite entender uma API candidata sem versionar o cliente dela.
    """
    if _prof > 8:
        return "<profundidade_excedida>"
    if isinstance(valor, dict):
        return {str(k): ("<redacted>" if chave_e_sensivel(k)
                         else shape_of(v, _prof=_prof + 1))
                for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        if not valor:
            return "<array:0>"
        # a forma do primeiro item representa a lista; o tamanho vai junto
        return {"__array__": len(valor), "__item__": shape_of(valor[0], _prof=_prof + 1)}
    if isinstance(valor, bool):
        return "<bool>"
    if isinstance(valor, int):
        return "<int>"
    if isinstance(valor, float):
        return "<float>"
    if valor is None:
        return "<null>"
    return f"<string:{len(str(valor))}>"


def tem_vazamento(valor: Any) -> List[str]:
    """Devolve os TIPOS de segredo/PII encontrados. Vazio = limpo.

    Usado pelos testes-armadilha do Gate H e pelo sanitizador de fixture: um
    guarda que não consegue apontar O QUE vazou não ajuda a consertar.
    """
    achados: List[str] = []

    def _anda(v: Any, prof: int = 0) -> None:
        if prof > 12:
            return
        if isinstance(v, dict):
            for k, sub in v.items():
                if chave_e_sensivel(k) and sub not in (None, ""):
                    if not (isinstance(sub, str) and sub.startswith("<redacted")):
                        achados.append(str(k).strip().lower())
                _anda(sub, prof + 1)
        elif isinstance(v, (list, tuple)):
            for sub in v:
                _anda(sub, prof + 1)
        elif isinstance(v, str):
            for nome, padrao in _PADROES:
                if padrao.search(v):
                    achados.append(nome)

    _anda(valor)
    return sorted(set(achados))


# --------------------------------------------------------------------------
# O envelope da evidência — SPEC-073 H1/H2
# --------------------------------------------------------------------------
# 🔴 Esta separação nasceu de uma REGRESSÃO REAL, achada pelo canário P-186 em
# 16/08/2026, e vale escrever por extenso porque a lição não é óbvia.
#
# A primeira versão do worker envolvia a evidência INTEIRA em `redigir()`. O
# resultado, medido em produção:
#
#     inadimplentes[0].recibo         -> "<redacted:...>"
#     inadimplentes[0].apolice_susep  -> "<redacted:...>"
#     inadimplentes[0].cpf_cnpj       -> "<redacted:...>"
#
# `recibo` é a chave estável do item na fila, o nome do PDF no bucket
# (`boleto-{recibo}.pdf`) e a chave anti-duplicação em `billing_sent_log`.
# Mascará-lo faria TODA execução concluir que nada foi enviado — e o segurado
# receberia a mesma cobrança de novo, e de novo.
#
# A proteção teria produzido o pior desfecho do sistema.
#
# A distinção que faltava:
#
#     PAYLOAD DE TRABALHO   o que a journey capturou e o serviço CONSOME.
#                           É o dado da corretora, sobre o cliente dela, que ela
#                           tem direito e necessidade de processar. Sai intacto.
#
#     SUPERFÍCIE DE         profiler, trace, log, discovery, bloqueios — tudo
#     DIAGNÓSTICO           que existe para ALGUÉM LER, e que a SPEC-073 criou.
#                           Passa pelo redator.
#
# A SPEC-073 H2 sempre disse "um único sanitizador para profiler/logs". Eu é que
# apliquei largo demais.
# --------------------------------------------------------------------------
CHAVES_DE_DIAGNOSTICO: tuple[str, ...] = (
    "runtime", "execution", "profiler", "discovery", "blocked_actions",
    "acoes_recusadas", "trace", "debug_dom", "mdselect_overlay",
    "security_stop", "recovery", "final_state",
)


def redigir_envelope(evidence: Any) -> Any:
    """Sanitiza SÓ as superfícies de diagnóstico. O trabalho passa intacto.

    Usada no caminho de escrita do worker. O que a journey capturou para o
    serviço consumir continua exatamente como ela escreveu — inclusive antes
    desta SPEC existir, que é o que torna a mudança zero-regressão.
    """
    if not isinstance(evidence, dict):
        return evidence
    saida: Dict[str, Any] = {}
    for k, v in evidence.items():
        if str(k) in CHAVES_DE_DIAGNOSTICO:
            saida[str(k)] = redigir(v)
        else:
            saida[str(k)] = v
    return saida


def linha_de_log(**campos: Any) -> str:
    """`[PORTAL] job=... portal=... layer=api status=200` — nunca com segredo.

    Todo valor passa pelo redator antes de virar texto, então um campo novo
    acrescentado com pressa não vira o vazamento da próxima semana.
    """
    partes: Iterable[str] = (
        f"{k}={redigir_texto(v)}" for k, v in campos.items() if v is not None
    )
    return " ".join(partes)
