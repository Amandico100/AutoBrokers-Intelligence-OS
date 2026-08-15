"""SPEC-038 ATLAS — Tecelão/Weaver v2 (Bloco B + fidelidade de sequência).

╔══════════════════════════════════════════════════════════════════════════╗
║  O MAPA QUE ESTE ARQUIVO CONSTRÓI É UM SÓ, E É DE TODAS AS CORRETORAS.  ║
╚══════════════════════════════════════════════════════════════════════════╝

Decisão do Founder, 15/08/2026. Leia
`docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` antes de mexer aqui.

Não existe "o mapa da Resulta" nem "o mapa da AutoFleet". Existe **o mapa**, da
AutoBrokers, que todas as corretoras preenchem juntas. `ura_maps` não tem
`company_id` **de propósito**: agregar entre corretoras é o produto, não um
vazamento. A URA da Porto é a mesma para quem entrou em julho e para quem entrar
em dezembro — quem descobre uma rota, descobre para todo mundo.

O objetivo é um só: o agente **saber a pergunta antes de ela chegar**. Sabendo,
ele já tem a resposta pronta e não trava com um segurado esperando guincho. Por
isso **quanto mais rotas, melhor**, e por isso rota que já existe é descartada e
rota nova entra.

🔴 O QUE NUNCA PODE ENTRAR NO MAPA — e não é por privacidade:

    identidade de CORRETORA ou de ATENDENTE (nome, razão social, apelido)

O agente de atendimento é GLOBAL; quem personaliza é o dashboard, com dados de
configuração, em tempo de execução. Um nó que diga "Saionara - Resulta" está
errado por ser **específico onde tinha de ser neutro** — e faz o agente da
corretora seguinte se apresentar com o nome de outra empresa.

📊 Em 15/08/2026 havia 14 nós de mapas ativos com nome de corretora sem redação,
e o redator era inconsistente: "Maria Regina - Autofleet" virava
"Maria {NOME} - {CORRETORA}" (o primeiro nome escapava) e "Saionara - Resulta"
passava inteiro. Ver PENDENCIAS.md#P-165.

⚠️ Dado de segurado (CPF, CNPJ, placa, telefone) é regra SEPARADA — CLAUDE.md §7
— e vale para os nós **e para as arestas**. 📊 Em 15/08 os nós estavam mascarados
e as arestas não, com 141 CPF gravados como rótulo de aresta (P-162).

O teste que separa os dois casos, para qualquer campo novo:

    descreve a SEGURADORA?               → é do Atlas, é global, agregue
    descreve a CORRETORA ou quem atende? → NÃO entra, vem da configuração


Lê as sessões observadas e TECE o mapa da URA: cada tela da URA vira um nó (com
as opções que ela oferece); a escolha do humano (evento 'out' entre duas telas)
vira a aresta rotulada A→B. Sem a escolha capturada, cria aresta SEQUENCIAL
inferida (menor confiança) para a árvore ainda se formar.

v2 (founder 18/07 — "a sequência precisa ser fiel à seguradora"):
- Sessões processadas em ORDEM CRONOLÓGICA; cada nó/aresta ganha `order`
  (primeira vez em que apareceu) — a árvore renderiza na sequência real.
- RAIZ = a tela por onde as sessões mais COMEÇAM (saudação), não a primeira
  processada por acaso.
- `paths` = transcript fiel (templatizado, sem PII) das últimas sessões, para
  o modal "Sequência escrita".
- Casamento FUZZY clique×opção: o buttonText do clique ("Chaveiro") casa com o
  rótulo formatado da tela ("*7 -* *Chaveiro*") por normalização.
- VARIANTES: mesma escolha levando a telas diferentes em sessões diferentes
  (ex.: seguradora já tem o telefone salvo) ficam registradas com contagem.

Merge ACUMULATIVO em ura_maps (source='observed'). Qualidade sobre pressa:
ambíguo não é chutado — vira aresta inferida de baixa confiança.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIRM_THRESHOLD = 2  # aresta vista ≥2x = confirmada
_MAX_PATHS = 12         # transcripts guardados p/ o modal


def _norm_label(label: str) -> str:
    """Normaliza rótulo p/ casar clique×opção: sem acento/asterisco/número/pontuação."""
    s = unicodedata.normalize("NFKD", str(label or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"[^a-z]", "", s)
    return s


def _norm_frase(texto: str) -> str:
    """Normaliza PRESERVANDO a fronteira de palavra — e é essa a diferença.

    `_norm_label` apaga tudo que não é letra, inclusive o espaço: "para manhã"
    vira `paramanha`, que CONTÉM `amanha`. Foi assim que o eco decidiu, no mapa
    da Bradesco em produção, que a pessoa escolheu *Amanhã* — quando a tela
    seguinte só dizia "*06:00* para manhã".

    Aqui o espaço vira separador e sobrevive. Comparar ` amanha ` com
    ` para manha ` não casa, que é a resposta certa. Os dígitos ficam: "02
    (duas) unidades" precisa deles para casar com o eco da tela seguinte.
    """
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def _sem_numero_de_opcao(label: str) -> str:
    """Tira o "7 - " de "7 - Chaveiro". Mesma regra do `cartographer`: a tela
    seguinte ecoa a PALAVRA ("precisa do *chaveiro*?"), nunca o número."""
    return re.sub(r"^\s*\d{1,2}\s*[-–.)\]]\s*", "", str(label or "")).strip()


def _so_placeholder(label: str) -> bool:
    """O rótulo é só PII mascarada ({CPF}, {CNPJ}, {TELEFONE})?

    A Porto tem uma tela de erro — "digite um *CPF ou CNPJ válido*, conforme
    exemplos abaixo" — cujos "exemplos" o leitor de opções capturou como se
    fossem escolhas de menu. O eco então casava `{CNPJ}` com a palavra "CNPJ"
    da pergunta seguinte e gravava uma rota chamada `{CNPJ}`. 📊 Duas arestas
    assim nos mapas de 04/08/2026.

    Valor mascarado não é escolha: ninguém digita "{CNPJ}" para navegar.
    """
    return not re.search(r"[a-zà-ú]", re.sub(r"\{[^}]*\}", " ", str(label or "")), re.IGNORECASE)


def labels_match(option_label: str, click_label: str) -> bool:
    """Esta opção do menu é a que a pessoa escolheu?

    Existem duas formas de escolher, e o casamento tinha só uma.

    **Clique** (lista/botão do WhatsApp): o rótulo volta inteiro, e comparar
    texto com texto resolve.

    **Digitação** (URA de texto, como a Allianz): a pessoa manda **"2"**. O
    rótulo da opção é "2 - Residência, Condomínio ou Empresa". Comparar os dois
    como texto nunca casa — e foi isso que produziu 4% de cobertura sobre
    milhares de atendimentos reais em 28/07/2026.

    O número é a chave. Quando os dois lados têm número, ele decide sozinho:
    "2" e "2 - Residência…" são a mesma escolha, e "2" e "3 - Vida…" não são —
    mesmo que os textos se pareçam.
    """
    from app.services.cartographer import numero_da_opcao

    bruto_clique = str(click_label or "").strip()

    # Caminho do menu digitado. Só vale quando a resposta é SÓ o número: um
    # CPF de 11 dígitos ou um endereço que começa com número não são escolha
    # de menu.
    if bruto_clique.isdigit() and len(bruto_clique) <= 2:
        n_opcao = numero_da_opcao(option_label)
        return n_opcao is not None and n_opcao.lstrip("0") == bruto_clique.lstrip("0")

    a, b = _norm_label(option_label), _norm_label(click_label)
    if not a or not b:
        return False

    # Quando a opção tem número e o clique também, os números têm de bater —
    # senão "1 - Residencial" casaria com "2 - Condomínio" pela semelhança do
    # texto ao redor.
    n_a, n_b = numero_da_opcao(option_label), numero_da_opcao(click_label)
    if n_a and n_b and n_a.lstrip("0") != n_b.lstrip("0"):
        return False

    return a == b or a.endswith(b) or b.endswith(a) or (len(b) >= 4 and b in a) or (len(a) >= 4 and a in b)


# TELA DE ESPERA — a que pede paciência, não a que abre o atendimento.
#
# Deliberadamente estreita: só pega tela CURTA, SEM MENU, que COMEÇA pedindo
# para aguardar. "Aguarde um momento 🙂" entra; "Olá! Enquanto aguarda, veja
# nossas opções: 1 - …" não entra, porque tem menu. Alargar isto custaria uma
# raiz legítima, que é um preço pior do que a raiz errada que ela conserta.
_ESPERA = re.compile(
    r"^(?:aguarde|aguardando|so um momento|um momento|so um instante|um instante|"
    r"so um minuto|um minuto|estamos verificando|estou verificando|"
    r"estamos analisando|estou analisando|ja retorno|ja te respondo)\b")


def _tela_de_espera(node: Dict[str, Any]) -> bool:
    """Esta tela é só um 'já te atendo'? Então ela não é porta de entrada."""
    if node.get("options"):
        return False
    texto = _norm_frase(str(node.get("text") or ""))
    return len(texto) <= 120 and bool(_ESPERA.match(texto))


def _sem_copias(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A mesma regra de identidade que o Destilador usa. Ver `atlas.mensagem`."""
    from app.services.atlas.mensagem import sem_copias

    return sem_copias(events)


def _events_to_steps(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena a sessão e casa cada tela da URA (in) com a resposta humana (out)
    que veio logo depois. Retorna [{screen, choice}]."""
    ordered = sorted(events, key=lambda e: (e.get("wa_timestamp") or "", e.get("created_at") or ""))
    steps: List[Dict[str, Any]] = []
    pending_screen: Optional[Dict[str, Any]] = None
    for ev in ordered:
        if ev.get("direction") == "in":
            if pending_screen is not None:
                steps.append({"screen": pending_screen, "choice": None})
            pending_screen = ev
        else:  # out = escolha do humano
            if pending_screen is not None:
                steps.append({"screen": pending_screen, "choice": ev})
                pending_screen = None
    if pending_screen is not None:
        steps.append({"screen": pending_screen, "choice": None})
    return steps


def _choice_label(choice: Optional[Dict[str, Any]]) -> Optional[str]:
    if not choice:
        return None
    it = choice.get("interactive") or {}
    for k in ("title", "selected"):
        if it.get(k):
            return str(it[k])[:60]
    txt = str(choice.get("text") or "").strip()
    return txt[:60] or None


def weave_session(map_acc: Dict[str, Any], events: List[Dict[str, Any]],
                  session_at: Optional[str] = None) -> Dict[str, Any]:
    """Tece UMA sessão sobre o mapa acumulado (mutação in-place + retorno)."""
    from app.services.atlas.templater import screen_node

    nodes: Dict[str, Any] = map_acc.setdefault("nodes", {})
    edges: Dict[str, Any] = map_acc.setdefault("edges", {})
    starts: Dict[str, int] = map_acc.setdefault("_starts", {})
    steps = _events_to_steps(events)

    # A URA acaba quando entra gente.
    #
    # A Allianz diz "Vou transferir seu caso para um especialista" — 233 vezes
    # nas conversas da Resulta — e dali em diante quem escreve é uma pessoa.
    # "Boa tarde!", "Ok um momento", "Precisa de escada?", "Seria
    # desentupimento": tudo isso entrava no Atlas como se fosse tela de menu.
    #
    # O mapa da Allianz tinha 930 telas quando a URA de verdade tem umas
    # dezenas. O resto era conversa — e conversa não tem rota.
    #
    # As telas continuam sendo guardadas, com `fase="humano"`: elas ensinam
    # como o especialista conduz, e isso vale. O que muda é que param de contar
    # como opção de menu a percorrer, e param de poluir a árvore de navegação.
    #
    # 03/08/2026 — quem responde a pergunta agora é `entrou_humano`, não o
    # regex cru. 📊 Na HDI o regex reconhecia 3 das 23 formas de anunciar
    # transferência (3 de 61 ocorrências), e alargá-lo sem freio marcaria a
    # tela de BOAS-VINDAS como handoff, porque ela OFERECE falar com um
    # analista "caso seja necessário". Ver `cartographer.entrou_humano`.
    from app.services.cartographer import entrou_humano, nao_e_rota

    fase_humana = False

    path_steps: List[Dict[str, Any]] = []
    prev_node_id: Optional[str] = None
    prev_choice: Optional[str] = None
    first = True
    for step in steps:
        texto_bruto = step["screen"].get("text") or ""
        node = screen_node(texto_bruto, step["screen"].get("interactive"))
        nid = node["hash"]
        if nid not in nodes:
            map_acc["_seq"] = int(map_acc.get("_seq") or 0) + 1
            nodes[nid] = {**node, "samples": 0, "order": map_acc["_seq"]}
        nodes[nid]["samples"] += 1

        # CONTA, NÃO CARIMBA.
        #
        # A primeira versão marcava `fase="humano"` na hora e a marca ficava no
        # nó para sempre. Uma sessão é uma janela de DUAS HORAS: o cliente é
        # transferido para o especialista e depois volta a falar com a URA na
        # mesma janela. Bastou isso acontecer uma vez para o MENU PRINCIPAL da
        # Allianz ser carimbado como conversa humana.
        #
        # Medido em 28/07/2026: 782 das 919 telas viraram "humano", incluindo o
        # menu de ramo e mais 55 telas COM MENU. Tela marcada assim é pulada no
        # cálculo de rotas — foi por isso que o Canvas ficou sem nenhuma rota
        # depois da raiz, com tudo laranja.
        #
        # Agora só se CONTA de que lado do handoff a tela apareceu. Quem decide
        # é `compute_coverage`, no fim, com o quadro inteiro na mão.
        chave = "pos_handoff" if fase_humana else "pre_handoff"
        nodes[nid][chave] = int(nodes[nid].get(chave) or 0) + 1
        if not fase_humana and entrou_humano(texto_bruto):
            # A tela que ANUNCIA a transferência ainda é da URA — ela é o fim
            # da rota, e o agente precisa saber que chegou nela.
            nodes[nid]["kind"] = "handoff_humano"
            fase_humana = True

        # NÃO É ROTA — E FICA REGISTRADO POR QUÊ.
        #
        # Pesquisa de satisfação e lista gerada pelo cliente não têm caminho a
        # percorrer. A marca fica NO NÓ, ao lado do texto: apagar o nó
        # destruiria a evidência de que a tela existe e de por que ela não
        # entra na conta. Quem lê a marca é `compute_coverage`.
        motivo = nao_e_rota(texto_bruto)
        if motivo:
            nodes[nid]["nao_rota"] = motivo
        # RECÊNCIA (founder 18/07): guarda a última vez que a tela apareceu — o
        # recente prevalece; telas obsoletas são marcadas depois (compute_coverage).
        st = step["screen"].get("wa_timestamp")
        if st and str(st) > str(nodes[nid].get("last_seen") or ""):
            nodes[nid]["last_seen"] = st
        # funde opções novas que apareceram nesta passagem (mantendo a ordem da URA)
        seen = {o["label"] for o in nodes[nid]["options"]}
        for o in node["options"]:
            if o["label"] not in seen:
                nodes[nid]["options"].append(o)
        if first:
            starts[nid] = starts.get(nid, 0) + 1
            first = False

        # liga a aresta do passo anterior até este nó
        # Uma tela apontando para ELA MESMA, sem escolha capturada, não é rota.
        #
        # Medido em 28/07/2026 nos mapas gravados: 840 das 1.899 arestas da
        # Allianz (44%), 284 das 576 da Porto (49%), 40 das 58 da Tokio (69%).
        # Quase metade das setas do Atlas não levava a lugar nenhum.
        #
        # Vinham das cópias do histórico: a mesma tela gravada três vezes vira
        # A→A→A. E como o destino da aresta sequencial é eleito por maioria
        # (`dests`), o voto de A em si mesma chegava a VENCER o destino real —
        # a seta passava a apontar de volta para a própria tela.
        #
        # Com escolha capturada é diferente e fica: "digitou 9 e voltou pro
        # mesmo menu" é rota de verdade, e o agente precisa saber disso.
        if prev_node_id == nid and prev_choice is None:
            # A escolha DESTE passo continua valendo para o passo seguinte —
            # descartá-la junto com a aresta inútil apagaria uma rota real.
            prev_choice = _choice_label(step["choice"])
            path_steps.append({"n": nid, "c": prev_choice})
            continue

        if prev_node_id is not None:
            label = prev_choice or "→"  # sem escolha capturada = sequencial
            ekey = f"{prev_node_id}|{label}"
            e = edges.get(ekey)
            if e is None:
                map_acc["_seq"] = int(map_acc.get("_seq") or 0) + 1
                e = edges[ekey] = {"src": prev_node_id, "label": label, "to": nid,
                                   "count": 0, "inferred": prev_choice is None,
                                   "order": map_acc["_seq"], "dests": {}}
            e.setdefault("dests", {})
            e["dests"][nid] = e["dests"].get(nid, 0) + 1
            e["to"] = max(e["dests"], key=e["dests"].get)
            e["count"] += 1
            if prev_choice is not None:
                e["inferred"] = False  # escolha real confirma a aresta

        choice_lab = _choice_label(step["choice"])
        path_steps.append({"n": nid, "c": choice_lab})
        prev_node_id = nid
        prev_choice = choice_lab

    if path_steps:
        # AS 12 MAIS RECENTES — e a mais recente por ÚLTIMO.
        #
        # Era `del paths[:-_MAX_PATHS]`, que guarda as 12 ÚLTIMAS ANEXADAS. E o
        # laço de `weave_insurer` é recência-primeiro: as últimas anexadas são
        # as sessões MAIS ANTIGAS do acervo. 📊 Medido em 04/08/2026: a Allianz
        # exibia caminhos de 28/07/2025 a 17/09/2025 com sessão mais nova em
        # 04/08/2026 — onze meses de atraso no modal "Sequência escrita".
        #
        # E o estrago não parava no modal. `route_sentinel._script_from_observed`
        # lê `paths[-1]` chamando-o de "transcript observado mais recente":
        # estava recebendo a conversa MAIS ANTIGA de todas, e era com ela que o
        # Alfaiate montava o script do Simulador. Um menu de um ano atrás
        # decidindo se o playbook de hoje passa.
        #
        # Ordenar por data CRESCENTE conserta os dois de uma vez: sobram as 12
        # mais novas, e `paths[-1]` volta a ser o que o nome promete. Sessão sem
        # data vai para o começo — desconhecido não desloca recente conhecido.
        paths: List[Dict[str, Any]] = map_acc.setdefault("paths", [])
        paths.append({"at": session_at, "steps": path_steps})
        paths.sort(key=lambda p: str(p.get("at") or ""))
        del paths[:-_MAX_PATHS]
    return map_acc


def _prosa_do_destino(dest: Dict[str, Any]) -> str:
    """O texto do destino MENOS o menu que ele próprio oferece.

    Eco é a tela seguinte repetindo a escolha na NARRATIVA — "Certo! Para
    quando precisa do *chaveiro*?". Quando a palavra só aparece porque a tela
    seguinte oferece a MESMA opção de novo, não há eco nenhum: há um botão
    repetido.

    📊 É o defeito que produziu, no mapa da HDI de 04/08/2026:

        "O veículo é elétrico ou híbrido?" --Voltar (5x)--> "O veículo é rebaixado?"
        "Houve vítimas no local?"          --Voltar (6x)--> "A polícia foi acionada?"

    As duas telas são `Sim`/`Não`/`Voltar`. "sim" e "nao" têm 3 letras e caíam
    no piso de 4; sobrava "voltar" — presente no destino porque o destino
    também tem botão Voltar. O que o humano de fato respondeu na primeira: 14
    cliques sem rótulo e 4 "Não". Nenhum "Voltar".
    """
    prosa = " " + _norm_frase(str(dest.get("text") or "")[:240]) + " "
    for o in dest.get("options") or []:
        frase = _norm_frase(_sem_numero_de_opcao(o.get("label") or ""))
        if frase:
            # `(?= )` consome só o espaço da frente: rótulos repetidos em
            # sequência ("ENCANADOR ENCANADOR") continuam sendo alcançados.
            prosa = re.sub(r" " + re.escape(frase) + r"(?= )", " ", prosa)
    return prosa


def label_inferred_edges(map_acc: Dict[str, Any]) -> int:
    """ROTULADOR POR ECO (Bloco C, determinístico — custo zero): em URAs de menu
    DIGITADO (Allianz "*1 -* ...") a escolha não chega por evento; mas a tela
    SEGUINTE costuma ecoar a opção ("Certo! ... *chaveiro* ..."). Se a PROSA do
    destino ecoa EXATAMENTE UMA opção da origem, a aresta ganha esse rótulo —
    **como palpite**, não como escolha capturada.

    Quatro coisas que o eco NÃO pode fazer, cada uma paga com um defeito medido
    em produção em 04/08/2026 (📊 47 arestas `echo` nos 10 mapas observados):

    1. **Não pode chamar navegação de escolha.** 35 das 47 (74%) foram
       rotuladas com Voltar/Sair/menu. Quem sabe o que é navegação é
       `cartographer.acao_conhecida` — a mesma autoridade que a cobertura usa.
       Ela pega até o caso que a regra da prosa não pega: a Porto tem duas
       telas cujo texto É "Se quiser mudar de opção, digite voltar."

    2. **Não pode casar no meio de uma palavra.** Ver `_norm_frase`: "para
       manhã" continha "amanha" e virou a escolha *Amanhã* na Bradesco.

    3. **Não pode achar eco no menu do destino.** Ver `_prosa_do_destino`.

    4. **Não pode zerar `inferred`.** Era o pior: a aresta nascia
       `inferred=False`, e um palpite entrava no mapa com a mesma cara de uma
       escolha que alguém clicou de verdade. Quem lê não tinha como separar as
       duas. Agora `inferred` continua `True` e só `echo=True` diz de onde veio
       o rótulo — `compute_coverage` marca a opção como `confidence="echo"`.

    Sobre o piso de 4 letras, que descarta `sim`/`não`: ele FICA, de propósito.
    Uma URA não ecoa "Sim" — ela ecoa o assunto ("Certo, guincho!"); e num menu
    de botão a escolha chega como evento de clique, então o eco nem é o
    instrumento certo ali. Baixar o piso só faria "Não entendi" casar com a
    opção "Não". O resíduo Sim/Não é trabalho do resolvedor de IA
    (`atlas_parser`), que lê sentido — não do eco, que lê coincidência.

    Ambíguo = não mexe (qualidade>pressa). Retorna quantas arestas rotulou.
    """
    from app.services.cartographer import acao_conhecida

    nodes = map_acc.get("nodes") or {}
    edges = map_acc.get("edges") or {}
    labeled = 0
    for ekey in list(edges.keys()):
        e = edges[ekey]
        if e.get("label") != "→":
            continue
        src, dest = nodes.get(e.get("src")), nodes.get(e.get("to"))
        if not src or not dest or not src.get("options"):
            continue
        prosa = _prosa_do_destino(dest)
        matches: List[str] = []
        for o in src["options"]:
            rotulo = o.get("label") or ""
            if acao_conhecida(rotulo) or _so_placeholder(rotulo):
                continue
            alvo = _norm_frase(_sem_numero_de_opcao(rotulo))
            if len(re.sub(r"[^a-z]", "", alvo)) < 4:
                continue
            if f" {alvo} " in prosa:
                matches.append(rotulo)
        if len(matches) == 1:
            new_label = matches[0]
            new_key = f"{e['src']}|{new_label}"
            if new_key not in edges:
                # `inferred` NÃO é tocado: vem True da aresta sequencial e
                # continua True. Rótulo adivinhado segue sendo palpite.
                edges[new_key] = {**e, "label": new_label, "echo": True}
                del edges[ekey]
                labeled += 1
    return labeled


def compute_coverage(map_acc: Dict[str, Any]) -> Dict[str, Any]:
    """Casa cada OPÇÃO oferecida com a aresta percorrida (fuzzy), marca lacunas,
    variantes e o status de cada nó. Escolhe a RAIZ pela frequência de abertura."""
    from app.services.cartographer import acao_conhecida

    edges = map_acc.get("edges") or {}
    nodes = map_acc.get("nodes") or {}

    # arestas reais (não sequenciais) agrupadas por nó de origem
    by_src: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in edges.values():
        if e.get("label") != "→":
            by_src[e["src"]].append(e)

    # A COBERTURA CONTA OPÇÃO DISTINTA, NÃO OCORRÊNCIA DE OPÇÃO.
    #
    # Isto somava `+= 1` por nó. E a MESMA tela aparece como vários nós, porque
    # a assinatura é o texto inteiro e o texto muda de uma sessão para outra (um
    # nome, um "bom dia", uma linha a mais). Cada cópia trazia as mesmas opções
    # de novo, e as duas parcelas cresciam — só que não na mesma proporção.
    #
    # A tela que mais duplica é justamente a mais percorrida (duplicou porque
    # apareceu em muitas sessões), então o numerador inflava mais que o
    # denominador e a cobertura saía OTIMISTA. Medido em 29/07/2026 com dado
    # real, deduplicando por (menu, rótulo):
    #
    #     Allianz  painel 63%  ->  real 37%      Porto  29% -> 21%
    #     Yelum        32%     ->      24%       HDI    33% -> 23%
    #     Zurich       31%     ->      15%
    #
    # Vinte e seis pontos de otimismo na Allianz. O Founder olhava 63% e via um
    # mapa quase explorado; o mapa está em pouco mais de um terço. Cobertura que
    # mente para cima é pior que cobertura baixa: ela manda parar de explorar.
    #
    # A chave é (conjunto de opções da tela, rótulo da opção). Duas telas que
    # oferecem exatamente as mesmas escolhas são a mesma tela do ponto de vista
    # de navegação, ainda que o cabeçalho traga um protocolo diferente.
    def _chave_de_opcao(label: str) -> str:
        """Identidade da opcao. Preserva o NUMERO — `_norm_label` apaga digitos,
        porque foi feito para casar clique x opcao, e usa-lo como identidade
        fundia "1 - Guincho" com "2 - Guincho". Medido em 29/07/2026: com
        `_norm_label` a Allianz deu 67%, e a medida deduplicada correta era 37%.
        Um conserto de cobertura inflada nao pode inflar por outro caminho."""
        s = unicodedata.normalize("NFKD", str(label or ""))
        s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
        return re.sub(r"[^a-z0-9]", "", s)

    def _assinatura_do_menu(node: Dict[str, Any]) -> str:
        return "|".join(sorted(
            _chave_de_opcao(o.get("label") or "") for o in (node.get("options") or [])))

    universo: set = set()
    percorrido: set = set()
    for nid, node in nodes.items():
        _sig = _assinatura_do_menu(node)
        node_gaps = 0
        # TELA COM MENU É DA URA. SEMPRE.
        #
        # Pessoa nenhuma manda "*1 -* Automóvel *2 -* Residência". Esta é a
        # regra que impede a contaminação: mesmo que a tela só tenha aparecido
        # depois de um handoff, se ela oferece escolha ela é da URA.
        #
        # Fora isso, é da fase humana a tela que NUNCA apareceu antes de um
        # handoff. "Boa tarde!", "Ok um momento", "Precisa de escada?" — texto
        # livre do especialista, que não tem rota a percorrer. Contá-la faria a
        # cobertura cair para sempre: a lacuna nunca fecha porque não há o que
        # clicar.
        e_humana = (not node.get("options")
                    and int(node.get("pos_handoff") or 0) > 0
                    and int(node.get("pre_handoff") or 0) == 0)
        node["fase"] = "humano" if e_humana else "ura"
        if e_humana:
            continue
        # TELA SEM ROTA SAI DOS DOIS LADOS DA FRAÇÃO.
        #
        # A marca vem de `weave_session`/`cartographer.nao_e_rota`. O nó fica
        # no mapa com o texto e o motivo; o que ele não faz é oferecer opção
        # para contar. Esta segunda barreira existe porque as opções podem ter
        # vindo da estrutura `interactive` — que não passa por `parse_options`
        # e portanto escapa do filtro de lá. É o caso da pesquisa da Mapfre,
        # que chega como lista do WhatsApp.
        if node.get("nao_rota"):
            for opt in node.get("options") or []:
                opt["confidence"] = "nao_rota"
                opt["acao"] = node["nao_rota"]
            node["status"] = "nao_rota"
            continue
        for opt in node.get("options") or []:
            _acao_previa = acao_conhecida(opt.get("label") or "")
            if _acao_previa == "nao_e_opcao":
                # Frase de pesquisa de satisfacao e item de lista de documentos
                # nao sao escolha de menu: ninguem digita nada para "escolhe-las".
                # Ficam fora dos DOIS lados da fracao — conta-las como cobertas
                # inflaria, e como lacuna afundaria a cobertura para sempre.
                opt["confidence"] = "nao_e_opcao"
                opt["acao"] = "nao_e_opcao"
                continue
            _chave = (_sig, _chave_de_opcao(opt.get("label") or ""))
            universo.add(_chave)
            match = None
            for e in by_src.get(nid, []):
                if labels_match(opt["label"], e["label"]):
                    match = e
                    break
            acao_desta = acao_conhecida(opt["label"])
            if acao_desta:
                opt["acao"] = acao_desta
            if match:
                opt["leads_to"] = match["to"]
                if match.get("echo"):
                    opt["confidence"] = "echo"  # deduzida pelo eco da tela seguinte
                else:
                    opt["confidence"] = "confirmed" if match.get("count", 0) >= _CONFIRM_THRESHOLD else "seen_once"
                opt["seen_count"] = match.get("count", 0)
                dests = match.get("dests") or {}
                if len(dests) > 1:  # variação real (ex.: já tem telefone salvo)
                    opt["variants"] = sorted(
                        ({"to": d, "count": c} for d, c in dests.items()),
                        key=lambda v: -v["count"])
                percorrido.add(_chave)
            else:
                # OPÇÃO CUJO COMPORTAMENTO JÁ SE CONHECE NÃO É LACUNA.
                #
                # "Voltar" aparece 222 vezes nos mapas e 190 delas contavam
                # como buraco. Ninguém clica em "Voltar" num atendimento real
                # — e se clicasse não ensinaria nada: já se sabe que volta.
                # A lacuna nunca fecharia, e ela afunda a cobertura de todas
                # as seguradoras para sempre.
                #
                # Pior é a escolha de horário: "{DATA} (quarta-feira)" muda de
                # rótulo todo dia, então o mapa de amanhã inventa lacunas novas
                # que ninguém jamais percorre.
                #
                # `acao` também é o que o agente precisa saber: "Voltar" é a
                # saída quando ele errou o caminho, "Sair" é como encerrar sem
                # deixar a conversa pendurada, e qualquer horário serve.
                acao = acao_conhecida(opt["label"])
                if acao:
                    opt["leads_to"] = None
                    opt["acao"] = acao
                    opt["confidence"] = "navegacao"
                    percorrido.add(_chave)
                else:
                    opt["leads_to"] = None
                    opt["confidence"] = "gap"
                    node_gaps += 1
        if node.get("kind") == "app_form":
            node["status"] = "app_form"
        elif not node.get("options"):
            node["status"] = "complete"
        elif node_gaps == 0:
            node["status"] = "complete"
        else:
            node["status"] = "partial"

    # RAIZ fiel: a tela por onde as sessões mais começam — TIRANDO as telas de
    # espera, que não são porta de entrada de nada.
    #
    # 📊 04/08/2026, mapa da Porto em produção: a raiz eleita era
    # "Aguarde um momento 🙂". Ela aparece 93 vezes, mas só 10 das 149 sessões
    # começam nela — e 57 arestas apontam PARA ela. É tela que se recebe no
    # meio do caminho, não tela por onde se chega.
    #
    # Ela venceu por um motivo que não é mérito: é a única candidata que NÃO
    # fragmenta. As aberturas de verdade da Porto trazem o nome do cliente no
    # meio da frase ("Eu estou falando com Fulano?", 20 sessões; "Oi, sou
    # assistente virtual da Porto 👋\n\nFulano, ...", 56 sessões) e o
    # mascarador só cobre nome COLADO na saudação — então cada nome vira um nó
    # com 1 voto, enquanto "Aguarde um momento 🙂" junta os 10 dela num nó só.
    # A causa de raiz é a duplicação de nós; ver PENDENCIAS.
    #
    # ⚠️ Não tente "a raiz é a tela sem aresta entrando". Medido no mesmo dia:
    # 7 das 10 raízes atuais TÊM aresta entrando (porto 57, allianz 21, yelum
    # 7, hdi 7, azul 3, alfa 2, mapfre 1) — a janela de 2h faz a conversa voltar
    # à saudação, e essa regra reprovaria 6 raízes que estão certas.
    starts = map_acc.get("_starts") or {}
    for _nid, _q in starts.items():
        if _nid in nodes:
            nodes[_nid]["starts"] = _q  # a eleição fica auditável no mapa salvo
    if starts:
        elegiveis = {nid: q for nid, q in starts.items()
                     if not _tela_de_espera(nodes.get(nid) or {})}
        urna = elegiveis or starts  # todas de espera? então não há o que trocar
        map_acc["root"] = max(urna, key=urna.get)

    # OBSOLETO: telas cujo last_seen é muito mais antigo que o mais recente do
    # mapa (>60 dias) — provável menu antigo. Marcadas p/ revisão, não apagadas.
    seens = [str(n.get("last_seen")) for n in nodes.values() if n.get("last_seen")]
    if seens:
        newest = max(seens)
        try:
            from datetime import datetime, timezone

            newest_dt = datetime.fromtimestamp(int(newest), tz=timezone.utc) if newest.isdigit() \
                else datetime.fromisoformat(newest.replace("Z", "+00:00"))
            for n in nodes.values():
                ls = str(n.get("last_seen") or "")
                if ls:
                    ls_dt = datetime.fromtimestamp(int(ls), tz=timezone.utc) if ls.isdigit() \
                        else datetime.fromisoformat(ls.replace("Z", "+00:00"))
                    if (newest_dt - ls_dt).days > 60:
                        n["stale"] = True
        except (ValueError, OverflowError, OSError):
            pass
    # A FÓRMULA DA COBERTURA, escrita por inteiro (03/08/2026).
    #
    #                   |{ (menu, opção) que já sabemos percorrer }|
    #     cobertura  =  ───────────────────────────────────────────
    #                   |{ (menu, opção) que SÃO rota a percorrer }|
    #
    # A unidade é o par (assinatura do menu, rótulo da opção) — opção DISTINTA,
    # não ocorrência: a mesma tela vira vários nós quando o texto varia, e
    # contar por nó inflava o numerador mais que o denominador (26 pontos de
    # otimismo na Allianz em 29/07/2026).
    #
    # SAI DOS DOIS LADOS o que não é rota — não conta como coberto nem como
    # lacuna, porque não há nada a percorrer:
    #
    #     nó com `fase="humano"`   conversa do especialista depois do handoff
    #     nó com `nao_rota`        pesquisa de satisfação, lista do cliente
    #     opção `nao_e_opcao`      texto corrido que o leitor pegou por engano
    #
    # ENTRA NOS DOIS LADOS o que é rota de comportamento já conhecido — conta
    # como coberto sem precisar ser percorrido, porque percorrer não ensinaria
    # nada: Voltar, Sair, menu, faixa de horário, escolha de prestador, nota de
    # pesquisa solta, protocolo como rótulo (ver `cartographer.acao_conhecida`).
    #
    # A diferença entre os dois grupos é o que a exploração pode APRENDER.
    # Lacuna que nunca fecha no denominador afunda a cobertura para sempre e
    # manda o Founder explorar o que não existe.
    map_acc["coverage"] = {
        "options_total": len(universo),
        "options_covered": len(percorrido),
        "pct": round(100 * len(percorrido) / len(universo)) if universo else 0,
        "nodes": len(nodes),
        # Separar as duas contagens é o que impede a pergunta "por que 900
        # telas se a URA tem 50?". A URA tem 50; o resto é a conversa com o
        # especialista, que é material valioso e não é rota.
        "nodes_ura": sum(1 for n in nodes.values() if n.get("fase") != "humano"),
        "nodes_humano": sum(1 for n in nodes.values() if n.get("fase") == "humano"),
        # A terceira pilha, que antes se escondia dentro de "URA": telas que
        # existem, foram capturadas, e não são caminho — pesquisa e lista do
        # cliente. Separadas para que ninguém as procure como rota que falta.
        "nodes_nao_rota": sum(1 for n in nodes.values() if n.get("nao_rota")),
    }
    return map_acc


async def weave_insurer(insurer_key: str, ramo: str = "auto", company_id: Optional[str] = None,
                        use_ai: bool = False) -> Dict[str, Any]:
    """Reconstrói o mapa observado de uma seguradora×ramo a partir de TODAS as
    sessões capturadas (recência-primeiro) e salva como observed. Idempotente.
    use_ai=True liga o resolvedor de IA no resíduo ambíguo (custa; só na
    passada oficial da Sentinela, não no 'Tecer' manual)."""
    from app.core.database import get_supabase_client
    from app.services.atlas.templater import infer_ramo_servico

    supabase = get_supabase_client()

    # O PostgREST devolve no máximo 1.000 linhas por consulta, em silêncio.
    #
    # Isto custou caro em 28/07/2026. O laço abaixo pedia os eventos em lotes de
    # 50 sessões e confiava no que voltava. Com o histórico da Resulta:
    #
    #     Allianz .. 81 sessões, 2 lotes  ->  2.000 eventos de 4.986
    #     Porto .... 38 sessões, 1 lote   ->  1.000 eventos de 1.009
    #
    # O mapa da Allianz foi construído sobre 40% do material, e o número
    # gravado em `meta.events` era exatamente 2000 — redondo demais para ser
    # coincidência, e ninguém olhou.
    #
    # Truncar em silêncio é o pior defeito que um leitor pode ter: o mapa não
    # parecia quebrado, parecia pequeno. E "pequeno" a gente atribui a "a
    # corretora usou pouco".
    _PAGINA = 1000

    def _pagina_tudo(query_fn) -> List[Dict]:
        """Lê TODAS as páginas até a fonte secar. Nunca devolve pela metade."""
        tudo: List[Dict] = []
        inicio = 0
        while True:
            lote = (query_fn().range(inicio, inicio + _PAGINA - 1).execute().data) or []
            tudo.extend(lote)
            if len(lote) < _PAGINA:
                return tudo
            inicio += _PAGINA
            if inicio > 500_000:
                # Trava de segurança. Se um dia chegarmos aqui, é bug de laço,
                # não volume real — e é melhor gritar no log do que girar.
                logger.error("[ATLAS WEAVER] paginação passou de 500k linhas em "
                             "'%s' — interrompendo", insurer_key)
                return tudo

    def _load() -> Tuple[List[Dict], List[Dict]]:
        def _sessoes():
            q = (supabase.client.table("observed_sessions")
                 .select("id, started_at, ramo, servico")
                 .eq("insurer_key", insurer_key).order("started_at", desc=False))
            return q.eq("company_id", company_id) if company_id else q

        sessions = _pagina_tudo(_sessoes)
        sess_ids = [s["id"] for s in sessions]

        events: List[Dict] = []
        for i in range(0, len(sess_ids), 50):
            batch = sess_ids[i:i + 50]

            def _eventos(b=batch):
                return (supabase.client.table("observed_events")
                        .select("session_id, direction, msg_type, text, "
                                "interactive, wa_timestamp, created_at")
                        .in_("session_id", b)
                        # A ordem é obrigatória para paginar: sem `order`, o
                        # Postgres não garante a mesma sequência entre páginas,
                        # e a paginação passa a pular e repetir linhas.
                        .order("created_at", desc=False))

            events.extend(_pagina_tudo(_eventos))
        return sessions, events

    sessions, events = await asyncio.to_thread(_load)
    if not events:
        return {"ok": False, "error": "sem eventos observados", "insurer_key": insurer_key}

    events = _sem_copias(events)

    by_session: Dict[str, List[Dict]] = defaultdict(list)
    for e in events:
        by_session[e.get("session_id")].append(e)

    map_acc: Dict[str, Any] = {"root": None, "nodes": {}, "edges": {}}
    # RECÊNCIA-PRIMEIRO (founder 18/07): a conversa MAIS RECENTE define a
    # estrutura/ordem canônica; as antigas só somam cobertura. Menus obsoletos
    # não contaminam a sequência do fluxo atual.
    sessions_recent_first = sorted(sessions, key=lambda s: str(s.get("started_at") or ""), reverse=True)
    for sess in sessions_recent_first:
        evs = by_session.get(sess["id"])
        if evs:
            weave_session(map_acc, evs, session_at=sess.get("started_at"))

    all_labels: List[str] = []
    for node in map_acc["nodes"].values():
        all_labels.extend(o["label"] for o in node.get("options") or [])
    inferred_ramo, _servico = infer_ramo_servico(all_labels, " ".join(
        n["text"] for n in list(map_acc["nodes"].values())[:20]))
    ramo_final = ramo or inferred_ramo or "auto"

    echoes = label_inferred_edges(map_acc)  # Bloco C: rotula menus digitados pelo eco
    if echoes:
        logger.info(f"[ATLAS WEAVER] {insurer_key}: {echoes} rotas rotuladas por eco")
    compute_coverage(map_acc)
    # RESOLVEDOR DE IA (modelo forte): só o resíduo ambíguo que o eco não pegou.
    # OPT-IN (custo): só na passada oficial da Sentinela, não no 'Tecer' manual.
    if use_ai:
        try:
            from app.services.atlas.atlas_parser import resolve_typed_choices

            await resolve_typed_choices(map_acc, insurer_key)
        except Exception as e:  # noqa: BLE001
            logger.info(f"[ATLAS WEAVER] resolvedor de IA pulado ({type(e).__name__})")
    map_acc.pop("_starts", None)
    map_acc.pop("_seq", None)
    map_acc["meta"] = {"insurer_key": insurer_key, "ramo": ramo_final,
                       "sessions": len(by_session), "events": len(events)}

    # Idempotente: substitui a proposta observada anterior (não empilha versões).
    def _save() -> None:
        # Aposenta TODO mapa observado desta seguradora — não só os do mesmo
        # ramo.
        #
        # Quando o ramo padrão mudou de "auto" para "todos" em 28/07/2026, a
        # filtragem por `ramo` deixou os mapas antigos vivos: a tela do Atlas
        # passou a mostrar "Allianz · Auto" E "Allianz · Todos", com números
        # diferentes, sem dizer qual valia.
        #
        # Existe UM mapa observado por seguradora, porque existe UM WhatsApp e
        # UMA URA. Dois cartões para a mesma seguradora é o operador tendo de
        # adivinhar, e adivinhar errado significa o agente seguindo o mapa
        # velho.
        supabase.client.table("ura_maps").update({"status": "superseded"}).eq(
            "insurer_key", insurer_key).eq(
            "source", "observed").eq("status", "observed").execute()
        supabase.client.table("ura_maps").insert({
            "insurer_key": insurer_key, "ramo": ramo_final, "version": 1,
            "status": "observed", "map": map_acc, "source": "observed",
            "diff_summary": f"{len(map_acc['nodes'])} telas, cobertura {map_acc['coverage']['pct']}%",
        }).execute()

    await asyncio.to_thread(_save)
    try:
        from app.core.heartbeat import beat

        await beat("tecelao", 1)
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[ATLAS WEAVER] {insurer_key}/{ramo_final}: {len(map_acc['nodes'])} nós, "
                f"cobertura {map_acc['coverage']['pct']}%")
    return {"ok": True, "insurer_key": insurer_key, "ramo": ramo_final,
            "nodes": len(map_acc["nodes"]), "coverage": map_acc["coverage"]}
