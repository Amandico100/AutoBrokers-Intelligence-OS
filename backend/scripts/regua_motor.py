"""A camada de reuso da régua — UM SÓ lugar do repositório importa o motor.

SPEC-083 §5.4 é literal: *"Reimplementar qualquer uma faz a ferramenta medir uma
coisa e o produto fazer outra — o mesmo defeito do helper `_captura`, um nível
acima."* E o CLAUDE.md §5 proíbe motor paralelo.

Por isso este módulo existe. `medir_rota.py` e `gerar_corpus_de_telas.py` importam
DAQUI. Nenhum dos dois abre `corridor_playbooks` por conta própria — se abrissem,
os dois dariam jeitos diferentes para o mesmo `sys.path`, e um dia divergiriam.

⚠️ O import difícil, e a SPEC-083 §5.4 diz qual é: `insurer_dispatch_service` faz
`from app.services.corridor_playbooks import (...)` — import de pacote real. E
`app/services/__init__.py` puxa `IngestionService`, que puxa `fastembed`, que não
está instalado fora do contêiner. O truque de `types.ModuleType` cobre os pacotes
sem executar o `__init__.py` de nenhum deles.

📊 Conferido em 21/08/2026: sem o shim, `from app.services.atlas.templater import
templatize` morre em `ModuleNotFoundError: No module named 'fastembed'`.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
import types
from typing import Any, Dict, Iterator, List, Optional, Tuple

# ── o shim de import (SPEC-083 §5.4) ─────────────────────────────────────────
# `scripts/` mora em `backend/scripts`, então a raiz do pacote `app` é o pai.
RAIZ_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `app.services.atlas` não está na lista da SPEC-083 §5.4 e precisa estar: o
# mascarador (`templatize`) mora lá, e a SPEC-084 §2.5.1.3 manda reusá-lo.
_PACOTES = ("app", "app.services", "app.core", "app.services.atlas")

for _pkg in _PACOTES:
    if _pkg not in sys.modules:
        _mod = types.ModuleType(_pkg)
        _mod.__path__ = [os.path.join(RAIZ_BACKEND, *_pkg.split("."))]
        sys.modules[_pkg] = _mod

if RAIZ_BACKEND not in sys.path:
    sys.path.insert(0, RAIZ_BACKEND)

CP = importlib.import_module("app.services.corridor_playbooks")
IDS = importlib.import_module("app.services.insurer_dispatch_service")
TPL = importlib.import_module("app.services.atlas.templater")


# ── o motor, reexportado com o nome do produto ───────────────────────────────
# 🔴 Nada aqui é implementação. Tudo é ponteiro. Se algum dia uma destas linhas
#    virar um `def`, a régua parou de medir o produto e passou a medir a si mesma.
_norm = CP._norm
match_ura_step = CP.match_ura_step
extract_capture_anchors = CP.extract_capture_anchors
detect_finalize_anchor = CP.detect_finalize_anchor
detect_handoff_trigger = CP.detect_handoff_trigger

# ══════════════════════════════════════════════════════════════════════════
# 🔴 C6 · O MOTOR DO FORMULÁRIO NATIVO, QUE ESTA CAMADA NUNCA APONTOU
# ══════════════════════════════════════════════════════════════════════════
#
# 📊 23/08/2026: `detect_native_flow` existia no motor, estava listada em
#    `detector_do_eixo_e.py` como FUNÇÃO DO MOTOR — e não tinha ponteiro aqui.
#    Nenhum consumidor da régua conseguia chamá-la sem furar esta camada, que é
#    a única autorizada a abrir `corridor_playbooks`.
#
# 🔴 O furo tinha DOIS andares: `replay.py` não chamava a função, e esta camada
#    não a oferecia. A tela que TRAVA o acionamento saía do denominador como
#    "órfã inócua", e o item *"zero órfãs funcionais"* dava 20/20 a duas rotas
#    que não respondem o formulário.
detect_native_flow = CP.detect_native_flow
native_flow = CP.native_flow
montar_resposta_de_flow = CP.montar_resposta_de_flow
flow_components = CP._flow_components
# o vocabulário que `new_dispatch_session` injeta sozinha — o resto do que o
# corredor promete ter quando o formulário chegar
slots_com_padrao_do_motor = IDS._slots_com_padrao_do_motor
canonical_subservice = CP.canonical_subservice
missing_slots_for_subservice = CP.missing_slots_for_subservice
render_reply = CP.render_reply
auto_subservice_menu_value = CP.auto_subservice_menu_value
subservice_supported = CP.subservice_supported
resolve_playbook_ref = CP.resolve_playbook_ref
get_playbook = CP.get_playbook
list_playbooks = CP.list_playbooks

# 📊 `_tela_pede_alguma_coisa(playbook, texto) -> bool`, em
# `insurer_dispatch_service.py:1974`. A SPEC-083 §3.3 exige ESTE discriminador e
# nenhum outro: *"Um segundo discriminador divergiria em silêncio."*
tela_pede_alguma_coisa = IDS._tela_pede_alguma_coisa

# 📊 `client_summary_from_capture(session)` — recebe a SESSÃO, não a captura.
# É o item de 5 pontos do eixo B (SPEC-083 §3.3), e o furo nº 3 da §1.2.
client_summary_from_capture = IDS.client_summary_from_capture

# o mascarador do Atlas — SPEC-084 §2.5.1.3: *"NUNCA um segundo"*
templatize = TPL.templatize
marcas_de_corretora = TPL.marcas_de_corretora

PLAYBOOKS: Dict[str, Dict[str, Any]] = CP._PLAYBOOKS


# ── as rotas ─────────────────────────────────────────────────────────────────
class Rota(tuple):
    """`(seguradora, ramo, servico, playbook_ref)` com nomes legíveis."""

    __slots__ = ()

    def __new__(cls, seguradora: str, ramo: str, servico: str, ref: str):
        return super().__new__(cls, (seguradora, ramo, servico, ref))

    seguradora = property(lambda s: s[0])
    ramo = property(lambda s: s[1])
    servico = property(lambda s: s[2])
    ref = property(lambda s: s[3])

    def __str__(self) -> str:  # noqa: D105
        return f"{self[0]} x {self[1]} x {self[2]}"


def _seguradora_e_ramo(ref: str) -> Tuple[str, str]:
    """`allianz-residencial-whatsapp@v1` -> `('allianz', 'residencial')`.

    ⚠️ Derivado da CHAVE, não de uma tabela nova: a chave é a fonte, e uma tabela
    ao lado dela divergiria no dia em que um playbook fosse renomeado.
    """
    base = ref.split("@", 1)[0]
    partes = base.split("-")
    # <seguradora>-<ramo>-<canal>. Seguradora pode ter hífen? Hoje não tem, e o
    # `assert` abaixo é o guarda que avisa no dia em que tiver.
    assert len(partes) == 3, f"chave de playbook fora do formato esperado: {ref}"
    return partes[0], partes[1]


def rotas() -> List[Rota]:
    """As rotas do produto, derivadas dos playbooks.

    📊 62 em 21/08/2026 — a soma dos `subservices` dos 14 playbooks.
    🔴 NUNCA fixar 62: a SPEC-083 (Bloco D, VERIFY) é explícita — *"o número de
    linhas de dados É CALCULADO, não fixo em 62"*, porque a SPEC-084 §10.4 lista
    8+ serviços que ela vai criar, e um VERIFY fixo nasceria errado.
    """
    fora: List[Rota] = []
    for ref, pb in sorted(PLAYBOOKS.items()):
        seg, ramo = _seguradora_e_ramo(ref)
        for servico in sorted((pb.get("subservices") or {})):
            fora.append(Rota(seg, ramo, servico, ref))
    return fora


def rota_de(seguradora: str, ramo: str, servico: str) -> Optional[Rota]:
    """A rota pedida, ou `None` se ela não existe no produto."""
    for r in rotas():
        if (r.seguradora, r.ramo, r.servico) == (seguradora, ramo, servico):
            return r
    return None


def seguradoras() -> List[str]:
    """As seguradoras que têm playbook. 📊 10 em 21/08/2026."""
    return sorted({r.seguradora for r in rotas()})


# ── o banco ──────────────────────────────────────────────────────────────────
def tem_banco() -> bool:
    """Há credencial para ler `observed_events`?

    🔴 Presença/ausência, NUNCA o valor (CLAUDE.md §13.3).
    """
    try:
        from app.core.config import settings

        return bool(getattr(settings, "SUPABASE_URL", None)
                    and getattr(settings, "SUPABASE_KEY", None))
    except Exception:  # noqa: BLE001
        return False


def supabase():
    """O cliente do produto. Não abrimos conexão própria."""
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def controle_do_mascarador() -> int:
    """🔴 O CONTROLE que dá direito a qualquer medição sobre o mascarador.

    SPEC-084 §2.5.1.3, literal:

        CONTROLE OBRIGATÓRIO de qualquer medição sobre o mascarador:
            assert len(marcas_de_corretora(recarregar=True)) > 0
        Se falhar, a medição é INVÁLIDA e não autoriza ampliação nenhuma.

    📊 Foi esta linha que transformou "o mascarador tem três buracos" em "tem um":
    a medição anterior rodou sem banco, `marcas_de_corretora()` devolveu zero, e a
    quarta linha da saída — que era o controle das três primeiras — não foi lida
    como tal.

    Devolve o número de marcas. Levanta `AssertionError` se for zero.
    """
    marcas = marcas_de_corretora(recarregar=True)
    assert len(marcas) > 0, (
        "CONTROLE VERMELHO: marcas_de_corretora() devolveu 0. A medição rodou SEM "
        "BANCO e é INVÁLIDA. Nenhuma conclusão sobre mascaramento vale a partir "
        "daqui. (SPEC-084 §2.5.1.3)"
    )
    return len(marcas)


def eventos_observados(
    *,
    seguradora: Optional[str] = None,
    direction: Optional[str] = None,
    pagina: int = 1000,
) -> Iterator[Dict[str, Any]]:
    """Percorre `observed_events` em páginas, ordenado por `wa_timestamp`.

    ⚠️ Paginação obrigatória: o PostgREST corta em 1000 por padrão, e 📊 o acervo
    tem 28.096 eventos. Uma leitura sem paginação devolveria 3,6% dele e ninguém
    veria — a mesma classe do `limit 22` que fez a SPEC-084 declarar
    `"zurich": []` por corte de query (§2.5.1).
    """
    cli = supabase()
    inicio = 0
    while True:
        # 🔴 `msg_type` e `interactive` entram por medição do JUIZ 2, não por
        #    completude: 📊 **934 respostas de botão têm `text` VAZIO** — yelum
        #    370, hdi 254, porto 165, bradesco 62, azul 54 — e `interactive`
        #    guardou só as CHAVES (`selectedButtonID` entre elas) sem o valor.
        #    **A escolha do segurado não está no banco.**
        #
        #    É a maior causa isolada de perda do nível 1 da cascata. E 📊 1.151
        #    outras TÊM `interactive->>'title'` legível — sem estas colunas,
        #    nenhum consumidor da régua consegue sequer VER que a resposta existe.
        q = (cli.table("observed_events")
             .select("session_id,insurer_key,company_id,direction,text,"
                     "wa_timestamp,msg_type,interactive")
             .order("wa_timestamp")
             .range(inicio, inicio + pagina - 1))
        if seguradora is not None:
            q = q.eq("insurer_key", seguradora)
        if direction is not None:
            q = q.eq("direction", direction)
        linhas = q.execute().data or []
        if not linhas:
            return
        for linha in linhas:
            yield linha
        if len(linhas) < pagina:
            return
        inicio += pagina



# ═════════════════════════════════════════════════════════════════════════════
# C6 · O ESPELHO — as palavras que o SEGURADO escreveu
# ═════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Os apelidos vêm do ESPELHO, nunca do corpus da URA.** O corpus só guarda
#    `direction='in'` — as telas da seguradora. As palavras do cliente vivem em
#    `conversations`/`messages`.
#
# 📊 E o falso positivo que a leitura pelo corpus produzia: *"lavadora"* marca
#    23 vezes no corpus da Allianz porque **a URA** escreve "Lavadora de louças"
#    no menu Linha Branca — outro eletrodoméstico. Contar isso como "o cliente
#    fala assim" é ler a seguradora e chamar de cliente.
#
# ── AS DUAS TRAVAS, E NENHUMA É NEGOCIÁVEL ───────────────────────────────────
#
# 1 · `company_id` SEMPRE. Toda leitura real destas tabelas no produto já
#     filtra tenant (`human_handoff.py:593`, `admin_atlas.py:964`).
#
# 2 · 🔴 A EXCLUSÃO NOMEADA DA AMANDUS. Ela é a corretora de TESTE, e as
#     conversas dela são ficção. Semear `_SUBSERVICE_ALIASES` com vocabulário
#     inventado e depois contá-lo como prova é a pior forma de furo coberto:
#     a régua ficaria verde citando um cliente que não existe.
#
#     ⚠️ 📊 E MEDIDO EM 22/08/2026, o motivo de a trava ser NOMEADA e não
#        derivada: **a AMANDUS está marcada `is_technical = False` no banco.**
#        Filtrar só as corretoras técnicas NÃO a excluiria. É o mesmo alerta que
#        `canais_observados.py` já registra: *"a env var que exclui a Amandus é
#        do destilador e não cobriria isto"*.
_AMANDUS_COMPANY_ID = "3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe"

_ESPELHO_CACHE: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 C13 — O ESPELHO LIA O PRÓPRIO ECO E CHAMAVA DE PALAVRA DO CLIENTE
# ═══════════════════════════════════════════════════════════════════════════════
#
# 📊 Medido em 22/08/2026, auditando os apelidos do encanador. `tubulacao`
#    marcava 3 vezes, e as TRÊS eram isto:
#
#      "o que vc ve nessa imagem?
#       [contexto visual — imagem enviada pelo cliente]:
#       a imagem mostra uma tubulação..."
#
#    🔴 **É o próprio Claude descrevendo uma foto**, gravado como mensagem
#    `role='user'`. O Espelho contava a descrição que a IA escreveu como se
#    fosse a palavra do segurado — e o item da E8 pagava 4 pontos por isso.
#
# ⚠️ E a segunda fonte é a mesma armadilha um nível acima: TELA DE URA COLADA
#    no chat. `hidraulica` marcava 6, e duas eram o menu da Porto colado
#    ("como eu posso te ajudar? servicos para veiculo...").
#    📊 É exatamente o falso positivo que o próprio C6 nomeia (`lavadora` x
#    "Lavadora de louças"), movido do corpus para o Espelho.
#
# 📊 A contaminação é pequena no total — 13 textos distintos em 10.457 — mas
#    está CONCENTRADA nos termos técnicos, que são justamente os que viram
#    apelido. Filtrar 0,1% muda o veredito de vários apelidos.
_MARCAS_DE_ECO = (
    "[contexto visual",          # 🔴 texto que a PRÓPRIA IA escreveu
    "a imagem mostra",
    "selecione uma das opcoes",  # tela de URA colada no chat
    "informe o tipo de servico",
    "assistencia 24h para qual seguro",
    "escolha a opcao desejada",
    "como eu posso te ajudar?",
    "o que voce precisa",              # menu de auto (porto, azul, allianz)

    # 🔴 E A TERCEIRA FONTE, que so apareceu na ONDA B: **o proprio
    #    AutoBrokers**. O resumo que o agente escreve ao corretor antes de
    #    acionar volta para `messages` com `role='user'` e vira "palavra do
    #    cliente" na contagem de apelido.
    #    📊 "so para confirmar antes de acionar, eduardo: - apolice allianz
    #       (auto) - servico: guincho..."
    "so para confirmar antes de acionar",
    "neste caso, enviaremos um prestador",   # texto da URA colado

    # 🔴 E A QUARTA FONTE, achada ao conferir os apelidos de `allianz/auto`
    #    em 23/08/2026: **o PORTAL da seguradora colado no chat**.
    #
    #    Não é a URA do WhatsApp — é a tela do site, que o corretor copia para
    #    o chat quando pede ajuda. 📊 Dois textos, e os dois eram os ÚNICOS
    #    lugares onde `reboque` e `remocao de veiculo` apareciam:
    #
    #      "por favor, selecione a opcao que descreve melhor a sua
    #       necessidade. REMOCAO DE VEICULO preciso de REBOQUE para remover
    #       o veiculo do local | ENVOLVIMENTO EM ACIDENTE ..."
    #
    #      "aqui voce pode de forma rapida e facil: - assistencia 24h:
    #       solicite servicos de emergencia como REBOQUE, CHAVEIRO, TROCA DE
    #       PNEUS ou socorro mecanico..."
    #
    # ⚠️ O segundo é pior que menu: é um CARDÁPIO DE COBERTURA. Ele cita
    #    quatro serviços numa frase só, então crédita apelido para quatro
    #    rotas de uma vez — e nenhuma delas foi pedida por ninguém ali.
    #
    # 📊 O que este conserto CUSTA, medido antes de escrever: de 22 apelidos
    #    declarados hoje, **5 perdem exatamente 1 confirmação** (`mecanico`
    #    18→17, `para-brisa` 21→20, `retrovisor` 15→14, `socorro mecanico`
    #    8→7, `vidro` 50→49) e **NENHUM chega a zero**. Nota de nenhuma das
    #    73 rotas muda. É guarda, não é queda.
    "selecione a opcao que descreve melhor a sua necessidade",
    "solicite servicos de emergencia como",
)

# ⚠️ 🔴 O MARCADOR QUE NÃO TINHA COMO DISPARAR — 23/08/2026.
#
# A lista acima tinha `"*1 -*"`, escrito para pegar menu de URA colado no chat.
# 📊 Ele NUNCA casou nada, e o motivo é o `_norm` desta mesma régua:
#
#     "*1 -*"  →  _norm  →  "1 -"      # o asterisco é REMOVIDO
#
# Comparar o marcador COM asterisco contra um texto SEM asterisco não pode dar
# verdadeiro. **Um guarda que não tem como falhar não guarda nada** (§9.3), e
# este não tinha como ACUSAR — que é a mesma doença pelo outro lado.
#
# 🔴 Quem achou foi um subagente que media `allianz/auto/pneu`, fora do escopo
#    dele: as telas que contaminavam a conferência de apelido daquela rota
#    (`reboque`, `borracheiro`, `troca de pneu`) eram exatamente as que este
#    marcador deveria ter pego.
#
# ⚠️ E o conserto NÃO é trocar por `"1 -"` solto: qualquer lista numerada de
#    cliente ("1 - preciso de guincho") viraria eco. O que identifica MENU é
#    haver DUAS opções numeradas seguidas — prosa não tem isso.
_MENU_COLADO = re.compile(r"(?:^|\s)1\s*-\s*\S[\s\S]{0,180}?(?:^|\s)2\s*-\s*\S",
                          re.M)


def _e_eco(texto: str) -> bool:
    """A mensagem é eco — a IA ou a URA, não o cliente."""
    if any(m in texto for m in _MARCAS_DE_ECO):
        return True
    return bool(_MENU_COLADO.search(texto))


def vocabulario_do_espelho(*, recarregar: bool = False) -> List[str]:
    """As mensagens do SEGURADO, normalizadas, das corretoras REAIS.

    📊 Medido em 22/08/2026: 642 conversas no total — AutoFleet 373 · Resulta
    260 · **AMANDUS 9**. Depois das duas travas: **633 conversas · 10.457
    mensagens** do cliente.

    ⚠️ Devolve o texto normalizado pelo mesmo `_norm` do motor, para que a
    conferência de apelido não tropece em acento ou caixa — a armadilha nº 2 da
    §E3, que já derrubou uma prescrição de juiz dentro desta SPEC.
    """
    global _ESPELHO_CACHE
    if _ESPELHO_CACHE is not None and not recarregar:
        return _ESPELHO_CACHE
    if not tem_banco():
        _ESPELHO_CACHE = []
        return _ESPELHO_CACHE
    cli = supabase()

    # trava 1: só corretora real — e a 2 é a linha do meio, nomeada
    tecnicas = {c["id"] for c in
                cli.table("companies").select("id,is_technical").execute().data
                if c.get("is_technical")}
    excluidas = tecnicas | {_AMANDUS_COMPANY_ID}

    conversas = {c["id"] for c in
                 cli.table("conversations").select("id,company_id")
                 .limit(50000).execute().data
                 if c.get("company_id") not in excluidas}

    fora: List[str] = []
    inicio = 0
    while True:
        pagina = (cli.table("messages").select("conversation_id,role,content")
                  .eq("role", "user").range(inicio, inicio + 999).execute().data)
        if not pagina:
            break
        fora += [t for t in (_norm(m.get("content") or "") for m in pagina
                             if m.get("conversation_id") in conversas)
                 if not _e_eco(t)]
        if len(pagina) < 1000:
            break
        inicio += 1000
    _ESPELHO_CACHE = fora
    return fora


def apelidos_conferidos(servico: str, apelidos: List[str]) -> Dict[str, int]:
    """`{apelido: quantas mensagens do cliente o contêm}`.

    🔴 A pergunta que a E8 faz não é *"o apelido está declarado?"* — é **"o
    cliente escreve assim?"**. Sem esta função o item valeria 4 pontos por ter
    três strings no código.
    """
    textos = vocabulario_do_espelho()
    return {a: sum(1 for t in textos if _norm(a) in t) for a in apelidos}


def apelido_colide(apelido: str, servico: str, playbook: Dict[str, Any]) -> Optional[str]:
    """🔴 O CONTROLE NEGATIVO da E8: o apelido casa o nome de OUTRO serviço?

    📊 O caso que a SPEC nomeia: `lavadora` x **"Lavadora de louças"**, que é
    outro eletrodoméstico do MESMO menu. Um apelido que serve dois trabalhos
    não identifica nenhum — e `canonical_subservice` devolveria o primeiro que
    casar.

    Devolve o serviço que colide, ou `None`.
    """
    alvo = _norm(apelido)
    if not alvo:
        return servico
    for outro in (playbook.get("subservices") or {}):
        if outro == servico:
            continue
        # o nome canônico do outro serviço, escrito como gente fala
        if alvo == _norm(outro.replace("_", " ")):
            return outro
        # e os apelidos DELE
        for ap, dest in (CP._SUBSERVICE_ALIASES or {}).items():
            if dest == outro and _norm(ap) == alvo:
                return outro
    return None


__all__ = [
    "CP", "IDS", "TPL", "RAIZ_BACKEND",
    "_norm", "match_ura_step", "extract_capture_anchors", "detect_finalize_anchor",
    "detect_handoff_trigger", "canonical_subservice", "missing_slots_for_subservice",
    "render_reply", "auto_subservice_menu_value", "subservice_supported",
    "resolve_playbook_ref", "get_playbook", "list_playbooks",
    "tela_pede_alguma_coisa", "client_summary_from_capture",
    "templatize", "marcas_de_corretora", "PLAYBOOKS",
    "Rota", "rotas", "rota_de", "seguradoras",
    "tem_banco", "supabase", "controle_do_mascarador", "eventos_observados",
    "vocabulario_do_espelho", "apelidos_conferidos", "apelido_colide",
    "_e_eco",
    # C6 — o formulário nativo
    "detect_native_flow", "native_flow", "montar_resposta_de_flow",
    "flow_components", "slots_com_padrao_do_motor",
]

# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-089 BLOCO C — O TRAVAMENTO, POR ROTA
# ═════════════════════════════════════════════════════════════════════════════
#
# 📊 A régua não sabia dizer se a rota travou, se uma mão humana terminou, nem
# se o robô destravou sozinho: **zero ocorrências** de `needs_human`,
# `work_steps` ou clique humano nos quatro arquivos dela.
#
# ⚠️ E não é omissão que um item novo no corpus conserta: o corpus
# (`tests/corpus/telas_reais/*.jsonl`) **não tem `direction`** — só tem tela de
# seguradora. O turno do agente, o do atendente e o do segurado não estão lá.
#
# 🔴 Então este eixo lê o **BANCO**, não o corpus.
#
# ---------------------------------------------------------------------------
# ⚠️ E DUAS FONTES QUE A SPEC NOMEIA NÃO EXISTEM
# ---------------------------------------------------------------------------
#
# 📊 Medido em 26/08/2026:
#
#     work_events `travamento.assumido` .......... 🔴 NÃO EXISTE. Nenhum evento
#                                                  `travamento.*` foi gravado
#     work_runs `unblock_state='retomado_pelo_robo'`  🔴 ZERO linhas
#     work_runs `unblock_state='travado'` ........ 1
#     work_steps `step_key='needs_human'` ........ 2   ✅ a SPEC acertou
#
# ✅ O que a SPEC-093 realmente grava é `travamento.destravado` com
# `payload_redacted->>'por'` ∈ (humano · cerebro · sentinela · vigia · robo) —
# e está vazio porque **o piloto não rodou**. Este eixo lê as duas fontes
# reais e nasce inerte, ganhando poder na segunda-feira.


#: 📊 Quem destravou conta como HUMANO. ⚠️ Cérebro, Sentinela e Vigia são o
#: ROBÔ para esta contagem — é a mesma decisão da SPEC-093
#: (`DESTRAVADORES_HUMANOS`), e ela existe porque o que se quer medir é
#: *"precisou de gente?"*, não *"qual subsistema agiu?"*.
DESTRAVE_HUMANO = ("humano",)


def travamentos_por_rota(dias: int = 30) -> Optional[Dict[Tuple[str, str], Dict[str, int]]]:
    """`{(playbook_ref, subservico): {travou, humano, robo}}` — ou **`None`**.

    🔴 **`None` significa "NÃO CONSEGUI MEDIR", e é diferente de `{}`.**

    ⚠️ `{}` quer dizer *"olhei o banco e nenhuma rota travou"* — que é a notícia
    BOA. `None` quer dizer *"não olhei"* — e o BLOCO A desta mesma SPEC diz o
    que fazer com isso: **vale zero, dentro do denominador.**
    """
    if not tem_banco():
        return None
    try:
        db = supabase()
        runs = (db.table("work_runs")
                .select("id, company_id, input_payload, unblock_state")
                .eq("workflow_key", "acionamento.seguradora")
                .limit(2000).execute().data or [])
    except Exception:  # noqa: BLE001
        # ⛔ Falhar a leitura é `None`, nunca `{}`. Zero MEDIDO e zero NÃO
        #    MEDIDO não são a mesma coisa (CLAUDE.md §12.1).
        return None

    # ⚠️ A EXCLUSÃO NOMEADA DA AMANDUS vale aqui também: ela é a corretora de
    #    TESTE, e um travamento fabricado não pode reprovar rota de produção.
    runs = [r for r in runs
            if str(r.get("company_id") or "") != _AMANDUS_COMPANY_ID]
    por_run = {str(r["id"]): r for r in runs}
    if not por_run:
        return {}

    fora: Dict[Tuple[str, str], Dict[str, int]] = {}

    def _chave(r) -> Optional[Tuple[str, str]]:
        ip = r.get("input_payload") or {}
        if not isinstance(ip, dict):
            return None
        ref = str(ip.get("playbook_ref") or "").strip()
        sub = str(ip.get("subservice") or "").strip()
        return (ref, sub) if ref and sub else None

    try:
        etapas = (db.table("work_steps").select("work_run_id, step_key")
                  .eq("step_key", "needs_human").limit(2000).execute().data or [])
        eventos = (db.table("work_events")
                   .select("work_run_id, payload_redacted")
                   .eq("event_type", "travamento.destravado")
                   .limit(2000).execute().data or [])
    except Exception:  # noqa: BLE001
        return None

    for e in etapas:
        r = por_run.get(str(e.get("work_run_id") or ""))
        k = _chave(r) if r else None
        if k:
            fora.setdefault(k, {"travou": 0, "humano": 0, "robo": 0})["travou"] += 1

    for e in eventos:
        r = por_run.get(str(e.get("work_run_id") or ""))
        k = _chave(r) if r else None
        if not k:
            continue
        d = fora.setdefault(k, {"travou": 0, "humano": 0, "robo": 0})
        carga = e.get("payload_redacted") or {}
        por = str(carga.get("por") or "robo") if isinstance(carga, dict) else "robo"
        d["humano" if por in DESTRAVE_HUMANO else "robo"] += 1

    # 🔴 E a segunda fonte do destrave humano: `assumido_por_humano` é STICKY e
    #    dura mesmo sem evento (SPEC-093 C.1, e o defeito P-259 nasceu de
    #    confiar SÓ nela — aqui ela SOMA, não substitui).
    for r in runs:
        if str(r.get("unblock_state") or "") != "assumido_por_humano":
            continue
        k = _chave(r)
        if k:
            d = fora.setdefault(k, {"travou": 0, "humano": 0, "robo": 0})
            if not d["humano"]:
                d["humano"] += 1
    return fora
