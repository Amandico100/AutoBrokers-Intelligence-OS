"""
Fundação de escopo de conhecimento (SPEC-003) — apenas helpers PUROS.

NÃO cria motor RAG; reaproveita o RAG do Smith (Qdrant/embeddings/search).
Responsabilidades:
- normalizar o escopo de um documento (tenant/agent/global/...);
- preparar os campos de conhecimento que viajam no payload do Qdrant;
- montar os kwargs de busca de conhecimento GLOBAL (OPT-IN; default desligado).

Regras: global é curado/read-only; segredos/PII NUNCA entram aqui;
documentos antigos sem scope são tratados como 'tenant'. Defaults sempre seguros.
"""
from typing import Any, Dict, List, Optional

# ── Escopos canônicos (SPEC-003 §1 + SPEC-044 pessoal) ────────────────────────
SCOPE_TENANT = "tenant"
SCOPE_AGENT = "agent"
SCOPE_PERSONAL = "personal"  # SPEC-044: documento do USUÁRIO — só o dono vê
SCOPE_GLOBAL_AUTOBROKERS = "global_autobrokers"
SCOPE_GLOBAL_CARRIER = "global_carrier"
SCOPE_WORKFLOW = "workflow"
SCOPE_CONNECTOR = "connector"

VALID_SCOPES = {
    SCOPE_TENANT,
    SCOPE_AGENT,
    SCOPE_PERSONAL,
    SCOPE_GLOBAL_AUTOBROKERS,
    SCOPE_GLOBAL_CARRIER,
    SCOPE_WORKFLOW,
    SCOPE_CONNECTOR,
}
GLOBAL_SCOPES = [SCOPE_GLOBAL_AUTOBROKERS, SCOPE_GLOBAL_CARRIER]

# ── Coleções Qdrant ───────────────────────────────────────────────────────────
# A coleção global AINDA NÃO é criada neste batch (ver 41C.2B report §8).
GLOBAL_COLLECTION = "autobrokers_global"

# ── Namespaces do acervo global (SPEC-070 §6) ─────────────────────────────────
# Um `namespace` diz DE QUE TIPO é o conhecimento — não de quem é, nem sobre o
# que fala. São três, e cada um é escrito por um caminho de ingestão diferente:
#
#   normative  trecho de condição geral   insurance_corpus.py
#   cards      carta destilada            attendance_distiller.py
#   canon      canon do AutoBrokers       global_knowledge_seed.py
#
# 🔴 QUALQUER NAMESPACE NOVO PRECISA ENTRAR EM `ORCAMENTO_GLOBAL` ABAIXO.
# A busca global passou a ser feita POR FAIXA de namespace. Um valor que não
# apareça em nenhuma faixa não é filtrado errado — ele simplesmente **não é
# procurado**, e some do RAG sem levantar erro nenhum. O teste
# `test_o_contrato_e_a_carta_nao_disputam_a_mesma_vaga.py` compara esta lista
# com o que os escritores gravam, justamente para que isso não passe calado.
NAMESPACE_NORMATIVE = "normative"
NAMESPACE_CARDS = "cards"
NAMESPACE_CANON = "canon"
NAMESPACES_CONHECIDOS = (NAMESPACE_NORMATIVE, NAMESPACE_CARDS, NAMESPACE_CANON)


def company_collection(company_id: str) -> str:
    """Mesmo padrão do QdrantService._get_collection_name (mantido por consistência)."""
    return f"company_{str(company_id).replace('-', '_')}"


def normalize_document_scope(agent_id: Optional[str], requested_scope: Optional[str] = None) -> str:
    """Default seguro: 'agent' se houver agent_id; senão 'tenant'. requested_scope só se válido."""
    if requested_scope and requested_scope in VALID_SCOPES:
        return requested_scope
    return SCOPE_AGENT if agent_id else SCOPE_TENANT


# Campos de conhecimento que podem viajar no payload do Qdrant (todos opcionais).
PAYLOAD_KNOWLEDGE_KEYS = [
    "scope",
    "owner_user_id",  # SPEC-044: dono do documento pessoal (scope=personal)
    "knowledge_class",
    "namespace",
    "version",
    "curation_status",
    "visibility",
    "valid_until",
    "source_hash",
    "carrier_slug",
    "product_slug",
]


def extract_payload_extras(
    source: Optional[Dict[str, Any]], agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrai campos de conhecimento de um dict (metadata do doc ou linha de documents)
    para o payload do Qdrant. Tolerante a vazio. NUNCA inclui conteúdo/segredo/PII.
    `scope` é sempre definido (default tenant/agent).
    """
    src = source or {}
    extras: Dict[str, Any] = {}
    for k in PAYLOAD_KNOWLEDGE_KEYS:
        v = src.get(k)
        if v not in (None, ""):
            extras[k] = v
    if "scope" not in extras:
        extras["scope"] = normalize_document_scope(agent_id, None)
    return extras


def build_personal_search_kwargs(user_id: str) -> Dict[str, Any]:
    """SPEC-044 — kwargs p/ buscar SÓ os documentos pessoais do usuário da
    sessão (scope=personal + owner_user_id). Sem user_id não há busca pessoal
    (o runtime de atendimento nunca passa user → nunca vê doc pessoal)."""
    return {
        "agent_id": None,
        "include_tenant_wide": False,
        "scope_match": [SCOPE_PERSONAL],
        "owner_user_id": str(user_id),
    }


def seguradora_da_pergunta(texto: str) -> Optional[str]:
    """De qual seguradora esta pergunta fala? `None` quando não fala de nenhuma.

    🔴 REUSA O DICIONÁRIO QUE JÁ EXISTE — de propósito.
    ==================================================
    `corridor_playbooks._INSURER_ALIASES` é a única lista de apelidos de
    seguradora do sistema, e `normalize_insurer_key` é a única tradução. Um
    segundo dicionário aqui daria, no dia em que alguém acrescentasse uma
    companhia num só deles, uma pergunta reconhecida na indexação e ignorada na
    busca — o pior tipo de divergência, porque não dá erro.

    `None` é resposta comum e correta: *"como funciona vistoria complementar?"*
    não fala de companhia nenhuma, e aí TODA carta responde, como sempre foi.

    Conservador por escolha: na dúvida, devolve `None`. Errar para "não filtrar"
    devolve o comportamento antigo; errar para "filtrar pela companhia errada"
    esconde a resposta certa e o agente responde com a carta de outra.
    """
    alvo = str(texto or "").strip().lower()
    if not alvo:
        return None
    try:
        from app.services.corridor_playbooks import _INSURER_ALIASES
    except Exception:  # noqa: BLE001 — sem o dicionário, não filtra
        return None

    achadas = set()
    for apelido, chave in _INSURER_ALIASES.items():
        apelido = str(apelido or "").strip().lower()
        # Apelido curto ("azul", "alfa") precisa de fronteira de palavra, senão
        # "azulejo" viraria a seguradora Azul e a pergunta sobre vidro
        # residencial passaria a ser filtrada por uma companhia de auto.
        if len(apelido) < 6:
            import re as _re
            if _re.search(rf"\b{_re.escape(apelido)}\b", alvo):
                achadas.add(chave)
        elif apelido in alvo:
            achadas.add(chave)

    # Duas companhias na mesma pergunta ("a Porto cobre como a HDI?") é
    # comparação: filtrar por uma esconderia a outra. Sem filtro, as duas
    # respondem — que é o que a pergunta pede.
    return achadas.pop() if len(achadas) == 1 else None


# 🔴 SÓ UMA DAS OITO FACETAS FILTRA — E ESSA É A DECISÃO DE PROJETO
# =============================================================================
# `faceta` tem oito valores (`publicar_cartas.py:86`). Este dicionário reconhece
# UM. Não é preguiça — é o que a própria SPEC-070 §5 pede, lido com atenção:
#
#     "`faceta` é a pergunta que a carta responde… é por ela que a busca
#      EQUILIBRA a resposta, para a cobertura não voltar sem a exclusão que a
#      anula."                       (`attendance_distiller.py`, o comentário do payload)
#
# ⚠️ **`escopo` e `exclusao` são um PAR.** Filtrar uma pergunta de cobertura por
# `faceta='escopo'` esconderia justamente a cláusula de exclusão que a anula — o
# agente responderia "cobre" com a carta que diz que cobre, sem a que diz quando
# não cobre. Seria usar o rótulo para NARROW quando ele existe para BALANCE, e o
# defeito seria invisível: a busca devolve resultado, só que meio.
#
# `limite`, `franquia`, `prazo`, `carencia` e `definicao` provavelmente são
# seguras — e "provavelmente" é exatamente o que a **P-145** proíbe:
#
#     "Um sinal que grita mais do que acerta ensina o próximo a ignorar sinal."
#
# Lá, um teste por faceta foi implementado, MEDIDO contra 19 erros confirmados e
# **recusado** (3 acertos, 19 falsos alarmes). A pendência fecha com "não tente
# de novo sem dados novos". Não tenho dados novos para as outras sete.
#
# `documento` entra porque é a única em que a pergunta é fechada: *"quais
# documentos preciso mandar"* não tem contrapeso — não existe uma cláusula que
# anule uma lista de documentos. E é a que a SPEC-072 existe para servir.
#
# **O que destrava as outras sete:** medir, por faceta, quantas respostas melhoram
# e quantas pioram — com linha de controle. Até lá, elas devolvem `None`, que é o
# comportamento de hoje e não esconde nada.
_APELIDOS_DE_FACETA = {
    "documento": "documento",
    "documentos": "documento",
    "documentacao": "documento",
    "documentação": "documento",
    "quais papeis": "documento",
    "quais papéis": "documento",
    "o que precisa enviar": "documento",
    "o que preciso enviar": "documento",
    "o que devo enviar": "documento",
    "lista de documento": "documento",
    "relacao de documento": "documento",
    "relação de documento": "documento",
}


def faceta_da_pergunta(texto: str) -> Optional[str]:
    """Qual faceta esta pergunta pede? `None` quando não pede nenhuma.

    Molde de `seguradora_da_pergunta`, e pelos mesmos motivos: casamento de
    vocabulário, fronteira de palavra no apelido curto, **ambiguidade devolve
    `None`**, e conservador por escolha — errar para "não filtrar" devolve o
    comportamento de hoje; errar para "filtrar pela faceta errada" esconde a
    resposta certa e o agente responde com outra coisa.

    ⚠️ Reconhece **uma** das oito facetas. O porquê está no comentário longo
    acima de `_APELIDOS_DE_FACETA`, e ele é a parte importante desta função.

    ⚠️ E DUAS PROTEÇÕES DAQUI ESTÃO INERTES HOJE — dizer isso importa.
    O ramo `len(apelido) < 6` (fronteira de palavra) **nunca executa**: o menor
    apelido tem 9 caracteres. E `len(achadas) == 1` **nunca desempata**, porque
    todos os valores mapeiam para `"documento"`, então o conjunto tem 0 ou 1
    elemento. As duas ficam porque a segunda faceta as acorda no mesmo dia — mas
    vendê-las como garantia ativa seria mentir sobre o que o código faz.

    ⚠️ E a limitação que nenhuma das duas cobre: o gatilho é `in`, uma
    SUBSTRING. *"qual o prazo para mandar os documentos?"* devolve `documento`,
    embora a pergunta seja de prazo. É mais um motivo para o chamador usar isto
    para dar COTA, nunca para eliminar (SPEC-070 §5.1).
    """
    alvo = str(texto or "").strip().lower()
    if not alvo:
        return None
    achadas = set()
    for apelido, chave in _APELIDOS_DE_FACETA.items():
        if len(apelido) < 6:
            import re as _re
            if _re.search(rf"\b{_re.escape(apelido)}\b", alvo):
                achadas.add(chave)
        elif apelido in alvo:
            achadas.add(chave)
    return achadas.pop() if len(achadas) == 1 else None


# O mesmo critério, para o outro rótulo. A taxonomia tem 📊 24 temas vivos; este
# dicionário reconhece UM, pela mesma razão: `documentacao` é o único que a
# SPEC-072 precisa e o único cujo pedido é fechado. Um tema como `franquia` ou
# `regulacao` filtraria fora a carta que explica por que a regra existe.
_APELIDOS_DE_TEMA = {
    "documento": "documentacao",
    "documentos": "documentacao",
    "documentacao": "documentacao",
    "documentação": "documentacao",
    "o que precisa enviar": "documentacao",
    "o que preciso enviar": "documentacao",
    "lista de documento": "documentacao",
    "relacao de documento": "documentacao",
    "relação de documento": "documentacao",
}


def temas_da_pergunta(texto: str) -> Optional[List[str]]:
    """Quais temas esta pergunta pede? `None` quando não pede nenhum.

    Devolve LISTA porque `temas` é `text[]` e o filtro casa por `MatchAny` —
    uma pergunta pode legitimamente pedir dois assuntos. Ambiguidade aqui não é
    problema como na seguradora: pedir dois temas AMPLIA o braço positivo, não
    esconde nada.

    ⚠️ Mesmas duas proteções inertes de `faceta_da_pergunta`, e a mesma
    limitação de substring. E um risco a mais, que é o que desligou a fiação em
    15/08: 📊 `faceta` e `temas` **discordam em 47%** (só 201 das 380 cartas com
    `faceta='documento'` têm o tema `documentacao`). Passar os dois no mesmo
    `must` é um AND sobre rótulos que não concordam — e acha 53% do que deveria.
    """
    alvo = str(texto or "").strip().lower()
    if not alvo:
        return None
    achados = set()
    for apelido, chave in _APELIDOS_DE_TEMA.items():
        if len(apelido) < 6:
            import re as _re
            if _re.search(rf"\b{_re.escape(apelido)}\b", alvo):
                achados.add(chave)
        elif apelido in alvo:
            achados.add(chave)
    return sorted(achados) or None


# 🔴 A BUSCA EXTRA DA FACETA — COTA, NUNCA CORTE
# =============================================================================
# SPEC-070 §5.1:304: *"`null` passa em todo filtro, NUNCA ELIMINA. Rótulo dá
# COTA E PRIORIDADE."*
#
# Em 15/08/2026 eu implementei o filtro de faceta como `must` na busca global e
# tive de reverter: 📊 **0 de 5.396 cartas do acervo têm faceta ausente**, então
# o braço "OU ausente" não protegia ninguém ali e `faceta='documento'` escondia
# as outras 5.016 — inclusive a carta da Porto que diz *"não há cobertura se
# quem dirigia estava com a CNH suspensa, cassada, vencida"*, que é exatamente o
# que o segurado precisa ouvir ao perguntar sobre documentos.
#
# A forma certa é esta: quando a pergunta pede uma faceta, roda-se UMA busca a
# mais, com orçamento próprio, e o resultado é SOMADO. Nada é removido — o pior
# caso é a busca extra não achar nada e tudo continuar como estava.
#
# ⚠️ Fica FORA de `ORCAMENTO_GLOBAL` de propósito: aquela tupla é desempacotada
# em três (`for rotulo, faixa, cota in ...`) e um teste afirma essa forma. Um
# quarto elemento quebraria o guarda de outra SPEC para caber um desta.
COTA_DE_FACETA = 6
FAIXAS_DA_FACETA = ["normative", "cards"]


def build_global_search_kwargs(
    namespace: Optional[Any] = None,
    version: Optional[str] = None,
    carrier_slug: Optional[str] = None,
    faceta: Optional[str] = None,
    temas: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    kwargs para buscar conhecimento GLOBAL via QdrantService.search_similar.
    Coleção global dedicada, sem agent_id, somente curadoria publicada.

    🔴 `carrier_slug` ERA ACEITO E JOGADO FORA.
    ==========================================
    Por muito tempo esta função declarou os três parâmetros e devolveu um dict
    sem nenhum deles — o docstring dizia *"reservados para filtragem fina"*, e
    quem lia a assinatura concluía que a filtragem existia.

    O preço, medido em 07/08/2026: as cartas guardam `insurer_key` com 📊 zero
    nulos em `ramo` e `category`, e a busca não usava nada disso. Uma pergunta
    sobre a Porto podia ser respondida com a regra da Allianz — 608 cartas
    dela disputando com 361 da Porto, sem nada registrar a troca.

    🔴 E `namespace` FICOU "RESERVADO" POR MAIS UM CICLO — SPEC-070 §6.
    ==================================================================
    📊 08/08/2026, coleção `autobrokers_global`, 23.478 pontos:

        cards ..... 12.063   carta destilada, 📊 média de 186 caracteres
        normative . 11.409   trecho de condição geral, até 1.000 caracteres
        canon ..... 6

    Os dois primeiros disputavam as MESMAS vagas finais. E a disputa não era
    justa: o BM25 normaliza por comprimento, então uma carta de 186 caracteres
    vence um trecho de contrato de 1.000 quase sempre que o termo casa nos dois.
    O material contratual — que é a autoridade sobre *o que está escrito* — vivia
    estruturalmente suprimido pelo material que descreve *como se faz na prática*.

    Não é caso de escolher um. É caso de cada um ter orçamento próprio: um
    embedding só, duas buscas, dois filtros. `namespace` aceita string ou lista.
    `version` continua reservado — e isto está dito aqui, não prometido na
    assinatura.
    """
    kwargs = {
        "collection_name": GLOBAL_COLLECTION,
        "agent_id": None,
        "include_tenant_wide": False,
        "scope_match": list(GLOBAL_SCOPES),
        "curation_published_only": True,
    }
    if (carrier_slug or "").strip():
        kwargs["carrier_slug"] = str(carrier_slug).strip().lower()
    faixa = _normalizar_namespaces(namespace)
    if faixa:
        kwargs["namespace"] = faixa
    # ⚠️ Estes dois SÓ podem entrar aqui no mesmo commit que os parâmetros de
    # `search_similar`. O retorno é splatado com `**`, e um kwarg sem parâmetro
    # correspondente vira `TypeError` — que `search_service.py` e
    # `langchain_service.py` ENGOLEM num `except Exception`, matando TODOS os
    # resultados globais em silêncio. O agente responderia sem RAG nenhum e o
    # log diria só o nome da exceção.
    if (faceta or "").strip():
        kwargs["faceta"] = str(faceta).strip().lower()
    if temas:
        kwargs["temas"] = temas
    return kwargs


def _normalizar_namespaces(namespace: Optional[Any]) -> List[str]:
    """`"cards"` · `["cards", "canon"]` · `None` → lista limpa (possivelmente vazia)."""
    if namespace is None:
        return []
    bruto = [namespace] if isinstance(namespace, str) else list(namespace)
    vistos: List[str] = []
    for item in bruto:
        valor = str(item or "").strip().lower()
        if valor and valor not in vistos:
            vistos.append(valor)
    return vistos


# ── Orçamento da busca global, por faixa de namespace (SPEC-070 §6) ───────────
#
# Cada linha é UMA busca no Qdrant, com o MESMO embedding e o MESMO serviço —
# só o filtro muda. Não é um segundo motor de busca (CLAUDE.md §5): é a mesma
# `search_similar`, chamada duas vezes com filtros diferentes.
#
# POR QUE `canon` ANDA COM `cards`
# ================================
# São 📊 6 pontos. Uma terceira ida ao Qdrant por 6 pontos custaria uma
# viagem de rede por pergunta para sempre. Andando junto das cartas, o canon
# fica EXATAMENTE na posição competitiva que já tinha hoje (disputava com o
# índice inteiro; agora disputa com uma fatia menor dele) — nada regride.
#
# ⚠️ O que NÃO pode acontecer é um namespace novo não aparecer em faixa
# nenhuma: ele não seria filtrado errado, seria simplesmente **não procurado**.
# `NAMESPACES_CONHECIDOS` existe para o teste conferir essa cobertura.
ORCAMENTO_GLOBAL = (
    ("normativo", [NAMESPACE_NORMATIVE], 12),
    ("cartas", [NAMESPACE_CARDS, NAMESPACE_CANON], 12),
)


# ── Orçamento do corte final, por faixa (SPEC-070 §6) ─────────────────────────
#
# 🔴 SEPARAR NA BUSCA E JUNTAR NO CORTE NÃO CONSERTA NADA.
#
# Recuperar 12 trechos de contrato e 12 cartas e depois cortar os 3 melhores de
# uma lista só devolve o problema inteiro: o RRF de duas buscas distintas não é
# comparável (o próprio `search_service` documenta que ele "não mede relevância,
# mede concordância de posição"), e a carta curta volta a ganhar. O orçamento
# tem de sobreviver ATÉ a vaga final.
#
# 📊 A CONTA DAS VAGAS (08/08/2026)
# ---------------------------------
#   carta publicada .......... 186 chars de média (n=12.063, mediana 186, p90 260)
#                              +~30 do prefixo de assunto  → ~270 com cabeçalho
#   trecho normativo ......... chunk_size=1.000 (insurance_corpus.py:213)
#                                                          → ~1.050 com cabeçalho
#   documento da corretora ... mesmo splitter               → ~1.050
#
#   3 vagas, no pior caso todas cartas:      3 × 270  =    810 chars
#   `context_assembly.ORCAMENTO_TOTAL`                  14.000 chars
#   `TETO_POR_FONTE["normativo"]` sozinho                5.500 chars
#
# O sistema orçava 14.000 e entregava 810. As cotas abaixo entregam, no pior
# caso (tudo cheio):  3×1.050 + 3×270 + 2×1.050 = 6.060 chars — ainda **abaixo**
# do teto declarado, e agora com contrato garantido na mesa.
#
# Cota é TETO e PISO ao mesmo tempo, mas nenhuma vaga é desperdiçada: sobra de
# faixa vazia é redistribuída por ordem global (ver `selecionar_com_cota`).
# Pergunta sem nada de normativo continua respondida só por cartas, como hoje.
COTA_FINAL = {NAMESPACE_NORMATIVE: 3, NAMESPACE_CARDS: 3}
COTA_FINAL_OUTROS = 2  # documento da própria corretora, canon, ponto sem namespace

BALDE_OUTROS = "__outros__"


def balde_do_resultado(resultado: Dict[str, Any], cotas: Dict[str, int]) -> str:
    """Em que faixa este resultado compete. Fora das cotas → `__outros__`."""
    ns = str((resultado or {}).get("namespace") or "").strip().lower()
    return ns if ns in cotas else BALDE_OUTROS


def selecionar_com_cota(
    resultados: List[Dict[str, Any]],
    cotas: Optional[Dict[str, int]] = None,
    cota_outros: int = COTA_FINAL_OUTROS,
) -> List[Dict[str, Any]]:
    """As vagas finais, com orçamento por namespace. Puro, sem I/O.

    Recebe a lista JÁ ORDENADA (pelo reranker, ou pelo RRF quando ele está
    ausente) e devolve no máximo `soma das cotas + cota_outros` itens,
    **preservando a ordem recebida**.

    A regra, em duas passadas:

      1ª  percorre na ordem e aceita cada item enquanto a cota da SUA faixa não
          estourou. É isto que garante que o contrato tenha lugar mesmo quando
          as 12.063 cartas ocupam as primeiras posições.
      2ª  se ainda sobra vaga (faixa sem candidato), preenche pela ordem global.
          Vaga reservada e não usada seria conhecimento jogado fora — e a maior
          parte das perguntas de procedimento não tem trecho de contrato que
          responda.

    ⚠️ Isto governa **candidatura**, não inclusão: `_format_response` continua
    aplicando o corte de relevância por escala em cima do que sai daqui. Cota
    não promove chunk ruim; só impede que chunk bom seja espremido para fora
    antes de ser medido.
    """
    itens = list(resultados or [])
    if not itens:
        return []
    tabela = dict(cotas if cotas is not None else COTA_FINAL)
    total = sum(tabela.values()) + max(0, int(cota_outros))
    if total <= 0:
        return []

    usados: Dict[str, int] = {}
    escolhidos: List[int] = []
    for i, item in enumerate(itens):
        balde = balde_do_resultado(item, tabela)
        limite = cota_outros if balde == BALDE_OUTROS else tabela[balde]
        if usados.get(balde, 0) < limite:
            usados[balde] = usados.get(balde, 0) + 1
            escolhidos.append(i)

    if len(escolhidos) < total:
        ja = set(escolhidos)
        for i in range(len(itens)):
            if len(escolhidos) >= total:
                break
            if i not in ja:
                escolhidos.append(i)

    escolhidos.sort()
    return [itens[i] for i in escolhidos[:total]]


def merge_rag_results(
    primary: List[Dict[str, Any]], extra: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Une resultados (ex.: tenant/agent + global), dedupe por (document_id, chunk_index),
    mantendo o de maior score. Não loga conteúdo.
    """
    by_key: Dict[str, Dict[str, Any]] = {}
    for r in list(primary or []) + list(extra or []):
        key = f"{r.get('document_id')}::{r.get('chunk_index')}"
        cur = by_key.get(key)
        if cur is None or (r.get("score") or 0) > (cur.get("score") or 0):
            by_key[key] = r
    merged = list(by_key.values())
    merged.sort(key=lambda x: (x.get("rerank_score") or x.get("score") or 0), reverse=True)
    return merged
