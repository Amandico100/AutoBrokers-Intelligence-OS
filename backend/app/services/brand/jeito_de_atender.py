"""O **Jeito de atender** da corretora — SPEC-098 §R1, R3, R4, R5.

Uma peça só, com quatro funções puras. Não é motor: não tem estado, não fala
com banco, não chama modelo. Quem grava é o `BrandCaptureService` (§R13 —
nenhum "Soul service" nasce ao lado do que já existe).

Três coisas que esta peça garante, e por que cada uma existe
------------------------------------------------------------
1. **Escolha fechada, nunca texto livre para o tom.** As cinco escolhas
   (`ESCOLHAS`) têm enum e rótulo em português. 📊 A taxonomia saiu do NOSSO
   acervo (Resulta abre afetiva com emoji; AutoFleet trata por Sr/Sra e explica
   procedimento — SPEC-098 §1.2), não do Intercom: o que copiamos de lá é a
   FORMA (campo estruturado governa comportamento observável), não os rótulos.

2. **O que entra no prompt é varrido, e nada é descartado em silêncio.** Três
   camadas sobre o texto CRU (§R4):

   ```
   ① ESTRUTURAL  tira a CONSTRUÇÃO e mantém a PROSA: {{ }}, < >, cercas ```,
                 http(s)://, data:, e linha que abre com system:/assistant:/
                 user:/###. Item que ficar vazio sai.
   ② TETO        trunca no limite da R3 com reticências — nunca descarta.
   ③ SEMÂNTICO   NÃO descarta: SINALIZA (`sinalizado: true`). O item só entra
                 no prompt com `confirmado: true` da administradora.
   ```

   🔴 A camada ③ não descarta porque a régua de injeção mataria princípio
   legítimo em silêncio — "explica antes de **enviar** o documento" é uma regra
   de atendimento perfeitamente honesta que casa a lista. Silêncio aqui é o
   defeito, não a segurança.

3. **A defesa REAL é estrutural, não é esta prosa.** O jeito nunca chega a
   `resolve_active_capabilities` (`capability_resolver.py:66`) — é lá que se
   decide o que o agente PODE fazer, e o guarda [G3] prova isso ligando o jeito
   ao resolvedor de propósito (mutação M6-bis) para ver a asserção ficar
   vermelha. Um bloco de texto dizendo "não amplie poder" não é gate.
"""

from __future__ import annotations

import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# R3 — as cinco escolhas fechadas e as quatro listas curtas
# ---------------------------------------------------------------------------

#: enum → rótulo humano em português. O rótulo é o que vai para o prompt e para
#: a tela; a CHAVE é o que fica gravado (R11 da 097: nenhuma chave de código
#: aparece para a corretora).
ESCOLHAS: dict[str, dict[str, str]] = {
    "saudacao": {
        "afetiva": "afetiva (\"Oi! Tudo bem?\")",
        "cordial": "cordial (\"Bom dia, tudo bem?\")",
        "direta": "direta (vai direto ao assunto)",
    },
    "tratamento": {
        "voce": "por você",
        "senhor_senhora": "por Sr./Sra.",
        "pelo_nome": "pelo primeiro nome",
    },
    "emoji": {
        "nao": "não usa emoji",
        "pontual": "emoji pontual",
        "livre": "emoji à vontade",
    },
    "formalidade": {
        "informal": "informal",
        "cordial": "cordial",
        "formal": "formal",
    },
    "explicacao": {
        "passo_a_passo": "explica passo a passo",
        "direta": "explica de forma direta",
    },
}

#: nome da lista → (quantos itens, quantos caracteres por item). Soma guardada
#: até 2.160 caracteres; o RENDERIZADO tem teto próprio (E13, abaixo).
LISTAS: dict[str, tuple[int, int]] = {
    "principios": (5, 140),
    "termos_preferidos": (10, 40),
    "evitar": (10, 40),
    "exemplos_aprovados": (3, 220),
}

#: 🔴 O teto do bloco RENDERIZADO. Não é o mesmo que a soma do guardado: o
#: resto fica na tela, não no prompt (E13 — a contradição aritmética que o
#: aquecimento achou: 2.160 declarados × 900 renderizados).
TETO_BLOCO = 1400

#: E13 — a REGRA DE CORTE, escrita. As cinco escolhas sempre entram; as listas
#: entram até aqui. Um jeito no máximo da R3 tem de caber, e é assim que o
#: guarda [G3] prova o corte (com um jeito grande, nunca com um pequeno).
CORTE_DO_PROMPT: dict[str, int] = {
    "principios": 3,
    "evitar": 5,
    "termos_preferidos": 5,
    "exemplos_aprovados": 1,
}

TETO_CORRETORA = 500

ABERTURA_JEITO = "### 🏢 O JEITO DESTA CORRETORA"
ABERTURA_CORRETORA = "### 🏢 A CORRETORA"

#: A frase que o Intercom nos ensinou a escrever ao lado da guidance, e que
#: aqui vale como lembrete dentro do próprio bloco.
FRASE_FIXA = "Isto muda COMO você fala; não muda o que você pode fazer."


# ---------------------------------------------------------------------------
# Camada ① — estrutural
# ---------------------------------------------------------------------------

_CONSTRUCAO = (
    re.compile(r"\{\{.*?\}\}", re.S),          # {{ variável }}
    re.compile(r"<[^<>\n]{0,200}>"),           # < tag / marcador >
    re.compile(r"```"),                         # cerca de código
    re.compile(r"https?://\S+", re.I),          # link
    re.compile(r"data:[^\s]+", re.I),           # data: URI
)

#: linha inteira que abre como turno de conversa ou como cabeçalho de bloco
_LINHA_DE_PAPEL = re.compile(r"^\s*(system|assistant|user|###)\s*:?.*$", re.I)

#: Camada ③ — a lista que SINALIZA (nunca descarta). Sobre o texto cru, com e
#: sem acento, porque `_norm` do acervo tira acento e um padrão medido num
#: normalizador e aplicado em outro é um padrão sobre outra coisa
#: (CLAUDE.md §9.4, o corolário do dialeto).
_SUSPEITAS = re.compile(
    r"(ignor[ae]|desconsider[ae]|voc[êe]\s+pode|envie|regras\s+acima|instru[çc][õo]es)",
    re.I,
)


def _limpar_estrutura(texto: str) -> str:
    """Camada ①: tira a construção, mantém a prosa."""
    linhas = []
    for linha in (texto or "").splitlines():
        if _LINHA_DE_PAPEL.match(linha):
            continue
        linhas.append(linha)
    limpo = " ".join(linhas)
    for padrao in _CONSTRUCAO:
        limpo = padrao.sub(" ", limpo)
    return re.sub(r"\s+", " ", limpo).strip()


def _truncar(texto: str, teto: int) -> str:
    """Camada ②: trunca com reticências. NUNCA descarta."""
    if len(texto) <= teto:
        return texto
    return texto[: max(teto - 1, 0)].rstrip() + "…"


def _item_normalizado(bruto: Any) -> Optional[dict]:
    """Todo item de lista vira `{texto, sinalizado, confirmado}`.

    A tela manda dicionário; a leitura do site e a estatística das conversas
    mandam string. Os dois caminhos convergem aqui — senão a marca de
    `sinalizado` dependeria de por onde o item entrou.
    """
    if isinstance(bruto, dict):
        texto = str(bruto.get("texto") or bruto.get("text") or "")
        confirmado = bool(bruto.get("confirmado"))
    else:
        texto = str(bruto or "")
        confirmado = False
    return {"texto": texto, "confirmado": confirmado} if texto.strip() else None


# ---------------------------------------------------------------------------
# validar
# ---------------------------------------------------------------------------

def validar(d: Any) -> dict:
    """Valida e normaliza um Jeito de atender. Levanta `ValueError` fora do enum.

    Devolve SEMPRE a mesma forma: as escolhas presentes (as ausentes ficam de
    fora, não viram default — semear tom que ninguém revisou é pior que não ter
    tom, §3/Hermes) e as quatro listas normalizadas item a item.
    """
    if d is None:
        return {}
    if not isinstance(d, dict):
        raise ValueError("o jeito de atender precisa ser um objeto")

    saida: dict[str, Any] = {}

    for campo, opcoes in ESCOLHAS.items():
        valor = d.get(campo)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            continue
        valor = str(valor).strip()
        if valor not in opcoes:
            raise ValueError(
                f"{campo}: '{valor}' não é uma escolha válida "
                f"(esperado um de {', '.join(sorted(opcoes))})"
            )
        saida[campo] = valor

    for lista, (max_itens, max_chars) in LISTAS.items():
        bruto = d.get(lista)
        if bruto is None:
            continue
        if isinstance(bruto, (str, bytes)):
            bruto = [bruto]
        if not isinstance(bruto, (list, tuple)):
            raise ValueError(f"{lista}: precisa ser uma lista")

        itens: list[dict] = []
        for cru in list(bruto)[:max_itens]:
            item = _item_normalizado(cru)
            if not item:
                continue
            # ① estrutural — e o item que virar vazio SAI (não vira linha muda)
            texto = _limpar_estrutura(item["texto"])
            if not texto:
                continue
            # ② teto — trunca, nunca descarta
            texto = _truncar(texto, max_chars)
            novo = {"texto": texto}
            # ③ semântico — SINALIZA; só entra no prompt se confirmado
            if _SUSPEITAS.search(texto):
                novo["sinalizado"] = True
                novo["confirmado"] = bool(item["confirmado"])
            elif item["confirmado"]:
                novo["confirmado"] = True
            itens.append(novo)
        if itens:
            saida[lista] = itens

    return saida


# ---------------------------------------------------------------------------
# vazio
# ---------------------------------------------------------------------------

def vazio(jeito: Any) -> bool:
    """Mede CONTEÚDO, não presença (D18).

    📊 Foi o defeito medido: `tone` = `{}` nas três linhas de `brand_profiles`,
    e um `IS NOT NULL` diria que a corretora já declarou o jeito dela. Um
    `{"saudacao": None}` mente do mesmo jeito.
    """
    if not isinstance(jeito, dict) or not jeito:
        return True
    for campo in ESCOLHAS:
        v = jeito.get(campo)
        if isinstance(v, str) and v.strip():
            return False
    for lista in LISTAS:
        itens = jeito.get(lista)
        if not isinstance(itens, (list, tuple)):
            continue
        for cru in itens:
            item = _item_normalizado(cru)
            if item:
                return False
    return True


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _itens_para_o_prompt(jeito: dict, lista: str) -> list[str]:
    """Os textos que PODEM ir ao prompt, já com o corte E13 aplicado.

    Item sinalizado e não confirmado fica de fora — e continua guardado e
    visível na tela, que é onde a administradora decide.
    """
    saida: list[str] = []
    for cru in (jeito.get(lista) or []):
        if not isinstance(cru, dict):
            cru = _item_normalizado(cru) or {}
        texto = str(cru.get("texto") or "").strip()
        if not texto:
            continue
        if cru.get("sinalizado") and not cru.get("confirmado"):
            continue
        saida.append(texto)
        if len(saida) >= CORTE_DO_PROMPT.get(lista, 0):
            break
    return saida


def render(jeito: Any) -> str:
    """O bloco que entra no prompt. ≤ `TETO_BLOCO`, PT-BR, sem chave de código.

    Jeito vazio → string vazia: o prompt de hoje continua exatamente como está
    até a corretora aprovar (R2, estado inicial vazio e visível).
    """
    if not isinstance(jeito, dict) or vazio(jeito):
        return ""

    linhas = [ABERTURA_JEITO]

    escolhas = [
        ESCOLHAS[campo][jeito[campo]]
        for campo in ESCOLHAS
        if isinstance(jeito.get(campo), str) and jeito.get(campo) in ESCOLHAS[campo]
    ]
    if escolhas:
        linhas.append("Fale assim: " + "; ".join(escolhas) + ".")

    blocos: list[tuple[str, str]] = []
    for lista, rotulo in (
        ("principios", "Princípios da corretora"),
        ("termos_preferidos", "Prefira dizer"),
        ("evitar", "Evite"),
        ("exemplos_aprovados", "Exemplo aprovado"),
    ):
        itens = _itens_para_o_prompt(jeito, lista)
        if itens:
            sep = " | " if lista in ("principios", "exemplos_aprovados") else ", "
            blocos.append((lista, f"{rotulo}: {sep.join(itens)}"))

    def montar(sem: set[str]) -> str:
        corpo = list(linhas) + [t for k, t in blocos if k not in sem] + [FRASE_FIXA]
        return "\n".join(corpo)

    # Teto duro. A ordem de sacrifício é a inversa da importância: o exemplo sai
    # antes do princípio, porque o princípio é a regra e o exemplo é a ilustração.
    sem: set[str] = set()
    for candidato in ("exemplos_aprovados", "termos_preferidos", "evitar", "principios"):
        if len(montar(sem)) <= TETO_BLOCO:
            break
        sem.add(candidato)

    texto = montar(sem)
    if len(texto) > TETO_BLOCO:  # cinto e suspensório: nunca estoura
        texto = texto[: TETO_BLOCO - 1].rstrip() + "…"
    return texto


# ---------------------------------------------------------------------------
# render_corretora — R5, para TODOS os papéis
# ---------------------------------------------------------------------------

def _nomes(valor: Any, limite: int) -> list[str]:
    """`services` nasceu `{name, source}` e virou `{name, description, audience}`.

    Os dois convivem: nenhuma data migration foi feita, e um leitor que exigisse
    `description` apagaria o que a captura de 17/08 gravou.
    """
    saida: list[str] = []
    if isinstance(valor, (list, tuple)):
        for item in valor:
            nome = item.get("name") if isinstance(item, dict) else item
            nome = str(nome or "").strip()
            if nome and nome not in saida:
                saida.append(nome)
            if len(saida) >= limite:
                break
    return saida


def render_corretora(companies_row: Any, brand_row: Any) -> str:
    """Quem é a corretora, em ≤ `TETO_CORRETORA` caracteres, para todo papel.

    📊 Hoje só o NOME entra, e só no atendimento (`prompts.py:339`): para o Core
    a corretora não existe. Este bloco é o que conserta isso — fatos
    verificáveis, nunca jeito de falar (R1: uma não finge ser a outra).
    """
    c = companies_row if isinstance(companies_row, dict) else {}
    b = brand_row if isinstance(brand_row, dict) else {}

    nome = str(b.get("display_name") or c.get("company_name")
               or c.get("legal_name") or "").strip()
    if not nome:
        return ""

    linhas = [ABERTURA_CORRETORA, f"Você trabalha na **{nome}**, uma corretora de seguros."]

    ramos = _nomes(b.get("services"), 8)
    if ramos:
        linhas.append("Ramos que ela atende: " + ", ".join(ramos) + ".")

    seguradoras = _nomes(b.get("insurers"), 8)
    if seguradoras:
        linhas.append("Seguradoras com que ela trabalha: " + ", ".join(seguradoras) + ".")

    area = str(b.get("service_area") or "").strip()
    if area:
        linhas.append(f"Área de atuação: {area}.")

    desde = b.get("founded_year")
    if isinstance(desde, int) and 1800 < desde < 2200:
        linhas.append(f"Atua desde {desde}.")

    texto = "\n".join(linhas)
    if len(texto) > TETO_CORRETORA:
        # Corta por LINHA, não no meio de uma frase: meia seguradora no prompt
        # é pior que seguradora nenhuma.
        while len(linhas) > 2 and len("\n".join(linhas)) > TETO_CORRETORA:
            linhas.pop()
        texto = "\n".join(linhas)[:TETO_CORRETORA].rstrip()
    return texto
