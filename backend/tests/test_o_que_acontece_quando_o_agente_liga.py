"""O que acontece — e o que NÃO acontece — quando alguém clica em LIGAR AGENTE.

Por que este arquivo existe
---------------------------
Até 04/08/2026 o produto tinha três travas para a mesma coisa, e nenhuma delas
era um botão:

  · `portal_params.py` cravava `"confirm": False` no dicionário de params. 📊 Uma
    busca no repositório inteiro não achava NENHUM caminho que ligasse
    `confirm=True` — o acionamento de vidros percorria o formulário todo e
    parava no 80% para sempre. Dos 39 jobs de `abrir_atendimento`, **9 morreram
    exatamente ali** ("cheguei na confirmacao (80%) — aprove para enviar"), e a
    aprovação não existia em lugar nenhum.
  · `INSURER_DISPATCH_LIVE` nascia ausente = FECHADO, e sem ela o corredor de
    WhatsApp montava o plano e não enviava nada.
  · `DISPATCH_FINALIZE_MODE` nascia em `test`, e o motor CANCELAVA no passo em
    que a URA ia abrir o serviço.

A decisão do Founder, 04/08/2026, dita duas vezes e nas palavras dele:

    "A questão de trava no final sempre foi por um motivo exclusivo. Eu estava
     fazendo os testes no meu próprio celular. Se não tivesse a trava, seriam
     feitos os acionamentos dos serviços de vidro de verdade."
    "Quero tudo pronto e funcionando, mas o agente de atendimento tem que
     continuar desligado. Só podem funcionar se clicar em LIGAR AGENTE."

📊 Em 04/08/2026, `SELECT agent_role, is_active FROM agents` no projeto
`dcajcvlzcjbmyapmklil` devolve os quatro agentes `attendance` com
`is_active=false`.

A regra que este arquivo protege
--------------------------------
> **Uma coisa só segura tudo: `agents.is_active` do agente de atendimento.
> Mais um freio de emergência por env, solto por padrão.**

Trava sobre trava não protege — esconde. Quem tem duas fechaduras nunca sabe
qual está segurando, e a auditoria de 02/08 já pagou por isso ("uma trava que
depende de outra trava não é trava, é sorte"). O que fica é um interruptor que
uma pessoa clica, e um freio que uma pessoa puxa.

O CONTROLE, que é o que dá direito à conclusão
----------------------------------------------
Um teste que só provasse "com o agente desligado nada acontece" passaria num
sistema **quebrado**, onde nada acontece nunca — que é literalmente o estado de
ontem, com `confirm=False` cravado. Por isso cada bateria aqui exercita os DOIS
lados do mesmo interruptor e exige que eles deem respostas **diferentes**. Se
derem a mesma, o guarda não mede o interruptor: mede a incapacidade de ligá-lo
(CLAUDE.md §9.2).

Rodar: cd backend && python tests/test_o_que_acontece_quando_o_agente_liga.py
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ---------------------------------------------------------------------------
# Carga por CAMINHO. `app/__init__.py` puxa `app.agents.graph` (langgraph), que
# não existe fora do contêiner; `app.services` entra com o caminho REAL porque
# `portal_params` lê de lá o catálogo de perguntas do portal, e falsificá-lo
# esconderia justamente o formato do `params` que este arquivo precisa ver.
# ---------------------------------------------------------------------------
if str(RAIZ_BACKEND) not in sys.path:
    sys.path.insert(0, str(RAIZ_BACKEND))
for _nome in ("app", "app.core", "app.agents", "app.agents.tools"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []
_svc = sys.modules.setdefault("app.services", types.ModuleType("app.services"))
_svc.__path__ = [str(RAIZ_BACKEND / "app" / "services")]


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, RAIZ_BACKEND / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
# O INTERRUPTOR, falsificado — e só ele.
#
# `attendance_agent_active` fala com o banco e é async. Ele é a ÚNICA coisa
# falsificada aqui de propósito: tudo que decide a partir dele é o código real.
# Falsificar a regra em vez do interruptor provaria que a fixture funciona.
# ---------------------------------------------------------------------------
_atlas = sys.modules.setdefault("app.services.atlas", types.ModuleType("app.services.atlas"))
_atlas.__path__ = []
_captura = types.ModuleType("app.services.atlas.attendance_capture")

AGENTE_LIGADO = {"valor": False, "explode": False}


async def _attendance_agent_active(company_id: str) -> bool:
    if AGENTE_LIGADO["explode"]:
        raise RuntimeError("banco fora do ar")
    return bool(AGENTE_LIGADO["valor"])


_captura.attendance_agent_active = _attendance_agent_active
sys.modules["app.services.atlas.attendance_capture"] = _captura

DS = _carregar("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
_carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
PP = _carregar("app.agents.tools.portal_params", "app/agents/tools/portal_params.py")
PT = _carregar("app.agents.tools.portal_tool", "app/agents/tools/portal_tool.py")
IT = _carregar("app.agents.tools.insurer_dispatch_tool", "app/agents/tools/insurer_dispatch_tool.py")

# O poll do `_arun` dorme 5s entre leituras. Aqui o job já nasce terminado.
PT.POLL_EVERY_S = 0


# ---------------------------------------------------------------------------
# O caso real, para o acionamento não morrer por dado faltando e o teste acabar
# medindo outra coisa. 📊 Corretora, placa e pedido são os do job que o banco
# repetiu 30 vezes (Supabase dcajcvlzcjbmyapmklil, 04/08/2026).
# ---------------------------------------------------------------------------
EMPRESA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"
AGENTE = "aee852d3-c52f-4b52-b71a-5078ad8662c2"

PERFIL_ROW = {
    "company_name": "Resulta Seguros", "legal_name": "Resulta Seguros LTDA",
    "primary_contact_name": "Resulta Seguros", "primary_contact_email": "op@resulta.com.br",
    "primary_contact_phone": "4833646664", "cnpj": "00000000000191",
    "acionamento_profile": None,
}

INFOCAP = {
    "ok": True, "status": "found",
    "policy": {"numapo": "312520261149211", "seguradora": "LIBERTY SEGUROS S/A",
               "seguradora_abrev": "LIBE", "active": True},
    "vehicle": {"placa": "QJQ0A91", "chassi": "98867513WJKH74022",
                "veiculo": "COMPASS LIMITED 2.0 4X2 16V AUT. (FLEX)"},
    "client": {"nome": "RAFAEL LACAU DA SILVEIRA", "cpf_cnpj": "03074327936",
               "logradouro": "RUA CAPITAO ROMUALDO DE BARROS", "numero": "705",
               "bairro": "SACO DOS LIMOES", "cidade": "FLORIANOPOLIS",
               "estado": "SC", "cep": "88040-600", "telefone": "48999990000"},
}

# O que o agente já colheu na conversa. Completo de propósito: um pedido
# incompleto para ANTES do interruptor, e aí o teste mediria a checagem de
# dados em vez de medir a trava.
PEDIDO = {
    "cpf_cnpj": "03074327936",
    "data_dano": "05/07/2026",
    "peca": "vidro de porta",
    "como_ocorreu": "encontrou o veiculo danificado",
    "onde_ocorreu": "urbano",
    "descricao": "Encontrei o carro com o vidro da porta do motorista quebrado no estacionamento",
    "especificos": {"pelicula": "nao", "porta_dianteira_ou_traseira": "dianteira",
                    "lado_motorista_ou_carona": "motorista",
                    "onde_realizar_o_servico": "domicilio"},
}


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """O mínimo do cliente Supabase que estas duas ferramentas usam."""

    def __init__(self, banco: "BancoDeMentira", tabela: str):
        self.banco, self.tabela = banco, tabela
        self.filtros: dict = {}
        self.operacao = "select"
        self.linha: dict = {}

    def select(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.operacao, self.linha = "insert", dict(linha)
        return self

    def update(self, patch):
        self.operacao, self.linha = "update", dict(patch)
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def neq(self, *_a):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return self.banco.executar(self)


class BancoDeMentira:
    def __init__(self):
        self.jobs: list[dict] = []

    def table(self, nome):
        return _Consulta(self, nome)

    def executar(self, q: _Consulta) -> _Resposta:
        if q.tabela == "agents":
            if q.filtros.get("is_active") is True and not AGENTE_LIGADO["valor"]:
                return _Resposta([])
            return _Resposta([{"id": AGENTE}])
        if q.tabela == "companies":
            return _Resposta([dict(PERFIL_ROW)])
        if q.tabela == "portal_jobs":
            if q.operacao == "insert":
                linha = {**q.linha, "id": f"job-{len(self.jobs) + 1}"}
                # O índice único parcial, imitado: chave viva não entra duas vezes.
                chave = linha.get("idempotency_key")
                if chave and any(j.get("idempotency_key") == chave
                                 and j.get("status") != "failed" for j in self.jobs):
                    raise RuntimeError("duplicate key value violates unique constraint "
                                       "\"idx_portal_jobs_pedido_vivo\" (23505)")
                self.jobs.append(linha)
                return _Resposta([{"id": linha["id"]}])
            if q.operacao == "update":
                return _Resposta([])
            if "id" in q.filtros:      # o poll do `_arun`
                return _Resposta([{"status": "needs_human", "error": None,
                                   "evidence": {"message": "cheguei na confirmacao (80%)"}}])
            vivos = [j for j in self.jobs
                     if j.get("idempotency_key") == q.filtros.get("idempotency_key")
                     and j.get("status") != "failed"]
            return _Resposta([{**vivos[-1], "status": "needs_human", "evidence": {}}] if vivos else [])
        return _Resposta([])


class PortalDeMentira(PT.PortalActionTool):
    """A ferramenta REAL. Só a InfoCap é substituída — ela é rede, não decisão."""

    async def _fetch_infocap(self, cpf, policy_number):  # noqa: D102
        return INFOCAP


def _acionar_portal(banco: BancoDeMentira) -> dict:
    ferramenta = PortalDeMentira(company_id=EMPRESA, supabase_client=banco)
    return asyncio.run(ferramenta._arun(**dict(PEDIDO), session_id=""))


# ===========================================================================
# 1. A REGRA — pura, e num lugar só
# ===========================================================================

def teste_a_regra_e_uma_so():
    print("\n[1] Duas condições, as duas necessárias — e escritas uma vez")

    checar(DS.acionamento_liberado(False) is False,
           "agente DESLIGADO: acionamento bloqueado")
    checar(DS.acionamento_liberado(True) is True,
           "CONTROLE: agente LIGADO: acionamento liberado",
           "se os dois dessem False, a regra não estaria medindo o interruptor")
    checar(DS.acionamento_liberado(True, freio_armado=True) is False,
           "agente ligado + freio de emergência armado: bloqueado mesmo assim",
           "o freio existe para parar tudo sem esperar um deploy")

    checar(DS.freio_de_emergencia_armado("true") is True,
           "o freio arma com um 'sim' explícito")
    checar(DS.freio_de_emergencia_armado("") is False,
           "e nasce SOLTO — no sentido seguro, que é o do Founder")
    checar(DS.freio_de_emergencia_armado("talvez") is False,
           "um valor escrito errado NÃO arma o freio",
           "freio que se arma por typo faz o produto parar sem ninguém entender "
           "por quê — e não acionar é invisível, ao contrário de acionar")

    # A regra tem de ser UMA. Duas cópias divergem na primeira mudança, e a que
    # ficou para trás continua valendo em silêncio.
    for arquivo in ("app/agents/tools/portal_tool.py",
                    "app/agents/tools/insurer_dispatch_tool.py"):
        fonte = (RAIZ_BACKEND / arquivo).read_text(encoding="utf-8")
        checar("acionamento_liberado" in fonte and "attendance_agent_active" in fonte,
               f"{arquivo.split('/')[-1]} usa a regra compartilhada, não uma cópia")


# ===========================================================================
# 2. O PORTAL — a constante virou decisão
# ===========================================================================

def teste_o_confirm_deixou_de_ser_constante():
    print("\n[2] `confirm` deixou de ser uma constante cravada")

    perfil = {"nome": "Resulta", "email": "op@resulta.com.br",
              "telefone": "4833646664", "cpf_cnpj": "00000000000191"}
    desligado, e1 = PP.build_portal_params(dict(PEDIDO), perfil, INFOCAP)
    ligado, e2 = PP.build_portal_params(dict(PEDIDO), perfil, INFOCAP,
                                        enviar_de_verdade=True)

    checar(e1 is None and e2 is None, "o caso de teste é completo — não para antes",
           f"{e1 or ''} / {e2 or ''}")
    if not (desligado and ligado):
        return
    checar(desligado["confirm"] is False, "sem quem o ligue, `confirm` nasce False")
    checar(ligado["confirm"] is True, "CONTROLE: e o chamador CONSEGUE ligá-lo",
           "era exatamente isto que não existia: 📊 nenhum caminho do repositório "
           "chegava a confirm=True, e 9 dos 39 jobs morreram no 80% por causa disso")
    checar(desligado["confirm"] != ligado["confirm"],
           "as duas chamadas, com a MESMA entrada, dão respostas DIFERENTES",
           "sem isto o teste mediria a fixture, não a trava")

    # E o resto do pedido não pode mudar junto: o interruptor decide o ENVIO,
    # não o conteúdo. Se mudasse, ligar o agente mudaria o que se pede à
    # seguradora — e ninguém saberia o que foi pedido de verdade.
    checar({k: v for k, v in desligado.items() if k != "confirm"}
           == {k: v for k, v in ligado.items() if k != "confirm"},
           "e NADA mais no pedido muda com o interruptor")

    fonte = (RAIZ_BACKEND / "app/agents/tools/portal_params.py").read_text(encoding="utf-8")
    checar('"confirm": False,' not in fonte,
           "a constante cravada não voltou para a fonte",
           "era ela que fazia o acionamento parar a 20% do fim")


# ===========================================================================
# 3. O PORTAL, PELA FERRAMENTA — desligado × ligado, ponta a ponta
# ===========================================================================

def teste_o_portal_pela_ferramenta():
    print("\n[3] Pela ferramenta real: o job que nasce com o agente desligado × ligado")

    AGENTE_LIGADO["valor"] = False
    banco_off = BancoDeMentira()
    _acionar_portal(banco_off)
    AGENTE_LIGADO["valor"] = True
    banco_on = BancoDeMentira()
    _acionar_portal(banco_on)

    checar(len(banco_off.jobs) == 1 and len(banco_on.jobs) == 1,
           "os dois enfileiram um job (o trabalho é preparado dos dois jeitos)",
           f"off={len(banco_off.jobs)} on={len(banco_on.jobs)}")
    if not (banco_off.jobs and banco_on.jobs):
        return
    off, on = banco_off.jobs[0], banco_on.jobs[0]

    checar(off["params"]["confirm"] is False,
           "agente DESLIGADO: o job nasce com confirm=False — para no 80%, como sempre parou")
    checar(on["params"]["confirm"] is True,
           "agente LIGADO: o job nasce com confirm=True — segue até o passo 7, onde nasce o Nº")
    checar(off["params"]["confirm"] != on["params"]["confirm"],
           "CONTROLE: o MESMO pedido produz jobs DIFERENTES conforme o interruptor",
           "se produzisse o mesmo, o botão do Founder não estaria ligado em nada")

    # A idempotência não pode depender do interruptor: se dependesse, ligar o
    # agente criaria uma chave nova para o MESMO pedido, e o guarda que impede o
    # segundo atendimento sumiria justamente no dia em que ele passa a importar.
    checar(bool(off["idempotency_key"]) and off["idempotency_key"] == on["idempotency_key"],
           "e a chave de idempotência é a MESMA nos dois",
           f"{off['idempotency_key']!r} vs {on['idempotency_key']!r}")

    # E a chave continua sabendo separar pedidos de verdade diferentes (CONTROLE
    # da linha acima: uma chave constante também passaria naquela igualdade).
    outro = PP.chave_de_idempotencia(
        {**on["params"], "dano": {**on["params"]["dano"], "peca": "parabrisa"}}, EMPRESA)
    checar(outro and outro != on["idempotency_key"],
           "CONTROLE: outra peça continua sendo outro pedido",
           "chave constante passaria na igualdade acima sem guardar nada")


def teste_o_pedido_continua_nao_abrindo_duas_vezes():
    print("\n[4] Com `confirm` ligado, o guarda de duplicidade continua de pé")

    AGENTE_LIGADO["valor"] = True
    banco = BancoDeMentira()
    primeira = _acionar_portal(banco)
    segunda = _acionar_portal(banco)

    checar(len(banco.jobs) == 1,
           "a segunda chamada do MESMO pedido NÃO cria um segundo job",
           f"{len(banco.jobs)} jobs — o Nº do atendimento nasce no passo 7, antes "
           "do fim do fluxo: repetir cria um SEGUNDO atendimento, e isso não se desfaz")
    checar("ja existe" in segunda["content"].lower()
           or "já existe" in segunda["content"].lower(),
           "e o agente é informado de que o pedido já existe",
           segunda["content"][:120])
    checar(primeira["content"] != segunda["content"],
           "CONTROLE: a primeira e a segunda chamada dão respostas diferentes",
           "se dessem a mesma, o guarda não estaria sendo exercitado")


# ===========================================================================
# 5. O CORREDOR DE WHATSAPP — nada sai sem o interruptor
# ===========================================================================

CASO_AUTO = {
    "subservice": "guincho", "insurer_key": "allianz", "line_kind": "auto",
    "titular_cpf": "52998224725", "titular_nome": "Rafael Lacau",
    "veiculo_placa": "QJQ0A91", "telefone_contato": "48991234567",
    "local_atual": "Rua Capitao Romualdo de Barros, 705, Florianopolis, SC",
    "local_destino": "Oficina Central, Sao Jose, SC", "pessoa_no_local": "Rafael",
    "quando": "agora", "problema_descricao": "o carro nao liga e esta na rua",
    "dados_confirmados": True,
    "session_id": "whatsapp:5548999990000:co:ag",
}

CHAMADAS: list = []


def _instalar_transporte_de_mentira():
    """Fio-terra: se QUALQUER coisa tentar falar com o mundo, fica registrado.

    Nada aqui envia. `start_live_dispatch` devolve `ok` sem chamar o sender —
    o que este teste precisa saber é se o produto CHEGOU a ele, não se o
    WhatsApp funciona (isso já é testado em outros arquivos).
    """
    integ = types.ModuleType("app.services.integration_service")
    integ.get_integration_service = lambda: types.SimpleNamespace(
        get_whatsapp_integration=lambda *a, **k: {"id": "integ-1"})
    sys.modules["app.services.integration_service"] = integ

    wa = types.ModuleType("app.services.whatsapp_service")

    def _send(*a, **k):
        CHAMADAS.append(("send_message", a))
        return True

    wa.get_whatsapp_service = lambda: types.SimpleNamespace(send_message=_send)
    sys.modules["app.services.whatsapp_service"] = wa

    rot = types.ModuleType("app.services.dispatch_router")

    async def _start(**kw):
        CHAMADAS.append(("start_live_dispatch", kw))
        return {"ok": True, "session": {"state": "ura"}}

    async def _enqueue(*a, **k):
        CHAMADAS.append(("enqueue_dispatch", a))
        return 1

    rot.start_live_dispatch = _start
    rot.enqueue_dispatch = _enqueue
    sys.modules["app.services.dispatch_router"] = rot


class CorredorDeMentira(IT.InsurerDispatchTool):
    """A ferramenta REAL. Só o lookup de placa na InfoCap é curto-circuitado —
    ele é rede, e os fatos do caso já estão preenchidos."""

    async def _resolve_vehicle_facts(self, kwargs):  # noqa: D102
        return kwargs


def teste_o_corredor_de_whatsapp_so_fala_com_o_agente_ligado():
    print("\n[5] O corredor de WhatsApp: nada sai com o agente desligado")
    _instalar_transporte_de_mentira()
    os.environ["INSURER_CONTACT_ALLIANZ_ASSISTENCIA"] = "5511999998888"
    ferramenta = CorredorDeMentira(company_id=EMPRESA, supabase_client=BancoDeMentira())

    CHAMADAS.clear()
    AGENTE_LIGADO["valor"] = False
    desligado = asyncio.run(ferramenta._arun(**dict(CASO_AUTO)))
    chamadas_off = list(CHAMADAS)

    CHAMADAS.clear()
    AGENTE_LIGADO["valor"] = True
    ligado = asyncio.run(ferramenta._arun(**dict(CASO_AUTO)))
    chamadas_on = list(CHAMADAS)

    checar(not chamadas_off,
           "agente DESLIGADO: NADA foi chamado — nem envio, nem acionamento",
           f"chamou {[c[0] for c in chamadas_off]}")
    checar(desligado.get("status") == "ready_to_send"
           and "SIMULA" in desligado.get("content", "").upper(),
           "e a resposta é o plano em simulação, exatamente como com o gate fechado",
           str(desligado.get("status")))

    checar(any(c[0] == "start_live_dispatch" for c in chamadas_on),
           "CONTROLE: agente LIGADO: o acionamento REAL é iniciado",
           f"chamou {[c[0] for c in chamadas_on]} — se não chamasse nada nos dois "
           "casos, o caso acima não provaria nada sobre o interruptor")
    checar(ligado.get("status") == "dispatched",
           "e a ferramenta devolve `dispatched`", str(ligado.get("status")))
    checar(desligado.get("status") != ligado.get("status"),
           "os dois lados do interruptor dão respostas DIFERENTES")

    destino = next((kw for nome, kw in chamadas_on if nome == "start_live_dispatch"), {})
    checar(destino.get("insurer_phone") == "5511999998888"
           and destino.get("client_phone") == "5548999990000",
           "e o acionamento vai para a SEGURADORA, com o telefone do segurado do caso",
           str({k: destino.get(k) for k in ("insurer_phone", "client_phone")}))

    # O freio de emergência: uma linha, e o corredor volta a ficar mudo, com o
    # agente LIGADO. É o que existe para o dia em que for preciso parar sem deploy.
    CHAMADAS.clear()
    os.environ[DS.FREIO_DE_EMERGENCIA] = "true"
    try:
        freado = asyncio.run(ferramenta._arun(**dict(CASO_AUTO)))
    finally:
        os.environ.pop(DS.FREIO_DE_EMERGENCIA, None)
    checar(not CHAMADAS and freado.get("status") == "ready_to_send",
           "freio de emergência armado: agente ligado e mesmo assim NADA sai",
           f"{freado.get('status')} / chamou {[c[0] for c in CHAMADAS]}")


def teste_nao_conseguir_confirmar_e_o_mesmo_que_desligado():
    print("\n[6] Fail-closed: não conseguir CONFIRMAR nunca vira permissão")

    AGENTE_LIGADO["valor"], AGENTE_LIGADO["explode"] = True, True
    try:
        banco = BancoDeMentira()
        _acionar_portal(banco)
        checar(banco.jobs and banco.jobs[0]["params"]["confirm"] is False,
               "portal: banco fora do ar na leitura do interruptor → confirm=False",
               "o pior caso do False é um pedido que para no 80%; o do True é um "
               "atendimento aberto de verdade, que não se desfaz")

        CHAMADAS.clear()
        ferramenta = CorredorDeMentira(company_id=EMPRESA, supabase_client=BancoDeMentira())
        r = asyncio.run(ferramenta._arun(**dict(CASO_AUTO)))
        checar(not CHAMADAS and r.get("status") == "ready_to_send",
               "corredor: mesma falha → simulação, nada enviado",
               f"{r.get('status')} / {[c[0] for c in CHAMADAS]}")
    finally:
        AGENTE_LIGADO["explode"] = False


def main() -> int:
    print("=" * 72)
    print("O QUE ACONTECE QUANDO O AGENTE LIGA — E O QUE NAO ACONTECE ANTES")
    print("=" * 72)
    for teste in (teste_a_regra_e_uma_so,
                  teste_o_confirm_deixou_de_ser_constante,
                  teste_o_portal_pela_ferramenta,
                  teste_o_pedido_continua_nao_abrindo_duas_vezes,
                  teste_o_corredor_de_whatsapp_so_fala_com_o_agente_ligado,
                  teste_nao_conseguir_confirmar_e_o_mesmo_que_desligado):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O INTERRUPTOR E UM SO, E ELE LIGA E DESLIGA DE VERDADE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
