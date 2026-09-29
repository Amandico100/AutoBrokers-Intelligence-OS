"""A higiene do corpus de telas — SPEC-083 §6.4.

🔴 ISTO NÃO É UM SEGUNDO MASCARADOR.

O mascarador é **um só**: `templatize`, do Atlas (`app/services/atlas/templater.py`),
com as suas 38 regras de PII. Este módulo o CHAMA e aplica, sobre a saída dele,
duas exceções que a SPEC-083 §6.4 declara e que ele não cumpre — cada uma
registrada em `CHANGE-ADDENDA.md` com a medição que a produziu:

  CA-062  a EXCEÇÃO DA SENHA. `templatize` troca `*4743*` por `*{SEGREDO}*` e
          `extract_capture_anchors` para de capturar. A §6.4 é literal:
          *"preservar os 4 últimos se eles reaparecerem como senha — senão a
          âncora de senha perde o alvo"*.

  CA-064  o NOME NO VOCATIVO em tela sem saudação anterior. 📊 137 eventos em
          102 sessões entram no corpus com primeiro nome em claro.

⚠️ **Por que a segunda não foi feita dentro do `templatize`.** Ele já tem a regra
`NOME_NO_VOCATIVO`, e ela exige — de propósito, e com medição no próprio arquivo —
que a URA tenha se apresentado **na linha anterior**. Sem essa trava o mascarador
come português: 📊 o arquivo registra `"Roubo, furto e incêndio…"`,
`"Agora, me informe o CEP…"` e `"Elogios, reclamações…"` virando `{NOME}`.

**Nenhuma lista de palavras cobre o português.** A trava certa não é lexical — é
ESTRUTURAL, e o próprio `templater.py` diz isso com essas palavras. Aqui a
estrutura disponível é outra e mais forte, porque temos o ACERVO INTEIRO:

> ## Um NOME varia sobre o mesmo esqueleto. Um abridor de frase é sempre a MESMA palavra.

📊 Medido em 21/08/2026, sobre os 16.242 eventos `direction='in'`:

```
esqueletos com 1 cabeça só ....... 352   (2.090 eventos)   LÍNGUA — não se toca
esqueletos com >=3 cabeças .......   7   (  137 eventos)   DADO  — mascara
                                                           102 sessões, 5 seguradoras
```

🔴 **CONTROLE, e ele consegue ficar vermelho nos dois sentidos:**

```
as 7 famílias marcadas como DADO, todas vocativo real:
  "X, é você que está no local para acompanhar o serviço?"   15 cabeças / 19 ses
  "X, agora preciso saber se o veículo está em uma rodovia"   7 cabeças / 34 ses
  "X, escolha a opção desejada: seguro auto…"                11 cabeças / 15 ses
  "X, qual a placa do veículo?…"                              4 cabeças / 17 ses
  "X, escolha a opção desejada: cartão de crédito…"           5 cabeças /  9 ses
  "X, além do guincho, você precisa também solicitar táxi"    4 cabeças /  5 ses
  "X, localizei o seu *seguro auto*…"                         3 cabeças /  3 ses

as palavras de LÍNGUA, que EXISTEM em massa e NÃO são marcadas:
  "certo"   565 ocorrências ·  66 esqueletos · max_cabeças = 1   ✅ nunca marcada
  "agora"   341 ocorrências ·  24 esqueletos · max_cabeças = 1   ✅ nunca marcada
  "pronto"   68 ocorrências ·   9 esqueletos · max_cabeças = 1   ✅ nunca marcada
```

**Um guarda cujo controle nunca aparece não prova nada.** `certo`, `agora` e
`pronto` somam 974 ocorrências no acervo: o discriminador os VÊ e não os marca.
É isso que dá direito a confiar nele.
"""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

import regua_motor as M

# ── o limiar, e a faixa que ele deixa de fora ────────────────────────────────
# 📊 >=3 cabeças é o que está PROVADO acima. A faixa de exatamente 2 cabeças
# (8 esqueletos, 37 eventos) NÃO foi inspecionada uma a uma e por isso NÃO é
# mascarada automaticamente — ela vai para `INDICE.md` como `NOME_DUVIDOSO`,
# com a contagem, para leitura humana.
#
# 🔴 CLAUDE.md §9.2 e SPEC-083 §7: *"nunca pula em silêncio. Truncar calado
# lê-se como 'cobrimos tudo'."*
CABECAS_PARA_SER_DADO = 3
CABECAS_DUVIDOSO = 2

_RX_VOCATIVO = re.compile(r"^([A-Za-zÀ-Ýà-ÿ]{3,20})(\s*[,!]\s)")
_RX_RESTO = re.compile(r"^[A-Za-zÀ-Ýà-ÿ]{3,20}\s*[,!]\s*(.*)$", re.S)


def _esqueleto_do_resto(texto: str) -> Optional[str]:
    """Os 60 primeiros caracteres do que vem DEPOIS do vocativo, sem dígito.

    Os dígitos saem porque o resto carrega dado que varia por cliente (valores,
    datas) e a fragmentação por dígito faria o mesmo esqueleto virar vários — o
    que esconderia a variação das cabeças, que é justamente o sinal.

    🔴 E A PRIMEIRA LINHA SÓ — SPEC-119 CONSERTO A, 28/09/2026.

    ⚠️ Tirar DÍGITO e não tirar PALAVRA é o mesmo defeito da CLAUDE.md §9.4:
    📊 `"Juliana, você quer atendimento para qual veículo?\\n*1* - Land rover,
    ano 2018"` e a mesma tela com `Ram` produziam DOIS esqueletos — a marca do
    veículo fragmentava o molde, e a variação das cabeças (que é o sinal
    inteiro) desaparecia. O cardápio de veículos vive SEMPRE depois da primeira
    quebra de linha; a pergunta, que é o molde, vive antes dela.
    """
    m = _RX_RESTO.match(texto or "")
    if not m:
        return None
    primeira_linha = m.group(1).split("\n", 1)[0]
    resto = re.sub(r"\s+", " ", re.sub(r"[0-9]", "#", primeira_linha.lower()))
    return resto[:60] if len(resto[:60]) >= 25 else None


def levantar_vocativos(textos: Iterable[str]) -> Tuple[set, set]:
    """Percorre o acervo e devolve `(esqueletos_dado, esqueletos_duvidosos)`.

    Roda UMA vez, sobre o acervo inteiro, antes de mascarar qualquer linha —
    porque a decisão "esta cabeça é nome ou é língua" **não é local à tela**.
    Uma tela sozinha não tem como saber; o conjunto tem.
    """
    cabecas: Dict[str, set] = collections.defaultdict(set)
    for t in textos:
        esq = _esqueleto_do_resto(t or "")
        if esq is None:
            continue
        m = _RX_VOCATIVO.match(t)
        if m:
            cabecas[esq].add(m.group(1).lower())
    dado = {e for e, c in cabecas.items() if len(c) >= CABECAS_PARA_SER_DADO}
    duvidoso = {e for e, c in cabecas.items() if len(c) == CABECAS_DUVIDOSO}
    # 🔴 O ESQUELETO CONTAMINADO — SPEC-119 CONSERTO A, 28/09/2026.
    #
    # Se ALGUMA cabeça deste esqueleto já se provou nome, o esqueleto é um campo
    # de NOME — e o que aparece nele é dado, mesmo quando a palavra existe no
    # dicionário. É o que fecha o último buraco da inversão: um nome que COLIDE
    # com palavra de língua passaria pelo léxico. 📊 Medido: de 34 nomes próprios
    # PT-BR comuns testados contra o léxico, **2** passariam (`Luz`, `Graça`).
    #
    # 📊 E o preço do reforço foi medido sobre os 18.623 eventos `in`: 335
    #    esqueletos com vocativo, 50 com ao menos um nome, e ele alcança **duas**
    #    cabeças de língua no acervo inteiro:
    #
    # ```
    # "Certo! Confira o resumo da sua solicitação"   <- `Alvaro,` abre a mesma
    #     ⚠️ falso positivo ACEITO: custa `{NOME}!` numa tela de resumo
    #
    # "Atendimento, agora preciso saber se o veículo está em uma rodovia?"
    #     🔴 NÃO é falso positivo: `christian`, `Maria`, `chrstian`, `MARI` e
    #        `Andre` abrem a MESMA frase. Ali a URA ecoa o nome do perfil do
    #        WhatsApp — e um perfil chamado "Atendimento" é o aparelho de um
    #        ATENDENTE, que o CLAUDE.md §13.9 nomeia junto com o cliente.
    # ```
    #
    # ⚠️ Um falso positivo barato contra o vazamento do nome de um funcionário:
    #    falhar fechado é o certo, e a conta está medida, não suposta.
    contaminado = {e for e, c in cabecas.items()
                   if any(not e_lingua(x) for x in c)}
    return dado | contaminado, duvidoso


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O PADRÃO INVERTIDO — SPEC-119 · CONSERTO A · 28/09/2026
# ═════════════════════════════════════════════════════════════════════════════
#
# ⚠️ O mecanismo de cima (≥3 cabeças = DADO) continua valendo e continua certo no
# que afirma. O que ele NÃO cobre é o caso mais perigoso de todos:
#
# > ## O esqueleto com UMA cabeça só era INVISÍVEL — nem mascarado, nem sinalizado.
# > ## E uma cabeça só é a pessoa que recebeu a frase que mais ninguém recebeu.
#
# 📊 Medido em 28/09/2026 sobre os 16 `.jsonl` do acervo versionado (HEAD
# `e76cb28`), com o `_RX_VOCATIVO` da v1:
#
# ```
# cabeças distintas em posição de vocativo .......... 43
# delas, primeiro nome de segurado real ............. 18   (78 linhas)
#   Saionara ×17 · Maria ×13 · Carlos ×11 · Magda ×8 · Juliana ×5 · christian ×4
#   Nathalya ×3 · Elienai ×2 · Thaize ×2 · Maisa ×2 · Rafael ×2 · Alvaro ×2
#   Zany ×2 · Debora ×1 · Isac ×1 · Valmor ×1 · Paulo ×1 · Yan ×1
# ```
#
# 🔴 **A INVERSÃO.** Antes: mascara só se PROVAR que é nome. Agora: mascara
# **a menos que prove que é LÍNGUA**. ⚠️ Falhar fechado é o certo aqui —
# mascarar uma palavra comum por engano custa uma tela menos legível; deixar um
# nome passar custa o dado de uma pessoa (CLAUDE.md §13.9 e §7).
#
# ─────────────────────────────────────────────────────────────────────────────
# DE ONDE VEM A PROVA DE QUE É LÍNGUA — o PRODUTO primeiro, a lista depois
# ─────────────────────────────────────────────────────────────────────────────
# 📊 Medido em 28/09/2026 sobre as 118 cabeças de língua do acervo inteiro
# (18.623 eventos `in` do banco, 137 cabeças distintas):
#
# ```
# cabeças que o VOCABULÁRIO DO PRODUTO já cobre ......  78 de 118
#   (2.406 palavras dos 14 playbooks + 53 dos padrões de serviço)
# cabeças que sobraram para a lista fechada ...........  40
# 🔴 nomes de segurado que o vocabulário do produto chamaria de língua ......  0
# ```
#
# **Os 47 nomes medidos no acervo não aparecem em nenhum playbook.** É isso que
# dá direito a usar o produto como dicionário: ele é feito de língua de serviço,
# e nome de gente não entra nele. ⚠️ E a lista fechada **não é uma segunda lista
# de serviço** (CLAUDE.md §5): é só o que o produto não tem como saber —
# interjeição, saudação, rótulo de campo de terceiro e marca de veículo. Cada
# entrada carrega a contagem que a pôs lá.
_ABRIDORES_DE_FALA = frozenset({
    # 📊 interjeição e abridor de fala (contagem medida no acervo do banco):
    "perfeito",      # 17
    "imagina",       # 40  · `maginaa` ×10 e `imgina` ×1 são o MESMO erro de digitação
    "maginaa", "imgina",
    "ops",           # 12
    "opa",           # 2
    "claro",         # 10
    "otimo",         # 8   (o léxico é comparado SEM acento)
    "disponha",      # 7
    "desculpa",      # 6   (`desculpe` já vem do produto)
    "legal",         # 5
    "infelizmente",  # 4
    "igualmente",    # 2
    "compreendi",    # 2
    "exatamente",    # 2
    "capriche",      # 8
    "alterado",      # 2
    "cancelado",     # 2
    "atualmente",    # 1
    "correto",       # 1
    "anotado",       # 1
    "correcao",      # 1
    "okay", "okey",
    # 📊 rótulo de MENU que o produto ainda não declara:
    "pagamento",     # 8   menu da porto
    "elogios",       # 3   "Elogios, reclamações…"
    "participe",     # 2   convite de pesquisa de satisfação
    "coberturas",    # 1
    "incendio",      # 1   menu de sinistro
    "alagamento",    # 1   menu de sinistro
    # 📊 rótulo de campo que a URA ou o PRESTADOR escreve, e não é do produto:
    "dica", "atencao", "lembrete", "vigia", "requerimento", "laudo",
    "parcela", "boleto", "vencimento", "especialidade", "classificacao",
    "parachoque", "exemplos", "prestador",
    # 📊 marca de veículo que abre linha de cardápio ("Hyundai, ano 2011, placa…").
    #    ⚠️ Não existe lista de marcas no produto; no dia em que existir, estas
    #    duas saem daqui e a fonte passa a ser ela.
    "hyundai", "ram",
})

_CACHE_LINGUA: Optional[frozenset] = None


def _sem_acento(s: str) -> str:
    n = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


def vocabulario_de_lingua(*, recarregar: bool = False) -> frozenset:
    """Toda palavra que o PRODUTO já declara — mais a lista fechada acima.

    🔴 Lê os playbooks (âncoras, rótulos de passo, nomes de subserviço) e os
    `PADROES_DE_SERVICO_TEXTO`. Não é uma cópia deles: é o próprio produto
    servindo de dicionário, e quando uma seguradora nova entra, o vocabulário
    dela entra junto — que é o que a CLAUDE.md §5 pede no lugar de uma
    segunda lista.
    """
    global _CACHE_LINGUA
    if _CACHE_LINGUA is not None and not recarregar:
        return _CACHE_LINGUA
    palavras = set(_ABRIDORES_DE_FALA)
    try:
        import padroes_de_servico as _PSV
        for nome, padrao in _PSV.PADROES_DE_SERVICO_TEXTO.items():
            for w in re.findall(r"[a-zA-ZÀ-ÿ]{3,}", padrao):
                palavras.add(_sem_acento(w))
            for w in nome.split("_"):
                palavras.add(_sem_acento(w))
    except Exception:   # noqa: BLE001 — sem o módulo, sobra a lista fechada
        pass
    try:
        for pb in M.PLAYBOOKS.values():
            for w in re.findall(r"[A-Za-zÀ-ÿ]{2,25}",
                                json.dumps(pb, ensure_ascii=False)):
                palavras.add(_sem_acento(w))
    except Exception:   # noqa: BLE001 — sem playbook carregado, sobra o resto
        pass
    # 🔴 O TIPO DE LOGRADOURO vem do MASCARADOR, não de uma cópia.
    # 📊 `*Unnamed Road,  - Angelina  - SC*.` era o único falso positivo dos 25
    #    medidos: `Unnamed Road` é o nome que o Google Maps dá a via sem nome, e
    #    ele já está na alternância `_LOGRADOURO` do `templater.py`. Ler de lá é
    #    o que impede as duas listas de divergirem (CLAUDE.md §5).
    try:
        for w in re.findall(r"[a-zà-ÿ]{2,}", M.TPL._LOGRADOURO.pattern):
            palavras.add(_sem_acento(w))
    except Exception:   # noqa: BLE001
        pass
    _CACHE_LINGUA = frozenset(palavras)
    return _CACHE_LINGUA


def e_lingua(cabeca: str) -> bool:
    """A cabeça do vocativo é LÍNGUA (fica) ou é NOME (mascara-se)?

    🔴 Cabeça de VÁRIAS palavras (`MARIA DE LOURDES SOUZA SANTOS`) só é língua
    se **todas** forem — senão o sobrenome atravessa. 📊 Foi exatamente o que
    aconteceu com `"Olá, {NOME} Manfroi, sou a Sofia…"` (hdi-auto.jsonl:722):
    o primeiro nome saiu e o sobrenome ficou.
    """
    palavras = re.findall(r"[A-Za-zÀ-ÿ]{2,}", cabeca or "")
    if not palavras:
        return True          # só marcador (`{NOME}`) — já está mascarado
    voc = vocabulario_de_lingua()
    return all(_sem_acento(p) in voc for p in palavras)


# ─────────────────────────────────────────────────────────────────────────────
# ONDE O VOCATIVO MORA — e as três formas que a v1 não via
# ─────────────────────────────────────────────────────────────────────────────
# 📊 Medidas em 28/09/2026, no acervo versionado:
#
# ```
# ① o NEGRITO engole a âncora          `*chrstian*, agora definiremos…`
#    `^([A-Za-zÀ-ÿ]{3,20})` não casa porque o primeiro caractere é `*`.
#
# ② o nome vem DEPOIS de um abridor    `Certo, Alvaro.`  ·  `Certo, Magda!`
#                                      `Legal, Saionara! Você possui…`
#    porto-auto.jsonl:691 · porto-residencial.jsonl:24
#
# ③ o nome é COMPOSTO                  `Olá MARIA DE LOURDES SOUZA SANTOS,
#                                        como foi o serviço de MECANICO?`
#    bradesco-auto.jsonl:175 — nome COMPLETO em claro, o pior caso do acervo.
# ```
#
# ⚠️ E o vocativo não mora só no caractere 0: a linha de cardápio começa no meio
# do texto. Por isso a regra vale em TODO início de linha — e é a MESMA regra
# que o auditor usa, para que máscara e guarda não possam discordar (§9.3).
_PALAVRA_DE_NOME = (r"(?:\{[A-Z_]+\}|[A-ZÀ-Ý][A-Za-zÀ-ÿ'’´-]{1,19}|[A-ZÀ-Ý]{2,20})")
# a PRIMEIRA palavra aceita minúscula — 📊 `christian,` `maria,` `ola,` existem
# no acervo, escritos pela própria URA.
_PRIMEIRA_PALAVRA = (r"(?:\{[A-Z_]+\}|[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’´-]{2,19})")
# ⚠️ SEIS palavras depois da primeira, não quatro. 📊 `"Olá MARIA DE LOURDES
#    SOUZA SANTOS, como foi o serviço…"` (bradesco-auto.jsonl:175) tem SETE
#    palavras antes da vírgula — com o teto em quatro, a linha com o nome
#    COMPLETO do segurado passava limpa, e ela é o pior caso do acervo.
_RX_CABECA = re.compile(
    r"\**(" + _PRIMEIRA_PALAVRA + r"(?:[ \t]+" + _PALAVRA_DE_NOME + r"){0,6})\**"
    r"[ \t]*([,!.])(?=[ \t]|$)")
# depois de um abridor, a cabeça tem de ser CAPITALIZADA — senão
# `"Agora, informe apenas o nome do logradouro"` viraria `"Agora, {NOME}"`.
_RX_CABECA_APOS_ABRIDOR = re.compile(
    r"\**(" + _PALAVRA_DE_NOME + r"(?:[ \t]+" + _PALAVRA_DE_NOME + r"){0,6})\**"
    r"[ \t]*([,!.])(?=[ \t]|$)")


def achar_vocativo(linha: str) -> Optional[Tuple[int, int, str]]:
    """`(inicio, fim, cabeca)` do vocativo desta LINHA, ou `None`.

    🔴 Duas tentativas, nesta ordem, e a segunda é a que a v1 não tinha:
      1. a cabeça abre a linha                      → `Saionara, o telefone…`
      2. um ABRIDOR abre e a cabeça vem em seguida  → `Certo, Alvaro.`

    Se a cabeça da tentativa 1 for língua, tenta a 2 a partir do fim dela.

    ⚠️ E quando a cabeça COMEÇA por língua (`Olá DOBEREINER MILLER SILVA
    RODRIGUES,`), a saudação fica e só o resto vira `{NOME}` — mascarar o `Olá`
    junto tiraria da tela a informação de que ali há uma saudação, que é
    justamente o que o corpus existe para ensinar.
    """
    m = _RX_CABECA.match(linha or "")
    if not m:
        return None
    if not e_lingua(m.group(1)):
        ini, fim = m.start(1), m.end(1)
        palavras = m.group(1).split()
        while len(palavras) > 1 and e_lingua(palavras[0]):
            ini = linha.index(palavras[1], ini + len(palavras[0]))
            palavras = palavras[1:]
        return ini, fim, linha[ini:fim]
    resto = linha[m.end():]
    desloc = m.end() + (len(resto) - len(resto.lstrip(" \t")))
    m2 = _RX_CABECA_APOS_ABRIDOR.match(linha, desloc)
    if m2 and not e_lingua(m2.group(1)):
        return m2.start(1), m2.end(1), m2.group(1)
    return None


def _mascarar_vocativo(texto: str, esqueletos_dado: set = frozenset()) -> Tuple[str, bool]:
    """Troca por `{NOME}` toda cabeça de vocativo que NÃO se prova língua.

    ⚠️ `esqueletos_dado` continua sendo honrado como REFORÇO — um esqueleto que
    o levantamento de ≥3 cabeças marcou como DADO é mascarado mesmo que a
    cabeça caia no léxico. Os dois mecanismos somam; nenhum substitui o outro.
    """
    if not texto:
        return texto, False
    esq = _esqueleto_do_resto(texto)
    reforco = esq is not None and esq in (esqueletos_dado or frozenset())
    saida: List[str] = []
    houve = False
    for i, linha in enumerate(texto.split("\n")):
        achado = achar_vocativo(linha)
        if achado is None and reforco and i == 0:
            m = _RX_CABECA.match(linha)
            achado = (m.start(1), m.end(1), m.group(1)) if m else None
        if achado is None:
            saida.append(linha)
            continue
        ini, fim, _cab = achado
        saida.append(linha[:ini] + "{NOME}" + linha[fim:])
        houve = True
    return "\n".join(saida), houve


def nomes_no_vocativo(textos: Iterable[str]) -> set:
    """Os nomes que o vocativo REVELOU nas telas de uma sessão.

    🔴 Serve à segunda metade do vazamento: o nome que aparece FORA da posição
    de vocativo, onde nenhuma regra de forma o alcança. 📊 Medido em 28/09/2026:

    ```
    porto-auto.jsonl:691        "Certo, Alvaro. A solicitação de agendamento foi encerrada"
    porto-residencial.jsonl:24  "Certo, Magda! Antes de continuar, tenha em mente que…"
    ```

    ⚠️ A sessão é a unidade certa: `Alvaro` só é nome NAQUELA conversa. Usar o
    acervo inteiro transformaria um nome numa palavra proibida para todas as
    corretoras, que é o que a CLAUDE.md §13.9 manda não fazer.
    """
    fora: set = set()
    for t in textos:
        for linha in (t or "").split("\n"):
            achado = achar_vocativo(linha)
            if achado is None:
                continue
            for palavra in re.findall(r"[A-Za-zÀ-ÿ]{3,}", achado[2]):
                if not e_lingua(palavra):
                    fora.add(palavra)
    return fora


def _mascarar_nomes_conhecidos(texto: str, nomes: Iterable[str]) -> Tuple[str, bool]:
    """Troca por `{NOME}` os nomes que a própria sessão já revelou."""
    houve = False
    for nome in sorted(set(nomes or ()), key=len, reverse=True):
        if len(nome) < 3:
            continue
        novo, n = re.subn(rf"(?i)(?<![\w{{]){re.escape(nome)}(?![\w}}])",
                          "{NOME}", texto)
        if n:
            texto, houve = novo, True
    return texto, houve


# ── a exceção da senha (CA-062 · SPEC-083 §6.4) ──────────────────────────────
# ⚠️ `{CEP}` entra na lista por medicao: 📊 o protocolo `52955490` tem oito
#    digitos e o mascarador o le como CEP.
_RX_MARCADOR_DE_SEGREDO = re.compile(
    r"\{SEGREDO\}|\{TELEFONE\}|\{NUM\}|\{VALOR\}|\{CEP\}|\{PROTOCOLO\}|\{NUMERO\}")


def _preservar_capturas(playbook: Dict[str, Any], cru: str,
                        mascarado: str) -> Tuple[str, bool]:
    """Reinjeta o que o MOTOR capturava e o `templatize` apagou.

    🔴 A condição é ESTREITA de propósito: só reinjeta um valor que
    `extract_capture_anchors` **capturou no texto CRU**. Não é "todo número
    volta" — isso seria um buraco de PII disfarçado de exceção. E cada reinjeção
    é **verificada pelo motor** antes de ser aceita.

    ═══════════════════════════════════════════════════════════════════════════
    ⚠️ ESTA FUNÇÃO NASCEU CUIDANDO SÓ DA SENHA, E A MEDIÇÃO A OBRIGOU A CRESCER.
    ═══════════════════════════════════════════════════════════════════════════

    CA-062 tratava a exceção da §6.4 como sendo sobre a senha, porque é o
    exemplo que a SPEC dá (*"preservar os 4 últimos se eles reaparecerem como
    senha — senão a âncora de senha perde o alvo"*).

    🔴 **O PROTOCOLO morre do mesmo jeito, e vale muito mais.** 📊 Medido em
    21/08/2026, com o CONTROLE verde:

    ```
    "...o numero de protocolo e 52955490"
       cru       -> {'protocol': '52955490'}
       mascarado -> {}                                    A CAPTURA MORRE

    "*RESUMO* *Protocolo N.deg:* 52955490 *Agendamento para:* ..."
       mascarado -> "*Protocolo N.deg:* {CEP} ..."        oito digitos viram CEP
    ```

    **E o protocolo é o `DECIDE:` #1 da rubrica inteira** — os 12 pontos de
    *"a ROTA foi percorrida até o fim"*, mais os 5 de *"o cliente recebe
    protocolo + dia + período"*, mais o helper `sessao_chegou_ao_fim`.

    > ## Sem esta generalização, o eixo A daria ZERO para as 62 rotas — e o
    > ## motivo não seria qualidade de rota nenhuma. Seria o mascarador.

    ⚠️ **E o protocolo não é PII.** A SPEC-083 §6.4 lista o que se mascara:
    telefone, CPF/CNPJ, nome, corretora. Número de chamado da seguradora não
    está lá — e é justamente o que o corpus existe para provar.
    """
    cap_cru = M.extract_capture_anchors(playbook, cru)
    # 🔴 só valores ESCALARES que o motor capturou. `schedule` e um dict e vem
    #    da PROSA da tela, que o mascarador nao toca.
    alvos = {k: v for k, v in cap_cru.items()
             if k in ("protocol", "password", "eta", "tracking_link")
             and isinstance(v, str) and v}
    if not alvos:
        return mascarado, False
    perdidos = {k: v for k, v in alvos.items()
                if M.extract_capture_anchors(playbook, mascarado).get(k) != v}
    if not perdidos:
        return mascarado, False   # ja sobreviveu; nao se mexe

    # 🔴 UM MARCADOR POR VEZ, E O MOTOR DECIDE QUAL.
    #
    # ⚠️ A primeira versão fazia `subn(..., count=1)` — trocava o **primeiro**
    #    marcador da string. O JUIZ 2 mediu, sobre a tela #27 real, que o primeiro
    #    marcador é `{TELEFONE}` (o telefone no topo da tela) e não `{SEGREDO}`
    #    (a senha no fim):
    #
    #      "...falando agora:\n*####*.\n\nSua senha sera os 4 ultimos digitos
    #       desse telefone *{SEGREDO}*"
    #
    #    O verificador da linha seguinte pegava o erro e devolvia o texto sem
    #    mexer — então a exceção **existia no comentário e não no comportamento**.
    #    📊 `senha_preservada=False` em 100% das telas. CA-062 escrito e não entregue.
    #
    # 🔴 A correção não escolhe o marcador por posição nem por nome: ela **tenta
    #    cada um e pergunta ao MOTOR** qual devolve a senha. É a mesma disciplina
    #    da §1.3 — quem decide é `extract_capture_anchors`, não uma heurística.
    # ══════════════════════════════════════════════════════════════════════
    # ⚠️ 🔴 E O MASCARADOR NEM SEMPRE COME O VALOR INTEIRO — 23/08/2026
    # ══════════════════════════════════════════════════════════════════════
    #
    # 📊 O protocolo da PORTO tem PREFIXO, e a regra de dígitos só mordeu o
    #    rabo dele:
    #
    # ```
    #   cru       "Aqui está seu protocolo de atendimento 👇 1-408029004672"
    #   motor     {'protocol': '1-408029004672'}          <- captura o inteiro
    #   mascarado "Aqui está seu protocolo de atendimento 👇 1-{NUMERO}"
    #                                                        ^^  sobrou
    # ```
    #
    # 🔴 Trocar `{NUMERO}` pelo valor INTEIRO produzia `1-1-408029004672`, e o
    #    motor devolvia outra coisa — então o verificador recusava, com razão,
    #    e o protocolo morria. **Nas cinco rotas de `porto/auto` com corpus,
    #    NENHUMA conseguia provar que chegou ao fim**, e o motivo não era o
    #    corredor: era o `1-` que sobrou na frente do marcador.
    #
    # ⚠️ E a allianz e a hdi passavam, porque o protocolo delas é só dígitos e
    #    o marcador cobre o valor inteiro. O defeito só aparece em quem usa
    #    prefixo — e some do radar exatamente por isso.
    #
    # 🔴 O conserto NÃO afrouxa nada: ele absorve, no máximo, um pedaço que já
    #    estava no texto E que é PREFIXO do valor capturado. Continua sendo o
    #    MOTOR quem aceita ou recusa a tentativa, uma por uma.
    houve = False
    for chave, valor in perdidos.items():
        for m in _RX_MARCADOR_DE_SEGREDO.finditer(mascarado):
            inicios = [m.start()]
            sobra = re.search(r"[\w./-]{1,16}$", mascarado[:m.start()])
            if sobra and valor.startswith(sobra.group(0)):
                inicios.append(sobra.start())
            for ini in inicios:
                tentativa = mascarado[:ini] + valor + mascarado[m.end():]
                if M.extract_capture_anchors(playbook, tentativa).get(chave) == valor:
                    mascarado, houve = tentativa, True
                    break
            if houve:
                break
    return mascarado, houve


# ── a auditoria de PII (SPEC-083 Bloco A, VERIFY) ────────────────────────────
# 🔴 A v1 da SPEC usava `grep -cE '[0-9]{11}'`. Ele NÃO casa
# `+55 (47) 90000-0000` — a maior sequência de dígitos ali tem CINCO. Devolvia
# 0 com quatro telefones no arquivo. *"Um guarda que não tem como falhar não
# guarda nada"* (CLAUDE.md §9.3). Os padrões abaixo são os da própria SPEC.
_AUDITORIA = (
    ("TELEFONE", re.compile(r"\+?55[\s(]*\d{2}[\s)-]*9?\d{4}[\s-]*\d{4}")),
    ("TELEFONE", re.compile(r"\(\d{2}\)\s*9?\d{4}[- ]?\d{4}")),
    ("CPF",      re.compile(r"\d{3}[.\s]\d{3}[.\s]\d{3}[-\s]\d{2}")),
    ("CNPJ",     re.compile(r"\d{2}[.\s]\d{3}[.\s]\d{3}/\d{4}-\d{2}")),
    ("EMAIL",    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")),
    # razão social genérica — a classe do `SGA Corretora de Seguros Ltda`, que
    # 📊 sobrevive ao `templatize` porque a SGA não é corretora cliente e não
    # está em `companies` (CA-063).
    ("RAZAO_SOCIAL", re.compile(
        r"\b[A-ZÀ-Ý][\wÀ-ÿ&.-]*(?:\s+[\wÀ-ÿ&.-]+){0,4}\s+"
        r"(?:Ltda|LTDA|S\.?A\.?|ME\b|EIRELI|Corretora)\b")),
)

# 🔴 A EXCEÇÃO QUE A PRIMEIRA EXECUÇÃO EXIGIU, e ela é o defeito da §6.4 acontecendo.
#
# 📊 A regra de razão social acima RECUSOU 8 linhas da hdi na estreia. As 8 eram:
#
#     "*HDI SEGUROS S.A*: encontramos o prestador que realizará o serviço de
#      *GUINCHO* para a assistência *{NUMERO}*, agendada para *{DATA}* às *14:00*"
#     "*HDI SEGUROS S.A*: o prestador está a caminho e faltam ~30 minutos"
#     "*HDI SEGUROS S.A*: o prestador chegou no local para te atender?"
#
# 🔴 **É o nome da PRÓPRIA SEGURADORA — não é corretora, não é pessoa, não é PII.**
# E são as telas mais valiosas do acervo da hdi: as de chegada do prestador, que
# é literalmente o desfecho que o produto persegue.
#
# É a §6.4 acontecendo comigo: *"Recusar apagaria a tela #27… O replay perderia
# 3 passos da régua e ninguém veria, porque a recusa vira só um número."*
#
# ⚠️ **Reuso a lista que já existe** — `_marcas_das_seguradoras()` do
# `templater.py`, que lê o `INSURER_REGISTRY`. Escrever uma lista de seguradoras
# ao lado dela seria a segunda lista que o CLAUDE.md §5 proíbe: as duas divergem
# no dia em que uma seguradora nova entrar no produto.
_NOMES_DE_SEGURADORA: Optional[frozenset] = None


#
# 🔴 E a exceção precisa ser APERTADA, porque a primeira versão dela era larga
#    demais — achado no controle, não em produção:
#
#    📊 `_marcas_das_seguradoras()` devolve 16 nomes, e entre eles estão as
#       palavras **genéricas** `seguro` e `seguros` (vêm dos rótulos, tipo
#       *"HDI Seguros"*). Com a checagem em QUALQUER palavra do trecho, isso fez
#       `"SGA Corretora de Seguros Ltda"` **passar limpo** — e é exatamente o caso
#       que a SPEC-083 §6.4 nomeia como o que tem de ser pego.
#
#    A trava certa é a **PRIMEIRA palavra**: é ali que mora a marca
#    (`HDI SEGUROS S.A`, `Allianz Seguros`), e não é ali que mora o terceiro
#    (`SGA Corretora…`, `Oficina Bruno Mecanica Ltda`).
_GENERICAS_DEMAIS = frozenset({"seguro", "seguros", "marine"})


def _nomes_de_seguradora() -> frozenset:
    global _NOMES_DE_SEGURADORA
    if _NOMES_DE_SEGURADORA is None:
        _NOMES_DE_SEGURADORA = frozenset(
            M.TPL._marcas_das_seguradoras()) - _GENERICAS_DEMAIS
    return _NOMES_DE_SEGURADORA


def auditar_pii(texto: str, *, nomes_da_sessao: Iterable[str] = ()) -> List[str]:
    """O que sobrou de identidade depois da máscara. Lista vazia = limpo.

    `nomes_da_sessao` é o `slots.titular_nome` e o nome de atendente, que a
    SPEC-083 manda conferir **contra o texto da tela** — um primeiro nome solto
    não casa nenhum padrão lexical, e é o vazamento que
    `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` nomeia como o real.
    """
    achados: List[str] = []
    seguradoras = _nomes_de_seguradora()
    for rotulo, rx in _AUDITORIA:
        for m in rx.finditer(texto or ""):
            trecho = m.group(0)
            # 🔴 O nome da PRÓPRIA SEGURADORA não é vazamento — ver a nota acima.
            if rotulo == "RAZAO_SOCIAL" and any(
                    p.lower() in seguradoras for p in trecho.split()):
                continue
            achados.append(f"{rotulo}:{trecho[:6]}…")
    # 🔴 O NOME NO VOCATIVO — SPEC-119 CONSERTO A, 28/09/2026.
    #
    # 📊 Antes deste bloco, `--auditar-pii` devolvia `6048 linhas, 0 sujas` e
    # `exit 0` sobre um acervo com 78 linhas de primeiro nome de segurado em
    # claro. **Era um carimbo, não um guarda** (CLAUDE.md §9.3).
    #
    # ⚠️ É a MESMA regra que `_mascarar_vocativo` usa, de propósito: guarda e
    # máscara que discordam produzem um vermelho que ninguém consegue apagar.
    for linha in (texto or "").split("\n"):
        achado = achar_vocativo(linha)
        if achado is not None:
            achados.append(f"NOME_NO_VOCATIVO:{achado[2][:6]}…")
    # 🔴 SPEC-121 F3 · a apresentação da pessoa (P-120-12) — MESMA regra da máscara.
    apres = achar_apresentacao(texto or "")
    if apres is not None:
        achados.append(f"NOME_NA_APRESENTACAO:{apres[:3]}…")
    # 🔴 SPEC-121 F3 · o endereço postal — MESMA regra da máscara.
    if _ENDERECO_POSTAL.search(texto or "") or [
            m for m in _SOBRA_DO_ENDERECO.finditer(texto or "")
            if m.group(0).strip() != (m.group(1) + "{ENDERECO}").strip()]:
        achados.append("ENDERECO_POSTAL:…")
    baixo = (texto or "").lower()
    for nome in nomes_da_sessao:
        nome = (nome or "").strip()
        if len(nome) >= 3 and re.search(rf"\b{re.escape(nome.lower())}\b", baixo):
            achados.append(f"NOME_DA_SESSAO:{nome[:3]}…")
    return achados


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-121 F3 · A APRESENTAÇÃO DA PESSOA DA SEGURADORA — fecha P-120-12.
#
# O vocativo ("Maria, …") já era mascarado; a APRESENTAÇÃO não. 📊 No acervo
# versionado de 28/09 (`scratchpad/f3` · varredura por `aqui é a | meu nome é |
# me chamo | sou a` em todos os `.jsonl`): porto `4830574a` ("Aqui é a <nome>.
# Sou consultora de relacionamento") e yelum `9e562ae5`, `c0c3c694` ("Meu nome é
# *_<nome>_* e vou iniciar seu atendimento") — primeiro nome de FUNCIONÁRIA num
# arquivo global (CLAUDE.md §13.9).
#
# 🔴 O CONTROLE NEGATIVO é o mesmo que separa robô de pessoa em
#    `quem_fala_na_seguradora`: a linha em que o ROBÔ se apresenta ("eu sou a
#    <persona>, assistente virtual da zurich" — 📊 hdi, mapfre, zurich) NÃO é
#    tocada. O nome da persona do robô é produto, não pessoa.
# ⚠️ E papel não é nome: "Sou o Segurado", "sou a responsável" ficam.
# ═════════════════════════════════════════════════════════════════════════════
_APRESENTACAO_COM_NOME = re.compile(
    r"(?i:\b(?:aqui [ée] (?:a|o)|meu nome [ée]|me chamo|sou (?:a|o)))\s+([*_]*)"
    r"(?!(?i:segurad|terceir|respons|condutor|propriet|titular|client|corretor"
    r"|assistente|atendente|consultor|analista|especialista|pessoa)\w*)"
    r"([A-ZÀ-Ú][a-zà-ÿ]{2,})")


def _e_o_robo(texto: str) -> bool:
    import zonas_do_acervo as Z   # noqa: E402 — tardio: Z importa o motor
    return Z.e_o_robo_se_apresentando(texto)


def _mascarar_apresentacao(texto: str) -> Tuple[str, bool]:
    """`Aqui é a <Nome>` → `Aqui é a {NOME}` — só quando NÃO é o robô."""
    if not texto or _e_o_robo(texto):
        return texto, False
    novo, n = _APRESENTACAO_COM_NOME.subn(
        lambda m: m.group(0)[: m.start(2) - m.start(0)] + "{NOME}", texto)
    return novo, bool(n)


def achar_apresentacao(texto: str) -> Optional[str]:
    """A MESMA regra, do lado do guarda: o nome que sobrou numa apresentação."""
    if not texto or _e_o_robo(texto):
        return None
    m = _APRESENTACAO_COM_NOME.search(texto)
    return m.group(2) if m else None


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-121 F3 · O ENDEREÇO QUE O `templatize` DEIXA PELA METADE.
#
# 📊 Varredura independente do acervo versionado de 28/09 (`scratchpad/f3/
#    varrer_pii.py`, regex própria, 6.048 linhas): 7 linhas em 6 sessões com o
#    endereço do SEGURADO meio mascarado — `*1 -* AV #### ##<pedaço> DE # #####,
#    <número da casa> - <pedaço da cidade> - SC` (allianz `8ad1d251`, `96f220ca`,
#    `21610390`, `88eb97a9`, `f22b6d12`, `298e0c49`). O nome da rua some; o
#    NÚMERO DA CASA, pedaços do nome e a UF ficam. É a tela de confirmar o
#    endereço — e o recomeço da F3 traz mais delas para o acervo.
#
# 🔴 A forma que casa é a de ENDEREÇO POSTAL: logradouro + vírgula + número +
#    ` - UF` no fim da linha. Nada de "rua" solta: a URA escreve "informe o nome
#    do logradouro (rua, avenida…)" e "(Ex. Avenida Brasil)" — 📊 esses dois são
#    os falsos positivos que a varredura mostrou, e NÃO têm número + UF.
# ⚠️ O conserto de raiz é no `templatize` (outro dono) → pendência.
# ═════════════════════════════════════════════════════════════════════════════
_ENDERECO_POSTAL = re.compile(
    # ⚠️ `R.` só COM o ponto: "R$ 150,00 - SC" não é rua.
    r"(?:\b(?:AV|AVENIDA|RUA|ROD|RODOVIA|AL|ALAMEDA|TV|TRAVESSA|ESTR|ESTRADA|SERV|SERVIDAO"
    r"|Av|Avenida|Rua|Rodovia|Alameda|Travessa|Estrada|Servid[ãa]o)\b\.?|\bR\.)"
    # 🔴 da palavra do logradouro ATÉ O FIM DA LINHA, quando a linha tem vírgula e
    #    " - UF" depois dela. 📊 O `templatize` deixa, depois do `{ENDERECO}`, o
    #    número da casa, "BL"/"AP", pedaços do nome, bairro e cidade (allianz,
    #    bradesco, hdi, porto, yelum — `scratchpad/f3`, 44 linhas no acervo
    #    regerado). O número pode faltar (`96f220ca`: "<rua>,  - <cidade> - SC").
    r"(?=[^\n]*,)(?=[^\n]*-\s*[A-Z]{2}\b)[^\n]*")


# 🔴 E a SOBRA depois do `{ENDERECO}` que o `templatize` já pôs: 📊 acervo
#    regerado, 30 linhas (`*Endereço:* R. {ENDERECO} - <bairro> - SC`,
#    `*1 -* R. {ENDERECO}<pedaço da cidade> - SC`, `*1 -* RD <…>, <nº> - <…>
#    {ENDERECO}<…> - SC`). A linha que tem `{ENDERECO}` e termina em " - UF" vira
#    só o rótulo dela (`*Endereço:*`, `*1 -*`) + `{ENDERECO}`.
_SOBRA_DO_ENDERECO = re.compile(
    r"(?m)^([ \t]*(?:\*[^*\n]{0,30}\*[ \t]*)?)[^\n]*\{ENDERECO\}[^\n]*-[ \t]*[A-Z]{2}[ \t]*$")


def _mascarar_endereco(texto: str) -> Tuple[str, bool]:
    novo, n = _ENDERECO_POSTAL.subn("{ENDERECO}", texto or "")
    novo, n2 = _SOBRA_DO_ENDERECO.subn(lambda m: m.group(1) + "{ENDERECO}", novo)
    return novo, bool(n or n2)


# ── a porta única ────────────────────────────────────────────────────────────
def higienizar(playbook: Dict[str, Any], cru: str, esqueletos_dado: set = frozenset(),
               *, nomes_da_sessao: Iterable[str] = ()) -> Tuple[str, Dict[str, bool]]:
    """`templatize` + as duas exceções da §6.4. A ordem importa.

    🔴 Mascarar ANTES de qualquer `_norm` (SPEC-084 §2.5.1.3): senão a mesma tela
    vira várias, uma por nome de atendente, e a contagem de sessões se fragmenta
    em silêncio.
    """
    # 🔴 SPEC-121 F3 · a apresentação da pessoa da seguradora (P-120-12) — sobre o
    #    texto CRU, ANTES do `templatize`: 📊 ele troca o "Meu" de "Olá! Meu nome é
    #    X" por `{NOME}` (vocativo depois de saudação) e deixa o X — a apresentação
    #    precisa ser lida enquanto ainda tem a forma dela.
    sem_apresentacao, houve_apres = _mascarar_apresentacao(cru)
    mascarado = M.templatize(sem_apresentacao)
    mascarado, houve_senha = _preservar_capturas(playbook, cru, mascarado)
    mascarado, houve_vocativo = _mascarar_vocativo(mascarado, esqueletos_dado)
    mascarado, houve_nome = _mascarar_nomes_conhecidos(mascarado, nomes_da_sessao)
    # 🔴 SPEC-121 F3 · o endereço que sobrou pela metade
    mascarado, houve_end = _mascarar_endereco(mascarado)
    return mascarado, {"endereco_mascarado": houve_end,
                       "senha_preservada": houve_senha,
                       "vocativo_mascarado": houve_vocativo,
                       "nome_da_sessao_mascarado": houve_nome,
                       "apresentacao_mascarada": houve_apres}
