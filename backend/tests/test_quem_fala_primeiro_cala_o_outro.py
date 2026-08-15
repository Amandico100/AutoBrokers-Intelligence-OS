"""Quem responde primeiro cala o outro — naquela conversa, e só nela.

A REGRA, nas palavras do Founder (06/08/2026)
=============================================
    "Se a Regina notar algo errado, eu gostaria que ela pudesse intervir na
     conversa e assumir. Se ela enviar uma mensagem no WhatsApp dela, o agente
     de atendimento para e a Regina assume. Isso é para não ficarem duas pessoas
     respondendo."

    "Ele precisa parar a conversar com aquele cliente naquele número, mas ele
     deve continuar ligado e fazendo o trabalho dele nas outras conversas. Então
     ele não desliga totalmente. Ele apenas para aquela conversa e se aparecer
     outra, ele fala na outra. Ele só para totalmente se o agente de atendimento
     for desligado no botão do dashboard."

O DEFEITO QUE ESTAVA LÁ
=======================
O sistema já capturava a resposta manual da atendente (`webhook.py`, ramo
`from_me`) — mas dentro de `if not await attendance_agent_active(company)`, ou
seja: **só quando o agente já estava desligado.** Que é exatamente o caso em que
não há nada para pausar.

Com o agente ligado — o único momento em que a intervenção humana importa — a
mensagem da atendente não era vista, não entrava no chat e não calava ninguém.
Duas pessoas responderiam o mesmo cliente.

O QUE ESTE ARQUIVO GUARDA
=========================
Que a intervenção é vista SEMPRE, que ela pausa a conversa certa, e — o guarda
que mais importa — que ela **não** pausa as outras.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _fonte(caminho_relativo: str) -> str:
    with open(os.path.join(RAIZ, caminho_relativo), encoding="utf-8") as arquivo:
        return arquivo.read()


def _comandos(caminho_relativo: str) -> str:
    return "\n".join(l for l in _fonte(caminho_relativo).split("\n")
                     if not l.lstrip().startswith("#"))


# O mesmo banco de mentira do teste irmão. Duplicado de propósito: cada teste
# roda sozinho, e um helper compartilhado entre arquivos de teste vira uma
# dependência que quebra os dois de uma vez.
class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros: list = []
        self._insert = None
        self._update = None
        self._limite = None
        self._ordem: list = []

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
        """🔴 NÃO EXISTIA, e a ausência era um falso verde esperando a vez.

        📊 13/08/2026: o guarda de eco passou a filtrar `created_at >= agora-300s`
        em vez de carregar as 40 últimas mensagens. Este dublê não conhecia
        `gte`, então a chamada estourava `AttributeError`, o `try/except` do
        espelho engolia, e TRÊS controles de eco ficaram vermelhos de uma vez.

        Deu certo por acaso: o dublê falhou barulhento. Se ele tivesse um `gte`
        que ignorasse o filtro, os mesmos três testes teriam ficado VERDES
        enquanto o guarda de eco lia a conversa inteira em produção.
        """
        self.filtros.append(("gte", campo, valor))
        return self

    def lt(self, campo, valor):
        self.filtros.append(("lt", campo, valor))
        return self

    def order(self, campo, desc=False, **_k):
        """ORDENA DE VERDADE — era `return self`, um no-op.

        O arquivo irmão já pagou por isto: um dublê que ignora `order` devolve
        as N linhas PRIMEIRAS inseridas onde o Postgres devolveria as N ÚLTIMAS.
        O guarda de eco lê `order("created_at", desc=True).limit(20)`; com o
        no-op, ele leria as 20 mensagens mais ANTIGAS da conversa — o oposto
        exato do que precisa — e o teste ficaria verde por inversão.

        Lista e não par: `order()` pode ser chamado duas vezes (desempate).
        """
        self._ordem.append((campo, bool(desc)))
        return self

    def limit(self, n):
        self._limite = n
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
            if tipo == "lt" and not (str(atual or "") < str(valor)):
                return False
        return True

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        if self._insert is not None:
            _conferir_indice_unico(self.tabela, self._insert, linhas)
            novo = dict(self._insert)
            novo.setdefault("id", f"{self.tabela}-{len(linhas) + 1}")
            linhas.append(novo)
            return _Resposta([novo])
        if self._update is not None:
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self._update)
            return _Resposta(tocadas)
        achadas = [l for l in linhas if self._casa(l)]
        # ORDEM antes de LIMITE, como no Postgres.
        for campo, desc in reversed(self._ordem):
            achadas = sorted(achadas, key=lambda l: str(self._valor(l, campo) or ""),
                             reverse=desc)
        if self._limite:
            achadas = achadas[: self._limite]
        return _Resposta(achadas)


class ChaveDuplicada(Exception):
    """O banco real diria `23505 duplicate key value violates unique constraint`."""


def _conferir_indice_unico(tabela: str, linha: dict, existentes: list) -> None:
    """`messages_espelho_sem_duplicata_uidx` — migration 20260806_02.

    🔴 PASSOU A SER OBRIGATÓRIO NESTE ARQUIVO EM 13/08/2026.

    Antes, a dedup era feita em Python sobre as 40 últimas mensagens, e este
    dublê podia ignorar o índice sem consequência. Agora o espelho INSERE e
    deixa o banco responder: sem o índice aqui, o dublê aceitaria a mensagem
    reentregue duas vezes e o teste da reentrega ficaria verde por permissão —
    o pior tipo de verde, porque o guarda existiria e não guardaria nada.
    """
    if tabela != "messages":
        return
    wa = (linha.get("payload") or {}).get("wa_message_id")
    if not wa:
        return
    conversa = linha.get("conversation_id")
    for outra in existentes:
        if (outra.get("conversation_id") == conversa
                and (outra.get("payload") or {}).get("wa_message_id") == wa):
            raise ChaveDuplicada(
                'duplicate key value violates unique constraint '
                '"messages_espelho_sem_duplicata_uidx" (23505)')


class BancoFalso:
    def __init__(self):
        self.dados: dict = {}
        self.client = self

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, tabela):
        return self.dados.setdefault(tabela, [])

    def semear(self, tabela, linhas):
        self.dados.setdefault(tabela, []).extend(dict(l) for l in linhas)

    def por_id(self, tabela, ident):
        return next((l for l in self.linhas(tabela) if l.get("id") == ident), None)


def _carregar_espelho():
    nome = "_teste_espelho_chat_pausa"
    if nome in sys.modules:
        return sys.modules[nome]
    if "app.services.integration_service" not in sys.modules:
        falso = types.ModuleType("app.services.integration_service")

        class _Servico:
            @staticmethod
            def get_or_create_user(phone: str, company_id: str, name=None) -> str:
                return f"user:{company_id}:{phone}"

        # A forma REAL do módulo é uma FÁBRICA. 📊 Dublar `integration_service`
        # — um nome que não existe lá — deixou este arquivo verde enquanto
        # produção acumulava 2.255 ImportError e o chat ficava vazio.
        falso.get_integration_service = lambda *_a, **_k: _Servico()
        sys.modules["app.services.integration_service"] = falso

    # 🔴 O catálogo de canais entra REAL — 15/08/2026.
    #
    # `espelho_chat` passou a importar `canais_observados` NO TOPO, de propósito:
    # a versão anterior tinha o import dentro da função, embrulhado num
    # `except Exception: pass`, e isso é o defeito de 2.255 ImportError narrado
    # logo acima — a guarda vira no-op silencioso e o /health diz que está tudo
    # bem. Como o import agora é de topo, este carregador precisa registrar o
    # módulo, senão ele quebra alto. **Quebrar alto é o comportamento certo.**
    if "app.services.atlas.canais_observados" not in sys.modules:
        for _pkg in ("app", "app.services", "app.services.atlas"):
            if _pkg not in sys.modules:
                sys.modules[_pkg] = types.ModuleType(_pkg)
        _cam = os.path.join(RAIZ, "backend", "app", "services", "atlas",
                            "canais_observados.py")
        _sp = importlib.util.spec_from_file_location(
            "app.services.atlas.canais_observados", _cam)
        _mod = importlib.util.module_from_spec(_sp)
        sys.modules["app.services.atlas.canais_observados"] = _mod
        _sp.loader.exec_module(_mod)

    caminho = os.path.join(RAIZ, "backend", "app", "services", "atlas", "espelho_chat.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
def teste_a_resposta_pelo_celular_aparece_no_chat():
    print("\n[1] A atendente responde pelo celular e a mensagem entra no chat")
    cmd = _comandos("backend/app/api/webhook.py")

    checar("espelhar_no_chat(" in cmd, "o ramo fromMe espelha no chat")
    trecho = cmd.split('skip_reason") == "from_me"')[1][:3000]
    checar("espelhar_no_chat(" in trecho,
           "e o espelho acontece dentro do ramo fromMe")

    # CONTROLE — o espelho e a pausa vêm ANTES do teste de agente ligado.
    #
    # O bloco antigo rodava dentro de `if not attendance_agent_active(...)`, que
    # é exatamente o caso em que a informação não serve para nada: sem agente,
    # não há o que pausar. Com agente LIGADO é que a intervenção humana precisa
    # ser vista e obedecida.
    i_espelho = trecho.find("espelhar_no_chat(")
    i_gate = trecho.find("attendance_agent_active")
    checar(0 <= i_espelho < i_gate,
           "CONTROLE — o espelho vem ANTES do teste de agente ligado",
           "depois dele, a intervenção só valeria quando não há o que pausar")


def teste_a_pausa_e_por_conversa_e_nao_global():
    print("\n[2] Pausar é POR CONVERSA — o agente segue nas outras")
    EC = _carregar_espelho()
    banco = BancoFalso()
    banco.semear("conversations", [
        {"id": "c1", "company_id": "autofleet", "user_phone": "554799956540",
         "channel": "whatsapp", "status": "open", "claimed_by": None},
        {"id": "c2", "company_id": "autofleet", "user_phone": "554788887777",
         "channel": "whatsapp", "status": "open", "claimed_by": None},
    ])

    ok = asyncio.run(EC.pausar_por_intervencao_humana(
        company_id="autofleet", counterparty="554799956540", db=banco))
    checar(ok is True, "pausou a conversa em que a pessoa falou")
    checar(banco.por_id("conversations", "c1")["status"] == "HUMAN_REQUESTED",
           "aquela conversa fica com a pessoa")

    # CONTROLE — o guarda que MAIS importa. Sem esta linha, uma intervenção numa
    # conversa calaria o agente em todas, e a regra 4 do Founder seria violada:
    # "ele apenas para aquela conversa e se aparecer outra, ele fala na outra".
    checar(banco.por_id("conversations", "c2")["status"] == "open",
           "CONTROLE — a OUTRA conversa segue com o agente",
           "o agente só para de vez pelo botão Ligar/Desligar agente")

    # CONTROLE — corretora diferente não é tocada (CLAUDE.md §7).
    banco.semear("conversations", [
        {"id": "c3", "company_id": "resulta", "user_phone": "554799956540",
         "channel": "whatsapp", "status": "open", "claimed_by": None}])
    asyncio.run(EC.pausar_por_intervencao_humana(
        company_id="autofleet", counterparty="554799956540", db=banco))
    checar(banco.por_id("conversations", "c3")["status"] == "open",
           "CONTROLE — mesmo telefone noutra corretora não é pausado")

    # CONTROLE — conversa encerrada não ressuscita.
    banco.semear("conversations", [
        {"id": "c4", "company_id": "autofleet", "user_phone": "554711112222",
         "channel": "whatsapp", "status": "closed", "claimed_by": None}])
    asyncio.run(EC.pausar_por_intervencao_humana(
        company_id="autofleet", counterparty="554711112222", db=banco))
    checar(banco.por_id("conversations", "c4")["status"] == "closed",
           "CONTROLE — conversa encerrada continua encerrada")


def teste_a_pausa_nunca_desliga_o_agente():
    print("\n[3] Pausar uma conversa não desliga o agente da corretora")
    cmd = _comandos("backend/app/services/atlas/espelho_chat.py")

    checar('table("agents")' not in cmd,
           "a ponte não escreve na tabela de agentes")

    # O guarda precisa ser PRECISO, não genérico.
    #
    # A primeira versão proibia a string `"is_active"` em qualquer lugar do
    # arquivo — e reprovou quando `sincronizar_chats` passou a LER as
    # integrações ativas com `.eq("is_active", True)`. Aquilo é filtro de
    # leitura sobre `integrations`, não escrita sobre `agents`; um guarda que
    # reprova o certo é um guarda que alguém vai desligar.
    #
    # O que não pode é `is_active` aparecer como VALOR gravado — a forma de
    # dicionário, que é como um insert/update escreve.
    for forma in ('"is_active": True', '"is_active": False', "'is_active':"):
        checar(forma not in cmd,
               f"CONTROLE — a ponte nunca GRAVA is_active ({forma})",
               "só o botão Ligar/Desligar agente mexe nisso")
    checar('.eq("company_id"' in cmd and '.eq("user_phone"' in cmd,
           "o UPDATE é por corretora E por telefone — nunca a corretora inteira")


def teste_o_agente_respeita_a_pausa():
    print("\n[4] E o agente OBEDECE a pausa")
    # O gate já existia antes deste trabalho. Este guarda impede que ele suma
    # numa refatoração — sem ele, a pausa viraria um campo que ninguém lê.
    for arquivo in ("backend/app/api/chat.py", "backend/app/api/webhook.py"):
        checar("HUMAN_REQUESTED" in _comandos(arquivo),
               f"{os.path.basename(arquivo)} consulta o estado antes de o agente falar")


def teste_a_resposta_do_dashboard_nao_volta_em_dobro():
    print("\n[5] Resposta enviada do dashboard não aparece duas vezes")
    from datetime import datetime, timedelta, timezone

    EC = _carregar_espelho()
    banco = BancoFalso()
    agora = datetime.now(timezone.utc)

    # A atendente escreveu no chat. A rota grava assim — com a marca de origem.
    banco.semear("conversations", [
        {"id": "c1", "company_id": "autofleet", "user_id": "user:autofleet:554799956540",
         "user_phone": "554799956540", "channel": "whatsapp", "agent_id": None,
         "status": "open"}])
    banco.semear("messages", [
        {"id": "m1", "conversation_id": "c1", "role": "assistant",
         "content": "Já verifiquei com a seguradora", "type": "text",
         "created_at": agora.isoformat(),
         "payload": {"origem": "dashboard", "wa_message_id": None}}])

    # Agora ela VOLTA pelo webhook como fromMe, segundos depois.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540",
        texto="Já verifiquei com a seguradora", msg_type="text", direcao="out",
        message_id="WA-ECO-1", quando_iso=agora.isoformat(), db=banco))
    checar(len(banco.linhas("messages")) == 1,
           "o eco da própria resposta NÃO vira segunda mensagem",
           "sem isto, tudo que a atendente escreve aparece em dobro no chat dela")

    # CONTROLE 1 — texto diferente entra normalmente.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540",
        texto="Outra coisa", msg_type="text", direcao="out",
        message_id="WA-2", quando_iso=agora.isoformat(), db=banco))
    checar(len(banco.linhas("messages")) == 2,
           "CONTROLE — mensagem diferente entra")

    # CONTROLE 2 — o MESMO texto digitado no CELULAR horas depois entra.
    # A janela de eco é curta de propósito: ela cobre a ida-e-volta ao WhatsApp,
    # não dá à atendente uma palavra proibida pelo resto do dia.
    banco.semear("messages", [
        {"id": "m9", "conversation_id": "c1", "role": "assistant",
         "content": "Bom dia", "type": "text",
         "created_at": (agora - timedelta(hours=3)).isoformat(),
         "payload": {"origem": "dashboard", "wa_message_id": None}}])
    antes = len(banco.linhas("messages"))
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540",
        texto="Bom dia", msg_type="text", direcao="out",
        message_id="WA-3", quando_iso=agora.isoformat(), db=banco))
    checar(len(banco.linhas("messages")) == antes + 1,
           "CONTROLE — o mesmo texto 3 horas depois entra",
           "a janela de eco cobre a ida-e-volta, não o dia inteiro")

    # CONTROLE 3 — mensagem do CLIENTE com o mesmo texto nunca é engolida.
    antes = len(banco.linhas("messages"))
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540",
        texto="Já verifiquei com a seguradora", msg_type="text", direcao="in",
        message_id="WA-4", quando_iso=agora.isoformat(), db=banco))
    checar(len(banco.linhas("messages")) == antes + 1,
           "CONTROLE — mensagem do cliente entra mesmo com texto idêntico",
           "o eco só existe para o lado que o dashboard enviou")

    # CONTROLE 4 — o que a MUTAÇÃO revelou, e o motivo de este bloco existir.
    #
    # Uma mutação removeu o filtro `origem='dashboard'` do guarda de eco e todos
    # os controles acima continuaram verdes: o caso do cliente não passa pelo
    # eco (é `in`), e o de 3 horas está fora da janela. O guarda não guardava.
    #
    # O caso real é este: a atendente digita a mesma palavra DUAS VEZES no
    # celular, com segundos de diferença — "ok", "?", "sim". Sem o filtro de
    # origem, a segunda seria confundida com o eco da primeira e sumiria do
    # chat, e ela nunca saberia por quê.
    banco2 = BancoFalso()
    banco2.semear("conversations", [
        {"id": "cc", "company_id": "autofleet", "user_id": "user:autofleet:554711113333",
         "user_phone": "554711113333", "channel": "whatsapp", "agent_id": None,
         "status": "open"}])
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554711113333", texto="ok",
        msg_type="text", direcao="out", message_id="CEL-1",
        quando_iso=agora.isoformat(), db=banco2))
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554711113333", texto="ok",
        msg_type="text", direcao="out", message_id="CEL-2",
        quando_iso=agora.isoformat(), db=banco2))
    checar(len(banco2.linhas("messages")) == 2,
           "CONTROLE — 'ok' digitado duas vezes NO CELULAR aparece duas vezes",
           "o eco só compara com o que o DASHBOARD enviou; o celular não é eco de nada")

    rota = _fonte("app/api/dashboard/conversas/[id]/route.ts")
    checar("origem: 'dashboard'" in rota,
           "a rota do dashboard marca a origem da mensagem",
           "é a marca que o espelho procura para reconhecer o próprio eco")


def _carregar_voz():
    """Carrega `voz_propria` com um Redis de mentira — sem rede, sem contêiner."""
    nome = "_teste_voz_propria"
    if nome in sys.modules:
        return sys.modules[nome]

    class _RedisFalso:
        def __init__(self):
            self.chaves: dict = {}
            self.quebrado = False

        def setex(self, chave, ttl, valor):
            if self.quebrado:
                raise ConnectionError("redis fora do ar")
            self.chaves[chave] = valor

        def getdel(self, chave):
            if self.quebrado:
                raise ConnectionError("redis fora do ar")
            return self.chaves.pop(chave, None)

    falso = types.ModuleType("app.core.redis")
    falso._banco = _RedisFalso()
    falso.get_redis_client = lambda: falso._banco
    sys.modules["app.core.redis"] = falso

    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                           "voz_propria.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    modulo._redis_falso = falso._banco
    return modulo


def teste_a_ia_reconhece_a_propria_voz():
    """🔴 O DEFEITO QUE TERIA MATADO O GO-LIVE.

    📊 14/08/2026, conferido em `webhook.py`: o ramo `fromMe` tratava TODA
    mensagem de saída como "a atendente respondeu pelo celular" — sem perguntar
    quem escreveu. Mas a resposta do próprio agente VOLTA por ali (medido e
    documentado desde 06/08). O agente responderia uma vez, pausaria a si mesmo,
    e ficaria mudo para sempre naquela conversa — com o vigia mandando
    "⏳ AINDA SEM ATENDIMENTO" ao grupo 30 minutos depois.

    Não mordia porque o agente estava desligado. Abriria sozinho no go-live.
    """
    print("\n[6] A IA reconhece a própria voz e não se cala sozinha")
    V = _carregar_voz()
    V._redis_falso.chaves.clear()
    V._redis_falso.quebrado = False

    EMPRESA, FONE = "autofleet", "554799956540"

    # O produto fala. A digital é anotada ANTES de enviar.
    V.registrar_nossa_fala(EMPRESA, FONE, "Sinto muito! Me diga a placa, por favor")

    # O eco volta pelo webhook como fromMe.
    checar(V.e_a_nossa_propria_voz(EMPRESA, FONE,
                                   "Sinto muito! Me diga a placa, por favor") is True,
           "o eco da própria resposta é reconhecido",
           "sem isto o agente responde uma vez e emudece")

    # CONTROLE — a atendente digitando de verdade NÃO é reconhecida como eco.
    checar(V.e_a_nossa_propria_voz(EMPRESA, FONE,
                                   "Oi, aqui é a Regina, vou assumir") is False,
           "CONTROLE — fala de pessoa NÃO é confundida com eco",
           "se fosse, a IA nunca calaria e duas vozes falariam com o cliente")

    # CONTROLE — a digital vale UMA volta. A atendente repetindo de propósito
    # a mesma frase logo depois É uma pessoa, e tem de pausar.
    V.registrar_nossa_fala(EMPRESA, FONE, "ok")
    primeira = V.e_a_nossa_propria_voz(EMPRESA, FONE, "ok")
    segunda = V.e_a_nossa_propria_voz(EMPRESA, FONE, "ok")
    checar(primeira is True and segunda is False,
           "CONTROLE — a digital vale UMA volta só",
           "a 2ª vez que o texto aparece é pessoa, e pausa")

    # CONTROLE — outra corretora com o MESMO telefone e o MESMO texto não
    # aproveita a digital alheia.
    V.registrar_nossa_fala("autofleet", FONE, "seu guincho está a caminho")
    checar(V.e_a_nossa_propria_voz("resulta", FONE,
                                   "seu guincho está a caminho") is False,
           "CONTROLE — a digital NÃO atravessa corretoras",
           "cross-tenant nem aqui")

    # CONTROLE — espaço e maiúscula variam no transporte; a digital sobrevive.
    V.registrar_nossa_fala(EMPRESA, FONE, "Vou verificar sua apólice")
    checar(V.e_a_nossa_propria_voz(EMPRESA, FONE,
                                   "  vou   verificar sua apólice  ") is True,
           "CONTROLE — espaço e caixa não quebram o reconhecimento",
           "o provedor não devolve byte a byte")

    # 🔴 CONTROLE — Redis fora do ar: erra para o lado SEGURO.
    V._redis_falso.quebrado = True
    checar(V.e_a_nossa_propria_voz(EMPRESA, FONE, "qualquer coisa") is False,
           "🔴 CONTROLE — Redis fora ⇒ trata como PESSOA (a IA cala)",
           "duas vozes no mesmo cliente é pior que uma IA calada")
    V._redis_falso.quebrado = False


def teste_o_codigo_faz_as_tres_perguntas_certas():
    """Os três guardas, lidos na fonte real. Guarda de fonte porque o caminho
    do webhook depende de FastAPI e Supabase — o que dá para provar sem rede é
    que as decisões estão escritas onde precisam estar."""
    print("\n[7] Os três portões do atendimento monitorado")
    wh = _comandos("backend/app/api/webhook.py")
    ws = _comandos("backend/app/services/whatsapp_service.py")

    checar("e_a_nossa_propria_voz(" in wh,
           "o ramo fromMe pergunta QUEM escreveu",
           "sem esta pergunta o agente se cala sozinho")
    checar("registrar_nossa_fala(" in ws,
           "o envio anota a digital da própria fala",
           "e anota no ÚNICO lugar por onde todo envio passa")

    # 2.2 — a condição não pode voltar a exigir texto
    ramo = wh[wh.find('skip_reason") == "from_me"'):][:200]
    checar('normalized.get("text")' not in ramo,
           "áudio e foto da atendente TAMBÉM pausam a IA",
           "áudio é o formato mais comum no WhatsApp")

    # 2.3 — o portão de silêncio virou fail-closed
    i = wh.find("is_human_mode = False")
    trecho = wh[i:i + 1400] if i >= 0 else ""
    checar("is_human_mode = True" in trecho.split("except")[-1],
           "🔴 falha de leitura ⇒ a IA CALA (fail-closed)",
           "não conseguir confirmar nunca é permissão para falar")
    checar('.eq("company_id", company_id)' in trecho,
           "CONTROLE — o portão filtra por corretora (CLAUDE.md §7)")


def main() -> int:
    print("=" * 70)
    print("QUEM FALA PRIMEIRO CALA O OUTRO — NAQUELA CONVERSA")
    print("=" * 70)
    teste_a_resposta_pelo_celular_aparece_no_chat()
    teste_a_pausa_e_por_conversa_e_nao_global()
    teste_a_pausa_nunca_desliga_o_agente()
    teste_o_agente_respeita_a_pausa()
    teste_a_resposta_do_dashboard_nao_volta_em_dobro()
    teste_a_ia_reconhece_a_propria_voz()
    teste_o_codigo_faz_as_tres_perguntas_certas()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — uma pessoa assume a conversa, e só aquela.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
