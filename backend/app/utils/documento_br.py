# -*- coding: utf-8 -*-
"""O CPF/CNPJ brasileiro: a regra do DÍGITO VERIFICADOR, pura — SPEC-131-A F2 (P-1310-02).

> **O TESTE DO PRODUTO:** 📊 a InfoCap devolve um cliente REAL para o CPF `00000000000` (BLOCO 0 §6.2 da 131-0,
> laudo da CorpAPI, 11/10). Um CPF zerado ou com um dígito trocado, consultado na InfoCap, mostra a apólice de OUTRA
> pessoa ao corretor — e, no canal, ao segurado. O documento inválido é barrado ANTES de qualquer consulta.

🔴 A régua MUDOU DE CASA (decisão do gerente da 131-A, 12/10): morava em `app/agents/tools/insurer_dispatch_tool.py`,
que importa `langchain_core` e, pelo pacote `app.agents`, o grafo inteiro do agente — a consulta à InfoCap
(`app/api/infocap_connector.py`) e os scripts não podem subir o agente para perguntar se onze dígitos fecham a conta.
Lá ficam os nomes de sempre (`cpf_valido`, `cnpj_valido`, `documento_br_valido`), REEXPORTADOS daqui: uma régua só.

⚠️ E ele não importa NADA do produto (o mesmo princípio de `app/telefone_br.py`).
"""
from __future__ import annotations

from typing import Any, Iterable

#: o motivo explícito que o ponto de consulta devolve (nunca o documento)
DOCUMENTO_INVALIDO = "documento_invalido"


class DocumentoInvalido(ValueError):
    """O CPF/CNPJ não fecha o dígito verificador. ⛔ A mensagem nunca traz o documento."""

    motivo = DOCUMENTO_INVALIDO

    def __init__(self) -> None:
        super().__init__("documento inválido: o CPF/CNPJ não fecha o dígito verificador")


def so_digitos(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _dv(numeros: Iterable[int], pesos: Iterable[int]) -> int:
    resto = sum(n * p for n, p in zip(numeros, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(valor: Any) -> bool:
    """CPF pelo DÍGITO VERIFICADOR, nunca pelo comprimento. `111.111.111-11` fecha a conta e não existe: todos os
    dígitos iguais são recusados (inclui `000.000.000-00`)."""
    d = [int(c) for c in so_digitos(valor)]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    return d[9] == _dv(d[:9], range(10, 1, -1)) and d[10] == _dv(d[:10], range(11, 1, -1))


def cnpj_valido(valor: Any) -> bool:
    """CNPJ pelo dígito verificador (o titular pode ser condomínio ou empresa). Todos iguais → recusado."""
    d = [int(c) for c in so_digitos(valor)]
    if len(d) != 14 or len(set(d)) == 1:
        return False
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return d[12] == _dv(d[:12], pesos) and d[13] == _dv(d[:13], [6] + pesos)


def documento_valido(doc: Any) -> bool:
    """CPF (11 dígitos) ou CNPJ (14), pelo dígito verificador. Pontuação não importa; letras não contam."""
    return cpf_valido(doc) or cnpj_valido(doc)


def exigir_documento_valido(doc: Any) -> str:
    """Os dígitos do documento — ou `DocumentoInvalido` (o ponto de consulta à InfoCap chama ANTES da rede)."""
    if not documento_valido(doc):
        raise DocumentoInvalido()
    return so_digitos(doc)
