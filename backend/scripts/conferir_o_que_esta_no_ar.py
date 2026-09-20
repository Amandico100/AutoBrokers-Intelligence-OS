# -*- coding: utf-8 -*-
"""Responde, em duas linhas, a pergunta que a P-189 deixou sem resposta:
**o processo no ar tem o código que está no meu repositório?**

    python backend/scripts/conferir_o_que_esta_no_ar.py

📊 Por que isto foi preciso: em 16/08/2026 disparei três deploys, os três
responderam HTTP 200 `Deploying...`, e não havia como saber o que tinha subido —
`build_sha` chega `"unknown"` e `git_commit` chega `"nao-injetado"`, porque o
EasyPanel exporta a árvore sem o `.git`. O único marcador restante era
`build_time`, que diz QUANDO a imagem foi construída, não O QUE tem dentro dela.

Compara a digital do código no repositório com a que cada `/health` devolve.
Não pede credencial, não escreve nada e não toca em portal de seguradora.

Saída: `0` só quando TODOS os serviços conferidos batem.

----------------------------------------------------------------------------
EXTRA-001.7 — O CHECKLIST DE LIGAR
----------------------------------------------------------------------------

    cd backend && python scripts/conferir_o_que_esta_no_ar.py --ligar

Responde, em uma linha por trava e por corretora, a única pergunta da véspera
do piloto: **dá para ligar o agente hoje?**

🔴 ⛔ **Nunca fail-open.** Uma trava que não PÔDE ser conferida conta como
fechada. 📊 O motivo foi medido em 20/09/2026, neste mesmo produto: o
`/health` publica `corretoras_ligadas_sem_destino_de_suporte: []` e essa lista
vazia parecia dizer "está tudo certo" — mas ela só conta corretoras com o
agente **já ligado**, e nenhuma está. As DUAS corretoras do piloto estavam sem
destino de suporte naquele instante. Um checklist que lesse aquele `[]` daria
"PODE LIGAR" no exato dia em que o handoff não teria para onde ir.

⛔ **Nada envia, nada escreve, nada liga.** Só `GET /health` e `SELECT`.
⛔ **Nenhum telefone, CPF, apólice ou segredo sai daqui** (`CLAUDE.md` §13.3):
só presença, ausência e CONTAGEM.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from portal_worker.impressao import impressao_do_diretorio  # noqa: E402

try:  # o terminal do Founder é Windows; as frases têm acento.
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass

BASE = "https://autobrokers-intelligence-os"
SERVICOS = (
    # (nome, url do /health, pasta que a imagem carrega, onde a digital aparece)
    ("portal-worker", f"{BASE}-portal-worker.golhpm.easypanel.host/health",
     "backend/portal_worker", ()),
    ("smith-api", f"{BASE}-autobrokers-smith-api.golhpm.easypanel.host/health",
     "backend/app", ("codigo",)),
)


def _cavar(d: dict, caminho: tuple) -> dict:
    for parte in caminho:
        d = (d or {}).get(parte) or {}
    return d or {}


def conferir(nome: str, url: str, pasta: str, caminho: tuple) -> bool:
    local, quantos = impressao_do_diretorio(RAIZ / pasta)
    print(f"\n{nome}")
    print(f"  repositorio : {local}  ({quantos} arquivos .py em {pasta})")

    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            saude = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  no ar       : NAO RESPONDEU ({type(e).__name__})")
        return False

    bloco = _cavar(saude, caminho) if caminho else saude
    remoto = str(bloco.get("code_fingerprint") or "ausente")
    extra = saude.get("build_time") or saude.get("timestamp") or ""
    print(f"  no ar       : {remoto}  ({bloco.get('code_files')} arquivos)  {extra}")

    if remoto == "ausente":
        print("  VEREDITO    : o /health no ar ainda NAO expoe a digital -- ou")
        print("                seja, a versao no ar e ANTERIOR a P-189.")
        return False
    if remoto == local:
        print("  VEREDITO    : BATE.")
        return True
    print("  VEREDITO    : DIVERGE. O deploy nao trocou o codigo, por mais verde")
    print("                que o painel esteja -- ou ha trabalho nao commitado.")
    return False


# ===========================================================================
# EXTRA-001.7 — O CHECKLIST DE LIGAR
#
# O FIO:  /health + linhas do banco  ->  coletar  ->  avaliar (PURA)
#         ->  travas  ->  texto impresso + código de saída
# ===========================================================================

CORRETORAS_DO_PILOTO = ("Resulta Seguros", "AutoFleet")
SAUDE_DA_API = SERVICOS[1][1]

ABERTA = "aberta"
FECHADA = "fechada"
NAO_CONFERIDA = "nao_conferida"

#: 🔴 A REGRA QUE IMPEDE O CHECKLIST DE MENTIR. Uma trava que não pôde ser
#: lida NÃO é uma trava aberta. ⚠️ Foi assim que o `[]` de
#: `corretoras_ligadas_sem_destino_de_suporte` quase virou um "pode ligar" com
#: as duas corretoras sem destino (ver o docstring do módulo).
REPROVAM = (FECHADA, NAO_CONFERIDA)

_MARCA = {ABERTA: "[ok]   ", FECHADA: "[TRAVA]", NAO_CONFERIDA: "[?]    "}


def _trava(nome: str, estado: str, frase: str, corretora: str = "",
           detalhes: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"nome": nome, "estado": estado, "frase": frase,
            "corretora": corretora, "detalhes": detalhes or []}


# ---------------------------------------------------------------------------
# ② AVALIAR — função PURA: fatos entram, travas saem. Nenhuma rede, nenhum
#    banco, nenhum relógio. É ela que o par de guardas cobre trava a trava.
# ---------------------------------------------------------------------------
def avaliar(fatos: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Os fatos coletados viram a lista de travas que o Founder lê.

    ⛔ As frases são o produto e ficam AQUI, ao lado da regra que as escolhe —
    o mesmo desenho de `porteiro_do_agente.py:43`. Nome de tabela, coluna ou
    variável de ambiente só aparece ENTRE PARÊNTESES no fim, como pista para
    quem vai consertar; nunca no meio da frase.
    """
    travas: List[Dict[str, Any]] = []
    saude = fatos.get("health")
    # 🔴 UM `/health` QUE NÃO É UM OBJETO NÃO PODE DERRUBAR O CHECKLIST.
    # 📊 Achado [B-?] do red team: um 500 com HTML, uma lista, ou `codigo`
    # vindo como string faziam `avaliar` levantar `AttributeError` — e um
    # checklist que EXPLODE não diz nem "pode" nem "não pode". A frase tem de
    # ser legível, e o veredito tem de ser NÃO PODE.
    ilegivel = saude is not None and not isinstance(saude, dict)

    ruins, ausentes = _infra(saude if isinstance(saude, dict) else {})

    # ---- ① o que está no ar é o que está no repositório --------------------
    if saude is None:
        travas.append(_trava(
            "no_ar", FECHADA,
            "O sistema não respondeu. Enquanto ele não responder, não há como "
            "ligar nada (GET /health)."))
    elif ilegivel:
        travas.append(_trava(
            "no_ar", FECHADA,
            "O sistema respondeu, mas não de um jeito que eu consiga ler. "
            "Pode ser uma página de erro no lugar da resposta (GET /health)."))
    elif str(saude.get("status") or "").lower() != "healthy" or ruins:
        travas.append(_trava(
            "no_ar", FECHADA,
            "O sistema respondeu, mas alguma peça dele está com problema: "
            + ", ".join(ruins or ["o próprio sistema se declarou fora do ar"])
            + " (/health)."))
    elif ausentes:
        # ⛔ NUNCA FAIL-OPEN. 📊 Achado do red team: um `/health` sem as chaves
        # `redis`/`qdrant`/`storage` passava como ABERTO — "não veio" virava
        # "está bem". Peça que não se anuncia é peça que não foi conferida.
        travas.append(_trava(
            "no_ar", NAO_CONFERIDA,
            "O sistema respondeu, mas não contou nada sobre: "
            + ", ".join(ausentes) + " (/health)."))
    elif fatos.get("digital_bate") is None:
        travas.append(_trava(
            "no_ar", NAO_CONFERIDA,
            "Não deu para saber se o sistema no ar tem o código do seu "
            "repositório (code_fingerprint)."))
    elif not fatos.get("digital_bate"):
        travas.append(_trava(
            "no_ar", FECHADA,
            "O sistema no ar está rodando um código diferente do seu "
            "repositório. Clique Implantar antes de ligar (code_fingerprint)."))
    else:
        travas.append(_trava(
            "no_ar", ABERTA,
            "O sistema está no ar e rodando o código do seu repositório."))

    # ---- ⑤ quem escapa do silêncio da janela --------------------------------
    travas.append(_avaliar_excecoes(saude))

    # ---- ⑤b quem consegue escrever PARA o produto ---------------------------
    # 🔴 Era uma promessa que o código não cumpria: o comentário dizia "e quem
    # pode escrever para o produto" e `allowlist_ativa` não era lido em lugar
    # nenhum. Agora é uma trava com nome próprio, e ela depende do MODO.
    travas.append(_avaliar_allowlist(saude, str(fatos.get("modo") or MODO_PILOTO)))

    # ---- ⑦ o ambiente não está travando o acionamento ----------------------
    travas.append(_avaliar_flags(saude))

    # ---- por corretora: ② destino · ③ canal · ④ telefones · ⑥ agente ------
    for c in fatos.get("corretoras") or []:
        travas.extend(_avaliar_corretora(c))
    return travas


#: 📊 O valor SAUDÁVEL dos bancos, lido na captura real de 20/09/2026
#: (`main.py:1007`/`:1017` escrevem exatamente isto). 🔴 A comparação é por
#: IGUALDADE com ele, nunca por procurar a palavra "error": achado do red team
#: — `database_async: "unavailable: timeout"` não tem "error" nem "disconnect"
#: dentro, e passava como saudável. Nomear o que é BOM fecha a porta; tentar
#: listar tudo que é ruim deixa sempre uma frase de fora.
BANCO_SAUDAVEL = "connected"


def _infra(saude: Dict[str, Any]) -> tuple:
    """`(peças doentes, peças que não se anunciaram)` — nesta ordem.

    ⛔ As duas listas são separadas de propósito: doente FECHA a trava, e
    ausente deixa a trava NÃO CONFERIDA. Misturá-las seria dizer "está tudo
    bem" para um `/health` que simplesmente não falou (fail-open), ou acusar
    de defeito um backend que só é mais velho.
    """
    ruins, ausentes = [], []
    for chave in ("database_sync", "database_async", "redis", "qdrant", "storage"):
        if chave not in saude or saude.get(chave) is None:
            ausentes.append(chave)
            continue
        valor = saude.get(chave)
        if isinstance(valor, dict):
            if valor.get("conectado") is not True:
                ruins.append(chave)
        elif str(valor).strip().lower() != BANCO_SAUDAVEL:
            ruins.append(chave)
    return ruins, ausentes


# ⛔ `_componentes_ruins` foi ABSORVIDA por `_infra` (CLAUDE.md §5): duas
# funções decidindo "esta peça está boa?" dariam vereditos diferentes no dia em
# que só uma fosse consertada. A lição das DUAS FORMAS (string × dicionário)
# mora agora no docstring de `_infra` e em `BANCO_SAUDAVEL`. 📊 Medido na
# captura de 20/09/2026: os bancos chegam como STRING (`"connected"`) e Redis,
# Qdrant e MinIO como DICIONÁRIO (`{"conectado": true, …}`). ⚠️ E o `status` de
# topo não cobre nada disso: `main.py:1048` só escreve `"unhealthy"` quando o
# banco SÍNCRONO cai.


def _codigo(saude: Any) -> Dict[str, Any]:
    """Os sinais do `/health`, e `{}` quando não há sinal LEGÍVEL.

    ⛔ `(saude or {}).get("codigo") or {}` não bastava: `codigo` vindo como
    STRING é truthy, e a próxima linha explodia num `AttributeError` dentro do
    `in`. Um checklist que explode não diz nem "pode" nem "não pode".
    """
    if not isinstance(saude, dict):
        return {}
    bloco = saude.get("codigo")
    return bloco if isinstance(bloco, dict) else {}


#: 🔴 OS DOIS MODOS, e a decisão escrita ao lado deles.
#:
#: `ATTENDANT_INBOUND_ALLOWLIST` decide QUEM consegue escrever para o produto
#: (`whatsapp/channel_security.py:61`): configurada, o agente só responde aos
#: números listados e **descarta o resto em silêncio**. A mesma configuração é
#: o oposto de certo nos dois momentos do piloto:
#:
#:   canário  o Founder quer falar SÓ com o número de teste. Allowlist vazia
#:            aqui é o defeito: o produto responderia a segurado de verdade
#:            numa rodada que era para ser de laboratório.
#:   piloto   os segurados precisam chegar. Allowlist ativa aqui é o defeito:
#:            📊 o piloto de 3 dias mediria SILÊNCIO e ninguém saberia por quê
#:            — "ninguém escreveu" é indistinguível de um dia fraco.
#:
#: ⚠️ Por isso o modo é uma ESCOLHA declarada no comando, nunca um palpite do
#: script: os dois estados são legítimos, e só quem roda sabe qual é a rodada.
MODO_PILOTO = "piloto"
MODO_CANARIO = "canario"


def _avaliar_allowlist(saude: Optional[Dict[str, Any]], modo: str) -> Dict[str, Any]:
    """Quem consegue escrever para o produto — e isso depende do MODO."""
    codigo = _codigo(saude)
    ativa = codigo.get("allowlist_ativa")
    tamanho = codigo.get("allowlist_tamanho")
    if "allowlist_ativa" not in codigo or ativa is None:
        # ⛔ `None` é o caminho de ERRO de `main.py:754`. Fail-open aqui seria
        # liberar o piloto sem saber se o produto está escutando alguém.
        return _trava("allowlist", NAO_CONFERIDA,
                      "Não deu para saber quem consegue falar com o agente "
                      "(ATTENDANT_INBOUND_ALLOWLIST).")
    quantos = int(tamanho) if isinstance(tamanho, int) else None

    if modo == MODO_CANARIO:
        if not ativa:
            return _trava("allowlist", FECHADA,
                          "Você pediu uma rodada de teste, mas qualquer pessoa "
                          "consegue falar com o agente: um segurado de verdade "
                          "seria atendido no meio do teste. Deixe só os números "
                          "de teste na lista (ATTENDANT_INBOUND_ALLOWLIST).")
        return _trava("allowlist", ABERTA,
                      f"Rodada de teste: só {quantos if quantos is not None else 'os'} "
                      "número(s) da lista falam com o agente "
                      "(ATTENDANT_INBOUND_ALLOWLIST).")

    if ativa:
        return _trava("allowlist", FECHADA,
                      f"Só {quantos if quantos is not None else 'alguns'} "
                      "número(s) conseguem falar com o agente; todos os outros "
                      "segurados seriam ignorados em silêncio. Esvazie a lista "
                      "antes do piloto real (ATTENDANT_INBOUND_ALLOWLIST).")
    return _trava("allowlist", ABERTA,
                  "Qualquer segurado consegue falar com o agente — ninguém é "
                  "descartado na entrada.")


def _avaliar_excecoes(saude: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """A lista de quem NÃO é calado pela janela de silêncio.

    🔴 É a trava mais perigosa do piloto: um número de segurado nessa lista faz
    o agente falar por cima da atendente (`o_fim_do_atendimento.py:1440`).
    """
    codigo = _codigo(saude)
    if "excecoes_da_janela_tamanho" not in codigo:
        return _trava(
            "excecoes", NAO_CONFERIDA,
            "O sistema no ar ainda não informa quem escapa do silêncio. "
            "Clique Implantar e rode de novo (JANELA_SILENCIO_EXCECOES).")
    total = codigo.get("excecoes_da_janela_tamanho")
    fora = codigo.get("excecoes_da_janela_fora_do_teste")
    if total is None or fora is None:
        return _trava(
            "excecoes", NAO_CONFERIDA,
            "O sistema no ar não conseguiu conferir quem escapa do silêncio "
            "(JANELA_SILENCIO_EXCECOES).")
    if int(fora) > 0:
        return _trava(
            "excecoes", FECHADA,
            f"{int(fora)} número(s) que não são de teste escapam do silêncio: "
            "o agente pode responder por cima de quem está atendendo. Tire "
            "esses números da lista (JANELA_SILENCIO_EXCECOES).")
    quantos = int(total)
    if quantos == 0:
        return _trava("excecoes", ABERTA,
                      "Ninguém escapa do silêncio — nenhuma exceção cadastrada.")
    return _trava("excecoes", ABERTA,
                  f"As {quantos} exceção(ões) do silêncio são todas números de "
                  "teste declarados (JANELA_SILENCIO_EXCECOES).")


def _avaliar_flags(saude: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Os interruptores do ambiente que impedem um acionamento de sair.

    ⚠️ 📊 MEDIDO EM 20/09/2026, e diverge do mapa que recebi:
    `alarme_de_canal_mudo` NÃO é um interruptor de ambiente. Ele é um
    autoteste do código no ar (`main.py:857` roda `decidir_alarme_de_entrega`
    com um par de casos). Ele não trava acionamento nenhum — mas se vier
    `false`, o produto no ar não sabe avisar que o WhatsApp ficou verde e
    mudo, e 📊 foi assim que 44 h (AutoFleet) e 68 h (Resulta) passaram sem
    ninguém notar. Fica na trava, com a frase do que ele realmente significa.
    """
    codigo = _codigo(saude)
    if not codigo:
        return _trava("flags", NAO_CONFERIDA,
                      "Não deu para conferir os interruptores do ambiente "
                      "(/health codigo).")

    problemas: List[str] = []
    naoconf: List[str] = []

    def _olhar(chave: str, ok, frase_ruim: str, frase_nc: str) -> None:
        if chave not in codigo or codigo.get(chave) is None:
            naoconf.append(frase_nc)
        elif not ok(codigo.get(chave)):
            problemas.append(frase_ruim)

    _olhar("acionamento_env_aberta", lambda v: v is True,
           "Os acionamentos estão desligados no ambiente (INSURER_DISPATCH_LIVE).",
           "Não deu para saber se os acionamentos estão ligados no ambiente "
           "(INSURER_DISPATCH_LIVE).")
    _olhar("freio_de_emergencia_armado", lambda v: v is False,
           "O freio de emergência está armado: nenhum acionamento sai enquanto "
           "ele estiver puxado.",
           "Não deu para saber se o freio de emergência está armado.")
    _olhar("finalize_modo", lambda v: str(v).strip().lower() == "live",
           "Os chamados terminam em modo de teste e não abrem de verdade "
           "(DISPATCH_FINALIZE_MODE).",
           "Não deu para saber se os chamados abrem de verdade "
           "(DISPATCH_FINALIZE_MODE).")
    _olhar("finalize_abre_de_verdade", lambda v: bool(v),
           "Nenhuma seguradora está autorizada a abrir chamado de verdade.",
           "Não deu para saber quais seguradoras abrem chamado de verdade.")
    _olhar("alarme_de_canal_mudo", lambda v: v is True,
           "Se o WhatsApp ficar conectado e mudo, ninguém será avisado.",
           "Não deu para saber se o aviso de WhatsApp mudo funciona.")

    if problemas:
        return _trava("flags", FECHADA,
                      "O ambiente está travando o trabalho:", detalhes=problemas + naoconf)
    if naoconf:
        return _trava("flags", NAO_CONFERIDA,
                      "Nem todos os interruptores do ambiente puderam ser lidos:",
                      detalhes=naoconf)
    return _trava("flags", ABERTA,
                  "Nada no ambiente está travando o trabalho, e o aviso de "
                  "WhatsApp mudo está de pé.")


def _avaliar_corretora(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    nome = str(c.get("nome") or "?")
    travas: List[Dict[str, Any]] = []

    # ---- ② destino de alerta ativo ----------------------------------------
    if c.get("destino") is None:
        travas.append(_trava("destino", NAO_CONFERIDA,
                             "Não deu para conferir para onde o agente pede "
                             "ajuda (human_support_destinations).", nome))
    elif c.get("destino_recusado"):
        travas.append(_trava("destino", FECHADA,
                             "O lugar para onde o agente pede ajuda pertence a "
                             "outra corretora. Cadastre um grupo só desta, em "
                             "Personalização → Suporte humano.", nome))
    elif not c.get("destino"):
        travas.append(_trava("destino", FECHADA,
                             "Não há para onde o agente pedir ajuda: o pedido "
                             "sairia e ninguém receberia. Cadastre o grupo da "
                             "equipe em Personalização → Suporte humano "
                             "(human_support_destinations).", nome))
    else:
        travas.append(_trava("destino", ABERTA,
                             "Quando o agente precisar de uma pessoa, a equipe "
                             "vai receber o pedido.", nome))

    # ---- ③ canal WhatsApp conectado ---------------------------------------
    if c.get("canal") is None:
        travas.append(_trava("canal", NAO_CONFERIDA,
                             "Não deu para conferir se o WhatsApp da corretora "
                             "está conectado (integrations).", nome))
    elif not c.get("canal"):
        travas.append(_trava("canal", FECHADA,
                             "O WhatsApp da corretora não está conectado. "
                             "Conecte o número em Conectores → WhatsApp "
                             "(integrations.channel_status).", nome))
    else:
        travas.append(_trava("canal", ABERTA,
                             "O WhatsApp da corretora está conectado.", nome))

    # ---- ④ telefones da casa ----------------------------------------------
    quantos = c.get("telefones_da_casa")
    if quantos is None:
        travas.append(_trava("casa", NAO_CONFERIDA,
                             "Não deu para conferir os telefones da equipe "
                             "(company_internal_numbers).", nome))
    elif int(quantos) <= 0:
        travas.append(_trava("casa", FECHADA,
                             "Nenhum telefone da equipe está cadastrado: o "
                             "agente vai tratar a própria equipe como se fosse "
                             "cliente. Cadastre os números da casa "
                             "(company_internal_numbers / users_v2.phone).", nome))
    else:
        travas.append(_trava("casa", ABERTA,
                             f"A equipe tem telefone cadastrado ({int(quantos)} "
                             "forma(s) de número reconhecida(s)): o agente não "
                             "vai responder à própria equipe como cliente.", nome))

    # ---- ⑥ agente de atendimento cadastrado -------------------------------
    #
    # 🔴 A DECISÃO, ESCRITA AO LADO DO CÓDIGO: **agente desligado NÃO reprova.**
    # Este checklist roda ANTES de ligar — desligado é o estado esperado, e
    # reprovar por ele seria pedir que o Founder ligue o agente para descobrir
    # se pode ligar o agente. O que reprova é NÃO EXISTIR agente de atendimento
    # para a corretora: aí não há o que ligar. 📊 Medido em 20/09/2026: as duas
    # corretoras do piloto têm 1 agente de atendimento cadastrado e 0 ligados.
    if c.get("agente_existe") is None:
        travas.append(_trava("agente", NAO_CONFERIDA,
                             "Não deu para conferir se a corretora tem agente "
                             "de atendimento (agents).", nome))
    elif not c.get("agente_existe"):
        travas.append(_trava("agente", FECHADA,
                             "A corretora não tem agente de atendimento "
                             "cadastrado: não há o que ligar "
                             "(agents.agent_role='attendance').", nome))
    else:
        estado = "ligado" if c.get("agente_ligado") else "desligado — é assim que ele deve estar até você decidir ligar"
        travas.append(_trava("agente", ABERTA,
                             f"A corretora tem agente de atendimento ({estado}).",
                             nome))
    return travas


# ---------------------------------------------------------------------------
# ① COLETAR — a única parte que toca rede e banco. Só GET e SELECT.
# ---------------------------------------------------------------------------
class MotoresReais:
    """A borda. ⛔ Nenhuma regra aqui: só leitura, e só pelos MOTORES que o
    produto já usa (`CLAUDE.md` §5 e §9.4). Uma consulta "parecida" escrita
    aqui diria uma coisa e o produto faria outra."""

    def ler_health(self) -> Optional[Dict[str, Any]]:
        try:
            with urllib.request.urlopen(SAUDE_DA_API, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return None

    def _db(self):
        from app.core.database import get_supabase_client

        return get_supabase_client()

    def empresas(self, nomes) -> List[Dict[str, str]]:
        linhas = (self._db().client.table("companies")
                  .select("id, company_name")
                  .in_("company_name", list(nomes)).execute().data or [])
        return [{"id": str(l["id"]), "nome": str(l.get("company_name"))}
                for l in linhas if l.get("id")]

    async def destino(self, company_id: str) -> Dict[str, Any]:
        from app.services.dispatch_router import resolver_destino_de_suporte

        return await resolver_destino_de_suporte(company_id)

    def canal(self, company_id: str) -> List[Dict[str, Any]]:
        # ⚠️ `provider` vem junto: sem ele, uma integração ativa que NÃO é de
        # WhatsApp responderia pela trava do WhatsApp (achado do red team).
        return (self._db().client.table("integrations")
                .select("channel_status, is_active, provider, purpose")
                .eq("company_id", company_id)      # 🔴 CLAUDE.md §7
                .eq("is_active", True).limit(20).execute().data or [])

    async def telefones_da_casa(self, company_id: str) -> int:
        from app.services.o_grupo_so_o_que_importa import numeros_da_casa

        # ⛔ A CONTAGEM, nunca os dígitos (`CLAUDE.md` §13.3). E são VARIANTES
        # (com/sem o nono dígito), por isso a frase diz "formas de número".
        return len(await numeros_da_casa(self._db(), company_id))

    def agente(self, company_id: str) -> List[Dict[str, Any]]:
        # A MESMA consulta do portão canônico `attendance_agent_active`
        # (`atlas/attendance_capture.py:296`) — sem o `.limit(1)`, porque aqui
        # a pergunta é "existe?" e não "está ligado?".
        return (self._db().client.table("agents").select("id, is_active")
                .eq("company_id", company_id)      # 🔴 CLAUDE.md §7
                .eq("agent_role", "attendance").limit(5).execute().data or [])


#: 📊 Os provedores de WhatsApp vivos em `integrations`, medidos em 20/09/2026
#: sobre 200 linhas: `evolution-go` (5), `evolution` (1), `z-api` (1) — e
#: nenhum outro tipo de integração existe hoje na tabela. Os três nomes vêm do
#: código que PAREIA o canal (`whatsapp/pairing_orchestrator.py:621`,
#: `whatsapp/grupos.py:127`).
PROVEDORES_DE_WHATSAPP = {"evolution-go", "evolution", "z-api"}


async def coletar(nomes, motores=None, digital=None, modo=MODO_PILOTO) -> Dict[str, Any]:
    """Lê o mundo e devolve FATOS. Nunca levanta: o que não pôde ser lido vira
    `None`, e `None` reprova em `avaliar`."""
    from app.api.porteiro_do_agente import CANAL_FORA_DO_AR

    m = motores or MotoresReais()
    fatos: Dict[str, Any] = {"health": None, "digital_bate": None,
                             "corretoras": [], "modo": modo, "desconhecidas": []}

    fatos["health"] = m.ler_health()
    if isinstance(fatos["health"], dict):
        remoto = str(_codigo(fatos["health"]).get("code_fingerprint") or "")
        local = digital if digital is not None else impressao_do_diretorio(
            RAIZ / "backend/app")[0]
        fatos["digital_bate"] = (remoto == local) if remoto and remoto not in (
            "ausente", "indisponivel") else None

    # ⚠️ DUAS COISAS DIFERENTES, e o código de saída as separa: a corretora que
    # o banco respondeu NÃO TER (nome errado no comando → saída 2, erro de uso)
    # e a corretora que não pôde ser lida (banco fora → saída 1, trava). Juntá-
    # las mandaria o Founder caçar um nome errado durante uma indisponibilidade.
    leu = True
    try:
        empresas = m.empresas(nomes)
    except Exception:  # noqa: BLE001
        empresas, leu = [], False
    achadas = {e["nome"] for e in empresas}
    for nome in nomes:
        if nome not in achadas:
            fatos["corretoras"].append({"nome": nome})
            if leu:
                fatos["desconhecidas"].append(nome)

    for e in empresas:
        c: Dict[str, Any] = {"nome": e["nome"]}
        try:
            alvo = await m.destino(e["id"])
            c["destino_recusado"] = bool(alvo.get("recusa"))
            c["destino"] = bool(str(alvo.get("destino") or "").strip())
        except Exception:  # noqa: BLE001
            c["destino"] = None
        try:
            linhas = m.canal(e["id"])
            # 🔴 SÓ AS LINHAS DE WHATSAPP. 📊 Achado do red team: o porteiro
            # (`porteiro_do_agente.py:98`) aceita QUALQUER integração ativa, e
            # uma linha ativa de outro tipo com `channel_status` nulo passaria
            # pela assimetria do NULL e diria "WhatsApp conectado" com o
            # WhatsApp `disconnected`. A assimetria do NULL continua — mas só
            # vale para uma linha que É de WhatsApp.
            wa = [l for l in linhas
                  if str((l or {}).get("provider") or "").strip().lower()
                  in PROVEDORES_DE_WHATSAPP]
            estados = {str((l or {}).get("channel_status") or "").strip().lower()
                       for l in wa}
            # ⚠️ A MESMA lista do porteiro, importada e não copiada. O vazio
            # conta como VIVO de propósito: `channel_status` nulo é canal
            # antigo, não canal caído (`porteiro_do_agente.py:110`).
            if not wa and linhas:
                # Há canal ativo, mas de um provedor que eu não reconheço como
                # WhatsApp. ⛔ Não afirmo nem que está, nem que não está.
                c["canal"] = None
            else:
                c["canal"] = bool(wa) and bool(
                    [x for x in estados if x not in CANAL_FORA_DO_AR])
        except Exception:  # noqa: BLE001
            c["canal"] = None
        try:
            c["telefones_da_casa"] = await m.telefones_da_casa(e["id"])
        except Exception:  # noqa: BLE001
            c["telefones_da_casa"] = None
        try:
            linhas = m.agente(e["id"])
            c["agente_existe"] = bool(linhas)
            c["agente_ligado"] = any(l.get("is_active") is True for l in linhas)
        except Exception:  # noqa: BLE001
            c["agente_existe"] = None
        fatos["corretoras"].append(c)
    return fatos


# ---------------------------------------------------------------------------
# ③ O TEXTO E O VEREDITO
# ---------------------------------------------------------------------------
def imprimir(travas: List[Dict[str, Any]], escrever: Callable[[str], None] = print) -> bool:
    grupos: List[str] = []
    for t in travas:
        if t["corretora"] not in grupos:
            grupos.append(t["corretora"])
    for g in grupos:
        escrever("")
        escrever(g or "O SISTEMA")
        for t in [x for x in travas if x["corretora"] == g]:
            escrever(f"  {_MARCA[t['estado']]} {t['frase']}")
            for d in t["detalhes"]:
                escrever(f"            - {d}")

    fechadas = [t for t in travas if t["estado"] == FECHADA]
    naoconf = [t for t in travas if t["estado"] == NAO_CONFERIDA]
    # 🔴 A regra do fail-closed mora numa constante só (REPROVAM), para que
    # ninguém a reescreva de um jeito que deixe passar o "não conferida".
    pode = not [t for t in travas if t["estado"] in REPROVAM]
    escrever("")
    escrever("=" * 70)
    if pode:
        escrever("PODE LIGAR")
    else:
        resumo = []
        if fechadas:
            resumo.append(f"{len(fechadas)} trava(s) fechada(s)")
        if naoconf:
            resumo.append(f"{len(naoconf)} que nao pude conferir "
                          "(e o que nao se confere conta como fechada)")
        escrever("NAO PODE LIGAR — " + " e ".join(resumo))
    escrever("=" * 70)
    return pode


def checklist(nomes, motores=None, digital=None, modo=MODO_PILOTO,
              escrever: Callable[[str], None] = print) -> int:
    """O FIO inteiro, em uma linha: mundo -> fatos -> travas -> texto -> saída.

    `0` pode ligar · `1` alguma trava fecha (ou não pôde ser conferida) ·
    `2` o comando pediu uma corretora que não existe — erro de uso, não trava.
    """
    fatos = asyncio.run(coletar(nomes, motores=motores, digital=digital, modo=modo))
    pode = imprimir(avaliar(fatos), escrever)
    if fatos.get("desconhecidas"):
        escrever("")
        escrever("Não encontrei esta(s) corretora(s) pelo nome: "
                 + ", ".join(fatos["desconhecidas"])
                 + ". Confira o nome e rode de novo.")
        return 2
    return 0 if pode else 1


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("servico", nargs="?", default="")
    p.add_argument("--ligar", action="store_true",
                   help="dá para ligar o agente hoje?")
    p.add_argument("--corretora", action="append", default=None)
    p.add_argument("--modo", choices=(MODO_PILOTO, MODO_CANARIO),
                   default=MODO_PILOTO,
                   help="piloto: os segurados precisam chegar (padrão) · "
                        "canario: só os números de teste devem chegar")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    if args.ligar:
        nomes = tuple(args.corretora or CORRETORAS_DO_PILOTO)
        print(f"CHECKLIST DE LIGAR ({args.modo}) — nada aqui envia, liga ou escreve.")
        return checklist(nomes, modo=args.modo)

    # ⛔ O modo antigo (P-189) continua EXATAMENTE como era.
    alvo = args.servico
    servicos = [s for s in SERVICOS if not alvo or s[0] == alvo]
    if not servicos:
        print(f"servico desconhecido: {alvo}")
        return 2
    todos = [conferir(*s) for s in servicos]
    print()
    print("=" * 60)
    print("TODOS BATEM" if all(todos) else "HA DIVERGENCIA")
    print("=" * 60)
    return 0 if all(todos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
