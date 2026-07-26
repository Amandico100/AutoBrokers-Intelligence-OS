"""Redacao de PII — autoridade unica do pipeline de inteligencia. §30.

Por que este modulo existe separado
-----------------------------------
A SPEC-058 ja tinha uma redacao dentro da Auxiliary Factory. Manter duas
listas de padroes seria o pior arranjo possivel: as duas divergem com o tempo,
e a que fica para tras e justamente a que deixa passar o CPF. Aqui fica a
lista **unica**; a Factory delega para ca.

O modulo nao importa nada do projeto de proposito — so `re`. Redacao e a
ultima linha entre um dado de segurado e um painel lido pela plataforma; ela
precisa poder ser carregada e testada sem subir banco, Redis ou LLM.

Limite honesto
--------------
Isto e redacao por padrao, nao deteccao semantica. Nome proprio solto no meio
de uma frase continua passando. Por isso a regra do produto nao e "redigiu,
logo pode ir para o global": e **resumo agregado no global, texto literal so
dentro do tenant** (§18.5). A redacao reduz o dano; o escopo e que o evita.
"""

from __future__ import annotations

import re

# Ordem importa: o mais especifico primeiro. `apolice nº 4471-XY` precisa ser
# capturado antes de o padrao de telefone tentar a sorte com os digitos.
PADROES_PII: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[CNPJ]"),
    (re.compile(r"\bap[óo]lice\s+(?:n[º°.]?\s*)?[\w.\-/]{4,}", re.I), "apólice [NUMERO]"),
    (re.compile(r"\b(?:sinistro|aviso)\s+(?:n[º°.]?\s*)?[\w.\-/]{4,}", re.I), "sinistro [NUMERO]"),
    (re.compile(r"\b[A-Z]{3}-?\d[A-Z\d]\d{2}\b"), "[PLACA]"),
    (re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"), "[EMAIL]"),
    (re.compile(r"(?:\+?55\s*)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}"), "[TELEFONE]"),
    # Cartao: 13 a 16 digitos em grupos. Vem DEPOIS do telefone porque o
    # padrao de telefone e mais restrito e nao rouba estes.
    (re.compile(r"\b(?:\d[ .\-]?){13,16}\b"), "[CARTAO]"),
    (re.compile(r"\bCEP\s*:?\s*\d{5}-?\d{3}\b", re.I), "[CEP]"),
    (re.compile(r"\b\d{11}\b"), "[DOCUMENTO]"),
]

LIMITE_PADRAO = 2000


def redigir(texto: str, limite: int = LIMITE_PADRAO) -> str:
    """Remove PII conhecida e corta no limite. Nunca levanta excecao.

    Falhar aqui nao pode derrubar o pipeline: um sinal a menos e um problema;
    um worker morto por causa de uma regex e um problema maior.
    """
    saida = texto or ""
    for padrao, marca in PADROES_PII:
        try:
            saida = padrao.sub(marca, saida)
        except Exception:  # noqa: BLE001
            continue
    return saida.strip()[:limite]


def contem_pii(texto: str) -> bool:
    """`True` se algum padrao conhecido casar. Usado nos gates de publicacao."""
    alvo = texto or ""
    return any(p.search(alvo) for p, _ in PADROES_PII)


def relatorio_pii(texto: str) -> dict:
    """O que foi encontrado, por marca. Vai para `pii_check` do candidato.

    Guardar a CONTAGEM e nao o trecho e deliberado: um relatorio de PII que
    guarda o CPF encontrado nao protege ninguem.
    """
    alvo = texto or ""
    achados: dict[str, int] = {}
    for padrao, marca in PADROES_PII:
        n = len(padrao.findall(alvo))
        if n:
            achados[marca] = achados.get(marca, 0) + n
    return {"limpo": not achados, "achados": achados}


def resumo_seguro(texto: str, limite: int = 220) -> str:
    """Resumo curto e redigido, pronto para aparecer em briefing ou painel."""
    limpo = redigir(texto, limite=limite + 40)
    if len(limpo) <= limite:
        return limpo
    return limpo[: limite - 1].rstrip() + "…"
