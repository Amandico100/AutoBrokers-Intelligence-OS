"""Transcript cru -> transcript MASCARADO, com as funções de produção.

Por que este arquivo existe
---------------------------
A destilação das 6.118 conversas restantes da Resulta custaria ~US$ 80 de API
— dinheiro que o projeto não tem em 29/07/2026. A alternativa é fazer a parte
cara (ler a conversa e escrever o conhecimento) com o plano Max, por fora, e
devolver o resultado ao sistema pelo mesmo caminho de sempre.

Para isso o texto precisa sair do banco e ser lido por um subagente. E aí vale
a mesma regra de sempre: **PII nunca chega a um modelo**. Este script é o
portão. Ele não reimplementa nada — importa `sem_copias` e `templatize`, as
MESMAS funções que `_load_session_text_sync` usa em produção. Se o mascaramento
melhorar lá, melhora aqui no mesmo commit.

Reimplementar o mascaramento aqui seria criar um segundo motor de PII que
envelheceria em silêncio — exatamente o que o CLAUDE.md §5 proíbe.

Uso
---
    python mascarar.py < cru.json > mascarado.jsonl

Entrada: JSON com [{session_id, direction, msg_type, text, wa_timestamp}, ...]
Saída:   uma linha JSON por sessão: {"id": ..., "conversa": "CLIENTE: ..."}
"""

from __future__ import annotations

import importlib.util
import json
import re
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# O `app/__init__.py` real arrasta openai e pydantic_settings, que não existem
# na máquina do Founder. O templater e o `sem_copias` não dependem de nada —
# são carregados por caminho, sobre pacotes de fachada.
for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(nome: str):
    caminho = os.path.join(RAIZ, "app", "services", "atlas", f"{nome}.py")
    spec = importlib.util.spec_from_file_location(f"app.services.atlas.{nome}", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"app.services.atlas.{nome}"] = mod
    spec.loader.exec_module(mod)
    return mod


_TEMPLATER = _carregar("templater")
templatize = _TEMPLATER.templatize
# A MESMA regra que decide `{NOME}` em produção. Importada, nunca reescrita:
# uma segunda definição de "isto é um nome" divergiria da primeira no dia em
# que uma delas fosse corrigida, e a que envelhece é sempre a que ninguém olha.
NOME_NA_SAUDACAO = _TEMPLATER.NOME_NA_SAUDACAO
sem_copias = _carregar("mensagem").sem_copias


def _carregar_servico(nome: str):
    caminho = os.path.join(RAIZ, "app", "services", f"{nome}.py")
    spec = importlib.util.spec_from_file_location(f"app.services.{nome}", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"app.services.{nome}"] = mod
    spec.loader.exec_module(mod)
    return mod


# A chave canônica da seguradora vem do MESMO normalizador dos corredores —
# `corridor_playbooks` não importa nada pesado, então carrega por caminho igual
# ao templater. Reescrever a tabela de apelidos aqui criaria a terceira cópia
# dela no projeto, e a que envelhece primeiro é sempre a que ninguém olha.
normalize_insurer_key = _carregar_servico("corridor_playbooks").normalize_insurer_key

# O mesmo teto de produção: acima disto a conversa é cortada, e o corte tem de
# ser idêntico ao que o destilador faria — senão o conhecimento extraído aqui
# seria diferente do extraído lá, sem ninguém saber qual dos dois está certo.
TETO = 7000


# Os quatro papéis que este projeto sabe escrever num transcript. `CLIENTE` e
# `ATENDENTE` vêm do acervo de atendimento (corretora ↔ segurado); `NOS` e
# `SEGURADORA` vêm do acervo observado (corretora ↔ URA da seguradora).
#
# Esta lista NÃO é decoração: `remascarar` precisa reconhecer o prefixo para
# arrancá-lo ANTES de chamar o templatize. `SEGURADORA: Por favor, informe o
# CPF do titular` casa em `_LABELED_VALUE` pelo pedaço `segurado` — o rótulo
# vira grupo 1, o resto da linha vira "valor", e a frase inteira colapsa em
# `SEGURADO{VALOR}`. A instrução da seguradora, que é o conhecimento que este
# acervo existe para extrair, some junto. É o mesmo defeito de 29/07/2026 que
# colapsava a fala do CLIENTE, com outro rótulo.
_QUEM = re.compile(r"^(CLIENTE|ATENDENTE|NOS|SEGURADORA): ?(.*)$")


def remascarar(conversa: str) -> str:
    """Passa o portão CORRIGIDO por cima de um transcript já montado.

    NUNCA chame `templatize` direto num transcript inteiro. `cliente` está na
    lista de rótulos do `_LABELED_VALUE`, e a regra é ancorada em início de
    linha: `CLIENTE: meu vidro trincou ontem` casa como "rótulo: valor" e a
    fala inteira do segurado vira `{VALOR}`.

    Foi o que eu fiz em 29/07/2026, três vezes, ao reaplicar o mascarador nos
    lotes pendentes depois de cada conserto de PII. O subagente do lote 013
    percebeu: "a mascaração de origem colapsa quase toda fala do CLIENTE em
    {VALOR}, o que impede reconstruir `perguntas_na_ordem` e derruba o teto de
    fatos extraíveis". Consertando vazamento eu estava apagando conhecimento.

    Aqui o prefixo é retirado, o texto da mensagem é mascarado como em
    produção — uma mensagem de cada vez, que é o único jeito que o
    `_LABELED_VALUE` foi desenhado para ver — e o prefixo volta.
    """
    saida = []
    for linha in str(conversa or "").split("\n"):
        m = _QUEM.match(linha)
        if m:
            saida.append(f"{m.group(1)}: {templatize(m.group(2))}")
        else:
            saida.append(templatize(linha))
    return "\n".join(saida)


def transcript(eventos: list) -> str:
    linhas = []
    for e in sem_copias(eventos):
        quem = "ATENDENTE" if e.get("direction") == "out" else "CLIENTE"
        txt = str(e.get("text") or "").strip() or f"[{e.get('msg_type') or 'midia'}]"
        linhas.append(f"{quem}: {templatize(txt)}")
    return "\n".join(linhas)[:TETO]


# `interactive` guarda o clique do humano. As três chaves abaixo são as ÚNICAS
# que podem ser lidas. `raw_out` é a mensagem waE2E crua da nossa ponta e
# `raw_keys` é a lista de chaves do envelope — a primeira carrega tudo o que o
# humano escreveu, sem passar por parser nenhum, e é por onde a PII entraria
# inteira se a leitura fosse genérica. Lista fechada, e não `for k in dict`.
_ROTULO_DO_CLIQUE = ("title", "button_label", "selected")


def _fala(e: dict) -> str:
    """O texto de UM evento observado, ainda sem máscara e sem prefixo.

    Para `buttons` e `list` vindos da seguradora, o `text` gravado já traz o
    corpo E as opções ("Botão 1: Guincho", os títulos da lista) — quem monta
    isso é `evolution_inbound._interactive_from_message`, na entrada. O menu
    não precisa ser remontado aqui, e remontá-lo seria a segunda régua do que
    é uma tela.

    O que falta no `text` é a nossa ESCOLHA: 📊 937 dos 1.861 `button_reply`
    têm texto vazio, e o rótulo do que foi clicado está em `interactive.title`.
    Sem esta linha, metade dos cliques vira `[button_reply]` e o transcript
    perde o caminho percorrido dentro da URA — que é o objeto do acervo.

    Sem rótulo em lugar nenhum, a fala é `[clique sem rótulo]`. Escrever o id
    opaco no lugar faria o destilador ler `btn_3a9f` como se a seguradora
    tivesse dito isso: rótulo não se inventa.
    """
    txt = str(e.get("text") or "").strip()
    if txt:
        return txt
    inter = e.get("interactive")
    if isinstance(inter, dict):
        for chave in _ROTULO_DO_CLIQUE:
            v = str(inter.get(chave) or "").strip()
            if v:
                return v
        if str(e.get("msg_type") or "").endswith("_reply"):
            return "[clique sem rótulo]"
    return f"[{e.get('msg_type') or 'midia'}]"


# O vocativo: uma palavra capitalizada no COMEÇO da mensagem, seguida de
# vírgula ou exclamação. "Magda, só mais uma informação:" — e também
# "Guincho, borracheiro e chaveiro estão disponíveis", que é o problema.
#
# O prefixo opcional é a metade que faltava: 📊 "Certo, Magda!" e
# "Certo Saionara," escapavam porque a decisão era do bloco inteiro e "certo" é
# interjeição. A interjeição protege a si mesma, não o que vem depois dela.
_VOCATIVO = re.compile(
    r"^(?:(?-i:[A-ZÀ-Ú][a-zà-ú]{2,}),\s+)?"
    r"((?-i:[A-ZÀ-Ú][a-zà-ú]{2,}(?:\s+[A-ZÀ-Ú][a-zà-ú]{2,})?))(?=\s*[,!]\s*)")

# A pergunta da URA que só admite um NOME por resposta. O que vem depois dela,
# do nosso lado, é o nome de uma pessoa — não há segunda leitura possível.
#
#     "Nesse caso, qual é o nome de quem estará na residência?"
#     → NOS: Magda
#
# Nenhuma regra de forma alcança isso: a resposta é uma palavra capitalizada
# solta, igual a "Guincho". Quem sabe o que ela é não é o texto dela, é a
# pergunta que a provocou — e a pergunta está na linha de cima.
_PERGUNTA_POR_NOME = re.compile(
    r"(?i)(?:qual (?:é |e )?o nome|informe o nome|nome (?:completo )?d[eoa] quem|"
    r"nome do respons[áa]vel|com quem (?:falo|estou falando)|"
    r"quem (?:estar[áa]|vai estar|ir[áa] estar) (?:no local|na resid[êe]ncia))")

# INTERJEIÇÃO — a lista de quem NUNCA é nome, ainda que a seguradora não a
# ofereça como opção de menu. 📊 Medida, não imaginada: são as 25 palavras que
# abrem mensagem antes de vírgula nas 319 sessões, somando 750 das 988
# ocorrências. Errar para o lado de deixar uma de fora custa uma palavra de
# recheio virando `{NOME}`; errar para o outro lado custa um nome vazando.
_INTERJEICAO = {
    "ola", "oi", "agora", "certo", "perfeito", "pronto", "entendi", "entendo",
    "somente", "sim", "nao", "desculpe", "desculpa", "claro", "imagina",
    "imagino", "isso", "bom", "boa", "poxa", "correto", "infelizmente",
    "entao", "legal", "opa", "otimo", "olha", "obrigada", "obrigado",
    "exatamente", "compreendi", "disponha", "seguinte", "atualmente",
    "atencao", "prontinho", "beleza", "show", "lamento", "sinto", "atendimento",
}


def _sem_acento(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


# Em quantas SESSÕES distintas uma palavra precisa aparecer como opção para
# contar como vocabulário de menu.
#
# 📊 Medido em 06/08/2026, e é o número que separa as duas nuvens sem tocar
# nenhuma delas:
#
#     opção de verdade   chaveiro 164 · guincho 105 · roubo 59 · vidros 56 ·
#                        limpeza 55 · reboque 37 · reparo 33 · coberturas 21 ·
#                        roda 7 · elogios 4
#     nome de pessoa     joao 3 · maria 2 · paulo 2 · jose 2 · carlos 1 ·
#                        magda 0 · alvaro 0 · juliana 0 · rafael 0 · saionara 0
#
# Sem o limiar, um nome entrava no vocabulário porque a URA o ECOA dentro de
# uma linha de lista — "Falar sobre {PROTOCOLO}-CHAVEIRO" e o nome do titular
# viram títulos de opção. Uma opção de verdade se repete entre conversas de
# gente diferente; um eco aparece uma vez, na conversa de quem foi ecoado.
_MIN_SESSOES_DA_OPCAO = 4


def vocabulario_de_menu(eventos: list, min_sessoes: int = _MIN_SESSOES_DA_OPCAO) -> frozenset:
    """As palavras que as SEGURADORAS publicam como opção de menu, no acervo.

    Serve para responder a uma pergunta só: "Roubo," no começo de uma mensagem
    é o nome de alguém ou uma opção de menu?

    A resposta não se adivinha — pergunta-se à própria seguradora. Ela já
    escreveu o rótulo literal de cada botão e de cada linha de lista que mandou:
    em `interactive.options` quando o menu é nativo, e no texto da tela quando
    é menu numerado, que `cartographer.parse_options` sabe ler. É o MESMO leitor
    de opções do Atlas — um segundo entendimento de "o que é uma opção" faria
    esta máscara e o mapa da URA discordarem sobre a mesma tela.

    📊 Medido em 06/08/2026 sobre os 19.421 eventos: 585 palavras distintas só
    de `interactive.options`. Com as duas fontes somadas, as 9 palavras de
    controle (Guincho, Roubo, Chaveiro, Vidros, Reparo, Reboque, Coberturas,
    Limpeza, Elogios) sobrevivem, e restam 220 ocorrências para mascarar — que
    são os nomes.

    A unidade é o ACERVO, não a sessão. Testei a sessão primeiro: "Roubo" e
    "Chaveiro" aparecem como vocativo em conversas onde o menu que os ofereceu
    não está — a seguradora ecoa a escolha várias telas depois. Sessão é
    pequena demais para conter o vocabulário dela mesma.
    """
    from app.services.cartographer import parse_options

    sessoes_da_palavra: dict = {}

    def _guardar(rotulo, sid: str) -> None:
        for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", str(rotulo or "")):
            sessoes_da_palavra.setdefault(_sem_acento(w), set()).add(sid)

    for e in eventos:
        if str(e.get("direction")) != "in":
            continue          # só o que a SEGURADORA ofereceu é menu dela
        sid = str(e.get("session_id") or id(e))
        inter = e.get("interactive")
        if isinstance(inter, dict):
            for o in inter.get("options") or []:
                _guardar(o.get("title") if isinstance(o, dict) else o, sid)
            _guardar(inter.get("button_label"), sid)
        texto = str(e.get("text") or "")
        if texto:
            for rotulo in parse_options(texto):
                _guardar(rotulo, sid)
    return frozenset(p for p, s in sessoes_da_palavra.items() if len(s) >= min_sessoes)


def _nomes_ditos_na_sessao(eventos: list) -> list:
    """Os tokens que a regra da saudação já reconheceu como nome NESTA sessão.

    O problema que isto resolve
    --------------------------
    A URA da seguradora cumprimenta pelo nome uma vez — "Olá, Magda" — e depois
    volta a usar o nome como vocativo, sem saudação nenhuma: "Magda, só mais uma
    informação:". O `templatize` mascara a primeira e não tem como alcançar a
    segunda, porque a segunda não tem marca nenhuma de que é nome. Ela é uma
    palavra capitalizada seguida de vírgula, igual a "Guincho, borracheiro e
    chaveiro".

    Três hipóteses foram medidas em 06/08/2026 sobre as 319 sessões
    substanciais, e as três primeiras foram REFUTADAS pela própria medição:

    | hipótese | o que dizia | o que a medição mostrou |
    |---|---|---|
    | forma | capitalizada + vírgula é nome | 76% dos casamentos eram menu: Roubo 21×, Guincho 28×, Chaveiro 9× |
    | raridade | nome aparece em poucas sessões | "Saionara" em 97 sessões, "Microondas" em 9 — as nuvens se tocam |
    | vocativo puro | nome só aparece como vocativo | Roubo, Chaveiro, Vidros e Coberturas caíram no mesmo balde |

    A quarta é de outra espécie: ela **não inventa critério nenhum**. Pergunta à
    regra que já existe quem ELA chamou de nome nesta conversa, e mascara as
    outras aparições daquele mesmo token. Falso positivo novo: zero por
    construção — se a saudação não reconheceu, nada acontece.

    📊 Medido em 06/08/2026: 156 das 319 sessões têm nome reconhecido pela
    saudação; **342 aparições a mais** seriam mascaradas em 126 sessões; e o
    CONTROLE — quantas dessas palavras são vocabulário de menu — deu **zero**.

    O que ela NÃO resolve: as 163 sessões em que a URA nunca cumprimentou pelo
    nome. Lá o vocativo continua passando, e não há regra determinística que o
    separe de uma opção de menu. Está registrado em PENDENCIAS.
    """
    nomes: set = set()
    for e in eventos:
        for m in NOME_NA_SAUDACAO.finditer(str(e.get("text") or "")):
            for token in m.group(3).split():
                # Três letras é o mínimo que a própria regra da saudação aceita.
                # Abaixo disso o token casaria dentro de palavra e apagaria prosa.
                if len(token) >= 3:
                    nomes.add(token)
    # Mais longo primeiro: "Carlos Humberto" antes de "Carlos", senão sobra
    # " Humberto" solto na linha.
    return sorted(nomes, key=len, reverse=True)


def transcript_seguradora(eventos: list, vocabulario: frozenset = frozenset()) -> str:
    """Transcript de uma conversa com a URA da SEGURADORA. Sem corte.

    `vocabulario` é o vocabulário de menu do ACERVO INTEIRO, calculado uma vez
    por `vocabulario_de_menu` e passado aqui. Sem ele, a sessão só conhece o
    próprio menu — e o teste mostrou que isso não basta.

    Duas diferenças em relação a `transcript`, e as duas são de leitura, não
    de proteção — a máscara é a mesma `templatize`, uma mensagem por vez, com
    o prefixo colado DEPOIS (é o que impede o `_LABELED_VALUE` de comer a
    linha inteira).

    **Os papéis se invertem.** Aqui `direction="out"` é a corretora acionando
    e `direction="in"` é a seguradora respondendo. Chamar a seguradora de
    `CLIENTE`, como faz o acervo de atendimento, faria o destilador ler o robô
    da Porto como se fosse um segurado — o erro que a regra 8 do
    `PROMPT-DESTILADOR.md` passou cinco destiladores para descobrir. Aqui o
    rótulo já sai certo da fonte.

    **Não há teto.** `TETO = 7000` existe porque em produção o transcript entra
    num prompt junto com o resto. 📊 Medido em 06/08/2026: 82 das 320 sessões
    substanciais (26%) passam de 7.000 caracteres e a maior tem 81.760. Cortar
    aqui, em silêncio, jogaria fora um quarto do material — e o fim de uma
    conversa com URA é onde mora o desfecho (para onde ela mandou, o que ela
    recusou). Quem corta é o exportador, que sabe dizer o que cortou.
    """
    unicos = sem_copias(eventos)
    nomes = _nomes_ditos_na_sessao(unicos)
    vocativos = [re.compile(rf"(?-i:\b{re.escape(n)}\b)") for n in nomes]
    # Só o vocabulário do ACERVO. Um vocabulário local à sessão seria pior que
    # nenhum: a lista da própria conversa ecoa o nome do titular como título de
    # linha, e o nome entraria no vocabulário que deveria denunciá-lo.
    menu = vocabulario or frozenset()
    linhas = []
    perguntaram_nome = False
    for e in unicos:
        txt = templatize(_fala(e))
        for rx in vocativos:
            txt = rx.sub("{NOME}", txt)

        # A resposta a uma pergunta por nome é um nome, venha na forma que vier.
        de_nos = e.get("direction") == "out"
        if perguntaram_nome and de_nos and txt and not txt.startswith("["):
            txt = "{NOME}"
        if not de_nos:
            perguntaram_nome = bool(_PERGUNTA_POR_NOME.search(txt))
        # O vocativo que a saudação NÃO denunciou: mascara-se o que a
        # seguradora nunca ofereceu como opção e não é interjeição.
        #
        # PALAVRA POR PALAVRA, e não o casamento inteiro. 📊 "Certo Saionara,"
        # e "Certo Soraia," (4 ocorrências) escapavam quando a decisão era do
        # bloco: "certo" é interjeição, o bloco era poupado, e o nome ia junto
        # de carona. A interjeição protege a si mesma, não o que vem depois.
        m = _VOCATIVO.match(txt)
        if m:
            palavras = m.group(1).split()
            trocadas = ["{NOME}" if (_sem_acento(p) not in menu
                                     and _sem_acento(p) not in _INTERJEICAO)
                        else p for p in palavras]
            if trocadas != palavras:
                txt = txt[:m.start(1)] + " ".join(trocadas) + txt[m.end(1):]
        linhas.append(f"{'NOS' if e.get('direction') == 'out' else 'SEGURADORA'}: {txt}")
    return "\n".join(linhas)


def main() -> int:
    linhas = json.load(sys.stdin)
    por_sessao: dict = {}
    for e in linhas:
        por_sessao.setdefault(str(e.get("session_id")), []).append(e)

    escritas = curtas = 0
    for sid, eventos in por_sessao.items():
        texto = transcript(eventos)
        if len(texto) < 80:          # mesma regra do destilador: sessão sem conteúdo
            curtas += 1
            continue
        sys.stdout.write(json.dumps({"id": sid, "conversa": texto}, ensure_ascii=False) + "\n")
        escritas += 1
    print(f"[mascarar] {escritas} conversas · {curtas} curtas demais (puladas)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
