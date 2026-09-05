# -*- coding: utf-8 -*-
"""O CASO SE EXPLICA SOZINHO -- o guarda do POS-ACIONAMENTO. SPEC-097.1.

🔴 ESCRITO ANTES DO CODIGO (protocolo AAA v11.2 §4: quem faz a prova nao faz a
resposta). Ele NASCE VERMELHO -- e e para nascer. O que esta vermelho hoje E o
GATE ZERO da 097.1.

===============================================================================
📊 A RAZAO, MEDIDA EM 05/09/2026 (SPEC-097.1 §1, `reality-report-0971.md`)
===============================================================================

    work_waits ..............................    0 linhas na vida
    work_steps step_type='dispatch_phase' ....   12 em todo o banco, e
                                                 `captured` NUNCA aparece
    human_handoff_reason NULL ...............  725 / 729
    agentes agent_role='attendance' ..........    4, todos is_active=false
    prompts de atendimento ...................  so ABERTURA (1,5 KB)
    turnos do acervo pos-acionamento .........  542 (a 2,01 msgs/turno)
    mensagens <= 24 caracteres ...............  56,3%  (R1: a unidade e o TURNO)

> O produto tem **zero** no trecho que comeca depois do protocolo. A 097.1 nao
> conserta: ela CONSTROI -- e este guarda e o contrato do que sera construido.

===============================================================================
O CONTRATO QUE ESTE GUARDA FIXA -- e o que os builders tem de escrever
===============================================================================

    app/atendimento/pos_acionamento.py                              (U3.1/E9)
        CARTAS                 as 6 cartas C1..C6 como DADOS (id, titulo,
                               texto, cobre=(rotulos)) -- linguagem de
                               corretora, cada uma termina numa proxima acao
                               com dono.
        classificar_turno(mensagens) -> rotulo          (R1: a rajada, nao a msg)
                               devolve a PRIMEIRA categoria != M/N/Z da rajada;
                               'N' quando nenhuma casa.
        mapa_de_cartas() -> {rotulo: id_da_carta}       (D,E,F,C,B,H)
        bloco_do_prompt() -> str               🔴 GERADO de
                               `mapa_de_cartas()` -- nunca constante (E9).

    app/services/dispatch_router.py::registrar_checkpoint            (U1.1/R4)
        · fase `captured`/`monitoring` COM protocolo ou previsao abre
          work_waits(kind='esperando_seguradora', scope='pos_acionamento',
                     vence_em, company_id, conversation_id, work_run_id)
        · SEM protocolo e SEM previsao: nao abre nada.
        ⛔ `encaminhado` NAO abre (E5: `marcar_fim` ja encerrou antes).
        ⛔ o escopo 'acionamento' continua sendo so do travamento (E4).

    app/services/o_fim_do_atendimento.py                             (U1.2)
        ESCOPO_POS_ACIONAMENTO = "pos_acionamento"
        · `marcar_fim` SATISFAZ a espera do pos-acionamento da conversa.
        · `abrir_espera` no MESMO escopo satisfaz a anterior com
          satisfeito_por='substituida' (o UNIQUE e por escopo).

    app/agents/tools/human_handoff.py                                (U2)
        · `_montar_dossie` de caso JA ACIONADO: titulo
          `🔁 *POS-ACIONAMENTO · <SERVICO>*`, `Quem fala`, `Onde parou`
          (de quem se espera + desde quando), `Falta`, `O que fazer`.
        ⛔ "conclua o acionamento" NUNCA em caso acionado.
        · `_arun` grava `human_handoff_reason` com default
          `pos_acionamento:<categoria>` quando o motivo vem vazio (E19).

    app/agents/graph.py  (~l.1092)                                   (U3.2)
        · anexa `bloco_do_prompt()` ao prompt base sob o MESMO gate
          `agent_role == 'attendance'` do bloco de acionamento.
        ⛔ o bloco de ABERTURA nao muda: hash congelado em [E2].

    scripts/regua_0971.py                                            (U4.1)
        medir(turnos, mapa=None) -> dict   🔴 FUNCAO PURA, sem banco e sem LLM.
        chaves: denominador · resolvido_por_carta · estado_REAL ·
                estado_SIMULADO · para_humano · pct_real · pct_simulado · teto
        · `mapa=None` usa `mapa_de_cartas()`; `mapa={}` e a linha de CONTROLE.
        · e importa `classificar_turno` de `app.atendimento.pos_acionamento` --
          o MESMO objeto que o prompt usa (§9.4: a regua chama o MOTOR).

    app/api/auxiliaries.py                                           (U3.3)
        · o draft do follow-up carrega a ESPERA ativa da conversa e devolve
          `dry_run: true` NA RESPOSTA (hoje so no metadata do run, l.689).

    ---- v1.2 (a direcao do Founder: o acompanhamento e uma FASE) ----------
    app/atendimento/acompanhamento.py                           (R10/U5.1-3)
        pode_falar_com_o_cliente(db, company_id, conversa) -> (pode, porque)
        async entregar_novidade(db, *, company_id, conversation_id, texto,
                                gatilho) -> {"gerada", "entregue",
                                             "suprimida_por", "texto"}
        🔴 UMA PORTA SO para os dois gatilhos. Nela moram `agents.is_active`,
        `companies.agent_enabled`, `acionamento_profile.acompanhamento` e
        `pausar_ia` -- duas portas seriam dois lugares para esquecer o
        desligador, e desligador esquecido e mensagem no WhatsApp de um
        segurado de verdade (R7).

    app/services/dispatch_router.py::registrar_checkpoint          (U5.1)
        · estado/previsao que MUDA em `captured`/`monitoring` chama
          `entregar_novidade` UMA vez, com texto humano (C3) do estado.
        ⛔ previsao que nao mudou: nao chama.

    app/tasks/handoff_watchdog.py::varrer_esperas_vencidas         (U5.2)
        · `scope='pos_acionamento'` vencida: alem do aviso a equipe (hoje),
          chama `entregar_novidade` com "ainda sem novidade; a corretora esta
          cobrando" -- uma por aviso, ate `AVISOS_ATE_EXPIRAR`, sem previsao.
        ⛔ `scope='acionamento'`: comportamento de hoje, nada ao cliente.

    app/atendimento/pos_acionamento.py                          (R9/R11/U3.1)
        SITUACOES_PARA_HUMANO   🔴 a FONTE UNICA lida pelo prompt, pelo
                                handoff e pela regua (K1,K2,K3,J,L,F*,B*,E*,Z,P)
        e_atendimento_de_seguro(conversa) -> bool     (R11: pessoal e colega
                                sao DESCARTADOS, nunca viram carta nem regua)

    app/agents/tools/human_handoff.py                              (U2.3)
        · o handoff POS grava `ficha_atendimento.agente_concluiu = {em,
          motivo}` (jsonb existente). ⛔ `resolvido_em` continua sendo o
          desfecho da CORRETORA.

    scripts/regua_0971.py                                        (R8/U4.1)
        · alem do que a v1.1 pedia: `resolvido_pelo_agente` (carta ∨ estado ∨
          handoff com dossie COMPLETO) · `resolvido_sem_humano` (carta ∨
          estado) · `para_humano_sem_dossie` · `descartados` (R11).

    lib/atendimento/casos.ts + scripts/a-operacao-tem-uma-casa.test.mjs  (U1.3/E6)
        · DUAS esperas ativas (escopos diferentes) -> a projecao escolhe a de
          MENOR `vence_em`; empate -> `pos_acionamento`.
        · `--fila-json` passa a expor `work_waits` do dubles, senao [L] nao tem
          como provar a escolha.

===============================================================================
A TABELA -- assercao -> R/U da SPEC -> PAR -> mutacao que a derruba
===============================================================================

  bloco  o que afirma                       R/U      PAR (controle)            mutacao
  -----  ---------------------------------  -------  ------------------------  -------
  [A1]   captured+protocolo abre a espera   R4/U1.1  [A2] sem protocolo: 0      U1
  [A1b]  a linha tem escopo pos_acionamento R4/E4    [A4] nenhum INSERT em      U1B
                                                     scope='acionamento'
  [A3]   `encaminhado` NAO abre             R4/E5    [A1] captured abre         U1C
  [B1]   marcar_fim satisfaz a espera       U1.2     [B2] outra corretora nao   U1
  [B3]   nova espera substitui a anterior   U1.2     [B3p] a 1a era 'ativo'     U1
  [K1]   dois escopos = DUAS ativas         E4       [K2] mesmo escopo = UMA    U1B
  [C1]   dossie acionado tem titulo POS     R5/U2.1  [C4] caso sem acionamento  U2
  [C2]   tem Quem fala/Onde parou/Falta     R5       [C5] o dossie ANTIGO       U2
                                                     reprova na mesma regua
  [C3]   nunca "conclua o acionamento"      R5       [C5]                       U2B
  [D1]   motivo vazio grava o default       U2.2/E19 [D2] motivo explicito      U2C
                                                     e preservado
  [E1]   o bloco POS sai de mapa_de_cartas  U3.2/E9  [E1p] mapa vazio -> bloco  U3
                                                     sem carta
  [E2]   o hash da ABERTURA nao mudou       U3.2     [E2p] 1 byte muda o hash   --
  [E3]   o gate agent_role=='attendance'    U3.2/E16 [E3p] fonte-controle sem   U3B
                                                     gate e acusada
  [J1]   trocar mapa_de_cartas muda o bloco E9       [J2] sem trocar, igual     U3
  [F]    as 6 cartas em lingua de gente     R6       [Fp] carta defeituosa      --
                                                     e acusada
  [G1]   a regua exclui M/N/Z               R8/U4.1  [G4] mapa vazio da MENOS   U4B
  [G2]   estado_REAL so com espera ativa    E10      [G2p] sem espera: 0        U4
  [G3]   o teto de desenho e impresso       E8       --
  [H1]   o draft responde dry_run: true     U3.3/E11 [H4] zero envio            U5
  [H2]   o prompt carrega a espera ativa    U3.3/E12 [H3] sem espera nao        U5B
                                                     inventa previsao
  [L1]   duas esperas -> a de menor vence   E6       [L1p] as duas SAO           --
                                                     distinguiveis
  [I1]   nenhum motor novo (cron/scheduler) §5       [I1p] fonte-controle com   --
                                                     APScheduler e acusada
  [I2]   classificar_turno e UM objeto so   §9.4     [I2p] copia != original    U4
  ---- v1.2 ------------------------------------------------------------------
  [M1]   previsao que MUDA gera a novidade   R10/U5.1 [M1p] sem mudanca, nao    --
  [M2]   desligado: GERADA e SUPRIMIDA,      R7/U5.3  [M2p] ligado: ENTREGUE    U6
         ZERO envio (3 desligadores)
  [N1]   espera POS vencida fala com o       R10/U5.2 [N3] `acionamento` segue  U6B
         cliente, uma por aviso                       como hoje; [N3b] no teto
  [N2]   a mensagem e honesta                R3       [N2b] sem data/previsao   --
  [N4]   o vigia usa a PORTA UNICA           R7       0 envios reais            U6B
  [O1]   ACEITA atendimento de verdade       R11      [O2p] separa os DOIS      U7
  [O2]   DESCARTA pessoal e colega           R11      lados                     U7
  [O3]   a regua PUBLICA os descartados      U4.1     [O3p] a fixture tem       --
  [Q1]   handoff grava `agente_concluiu`     U2.3     [Q1p] e NAO resolvido_em  --
  [Q2]   as DUAS reguas sao publicadas       R8       [Q2p] elas DIFEREM        --
  [Q3]   handoff sem dossie NAO conta        R8       [Q3b] vai para            U8
                                                      para_humano_sem_dossie
  [Q4]   SITUACOES_PARA_HUMANO e UM objeto   R9/§9.4  [Q4p] fonte sem a lista   --

===============================================================================
COMO ELE FUNCIONA -- sem rede, sem banco, sem servidor
===============================================================================

Banco DUBLADO em memoria (a classe da 096/097, com `insert/update/upsert`
REGISTRADOS e os filtros APLICADOS). A rede fica FECHADA. Quando um modulo do
produto nao importa nesta maquina, o bloco mostra a CAUSA CRUA -- nunca "ainda
nao existe" (a licao da 096).

🔴 CADA ASSERCAO EXECUTA O PRODUTO. As excecoes sao [E3] e [I1] -- gate e
ausencia de motor sao FORMA da fonte (CLAUDE.md §9.4, a excecao escrita) -- e
cada uma vem com o seu cortador-PAR, que prova que a leitura CONSEGUE acusar.

Rodar:  PYTHONIOENCODING=utf-8 python tests/test_o_caso_se_explica_sozinho.py
        (de dentro de `backend/`)
        `--mutar` roda as mutacoes por COPIA, cada uma em SUBPROCESSO sobre a
        copia mutada, restaurando em `finally`; as checagens de FORMA ([E3],
        [I1], [C5]) rodam so na fonte LIMPA. `--mutar U5` roda so ela.
"""
from __future__ import annotations

import importlib
import importlib.util
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)                      # .../backend
PROJETO = os.path.dirname(RAIZ)                     # .../AutoBrokers-FIX
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

ARNES_MJS = os.path.join(PROJETO, "scripts", "a-operacao-tem-uma-casa.test.mjs")
FIXTURE_TURNOS = os.path.join(TESTES, "fixtures", "turnos_0971.json")

CO_ALFA = "co-alfa-0000-4000-8000-000000000001"
CO_BETA = "co-beta-0000-4000-8000-000000000002"
CONVERSA_A = "11111111-1111-4111-8111-111111111111"
CONVERSA_B = "22222222-2222-4222-8222-222222222222"
RUN_A = "33333333-3333-4333-8333-333333333333"

#: 🔴 O HASH DO TRECHO DE ABERTURA -- 📊 medido em 05/09/2026, nesta arvore,
#: com a arvore limpa em `45ffde0`:
#:
#:     cd backend && PYTHONIOENCODING=utf-8 python -c "import hashlib; \
#:       from app.services.corridor_playbooks import _PLAYBOOKS, \
#:       conhecimento_de_assistencia; \
#:       b=conhecimento_de_assistencia(sorted(_PLAYBOOKS)); \
#:       print(len(b), len(_PLAYBOOKS), hashlib.sha256(b.encode('utf-8')).hexdigest())"
#:     -> 6985 14 ae32a6761152fa9f82cdf9291ffa6c169eb3da55ba6b308a66a5652050f3b394
#:
#: ⚠️ E o hash e do TEXTO GERADO, nao da fonte: e o texto que chega ao prompt.
#: Mexer num `required_slots` MUDA este hash de proposito -- e ai a 097.1 tem de
#: dizer em voz alta que mexeu na ABERTURA, que ela jurou nao tocar (U3.2).
ABERTURA_SHA256 = "ae32a6761152fa9f82cdf9291ffa6c169eb3da55ba6b308a66a5652050f3b394"
ABERTURA_TAMANHO = 6985
ABERTURA_CORREDORES = 14

# ===========================================================================
# 🔴 A DECLARACAO DE MUTACOES (SPEC-097.1 §3 G)
#
# Formato: (caminho relativo a `backend/`, de, para, marcador). Marcador UNICO,
# ancora no CODIGO que persiste -- nunca em docstring ou comentario.
# ⚠️ No gate zero quase todas PULAM: o arquivo do builder ainda nao existe. A
# mutacao que ja tem alvo hoje e a U5 (`auxiliaries.py`).
# ===========================================================================
MUTACOES = [
    # U1 -- a abertura da espera do pos-acionamento some -> [A1]/[B1] vermelhos
    ("app/services/dispatch_router.py",
     "ESCOPO_POS_ACIONAMENTO", 'ESCOPO_POS_ACIONAMENTO_MUTADO_0971_U1"" or ""',
     "U1"),
    # U1B -- o escopo vira 'acionamento' -> [A1b]/[K1] vermelhos
    ("app/services/o_fim_do_atendimento.py",
     'ESCOPO_POS_ACIONAMENTO = "pos_acionamento"',
     'ESCOPO_POS_ACIONAMENTO = "acionamento"  # _MUTADO_0971_U1B',
     "U1B"),
    # U1C -- passa a abrir tambem em `encaminhado` -> [A3] vermelho
    ("app/services/dispatch_router.py",
     'in ("captured", "monitoring")',
     'in ("captured", "monitoring", "encaminhado")  # _MUTADO_0971_U1C',
     "U1C"),
    # U2 -- o titulo POS some -> [C1] vermelho
    ("app/agents/tools/human_handoff.py",
     "PÓS-ACIONAMENTO", "ACIONAMENTO_MUTADO_0971_U2",
     "U2"),
    # U2B -- "conclua o acionamento" volta para o caso acionado -> [C3] vermelho
    ("app/agents/tools/human_handoff.py",
     "def _o_que_fazer(conversa: Dict[str, Any], motivo: str) -> str:",
     "def _o_que_fazer(conversa: Dict[str, Any], motivo: str) -> str:\n"
     '    return "Peça ao cliente o que está faltando acima e conclua o '
     'acionamento."  # _MUTADO_0971_U2B',
     "U2B"),
    # U2C -- motivo vazio deixa de gravar o default -> [D1] vermelho
    ("app/agents/tools/human_handoff.py",
     "pos_acionamento:", "sem_motivo_MUTADO_0971_U2C:",
     "U2C"),
    # U3 -- o bloco do prompt vira CONSTANTE -> [E1]/[J1] vermelhos
    ("app/atendimento/pos_acionamento.py",
     "def bloco_do_prompt(",
     "def bloco_do_prompt(*a, **k):  # _MUTADO_0971_U3\n"
     '    return "PÓS-ACIONAMENTO: responda com o que está escrito."\n\n\n'
     "def _bloco_do_prompt_original(",
     "U3"),
    # U3B -- o gate `attendance` some do anexo do bloco -> [E3] vermelho
    ("app/agents/graph.py",
     "bloco_do_prompt", "bloco_do_prompt_MUTADO_0971_U3B",
     "U3B"),
    # U4 -- a regua conta MENSAGEM em vez de TURNO -> [G1]/[I2] vermelhos
    ("scripts/regua_0971.py",
     "classificar_turno", "_classificar_msg_MUTADO_0971_U4",
     "U4"),
    # U4B -- a linha de CONTROLE deixa de honrar o mapa vazio -> [G4] vermelho
    ("scripts/regua_0971.py",
     "mapa_de_cartas()", "mapa_de_cartas()  # _MUTADO_0971_U4B\n    mapa = None",
     "U4B"),
    # U5 -- `dry_run` deixa de ser True (auxiliaries.py:689) -> [H1] vermelho
    ("app/api/auxiliaries.py",
     '"dry_run": True,', '"dry_run": False,  # _MUTADO_0971_U5',
     "U5"),
    # U5B -- o draft deixa de carregar a espera -> [H2] vermelho
    ("app/api/auxiliaries.py",
     "esperando_seguradora", "esperando_seguradora_MUTADO_0971_U5B",
     "U5B"),
    # ---- v1.2 (R10/R11/R8, SPEC §4 G) -------------------------------------
    # U6 -- a novidade SAI mesmo com o agente desligado -> [M2] vermelho
    ("app/atendimento/acompanhamento.py",
     "def pode_falar_com_o_cliente(",
     "def pode_falar_com_o_cliente(*a, **k):  # _MUTADO_0971_U6\n"
     '    return True, ""\n\n\n'
     "def _pode_falar_com_o_cliente_original(",
     "U6"),
    # U6B -- o vigia manda ao cliente por fora da porta unica -> [N4] vermelho
    ("app/tasks/handoff_watchdog.py",
     "entregar_novidade", "_entregar_direto_MUTADO_0971_U6B",
     "U6B"),
    # U7 -- o filtro deixa passar conversa pessoal -> [O2] vermelho
    ("app/atendimento/pos_acionamento.py",
     "def e_atendimento_de_seguro(",
     "def e_atendimento_de_seguro(*a, **k):  # _MUTADO_0971_U7\n"
     "    return True\n\n\n"
     "def _e_atendimento_de_seguro_original(",
     "U7"),
    # U8 -- handoff SEM `Onde parou` passa a contar como resolvido -> [Q3] vermelho
    ("scripts/regua_0971.py",
     "o_que_fazer", "o_que_fazer_MUTADO_0971_U8",
     "U8"),
]

# ===========================================================================
# A rede fechada -- so dentro de main()
# ===========================================================================
_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _loopback(destino):
    """⚠️ O `asyncio` do Windows abre um socketpair em 127.0.0.1 para o proprio
    laco de eventos. Barrar o loopback impediria o guarda de rodar `async`."""
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
# O placar -- tres verbos (o molde de 095/096/097, protocolo §5)
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


def ler(relativo):
    caminho = os.path.join(RAIZ, relativo)
    if not os.path.exists(caminho):
        return ""
    return io.open(caminho, encoding="utf-8", errors="replace").read()


def so_o_codigo_py(fonte):
    """O python sem docstring de modulo e sem `#`. A prosa ja enganou sete
    assercoes na SPEC-086 e nao vai enganar a oitava."""
    sem_doc = '"""'.join(fonte.split('"""')[::2])
    return "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())


def razao_ausencia(erro, mensagem_de_produto):
    """🔴 A licao da 096: quando o modulo NAO IMPORTA, mostre a CAUSA CRUA."""
    if erro is None:
        return mensagem_de_produto
    texto = "%s: %s" % (type(erro).__name__, erro)
    if isinstance(erro, ModuleNotFoundError):
        m = re.search(r"No module named '([^']+)'", str(erro))
        faltando = m.group(1) if m else str(erro)
        # 🔴 A licao da 096 tem DOIS lados. "AMBIENTE" so vale para o que esta
        #    FORA do produto (langgraph, redis, qdrant). Um `app.*` que nao
        #    existe e o PRODUTO que ainda nao foi escrito -- e chamar isso de
        #    ambiente ensinaria o builder a procurar no lugar errado.
        if faltando.startswith("app.") or faltando.startswith("scripts."):
            return ("PRODUTO: `%s` ainda nao existe -- %s (%s)"
                    % (faltando, mensagem_de_produto, texto))
        return ("AMBIENTE: falta %s -- o bloco nao pode ser medido nesta maquina (%s)"
                % (faltando.split(".")[0], texto))
    return "IMPORT FALHOU: %s -- (a razao de produto seria: %s)" % (texto, mensagem_de_produto)


def importar(caminho_modulo, razao):
    """Importa PELO PACOTE (nao por caminho): [I2] afirma identidade de objeto,
    e dois carregamentos por caminho dariam dois objetos distintos de graca."""
    try:
        return importlib.import_module(caminho_modulo), None
    except Exception as erro:  # noqa: BLE001
        return None, RuntimeError(razao_ausencia(erro, razao))


def carregar_solto(relativo, nome):
    """Importa um arquivo do produto por CAMINHO -- para `scripts/`, que nao e
    pacote. Devolve `(modulo, erro)`."""
    caminho = os.path.join(RAIZ, relativo)
    if not os.path.exists(caminho):
        return None, FileNotFoundError(
            "PRODUTO: `backend/%s` ainda nao existe -- o builder nao escreveu" % relativo)
    try:
        spec = importlib.util.spec_from_file_location(nome, caminho)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
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

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def maybe_single(self):
        return self

    def single(self):
        return self

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

    def eq(self, c, v):
        self.filtros.append(("eq", c, v))
        return self

    def neq(self, c, v):
        self.filtros.append(("neq", c, v))
        return self

    def in_(self, c, vs):
        self.filtros.append(("in", c, list(vs)))
        return self

    def is_(self, c, v):
        (self.nulos if v in (None, "null") else self.nao_nulos).append(c)
        return self

    def not_(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def lte(self, *a, **k):
        return self

    def _casa(self, linha):
        for op, campo, valor in self.filtros:
            atual = linha.get(campo)
            if op == "in":
                if atual not in valor:
                    return False
            elif op == "neq":
                if str(atual) == str(valor):
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
                nova.setdefault("created_at", "2026-09-05T12:00:00+00:00")
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
    """O cliente do Supabase que a tool de handoff usa e SINCRONO."""

    def execute(self):  # type: ignore[override]
        return self._rodar()


class Banco:
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

    def escritas(self, tabela=None, op=None):
        return [r for r in self.registro
                if r["op"] in ("insert", "upsert", "update", "delete")
                and (tabela is None or r["tabela"] == tabela)
                and (op is None or r["op"] == op)]

    def linhas(self, tabela):
        return list(self.dados.get(tabela) or [])


def espera_ativa(conversa=CONVERSA_A, empresa=CO_ALFA, scope="pos_acionamento",
                 kind="esperando_seguradora", vence="2026-09-12T12:00:00+00:00",
                 desde="2026-08-29T09:00:00+00:00", ident="ww-pos-1"):
    return {"id": ident, "company_id": empresa, "conversation_id": conversa,
            "work_run_id": RUN_A, "kind": kind, "scope": scope, "status": "ativo",
            "vence_em": vence, "satisfeito_por": None, "satisfeito_em": None,
            "avisos": 0, "created_at": desde, "updated_at": desde}


def conversa_acionada():
    """🔴 O MUNDO DEFEITUOSO que a 097 esqueceu: a conversa com DONO, status e
    um acionamento JA ENTREGUE. Fixture ficticia e obvia -- NUNCA PII."""
    return {"id": CONVERSA_A, "company_id": CO_ALFA, "session_id": "ss-pos-1",
            "user_phone": "5511900000001", "user_name": "Cliente Canario",
            "status": "HUMAN_REQUESTED", "claimed_by": None, "claimed_by_name": None,
            "human_handoff_reason": None, "last_message_preview":
                "o vidro ja tem previsao? o protocolo saiu semana passada",
            "ficha_atendimento": {"servico": "vidros", "seguradora": "canaria",
                                  "ramo": "auto", "protocolo": "P-CANARIO-1",
                                  "dispatch_state": "captured",
                                  "faltando": []},
            "resolvido_em": None, "resolucao_motivo": None}


def conversa_sem_acionamento():
    c = conversa_acionada()
    c = dict(c, id=CONVERSA_B, session_id="ss-novo-1",
             last_message_preview="meu carro quebrou agora, preciso de guincho")
    c["ficha_atendimento"] = {"servico": "guincho", "faltando": ["endereço exato"]}
    return c


# ===========================================================================
# [A] O CORREDOR ESCREVE A ESPERA -- `registrar_checkpoint`, MOTOR REAL
# ===========================================================================
def _sessao(fase, protocolo=None, previsao=None):
    s = {"state": fase, "work_run_id": RUN_A, "case_id": "case-canario",
         "mirror_conversation_id": CONVERSA_A, "playbook_ref": "canaria-auto",
         "subservice": "vidros", "company_id": CO_ALFA}
    if protocolo:
        s["protocolo"] = protocolo
        s["slots"] = {"protocolo": protocolo}
    if previsao:
        s["previsao"] = previsao
        s.setdefault("slots", {})["previsao"] = previsao
    return s


def _checkpoint(fase, protocolo=None, previsao=None, dados=None):
    """Roda o funil REAL (`registrar_checkpoint`) com o banco dublado."""
    import asyncio

    DR, erro = importar("app.services.dispatch_router",
                        "o corredor do acionamento ainda nao carrega")
    if DR is None:
        return None, None, erro
    banco = Banco(dados if dados is not None else {"work_waits": []})

    async def _db_dublado():
        return banco

    original = DR._db
    DR._db = _db_dublado
    try:
        asyncio.run(DR.registrar_checkpoint(CO_ALFA, "5511999999999",
                                            _sessao(fase, protocolo, previsao)))
    except Exception as exc:  # noqa: BLE001
        return banco, None, exc
    finally:
        DR._db = original
    return banco, DR, None


def _inserts_de_espera(banco):
    return [r["carga"] for r in banco.escritas("work_waits", "insert")]


def bloco_A():
    _p("\n[A] R4/U1.1 -- o corredor ABRE a espera quando o acionamento entrega protocolo")
    banco, _dr, erro = _checkpoint("captured", protocolo="P-CANARIO-1",
                                   previsao="2026-09-12T12:00:00+00:00")
    if banco is None:
        certo(False, "[A1] `registrar_checkpoint` roda com o banco dublado", repr(erro))
        return
    if erro is not None:
        certo(False, "[A1] `registrar_checkpoint` roda com o banco dublado",
              "%s: %s" % (type(erro).__name__, erro))
        return

    abertas = _inserts_de_espera(banco)
    pos = [c for c in abertas if str((c or {}).get("scope")) == "pos_acionamento"]
    certo(len(pos) == 1,
          "[A1] `captured` COM protocolo abre UMA espera de pos-acionamento",
          "inserts em work_waits=%r" % (abertas,))
    linha = pos[0] if pos else {}
    certo(str(linha.get("kind")) == "esperando_seguradora",
          "[A1b] a espera e `esperando_seguradora` (R2/E13: `esperando_oficina` NAO e kind)",
          "kind=%r" % linha.get("kind"))
    certo(str(linha.get("company_id")) == CO_ALFA
          and str(linha.get("conversation_id")) == CONVERSA_A
          and bool(str(linha.get("vence_em") or "").strip()),
          "[A1c] a linha tem corretora (§7), conversa e `vence_em`",
          "linha=%r" % (linha,))

    # 🔴 O PAR de [A1]: o MESMO motor, o MESMO mundo, SEM protocolo e SEM
    #    previsao. Se abrir aqui tambem, [A1] nao mede o protocolo -- mede a fase.
    banco2, _dr2, erro2 = _checkpoint("captured")
    sem = _inserts_de_espera(banco2) if banco2 is not None else []
    par(not [c for c in sem if str((c or {}).get("scope")) == "pos_acionamento"],
        "[A2] `captured` SEM protocolo e SEM previsao nao abre nada",
        "abriu %r (erro=%r)" % (sem, erro2))

    # E5 -- `encaminhado` ja ENCERRA o atendimento antes (MOTIVO_DO_ESTADO).
    banco3, _dr3, _e3 = _checkpoint("encaminhado", protocolo="P-CANARIO-1")
    enc = _inserts_de_espera(banco3) if banco3 is not None else []
    certo(not [c for c in enc if str((c or {}).get("scope")) == "pos_acionamento"],
          "[A3] `encaminhado` NAO abre espera nova (E5: `marcar_fim` venceu)",
          "abriu %r" % (enc,))

    par(not [c for c in abertas if str((c or {}).get("scope")) == "acionamento"],
        "[A4] o escopo do TRAVAMENTO nao recebe INSERT nenhum (E4)",
        "inserts=%r" % (abertas,))


# ===========================================================================
# [B]/[K] A ESPERA SE FECHA -- `marcar_fim` e o escopo
# ===========================================================================
def bloco_B():
    _p("\n[B] U1.2 -- `marcar_fim` satisfaz a espera, e a nova SUBSTITUI a anterior")
    import asyncio

    FIM, erro = importar("app.services.o_fim_do_atendimento",
                         "o modulo do desfecho ainda nao carrega")
    if FIM is None:
        certo(False, "[B1] `o_fim_do_atendimento` importa", repr(erro))
        return

    escopo = getattr(FIM, "ESCOPO_POS_ACIONAMENTO", None)
    certo(escopo == "pos_acionamento",
          "[B0] `ESCOPO_POS_ACIONAMENTO` e um nome do modulo, nao uma string solta",
          "valor=%r" % (escopo,))
    escopo = escopo or "pos_acionamento"

    mundo = {"conversations": [conversa_acionada()],
             "attendance_sessions": [],
             "work_waits": [espera_ativa(),
                            # a espera de OUTRA corretora -- o PAR do §7
                            espera_ativa(conversa=CONVERSA_A, empresa=CO_BETA,
                                         ident="ww-beta-1")]}
    banco = Banco(mundo)
    try:
        asyncio.run(FIM.marcar_fim(banco, company_id=CO_ALFA,
                                   motivo=FIM.ACIONAMENTO_CONCLUIDO,
                                   conversation_id=CONVERSA_A))
        rodou, exc = True, None
    except Exception as e:  # noqa: BLE001
        rodou, exc = False, e

    linhas = {l["id"]: l for l in banco.linhas("work_waits")}
    alfa = linhas.get("ww-pos-1", {})
    beta = linhas.get("ww-beta-1", {})
    certo(rodou and str(alfa.get("status")) == "satisfeito"
          and bool(str(alfa.get("satisfeito_por") or "").strip()),
          "[B1] `marcar_fim` satisfaz a espera de pos-acionamento da conversa",
          "rodou=%r exc=%r linha=%r" % (rodou, exc, alfa))
    par(str(beta.get("status")) == "ativo",
        "[B2] a espera da OUTRA corretora continua ativa (§7)",
        "linha beta=%r" % (beta,))

    # U1.2 -- nova espera no MESMO escopo satisfaz a anterior com 'substituida'
    banco2 = Banco({"work_waits": [espera_ativa()]})
    try:
        asyncio.run(FIM.abrir_espera(banco2, company_id=CO_ALFA,
                                     conversation_id=CONVERSA_A,
                                     kind=FIM.ESPERANDO_SEGURADORA,
                                     vence_em_iso="2026-09-20T12:00:00+00:00",
                                     scope=escopo))
        rodou2, exc2 = True, None
    except Exception as e:  # noqa: BLE001
        rodou2, exc2 = False, e
    todas = banco2.linhas("work_waits")
    antiga = [l for l in todas if l["id"] == "ww-pos-1"]
    ativas = [l for l in todas if str(l.get("status")) == "ativo"]
    certo(rodou2 and antiga and str(antiga[0].get("status")) == "satisfeito"
          and str(antiga[0].get("satisfeito_por")) == "substituida",
          "[B3] a espera nova SUBSTITUI a anterior no mesmo escopo",
          "rodou=%r exc=%r linhas=%r" % (rodou2, exc2, todas))
    par(len(ativas) <= 1,
        "[B3p] depois da substituicao sobra UMA ativa no escopo (o UNIQUE)",
        "ativas=%r" % (ativas,))


def bloco_K():
    _p("\n[K] E4 -- o UNIQUE e POR ESCOPO: dois escopos convivem, o mesmo nao")
    import asyncio

    FIM, erro = importar("app.services.o_fim_do_atendimento",
                         "o modulo do desfecho ainda nao carrega")
    if FIM is None:
        certo(False, "[K1] `o_fim_do_atendimento` importa", repr(erro))
        return
    escopo = getattr(FIM, "ESCOPO_POS_ACIONAMENTO", "pos_acionamento")

    banco = Banco({"work_waits": []})

    async def _abrir(scope, kind, vence):
        return await FIM.abrir_espera(banco, company_id=CO_ALFA,
                                      conversation_id=CONVERSA_A, kind=kind,
                                      vence_em_iso=vence, scope=scope)

    async def _dois():
        await _abrir("acionamento", FIM.ESPERANDO_HUMANO, "2026-09-10T12:00:00+00:00")
        await _abrir(escopo, FIM.ESPERANDO_SEGURADORA, "2026-09-12T12:00:00+00:00")

    try:
        asyncio.run(_dois())
        exc = None
    except Exception as e:  # noqa: BLE001
        exc = e
    ativas = [l for l in banco.linhas("work_waits") if str(l.get("status")) == "ativo"]
    escopos = sorted(str(l.get("scope")) for l in ativas)
    certo(exc is None and escopos == sorted(["acionamento", escopo]),
          "[K1] abrir em 'acionamento' e em 'pos_acionamento' da DUAS ativas",
          "exc=%r escopos=%r" % (exc, escopos))

    banco2 = Banco({"work_waits": []})

    async def _mesmo():
        for v in ("2026-09-12T12:00:00+00:00", "2026-09-13T12:00:00+00:00"):
            await FIM.abrir_espera(banco2, company_id=CO_ALFA,
                                   conversation_id=CONVERSA_A,
                                   kind=FIM.ESPERANDO_SEGURADORA,
                                   vence_em_iso=v, scope=escopo)

    try:
        asyncio.run(_mesmo())
        exc2 = None
    except Exception as e:  # noqa: BLE001
        exc2 = e
    ativas2 = [l for l in banco2.linhas("work_waits") if str(l.get("status")) == "ativo"]
    par(exc2 is None and len(ativas2) == 1,
        "[K2] duas no MESMO escopo: a segunda substitui, sobra UMA",
        "exc=%r ativas=%r" % (exc2, ativas2))


# ===========================================================================
# [C]/[D] O HANDOFF DIZ POS -- `_montar_dossie` e `_arun`, MOTOR REAL
# ===========================================================================
#: 🔴 A REGUA DO DOSSIE POS. Ela e uma FUNCAO porque tem de rodar duas vezes:
#: sobre o dossie NOVO (tem de passar) e sobre o dossie ANTIGO do MESMO caso
#: acionado (tem de reprovar). Sem a segunda passada ela nao distingue nada --
#: e regua que nao distingue e carimbo (CLAUDE.md §9.3).
def regua_do_dossie_pos(texto):
    p = []
    t = str(texto or "")
    if "PÓS-ACIONAMENTO" not in t:
        p.append("nao diz que e POS-ACIONAMENTO (cairia em SINISTRO ou no generico)")
    if "🔁" not in t:
        p.append("sem a marca 🔁 do retorno")
    for rotulo in ("Quem fala", "Onde parou", "Falta", "O que fazer"):
        if rotulo.lower() not in t.lower():
            p.append("nao tem a secao `%s`" % rotulo)
    if "conclua o acionamento" in t.lower():
        p.append("manda CONCLUIR um acionamento que ja foi feito")
    return p


def bloco_C():
    _p("\n[C] R5/U2.1 -- o dossie de um caso JA ACIONADO diz POS, e nunca 'conclua'")
    HH, erro = importar("app.agents.tools.human_handoff",
                        "a tool de handoff ainda nao carrega")
    if HH is None:
        certo(False, "[C1] `human_handoff` importa", repr(erro))
        return

    mundo = {"conversations": [conversa_acionada(), conversa_sem_acionamento()],
             "work_waits": [espera_ativa()],
             "messages": [{"role": "user", "content": "e a previsao do vidro?",
                           "created_at": "2026-09-05T12:00:00+00:00", "payload": {}}]}
    banco = Banco(mundo, sincrono=True)
    try:
        tool = HH.HumanHandoffTool(banco)
        dossie = tool._montar_dossie(conversa_acionada(), "")
        exc = None
    except Exception as e:  # noqa: BLE001
        dossie, exc = "", e
    if exc is not None:
        certo(False, "[C1] `_montar_dossie` roda sobre o caso acionado",
              "%s: %s" % (type(exc).__name__, exc))
        return

    problemas = regua_do_dossie_pos(dossie)
    certo(not problemas, "[C1] o dossie do caso acionado passa na regua POS",
          "problemas=%r\n         dossie=%r" % (problemas, dossie[:400]))
    certo("VIDROS" in dossie.upper(),
          "[C2] o titulo nomeia o SERVICO em lingua de gente", dossie[:120])
    certo("esperando" in dossie.lower() and "29/08" in dossie,
          "[C2b] `Onde parou` diz de quem se espera E desde quando (a espera ativa)",
          dossie[:400])

    # 🔴 O PAR que prova que a regua distingue: o MESMO caso, o dossie de HOJE.
    banco2 = Banco(mundo, sincrono=True)
    try:
        antigo = "\n".join([HH._titulo_humano(conversa_acionada(), ""), HH._TRACO,
                            HH._o_que_fazer(conversa_acionada(), "")])
    except Exception as e:  # noqa: BLE001
        antigo = "ERRO: %s" % e
    par(bool(regua_do_dossie_pos(antigo)),
        "[C5] o dossie ANTIGO sobre o MESMO caso acionado reprova na regua",
        "antigo=%r" % antigo[:300])

    # E o caso SEM acionamento continua com o titulo de sempre.
    try:
        tool2 = HH.HumanHandoffTool(banco2)
        novo_caso = tool2._montar_dossie(conversa_sem_acionamento(), "")
    except Exception as e:  # noqa: BLE001
        novo_caso = "ERRO: %s" % e
    par("PÓS-ACIONAMENTO" not in novo_caso,
        "[C4] caso SEM acionamento NAO recebe o titulo POS",
        novo_caso[:200])


def bloco_D():
    _p("\n[D] U2.2/E19 -- `human_handoff_reason` e GRAVADO, e nunca vai vazio")
    import asyncio

    HH, erro = importar("app.agents.tools.human_handoff",
                        "a tool de handoff ainda nao carrega")
    if HH is None:
        certo(False, "[D1] `human_handoff` importa", repr(erro))
        return

    def _rodar(motivo):
        mundo = {"conversations": [conversa_acionada()],
                 "work_waits": [espera_ativa()], "messages": []}
        banco = Banco(mundo, sincrono=True)
        tool = HH.HumanHandoffTool(banco)

        # 🔴 O DUBLE DE SAIDA: nada sai. E ele CONTA -- [H4] usa o mesmo verbo.
        enviados = []

        async def _sem_saida(*a, **k):
            enviados.append((a, k))
            return {"avisado": False, "motivo": "duble do guarda"}

        tool._avisar_suporte = _sem_saida
        try:
            asyncio.run(tool._arun(reason=motivo, session_id="ss-pos-1",
                                   company_id=CO_ALFA))
            exc = None
        except Exception as e:  # noqa: BLE001
            exc = e
        cargas = [r["carga"] for r in banco.escritas("conversations", "update")]
        return cargas, exc, enviados

    cargas, exc, _env = _rodar("")
    motivos = [str((c or {}).get("human_handoff_reason") or "") for c in cargas]
    gravados = [m for m in motivos if m]
    certo(exc is None and gravados and gravados[0].startswith("pos_acionamento:"),
          "[D1] motivo VAZIO grava o default `pos_acionamento:<categoria>`",
          "exc=%r cargas=%r" % (exc, cargas))

    cargas2, exc2, _e2 = _rodar("cliente pediu pessoa")
    motivos2 = [str((c or {}).get("human_handoff_reason") or "") for c in cargas2]
    par(exc2 is None and "cliente pediu pessoa" in motivos2,
        "[D2] motivo EXPLICITO e preservado, nao sobrescrito pelo default",
        "cargas=%r" % (cargas2,))


# ===========================================================================
# [E]/[J]/[F] O PROMPT E AS CARTAS
# ===========================================================================
#: 🔴 O guarda de lingua humana da 097 ([13], R11), aplicado as cartas.
_CHAVE = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+(@\d+)?|[a-z]+_[a-z_]+@\d+|\B@\d+\b")
_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_APOLICE = ("segurado fica obrigado", "conforme cláusula", "nos termos da apólice",
            "sub-rogação", "salvo disposição em contrário")
_ACAO_COM_DONO = ("quer que eu", "eu confirmo", "eu cobro", "me diz", "pode mandar",
                  "vou verificar", "eu te aviso", "eu procuro", "eu confiro")


def problemas_de_lingua(texto):
    p = []
    t = str(texto or "")
    baixo = t.lower()
    for m in _SNAKE.findall(baixo):
        p.append("snake_case: %r" % m)
    for m in _CHAVE.findall(baixo):
        if m:
            p.append("chave/versao: %r" % (m,))
    if re.search(r"\B@\d+\b", t):
        p.append("versao `@N`")
    for frase in _APOLICE:
        if frase in baixo:
            p.append("lingua de apolice: %r" % frase)
    if not any(a in baixo for a in _ACAO_COM_DONO):
        p.append("nao termina numa proxima acao COM DONO")
    return p


def bloco_F():
    _p("\n[F] R6 -- as 6 cartas falam como corretora, e cada uma tem dono da proxima acao")
    PA, erro = importar("app.atendimento.pos_acionamento",
                        "as cartas do pos-acionamento ainda nao existem")
    if PA is None:
        certo(False, "[F1] `app/atendimento/pos_acionamento.py` importa", repr(erro))
        return

    cartas = list(getattr(PA, "CARTAS", []) or [])
    if isinstance(getattr(PA, "CARTAS", None), dict):
        cartas = list(PA.CARTAS.values())
    certo(len(cartas) == 6, "[F1] sao SEIS cartas (C1..C6)", "n=%d" % len(cartas))
    for i, carta in enumerate(cartas, 1):
        texto = carta.get("texto") if isinstance(carta, dict) else str(carta)
        titulo = carta.get("titulo") if isinstance(carta, dict) else ""
        p = problemas_de_lingua("%s\n%s" % (titulo, texto))
        certo(not p, "[F2.%d] a carta %r passa no guarda de lingua humana"
              % (i, str(titulo)[:40]), "problemas=%r" % p[:6])

    # 🔴 O PAR: uma carta ESCRITA ERRADO tem de ser acusada -- senao [F2] e carimbo.
    ruim = ("O status do caso e `dispatch_state.captured@1`; o segurado fica "
            "obrigado a aguardar.")
    par(bool(problemas_de_lingua(ruim)),
        "[Fp] a carta-controle (chave + lingua de apolice + sem dono) e acusada")


def bloco_E():
    _p("\n[E] U3.2/E9 -- o bloco POS e GERADO das cartas, e a ABERTURA nao muda")
    import hashlib

    PA, erro = importar("app.atendimento.pos_acionamento",
                        "o gerador do bloco do prompt ainda nao existe")
    if PA is None:
        certo(False, "[E1] `pos_acionamento` importa", repr(erro))
    else:
        try:
            bloco = PA.bloco_do_prompt()
            exc = None
        except Exception as e:  # noqa: BLE001
            bloco, exc = "", e
        certo(exc is None and len(str(bloco)) > 200,
              "[E1] `bloco_do_prompt()` gera texto",
              "exc=%r len=%d" % (exc, len(str(bloco))))
        mapa = {}
        try:
            mapa = PA.mapa_de_cartas() or {}
        except Exception as e:  # noqa: BLE001
            mapa = {"ERRO": e}
        certo(bool(mapa) and all(str(v) in str(bloco) or
                                 str(v).lower() in str(bloco).lower() for v in mapa.values()),
              "[E1b] o bloco cita TODAS as cartas do mapa (e gerado dele)",
              "mapa=%r" % (mapa,))
        certo("não" in str(bloco).lower() and "escrit" in str(bloco).lower(),
              "[E1c] o bloco manda dizer que NAO ha novidade quando nao ha estado ESCRITO (R3)",
              str(bloco)[:300])

    # E2 -- o trecho de ABERTURA, EXECUTADO. Nao e leitura de fonte: e o texto
    #       que chega ao prompt do agente de atendimento.
    try:
        from app.services.corridor_playbooks import _PLAYBOOKS, conhecimento_de_assistencia
        abertura = conhecimento_de_assistencia(sorted(_PLAYBOOKS))
        h = hashlib.sha256(abertura.encode("utf-8")).hexdigest()
        certo(h == ABERTURA_SHA256 and len(abertura) == ABERTURA_TAMANHO
              and len(_PLAYBOOKS) == ABERTURA_CORREDORES,
              "[E2] o bloco de ABERTURA e IDENTICO ao medido em 05/09/2026",
              "sha=%s len=%d corredores=%d (esperado %s/%d/%d)"
              % (h, len(abertura), len(_PLAYBOOKS), ABERTURA_SHA256,
                 ABERTURA_TAMANHO, ABERTURA_CORREDORES))
        par(hashlib.sha256((abertura + " ").encode("utf-8")).hexdigest() != ABERTURA_SHA256,
            "[E2p] um byte a mais MUDA o hash (o guarda consegue reprovar)")
    except Exception as e:  # noqa: BLE001
        certo(False, "[E2] o bloco de ABERTURA e medivel", repr(e))

    # E3 -- ⚠️ A METADE FRACA, DECLARADA: o GATE mora dentro de uma funcao de
    #       1.100 linhas de `graph.py` que so roda com langgraph, LLM e banco.
    #       Aqui se le a FONTE sem comentario -- e o PAR abaixo prova que a
    #       leitura consegue acusar uma fonte sem gate (CLAUDE.md §9.4).
    fonte = so_o_codigo_py(ler("app/agents/graph.py"))
    def _tem_gate(texto):
        i = texto.find("bloco_do_prompt")
        if i < 0:
            return False
        janela = texto[max(0, i - 1500):i + 500]
        return ('_papel == "attendance"' in janela
                or "_papel == 'attendance'" in janela
                or 'agent_role") or "").strip().lower()' in janela and "attendance" in janela)
    certo(_tem_gate(fonte),
          "[E3] `graph.py` anexa o bloco POS sob o gate `agent_role=='attendance'`",
          "📊 4 agentes attendance (E16); metade fraca declarada")
    par(not _tem_gate('base_instructions += bloco_do_prompt()'),
        "[E3p] a fonte-controle SEM gate e acusada pela mesma leitura")


def bloco_J():
    _p("\n[J] E9 -- mudar `mapa_de_cartas()` MUDA o bloco do prompt")
    PA, erro = importar("app.atendimento.pos_acionamento",
                        "o gerador do bloco do prompt ainda nao existe")
    if PA is None:
        certo(False, "[J1] `pos_acionamento` importa", repr(erro))
        return
    try:
        antes = PA.bloco_do_prompt()
        igual = PA.bloco_do_prompt()
        original = PA.mapa_de_cartas
        PA.mapa_de_cartas = lambda: {}
        try:
            depois = PA.bloco_do_prompt()
        finally:
            PA.mapa_de_cartas = original
        exc = None
    except Exception as e:  # noqa: BLE001
        antes = igual = depois = ""
        exc = e
    certo(exc is None and antes and depois != antes,
          "[J1] com o mapa VAZIO o bloco muda -- ele nao e constante",
          "exc=%r antes=%d depois=%d" % (exc, len(str(antes)), len(str(depois))))
    par(antes == igual,
        "[J2] sem trocar nada o bloco e IGUAL (a diferenca veio do mapa, nao do acaso)")


# ===========================================================================
# [G] A REGUA DA META -- `scripts/regua_0971.py::medir(turnos)`
# ===========================================================================
def _turnos_da_fixture():
    if not os.path.exists(FIXTURE_TURNOS):
        return None, "a fixture %s nao existe" % FIXTURE_TURNOS
    try:
        bruto = json.load(io.open(FIXTURE_TURNOS, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return None, "a fixture nao e JSON valido (%s)" % e
    # ⚠️ As entradas `_doc*` sao a PROSA da fixture (por que cada faixa existe).
    #    Contar prosa no denominador seria o defeito que [G1] mede.
    return [t for t in bruto if isinstance(t, dict) and "turno" in t], None


def bloco_G():
    _p("\n[G] R8/U4.1 -- a regua conta TURNO, exclui M/N/Z e publica o teto")
    turnos, motivo = _turnos_da_fixture()
    if turnos is None:
        certo(False, "[G0] a fixture sintetica de turnos existe", motivo)
        return
    RG, erro = carregar_solto("scripts/regua_0971.py", "_regua_0971")
    if RG is None:
        certo(False, "[G1] `scripts/regua_0971.py` carrega e expoe `medir`",
              razao_ausencia(erro, "a regua da meta ainda nao existe"))
        return
    if not hasattr(RG, "medir"):
        certo(False, "[G1] `regua_0971.medir(turnos)` existe",
              "o modulo carrega mas nao tem `medir`")
        return
    try:
        r = RG.medir(turnos)
        exc = None
    except Exception as e:  # noqa: BLE001
        r, exc = {}, e
    if exc is not None:
        certo(False, "[G1] `medir(turnos)` roda sobre a fixture",
              "%s: %s" % (type(exc).__name__, exc))
        return

    # 📊 A fixture declara, em cada turno, o rotulo esperado. O denominador
    #    honesto e o numero de turnos cujo rotulo nao e M/N/Z.
    esperado = len([t for t in turnos if str(t.get("rotulo_esperado")) not in ("M", "N", "Z")])
    certo(int(r.get("denominador") or 0) == esperado,
          "[G1] o denominador exclui social (M), fragmento (N) e midia (Z)",
          "medido=%r esperado=%d" % (r.get("denominador"), esperado))

    com_carta = int(r.get("resolvido_por_carta") or 0)
    certo(com_carta > 0 and com_carta <= esperado,
          "[G2] `resolvido_por_carta` conta so rotulo COM carta no mapa",
          "resolvido_por_carta=%r denominador=%d" % (r.get("resolvido_por_carta"), esperado))

    # E10 -- estado REAL so existe com espera ativa NO INSTANTE do turno.
    #        📊 zero `captured` no banco: sobre uma fixture sem espera, e ZERO.
    sem_espera = [dict(t, espera_ativa=False) for t in turnos]
    try:
        r_sem = RG.medir(sem_espera)
    except Exception as e:  # noqa: BLE001
        r_sem = {"ERRO": e}
    certo(int(r_sem.get("estado_REAL") or 0) == 0,
          "[G2b] sem espera ativa, `estado_REAL` e ZERO -- e a regua DIZ isso (E10)",
          "r_sem=%r" % (r_sem,))
    par(int(r.get("estado_REAL") or 0) > 0,
        "[G2p] com espera ativa na fixture, `estado_REAL` e maior que zero "
        "(as duas passadas CONSEGUEM diferir)",
        "com=%r sem=%r" % (r.get("estado_REAL"), r_sem.get("estado_REAL")))

    certo(r.get("teto") is not None,
          "[G3] a regua publica o TETO de desenho ao lado do numero (E8)",
          "chaves=%r" % sorted(r))

    # 🔴 A LINHA DE CONTROLE: a MESMA passada com o mapa de cartas VAZIO.
    try:
        r_controle = RG.medir(turnos, mapa={})
    except Exception as e:  # noqa: BLE001
        r_controle = {"ERRO": e}
    par(int(r_controle.get("resolvido_por_carta") or 0) < com_carta,
        "[G4] o CONTROLE (mapa vazio) resolve MENOS que com as cartas",
        "controle=%r com_cartas=%d" % (r_controle.get("resolvido_por_carta"), com_carta))


# ===========================================================================
# [H] O FOLLOW-UP -- o endpoint REAL, e nada sai
# ===========================================================================
def _chamar_draft(mundo, objetivo="saber a previsao"):
    """POST /follow-up-whatsapp/draft de verdade (TestClient), com o banco
    dublado, a chave interna dublada e o LLM dublado. Devolve
    `(status, corpo, prompt_visto, envios, erro)`."""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api import auxiliaries as AUX
        from app.core.database import get_async_db
    except Exception as e:  # noqa: BLE001
        return None, None, None, None, e

    banco = Banco(mundo)
    visto = {}
    envios = []

    # 🔴 O DUBLE DE SAIDA, no ponto REAL por onde sai mensagem de WhatsApp.
    #    ⚠️ Um contador que nada consegue incrementar nao guarda nada
    #    (CLAUDE.md §9.3) -- por isso [H4] tem o par que o INCREMENTA.
    try:
        from app.services import whatsapp_service as WS

        original_envio = WS.WhatsappService.send_message

        def _sem_saida(self, *a, **k):  # noqa: ANN001
            envios.append((a, k))
            return False

        WS.WhatsappService.send_message = _sem_saida
    except Exception:  # noqa: BLE001
        WS, original_envio = None, None

    async def _draft_dublado(*a, **k):
        visto["args"] = a
        visto["kwargs"] = k
        return ("Oi! Ainda estamos acompanhando o seu caso.", {"input_tokens": 1,
                                                               "output_tokens": 1}, "duble")

    original_draft = AUX._draft_followup
    original_saldo = AUX._require_sufficient_balance
    AUX._draft_followup = _draft_dublado
    AUX._require_sufficient_balance = lambda company_id: None
    os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-do-guarda-0971")

    app = FastAPI()
    app.include_router(AUX.router)
    app.dependency_overrides[get_async_db] = lambda: banco
    try:
        with TestClient(app) as cliente:
            resp = cliente.post("/follow-up-whatsapp/draft",
                                headers={"X-AutoBrokers-Internal-Key":
                                         os.environ["BACKEND_INTERNAL_API_KEY"]},
                                json={"company_id": CO_ALFA,
                                      "conversation_id": CONVERSA_A,
                                      "objective": objetivo})
        corpo = None
        try:
            corpo = resp.json()
        except Exception:  # noqa: BLE001
            corpo = {"texto": resp.text[:300]}
        return resp.status_code, corpo, visto, envios, None
    except Exception as e:  # noqa: BLE001
        return None, None, visto, envios, e
    finally:
        AUX._draft_followup = original_draft
        AUX._require_sufficient_balance = original_saldo
        if WS is not None and original_envio is not None:
            _cobaia = WS.WhatsappService.send_message
            WS.WhatsappService.send_message = original_envio
            # o par de [H4]: o contador SABE contar -- provado com o duble ainda
            # em memoria, depois de a medicao do endpoint ja ter sido colhida.
            visto["contador_sabe_contar"] = (
                lambda: (_cobaia(None, "5511900000001", "controle", {}), len(envios))[1])


def bloco_H():
    _p("\n[H] U3.3/E11/E12 -- o rascunho e RASCUNHO, e carrega a espera escrita")
    mundo = {"conversations": [conversa_acionada()],
             "work_waits": [espera_ativa()],
             "messages": [{"role": "user", "content": "alguma novidade?",
                           "created_at": "2026-09-05T12:00:00+00:00"}],
             "tenant_auxiliaries": [{"id": "ta-1", "company_id": CO_ALFA,
                                     "slug": "follow-up-whatsapp",
                                     "status": "active", "template_id": "tpl-1"}],
             "auxiliary_runs": []}
    status, corpo, visto, envios, erro = _chamar_draft(mundo)
    if erro is not None:
        certo(False, "[H1] o endpoint do rascunho responde",
              razao_ausencia(erro, "a rota do follow-up nao pode ser chamada"))
        return
    certo(status == 200, "[H0] `POST /follow-up-whatsapp/draft` responde 200",
          "status=%r corpo=%r" % (status, corpo))
    certo(isinstance(corpo, dict) and corpo.get("dry_run") is True,
          "[H1] a RESPOSTA diz `dry_run: true` (E11: hoje isso so existe no metadata)",
          "corpo=%r" % (corpo,))

    prompt = json.dumps(visto or {}, ensure_ascii=False, default=str).lower()
    certo("esperando" in prompt and "seguradora" in prompt and "29/08" in prompt,
          "[H2] o que vai ao modelo carrega a ESPERA ATIVA da conversa (de quem, desde quando)",
          "visto=%s" % prompt[:400])

    # CONTROLE: sem espera ativa, o rascunho nao inventa previsao.
    mundo2 = dict(mundo, work_waits=[])
    _s2, _c2, visto2, _e2, erro2 = _chamar_draft(mundo2)
    prompt2 = json.dumps(visto2 or {}, ensure_ascii=False, default=str).lower()
    inventou = bool(re.search(r"previs[ãa]o de |\b\d{2}/\d{2}\b", prompt2))
    par(erro2 is None and not inventou,
        "[H3] SEM espera ativa o rascunho nao carrega previsao nem data",
        "visto=%s" % prompt2[:300])

    certo(envios == [],
          "[H4] NENHUMA funcao de envio foi chamada -- nada sai (R7)",
          "envios=%r" % (envios,))
    contar = (visto or {}).get("contador_sabe_contar")
    par(callable(contar) and contar() == 1,
        "[H4p] o contador de envio SABE contar (o duble incrementa quando chamado)",
        "contador=%r" % (contar,))


# ===========================================================================
# [L] A PROJECAO ESCOLHE A ESPERA CERTA -- o MESMO arnes da 097, por node
# ===========================================================================
def bloco_L():
    _p("\n[L] E6/U1.3 -- com DUAS esperas ativas, a projecao escolhe a de menor `vence_em`")
    if not os.path.exists(ARNES_MJS):
        certo(False, "[L1] o arnes da 097 existe", "%s nao existe" % ARNES_MJS)
        return
    try:
        r = subprocess.run(["node", ARNES_MJS, "--fila-json"], cwd=PROJETO,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
    except FileNotFoundError as exc:
        certo(False, "[L1] o arnes roda",
              "AMBIENTE: `node` nao esta no PATH desta maquina (%s)" % exc)
        return
    except subprocess.TimeoutExpired:
        certo(False, "[L1] o arnes roda", "nao terminou em 300s")
        return
    if r.returncode != 0:
        certo(False, "[L1] o arnes roda",
              "saiu com %d: %s" % (r.returncode, (r.stderr or "")[-500:]))
        return
    try:
        dados = json.loads(r.stdout)
    except ValueError as exc:
        certo(False, "[L1] o arnes devolve JSON", "%s: %s" % (exc, r.stdout[:300]))
        return

    waits = ((dados.get("mundo") or {}).get("work_waits")) or []
    if not waits:
        certo(False, "[L1] `--fila-json` expoe `work_waits` do duble",
              "sem as linhas de espera nao ha como provar QUAL a projecao escolheu (E6)")
        return

    ativas = {}
    for w in waits:
        if str(w.get("status")) == "ativo":
            ativas.setdefault(str(w.get("conversation_id")), []).append(w)
    duplas = {k: v for k, v in ativas.items() if len(v) >= 2}
    if not duplas:
        certo(False, "[L1] o mundo do arnes tem uma conversa com DUAS esperas ativas",
              "📊 hoje o duble tem no maximo uma por conversa -- sem o par, E6 nao e testavel")
        return

    conversa, par_de_esperas = sorted(duplas.items())[0]
    def _chave(w):
        return (str(w.get("vence_em") or "9999"),
                0 if str(w.get("scope")) == "pos_acionamento" else 1)
    correta = sorted(par_de_esperas, key=_chave)[0]
    outra = [w for w in par_de_esperas if w is not correta]

    itens = ((dados.get("projecao") or {}).get("items")) or []
    achado = [i for i in itens
              if str(((i.get("agora") or {}).get("esperando") or {}).get("fonte_id") or
                     (i.get("esperando") or {}).get("fonte_id") or "") ]
    escolhida = ""
    for i in itens:
        e = (i.get("agora") or {}).get("esperando") or i.get("esperando") or {}
        if str(i.get("conversa_id") or i.get("conversaId") or "") == conversa:
            escolhida = str(e.get("fonte_id") or "")
    certo(escolhida == str(correta.get("id")),
          "[L1] a projecao escolheu a espera de MENOR `vence_em` (empate -> pos_acionamento)",
          "escolhida=%r correta=%r candidatas=%r itens_com_espera=%d"
          % (escolhida, correta.get("id"), par_de_esperas, len(achado)))
    par(bool(outra) and str(outra[0].get("id")) != str(correta.get("id"))
        and str(outra[0].get("vence_em")) != str(correta.get("vence_em")),
        "[L1p] as duas esperas SAO distinguiveis (vencimentos diferentes)",
        "par=%r" % (par_de_esperas,))


# ===========================================================================
# [I] NENHUM MOTOR NOVO -- §5, e o mesmo objeto nos dois lugares
# ===========================================================================
_MOTOR_NOVO = re.compile(
    r"\bAPScheduler\b|\bBackgroundScheduler\b|\bCronTrigger\b|\bcelery\.beat\b|"
    r"\bschedule\.every\b|add_periodic_task|\basyncio\.create_task\(\s*_?loop",
    re.IGNORECASE)

_TOCADOS_PELA_0971 = (
    "app/atendimento/pos_acionamento.py",
    "app/services/dispatch_router.py",
    "app/services/o_fim_do_atendimento.py",
    "app/agents/tools/human_handoff.py",
    "app/api/auxiliaries.py",
    "scripts/regua_0971.py",
    "scripts/canario_0971.py",
    "scripts/publicar_cartas_0971.py",
)


def bloco_I():
    _p("\n[I] §5 -- nenhum motor paralelo, e `classificar_turno` e UMA funcao so")
    achados = []
    for rel_ in _TOCADOS_PELA_0971:
        fonte = so_o_codigo_py(ler(rel_))
        if not fonte:
            continue
        for m in _MOTOR_NOVO.findall(fonte):
            achados.append((rel_, m))
    certo(not achados,
          "[I1] nenhum scheduler/cron/listener novo nos arquivos da 097.1",
          "achados=%r (o gatilho do follow-up e P-097.1-GATILHO-DO-FOLLOW-UP)" % achados[:5])
    par(bool(_MOTOR_NOVO.search(
            "from apscheduler.schedulers.background import BackgroundScheduler\n"
            "sched = BackgroundScheduler()")),
        "[I1p] a fonte-controle COM APScheduler e acusada pela mesma leitura")

    PA, erro_pa = importar("app.atendimento.pos_acionamento", "as cartas ainda nao existem")
    RG, erro_rg = carregar_solto("scripts/regua_0971.py", "_regua_0971_i2")
    if PA is None or RG is None:
        certo(False, "[I2] a regua e o prompt compartilham `classificar_turno`",
              "pos_acionamento: %r · regua: %r" % (erro_pa, erro_rg))
        return
    certo(getattr(RG, "classificar_turno", None) is getattr(PA, "classificar_turno", 1),
          "[I2] `classificar_turno` da regua e o MESMO OBJETO do modulo das cartas (§9.4)",
          "regua=%r cartas=%r" % (getattr(RG, "classificar_turno", None),
                                  getattr(PA, "classificar_turno", None)))
    # 🔴 O PAR de [I2]: uma COPIA que se comporta igual nao passa no `is`. Sem
    #    isto, "sao o mesmo objeto" poderia ser verdade por acaso e ninguem
    #    saberia que a asserçao consegue reprovar (CLAUDE.md §9.3).
    import types

    alvo = getattr(PA, "classificar_turno", None)
    try:
        copia = types.FunctionType(alvo.__code__, alvo.__globals__, "copia_0971")
        sabe_reprovar = copia is not alvo
    except Exception as e:  # noqa: BLE001
        copia, sabe_reprovar = e, False
    par(sabe_reprovar,
        "[I2p] uma COPIA da mesma funcao NAO passa no `is` (a identidade sabe reprovar)",
        "copia=%r" % (copia,))


# ===========================================================================
# [M] O ACOMPANHAMENTO (R10/U5.1) -- a novidade nasce, e o desligador cala
#
# 🔴 A PORTA E UMA SO. O gatilho do corredor (U5.1) e o do vigia (U5.2) passam
# pela MESMA funcao, porque e nela que moram `agents.is_active`,
# `companies.agent_enabled`, `acionamento_profile.acompanhamento` e `pausar_ia`.
# Duas portas seriam dois lugares para esquecer o desligador -- e o desligador
# esquecido e mensagem no WhatsApp de um segurado de verdade (R7).
#
#     app/atendimento/acompanhamento.py
#       pode_falar_com_o_cliente(db, company_id, conversa) -> (pode, porque)
#       async entregar_novidade(db, *, company_id, conversation_id, texto,
#                               gatilho) -> {"gerada", "entregue",
#                                            "suprimida_por", "texto"}
# ===========================================================================
def _mundo_do_acompanhamento(ligado=True, acompanhamento=True, assumida=False):
    conversa = conversa_acionada()
    conversa["status"] = "open"
    if assumida:
        conversa["claimed_by"] = "u-atendente-1"
        conversa["claimed_by_name"] = "Alguem da equipe"
    perfil = {} if acompanhamento else {"acompanhamento": False}
    return {"conversations": [conversa],
            "companies": [{"id": CO_ALFA, "agent_enabled": bool(ligado),
                           "acionamento_profile": perfil}],
            "agents": [{"id": "ag-1", "company_id": CO_ALFA,
                        "agent_role": "attendance", "is_active": bool(ligado)}],
            "work_waits": [espera_ativa()],
            "work_events": [], "messages": []}


def _com_outbound_dublado(fn):
    """Roda `fn(envios)` com TODA saida de WhatsApp dublada e CONTADA."""
    envios = []
    try:
        from app.services import whatsapp_service as WS
    except Exception as exc:  # noqa: BLE001
        return None, envios, exc
    original = WS.WhatsappService.send_message

    def _sem_saida(self, *a, **k):  # noqa: ANN001
        envios.append((a, k))
        return False

    WS.WhatsappService.send_message = _sem_saida
    try:
        return fn(envios), envios, None
    except Exception as exc:  # noqa: BLE001
        return None, envios, exc
    finally:
        WS.WhatsappService.send_message = original


def bloco_M():
    _p("\n[M] R10/U5.1 -- o corredor gera a NOVIDADE, e o desligador a suprime")
    import asyncio

    AC, erro = importar("app.atendimento.acompanhamento",
                        "a porta unica do acompanhamento ainda nao existe")
    if AC is None:
        certo(False, "[M1] `app/atendimento/acompanhamento.py` importa", repr(erro))
        return

    # ---- M1: o corredor CHAMA a porta quando a previsao MUDA ---------------
    chamadas = []

    async def _recorder(db, **k):
        chamadas.append(k)
        return {"gerada": True, "entregue": False, "suprimida_por": "duble",
                "texto": str(k.get("texto") or "")}

    original = AC.entregar_novidade
    AC.entregar_novidade = _recorder
    try:
        mundo = _mundo_do_acompanhamento()
        mundo["work_waits"] = [espera_ativa(vence="2026-09-12T12:00:00+00:00")]
        banco, _dr, exc = _checkpoint("captured", protocolo="P-CANARIO-1",
                                      previsao="2026-09-19T12:00:00+00:00",
                                      dados=mundo)
        # o CONTROLE: o MESMO checkpoint, com a previsao que ja estava escrita
        chamadas_com_mudanca = list(chamadas)
        chamadas[:] = []
        mundo2 = _mundo_do_acompanhamento()
        mundo2["work_waits"] = [espera_ativa(vence="2026-09-12T12:00:00+00:00")]
        _b2, _d2, _e2 = _checkpoint("captured", protocolo="P-CANARIO-1",
                                    previsao="2026-09-12T12:00:00+00:00",
                                    dados=mundo2)
        chamadas_sem_mudanca = list(chamadas)
    finally:
        AC.entregar_novidade = original

    certo(exc is None and len(chamadas_com_mudanca) == 1,
          "[M1] previsao que MUDA em `captured` gera UMA novidade ao cliente",
          "exc=%r chamadas=%r" % (exc, chamadas_com_mudanca))
    texto = str((chamadas_com_mudanca or [{}])[0].get("texto") or "")
    certo(bool(texto) and not problemas_de_lingua(texto)
          and ("seguradora" in texto.lower() or "loja" in texto.lower()),
          "[M1b] a novidade e TEXTO HUMANO e diz o estado (R3/R6)",
          "texto=%r problemas=%r" % (texto[:200], problemas_de_lingua(texto)[:4]))
    par(not chamadas_sem_mudanca,
        "[M1p] o MESMO checkpoint SEM mudanca de previsao nao gera novidade",
        "chamadas=%r" % (chamadas_sem_mudanca,))

    # ---- M2: o desligador. A novidade e GERADA e SUPRIMIDA, e nada sai ------
    def _entregar(mundo):
        banco = Banco(mundo)

        def _rodar(_envios):
            return asyncio.run(AC.entregar_novidade(
                banco, company_id=CO_ALFA, conversation_id=CONVERSA_A,
                texto="A loja ainda nao devolveu a previsao; seguimos cobrando.",
                gatilho="corredor"))

        r, envios, exc_ = _com_outbound_dublado(_rodar)
        return r or {}, envios, exc_, banco

    for nome, mundo in (("agente desligado", _mundo_do_acompanhamento(ligado=False)),
                        ("acompanhamento=false",
                         _mundo_do_acompanhamento(acompanhamento=False)),
                        ("conversa assumida",
                         _mundo_do_acompanhamento(assumida=True))):
        r, envios, exc_, banco = _entregar(mundo)
        certo(exc_ is None and r.get("gerada") is True and r.get("entregue") is False
              and bool(str(r.get("suprimida_por") or "").strip()) and envios == [],
              "[M2 · %s] a novidade e GERADA e SUPRIMIDA, e ZERO envio" % nome,
              "exc=%r r=%r envios=%r" % (exc_, r, envios))
        eventos = [c["carga"] for c in banco.escritas("work_events", "insert")]
        certo(any("suprimida_por" in json.dumps(e, default=str) for e in eventos),
              "[M2b · %s] a supressao fica REGISTRADA (`suprimida_por`)" % nome,
              "work_events=%r" % (eventos,))

    # ---- o CONTROLE de [M2]: tudo LIGADO, a novidade e entregue -------------
    r_on, envios_on, exc_on, _b = _entregar(_mundo_do_acompanhamento())
    par(exc_on is None and r_on.get("entregue") is True
        and not str(r_on.get("suprimida_por") or "").strip(),
        "[M2p] com o agente LIGADO e o acompanhamento LIGADO, ela e ENTREGUE "
        "(as duas passadas CONSEGUEM diferir)",
        "r=%r envios=%r exc=%r" % (r_on, envios_on, exc_on))


# ===========================================================================
# [N] O VIGIA QUE JA RODA (R10/U5.2) -- a espera vencida fala com o cliente
# ===========================================================================
def _vigiar(mundo):
    """Roda `varrer_esperas_vencidas` REAL com o banco dublado."""
    import asyncio

    WD, erro = importar("app.tasks.handoff_watchdog", "o vigia nao carrega")
    if WD is None:
        return None, None, erro
    try:
        from app.core import database as DB
    except Exception as exc:  # noqa: BLE001
        return None, None, exc
    banco = Banco(mundo)

    async def _cliente():
        return banco

    original = DB.create_async_supabase_client
    DB.create_async_supabase_client = _cliente
    try:
        resumo = asyncio.run(WD.varrer_esperas_vencidas())
        return banco, resumo, None
    except Exception as exc:  # noqa: BLE001
        return banco, None, exc
    finally:
        DB.create_async_supabase_client = original


def bloco_N():
    _p("\n[N] R10/U5.2 -- a espera VENCIDA avisa a equipe (como hoje) E fala com o cliente")
    AC, erro = importar("app.atendimento.acompanhamento",
                        "a porta unica do acompanhamento ainda nao existe")
    if AC is None:
        certo(False, "[N1] `app/atendimento/acompanhamento.py` importa", repr(erro))
        return
    FIM, _e = importar("app.services.o_fim_do_atendimento", "o desfecho nao carrega")
    teto = getattr(FIM, "AVISOS_ATE_EXPIRAR", 3) if FIM else 3

    vencida = "2026-09-01T12:00:00+00:00"
    chamadas = []

    async def _recorder(db, **k):
        chamadas.append(k)
        return {"gerada": True, "entregue": False, "suprimida_por": "duble",
                "texto": str(k.get("texto") or "")}

    original = AC.entregar_novidade
    AC.entregar_novidade = _recorder
    try:
        mundo = _mundo_do_acompanhamento()
        mundo["work_waits"] = [espera_ativa(vence=vencida)]
        _b, resumo, exc = _vigiar(mundo)
        do_pos = list(chamadas)

        # CONTROLE: a espera do TRAVAMENTO vencida -> comportamento de hoje
        chamadas[:] = []
        mundo2 = _mundo_do_acompanhamento()
        mundo2["work_waits"] = [espera_ativa(vence=vencida, scope="acionamento",
                                             kind="esperando_humano", ident="ww-ac-1")]
        _b2, _r2, _e2 = _vigiar(mundo2)
        do_acionamento = list(chamadas)

        # e a espera que JA gastou os avisos nao fala mais
        chamadas[:] = []
        mundo3 = _mundo_do_acompanhamento()
        linha = espera_ativa(vence=vencida)
        linha["avisos"] = teto
        mundo3["work_waits"] = [linha]
        _b3, _r3, _e3 = _vigiar(mundo3)
        no_teto = list(chamadas)
    finally:
        AC.entregar_novidade = original

    certo(exc is None and len(do_pos) == 1,
          "[N1] espera `pos_acionamento` vencida gera UMA mensagem ao cliente",
          "exc=%r resumo=%r chamadas=%r" % (exc, resumo, do_pos))
    texto = str((do_pos or [{}])[0].get("texto") or "").lower()
    certo("novidade" in texto and "cobra" in texto,
          "[N2] a mensagem e a HONESTA: sem novidade, e a corretora esta cobrando (R3)",
          "texto=%r" % texto[:200])
    # ⚠️ `bool(texto)` NAO e enfeite: sem ele, uma mensagem VAZIA passaria na
    #    regex e [N2b] seria um guarda que nao tem como falhar (§9.3).
    certo(bool(texto) and not re.search(
              r"previs[ãa]o de |\b\d{2}/\d{2}\b|\bat[ée] \d+ *(h|dia|min)", texto),
          "[N2b] e NAO inventa previsao, data nem prazo",
          "texto=%r" % texto[:200])
    par(bool(re.search(r"previs[ãa]o de |\b\d{2}/\d{2}\b",
                       "previsao de 12/09 para a peca")),
        "[N2bp] a regex de previsao inventada SABE acusar (texto-controle)")
    par(not do_acionamento,
        "[N3] a espera do TRAVAMENTO (`scope='acionamento'`) segue como hoje: "
        "avisa a equipe e NAO fala com o cliente",
        "chamadas=%r" % (do_acionamento,))
    par(not no_teto,
        "[N3b] no teto de `AVISOS_ATE_EXPIRAR` (%d) o cliente nao recebe mais nada" % teto,
        "chamadas=%r" % (no_teto,))

    # ---- N4: o vigia NAO tem porta propria. Com o desligador ligado e SEM
    #          recorder, a saida real tem de ser ZERO.
    mundo4 = _mundo_do_acompanhamento(acompanhamento=False)
    mundo4["work_waits"] = [espera_ativa(vence=vencida)]

    def _rodar(_envios):
        return _vigiar(mundo4)

    (_b4, _r4, exc4), envios, exc_out = _com_outbound_dublado(_rodar)
    certo(exc_out is None and envios == [],
          "[N4] com `acompanhamento=false` o vigia nao manda NADA ao cliente "
          "(ele usa a porta unica, nao uma propria)",
          "envios=%r exc=%r" % (envios, exc_out or exc4))


# ===========================================================================
# [O] R11 -- so ATENDIMENTO vira conhecimento
#
# 💭 As conversas abaixo sao SINTETICAS, reescritas do §2 do relatorio (a linha
# da atendente carrega caso, colega e vida pessoal no mesmo fio). ZERO PII.
# ===========================================================================
_PESSOAIS = [
    ["oi, tudo bem? como foi o fim de semana?", "levei as criancas na praia"],
    ["passa pra fulana, por favor", "me coloca em copia do e-mail"],
    ["voce ja almocou?", "vou sair mais cedo hoje"],
    ["bom diaaa", "kkkk"],
]
_ATENDIMENTOS = [
    ["meu carro quebrou, preciso de guincho na br"],
    ["o vidro do para-brisa trincou, tem cobertura?"],
    ["qual o valor da franquia do meu seguro?"],
    ["a oficina credenciada ja recebeu a autorizacao da seguradora?"],
]


def bloco_O():
    _p("\n[O] R11 -- conversa pessoal e coordenacao entre colegas NAO viram conhecimento")
    PA, erro = importar("app.atendimento.pos_acionamento",
                        "o filtro `e_atendimento_de_seguro` ainda nao existe")
    if PA is None:
        certo(False, "[O1] `pos_acionamento` importa", repr(erro))
        return
    filtro = getattr(PA, "e_atendimento_de_seguro", None)
    if not callable(filtro):
        certo(False, "[O1] `e_atendimento_de_seguro(conversa)` existe e e chamavel",
              "encontrado=%r" % (filtro,))
        return

    def _conversa(msgs):
        return {"id": "cv-sintetica", "company_id": CO_ALFA,
                "mensagens": [{"role": "user", "content": m} for m in msgs],
                "messages": [{"role": "user", "content": m} for m in msgs],
                "texto": " ".join(msgs)}

    aceitos, erros = [], []
    for msgs in _ATENDIMENTOS:
        try:
            aceitos.append(bool(filtro(_conversa(msgs))))
        except Exception as e:  # noqa: BLE001
            erros.append(e)
    certo(not erros and all(aceitos) and len(aceitos) == len(_ATENDIMENTOS),
          "[O1] ACEITA as %d conversas de atendimento (guincho, vidro, franquia, oficina)"
          % len(_ATENDIMENTOS),
          "aceitos=%r erros=%r" % (aceitos, erros[:2]))

    descartados = []
    for msgs in _PESSOAIS:
        try:
            descartados.append(not bool(filtro(_conversa(msgs))))
        except Exception as e:  # noqa: BLE001
            erros.append(e)
    certo(not erros and all(descartados) and len(descartados) == len(_PESSOAIS),
          "[O2] DESCARTA papo pessoal e coordenacao entre colegas",
          "descartados=%r" % (descartados,))
    par(all(descartados) and all(aceitos),
        "[O2p] o filtro separa os DOIS lados -- ele nao esta so dizendo sim ou so nao",
        "aceitos=%r descartados=%r" % (aceitos, descartados))

    # ---- O3: e a REGUA conta o que foi descartado (U4.1) --------------------
    turnos, motivo = _turnos_da_fixture()
    RG, erro_rg = carregar_solto("scripts/regua_0971.py", "_regua_0971_o")
    if turnos is None or RG is None or not hasattr(RG, "medir"):
        certo(False, "[O3] a regua conta os descartados por R11",
              "fixture=%r regua=%r" % (motivo, erro_rg))
        return
    try:
        r = RG.medir(turnos)
        exc = None
    except Exception as e:  # noqa: BLE001
        r, exc = {}, e
    pessoais = len([t for t in turnos if t.get("pessoal")])
    certo(exc is None and int(r.get("descartados") or 0) == pessoais,
          "[O3] a regua PUBLICA quantos turnos foram descartados por R11",
          "exc=%r descartados=%r esperado=%d" % (exc, r.get("descartados"), pessoais))
    par(pessoais > 0,
        "[O3p] a fixture TEM turnos descartaveis (senao a contagem seria zero por vazio)",
        "pessoais=%d" % pessoais)


# ===========================================================================
# [Q] R8/U2.3 -- o agente ENCERRA a parte dele, e as duas reguas dizem isso
# ===========================================================================
def bloco_Q():
    _p("\n[Q] R8/U2.3 -- o handoff POS grava `agente_concluiu`, e a regua conta as DUAS linhas")
    import asyncio

    HH, erro = importar("app.agents.tools.human_handoff", "a tool de handoff nao carrega")
    if HH is None:
        certo(False, "[Q1] `human_handoff` importa", repr(erro))
    else:
        mundo = {"conversations": [conversa_acionada()],
                 "work_waits": [espera_ativa()], "messages": []}
        banco = Banco(mundo, sincrono=True)
        tool = HH.HumanHandoffTool(banco)

        async def _sem_saida(*a, **k):
            return {"avisado": False, "motivo": "duble do guarda"}

        tool._avisar_suporte = _sem_saida
        try:
            asyncio.run(tool._arun(reason="", session_id="ss-pos-1", company_id=CO_ALFA))
            exc = None
        except Exception as e:  # noqa: BLE001
            exc = e
        cargas = [c["carga"] for c in banco.escritas("conversations", "update")]
        marca = {}
        for c in cargas:
            ficha = (c or {}).get("ficha_atendimento") or {}
            if isinstance(ficha, dict) and ficha.get("agente_concluiu"):
                marca = ficha["agente_concluiu"]
        certo(exc is None and isinstance(marca, dict)
              and bool(str(marca.get("em") or "").strip())
              and bool(str(marca.get("motivo") or "").strip()),
              "[Q1] o handoff POS grava `ficha_atendimento.agente_concluiu = {em, motivo}`",
              "exc=%r cargas=%r" % (exc, cargas))
        # ⛔ `resolvido_em` continua sendo o desfecho da CORRETORA (U2.3).
        par(not any("resolvido_em" in (c or {}) for c in cargas),
            "[Q1p] o handoff NAO grava `resolvido_em` -- encerrar a parte do agente "
            "nao e resolver o caso da corretora",
            "cargas=%r" % (cargas,))

    turnos, motivo = _turnos_da_fixture()
    RG, erro_rg = carregar_solto("scripts/regua_0971.py", "_regua_0971_q")
    PA, erro_pa = importar("app.atendimento.pos_acionamento", "as cartas nao existem")
    if turnos is None or RG is None or not hasattr(RG, "medir") or PA is None:
        certo(False, "[Q2] a regua e o modulo das cartas carregam",
              "fixture=%r regua=%r cartas=%r" % (motivo, erro_rg, erro_pa))
        return
    try:
        r = RG.medir(turnos)
        exc2 = None
    except Exception as e:  # noqa: BLE001
        r, exc2 = {}, e
    agente = int((r or {}).get("resolvido_pelo_agente") or 0)
    sem_humano = int((r or {}).get("resolvido_sem_humano") or 0)
    certo(exc2 is None and "resolvido_pelo_agente" in r and "resolvido_sem_humano" in r,
          "[Q2] a regua publica as DUAS linhas (R8)",
          "exc=%r chaves=%r" % (exc2, sorted(r)))
    par(agente > sem_humano,
        "[Q2p] as duas linhas SAO diferentes na fixture (o handoff POS soma "
        "algo que a outra nao conta -- §9.3)",
        "resolvido_pelo_agente=%r resolvido_sem_humano=%r" % (agente, sem_humano))

    # 🔴 O handoff SEM `Onde parou`/`O que fazer` NAO conta. Sem esta linha,
    #    "foi para humano" viraria carimbo de resolvido (R8, CLAUDE.md §9.5).
    quebrados = [dict(t, dossie={"o_que_fazer": ""}) if t.get("dossie") else t
                 for t in turnos]
    try:
        r_quebrado = RG.medir(quebrados)
    except Exception as e:  # noqa: BLE001
        r_quebrado = {"ERRO": e}
    certo(int(r_quebrado.get("resolvido_pelo_agente") or 0) < agente,
          "[Q3] handoff SEM `Onde parou`/`O que fazer` NAO conta como resolvido",
          "quebrado=%r inteiro=%d" % (r_quebrado.get("resolvido_pelo_agente"), agente))
    certo(int(r_quebrado.get("para_humano_sem_dossie") or 0) > 0,
          "[Q3b] o que perdeu o dossie aparece em `para_humano_sem_dossie`",
          "r=%r" % (r_quebrado,))

    # A FONTE UNICA (R9): a mesma lista no prompt, no handoff e na regua.
    situacoes = getattr(PA, "SITUACOES_PARA_HUMANO", None)
    certo(situacoes is not None
          and getattr(RG, "SITUACOES_PARA_HUMANO", None) is situacoes,
          "[Q4] `SITUACOES_PARA_HUMANO` da regua e o MESMO OBJETO do modulo (§9.4)",
          "cartas=%r regua=%r" % (type(situacoes), type(getattr(RG, "SITUACOES_PARA_HUMANO", None))))
    fonte_hh = so_o_codigo_py(ler("app/agents/tools/human_handoff.py"))
    certo("SITUACOES_PARA_HUMANO" in fonte_hh,
          "[Q4b] o handoff LE a mesma lista (metade fraca: leitura da fonte)",
          "📊 sem isto, `O que fazer` seria uma segunda verdade sobre R9")
    par("SITUACOES_PARA_HUMANO" not in so_o_codigo_py(
            'def _o_que_fazer(c, m):\n    return "Confira e siga."  # sem a lista'),
        "[Q4p] a fonte-controle SEM a lista e acusada pela mesma leitura")


# ===========================================================================
# As mutacoes por COPIA -- so com `--mutar`
#
# 🔴 Cada uma roda em SUBPROCESSO sobre a copia MUTADA, e o processo PAI (que
# tem as checagens de FORMA -- [E3], [I1], [C5] -- na sua propria corrida sobre
# a fonte LIMPA) nunca reusa o placar do filho. Restaura por copia em `finally`.
# ===========================================================================
def _nomes_falhos_num_filho():
    """Roda `--medir-blocos` num processo FILHO e devolve os nomes vermelhos."""
    r = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--medir-blocos"],
        cwd=RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    nomes = set()
    for linha in r.stdout.splitlines():
        if linha.startswith("NOMES_FALHOS::"):
            nomes = set(n for n in linha[len("NOMES_FALHOS::"):].split("|") if n)
    return nomes, r


def rodar_mutacoes(filtro_id=None):
    _p("\n[M] MUTACOES POR COPIA -- cada uma em SUBPROCESSO, arvore precisa estar parada")
    # 🔴 A LINHA DE BASE, medida no MESMO filho que vai medir as mutacoes.
    #
    # ⚠️ Sem ela a mutacao se creditaria pelo vermelho que JA existia -- e no
    # gate zero, onde quase tudo esta vermelho, TODA mutacao pareceria boa. O
    # que decide e o conjunto de nomes NOVOS (antes x depois), nunca a
    # contagem (CLAUDE.md §9.2: a linha de controle e o que da direito a
    # conclusao).
    base, _r = _nomes_falhos_num_filho()
    _p("      linha de BASE (arvore limpa, no filho): %d nome(s) ja vermelho(s)" % len(base))
    selecionadas = [m for m in MUTACOES if filtro_id is None or m[3] == filtro_id]
    if filtro_id and not selecionadas:
        _p("        ID desconhecido: %r (validos: %s)"
           % (filtro_id, ", ".join(m[3] for m in MUTACOES)))

    resultado = []
    for caminho, de, para, marcador in selecionadas:
        alvo = os.path.join(RAIZ, caminho)
        if not os.path.exists(alvo):
            pular("mutacao %s (%s)" % (marcador, caminho),
                  "o arquivo ainda nao existe (o builder ainda nao escreveu)")
            continue
        original = io.open(alvo, encoding="utf-8", errors="replace").read()
        if de not in original:
            pular("mutacao %s (%s)" % (marcador, caminho),
                  "a ancora %r nao existe -- mutacao que nao aplica NAO e mutacao passada"
                  % de[:60])
            continue
        backup = alvo + ".bak-0971"
        shutil.copyfile(alvo, backup)
        try:
            io.open(alvo, "w", encoding="utf-8").write(original.replace(de, para, 1))
            nomes, r = _nomes_falhos_num_filho()
            novos = nomes - base
            if r.returncode not in (0, 1):
                novos.add("[SUBPROCESSO] o arquivo mutado nao roda ate o fim (rc=%d): %s"
                          % (r.returncode, (r.stderr or r.stdout or "")[-300:]))
            ficou_vermelho = bool(novos)
            if novos:
                _p("        %s -> nomes NOVOS vermelhos: %s" % (marcador, "; ".join(sorted(novos))))
            else:
                _p("        %s -> nenhum nome NOVO ficou vermelho (%d ja estavam)"
                   % (marcador, len(nomes & base)))
            par(ficou_vermelho, "mutacao %s em %s" % (marcador, caminho),
                "a mutacao foi aplicada e NENHUM NOME NOVO ficou vermelho -- o bloco e carimbo")
            resultado.append((marcador, ficou_vermelho, sorted(novos)))
        finally:
            shutil.copyfile(backup, alvo)
            os.remove(backup)

    vermelhas = [(m, n) for m, ok, n in resultado if ok]
    verdes = [m for m, ok, _n in resultado if not ok]
    _p("\n  PLACAR DAS MUTACOES: %d rodadas . %d vermelhas . %d verdes%s"
       % (len(resultado), len(vermelhas), len(verdes),
          (" (" + ", ".join(verdes) + ")") if verdes else ""))
    return verdes


def _rodar():
    bloco_A()
    bloco_B()
    bloco_K()
    bloco_C()
    bloco_D()
    bloco_F()
    bloco_E()
    bloco_J()
    bloco_G()
    bloco_H()
    bloco_L()
    bloco_I()
    bloco_M()
    bloco_N()
    bloco_O()
    bloco_Q()


def main():
    if "--medir-blocos" in sys.argv:
        _fechar_a_rede()
        try:
            _rodar()
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
                _p("  ⚠️ --mutar %r nao e marcador conhecido (%s) -- rodando TODAS"
                   % (candidato, ", ".join(m[3] for m in MUTACOES)))

    _p("=" * 78)
    _p("  O CASO SE EXPLICA SOZINHO -- o guarda do POS-ACIONAMENTO  (SPEC-097.1)")
    _p("=" * 78)
    _fechar_a_rede()
    try:
        _rodar()
    finally:
        _abrir_a_rede()

    verdes_mutacao = []
    if mutar:
        verdes_mutacao = rodar_mutacoes(filtro_mutacao)
    else:
        _p("\n[M] MUTACOES POR COPIA -- NAO rodaram (sem `--mutar`).")
        _p("      ⛔ Elas escrevem em `backend/app/` e `backend/scripts/`, e o builder")
        _p("      escreve la em paralelo. Com a arvore parada: `--mutar`. A lista")
        _p("      declarada esta em `MUTACOES`, no topo deste arquivo (%d entradas)."
           % len(MUTACOES))

    _p("\n" + "=" * 78)
    _p("  %d ok · %d falha(s) · %d pulado(s)" % (OK, FAIL, len(PULADOS)))
    if PULADOS:
        _p("  -- pulados: %s" % " · ".join(PULADOS))
    if FAIL:
        _p("\n  ⛔ HA %d VERMELHO -- procure as linhas `[FALHOU]`." % FAIL)
        _p("  🔴 Na arvore limpa esta lista E o GATE ZERO da SPEC-097.1.")
    else:
        _p("\n  VERDE -- o caso se explica sozinho: a espera esta escrita, o agente "
           "responde com ela e o que sobra chega ao humano dizendo que e POS.")
    if verdes_mutacao:
        _p("  ⛔ %d mutacao(oes) NAO ficaram vermelhas: %s -- o arnes nao guarda essa regra."
           % (len(verdes_mutacao), ", ".join(verdes_mutacao)))
    _p("=" * 78)
    return 1 if (FAIL or verdes_mutacao) else 0


def test_o_caso_se_explica_sozinho():
    """🔴 A prova nasceu ANTES do codigo (protocolo §4, opcao B).

    Roda a si mesmo num subprocesso: este guarda troca `sys.modules` e fecha a
    rede, e o processo do pytest carrega o mundo de outros testes junto."""
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=RAIZ,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, (r.stdout[-4000:] + r.stderr[-1500:])


if __name__ == "__main__":
    sys.exit(main())
