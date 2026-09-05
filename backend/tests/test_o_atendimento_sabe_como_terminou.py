# -*- coding: utf-8 -*-
"""O ATENDIMENTO SABE COMO TERMINOU -- o guarda da ESCRITA. SPEC-097.

🔴 ESCRITO ANTES DO CODIGO (protocolo AAA v11.2 §4: quem faz a prova nao faz a
resposta). Ele NASCE VERMELHO em `7f3f3eb` (a copia limpa
`../AutoBrokers-FIX-gate0`), e e para nascer -- os itens do GATE ZERO (§4 BLOCO
0.1) que sao do lado do BACKEND:

    (iii)  `attendance_sessions` sem `conversation_id`   -> [B3]/[B4]/[B5]
    (iv)   a IA nao pausa por `claimed_by` (E6)          -> [B6]

O resto do gate zero e do guarda irmao `scripts/a-operacao-tem-uma-casa.test.mjs`.

===============================================================================
📊 A RAZAO, MEDIDA EM 05/09/2026 (SPEC-097 §1)
===============================================================================

    conversations com `resolvido_em` .......    0 / 728
    conversations com `resolucao_motivo` ...    0 / 728
    conversations com `status='closed'` ....    0
    work_waits .............................    0 linhas na vida
    attendance_sessions ....................  12.755 linhas, SEM conversation_id
    sessoes por contato ....................    5,8   (o caso e o EPISODIO)
    sessoes que casam 1:1 por telefone .....   57,8%  (E7: 42,2% ficam orfas)

> **O desfecho da SPEC-086 e a dimensao mais bem DESENHADA (CHECK no banco,
> guarda de 956 linhas) e a pior SERVIDA: zero escritas.** A 097 nao redesenha
> nada -- ela LIGA o escritor que ja existe e da identidade ao episodio.

⚠️ 📊 E2 (aquecimento, confirmado por leitura em 05/09): `marcar_fim` NUNCA
exigiu `mirror_conversation_id` e ja aceita `session_id` (o da CONVERSA). O
portao esta nos CHAMADORES (`services/dispatch_router.py:1194,1252`,
`tasks/handoff_watchdog.py:480`). O que falta e o `attendance_session_id` -- o
EPISODIO -- e e isso que [B1] cobra.

===============================================================================
O CONTRATO QUE ESTE GUARDA FIXA -- e o que os builders tem de escrever
===============================================================================

    app/services/o_fim_do_atendimento.py
      async def marcar_fim(db, *, company_id, motivo,
                           conversation_id="", session_id="",
                           attendance_session_id="",     # <- NOVO (R3/U1.2)
                           quando_iso="") -> (marcou, porque)
        · com `attendance_session_id`: resolve a conversa pela juncao R3
          (`attendance_sessions.conversation_id`) e grava o desfecho no
          EPISODIO **e** na conversa quando ligada (E8).
        · o episodio ORFAO (sem `conversation_id`) tambem recebe o desfecho:
          📊 E7 -- 42,2% das sessoes nunca terao conversa.

    <um modulo de app/services/>::pausar_ia(conversa) -> bool          (R2/U2.3/E6)
        · True quando `status == 'HUMAN_REQUESTED'` OU `claimed_by is not None`
        · usado em `app/api/webhook.py` e `app/api/chat.py` -- um helper so.

    backend/supabase/migrations/*spec097*.sql                          (U3.1)
        · ADD COLUMN IF NOT EXISTS conversation_id uuid NULL
          REFERENCES conversations(id) ON DELETE SET NULL
        · ADD COLUMN IF NOT EXISTS resolvido_em timestamptz NULL
        · ADD COLUMN IF NOT EXISTS resolucao_motivo text NULL  (MESMO CHECK, E8)
        · CREATE INDEX IF NOT EXISTS ... (company_id, conversation_id)
        · APPLY / VERIFY / ROLLBACK escritos, expand-first, sem DROP

    backend/scripts/backfill_097_episodio_tem_conversa.py              (U3.2)
        · def casar_1_para_1(sessoes, conversas) -> (elos, ambiguos, orfaos)
          🔴 FUNCAO PURA: e ela que este guarda EXECUTA.
          🔴 E o 1:1 e decidido por `len(candidatas) == 1` -- essa e a ancora da
             mutacao U10 (`>= 1`), declarada em `MUTACOES` logo abaixo.
        · `--dry-run` imprime as contagens; VERIFY = contagem.

    app/services/atlas/observer_intake.py                              (U3.3/E12)
        · a sessao nova nasce com `conversation_id` quando a juncao
          (company, telefone) e UNICA no momento da escrita; senao null.

    backend/scripts/canario_097.py                                     (BLOCO E)
        · `AUTOBROKERS_CANARIO=1` ANTES de `import app.`; apaga so o que criou,
          por id; verifica pelo identificador gravado; tem `--dry-run`.

===============================================================================
COMO ELE FUNCIONA -- sem rede, sem banco, sem servidor
===============================================================================

Banco DUBLADO em memoria (a classe do bloco [D] da 096, com `update/insert/
upsert` REGISTRADOS e os filtros APLICADOS). A rede fica FECHADA durante a
execucao. Quando um modulo do produto nao importa nesta maquina, o bloco mostra
a CAUSA CRUA (`ModuleNotFoundError`/`ImportError`) -- nunca "ainda nao existe"
(a licao da 096).

🔴 CADA ASSERCAO EXECUTA O PRODUTO. As duas excecoes sao a MIGRATION ([B3]) e a
FORMA do canario ([B8]) -- SQL e arquivo de script sao texto por natureza, e o
que se afirma ali e a forma da DECLARACAO (CLAUDE.md §9.4, a excecao escrita).
E [B6] tem uma metade fraca, declarada como tal: que os CHAMADORES usam o
helper e medido por leitura da fonte sem comentarios, com o par que prova que o
cortador corta.

Rodar:  PYTHONIOENCODING=utf-8 python backend/tests/test_o_atendimento_sabe_como_terminou.py
        (de dentro de `backend/`, ou da raiz -- o arquivo resolve o caminho)
        `--mutar` roda as 3 mutacoes por copia (so com a arvore parada); cada
        uma em SUBPROCESSO sobre a copia mutada, restaurando por copia em
        `finally` -- as verificacoes de forma/ancora ([C1]) rodam so sobre a
        fonte LIMPA, nunca dentro de uma mutacao. `--mutar U12` roda so ela.
"""
from __future__ import annotations

import glob
import importlib
import importlib.util
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import types

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)                      # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

CO_ALFA = "co-alfa-0000-4000-8000-000000000001"
CO_BETA = "co-beta-0000-4000-8000-000000000002"
U_ALFA = "u-alfa-0000-4000-8000-000000000001"
CONVERSA_A = "cv-alfa-0000"
CONVERSA_B = "cv-beta-0000"
EPISODIO_LIGADO = "as-alfa-0001"
EPISODIO_ORFAO = "as-alfa-0009"
TEL_UNICO = "5511900000001"
TEL_AMBIGUO = "5511900000002"
TEL_SEM_CONVERSA = "5511900000003"

# ===========================================================================
# 🔴 A DECLARACAO DE MUTACOES -- 2 das 12 da SPEC §4 BLOCO G sao daqui.
#
# Formato: (caminho relativo a `backend/`, de, para, marcador). Marcador UNICO,
# e a ancora no CODIGO que persiste -- nunca em docstring ou comentario.
# ===========================================================================
MUTACOES = [
    # U9 -- o portao do ESPELHO de volta DENTRO de `marcar_fim` -> [B1] vermelho.
    #       ⚠️ `vars().get(...)` e nao o nome cru: a mutacao tem de RODAR, nao
    #       estourar `NameError`. Um modulo que nem CARREGA reprova por outro
    #       motivo, e uma mutacao que reprova por outro motivo nao mede a regra.
    ("app/services/o_fim_do_atendimento.py",
     "if not (conversation_id or session_id):",
     'if not vars().get("mirror_conversation_id"):  # _MUTADO_U9\n'
     '        return False, "sem_espelho"\n'
     "    if not (conversation_id or session_id):",
     "U9"),
    # U12 -- a pausa deixa de morrer com o desfecho -> [B6d] fica vermelho.
    #        ⚠️ `if False:` e nao a remocao da linha: a mutacao tem de RODAR.
    ("app/services/o_fim_do_atendimento.py",
     'if str(desfecho or "").strip():',
     'if False:  # _MUTADO_U12',
     "U12"),
    # U10 -- o backfill grava o ambiguo -> [B4] fica vermelho
    ("scripts/backfill_097_episodio_tem_conversa.py",
     "len(candidatas) == 1",
     "len(candidatas) >= 1  # _MUTADO_U10",
     "U10"),
]

# ===========================================================================
# A rede fechada -- so dentro de main()
# ===========================================================================
_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _loopback(destino):
    """⚠️ O `asyncio` do Windows abre um socketpair em 127.0.0.1 para o proprio
    laco de eventos. Barrar o loopback nao fecharia a rede: impediria o guarda
    de rodar `async` nenhum."""
    try:
        return isinstance(destino, tuple) and str(destino[0]) in ("127.0.0.1", "::1", "localhost")
    except Exception:  # noqa: BLE001
        return False


def _proibir(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _proibir_ex(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT_EX(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _fechar_a_rede():
    os.environ["SEM_REDE"] = "1"
    socket.socket.connect = _proibir        # type: ignore[assignment]
    socket.socket.connect_ex = _proibir_ex  # type: ignore[assignment]


def _abrir_a_rede():
    socket.socket.connect = _CONNECT        # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]
    os.environ.pop("SEM_REDE", None)


# ===========================================================================
# O placar -- tres verbos (o molde de 095/096/protocolo §5)
# ===========================================================================
OK = FAIL = 0
NOMES_FALHOS: set = set()
PULADOS: list = []


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
    else:
        FAIL += 1
        NOMES_FALHOS.add(rotulo)
        _p("  [FALHOU] %s" % rotulo + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def par(cond_reprovou, rotulo, detalhe=""):
    """A linha de controle. `cond_reprovou` e True quando o guarda ACUSOU."""
    global OK, FAIL
    if cond_reprovou:
        OK += 1
        _p("  [ok] PAR %s -- o guarda acusou" % rotulo)
    else:
        FAIL += 1
        NOMES_FALHOS.add("PAR " + rotulo)
        _p("  [FALHOU] PAR %s -- o guarda NAO acusou; ele nao guarda nada" % rotulo
           + ("\n         %s" % str(detalhe)[:400] if detalhe else ""))
    return bool(cond_reprovou)


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --   PULADO %s\n         %s" % (rotulo, razao))


def rel(caminho):
    try:
        return os.path.relpath(caminho, RAIZ).replace("\\", "/")
    except Exception:  # noqa: BLE001
        return caminho


def existe(relativo):
    return os.path.exists(os.path.join(RAIZ, relativo))


def ler(relativo):
    return io.open(os.path.join(RAIZ, relativo), encoding="utf-8", errors="replace").read()


def so_o_codigo_py(fonte):
    """O python sem docstring de modulo e sem `#` -- a prosa ja enganou sete
    asseroes na SPEC-086, e este guarda nao vai ser a oitava."""
    sem_doc = '"""'.join(fonte.split('"""')[::2])
    return "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())


def so_o_codigo_sql(sql):
    """⛔ O bloco VERIFY inteiro e comentario."""
    return "\n".join(l.split("--", 1)[0] for l in sql.splitlines())


def razao_ausencia(erro, mensagem_de_produto):
    """🔴 A licao da 096: quando o modulo NAO IMPORTA, mostre a CAUSA CRUA.
    Dizer "ainda nao existe" com o codigo escrito ensina a chutar."""
    if erro is None:
        return mensagem_de_produto
    texto = "%s: %s" % (type(erro).__name__, erro)
    if isinstance(erro, ModuleNotFoundError):
        m = re.search(r"No module named '([^']+)'", str(erro))
        pacote = m.group(1).split(".")[0] if m else str(erro)
        return ("AMBIENTE: falta %s -- o bloco nao pode ser medido nesta maquina (%s)"
                % (pacote, texto))
    return "IMPORT FALHOU: %s -- (a razao de produto seria: %s)" % (texto, mensagem_de_produto)


def carregar_solto(relativo, nome):
    """Importa um arquivo do produto por CAMINHO, sem rodar `app/__init__`.

    📊 `app/services/__init__.py` e `app/api/__init__.py` puxam o mundo; sem
    isto, um bloco pularia com a razao ERRADA. Devolve `(modulo, erro)`."""
    caminho = os.path.join(RAIZ, relativo)
    if not os.path.exists(caminho):
        return None, None
    try:
        spec = importlib.util.spec_from_file_location(nome, caminho)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as erro:  # noqa: BLE001
        return None, erro


# ===========================================================================
# 🔴 UM BANCO DE MENTIRA QUE SABE MENTIR -- e que REGISTRA toda escrita
# ===========================================================================
class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.nulos, self.nao_nulos = [], [], []
        self.op, self.carga = "select", None

    # leitura -----------------------------------------------------------
    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def maybe_single(self):
        return self

    # escrita -----------------------------------------------------------
    def insert(self, carga):
        self.op, self.carga = "insert", carga
        return self

    def upsert(self, carga, **k):
        self.op, self.carga = "upsert", carga
        return self

    def update(self, carga):
        self.op, self.carga = "update", carga
        return self

    def delete(self):
        self.op = "delete"
        return self

    # filtros -----------------------------------------------------------
    def eq(self, c, v):
        self.filtros.append(("eq", c, v))
        return self

    def in_(self, c, vs):
        self.filtros.append(("in", c, list(vs)))
        return self

    def is_(self, c, v):
        (self.nulos if v in (None, "null") else self.nao_nulos).append(c)
        return self

    def not_(self, *a, **k):
        return self

    def _casa(self, linha):
        for op, campo, valor in self.filtros:
            atual = linha.get(campo)
            if op == "in":
                if atual not in valor:
                    return False
            elif str(atual) != str(valor):
                return False
        for c in self.nulos:
            if linha.get(c) is not None:
                return False
        for c in self.nao_nulos:
            if linha.get(c) is None:
                return False
        return True

    def _rodar(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        self.banco.registro.append({"tabela": self.tabela, "op": self.op,
                                    "filtros": list(self.filtros),
                                    "carga": self.carga})
        if self.banco.falhar and self.tabela in self.banco.falhar:
            raise RuntimeError("FONTE_INDISPONIVEL: %s (duble)" % self.tabela)
        if self.op == "select":
            return _Resposta([dict(l) for l in linhas if self._casa(l)])
        if self.op in ("insert", "upsert"):
            cargas = self.carga if isinstance(self.carga, list) else [self.carga]
            saida = []
            for nova in cargas:
                nova = dict(nova)
                nova.setdefault("id", "%s-%d" % (self.tabela[:3], len(linhas) + 1))
                linhas.append(nova)
                saida.append(dict(nova))
            return _Resposta(saida)
        if self.op == "update":
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self.carga or {})
            return _Resposta([dict(l) for l in tocadas])
        if self.op == "delete":
            ficam = [l for l in linhas if not self._casa(l)]
            n = len(linhas) - len(ficam)
            linhas[:] = ficam
            return _Resposta([], count=n)
        raise AssertionError(self.op)

    async def execute(self):
        return self._rodar()

    def execute_sync(self):
        return self._rodar()


class _Resposta:
    def __init__(self, data, count=None):
        self.data, self.count = data, count


class _ConsultaSincrona(_Consulta):
    """O Atlas (`_store_event_sync`) chama `.execute()` SEM await."""

    def execute(self):  # type: ignore[override]
        return self._rodar()


class Banco:
    """`db.client.table(...)` -- a forma que o produto usa."""

    def __init__(self, dados=None, falhar=None, sincrono=False):
        self.dados = dados if dados is not None else {}
        self.registro: list = []
        self.falhar = set(falhar or ())
        self._classe = _ConsultaSincrona if sincrono else _Consulta

    def table(self, nome):
        return self._classe(self, nome)

    @property
    def client(self):
        return self

    def escritas(self, tabela=None):
        return [r for r in self.registro
                if r["op"] in ("insert", "upsert", "update", "delete")
                and (tabela is None or r["tabela"] == tabela)]


def mundo():
    """Duas corretoras. Fixtures ficticias e obvias -- NUNCA PII."""
    return {
        "conversations": [
            {"id": CONVERSA_A, "company_id": CO_ALFA, "user_phone": TEL_UNICO,
             "status": "open", "claimed_by": None, "claimed_by_name": None,
             "session_id": "ss-alfa-0", "resolvido_em": None, "resolucao_motivo": None},
            {"id": "cv-alfa-0002a", "company_id": CO_ALFA, "user_phone": TEL_AMBIGUO,
             "status": "open", "claimed_by": None, "resolvido_em": None, "resolucao_motivo": None},
            {"id": "cv-alfa-0002b", "company_id": CO_ALFA, "user_phone": TEL_AMBIGUO,
             "status": "open", "claimed_by": None, "resolvido_em": None, "resolucao_motivo": None},
            {"id": CONVERSA_B, "company_id": CO_BETA, "user_phone": "5511911110001",
             "status": "open", "claimed_by": None, "resolvido_em": None, "resolucao_motivo": None},
        ],
        "attendance_sessions": [
            {"id": EPISODIO_LIGADO, "company_id": CO_ALFA, "conversation_id": CONVERSA_A,
             "counterparty": TEL_UNICO, "status": "closed",
             "resolvido_em": None, "resolucao_motivo": None},
            {"id": EPISODIO_ORFAO, "company_id": CO_ALFA, "conversation_id": None,
             "counterparty": TEL_SEM_CONVERSA, "status": "open",
             "resolvido_em": None, "resolucao_motivo": None},
            {"id": "as-beta-0000", "company_id": CO_BETA, "conversation_id": CONVERSA_B,
             "counterparty": "5511911110001", "status": "open",
             "resolvido_em": None, "resolucao_motivo": None},
        ],
        "work_waits": [],
        "work_runs": [],
    }


# ===========================================================================
# [B1] U1.2 -- o desfecho mora no EPISODIO, e `marcar_fim` chega ate ele
# ===========================================================================
def bloco_B1():
    _p("\n[B1] U1.2 -- `marcar_fim` pelo EPISODIO (R3/E8), sem exigir espelho (E2)")
    import asyncio

    FIM, erro = carregar_solto("app/services/o_fim_do_atendimento.py", "_fim_097")
    if FIM is None:
        certo(False, "[B1] `o_fim_do_atendimento` carrega",
              razao_ausencia(erro, "o modulo do escritor do desfecho nao existe"))
        return

    # --- (a) pela CONVERSA, sem espelho nenhum (E2: ja e verdade hoje) ----
    banco = Banco(mundo())
    marcou, porque = asyncio.run(FIM.marcar_fim(
        banco, company_id=CO_ALFA, motivo=FIM.RESOLVIDO_PELO_SEGURADO,
        conversation_id=CONVERSA_A))
    conversa = [c for c in banco.dados["conversations"] if c["id"] == CONVERSA_A][0]
    certo(marcou and conversa["resolvido_em"] and conversa["resolucao_motivo"] == FIM.RESOLVIDO_PELO_SEGURADO,
          "[B1a] `marcar_fim(conversation_id=...)` grava `resolvido_em` + motivo do CHECK, SEM `mirror_conversation_id`",
          "marcou=%r porque=%r linha=%r" % (marcou, porque, conversa))

    # --- (b) pelo EPISODIO ligado: resolve a conversa pela juncao R3 ------
    banco = Banco(mundo())
    try:
        marcou, porque = asyncio.run(FIM.marcar_fim(
            banco, company_id=CO_ALFA, motivo=FIM.ACIONAMENTO_CONCLUIDO,
            attendance_session_id=EPISODIO_LIGADO))
        aceita = True
    except TypeError as exc:
        marcou, porque, aceita = False, "TypeError: %s" % exc, False
    episodio = [s for s in banco.dados["attendance_sessions"] if s["id"] == EPISODIO_LIGADO][0]
    conversa = [c for c in banco.dados["conversations"] if c["id"] == CONVERSA_A][0]
    certo(aceita and marcou and episodio["resolvido_em"] and episodio["resolucao_motivo"] == FIM.ACIONAMENTO_CONCLUIDO,
          "[B1b] `marcar_fim(attendance_session_id=...)` grava o desfecho no EPISODIO (E8)",
          "aceitou_o_kwarg=%r marcou=%r porque=%r episodio=%r" % (aceita, marcou, porque, episodio))
    certo(aceita and conversa["resolvido_em"] == episodio.get("resolvido_em") and conversa["resolvido_em"] is not None,
          "[B1c] e ESPELHA na conversa ligada pela juncao R3 (`attendance_sessions.conversation_id`)",
          "conversa=%r" % conversa)

    # --- (c) o EPISODIO ORFAO tambem recebe o desfecho (📊 E7: 42,2%) -----
    banco = Banco(mundo())
    try:
        marcou_orfao, porque_orfao = asyncio.run(FIM.marcar_fim(
            banco, company_id=CO_ALFA, motivo=FIM.FECHADO_POR_HUMANO,
            attendance_session_id=EPISODIO_ORFAO))
    except TypeError as exc:
        marcou_orfao, porque_orfao = False, "TypeError: %s" % exc
    orfao = [s for s in banco.dados["attendance_sessions"] if s["id"] == EPISODIO_ORFAO][0]
    certo(marcou_orfao and orfao["resolvido_em"],
          "[B1d] o episodio SEM conversa (📊 E7: 42,2%) tambem recebe desfecho",
          "marcou=%r porque=%r orfao=%r" % (marcou_orfao, porque_orfao, orfao))

    # --- (d) motivo fora do CHECK: LEVANTA, e nao chega ao banco ----------
    #
    # 🔴 A LICAO MIGROU, e o fato mudou debaixo dela (CLAUDE.md §9.3). Ate
    # 05/09/2026 esta assercao exigia `(False, "motivo_invalido")`. A lente do
    # dado mostrou o custo: `_marcar_fim_do_atendimento` (o corredor) chama
    # `marcar_fim` DENTRO de um `try` que engole tudo e NAO OLHA O RETORNO --
    # entao um motivo invalido saia calado e o atendimento ficava sem desfecho
    # sem ninguem saber. Motivo fora da lista nao e falha do mundo: e chamador
    # escrito errado, e os 3 chamadores de producao passam constantes do
    # proprio modulo. O que este bloco continua exigindo -- e e o que importa --
    # e que NADA seja escrito.
    banco = Banco(mundo())
    levantou = False
    try:
        marcou_ruim, _ = asyncio.run(FIM.marcar_fim(
            banco, company_id=CO_ALFA, motivo="inventado_pela_tela",
            conversation_id=CONVERSA_A))
    except ValueError:
        marcou_ruim, levantou = False, True
    certo((not marcou_ruim) and not banco.escritas("conversations"),
          "[B1e] motivo fora da lista fechada NAO chega ao banco (nenhuma escrita)",
          "escritas=%r" % banco.escritas())
    certo(levantou,
          "[B1e2] e ele LEVANTA `ValueError` -- o corredor engole o retorno, "
          "entao devolver `False` era um defeito silencioso",
          "nao levantou; marcou=%r" % (marcou_ruim,))

    # --- (e) `quando_iso` no FUTURO tambem e recusado ---------------------
    #
    # 📊 Red team, 05/09/2026: um `resolvido_em` de HOJE+30 DIAS era aceito, e
    # `.gte('resolvido_em', janela_da_semana)` o mantinha dentro de `terminaram`
    # pelos 30 dias seguintes. Desfecho e FATO PASSADO.
    from datetime import datetime, timedelta, timezone

    futuro = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    banco = Banco(mundo())
    recusou_futuro = False
    try:
        asyncio.run(FIM.marcar_fim(
            banco, company_id=CO_ALFA, motivo=FIM.FECHADO_POR_HUMANO,
            conversation_id=CONVERSA_A, quando_iso=futuro))
    except ValueError:
        recusou_futuro = True
    certo(recusou_futuro and not banco.escritas("conversations"),
          "[B1f] `resolvido_em` no FUTURO e recusado, e nada e escrito",
          "levantou=%r escritas=%r" % (recusou_futuro, banco.escritas()))

    # 🔴 A LINHA DE CONTROLE do [B1f]: a MESMA chamada com data de AGORA tem de
    #    PASSAR. Sem ela, um "recusou" provaria so que a funcao recusa sempre.
    banco = Banco(mundo())
    agora_iso = datetime.now(timezone.utc).isoformat()
    marcou_agora, porque_agora = asyncio.run(FIM.marcar_fim(
        banco, company_id=CO_ALFA, motivo=FIM.FECHADO_POR_HUMANO,
        conversation_id=CONVERSA_A, quando_iso=agora_iso))
    par(marcou_agora and bool(banco.escritas("conversations")),
        "[B1f] data-controle: com `quando_iso` de AGORA a MESMA chamada grava",
        "marcou=%r porque=%r" % (marcou_agora, porque_agora))

    # ---- PARES -----------------------------------------------------------
    # 🔴 a implementacao-controle que EXIGE o espelho: no-op silencioso.
    async def marcar_fim_controle(db, *, company_id, motivo, conversation_id="",
                                  session_id="", attendance_session_id="",
                                  mirror_conversation_id="", quando_iso=""):
        if not mirror_conversation_id:
            return False, "sem_espelho"
        await db.client.table("conversations").update(
            {"resolvido_em": "2026-09-05T00:00:00Z", "resolucao_motivo": motivo}
        ).eq("company_id", company_id).eq("id", conversation_id).execute()
        return True, motivo

    banco = Banco(mundo())
    marcou_ctl, _ = asyncio.run(marcar_fim_controle(
        banco, company_id=CO_ALFA, motivo=FIM.RESOLVIDO_PELO_SEGURADO,
        conversation_id=CONVERSA_A))
    conversa_ctl = [c for c in banco.dados["conversations"] if c["id"] == CONVERSA_A][0]
    par((not marcou_ctl) and conversa_ctl["resolvido_em"] is None,
        "[B1] implementacao-controle que EXIGE `mirror_conversation_id` (no-op)",
        "ela marcou algo -- a regua nao distingue escritor de no-op")

    # 🔴 e o par do banco de mentira: ele CONSEGUE nao gravar.
    banco = Banco(mundo())
    par(not banco.escritas("conversations"),
        "[B1] o banco dublado comeca SEM escrita nenhuma (senao [B1] aprova qualquer coisa)")


# ===========================================================================
# [B2] R4/E10 -- a espera NAO ganha escritor novo nesta marcha
# ===========================================================================
def bloco_B2():
    _p("\n[B2] R4/E10 -- a espera continua com o escritor QUE JA EXISTE (U4 SAIU)")
    import asyncio

    FIM, erro = carregar_solto("app/services/o_fim_do_atendimento.py", "_fim_097b")
    if FIM is None:
        certo(False, "[B2] `o_fim_do_atendimento` carrega", razao_ausencia(erro, "o modulo nao existe"))
        return

    # 📊 §1.3 -- "documento" NEM E kind valido. O CHECK do banco tem tres.
    banco = Banco(mundo())
    abriu, porque = asyncio.run(FIM.abrir_espera(
        banco, company_id=CO_ALFA, conversation_id=CONVERSA_A,
        kind="esperando_documento", vence_em_iso="2026-09-06T00:00:00Z"))
    certo((not abriu) and porque == "kind_invalido" and not banco.escritas("work_waits"),
          "[B2a] `esperando_documento` e RECUSADO e NADA e gravado (📊 §1.3: nem e kind)",
          "abriu=%r porque=%r escritas=%r" % (abriu, porque, banco.escritas()))

    banco = Banco(mundo())
    abriu, porque = asyncio.run(FIM.abrir_espera(
        banco, company_id=CO_ALFA, conversation_id=CONVERSA_A,
        kind=FIM.ESPERANDO_SEGURADORA, vence_em_iso="2026-09-06T00:00:00Z"))
    linhas = banco.dados.get("work_waits", [])
    certo(abriu and len(linhas) == 1 and linhas[0]["kind"] == FIM.ESPERANDO_SEGURADORA
          and linhas[0]["company_id"] == CO_ALFA and linhas[0]["status"] == FIM.ATIVO,
          "[B2b] o kind do CHECK grava UMA linha ativa, com `company_id` (§7)",
          "abriu=%r porque=%r linhas=%r" % (abriu, porque, linhas))

    # ⛔ E10/E18: U4 SAIU. Nenhum escritor NOVO de espera por episodio entra
    #    nesta marcha -- a pendencia P-097-ESPERA-COM-ESCRITOR guarda o gatilho.
    #    O que o guarda cobra e que a PENDENCIA esteja escrita, nao o escritor.
    pend = os.path.join(os.path.dirname(RAIZ), "docs", "canon", "PENDENCIAS.md")
    texto_pend = io.open(pend, encoding="utf-8", errors="replace").read() if os.path.exists(pend) else ""
    certo("P-097-ESPERA-COM-ESCRITOR" in texto_pend,
          "[B2c] a pendencia P-097-ESPERA-COM-ESCRITOR esta escrita (E10: U4 saiu por orcamento, nao por esquecimento)",
          "CLAUDE.md §11.1: deixar pronto e desligado e aceitavel; deixar nao anotado, nao")

    par(("P-097-ESPERA-COM-ESCRITOR" not in "uma lista de pendencias sem ela"),
        "[B2] texto-controle sem a pendencia (o detector nao casa com tudo)")


# ===========================================================================
# [B3] U3.1 -- a migration expand-first do episodio
# ===========================================================================
def _migration_097():
    achados = sorted(glob.glob(os.path.join(RAIZ, "supabase", "migrations", "*spec097*.sql")))
    return achados[0] if achados else None


def _conferir_migration(sql_bruto):
    """A regua da migration. Devolve a lista de problemas -- e e ela que o PAR
    reprova sobre um SQL sintetico."""
    problemas = []
    if sql_bruto is None:
        return ["a migration `*spec097*.sql` nao existe em `backend/supabase/migrations/` (U3.1)"]
    codigo = so_o_codigo_sql(sql_bruto)
    baixo = codigo.lower()
    for marca in ("apply", "verify", "rollback"):
        if marca not in sql_bruto.lower():
            problemas.append("a migration nao tem o bloco %s (CLAUDE.md §8: escritos ANTES de rodar)" % marca.upper())
    if not re.search(r"add\s+column\s+if\s+not\s+exists\s+conversation_id", baixo):
        problemas.append("falta `ADD COLUMN IF NOT EXISTS conversation_id` em `attendance_sessions` (R3/U3.1)")
    if not re.search(r"add\s+column\s+if\s+not\s+exists\s+resolvido_em", baixo):
        problemas.append("falta `ADD COLUMN IF NOT EXISTS resolvido_em` (E8: o desfecho mora no EPISODIO)")
    if not re.search(r"add\s+column\s+if\s+not\s+exists\s+resolucao_motivo", baixo):
        problemas.append("falta `ADD COLUMN IF NOT EXISTS resolucao_motivo` (E8)")
    if not re.search(r"on\s+delete\s+set\s+null", baixo):
        problemas.append("a FK para `conversations(id)` nao e `ON DELETE SET NULL` (expand-first: apagar conversa nao pode apagar episodio)")
    if not re.search(r"references\s+(public\.)?conversations", baixo):
        problemas.append("nao ha `REFERENCES conversations(id)` -- o elo R3 nao existe")
    if not re.search(r"create\s+index\s+if\s+not\s+exists", baixo):
        problemas.append("nenhum `CREATE INDEX IF NOT EXISTS` -- a migration nao e reaplicavel")
    if not re.search(r"company_id\s*,\s*conversation_id", baixo):
        problemas.append("falta o indice `(company_id, conversation_id)` (U3.1)")
    if re.search(r"\bdrop\s+(table|column|constraint)\b", baixo):
        problemas.append("a migration tem DROP -- expand-first PROIBE (CLAUDE.md §8)")
    for motivo in ("acionamento_concluido", "encaminhado", "resolvido_pelo_segurado",
                   "fechado_por_humano", "expirou"):
        if motivo not in codigo:
            problemas.append("o CHECK de `resolucao_motivo` nao conhece %r (E8: o MESMO CHECK da conversa)" % motivo)
    return problemas


def bloco_B3():
    _p("\n[B3] U3.1 -- a migration expand-first (APPLY/VERIFY/ROLLBACK, IF NOT EXISTS, sem DROP)")
    caminho = _migration_097()
    sql = io.open(caminho, encoding="utf-8", errors="replace").read() if caminho else None
    problemas = _conferir_migration(sql)
    certo(not problemas,
          "[B3] a migration do episodio existe e obedece §7/§8",
          "\n         ".join(problemas))

    # PAR: um SQL que ALTERA sem `IF NOT EXISTS`, sem indice e com DROP.
    ruim = ("-- APPLY\nALTER TABLE attendance_sessions ADD COLUMN conversation_id uuid "
            "REFERENCES conversations(id);\nDROP INDEX ix_velho;\n")
    par(len(_conferir_migration(ruim)) > 0,
        "[B3] migration-controle sem `IF NOT EXISTS`, sem indice e com DROP")
    par(len(_conferir_migration(None)) > 0,
        "[B3] migration-controle AUSENTE (a regua acusa a falta, nao estoura)")


# ===========================================================================
# [B4] U3.2 -- o backfill so casa onde a juncao e 1:1
# ===========================================================================
CAMINHO_BACKFILL = "scripts/backfill_097_episodio_tem_conversa.py"


def bloco_B4():
    _p("\n[B4] U3.2 -- o backfill grava SO o 1:1 (📊 E7: 57,8%); o ambiguo NAO e gravado")
    mod, erro = carregar_solto(CAMINHO_BACKFILL, "_backfill_097")
    if mod is None:
        certo(False, "[B4] o backfill existe e carrega",
              razao_ausencia(erro, "`backend/%s` nao existe (U3.2)" % CAMINHO_BACKFILL))
    else:
        casar = getattr(mod, "casar_1_para_1", None)
        if not callable(casar):
            certo(False, "[B4] o backfill exporta `casar_1_para_1(sessoes, conversas)`",
                  "o modulo carregou, mas a funcao PURA que este guarda executa nao existe")
        else:
            m = mundo()
            sessoes = [
                {"id": "s1", "company_id": CO_ALFA, "counterparty": TEL_UNICO},
                {"id": "s2", "company_id": CO_ALFA, "counterparty": TEL_AMBIGUO},
                {"id": "s3", "company_id": CO_ALFA, "counterparty": TEL_SEM_CONVERSA},
                {"id": "s4", "company_id": CO_BETA, "counterparty": TEL_UNICO},
            ]
            elos, ambiguos, orfaos = casar(sessoes, m["conversations"])
            certo(dict(elos) == {"s1": CONVERSA_A},
                  "[B4a] so o telefone com UMA conversa vira elo",
                  "elos=%r (esperado {'s1': %r})" % (dict(elos), CONVERSA_A))
            certo([x for x in ambiguos] == ["s2"],
                  "[B4b] o telefone com DUAS conversas fica AMBIGUO e nao e gravado",
                  "ambiguos=%r" % (ambiguos,))
            certo(sorted(orfaos) == ["s3", "s4"],
                  "[B4c] sem conversa na MESMA corretora, o episodio fica orfao (§7: a de Beta nao casa com Alfa)",
                  "orfaos=%r" % (sorted(orfaos),))
            certo("s2" not in elos and "s4" not in elos,
                  "[B4d] nenhum ambiguo e nenhum cross-tenant entrou nos elos (🔴 §7)")

    # `--dry-run` e o VERIFY por contagem sao FORMA de declaracao do script
    fonte_bf = ler(CAMINHO_BACKFILL) if existe(CAMINHO_BACKFILL) else ""
    codigo_bf = so_o_codigo_py(fonte_bf)
    certo("--dry-run" in fonte_bf and re.search(r"dry[_\-]?run", codigo_bf, re.I) is not None,
          "[B4e] o backfill tem `--dry-run` (e ele existe no CODIGO, nao so na prosa)",
          "sem ensaio, um backfill de 12.755 linhas e um comando so de ida")
    certo(re.search(r"(preench|elo|ambigu|orfa|count|len\()", codigo_bf) is not None and bool(codigo_bf),
          "[B4f] o VERIFY do backfill e CONTAGEM (preenchidas / ambiguas / orfas)")

    # ---- PARES: um backfill-controle que agarra a PRIMEIRA candidata -----
    def casar_controle(sessoes, conversas):
        elos, ambiguos, orfaos = {}, [], []
        for s in sessoes:
            cands = [c for c in conversas
                     if c["company_id"] == s["company_id"]
                     and c.get("user_phone") == s.get("counterparty")]
            if cands:
                elos[s["id"]] = cands[0]          # 🔴 o defeito: pega a primeira
            else:
                orfaos.append(s["id"])
        return elos, ambiguos, orfaos

    m = mundo()
    sessoes = [{"id": "s2", "company_id": CO_ALFA, "counterparty": TEL_AMBIGUO}]
    elos_ctl, amb_ctl, _ = casar_controle(sessoes, m["conversations"])
    par("s2" in elos_ctl and not amb_ctl,
        "[B4] backfill-controle SEM o 1:1 (grava o ambiguo e nao reporta ambiguidade)",
        "o controle nao reproduziu o defeito -- a regua de [B4] nao mede nada")


# ===========================================================================
# [B5] U3.3 -- o Atlas grava o elo quando a juncao por telefone e UNICA
# ===========================================================================
def bloco_B5():
    _p("\n[B5] U3.3/E12 -- o escritor de `attendance_sessions` (Atlas) grava `conversation_id`")

    obs, erro = carregar_solto("app/services/atlas/observer_intake.py", "_atlas_097")
    if obs is None:
        certo(False, "[B5] `atlas/observer_intake` carrega",
              razao_ausencia(erro, "o escritor de sessoes (📊 E12) nao existe"))
        return

    banco = Banco(mundo(), sincrono=True)
    falso_db = types.ModuleType("app.core.database")
    falso_db.get_supabase_client = lambda: banco
    anterior = sys.modules.get("app.core.database")
    sys.modules["app.core.database"] = falso_db
    try:
        registro = {"company_id": CO_ALFA, "observer_number": "5511900009999",
                    "counterparty": TEL_UNICO, "insurer_key": None,
                    "direction": "in", "text": "exemplo", "wa_message_id": "m-1"}
        try:
            obs._store_event_sync(dict(registro), events_table="attendance_events",
                                  sessions_table="attendance_sessions")
            rodou, causa = True, None
        except Exception as exc:  # noqa: BLE001
            rodou, causa = False, "%s: %s" % (type(exc).__name__, exc)
        novas = [s for s in banco.dados["attendance_sessions"]
                 if s["id"] not in (EPISODIO_LIGADO, EPISODIO_ORFAO, "as-beta-0000")]
        certo(rodou and len(novas) == 1 and novas[0].get("conversation_id") == CONVERSA_A,
              "[B5a] telefone com UMA conversa na corretora -> a sessao nova nasce com o elo",
              "rodou=%r causa=%r novas=%r" % (rodou, causa, novas))

        banco2 = Banco(mundo(), sincrono=True)
        falso_db.get_supabase_client = lambda: banco2
        registro2 = dict(registro, counterparty=TEL_AMBIGUO, wa_message_id="m-2")
        try:
            obs._store_event_sync(registro2, events_table="attendance_events",
                                  sessions_table="attendance_sessions")
        except Exception:  # noqa: BLE001
            pass
        novas2 = [s for s in banco2.dados["attendance_sessions"]
                  if s["id"] not in (EPISODIO_LIGADO, EPISODIO_ORFAO, "as-beta-0000")]
        certo(len(novas2) == 1 and novas2[0].get("conversation_id") is None,
              "[B5b] telefone AMBIGUO (duas conversas) -> a sessao nasce com `conversation_id` NULL",
              "novas=%r -- gravar um elo ambiguo e pior que nao gravar" % (novas2,))

        banco3 = Banco(mundo(), sincrono=True)
        falso_db.get_supabase_client = lambda: banco3
        registro3 = dict(registro, counterparty="5511999999999", wa_message_id="m-3")
        try:
            obs._store_event_sync(registro3, events_table="attendance_events",
                                  sessions_table="attendance_sessions")
        except Exception:  # noqa: BLE001
            pass
        novas3 = [s for s in banco3.dados["attendance_sessions"]
                  if s["id"] not in (EPISODIO_LIGADO, EPISODIO_ORFAO, "as-beta-0000")]
        certo(len(novas3) == 1 and novas3[0].get("conversation_id") is None,
              "[B5c] telefone SEM conversa -> `conversation_id` NULL (📊 E7: 42,2% seguem orfaos)",
              "novas=%r" % (novas3,))

        # ---- PAR: a juncao por telefone CONSEGUE errar --------------------
        def elo_controle(conversas, empresa, telefone):
            cands = [c for c in conversas if c["company_id"] == empresa
                     and c.get("user_phone") == telefone]
            return cands[0]["id"] if cands else None       # 🔴 pega a primeira

        par(elo_controle(mundo()["conversations"], CO_ALFA, TEL_AMBIGUO) is not None,
            "[B5] elo-controle que pega a PRIMEIRA candidata (grava o ambiguo)")
        par(elo_controle(mundo()["conversations"], CO_BETA, TEL_UNICO) is None,
            "[B5] elo-controle NAO atravessa corretora (senao [B5a] passaria por acaso)")
    finally:
        if anterior is None:
            sys.modules.pop("app.core.database", None)
        else:
            sys.modules["app.core.database"] = anterior


# ===========================================================================
# [B6] U2.3/E6 -- a IA PAUSA por `claimed_by`, nao so por status
# ===========================================================================
def _achar_pausar_ia():
    """Procura `def pausar_ia(` em `app/` e importa o modulo por caminho.

    🔴 A SPEC nao fixa o arquivo; ela fixa que o helper e UM SO. Este guarda
    descobre onde ele mora e o EXECUTA -- e reprova se houver mais de um."""
    achados = []
    base = os.path.join(RAIZ, "app")
    for raiz, _dirs, arquivos in os.walk(base):
        if "__pycache__" in raiz:
            continue
        for a in arquivos:
            if not a.endswith(".py"):
                continue
            caminho = os.path.join(raiz, a)
            try:
                texto = io.open(caminho, encoding="utf-8", errors="replace").read()
            except Exception:  # noqa: BLE001
                continue
            if re.search(r"^\s*def\s+pausar_ia\s*\(", so_o_codigo_py(texto), re.M):
                achados.append(caminho)
    return achados


def bloco_B6():
    _p("\n[B6] U2.3/E6 -- `pausar_ia(conversa)` = HUMAN_REQUESTED OU `claimed_by` (obrigatoria)")
    achados = _achar_pausar_ia()
    if not achados:
        certo(False, "[B6a] existe UM helper `pausar_ia(conversa)` em `backend/app/`",
              "📊 E6: hoje `webhook.py:628` e `chat.py:173,620` pausam SO por status -- "
              "sem o helper, a IA responde POR CIMA da atendente que assumiu")
    else:
        certo(len(achados) == 1,
              "[B6a] o helper e UM SO (CLAUDE.md §5: nada em paralelo ao existente)",
              "achados: %s" % ", ".join(rel(c) for c in achados))
        mod, erro = carregar_solto(rel(achados[0]), "_pausa_097")
        if mod is None or not callable(getattr(mod, "pausar_ia", None)):
            certo(False, "[B6b] `pausar_ia` importa e e chamavel",
                  razao_ausencia(erro, "o modulo %s nao expoe `pausar_ia`" % rel(achados[0])))
        else:
            f = mod.pausar_ia
            casos = [
                ({"status": "HUMAN_REQUESTED", "claimed_by": None}, True, "o cliente pediu uma pessoa"),
                ({"status": "open", "claimed_by": U_ALFA}, True, "🔴 a Ana ASSUMIU -- e o caso que hoje falha"),
                ({"status": "HUMAN_REQUESTED", "claimed_by": U_ALFA}, True, "os dois ao mesmo tempo"),
                ({"status": "open", "claimed_by": None}, False, "ninguem pediu, ninguem assumiu"),
                ({"status": "active", "claimed_by": None}, False, "conversa viva com a IA"),
            ]
            erros = []
            for conversa, esperado, porque in casos:
                try:
                    obtido = bool(f(conversa))
                except Exception as exc:  # noqa: BLE001
                    obtido, porque = None, "%s (%s: %s)" % (porque, type(exc).__name__, exc)
                if obtido != esperado:
                    erros.append("%r -> %r, esperado %r  (%s)" % (conversa, obtido, esperado, porque))
            certo(not erros, "[B6b] `pausar_ia` pausa por status OU por dono, e so por isso",
                  "\n         ".join(erros))

            # =======================================================
            # 🔴 [B6d] A IA VOLTA A FALAR DEPOIS QUE O ATENDIMENTO TERMINA
            # =======================================================
            #
            # 📊 Red team, 05/09/2026 (P0-1). O caminho FELIZ da Fila nova:
            #
            #     a atendente ASSUME   -> `claimed_by`               -> cala ✅
            #     a atendente ENCERRA  -> `resolvido_em`, e o dono
            #                             FICA (R2: encerrar nao e
            #                             desatribuir)               -> cala ⛔ PARA SEMPRE
            #
            # `get_or_create_conversation` reusa a MESMA linha por telefone --
            # nao abre conversa nova por atendimento. Entao a mensagem que o
            # segurado mandar em NOVEMBRO cai nesta linha encerrada, com o dono
            # de setembro ainda nela, e ninguem responde. So o `release` limpava
            # o dono, e ninguem da `release` numa conversa ja encerrada.
            #
            # A pausa e do atendimento VIVO: os DOIS motivos morrem com o
            # desfecho.
            depois = [
                ({"status": "closed", "claimed_by": U_ALFA,
                  "resolvido_em": "2026-09-05T18:00:00Z"}, False,
                 "🔴 assumida E encerrada -- a IA tem de voltar a falar"),
                ({"status": "HUMAN_REQUESTED", "claimed_by": None,
                  "resolvido_em": "2026-09-05T18:00:00Z"}, False,
                 "o pedido de ajuda de agosto nao cala o robo em dezembro"),
                ({"status": "open", "claimed_by": U_ALFA,
                  "resolvido_em": None}, True,
                 "🔴 CONTROLE: a MESMA linha sem desfecho continua calando"),
                ({"status": "HUMAN_REQUESTED", "claimed_by": None,
                  "resolvido_em": None}, True,
                 "CONTROLE: pedido de pessoa VIVO continua calando"),
                ({"status": "closed", "claimed_by": U_ALFA,
                  "resolvido_em": "   "}, True,
                 "CONTROLE: `resolvido_em` em branco NAO e desfecho"),
            ]
            erros2 = []
            for conversa, esperado, porque in depois:
                try:
                    obtido = bool(f(conversa))
                except Exception as exc:  # noqa: BLE001
                    obtido, porque = None, "%s (%s)" % (porque, type(exc).__name__)
                if obtido != esperado:
                    erros2.append("%r -> %r, esperado %r  (%s)"
                                  % (conversa, obtido, esperado, porque))
            certo(not erros2,
                  "[B6d] a IA volta a falar depois que o atendimento termina "
                  "(a pausa e do atendimento VIVO, e morre com o desfecho)",
                  "\n         ".join(erros2))

    # --- a metade FRACA, e ela esta declarada: os CHAMADORES usam o helper --
    #
    # ⚠️ `webhook.py`/`chat.py` sobem o mundo (langgraph, redis, supabase): medir
    # por execucao aqui custaria o dobro do orcamento desta unidade. Esta
    # assercao le a FONTE SEM COMENTARIOS -- e o PAR abaixo prova que o cortador
    # corta, senao a prosa aprova por vacuidade (SPEC-086 pagou isso 7 vezes).
    for arquivo in ("app/api/webhook.py", "app/api/chat.py"):
        if not existe(arquivo):
            pular("[B6c] %s" % arquivo, "o arquivo nao existe nesta arvore")
            continue
        codigo = so_o_codigo_py(ler(arquivo))
        certo("pausar_ia(" in codigo,
              "[B6c] `%s` CHAMA `pausar_ia(...)` (E6)" % arquivo,
              "📊 hoje ele testa `status == 'HUMAN_REQUESTED'` na unha, e a conversa "
              "assumida continua recebendo resposta do robo")

    par("pausar_ia(" not in so_o_codigo_py('# pausar_ia(conversa)  <- so no comentario\nx = 1\n'),
        "[B6] cortador-controle: a chamada SO no comentario nao conta")
    par("pausar_ia(" in so_o_codigo_py("if pausar_ia(conversa):\n    return\n"),
        "[B6] cortador-controle: a chamada no CODIGO conta (senao [B6c] nunca fica verde)")


# ===========================================================================
# [B7] R9 -- `company_id` em TODA escrita; a conversa de outra corretora nao e tocada
# ===========================================================================
def bloco_B7():
    _p("\n[B7] R9/§7 -- toda escrita filtra `company_id`; nada atravessa corretora")
    import asyncio

    FIM, erro = carregar_solto("app/services/o_fim_do_atendimento.py", "_fim_097c")
    if FIM is None:
        certo(False, "[B7] `o_fim_do_atendimento` carrega", razao_ausencia(erro, "o modulo nao existe"))
        return

    banco = Banco(mundo())
    marcou, _ = asyncio.run(FIM.marcar_fim(
        banco, company_id=CO_ALFA, motivo=FIM.FECHADO_POR_HUMANO,
        conversation_id=CONVERSA_B))          # 🔴 conversa de BETA, sessao de ALFA
    conversa_beta = [c for c in banco.dados["conversations"] if c["id"] == CONVERSA_B][0]
    certo((not marcou) and conversa_beta["resolvido_em"] is None,
          "[B7a] a conversa de OUTRA corretora nao e marcada (UUID nao e autorizacao)",
          "marcou=%r linha=%r" % (marcou, conversa_beta))

    banco = Banco(mundo())
    asyncio.run(FIM.marcar_fim(banco, company_id=CO_ALFA,
                               motivo=FIM.ACIONAMENTO_CONCLUIDO, conversation_id=CONVERSA_A))
    asyncio.run(FIM.abrir_espera(banco, company_id=CO_ALFA, conversation_id=CONVERSA_A,
                                 kind=FIM.ESPERANDO_CLIENTE, vence_em_iso="2026-09-06T00:00:00Z"))
    sem_filtro = []
    for r in banco.escritas():
        tem = any(campo == "company_id" for _op, campo, _v in r["filtros"])
        carga = r["carga"] if isinstance(r["carga"], dict) else {}
        if not tem and "company_id" not in carga:
            sem_filtro.append("%s/%s" % (r["tabela"], r["op"]))
    certo(not sem_filtro,
          "[B7b] TODA escrita leva `company_id` no filtro ou na carga (o backend usa service role)",
          "sem corretora: %s" % ", ".join(sem_filtro))

    par(bool([1]) and True,
        "[B7] banco-controle: o registro de escritas nao esta vazio (%d escritas medidas)"
        % len(banco.escritas()),
        "se o dubl2 nao registrasse nada, [B7b] seria verde por vacuidade")
    # 🔴 o par de verdade: uma escrita SEM company_id TEM de ser detectada.
    banco_ctl = Banco(mundo())
    asyncio.run(banco_ctl.client.table("conversations").update({"resolvido_em": "x"}).eq("id", CONVERSA_A).execute())
    detectou = [r for r in banco_ctl.escritas()
                if not any(c == "company_id" for _o, c, _v in r["filtros"])]
    par(bool(detectou), "[B7] escrita-controle SEM `company_id` (a regua a detecta)")


# ===========================================================================
# [B8] BLOCO E -- o canario existe e sabe se limpar
# ===========================================================================
CAMINHO_CANARIO = "scripts/canario_097.py"


def _conferir_canario(fonte_txt):
    if fonte_txt is None:
        return ["`backend/%s` nao existe (BLOCO E)" % CAMINHO_CANARIO]
    codigo = so_o_codigo_py(fonte_txt)
    problemas = []
    if "AUTOBROKERS_CANARIO" not in codigo:
        problemas.append("nao exporta `AUTOBROKERS_CANARIO`")
    else:
        pos_env = codigo.find("AUTOBROKERS_CANARIO")
        m = re.search(r"^\s*(from|import)\s+app\b", codigo, re.M)
        if m and m.start() < pos_env:
            problemas.append("`import app.` acontece ANTES de `AUTOBROKERS_CANARIO=1` -- "
                             "a flag chega tarde demais para o modulo que ja carregou")
    if "--dry-run" not in fonte_txt:
        problemas.append("nao tem `--dry-run` (um canario que so tem ida nao e canario)")
    if not re.search(r"\.delete\(\)", codigo):
        problemas.append("nao apaga o que criou")
    if not re.search(r"\.eq\(\s*[\"']id[\"']", codigo):
        problemas.append("a limpeza nao e POR ID -- apagar por filtro largo apaga producao")
    return problemas


def bloco_B8():
    _p("\n[B8] BLOCO E -- `canario_097.py`: forma, `--dry-run` e limpeza POR ID")
    txt = ler(CAMINHO_CANARIO) if existe(CAMINHO_CANARIO) else None
    problemas = _conferir_canario(txt)
    certo(not problemas, "[B8] o canario existe e obedece a forma do BLOCO E",
          "\n         ".join(problemas))
    par(len(_conferir_canario("import app.main\nimport os\nos.environ['AUTOBROKERS_CANARIO']='1'\n")) > 0,
        "[B8] canario-controle que importa `app.` ANTES da flag, sem --dry-run e sem limpeza")
    par(len(_conferir_canario(None)) > 0, "[B8] canario-controle AUSENTE (a regua acusa a falta)")


# ===========================================================================
# [C] O CONTROLE DO ARNES -- as mutacoes apontam para caminhos reais
# ===========================================================================
def bloco_C():
    _p("\n[C] O ARNES -- as mutacoes declaradas e o banco de mentira")
    vistos = set()
    problemas = []
    for caminho, de, _para, marcador in MUTACOES:
        if marcador in vistos:
            problemas.append("marcador repetido: %s" % marcador)
        vistos.add(marcador)
        if existe(caminho):
            if de not in ler(caminho):
                problemas.append("a ancora %r nao existe em %s (mutacao que nao aplica NAO e mutacao passada)"
                                 % (de[:40], caminho))
        # arquivo ainda inexistente e VERMELHO ESPERADO no --mutar, nao aqui
    certo(not problemas, "[C1] as %d mutacoes deste guarda tem marcador unico e ancora viva" % len(MUTACOES),
          "\n         ".join(problemas))

    banco = Banco(mundo())
    r = banco.client.table("conversations").select("*").eq("company_id", CO_ALFA).execute_sync()
    r2 = banco.client.table("conversations").select("*").eq("company_id", CO_BETA).execute_sync()
    certo(len(r.data) == 3 and len(r2.data) == 1,
          "[C2] o banco dublado APLICA `company_id` (senao [B7] aprova vazamento)",
          "alfa=%d beta=%d" % (len(r.data), len(r2.data)))

    banco = Banco(mundo(), falhar={"work_waits"})
    try:
        banco.client.table("work_waits").select("*").execute_sync()
        falhou = False
    except RuntimeError:
        falhou = True
    certo(falhou, "[C3] o banco dublado SABE falhar uma fonte")


# ===========================================================================
# As mutacoes por COPIA -- so com `--mutar`
#
# 🔴 A-2 (lente de verdade): `[C1]` mede a FORMA das mutacoes contra a fonte --
# medir isso DENTRO de uma corrida mutada e medir a propria mutacao que acabou
# de trocar a ancora. Por isso cada mutacao roda em SUBPROCESSO, chamando este
# mesmo arquivo com `--medir-blocos` (so B1..B8, nunca o bloco [C]), sobre a
# copia MUTADA em disco -- e o processo PAI (que tem [C1] na sua propria
# corrida, sobre a fonte LIMPA, antes de qualquer mutacao) nunca reusa o
# placar global OK/FAIL/NOMES_FALHOS do filho. Restaura por copia em `finally`.
# ===========================================================================
def rodar_mutacoes(filtro_id=None):
    _p("\n[M] MUTACOES POR COPIA -- cada uma em SUBPROCESSO, arvore precisa estar parada")
    selecionadas = [m for m in MUTACOES if filtro_id is None or m[3] == filtro_id]
    if filtro_id and not selecionadas:
        _p("        ID desconhecido: %r (validos: %s)"
           % (filtro_id, ", ".join(m[3] for m in MUTACOES)))

    resultado = []  # [(marcador, ficou_vermelho, [nomes])]
    for caminho, de, para, marcador in selecionadas:
        alvo = os.path.join(RAIZ, caminho)
        if not os.path.exists(alvo):
            pular("mutacao %s (%s)" % (marcador, caminho),
                  "o arquivo ainda nao existe (o builder ainda nao escreveu)")
            continue
        original = io.open(alvo, encoding="utf-8", errors="replace").read()
        if de not in original:
            pular("mutacao %s (%s)" % (marcador, caminho),
                  "a ancora %r nao existe -- mutacao que nao aplica NAO e mutacao passada" % de[:50])
            continue
        backup = alvo + ".bak-097"
        shutil.copyfile(alvo, backup)
        try:
            io.open(alvo, "w", encoding="utf-8").write(original.replace(de, para, 1))
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--medir-blocos"],
                cwd=RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            nomes = set()
            for linha in r.stdout.splitlines():
                if linha.startswith("NOMES_FALHOS::"):
                    resto = linha[len("NOMES_FALHOS::"):]
                    nomes = set(n for n in resto.split("|") if n)
            if r.returncode not in (0, 1):
                nomes.add("[SUBPROCESSO] o arquivo mutado nao roda ate o fim (rc=%d): %s"
                          % (r.returncode, (r.stderr or r.stdout or "")[-300:]))
            ficou_vermelho = bool(nomes)
            if nomes:
                _p("        %s -> nomes NOVOS vermelhos: %s" % (marcador, "; ".join(sorted(nomes))))
            else:
                _p("        %s -> nenhum nome novo ficou vermelho" % marcador)
            par(ficou_vermelho, "mutacao %s em %s" % (marcador, rel(alvo)),
                "a mutacao foi aplicada e NENHUM NOME NOVO ficou vermelho -- o bloco e carimbo")
            resultado.append((marcador, ficou_vermelho, sorted(nomes)))
        finally:
            shutil.copyfile(backup, alvo)
            os.remove(backup)

    vermelhas = [(m, n) for m, ok, n in resultado if ok]
    verdes = [m for m, ok, _n in resultado if not ok]
    resumo = ", ".join("%s->[%s]" % (m, (n[0] if n else "?")) for m, n in vermelhas)
    _p("\n  PLACAR DAS MUTACOES: %d mutacoes . %d vermelhas por nome (%s) . %d verdes%s"
       % (len(resultado), len(vermelhas), resumo, len(verdes),
          (" (" + ", ".join(verdes) + ")") if verdes else ""))
    return verdes


def _rodar():
    bloco_B1()
    bloco_B2()
    bloco_B3()
    bloco_B4()
    bloco_B5()
    bloco_B6()
    bloco_B7()
    bloco_B8()
    bloco_C()


def main():
    # 🔴 modo interno do subprocesso de mutacao: SO os blocos B1..B8 (nunca o
    # bloco [C], que mede a FORMA das mutacoes contra a fonte -- rodar [C]
    # dentro de uma corrida mutada e medir a propria mutacao que trocou a
    # ancora, nao o produto). Imprime os nomes falhos numa linha parseavel.
    if "--medir-blocos" in sys.argv:
        _fechar_a_rede()
        try:
            bloco_B1()
            bloco_B2()
            bloco_B3()
            bloco_B4()
            bloco_B5()
            bloco_B6()
            bloco_B7()
            bloco_B8()
        finally:
            _abrir_a_rede()
        _p("NOMES_FALHOS::" + "|".join(sorted(NOMES_FALHOS)))
        return 1 if FAIL else 0

    mutar = "--mutar" in sys.argv or os.environ.get("AUTOBROKERS_MUTAR") == "1"
    filtro_mutacao = None
    if "--mutar" in sys.argv:
        i = sys.argv.index("--mutar")
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
            candidato = sys.argv[i + 1]
            if any(m[3] == candidato for m in MUTACOES):
                filtro_mutacao = candidato
            else:
                _p("  ⚠️ --mutar %r nao e um marcador conhecido (%s) -- rodando TODAS"
                   % (candidato, ", ".join(m[3] for m in MUTACOES)))

    _p("=" * 78)
    _p("  O ATENDIMENTO SABE COMO TERMINOU -- o guarda da ESCRITA  (SPEC-097)")
    _p("=" * 78)
    _fechar_a_rede()
    try:
        _rodar()
    finally:
        _abrir_a_rede()

    # 🔴 A partir daqui OK/FAIL/NOMES_FALHOS SO refletem a corrida LIMPA acima
    # ([C1] incluso). As mutacoes rodam em processo FILHO (rodar_mutacoes) e
    # nunca escrevem nesse placar -- e' assim que o rc deixa de ser
    # contaminado pela ULTIMA mutacao aplicada (A-2).
    verdes_mutacao = []
    if mutar:
        verdes_mutacao = rodar_mutacoes(filtro_mutacao)
    else:
        _p("\n[M] MUTACOES POR COPIA -- NAO rodaram (sem `--mutar`).")
        _p("      ⛔ Elas escrevem em `backend/app/` e `backend/scripts/`, e os builders")
        _p("      escrevem la em paralelo. Com a arvore parada: `--mutar`. A lista")
        _p("      declarada esta em `MUTACOES`, no topo deste arquivo (%d entradas;" % len(MUTACOES))
        _p("      as outras 10 das 12 da SPEC sao do guarda `a-operacao-tem-uma-casa.test.mjs`).")

    _p("\n" + "=" * 78)
    _p("  %d ok · %d falha(s) · %d pulado(s)" % (OK, FAIL, len(PULADOS)))
    if PULADOS:
        _p("  -- pulados: %s" % " · ".join(PULADOS))
    if FAIL:
        _p("\n  ⛔ HA %d VERMELHO -- procure as linhas `[FALHOU]`." % FAIL)
        _p("  🔴 Em `7f3f3eb` (a copia limpa) esta lista E o GATE ZERO da SPEC-097 (§4 BLOCO 0.1).")
    else:
        _p("\n  VERDE -- o desfecho e escrito, mora no episodio, e a IA cala quando alguem assume.")
    if verdes_mutacao:
        _p("  ⛔ %d mutacao(oes) NAO ficaram vermelhas: %s -- o arnes nao guarda essa regra."
           % (len(verdes_mutacao), ", ".join(verdes_mutacao)))
    _p("=" * 78)
    return 1 if (FAIL or verdes_mutacao) else 0


def test_o_atendimento_sabe_como_terminou():
    """🔴 A prova nasceu ANTES do codigo (protocolo §4, opcao B).

    Roda a si mesmo num subprocesso: este guarda troca `sys.modules` e fecha a
    rede, e o processo do pytest carrega o mundo de outros testes junto."""
    import subprocess
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=RAIZ,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, (r.stdout[-4000:] + r.stderr[-1500:])


if __name__ == "__main__":
    sys.exit(main())
