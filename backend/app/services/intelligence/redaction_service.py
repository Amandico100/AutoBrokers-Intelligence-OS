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


#: As marcas que `redigir` deixa no lugar da PII — lidas de `PADRÕES_PII` para
#: que a lista **não possa divergir** da que produz as marcas.
MARCAS = tuple(sorted({m for _, m in PADROES_PII}))

#: 🔴 O CURINGA QUE DEVOLVE O CASAMENTO. Ver `ancora_permissiva`.
#:
#: ⚠️ `{0,40}` e não `*`: um curinga ilimitado no meio de uma âncora casa
#: qualquer coisa entre os pedaços fixos, e a âncora deixa de distinguir uma tela
#: da outra. Quarenta cobre CPF, telefone, placa e apólice com folga.
_CURINGA = r".{0,40}"

#: Quantos caracteres FIXOS a âncora precisa ter para identificar uma tela.
#:
#: ⚠️ Não é sobre privacidade — é sobre servir. Uma âncora de três letras casa
#: meia URA, e o overlay dela responde por telas que ninguém examinou.
_MINIMO_FIXO = 12

_MARCA_NO_TEXTO = re.compile(r"(" + "|".join(
    re.escape(m) for m in sorted({m for _, m in PADROES_PII}, key=len, reverse=True)
) + r")")


def ancora_permissiva(texto: str, limite: int = 60) -> str:
    """Uma âncora regex a partir de texto **mascarado**, que ainda casa o texto CRU.

    🔴 ESTE É O GATE ② DA SPEC-087 EM CÓDIGO, e sem ele mascarar quebra o
    produto.

    O escritor de âncora fazia `re.escape(texto[:60])` sobre o texto **cru** —
    tráfego de uma corretora indo para uma tabela **global**, lida por todas.
    Mascarar antes resolve o vazamento e cria outro problema::

        cru        "Digite seu CPF 123.456.789-00 para continuar"
        mascarado  "Digite seu CPF [CPF] para continuar"
        re.escape  "Digite\ seu\ CPF\ \[CPF\]\ para\ continuar"   ← NÃO casa nada

    ⚠️ **Um mascarador que troca o menu por `{{texto}}` é perfeito em privacidade
    e inútil como âncora.** Então a marca volta a ser um curinga: o que é fixo na
    tela continua fixo na âncora, e só o que era PII vira `.{0,40}`.

    ⛔ E o que SAI daqui não contém PII: os pedaços fixos são o texto da
    seguradora; o dado da pessoa virou curinga.
    """
    mascarado = redigir(str(texto or "").strip(), limite=limite)[:limite]
    if not mascarado:
        return ""
    partes = [p for p in _MARCA_NO_TEXTO.split(mascarado) if p]

    # ⚠️ CURINGA NA BORDA NÃO ADICIONA NADA — e na borda ESQUERDA, tira.
    #
    # `re.search` já aceita qualquer coisa antes e depois da âncora, então um
    # curinga na ponta é ruído. Ele só some do fim; **na frente, ele significa
    # outra coisa**: que a tela COMEÇA com PII, e portanto o que sobrou da
    # máscara é um final genérico, sem fronteira à esquerda.
    while partes and partes[-1] in MARCAS:
        partes.pop()
    if partes and partes[0] in MARCAS:
        # 🔴 A IDENTIDADE DESTA TELA ERA A PII, E ELA SAIU. NÃO HÁ ÂNCORA.
        #
        # 📊 Medido ao escrever o gate ②c: `"123.456.789-00 confirmado com
        # sucesso"` viraria `.{0,40}\ confirmado\ com\ sucesso` — que casa
        # **"O protocolo 9988776655 confirmado com sucesso"**, uma tela
        # completamente diferente. O overlay sequestraria a resposta dela.
        #
        # ⚠️ **Mascarar pode custar a âncora, e quando custa, não se cria âncora.**
        # Âncora nenhuma é melhor que âncora que rouba tela alheia — e quem chama
        # já pula a vazia (`if not anchor: continue`).
        return ""

    fixos = sum(len(p) for p in partes if p not in MARCAS)
    if fixos < _MINIMO_FIXO:
        # O que sobrou não identifica tela nenhuma.
        return ""
    return "".join(_CURINGA if p in MARCAS else re.escape(p) for p in partes)


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
