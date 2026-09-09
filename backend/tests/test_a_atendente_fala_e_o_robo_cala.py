# -*- coding: utf-8 -*-
"""A atendente falou — e o robô cala NAQUELA conversa. Na de verdade.

O QUE ACONTECEU EM 09/09/2026 (primeiro dia de piloto real, AutoFleet)
=====================================================================
A Regina respondeu os segurados pelo WhatsApp Web e o robô continuou falando por
cima dela. Três causas medidas no banco de produção, e este arquivo guarda as
três:

    C   o WhatsApp Web endereça o chat por `@lid` — um identificador OPACO de
        15 dígitos. `normalize_evolution_inbound` gravava aquilo como
        "telefone", nascia uma conversa-FANTASMA e a pausa caía nela.
        📊 as 5 pausas por intervenção humana de TODA a história do produto
           estão em conversas com `user_phone` de 15 dígitos.

    C'  com o agente DESLIGADO, `observer_tap` consome o evento antes do ramo
        `fromMe` — então nada pausava.
        📊 430 mensagens `fromMe` humanas naquele dia, 11 tentativas de pausa.

    C'' corrida: a resposta já estava no buffer quando ela escreveu.
        📊 2 de 14 respostas indevidas chegaram em ≤ 25 s.

⛔ O QUE ESTE ARQUIVO NÃO FAZ: procurar strings no código-fonte. Cada guarda
chama o MOTOR (`normalize_evolution_inbound`, `_handle_evolution_like_inbound`,
`_pausar_quando_a_atendente_fala`, `process_whatsapp_message_background`,
`pausar_por_intervencao_humana`) sobre o evento REAL, com dublês de banco e
Redis — CLAUDE.md §9.4. Um teste que casasse o regex do arquivo provaria que o
conserto foi escrito, não que ele funciona.

⚠️ Sem rede, sem Redis, sem banco: tudo é dublê em memória.
"""
from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_PROBLEMAS: list = []

# Números de mentira, e é de propósito: nenhum telefone real entra num teste.
EMPRESA = "autofleet-teste"
TELEFONE = "5547999990001"          # o segurado, como o WhatsApp o entrega
LID = "128374651902847"             # 15 dígitos, opaco — NÃO é telefone de ninguém


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


# ===========================================================================
# OS DUBLÊS
# ===========================================================================
class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """Um PostgREST de mentira que filtra, ordena e limita de verdade.

    ⚠️ Filtrar de mentira é pior que não filtrar: um dublê que ignora `.eq()`
    deixaria o guarda da corretora vizinha verde por permissão.
    """

    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros: list = []
        self._insert = None
        self._update = None
        self._limite = None
        self._ordem: list = []
        self._single = False

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros.append(("eq", campo, valor))
        return self

    def neq(self, campo, valor):
        self.filtros.append(("neq", campo, valor))
        return self

    def is_(self, campo, _valor):
        self.filtros.append(("is_null", campo, None))
        return self

    def gte(self, campo, valor):
        self.filtros.append(("gte", campo, valor))
        return self

    def in_(self, campo, valores):
        self.filtros.append(("in", campo, list(valores or [])))
        return self

    def order(self, campo, desc=False, **_k):
        self._ordem.append((campo, bool(desc)))
        return self

    def limit(self, n):
        self._limite = n
        return self

    def range(self, inicio, fim):
        self._limite = fim - inicio + 1
        return self

    def single(self):
        self._single = True
        return self

    def insert(self, linha):
        self._insert = dict(linha)
        return self

    def update(self, campos):
        self._update = dict(campos)
        return self

    @staticmethod
    def _valor(linha, campo):
        if "->>" in campo:
            raiz, chave = campo.split("->>", 1)
            return (linha.get(raiz) or {}).get(chave)
        return linha.get(campo)

    def _casa(self, linha) -> bool:
        for tipo, campo, valor in self.filtros:
            atual = self._valor(linha, campo)
            if tipo == "eq" and str(atual) != str(valor):
                return False
            if tipo == "neq" and str(atual) == str(valor):
                return False
            if tipo == "is_null" and atual is not None:
                return False
            if tipo == "gte" and str(atual or "") < str(valor):
                return False
            if tipo == "in" and str(atual) not in {str(v) for v in valor}:
                return False
        return True

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        if self._insert is not None:
            novo = dict(self._insert)
            novo.setdefault("id", f"{self.tabela}-{len(linhas) + 1}")
            novo.setdefault("created_at", "2026-09-09T12:00:00+00:00")
            linhas.append(novo)
            return _Resposta([novo])
        if self._update is not None:
            self.banco.updates.append((self.tabela, list(self.filtros), dict(self._update)))
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self._update)
            return _Resposta(tocadas)
        achadas = [l for l in linhas if self._casa(l)]
        for campo, desc in reversed(self._ordem):
            achadas = sorted(achadas, key=lambda l: str(self._valor(l, campo) or ""),
                             reverse=desc)
        if self._limite:
            achadas = achadas[: self._limite]
        if self._single:
            return _Resposta(achadas[0] if achadas else {})
        return _Resposta(achadas)


class BancoFalso:
    def __init__(self):
        self.dados: dict = {}
        self.updates: list = []
        self.client = self

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, tabela):
        return self.dados.setdefault(tabela, [])

    def semear(self, tabela, linhas):
        self.dados.setdefault(tabela, []).extend(dict(l) for l in linhas)

    def por_id(self, tabela, ident):
        return next((l for l in self.linhas(tabela) if str(l.get("id")) == str(ident)), None)


class RedisFalso:
    """O Redis do produto, em memória. Guarda a digital da própria voz."""

    def __init__(self):
        self.dados: dict = {}

    # --- síncrono (voz_propria) ---
    def setex(self, chave, _ttl, valor):
        self.dados[chave] = valor

    def getdel(self, chave):
        return self.dados.pop(chave, None)

    # --- assíncrono (contadores) ---
    async def hincrby(self, chave, campo, quantos=1):
        self.dados.setdefault(chave, {})
        self.dados[chave][campo] = self.dados[chave].get(campo, 0) + quantos

    async def expire(self, *_a, **_k):
        return True


class ServicoDeIntegracaoFalso:
    """A forma REAL é uma FÁBRICA (`get_integration_service(client)`) — dublar o
    nome que não existe foi o defeito dos 2.255 ImportError de 06/08/2026."""

    def __init__(self, integracao=None):
        self.integracao = integracao or {}

    def get_or_create_user(self, phone, company_id, name=None):
        return f"user:{company_id}:{phone}"

    def get_integration_by_id(self, _ident):
        return self.integracao

    def get_integration_by_phone(self, _phone):
        return self.integracao


class EnvioFalso:
    """`whatsapp_service` — grava o que TERIA sido enviado, e não envia nada."""

    def __init__(self):
        self.enviados: list = []

    def send_message(self, to_number=None, text=None, integration=None, *a, **k):
        self.enviados.append({"para": to_number, "texto": text})
        return True


# ===========================================================================
# O CARREGADOR — o motor de verdade, com o mundo dublado à volta dele
# ===========================================================================
_MODULO = {}


def motor():
    """Importa `app.api.webhook` DE VERDADE e troca só as bordas de I/O."""
    if _MODULO:
        return _MODULO["w"]

    os.environ.setdefault("OPENAI_API_KEY", "test-key")

    import app.core.database as _database
    import app.core.redis as _redis
    import app.services.integration_service as _integration
    import app.api.webhook as w

    banco = BancoFalso()
    redis_falso = RedisFalso()

    _database.get_supabase_client = lambda: banco
    _redis.get_redis_client = lambda: redis_falso

    async def _async_redis():
        return redis_falso

    _redis.get_async_redis_client = _async_redis
    _integration.get_integration_service = lambda *_a, **_k: ServicoDeIntegracaoFalso()

    w.supabase = banco

    # Os vizinhos que este guarda não está medindo — desligados para não
    # tocarem rede. Cada um deles tem teste próprio.
    import app.services.atlas.attendance_capture as _captura
    import app.services.claims_shadow as _sombra
    import app.services.dispatch_router as _dispatch

    async def _sim(*_a, **_k):
        return True

    async def _nao(*_a, **_k):
        return False

    async def _nada(*_a, **_k):
        return None

    _dispatch.note_manual_outbound = _nada
    _dispatch.try_route_insurer_inbound = _nao
    _sombra.registrar_gesto = _nao
    _sombra.abrir_sombra = _nao
    _sombra.ficha_da_conversa = _nada
    _captura.capture_channel_message = _nao
    _captura.attendance_agent_active = _sim   # trocado por teste

    _MODULO.update({"w": w, "banco": banco, "redis": redis_falso,
                    "captura": _captura})
    return w


def banco() -> BancoFalso:
    motor()
    return _MODULO["banco"]


def redis_falso() -> RedisFalso:
    motor()
    return _MODULO["redis"]


def agente_ligado(ligado: bool) -> None:
    async def _resposta(*_a, **_k):
        return ligado

    motor()
    _MODULO["captura"].attendance_agent_active = _resposta


def zerar_banco() -> BancoFalso:
    b = banco()
    b.dados.clear()
    b.updates.clear()
    redis_falso().dados.clear()
    return b


def semear_as_duas_conversas(b: BancoFalso) -> None:
    """A conversa REAL do segurado e a FANTASMA que o LID criou.

    As duas existem no banco de produção hoje, lado a lado, com as mesmas
    mensagens espelhadas. É a forma exata do defeito.
    """
    b.semear("conversations", [
        {"id": "real", "company_id": EMPRESA, "channel": "whatsapp",
         "user_id": f"user:{EMPRESA}:{TELEFONE}", "user_phone": TELEFONE,
         "agent_id": None, "status": "open", "claimed_by": None,
         "resolvido_em": None, "session_id": f"whatsapp:{TELEFONE}:{EMPRESA}:default"},
        {"id": "fantasma", "company_id": EMPRESA, "channel": "whatsapp",
         "user_id": f"user:{EMPRESA}:{LID}", "user_phone": LID,
         "agent_id": None, "status": "open", "claimed_by": None,
         "resolvido_em": None, "session_id": f"whatsapp:{LID}:{EMPRESA}:default"},
    ])


def integracao() -> dict:
    return {"id": "int-1", "company_id": EMPRESA, "provider": "evolution-go",
            "identifier": "554800000000", "purpose": "attendance"}


def evento_go(*, texto: str, por_lid: bool, from_me: bool = True,
              ident: str = "WAMSG-1") -> dict:
    """O evento como o Evolution GO o entrega — whatsmeow cru.

    Por `@lid`, o telefone de verdade viaja em `ChatAlt`; o conversor
    (`evolution_go_events.py:123`) o preserva como `key.remoteJidAlt`.
    """
    info = {
        "Chat": f"{LID}@lid" if por_lid else f"{TELEFONE}@s.whatsapp.net",
        "Sender": f"{LID}@lid" if por_lid else f"{TELEFONE}@s.whatsapp.net",
        "IsFromMe": from_me,
        "ID": ident,
        "PushName": "Segurado",
        "Timestamp": 1789000000,
    }
    if por_lid:
        info["ChatAlt"] = f"{TELEFONE}@s.whatsapp.net"
    return {"instanceId": "inst-1", "Info": info,
            "Message": {"conversation": texto}}


def entregar(corpo: dict) -> None:
    """O pipeline compartilhado das duas rotas Evolution, chamado de verdade."""
    from fastapi import BackgroundTasks

    from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

    w = motor()
    envelope = go_event_to_v2_envelope(corpo)
    asyncio.run(w._handle_evolution_like_inbound(
        integracao(), envelope, BackgroundTasks(), "evolution-go"))


# ===========================================================================
# (a) O `@lid` PAUSA A CONVERSA REAL — não a fantasma
# ===========================================================================
def teste_a_atendente_no_whatsapp_web_pausa_a_conversa_certa():
    print("\n[a] fromMe por @lid pausa a conversa REAL do segurado")
    w = motor()
    agente_ligado(True)
    b = zerar_banco()
    semear_as_duas_conversas(b)

    from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

    envelope = go_event_to_v2_envelope(evento_go(texto="Já estou vendo, Regina.",
                                                 por_lid=True))
    normalizado = w.normalize_evolution_inbound(envelope)
    checar(normalizado.get("phone") == TELEFONE,
           "o normalizador devolve o TELEFONE, nunca o LID",
           f"devolveu {len(str(normalizado.get('phone') or ''))} dígitos")

    entregar(evento_go(texto="Já estou vendo, Regina.", por_lid=True))
    checar(b.por_id("conversations", "real")["status"] == "HUMAN_REQUESTED",
           "a conversa REAL do segurado ficou com a atendente")
    checar(b.por_id("conversations", "fantasma")["status"] == "open",
           "a conversa-FANTASMA do LID NÃO foi tocada",
           "era nela que as 5 pausas da história caíram")

    # CONTROLE — o MESMO evento endereçado por linha de telefone.
    #
    # 🔴 É ele que dá direito à conclusão (CLAUDE.md §9.2): se o `@lid` acertar
    # e o `@s.whatsapp.net` acertar TAMBÉM, então o conserto foi a resolução da
    # identidade e não um efeito colateral do formato do evento.
    b2 = zerar_banco()
    semear_as_duas_conversas(b2)
    envelope_linha = go_event_to_v2_envelope(
        evento_go(texto="Já estou vendo, Regina.", por_lid=False, ident="WAMSG-2"))
    normalizado_linha = w.normalize_evolution_inbound(envelope_linha)
    checar(normalizado_linha.get("phone") == normalizado.get("phone"),
           "CONTROLE — os DOIS formatos dão o MESMO telefone",
           "é o mesmo chat, tem de ser a mesma conversa")
    entregar(evento_go(texto="Já estou vendo, Regina.", por_lid=False, ident="WAMSG-2"))
    checar(b2.por_id("conversations", "real")["status"] == "HUMAN_REQUESTED",
           "CONTROLE — por @s.whatsapp.net também pausa a real")


# ===========================================================================
# (b) COM O AGENTE DESLIGADO A PAUSA ACONTECE MESMO ASSIM
# ===========================================================================
def teste_com_o_agente_desligado_a_pausa_acontece():
    print("\n[b] agente DESLIGADO (o tap consome o evento) — e a conversa pausa")
    w = motor()
    agente_ligado(False)
    b = zerar_banco()
    semear_as_duas_conversas(b)

    # É este o caminho de produção com o agente desligado: `observer_tap`
    # devolve `{"status": "observed"}` e o pipeline nunca roda.
    asyncio.run(w._pausar_quando_a_atendente_fala(
        integracao(), evento_go(texto="Bom dia, já vou verificar.", por_lid=True)))
    checar(b.por_id("conversations", "real")["status"] == "HUMAN_REQUESTED",
           "a conversa real pausou com o agente DESLIGADO",
           "📊 430 fromMe humanas em 09/09 e 11 tentativas de pausa")
    checar(b.por_id("conversations", "fantasma")["status"] == "open",
           "e continua não sendo a fantasma")

    # CONTROLE — com o agente LIGADO, quem pausa é o ramo `fromMe` do pipeline.
    # Os dois caminhos são mutuamente exclusivos, e os dois têm de pausar.
    agente_ligado(True)
    b2 = zerar_banco()
    semear_as_duas_conversas(b2)
    entregar(evento_go(texto="Bom dia, já vou verificar.", por_lid=True,
                       ident="WAMSG-3"))
    checar(b2.por_id("conversations", "real")["status"] == "HUMAN_REQUESTED",
           "CONTROLE — com o agente LIGADO também pausa")


# ===========================================================================
# (c) A VOZ DO PRÓPRIO ROBÔ NÃO PAUSA NADA
# ===========================================================================
def teste_a_voz_do_robo_nao_pausa():
    print("\n[c] o eco da própria voz do agente NÃO pausa")
    w = motor()
    agente_ligado(True)
    b = zerar_banco()
    semear_as_duas_conversas(b)

    from app.services.whatsapp.voz_propria import registrar_nossa_fala

    texto = "Recebi sua mensagem, já estou verificando com a seguradora."
    registrar_nossa_fala(EMPRESA, TELEFONE, texto)   # o produto anota antes de falar
    entregar(evento_go(texto=texto, por_lid=True, ident="WAMSG-4"))
    checar(b.por_id("conversations", "real")["status"] == "open",
           "o robô ouvindo a si mesmo não se pausa",
           "sem isto ele emudeceria na primeira resposta que desse")


# ===========================================================================
# (d) `#nota` ANOTA, NÃO ASSUME
# ===========================================================================
def teste_a_nota_nao_pausa_mas_o_texto_no_meio_pausa():
    print("\n[d] `#nota` no começo não pausa; `#nota` no meio é intervenção")
    w = motor()
    agente_ligado(True)
    b = zerar_banco()
    semear_as_duas_conversas(b)
    entregar(evento_go(texto="#nota o robô perguntou a placa duas vezes",
                       por_lid=True, ident="WAMSG-5"))
    checar(b.por_id("conversations", "real")["status"] == "open",
           "anotar NÃO é assumir — a IA continua atendendo")

    # CONTROLE — a exceção é ESTREITA. Se ela fosse larga, bastaria a palavra
    # aparecer em qualquer lugar para o robô continuar falando por cima.
    b2 = zerar_banco()
    semear_as_duas_conversas(b2)
    entregar(evento_go(texto="o robô errou #nota vou assumir daqui",
                       por_lid=True, ident="WAMSG-6"))
    checar(b2.por_id("conversations", "real")["status"] == "HUMAN_REQUESTED",
           "CONTROLE — `#nota` no MEIO do texto é intervenção e pausa")

    # E com o agente desligado a mesma regra vale — o segundo caminho não pode
    # ter uma terceira opinião sobre o que é uma nota.
    agente_ligado(False)
    b3 = zerar_banco()
    semear_as_duas_conversas(b3)
    asyncio.run(w._pausar_quando_a_atendente_fala(
        integracao(), evento_go(texto="#nota ligar depois", por_lid=True)))
    checar(b3.por_id("conversations", "real")["status"] == "open",
           "CONTROLE — com o agente desligado a nota também não pausa")


# ===========================================================================
# (e) O GUARDA DE FORMA — nenhum LID sai daqui vestido de telefone
# ===========================================================================
def teste_nenhum_lid_passa_por_telefone():
    print("\n[e] guarda de forma: 13+ dígitos sem `55` nunca é telefone")
    from app.services.whatsapp.identidade_do_evento import telefone_do_evento

    casos = [
        ({"remoteJid": f"{LID}@lid"}, "", "@lid sem alternativo não vira telefone"),
        ({"remoteJid": f"{LID}@lid", "remoteJidAlt": f"{LID}@lid"}, "",
         "alternativo que também é @lid não serve"),
        ({"remoteJid": f"{LID}@lid", "remoteJidAlt": f"{TELEFONE}@s.whatsapp.net"},
         TELEFONE, "@lid COM alternativo devolve o telefone"),
        ({"remoteJid": f"{LID}@lid", "remoteJidPn": f"{TELEFONE}@s.whatsapp.net"},
         TELEFONE, "`remoteJidPn` é a outra grafia da mesma coisa"),
        ({"remoteJid": f"{TELEFONE}@s.whatsapp.net"}, TELEFONE, "linha comum"),
        ({"remoteJid": f"{TELEFONE}:12@s.whatsapp.net"}, TELEFONE,
         "sufixo de dispositivo (`:12`) é descartado"),
        ({"remoteJid": "120363000000000000@g.us"}, "", "grupo não é pessoa"),
        ({"remoteJid": "status@broadcast"}, "", "status não é pessoa"),
        ({"remoteJid": f"{LID}@s.whatsapp.net"}, "",
         "🔴 nem disfarçado de linha: 15 dígitos sem `55` é recusado"),
    ]
    for chave, esperado, o_que in casos:
        checar(telefone_do_evento(chave) == esperado, o_que)

    # 🔴 O GUARDA QUE NÃO DEPENDE DA LISTA ACIMA: qualquer coisa que saia daqui
    # com 13 dígitos ou mais TEM de começar com 55. É a forma do defeito, não um
    # caso particular dele.
    saidas = [telefone_do_evento(c) for c, _e, _o in casos]
    checar(all(not s or len(s) < 13 or s.startswith("55") for s in saidas),
           "nenhuma saída tem 13+ dígitos sem o DDI 55")


# ===========================================================================
# (f) A CORRIDA — a conversa é assumida DURANTE o turno do robô
# ===========================================================================
def _rodar_o_turno(*, assume_no_meio: bool) -> list:
    """Roda o pipeline de resposta de verdade e devolve o que foi ENVIADO."""
    w = motor()
    agente_ligado(True)
    b = zerar_banco()
    semear_as_duas_conversas(b)

    envio = EnvioFalso()
    w.whatsapp_service = envio
    w.integration_service = ServicoDeIntegracaoFalso(integracao())

    import app.services.billing_gate as _porteira
    import app.services.billing_replies as _cobranca
    import app.services.platform_outbound as _plataforma

    _porteira.pode_consumir = lambda *_a, **_k: (True, "ok")

    async def _sem_nota(*_a, **_k):
        return None

    _cobranca.contexto_de_cobranca = _sem_nota
    _cobranca.telefones_da_equipe_de_cobranca = _sem_nota
    _plataforma.context_note_for = _sem_nota

    class _LangChainFalso:
        def __init__(self, *_a, **_k):
            pass

        async def process_message(self, *_a, **_k):
            # 🔴 É AQUI QUE A CORRIDA ACONTECE. Enquanto o modelo escreve — 8 a
            # 25 segundos, medidos —, a atendente responde pelo celular e a
            # conversa muda de dono. O portão da ENTRADA já tinha perguntado, e
            # a resposta dele era verdadeira quando ele perguntou.
            if assume_no_meio:
                await _pausar_engine(b)
            return "Claro! Vou verificar sua apólice agora mesmo.", {}

    w.LangChainService = _LangChainFalso

    # A conversa que o pipeline vai achar é a REAL (mesmo `session_id`).
    w.get_or_create_conversation = _conversa_fixa

    asyncio.run(w.process_whatsapp_message_background({
        "connectedPhone": "554800000000", "phone": TELEFONE, "isGroup": False,
        "fromMe": False, "text": {"message": "Oi, preciso de um guincho"},
        "messageId": "WAMSG-IN-1", "senderName": "Segurado",
        "_integration_id": "int-1",
    }))
    return envio.enviados


async def _conversa_fixa(**_k) -> str:
    return "real"


async def _pausar_engine(b: BancoFalso) -> None:
    """A atendente assume — pelo MOTOR real, não escrevendo no dublê na mão."""
    from app.services.atlas.espelho_chat import pausar_por_intervencao_humana

    await pausar_por_intervencao_humana(
        company_id=EMPRESA, conversation_id="real", db=b)


def teste_a_conversa_assumida_no_meio_do_turno_nao_recebe_resposta():
    print("\n[f] assumida DURANTE o turno: o robô não envia (a corrida de ≤ 25 s)")
    enviados = _rodar_o_turno(assume_no_meio=True)
    checar(not enviados,
           "NADA foi enviado ao segurado",
           "📊 2 de 14 respostas indevidas chegaram em 25 s ou menos")

    # CONTROLE — sem ninguém assumir, o robô responde normalmente. Sem esta
    # linha, um pipeline quebrado passaria como "conserto da corrida".
    enviados_livre = _rodar_o_turno(assume_no_meio=False)
    checar(len(enviados_livre) == 1,
           "CONTROLE — conversa livre: o segurado É respondido",
           f"{len(enviados_livre)} envio(s)")


# ===========================================================================
# A pausa por ID, e o incidente quando ela não casa linha nenhuma
# ===========================================================================
def teste_a_pausa_por_id_e_o_incidente_do_zero():
    print("\n[g] pausar pelo ID da conversa, e o zero-linhas vira incidente")
    b = zerar_banco()
    semear_as_duas_conversas(b)

    from app.services.atlas.espelho_chat import pausar_por_intervencao_humana

    ok = asyncio.run(pausar_por_intervencao_humana(
        company_id=EMPRESA, conversation_id="real", db=b))
    checar(ok is True and b.por_id("conversations", "real")["status"] == "HUMAN_REQUESTED",
           "o `conversation_id` pausa a linha exata")

    # CONTROLE — corretora errada não pausa, nem com o id certo (CLAUDE.md §7).
    b2 = zerar_banco()
    semear_as_duas_conversas(b2)
    outra = asyncio.run(pausar_por_intervencao_humana(
        company_id="resulta-teste", conversation_id="real", db=b2))
    checar(outra is False and b2.por_id("conversations", "real")["status"] == "open",
           "CONTROLE — o id de outra corretora não pausa nada")

    # E o zero-linhas é contado: era exatamente o que ninguém via em 09/09.
    r = redis_falso()
    contagem = (r.dados.get("espelho:chat") or {}).get("pausa:zero_linhas", 0)
    checar(contagem >= 1,
           "a pausa que não casou linha nenhuma virou contagem no /health",
           f"pausa:zero_linhas = {contagem}")


# ===========================================================================
# O plano da migração das fantasmas — funções puras, sem banco
# ===========================================================================
def teste_o_plano_da_migracao_reconhece_a_fantasma():
    print("\n[h] o script de migração sabe o que é fantasma e o que é telefone")
    import importlib.util

    caminho = os.path.join(RAIZ, "scripts", "migrar_conversas_fantasma_lid.py")
    spec = importlib.util.spec_from_file_location("_migrar_fantasma", caminho)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    checar(mig.e_fantasma(LID) is True, "o LID de 15 dígitos é fantasma")
    checar(mig.e_fantasma(TELEFONE) is False,
           "CONTROLE — o celular BR de 13 dígitos NÃO é fantasma",
           "o critério `>= 13` do plano condenaria todo celular do país")
    checar(mig.e_fantasma("554899887766") is False,
           "CONTROLE — 12 dígitos (sem o nono) também não é fantasma")

    pares = mig.parear_pelo_wa_id(
        [{"id": "fantasma"}],
        [{"conversation_id": "fantasma", "payload": {"wa_message_id": "WA-1"}},
         {"conversation_id": "real", "payload": {"wa_message_id": "WA-1"}}])
    checar(pares == {"fantasma": "real"},
           "a fantasma casa com a real pelo `wa_message_id` espelhado")

    ambiguo = mig.parear_pelo_wa_id(
        [{"id": "fantasma"}],
        [{"conversation_id": "fantasma", "payload": {"wa_message_id": "WA-1"}},
         {"conversation_id": "real", "payload": {"wa_message_id": "WA-1"}},
         {"conversation_id": "outra", "payload": {"wa_message_id": "WA-1"}}])
    checar(ambiguo == {},
           "CONTROLE — duas candidatas NÃO são gravadas",
           "um par errado mostra a uma pessoa o atendimento de outra")

    checar(mig.MOTIVO not in mig.MOTIVOS_ACEITOS_PELO_BANCO,
           "o script SABE que o CHECK do banco ainda recusa `fantasma_lid`",
           "e por isso o --vivo fica bloqueado até a migration do valor")


def main() -> int:
    print("=" * 72)
    print("A ATENDENTE FALA E O ROBÔ CALA — NA CONVERSA DE VERDADE")
    print("=" * 72)
    teste_a_atendente_no_whatsapp_web_pausa_a_conversa_certa()
    teste_com_o_agente_desligado_a_pausa_acontece()
    teste_a_voz_do_robo_nao_pausa()
    teste_a_nota_nao_pausa_mas_o_texto_no_meio_pausa()
    teste_nenhum_lid_passa_por_telefone()
    teste_a_conversa_assumida_no_meio_do_turno_nao_recebe_resposta()
    teste_a_pausa_por_id_e_o_incidente_do_zero()
    teste_o_plano_da_migracao_reconhece_a_fantasma()

    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — a pausa cai na conversa certa, com o agente ligado ou não.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
