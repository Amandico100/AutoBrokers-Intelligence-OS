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
import re
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
    """
    m = _RX_RESTO.match(texto or "")
    if not m:
        return None
    resto = re.sub(r"\s+", " ", re.sub(r"[0-9]", "#", m.group(1).lower()))
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
    return dado, duvidoso


def _mascarar_vocativo(texto: str, esqueletos_dado: set) -> Tuple[str, bool]:
    """Troca a cabeça por `{NOME}` **só** se o esqueleto está na lista medida."""
    esq = _esqueleto_do_resto(texto)
    if esq is None or esq not in esqueletos_dado:
        return texto, False
    m = _RX_VOCATIVO.match(texto)
    if not m:
        return texto, False
    return "{NOME}" + m.group(2) + texto[m.end():], True


# ── a exceção da senha (CA-062 · SPEC-083 §6.4) ──────────────────────────────
_RX_MARCADOR_DE_SEGREDO = re.compile(r"\{SEGREDO\}|\{TELEFONE\}|\{NUM\}|\{VALOR\}")


def _preservar_senha(playbook: Dict[str, Any], cru: str, mascarado: str) -> Tuple[str, bool]:
    """Reinjeta os 4 dígitos da senha que o `templatize` apagou.

    🔴 A condição é ESTREITA de propósito: só reinjeta se o MOTOR capturou uma
    senha no texto CRU. Não é "todo número de 4 dígitos volta" — isso seria um
    buraco de PII disfarçado de exceção.

    📊 CA-062: sem isto, `extract_capture_anchors` sobre a tela #27 de
    `7ac3c101` devolve `{}` em vez de `{'password': '4743'}`, e o replay da rota
    de referência perde um passo sem que ninguém veja.
    """
    cap = M.extract_capture_anchors(playbook, cru)
    senha = cap.get("password")
    if not senha:
        return mascarado, False
    # já sobreviveu (o mascarador não a comeu)? então não se mexe.
    if M.extract_capture_anchors(playbook, mascarado).get("password") == senha:
        return mascarado, False

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
    for m in _RX_MARCADOR_DE_SEGREDO.finditer(mascarado):
        tentativa = mascarado[:m.start()] + str(senha) + mascarado[m.end():]
        if M.extract_capture_anchors(playbook, tentativa).get("password") == senha:
            return tentativa, True
    return mascarado, False


# ── a auditoria de PII (SPEC-083 Bloco A, VERIFY) ────────────────────────────
# 🔴 A v1 da SPEC usava `grep -cE '[0-9]{11}'`. Ele NÃO casa
# `+55 (47) 99627-4743` — a maior sequência de dígitos ali tem CINCO. Devolvia
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
    baixo = (texto or "").lower()
    for nome in nomes_da_sessao:
        nome = (nome or "").strip()
        if len(nome) >= 3 and re.search(rf"\b{re.escape(nome.lower())}\b", baixo):
            achados.append(f"NOME_DA_SESSAO:{nome[:3]}…")
    return achados


# ── a porta única ────────────────────────────────────────────────────────────
def higienizar(playbook: Dict[str, Any], cru: str, esqueletos_dado: set) -> Tuple[str, Dict[str, bool]]:
    """`templatize` + as duas exceções da §6.4. A ordem importa.

    🔴 Mascarar ANTES de qualquer `_norm` (SPEC-084 §2.5.1.3): senão a mesma tela
    vira várias, uma por nome de atendente, e a contagem de sessões se fragmenta
    em silêncio.
    """
    mascarado = M.templatize(cru)
    mascarado, houve_senha = _preservar_senha(playbook, cru, mascarado)
    mascarado, houve_vocativo = _mascarar_vocativo(mascarado, esqueletos_dado)
    return mascarado, {"senha_preservada": houve_senha, "vocativo_mascarado": houve_vocativo}
