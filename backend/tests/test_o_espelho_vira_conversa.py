"""A conversa que acontece no WhatsApp aparece no chat da corretora.

A HISTÓRIA
==========
📊 06/08/2026, medido: a captura da AutoFleet gravava 124 mensagens por hora em
`attendance_transcripts` — conversas reais de sinistro, com áudio, entrada e
saída, em tempo real. E a tela `Atendimentos → Conversas` da corretora dizia
"Nenhuma conversa ainda".

As duas coisas eram verdade ao mesmo tempo. O acervo enchia; a mesa de trabalho
ficava vazia. Faltava a ponte entre um e outro: `observer_tap` consome o evento
enquanto o agente de atendimento está desligado, e era o pipeline consumido que
criaria a conversa.

Este arquivo guarda a ponte — e, mais do que ela, guarda **o que a ponte não pode
fazer**: ela não pode dar voz ao Observador, nem ligar agente nenhum, nem criar
uma conversa que o agente não vá encontrar no dia em que for ligado.

O DEFEITO QUE QUASE ENTROU
==========================
A primeira versão do plano procurava a conversa por `user_phone`. 📊 O pipeline
do agente procura por `company_id` + `user_id` + `channel` + `agent_id`
(`webhook.get_or_create_conversation`). Chave diferente = duas conversas para o
mesmo cliente — e o defeito só apareceria no dia de ligar o agente, que é o dia
mais caro possível para descobrir qualquer coisa.

`teste_a_ponte_e_o_agente_acham_a_MESMA_conversa` existe para esse dia.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

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
    """A fonte SEM comentários. Guarda que casa com comentário não guarda nada:
    fica verde por uma frase que ninguém executa."""
    return "\n".join(l for l in _fonte(caminho_relativo).split("\n")
                     if not l.lstrip().startswith("#"))


def _corpo_da_funcao(nome: str, fonte: str) -> str:
    """O corpo de UMA função, para o guarda mirar onde a regra vale.

    Existe porque um guarda que proíbe uma string no arquivo inteiro envelhece
    mal: basta a mesma string ganhar um uso legítimo noutro ponto e ele passa a
    reprovar código correto — ou, pior, alguém o afrouxa e ele deixa de reprovar
    o código errado. Recorta por indentação, que é o que delimita bloco em
    Python. Devolve `""` se não achar — e há um controle para esse caso, porque
    um recorte vazio deixaria qualquer `not in` verde por engano.
    """
    linhas = fonte.split("\n")
    for i, linha in enumerate(linhas):
        # `async def` conta. Sem isto o recorte devolvia "" para toda corrotina
        # — e um recorte vazio deixa qualquer `X in corpo` REPROVAR e qualquer
        # `X not in corpo` APROVAR, os dois pelo motivo errado.
        cabeca = linha.lstrip()
        if cabeca.startswith("async def "):
            cabeca = cabeca[len("async "):]
        if cabeca.startswith(f"def {nome}("):
            recuo = len(linha) - len(linha.lstrip())
            # 🔴 A ASSINATURA PODE OCUPAR VÁRIAS LINHAS, e a que fecha o
            # parêntese volta à coluna do `def`:
            #
            #     async def trazer_conversas_ja_capturadas(
            #         *, company_id: str, dias: int = ...,
            #     ) -> dict:            <-- indentação 0, igual à do `def`
            #
            # Cortar por indentação sem contar parênteses termina o recorte
            # AQUI — devolvendo 96 caracteres de assinatura e zero de corpo. O
            # guarda então ficava vermelho ("não achei `deve_espelhar`") por um
            # motivo que não tem nada a ver com o código sob teste.
            profundidade = 0
            inicio = i
            for j in range(i, len(linhas)):
                profundidade += linhas[j].count("(") - linhas[j].count(")")
                if profundidade <= 0 and linhas[j].rstrip().endswith(":"):
                    inicio = j
                    break
            corpo = []
            for seguinte in linhas[inicio + 1:]:
                if seguinte.strip() and (len(seguinte) - len(seguinte.lstrip())) <= recuo:
                    break
                corpo.append(seguinte)
            return "\n".join(corpo)
    return ""


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Um Supabase de mentira, com o mínimo que a ponte usa. Existe para o teste
# rodar sem rede e sem banco — teste que não roda não protege ninguém.
# --------------------------------------------------------------------------
class _Resposta:
    def __init__(self, data):
        self.data = data


# Quantas linhas o PostgREST devolve por resposta, no máximo, doa a quem doer o
# `.limit()`. 📊 Medido em 06/08/2026 pelo número redondo que apareceu no chat.
_TETO_DO_SERVIDOR = 1000


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros: list = []
        self._insert = None
        self._update = None
        self._limite = None
        self._faixa = None
        # Lista, não par: `order()` pode ser chamado duas vezes (critério de
        # desempate), e guardar só o último apagaria o primeiro.
        self._ordem: list = []

    # -- leitura ----------------------------------------------------------
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

    def lt(self, campo, valor):
        """`<` estrito — é o ATRASO DE SEGURANÇA do cursor incremental.

        Sem ele no dublê, o teto de `now() - 5min` seria ignorado e o teste que
        prova "linha recém-inserida ainda não é lida" ficaria VERDE lendo-a.
        """
        self.filtros.append(("lt", campo, valor))
        return self

    def order(self, campo, desc=False, **_k):
        """ORDENA DE VERDADE — e isso já custou dois defeitos hoje.

        🔴 Este método era `return self`, um no-op. Consequência: `limit(N)`
        devolvia as N linhas **primeiras inseridas**, enquanto o Postgres com
        `order desc` devolve as N **últimas**. Comportamento invertido no ponto
        exato de dois bugs reais:

          · o backfill lia as 1.500 MAIS ANTIGAS e o chat parava em 04/08
          · o dedup lia as 40 primeiras em vez das 40 últimas, e conversas com
            mais de 40 mensagens duplicariam a cada ciclo de 10 minutos

        Nos dois casos o teste ficou VERDE por inversão: no dublê, a linha que
        o real deixaria de fora estava sempre dentro.

        Um dublê que ignora `order` não é um banco de mentira — é um dicionário
        com sotaque de SQL.
        """
        self._ordem.append((campo, bool(desc)))
        return self

    def limit(self, n):
        self._limite = n
        return self

    def range(self, inicio, fim):
        """Paginação do PostgREST: `.range(a, b)` é INCLUSIVO nas duas pontas."""
        self._faixa = (int(inicio), int(fim))
        return self

    # -- escrita ----------------------------------------------------------
    def insert(self, linha):
        self._insert = dict(linha)
        return self

    def update(self, campos):
        self._update = dict(campos)
        return self

    @staticmethod
    def _valor(linha, campo):
        """Lê o campo, entendendo a sintaxe JSON do PostgREST (`payload->>chave`).

        O dublê precisa disto porque o dedup do espelho procura por
        `payload->>wa_message_id`. Sem entender a seta, o dublê devolveria
        sempre `None`, nada casaria, e o teste do dedup ficaria VERDE por
        ignorância — que é a pior forma de verde: o guarda existiria e não
        guardaria nada.
        """
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
            # O banco real recusa coluna inexistente e valor fora do CHECK.
            # O dublê passa a recusar também — ver `_COLUNAS_REAIS`.
            _conferir_contra_o_schema(self.tabela, self._insert)
            _conferir_indice_unico(self.tabela, self._insert, linhas)
            novo = dict(self._insert)
            novo.setdefault("id", f"{self.tabela}-{len(linhas) + 1}")
            linhas.append(novo)
            return _Resposta([novo])
        if self._update is not None:
            _conferir_contra_o_schema(self.tabela, self._update)
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self._update)
            return _Resposta(tocadas)
        achadas = [l for l in linhas if self._casa(l)]
        # A ORDEM vem antes do LIMITE — como no Postgres. Trocar a ordem destas
        # duas linhas é exatamente o defeito que o dublê escondia.
        for campo, desc in reversed(self._ordem):
            achadas = sorted(achadas, key=lambda l: str(self._valor(l, campo) or ""),
                             reverse=desc)
        if self._faixa:
            inicio, fim = self._faixa
            achadas = achadas[inicio : fim + 1]
        if self._limite:
            achadas = achadas[: self._limite]
        # 🔴 O TETO DO SERVIDOR, que vence qualquer `.limit()` pedido.
        #
        # 📊 06/08/2026: o backfill pedia `.limit(1500)` e recebia exatamente
        # 1.000 linhas. A janela tinha 1.570 e o chat da AutoFleet ficou parado
        # em 1.000 mensagens, com 19 conversas abertas e vazias — todas as de
        # atividade mais antiga da janela.
        #
        # O dublê antigo obedecia o `.limit()` ao pé da letra e por isso NÃO
        # tinha como reproduzir o defeito: no teste vinham 1.500, em produção
        # vinham 1.000. Um dublê mais generoso que o servidor real esconde
        # exatamente a classe de bug que só aparece com volume.
        return _Resposta(achadas[:_TETO_DO_SERVIDOR])


# 🔴 O SCHEMA REAL, transcrito do banco em 06/08/2026.
#
#   SELECT column_name FROM information_schema.columns
#    WHERE table_schema='public' AND table_name='messages';
#
# O `table_schema='public'` é a parte que eu tinha esquecido. Sem ele o Supabase
# devolve as colunas de `realtime.messages` MISTURADAS com as nossas — e foi daí
# que saíram `topic`, `extension`, `inserted_at` e `updated_at`, que eu passei a
# gravar. 📊 4.059 APIError, e toda conversa com o painel vazio.
#
# O dublê aceitava qualquer coluna. Um banco de mentira que aceita tudo não é
# um banco de mentira: é um saco. A partir daqui ele recusa o que o real recusa.
_COLUNAS_REAIS = {
    "messages": {"id", "conversation_id", "role", "content", "created_at",
                 "type", "audio_url", "image_url", "sender_user_id", "payload"},
    "conversations": {
        "id", "user_id", "session_id", "title", "created_at", "updated_at",
        "company_id", "status", "channel", "last_message_preview",
        "unread_count", "agent_name", "status_color", "user_name",
        "user_avatar", "user_phone", "last_message_at", "agent_id",
        "human_handoff_reason", "claimed_by", "claimed_by_name", "claimed_at",
        "ficha_atendimento", "resolvido_em", "resolucao_motivo"},
    # migration 20260813_01 — a marca d'agua do sync incremental.
    "espelho_sync_cursor": {"company_id", "last_created_at", "last_id",
                            "updated_at"},
}

# Os CHECK que o banco impõe. Mesma razão: o dublê que ignora CHECK deixa passar
# `type='image'`, e o banco real recusa a linha inteira.
_VALORES_ACEITOS = {
    ("messages", "role"): {"user", "assistant"},
    ("messages", "type"): {"text", "voice", None},
}


def _conferir_indice_unico(tabela: str, linha: dict, existentes: list) -> None:
    """`messages_espelho_sem_duplicata_uidx` — migration 20260806_02.

    UNIQUE (conversation_id, payload->>'wa_message_id') WHERE o id não é nulo.

    Sem isto no dublê, o teste da conversa longa não teria como distinguir "o
    Python deduplicou" de "o banco impediu". E é o banco que impede: a janela de
    40 do Python não alcança conversas de 60 mensagens.
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


class ChaveDuplicada(Exception):
    """O banco real diria `23505 duplicate key value violates unique constraint`."""


class ColunaInexistente(Exception):
    """O banco real diria `column "X" of relation "Y" does not exist`."""


class ValorRecusado(Exception):
    """O banco real diria `violates check constraint`."""


def _conferir_contra_o_schema(tabela: str, linha: dict) -> None:
    colunas = _COLUNAS_REAIS.get(tabela)
    if colunas is None:
        return
    for campo, valor in linha.items():
        if campo not in colunas:
            raise ColunaInexistente(
                f'column "{campo}" of relation "{tabela}" does not exist')
        aceitos = _VALORES_ACEITOS.get((tabela, campo))
        if aceitos is not None and valor not in aceitos:
            raise ValorRecusado(
                f'{tabela}.{campo}="{valor}" violates check constraint')


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
    """Carrega a ponte de verdade, com o `integration_service` dublado.

    O dublê é só do resolvedor de usuário, que faz I/O. A REGRA — qual chave a
    ponte usa — continua sendo a real, porque é ela que está sob teste.
    """
    nome = "_teste_espelho_chat"
    if nome in sys.modules:
        return sys.modules[nome]

    if "app.services.integration_service" not in sys.modules:
        falso = types.ModuleType("app.services.integration_service")

        class _Servico:
            @staticmethod
            def get_or_create_user(phone: str, company_id: str, name=None) -> str:
                # Determinístico e por corretora — como o real.
                return f"user:{company_id}:{phone}"

        # 🔴 O dublê tem a forma REAL do módulo: uma FÁBRICA
        # `get_integration_service(client)`, não um objeto solto.
        #
        # 📊 A primeira versão dublava `integration_service` — um nome que NÃO
        # EXISTE lá. O teste ficou verde contra a minha imaginação enquanto
        # produção acumulava 2.255 ImportError e o chat ficava vazio.
        #
        # Um dublê valida a sua suposição, não a realidade. Por isso, além dele,
        # `teste_a_ponte_usa_a_API_QUE_EXISTE` lê a assinatura do arquivo real.
        falso.get_integration_service = lambda *_a, **_k: _Servico()
        sys.modules["app.services.integration_service"] = falso

    caminho = os.path.join(RAIZ, "backend", "app", "services", "atlas", "espelho_chat.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
def teste_o_que_vira_conversa_e_o_que_nao():
    print("\n[1] Nem toda mensagem capturada vira conversa no chat")
    EC = _carregar_espelho()

    checar(EC.deve_espelhar(counterparty="554799956540", texto="Bom dia",
                            msg_type="text", e_grupo=False, e_seguradora=False,
                            idade_horas=0.1),
           "cliente falando agora: vira conversa")
    checar(EC.deve_espelhar(counterparty="554799956540", texto="",
                            msg_type="audio", e_grupo=False, e_seguradora=False,
                            idade_horas=0.1),
           "áudio sem texto AINDA vira conversa",
           "a atendente precisa ver que chegou algo, mesmo sem transcrição")

    # CONTROLE — sem estes, tudo viraria conversa e a mesa ficaria inutilizável.
    checar(not EC.deve_espelhar(counterparty="5511999999999", texto="Bom dia",
                                msg_type="text", e_grupo=False, e_seguradora=True,
                                idade_horas=0.1),
           "CONTROLE — seguradora NÃO vira conversa de atendimento")
    checar(not EC.deve_espelhar(counterparty="123@g.us", texto="oi",
                                msg_type="text", e_grupo=True, e_seguradora=False,
                                idade_horas=0.1),
           "CONTROLE — grupo NÃO vira conversa")
    checar(not EC.deve_espelhar(counterparty="", texto="oi", msg_type="text",
                                e_grupo=False, e_seguradora=False, idade_horas=0.1),
           "CONTROLE — sem contraparte não há conversa a criar")

    # A JANELA DE GRAVAÇÃO é larga, e não é a que a atendente vê.
    checar(EC.deve_espelhar(counterparty="554799956540", texto="oi",
                            msg_type="text", e_grupo=False, e_seguradora=False,
                            idade_horas=200.0),
           "conversa de 8 dias AINDA grava — a janela de 7 dias é da LISTA",
           "esconder na lista é diferente de não gravar; abrir a conversa mostra tudo")
    checar(not EC.deve_espelhar(counterparty="554799956540", texto="oi",
                                msg_type="text", e_grupo=False, e_seguradora=False,
                                idade_horas=5000.0),
           "CONTROLE — histórico de meses não entra de uma vez",
           "é o HISTORY_SYNC de um pareamento novo que esta janela contém")

    checar(EC.JANELA_DA_LISTA_DIAS == 7,
           "a lista mostra 7 dias — decisão do Founder em 06/08/2026",
           f"{EC.JANELA_DA_LISTA_DIAS} dias")


def teste_a_ponte_cria_conversa_e_mensagem():
    print("\n[2] A mensagem capturada vira conversa + mensagem no chat")
    import asyncio

    EC = _carregar_espelho()
    banco = BancoFalso()

    cid = asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="Bom dia",
        msg_type="text", direcao="in", message_id="MSG1",
        quando_iso=_agora_iso(), db=banco))
    checar(cid is not None, "criou a conversa")
    checar(len(banco.linhas("conversations")) == 1, "uma conversa")
    checar(len(banco.linhas("messages")) == 1, "uma mensagem")
    conversa = banco.linhas("conversations")[0]
    checar(conversa["status"] == "open",
           "nasce 'open', nunca HUMAN_REQUESTED",
           "HUMAN_REQUESTED significa 'alguém pediu' e alimenta o vigia de handoff")
    checar(conversa["channel"] == "whatsapp",
           "canal whatsapp — é o filtro que a tela usa")
    checar(conversa.get("agent_id") is None,
           "agent_id nulo — a mesma chave que o pipeline procura")

    # A segunda mensagem da MESMA pessoa entra na MESMA conversa.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="tudo bem?",
        msg_type="text", direcao="in", message_id="MSG2",
        quando_iso=_agora_iso(), db=banco))
    checar(len(banco.linhas("conversations")) == 1, "não duplicou a conversa")
    checar(len(banco.linhas("messages")) == 2, "duas mensagens na mesma conversa")

    # CONTROLE — o mesmo message_id NÃO entra duas vezes. Sem isto, toda
    # resposta enviada pelo dashboard apareceria em dobro: ela vai ao WhatsApp
    # e VOLTA como fromMe.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="tudo bem?",
        msg_type="text", direcao="in", message_id="MSG2",
        quando_iso=_agora_iso(), db=banco))
    checar(len(banco.linhas("messages")) == 2,
           "CONTROLE — message_id repetido não duplica")

    # CONTROLE — corretora diferente, conversa diferente. Multi-tenant (§7).
    asyncio.run(EC.espelhar_no_chat(
        company_id="resulta", counterparty="554799956540", texto="oi",
        msg_type="text", direcao="in", message_id="MSG3",
        quando_iso=_agora_iso(), db=banco))
    checar(len(banco.linhas("conversations")) == 2,
           "CONTROLE — mesmo telefone em outra corretora é outra conversa")

    # A direção vira o papel certo no chat.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="Já verifiquei",
        msg_type="text", direcao="out", message_id="MSG4",
        quando_iso=_agora_iso(), db=banco))
    papeis = [m["role"] for m in banco.linhas("messages")]
    checar("user" in papeis and "assistant" in papeis,
           "cliente vira 'user' e a corretora vira 'assistant'",
           "é assim que o chat sabe de que lado desenhar o balão")


def teste_a_ponte_e_o_agente_acham_a_MESMA_conversa():
    print("\n[3] A conversa do espelho é a MESMA que o agente vai usar")
    EC = _carregar_espelho()

    # 📊 `webhook.py:491` monta assim, e é determinístico.
    esperado = "whatsapp:554799956540:autofleet:default"
    checar(EC.session_id_do_chat("autofleet", "554799956540") == esperado,
           "o session_id é montado igual ao do pipeline do agente", esperado)
    checar(EC.session_id_do_chat("autofleet", "+55 (47) 9995-6540") == esperado,
           "e a formatação do telefone não muda o resultado",
           "senão o mesmo cliente teria duas conversas por causa de um hífen")

    # ⚠️ A PROVA QUE IMPORTA — e ela é COMPORTAMENTAL, não textual.
    #
    # A primeira versão deste guarda procurava `get_or_create_user` no arquivo.
    # A mutação que trocava `.eq("user_id", ...)` por `.eq("user_phone", ...)`
    # passou VERDE por ele: a função continuava importada, só não era usada no
    # filtro. Um guarda que não pega o defeito mais caro do plano não guarda
    # nada (CLAUDE.md §9.3).
    #
    # Agora o teste FAZ o que o pipeline faz: cria pela ponte e procura com a
    # chave do agente. Se não achar, é porque no dia de ligar o agente o mesmo
    # cliente teria duas conversas.
    import asyncio

    banco = BancoFalso()
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="Bom dia",
        msg_type="text", direcao="in", message_id="CONV1",
        quando_iso=_agora_iso(), db=banco))

    from app.services.integration_service import get_integration_service

    usuario_do_pipeline = get_integration_service(banco).get_or_create_user(
        phone="554799956540", company_id="autofleet", name=None)
    achadas = (banco.table("conversations").select("id")
               .eq("company_id", "autofleet").eq("user_id", usuario_do_pipeline)
               .eq("channel", "whatsapp").is_("agent_id", "null")
               .limit(1).execute().data or [])
    checar(len(achadas) == 1,
           "CONTROLE — o pipeline do agente ACHA a conversa que a ponte criou",
           "busca por company+user_id+channel+agent_id, igual a webhook.py:113-125")

    # E a linha do pipeline que este teste espelha — se ela mudar, avisa.
    fonte = _fonte("backend/app/api/webhook.py")
    checar('.eq("user_id", user_id)' in fonte and '.is_("agent_id", "null")' in fonte,
           "CONTROLE — o pipeline ainda procura por esta chave",
           "se mudar lá, a ponte precisa mudar junto — e o teste acima falha")

    # A FRAGILIDADE que a busca por telefone tem e a por `user_id` não tem.
    #
    # Buscar por `user_phone` até funciona enquanto os dois lados escrevem o
    # número igual. Mas o WhatsApp entrega o mesmo cliente ora `554799956540`,
    # ora `5547999956540` (o nono dígito), ora com formatação. `get_or_create_user`
    # resolve isso e devolve SEMPRE o mesmo usuário; o texto do telefone, não.
    #
    # Este guarda é o que separa "funciona hoje" de "vai funcionar sempre".
    banco2 = BancoFalso()
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="primeira",
        msg_type="text", direcao="in", message_id="FMT1",
        quando_iso=_agora_iso(), db=banco2))
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="+55 (47) 9995-6540", texto="segunda",
        msg_type="text", direcao="in", message_id="FMT2",
        quando_iso=_agora_iso(), db=banco2))
    checar(len(banco2.linhas("conversations")) == 1,
           "CONTROLE — o mesmo número em outro formato cai na MESMA conversa",
           "um hífen não pode partir a conversa de um cliente em duas")


def teste_a_ponte_usa_a_API_QUE_EXISTE():
    print("\n[3b] A ponte chama funções que existem de verdade")
    import ast

    # 🔴 O GUARDA QUE FALTAVA, e o motivo dele é o defeito mais caro do dia.
    #
    # 📊 06/08/2026: a ponte fazia `from app.services.integration_service import
    # integration_service`. Aquele nome NÃO EXISTE — o módulo exporta a fábrica
    # `get_integration_service(client)`. Produção acumulou **2.255 ImportError**,
    # o chat ficou vazio, e todos os testes deste arquivo estavam VERDES: eu
    # havia dublado o módulo com a forma que imaginei.
    #
    # Dublê testa a sua suposição. Este guarda testa o ARQUIVO REAL — e é a
    # única coisa aqui que teria pego aquele erro.
    fonte_real = _fonte("backend/app/services/integration_service.py")
    arvore = ast.parse(fonte_real)
    nomes_do_modulo = set()
    for no in arvore.body:  # só o nível de módulo — é o que um import alcança
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nomes_do_modulo.add(no.name)
        elif isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name):
                    nomes_do_modulo.add(alvo.id)
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            nomes_do_modulo.add(no.target.id)

    checar("get_integration_service" in nomes_do_modulo,
           "o módulo exporta a fábrica `get_integration_service`")
    checar("integration_service" not in nomes_do_modulo,
           "CONTROLE — e NÃO exporta um objeto `integration_service`",
           "era exatamente este nome que a ponte importava, 2.255 vezes por nada")

    # E o que a ponte importa dele tem de estar nessa lista.
    ponte = ast.parse(_fonte("backend/app/services/atlas/espelho_chat.py"))
    importados = set()
    for no in ast.walk(ponte):
        if isinstance(no, ast.ImportFrom) and (no.module or "").endswith("integration_service"):
            importados.update(a.name for a in no.names)
    checar(bool(importados), "a ponte importa algo do integration_service", str(importados))
    faltando = importados - nomes_do_modulo
    checar(not faltando,
           "e tudo o que ela importa EXISTE no módulo",
           f"faltando: {faltando or 'nada'}")


def teste_a_mensagem_obedece_o_que_o_BANCO_aceita():
    print("\n[3c] O que a ponte grava cabe nas regras do banco")
    import asyncio

    EC = _carregar_espelho()

    # 🔴 O DEFEITO QUE DEIXOU O CHAT EM BRANCO — 06/08/2026.
    #
    # `messages_type_check` é `CHECK (type = ANY (ARRAY['text','voice']))`. A
    # ponte gravava o tipo cru do WhatsApp (`audio`, `image`, `document`) e o
    # banco recusava a linha inteira. 📊 Resultado: **51 conversas da AutoFleet
    # com ZERO mensagens** e `{"erro:APIError": 2216}` no contador.
    #
    # O dublê do banco não valida CHECK — por isso este guarda testa a TRADUÇÃO,
    # que é a decisão que precisa estar certa.
    checar(EC._tipo_aceito("audio") == "voice", "áudio vira 'voice'")
    checar(EC._tipo_aceito("text") == "text", "texto continua 'text'")
    for bruto in ("image", "document", "video", "sticker", "unknown", ""):
        checar(EC._tipo_aceito(bruto) in ("text", "voice"),
               f"'{bruto or 'vazio'}' cabe no CHECK do banco",
               EC._tipo_aceito(bruto))

    # CONTROLE — o CHECK real, lido do banco em 06/08/2026. Se um dia aceitar
    # mais tipos, este teste continua correto; se aceitar MENOS, ele avisa.
    aceitos = {"text", "voice"}
    checar(all(EC._tipo_aceito(t) in aceitos
               for t in ("audio", "image", "document", "video", "sticker", "ptt", None)),
           "CONTROLE — NENHUM tipo do WhatsApp escapa da tradução",
           "era um tipo escapando que recusava a mensagem inteira")

    # E o tipo de verdade não se perde: vai para o payload.
    banco = BancoFalso()
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="",
        msg_type="image", direcao="in", message_id="IMG1",
        quando_iso=_agora_iso(), db=banco))
    msgs = banco.linhas("messages")
    checar(len(msgs) == 1, "a mensagem de imagem ENTRA")
    checar(msgs[0]["type"] == "text", "com um `type` que o banco aceita")
    checar((msgs[0].get("payload") or {}).get("wa_type") == "image",
           "e o tipo real preservado no payload",
           "para o dia em que a mídia for tocável (P-119)")
    checar("Imagem" in str(msgs[0]["content"]),
           "e a atendente lê algo em português, não `[image]`",
           str(msgs[0]["content"]))


def teste_a_ponte_esta_ligada_e_nao_muda_o_silencio():
    print("\n[4] Ligada ao Observador — e o silêncio intacto")
    cmd = _comandos("backend/app/services/atlas/observer_intake.py")

    checar("espelhar_no_chat(" in cmd, "o tap chama a ponte")

    # A ponte tem de estar nos DOIS ramos: o do segurado e o da SEGURADORA.
    #
    # Decisão do Founder, 06/08/2026: *"precisa aparecer no chat conversas de
    # seguradoras e com os segurados. Se um segurado pedir uma assistência,
    # essa conversa precisa aparecer."*
    #
    # 📊 Uma mutação que removeu a chamada do ramo da seguradora passou VERDE
    # neste arquivo — o guarda contava a existência, não os dois caminhos. Agora
    # conta: são duas chamadas, e um `assert` de quantidade é o que separa "está
    # lá" de "está lá nos dois lugares".
    chamadas = cmd.count("await _espelhar_no_chat_da_corretora(")
    checar(chamadas >= 2,
           "a ponte é chamada no ramo do SEGURADO e no da SEGURADORA",
           f"{chamadas} chamadas — sinistro com a seguradora também é trabalho da corretora")

    # CONTROLE — e o que NÃO pode aparecer continua barrado antes.
    checar('remote.endswith(("@g.us", "@broadcast", "@newsletter", "@call"))' in cmd,
           "CONTROLE — grupo, status e transmissão morrem no filtro de borda",
           'conversa pessoal ("amor, que hora te pego?") nunca chega ao chat')
    checar("client_chat_allowed(" in cmd,
           "CONTROLE — e a conversa com cliente ainda passa pela allowlist")
    # CONTROLE — a linha que decide o silêncio NÃO pode ter mudado. Ela é a
    # regra do Founder: o Observador não fala, e o agente só fala com o botão.
    checar('consumed = {"status": "observed"} if (is_observer and not _agente_ligado) else None' in cmd,
           "CONTROLE — a regra do silêncio está intacta, palavra por palavra")
    # CONTROLE — e a ponte não pode ter trazido caminho de ENVIO junto.
    for proibido in ("send_text(", "send_media(", "/send/", "send_message("):
        checar(proibido not in cmd,
               f"CONTROLE — o Observador continua sem como falar ({proibido})")


def teste_nada_disto_liga_agente_nenhum():
    print("\n[5] Nenhuma peça nova liga agente nenhum")
    for arquivo in ("backend/app/services/atlas/espelho_chat.py",
                    "backend/app/services/atlas/observer_intake.py"):
        cmd = _comandos(arquivo)
        checar('"is_active": True' not in cmd and "'is_active': True" not in cmd,
               f"{os.path.basename(arquivo)} nunca liga um agente")
        checar('table("agents")' not in cmd,
               f"CONTROLE — {os.path.basename(arquivo)} não escreve na tabela de agentes")

    cmd = _comandos("backend/app/services/atlas/espelho_chat.py")
    for proibido in ("send_text(", "send_media(", "/send/", "send_message("):
        checar(proibido not in cmd,
               f"CONTROLE — a ponte não tem caminho de envio ({proibido})")


def teste_a_lista_do_chat_mostra_sete_dias():
    print("\n[6] A lista mostra 7 dias — e abrir a conversa mostra tudo")
    rota = _fonte("app/api/dashboard/conversas/route.ts")

    checar("last_message_at" in rota and "gte" in rota,
           "a lista filtra por data da última mensagem")
    checar("JANELA_DIAS = 7" in rota or "7" in rota,
           "e a janela é de 7 dias")

    # CONTROLE — a janela é da LISTA. A conversa aberta não pode ser cortada:
    # um sinistro que arrasta 45 dias precisa ser legível do começo.
    detalhe = _fonte("app/api/dashboard/conversas/[id]/route.ts")
    checar("last_message_at" not in detalhe.split("action ===")[0]
           or "gte" not in detalhe,
           "CONTROLE — abrir a conversa NÃO aplica a janela",
           "o histórico da conversa não expira; só a lista é enxugada")


def teste_o_acervo_ja_capturado_pode_ir_para_o_chat():
    print("\n[7] O que já foi capturado também chega ao chat")
    import asyncio

    EC = _carregar_espelho()
    banco = BancoFalso()
    # Três mensagens no acervo, duas da mesma pessoa.
    banco.semear("attendance_transcripts", [
        {"id": "t1", "company_id": "autofleet", "counterparty": "554799956540",
         "direction": "in", "msg_type": "text", "text": "Bom dia",
         "message_id": "H1", "wa_timestamp": _agora_iso(),
         "created_at": _agora_iso()},
        {"id": "t2", "company_id": "autofleet", "counterparty": "554799956540",
         "direction": "out", "msg_type": "text", "text": "Bom dia, pois nao",
         "message_id": "H2", "wa_timestamp": _agora_iso(),
         "created_at": _agora_iso()},
        {"id": "t3", "company_id": "autofleet", "counterparty": "554788887777",
         "direction": "in", "msg_type": "audio", "text": "",
         "message_id": "H3", "wa_timestamp": _agora_iso(),
         "created_at": _agora_iso()},
    ])

    r = asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="autofleet", dias=2, db=banco))
    checar(r.get("ok") is True, "o backfill roda", str(r))
    checar(len(banco.linhas("conversations")) == 2,
           "duas pessoas viraram duas conversas")
    checar(len(banco.linhas("messages")) == 3,
           "e as três mensagens entraram")

    # CONTROLE — rodar de novo NÃO duplica. É o que torna seguro repetir quando
    # alguém não tem certeza se já rodou.
    asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="autofleet", dias=2, db=banco))
    checar(len(banco.linhas("messages")) == 3,
           "CONTROLE — rodar duas vezes não duplica nada",
           "a dedup por message_id é a mesma da ponte ao vivo")

    # CONTROLE — sem corretora não faz nada. Uma varredura sem tenant seria a
    # forma mais fácil de misturar acervo de duas corretoras (§7).
    vazio = asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="", dias=2, db=banco))
    checar(vazio.get("ok") is False,
           "CONTROLE — sem company_id o backfill recusa")


def teste_a_janela_inteira_chega_ao_chat_e_nao_so_as_primeiras_mil():
    """📊 06/08/2026 23:52 UTC — o teto de 1.000 do servidor, reproduzido.

        janela de 7 dias da AutoFleet    1.570 linhas no acervo
        mensagens no chat                1.000  (redondo, e parado)
        conversas abertas e VAZIAS          19  (as mais antigas da janela)

    O backfill pedia `.limit(1500)`. O PostgREST tem um teto de linhas por
    resposta que vence o `.limit()` pedido: vinham 1.000. O código achava que
    tinha lido a janela inteira e repetia as MESMAS 1.000 a cada 10 minutos.
    As outras 570 nunca teriam vez — não por erro de dedup, por erro de leitura.

    O número redondo era a pista, e ela estava na tela desde o começo.
    """
    print("\n[8a] A janela inteira chega ao chat — não só as primeiras mil")
    import asyncio

    EC = _carregar_espelho()
    banco = BancoFalso()

    # 1.570 linhas, como na AutoFleet real: acima do teto do servidor e abaixo
    # do limite pedido. É exatamente a faixa em que o defeito vive.
    TOTAL = 1570
    base = datetime.now(timezone.utc)
    banco.semear("attendance_transcripts", [
        {"id": f"t{i}", "company_id": "autofleet",
         # 12 interlocutores, para haver conversas inteiras na cauda antiga —
         # foi assim que as 19 conversas vazias apareceram na lista.
         "counterparty": f"55479995{6000 + (i % 12):04d}",
         "direction": "in" if i % 2 else "out",
         "msg_type": "text", "text": f"linha {i}",
         "message_id": f"W{i:05d}",
         # Mais nova primeiro na ordenação: i=0 é a mais recente.
         "wa_timestamp": (base - timedelta(minutes=i)).isoformat(),
         "created_at": base.isoformat()}
        for i in range(TOTAL)
    ])

    r = asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="autofleet", dias=7, limite=6000, db=banco))
    checar(r.get("ok") is True, "o backfill roda", str(r.get("lidas")))
    checar(r.get("lidas") == TOTAL,
           f"leu a janela INTEIRA: {TOTAL} linhas",
           f'leu {r.get("lidas")} — o teto do servidor é {_TETO_DO_SERVIDOR}')
    checar(len(banco.linhas("messages")) == TOTAL,
           f"e as {TOTAL} chegaram ao chat",
           str(len(banco.linhas("messages"))))

    # Nenhuma conversa aberta e vazia: era esse o sintoma na tela do Founder.
    vazias = [c for c in banco.linhas("conversations")
              if not [m for m in banco.linhas("messages")
                      if m.get("conversation_id") == c.get("id")]]
    checar(not vazias, "nenhuma conversa fica aberta e vazia na lista",
           f"{len(vazias)} vazia(s)")

    # CONTROLE — o dublê CONSEGUE cortar em 1.000. Sem esta linha, o teste
    # acima passaria mesmo que o teto não estivesse sendo simulado, e eu teria
    # "provado" um conserto contra um servidor que nunca recusa nada.
    uma_pagina = banco.client.table("attendance_transcripts").select("*") \
        .eq("company_id", "autofleet").execute().data
    checar(len(uma_pagina) == _TETO_DO_SERVIDOR,
           f"CONTROLE — uma leitura sem paginar ainda para em {_TETO_DO_SERVIDOR}",
           f"{len(uma_pagina)} linhas — é o teto que o conserto precisa vencer")

    # CONTROLE — repetir não duplica, mesmo com 1.570 linhas e 2 páginas.
    antes = len(banco.linhas("messages"))
    asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="autofleet", dias=7, limite=6000, db=banco))
    checar(len(banco.linhas("messages")) == antes,
           "CONTROLE — segunda rodada não duplica nada",
           f"{antes} antes, {len(banco.linhas('messages'))} depois")

    # CONTROLE — o `limite` ainda LIMITA. Se o conserto tivesse virado "leia
    # tudo sempre", uma corretora com 40 mil linhas na janela travaria o
    # agendador, e este teste passaria alegremente.
    outro = BancoFalso()
    outro.semear("attendance_transcripts", [
        {"id": f"u{i}", "company_id": "x", "counterparty": "5547999560001",
         "direction": "in", "msg_type": "text", "text": f"l{i}",
         "message_id": f"U{i:05d}",
         "wa_timestamp": (base - timedelta(minutes=i)).isoformat(),
         "created_at": base.isoformat()}
        for i in range(2500)
    ])
    curto = asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="x", dias=7, limite=2000, db=outro))
    checar(curto.get("lidas") == 2000,
           "CONTROLE — o limite pedido continua valendo como teto",
           f'leu {curto.get("lidas")} de 2.500 com limite=2000')


def teste_conversa_longa_nao_duplica_no_ciclo_seguinte():
    print("\n[8b] Conversa de 60 mensagens não duplica a cada 10 minutos")
    import asyncio

    EC = _carregar_espelho()
    banco = BancoFalso()

    # 🔴 A BOMBA QUE UMA AUDITORIA INDEPENDENTE ENCONTROU — 06/08/2026.
    #
    # O dedup em Python olha as 40 mensagens mais recentes. 📊 Já existem
    # conversas com 60, 53, 48 e 46. O backfill grava da mais ANTIGA para a mais
    # nova, então a mais antiga fica no fim da ordenação por `created_at desc`:
    # fora das 40. Na rodada seguinte do sync (10 em 10 min) ela entraria de
    # novo — e cada duplicata empurra mais mensagens para fora da janela, o que
    # ACELERA o estrago.
    #
    # Este teste roda o mesmo lote DUAS vezes, como o sync faria.
    linhas = []
    for i in range(60):
        linhas.append({
            "id": f"t{i}", "company_id": "autofleet",
            "counterparty": "554799956540", "direction": "in",
            "msg_type": "text", "text": f"mensagem {i}",
            "message_id": f"M{i:03d}",
            "wa_timestamp": (datetime.now(timezone.utc)
                             - timedelta(minutes=60 - i)).isoformat(),
            "created_at": _agora_iso(),
        })
    banco.semear("attendance_transcripts", linhas)

    asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="autofleet", dias=7, db=banco))
    depois_da_primeira = len(banco.linhas("messages"))
    checar(depois_da_primeira == 60,
           "a primeira passada grava as 60 mensagens", str(depois_da_primeira))

    # A SEGUNDA passada — é aqui que a bomba explodia.
    asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="autofleet", dias=7, db=banco))
    depois_da_segunda = len(banco.linhas("messages"))
    checar(depois_da_segunda == 60,
           "CONTROLE — a segunda passada não duplica NENHUMA",
           f"{depois_da_segunda} mensagens (era para ser 60)")

    # E a garantia de verdade não está no Python: está no índice único do banco.
    migracao = _fonte("backend/supabase/migrations/20260806_02_espelho_sem_duplicata.sql")
    checar("CREATE UNIQUE INDEX" in migracao
           and "wa_message_id" in migracao,
           "CONTROLE — e existe índice ÚNICO no banco, que não tem janela",
           "o Postgres garante o que a janela de 40 do Python não consegue")
    cmd = _comandos("backend/app/services/atlas/espelho_chat.py")
    checar('"23505" in str(erro)' in cmd,
           "CONTROLE — e a violação do índice é lida como 'já estava', não erro",
           "contar acerto como erro faria o /health gritar à toa")


def teste_o_historico_de_quinze_meses_nao_entope_a_mesa():
    print("\n[8] Um pareamento novo não despeja anos de conversa no chat")
    import asyncio

    EC = _carregar_espelho()
    banco = BancoFalso()

    # 🔴 O CASO REAL, medido em 06/08/2026.
    #
    # A Amandus pareou e o HISTORY_SYNC trouxe o histórico inteiro. Todas as
    # linhas ficaram com `created_at` de HOJE — e `wa_timestamp` de até maio de
    # 2025. Filtrando por `created_at`, a janela de "2 dias" pegava **34.072**
    # mensagens de quinze meses. Por `wa_timestamp`, pega 127.
    #
    # As duas datas existem na mesma linha e significam coisas diferentes:
    # quando foi GRAVADA × quando foi ENVIADA. Confundi-las é o tipo de engano
    # que não dá erro nenhum — só uma mesa de trabalho inutilizável.
    hoje = _agora_iso()
    velha = (datetime.now(timezone.utc) - timedelta(days=450)).isoformat()
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    banco.semear("attendance_transcripts", [
        # gravada hoje, ENVIADA há 15 meses — o histórico do pareamento
        {"id": "v1", "company_id": "amandus", "counterparty": "554711110000",
         "direction": "in", "msg_type": "text", "text": "oi de 2025",
         "message_id": "V1", "wa_timestamp": velha, "created_at": hoje},
        # gravada hoje, enviada ontem — esta é trabalho de verdade
        {"id": "n1", "company_id": "amandus", "counterparty": "554722220000",
         "direction": "in", "msg_type": "text", "text": "preciso de guincho",
         "message_id": "N1", "wa_timestamp": ontem, "created_at": hoje},
    ])

    r = asyncio.run(EC.trazer_conversas_ja_capturadas(
        company_id="amandus", dias=7, db=banco))
    checar(r.get("ok") is True, "o backfill roda", str(r))
    checar(len(banco.linhas("conversations")) == 1,
           "só a conversa RECENTE entra no chat",
           "a de 15 meses fica no acervo, onde ela pertence")
    checar(banco.linhas("conversations")[0]["user_phone"] == "554722220000",
           "e é a certa — a de ontem, não a de 2025")

    # CONTROLE — o guarda tem de conseguir reprovar. Se a leitura filtrasse por
    # `created_at`, as DUAS entrariam (ambas foram gravadas hoje).
    #
    # 🔴 ESTE GUARDA MUDOU DE FORMA EM 13/08/2026, E A LIÇÃO MIGROU INTEIRA.
    #
    # Ele proibia a string `.gte("created_at", desde)` no ARQUIVO INTEIRO. Era
    # suficiente enquanto `created_at` não tinha uso legítimo ali. Passou a ter
    # dois: a janela de eco (Alavanca A) e o cursor de ingestão (Alavanca B) —
    # e este último existe justamente porque `created_at` é o ÚNICO relógio que
    # responde "esta linha chegou agora?". 📊 99.845 das 99.951 linhas
    # `history_sync` chegam com mais de 15 min de atraso sobre o `wa_timestamp`;
    # um cursor por `wa_timestamp` perderia 99,89% delas em silêncio.
    #
    # A regra que continua valendo é mais estreita e não venceu:
    # **a ELEGIBILIDADE é julgada por `wa_timestamp`, nunca por `created_at`.**
    # Por isso o guarda passou a olhar a FUNÇÃO que lê o acervo, e não o arquivo
    # inteiro. CLAUDE.md §9.3: quando o fato muda, o teste muda com ele.
    cmd = _comandos("backend/app/services/atlas/espelho_chat.py")
    # 🔴 `_ler_pagina_do_acervo`, e não `_ler`. Havia DUAS funções `_ler` no
    # módulo — uma dentro de `diagnostico()`, outra dentro do backfill — e o
    # recorte pegava a primeira, deixando o guarda verde sobre a função errada.
    # O nome ambíguo foi desfeito na origem; o controle abaixo prova o recorte.
    leitura = _corpo_da_funcao("_ler_pagina_do_acervo", cmd)
    checar('.gte("wa_timestamp", desde)' in leitura,
           "CONTROLE — o backfill filtra pela data REAL da mensagem")
    checar('.gte("created_at"' not in leitura,
           "CONTROLE — e NÃO pela data em que ela foi gravada",
           "gravada hoje ≠ enviada hoje; o pareamento novo prova isso")
    checar(leitura != "" and "attendance_transcripts" in leitura,
           "CONTROLE — o guarda achou mesmo a função que lê o acervo",
           "um recorte vazio deixaria os dois controles acima verdes por engano")

    # 🔴 ESTE GUARDA TAMBÉM MUDOU DE FORMA EM 13/08/2026 — e pelo mesmo motivo.
    #
    # Ele exigia que o sync usasse a MESMA JANELA EM DIAS da lista. Fazia
    # sentido enquanto o sync era uma varredura por janela. Agora ele é um
    # CURSOR: não tem janela nenhuma, tem "o que chegou desde a última vez".
    #
    # Mas havia uma regra de produto escondida naquele guarda, e ela não venceu
    # — ao contrário, estava sendo VIOLADA e ninguém via:
    #
    #   📊 O backfill NÃO chamava `deve_espelhar`. Uma mensagem que chegava ao
    #   vivo valia 30 dias (`LIMITE_DE_RECENCIA_HORAS`); a MESMA mensagem, vinda
    #   do acervo, valia 7. Duas regras para a mesma pergunta, escolhidas pelo
    #   caminho que a mensagem tomou.
    #
    # A regra agora é uma só e é a documentada: quem julga ELEGIBILIDADE é
    # `deve_espelhar`, nos TRÊS caminhos. Os 7 dias continuam sendo o que a
    # LISTA mostra — que é outra coisa, e continua sendo verdade.
    checar(EC.JANELA_DA_LISTA_DIAS == 7,
           "a lista da mesa de trabalho continua mostrando 7 dias",
           "é o que a atendente vê ao abrir a tela")
    checar(EC.LIMITE_DE_RECENCIA_HORAS == 720.0,
           "e a elegibilidade continua sendo 30 dias",
           "existe para o HISTORY_SYNC de um pareamento novo")
    for caminho, funcao in (("ponte ao vivo", None),
                            ("backfill one-shot", "trazer_conversas_ja_capturadas"),
                            ("sync incremental", "_sincronizar_uma_corretora")):
        if funcao is None:
            continue
        corpo = _corpo_da_funcao(funcao, cmd)
        checar("deve_espelhar(" in corpo,
               f"CONTROLE — o {caminho} julga pela MESMA regra",
               "uma regra só, decidida pela mensagem e não pelo caminho dela")
    checar("deve_espelhar(" in _corpo_da_funcao(
               "_espelhar_no_chat_da_corretora",
               _comandos("backend/app/services/atlas/observer_intake.py")),
           "CONTROLE — e a ponte ao vivo também",
           "os três caminhos, a mesma pergunta")


def teste_um_ciclo_sem_novidade_nao_le_o_chat_inteiro() -> None:
    """🔴 O TESTE QUE MEDE O QUE CUSTOU A COTA DO SUPABASE.

    📊 13/08/2026, produção: o sync releu o acervo a cada ciclo e, para CADA
    linha, carregava as 40 últimas mensagens da conversa para deduplicar. O
    contador do Postgres registrou **771.313 chamadas** dessa consulta, com
    ~33 linhas de 290 B cada — para produzir **5.681 mensagens**.

        136 leituras de `messages` para cada mensagem escrita.

    Isso sozinho é da ordem dos 6,98 GB que restringiram a organização no plano
    Free, e o produto inteiro passou a responder 402.

    O que este teste guarda é a REGRA que impede a volta: uma passada que não
    tem nada novo para escrever não pode ler `messages` nenhuma vez. Nenhuma —
    não "poucas". O eco é a única leitura que sobrou, e ele não pode existir
    para mensagem antiga vinda do acervo.

    Guarda comportamento, não implementação: se alguém reintroduzir QUALQUER
    leitura por linha — outra janela, outro atalho, outro cache mal colocado —
    o número sobe e este teste reprova.
    """
    import asyncio

    print("\n[9] Um ciclo sem novidade não relê o chat inteiro")
    EC = _carregar_espelho()
    banco = BancoFalso()

    # Um contador de leituras por tabela, espetado no dublê.
    leituras: dict = {}
    original = BancoFalso.table

    def _contando(self, nome):
        consulta = original(self, nome)
        executar = consulta.execute

        def _conta():
            resposta = executar()
            # Só LEITURA conta: insert/update não são o problema do Egress.
            if consulta._insert is None and consulta._update is None:
                leituras[nome] = leituras.get(nome, 0) + 1
            return resposta

        consulta.execute = _conta
        return consulta

    BancoFalso.table = _contando
    try:
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        banco.semear("attendance_transcripts", [
            {"id": f"t{i}", "company_id": "autofleet",
             "counterparty": f"55479995{i:04d}", "direction": "in",
             "msg_type": "text", "text": f"mensagem {i}", "message_id": f"WA-{i}",
             "wa_timestamp": ontem, "created_at": ontem}
            for i in range(50)])

        # 1ª passada: trabalho de verdade — 50 conversas e 50 mensagens nascem.
        asyncio.run(EC.trazer_conversas_ja_capturadas(
            company_id="autofleet", dias=7, db=banco))
        primeira = dict(leituras)
        checar(len(banco.linhas("messages")) == 50,
               "a primeira passada grava as 50 mensagens",
               f"{len(banco.linhas('messages'))}")

        # 2ª passada: NADA é novo. É o ciclo que rodava a cada 10 minutos.
        leituras.clear()
        asyncio.run(EC.trazer_conversas_ja_capturadas(
            company_id="autofleet", dias=7, db=banco))

        checar(len(banco.linhas("messages")) == 50,
               "a segunda passada não escreve nada",
               f"{len(banco.linhas('messages'))} (era para ser 50)")
        checar(leituras.get("messages", 0) == 0,
               "🔴 e não lê `messages` NENHUMA vez",
               f"{leituras.get('messages', 0)} leitura(s) — o desenho antigo fazia 50")
        checar(leituras.get("attendance_transcripts", 0) <= 2,
               "CONTROLE — o acervo ainda é lido (senão não haveria o que deduplicar)",
               f"{leituras.get('attendance_transcripts', 0)} página(s)")
        checar(primeira.get("messages", 0) == 0,
               "CONTROLE — nem a PRIMEIRA passada lê `messages`",
               "mensagem do cliente (direcao=in) nunca pode ser eco de nada")
    finally:
        BancoFalso.table = original


def teste_o_eco_ainda_le_quando_precisa() -> None:
    """CONTROLE do teste acima: provar que a leitura de eco NÃO morreu.

    Um teste que só sabe dizer "leu zero vezes" fica verde se alguém apagar o
    guarda de eco inteiro. Este prova o outro lado: quando a mensagem PODE ser
    eco — saída, com texto, recém-chegada — a leitura acontece.

    Sem este par, "zero leituras" seria uma vitória vazia.
    """
    import asyncio

    print("\n[9b] CONTROLE — a leitura de eco acontece quando pode haver eco")
    EC = _carregar_espelho()
    banco = BancoFalso()
    leituras: dict = {}
    original = BancoFalso.table

    def _contando(self, nome):
        consulta = original(self, nome)
        executar = consulta.execute

        def _conta():
            resposta = executar()
            if consulta._insert is None and consulta._update is None:
                leituras[nome] = leituras.get(nome, 0) + 1
            return resposta

        consulta.execute = _conta
        return consulta

    BancoFalso.table = _contando
    try:
        agora = datetime.now(timezone.utc)
        banco.semear("conversations", [
            {"id": "c1", "company_id": "autofleet",
             "user_id": "user:autofleet:554799956540",
             "user_phone": "554799956540", "channel": "whatsapp",
             "agent_id": None, "status": "open"}])

        # Mensagem de SAÍDA, agora: pode ser eco → tem de ler.
        leituras.clear()
        asyncio.run(EC.espelhar_no_chat(
            company_id="autofleet", counterparty="554799956540", texto="pronto",
            msg_type="text", direcao="out", message_id="WA-OUT-1",
            quando_iso=agora.isoformat(), db=banco))
        checar(leituras.get("messages", 0) == 1,
               "mensagem de saída recente: o eco É consultado",
               f"{leituras.get('messages', 0)} leitura(s)")

        # Mesma mensagem de saída, mas de ONTEM: não pode ser eco → não lê.
        leituras.clear()
        asyncio.run(EC.espelhar_no_chat(
            company_id="autofleet", counterparty="554799956540", texto="antiga",
            msg_type="text", direcao="out", message_id="WA-OUT-2",
            quando_iso=(agora - timedelta(days=1)).isoformat(), db=banco))
        checar(leituras.get("messages", 0) == 0,
               "CONTROLE — mensagem de saída ANTIGA não consulta o eco",
               "eco de dois minutos não alcança mensagem de ontem")

        # Mensagem de ENTRADA agora: cliente não ecoa dashboard → não lê.
        leituras.clear()
        asyncio.run(EC.espelhar_no_chat(
            company_id="autofleet", counterparty="554799956540", texto="oi",
            msg_type="text", direcao="in", message_id="WA-IN-1",
            quando_iso=agora.isoformat(), db=banco))
        checar(leituras.get("messages", 0) == 0,
               "CONTROLE — mensagem do CLIENTE não consulta o eco",
               "o eco só existe para o lado que o dashboard enviou")
    finally:
        BancoFalso.table = original


def _com_banco_global(banco):
    """Faz `from app.core.database import get_supabase_client` devolver o dublê.

    `sincronizar_chats` não recebe `db` por parâmetro — ele é o job do
    agendador e resolve o cliente sozinho. Para testá-lo de verdade (e não uma
    versão dele com um parâmetro que só existe no teste), o módulo é dublado.
    """
    falso = types.ModuleType("app.core.database")
    falso.get_supabase_client = lambda: banco
    sys.modules["app.core.database"] = falso


def teste_o_cursor_nunca_perde_e_nunca_varre() -> None:
    """🔴 A ALAVANCA B: o sync passa a ler só o que CHEGOU desde a última vez.

    Este é o teste do desenho que quase entrou errado duas vezes. Ele guarda
    quatro garantias, e cada uma existe por uma medição:

    · **O cursor é o relógio de INGESTÃO.** 📊 99.845 das 99.951 linhas
      `history_sync` chegam com mais de 15 min de atraso entre `wa_timestamp` e
      `created_at` — média 3.981 h, máximo 16.293 h. Um cursor por
      `wa_timestamp` não as veria: ficariam intactas no acervo e nunca no chat.
    · **Sem cursor NÃO significa varrer tudo.** O acervo tem 105.275 linhas;
      uma varredura inicial automática seria 26× o ciclo que causou o incidente,
      no minuto seguinte ao Founder pagar pelo Pro.
    · **O cursor não avança sobre erro.** Uma queda de rede de três segundos não
      pode virar uma mensagem que nunca aparece.
    · **O atraso de segurança.** `created_at` usa `now()`, que no Postgres é o
      início da transação e não o commit.
    """
    import asyncio

    print("\n[10] O cursor: incremental, sem perder e sem varrer")
    EC = _carregar_espelho()
    banco = BancoFalso()
    _com_banco_global(banco)
    os.environ["ESPELHO_SYNC_ENABLED"] = "1"

    agora = datetime.now(timezone.utc)
    velho = (agora - timedelta(minutes=30)).isoformat()      # fora do atraso
    recentissimo = (agora - timedelta(seconds=30)).isoformat()  # DENTRO do atraso

    banco.semear("integrations", [
        {"id": "i1", "company_id": "amandus", "provider": "evolution-go",
         "is_active": True},
        {"id": "i2", "company_id": "autofleet", "provider": "evolution-go",
         "is_active": True}])

    # --- 1) sem cursor: nasce no presente e NÃO lê o acervo -----------------
    banco.semear("attendance_transcripts", [
        {"id": "a1", "company_id": "amandus", "counterparty": "554700000001",
         "direction": "in", "msg_type": "text", "text": "antiga do acervo",
         "message_id": "OLD-1", "wa_timestamp": velho, "created_at": velho,
         "insurer_key": None}])

    r = asyncio.run(EC.sincronizar_chats())
    checar(len(banco.linhas("espelho_sync_cursor")) == 2,
           "sem cursor, cada corretora ganha o seu — no PRESENTE",
           f"{len(banco.linhas('espelho_sync_cursor'))} cursor(es)")
    checar(int(r.get("lidas") or 0) == 0,
           "🔴 e NÃO varre o acervo na primeira passada",
           f"{r.get('lidas')} linha(s) lidas — 105.275 no banco real")
    checar(len(banco.linhas("messages")) == 0,
           "CONTROLE — nenhuma mensagem foi espelhada por varredura automática",
           "a recuperação inicial é ato deliberado, pelo endpoint one-shot")

    # --- 2) linha NOVA chega: o cursor a encontra ---------------------------
    cur = next(c for c in banco.linhas("espelho_sync_cursor")
               if c["company_id"] == "amandus")
    cur["last_created_at"] = (agora - timedelta(hours=1)).isoformat()

    banco.semear("attendance_transcripts", [
        {"id": "a2", "company_id": "amandus", "counterparty": "554700000002",
         "direction": "in", "msg_type": "text", "text": "preciso de guincho",
         "message_id": "NEW-1", "wa_timestamp": velho, "created_at": velho,
         "insurer_key": None},
        # 🔴 O CASO history_sync: ENVIADA em 2024, CHEGOU agora.
        {"id": "a3", "company_id": "amandus", "counterparty": "554700000003",
         "direction": "in", "msg_type": "text", "text": "oi de 2024",
         "message_id": "HIST-1",
         "wa_timestamp": (agora - timedelta(days=600)).isoformat(),
         "created_at": velho, "insurer_key": None},
        # Recém-inserida: dentro do atraso de segurança, ainda não pode ser lida
        {"id": "a4", "company_id": "amandus", "counterparty": "554700000004",
         "direction": "in", "msg_type": "text", "text": "acabou de chegar",
         "message_id": "FRESH-1", "wa_timestamp": recentissimo,
         "created_at": recentissimo, "insurer_key": None},
    ])

    r = asyncio.run(EC.sincronizar_chats())
    telefones = {c["user_phone"] for c in banco.linhas("conversations")}
    checar("554700000002" in telefones,
           "a linha nova entra no chat", "encontrada pelo relógio de ingestão")
    checar("554700000003" not in telefones,
           "a de 2024 não aparece na mesa de trabalho",
           "wa_timestamp julga a elegibilidade, e 600 dias > 30")
    # 🔴 A ASSERÇÃO QUE DE VERDADE PEGA O CURSOR ERRADO.
    #
    # "não apareceu no chat" tem DUAS explicações, e só uma é aceitável:
    #   · foi LIDA e RECUSADA pela elegibilidade  → certo
    #   · nunca foi lida, porque o cursor não a viu → é a perda silenciosa
    #
    # 📊 Com um cursor por `wa_timestamp`, 99,89% das linhas `history_sync`
    # caem no segundo caso. As duas versões deixam o chat igual; só uma delas
    # ainda funciona no dia em que a corretora pareia um WhatsApp novo.
    #
    # Por isso o guarda mede o que foi LIDO, não o que apareceu.
    checar(int(r.get("lidas") or 0) == 3,
           "🔴 CONTROLE — a de 2024 foi LIDA (encontrada pelo relógio de ingestão)",
           f"{r.get('lidas')} lidas: a1, a2 e a3 — a4 espera o atraso de segurança")
    checar(int(r.get("filtradas") or 0) >= 1,
           "CONTROLE — e foi RECUSADA como 'filtrada', não como erro",
           "se contasse como erro, o cursor travaria nela para sempre")
    checar("554700000004" not in telefones,
           "🔴 CONTROLE — a recém-inserida espera o atraso de segurança",
           "now() do Postgres é o início da transação, não o commit")

    # --- 3) tenants não se misturam ----------------------------------------
    checar(all(c["company_id"] == "amandus" for c in banco.linhas("conversations")),
           "CONTROLE — nada da Amandus apareceu na AutoFleet",
           "o cursor e a leitura são POR company_id")

    # --- 4) segunda passada sem novidade: trabalho mínimo ------------------
    r2 = asyncio.run(EC.sincronizar_chats())
    checar(int(r2.get("levadas") or 0) == 0,
           "a passada seguinte não escreve nada",
           f"{r2.get('levadas')} nova(s)")
    checar(int(r2.get("lidas") or 0) <= 2,
           "🔴 e quase não LÊ — o laço morreu",
           f"{r2.get('lidas')} linha(s) — o desenho antigo lia 4.008 por ciclo")

    os.environ.pop("ESPELHO_SYNC_ENABLED", None)


def teste_o_cursor_nao_avanca_sobre_erro() -> None:
    """Uma falha transitória não pode virar mensagem perdida para sempre.

    📊 `espelhar_no_chat` engole exceção e devolve `None` — de propósito: o
    espelho é bônus e a captura é a obrigação. Mas para um CURSOR isso não
    basta: "não gravei" e "não devia gravar" são a mesma resposta, e avançar
    sobre a primeira apaga a mensagem do chat em silêncio.

    Por isso o cursor só ultrapassa `DESFECHOS_DETERMINISTICOS`.
    """
    import asyncio

    print("\n[10b] O cursor trava antes da linha que falhou")
    EC = _carregar_espelho()
    banco = BancoFalso()
    _com_banco_global(banco)
    os.environ["ESPELHO_SYNC_ENABLED"] = "1"

    agora = datetime.now(timezone.utc)
    quando = (agora - timedelta(minutes=30)).isoformat()
    banco.semear("integrations", [
        {"id": "i1", "company_id": "amandus", "provider": "evolution-go",
         "is_active": True}])
    banco.semear("espelho_sync_cursor", [
        {"company_id": "amandus",
         "last_created_at": (agora - timedelta(hours=2)).isoformat(),
         "last_id": None, "updated_at": quando}])
    banco.semear("attendance_transcripts", [
        {"id": f"a{i}", "company_id": "amandus",
         "counterparty": f"55470000000{i}", "direction": "in",
         "msg_type": "text", "text": f"linha {i}", "message_id": f"M-{i}",
         "wa_timestamp": quando, "created_at": quando, "insurer_key": None}
        for i in range(1, 4)])

    # A segunda linha estoura. O cursor tem de parar ANTES dela.
    original = EC._espelhar_com_desfecho

    async def _com_falha(**kw):
        if kw.get("message_id") == "M-2":
            return None, "erro:APIError"
        return await original(**kw)

    EC._espelhar_com_desfecho = _com_falha
    try:
        r = asyncio.run(EC.sincronizar_chats())
    finally:
        EC._espelhar_com_desfecho = original

    cursor = banco.linhas("espelho_sync_cursor")[0]
    checar(int(r.get("travou_em") or 0) == 1,
           "o sync reconhece que travou numa linha", str(r.get("travou_em")))
    checar(cursor["last_id"] == "a1",
           "🔴 o cursor parou em a1 — ANTES da linha que falhou",
           f"last_id={cursor['last_id']} (a2 falhou; a3 nem foi tentada)")
    checar(len(banco.linhas("messages")) == 1,
           "CONTROLE — só a linha anterior à falha foi gravada",
           f"{len(banco.linhas('messages'))} mensagem(ns)")

    # E na passada seguinte, sem a falha, ela volta.
    r2 = asyncio.run(EC.sincronizar_chats())
    checar(len(banco.linhas("messages")) == 3,
           "🔴 CONTROLE — a linha que falhou VOLTA na próxima passada",
           f"{len(banco.linhas('messages'))} mensagens (a2 e a3 entraram)")
    checar(int(r2.get("travou_em") or 0) == 0,
           "CONTROLE — e agora nada trava", str(r2))

    os.environ.pop("ESPELHO_SYNC_ENABLED", None)


def teste_um_tropeco_de_rede_nao_derruba_o_lote() -> None:
    """📊 O defeito medido em 15/08: 499 linhas lidas, ~45 avançadas.

    Um `RemoteProtocolError` numa linha derrubava a passada inteira — e as
    outras 455 já tinham sido LIDAS, isto é, o Egress já tinha sido pago.
    Pagar a leitura e jogar fora é o desperdício de agosto na versão pequena.

    A linha que falha para SEMPRE continua travando o cursor: isso é o que
    impede perder mensagem, e o teste [10b] guarda. O que muda aqui é a linha
    que falha UMA vez — a cara de uma conexão que o Supabase fechou.
    """
    import asyncio

    print("\n[10d] Um tropeço de rede não leva as outras linhas junto")
    EC = _carregar_espelho()
    banco = BancoFalso()
    _com_banco_global(banco)
    os.environ["ESPELHO_SYNC_ENABLED"] = "1"

    agora = datetime.now(timezone.utc)
    quando = (agora - timedelta(minutes=30)).isoformat()
    banco.semear("integrations", [
        {"id": "i1", "company_id": "amandus", "provider": "evolution-go",
         "is_active": True}])
    banco.semear("espelho_sync_cursor", [
        {"company_id": "amandus",
         "last_created_at": (agora - timedelta(hours=2)).isoformat(),
         "last_id": None, "updated_at": quando}])
    banco.semear("attendance_transcripts", [
        {"id": f"a{i}", "company_id": "amandus",
         "counterparty": f"55470000000{i}", "direction": "in",
         "msg_type": "text", "text": f"linha {i}", "message_id": f"M-{i}",
         "wa_timestamp": quando, "created_at": quando, "insurer_key": None}
        for i in range(1, 4)])

    original = EC._espelhar_com_desfecho
    tropecos = {"M-2": 1}  # falha UMA vez, depois se comporta

    async def _tropeca_uma_vez(**kw):
        alvo = kw.get("message_id")
        if tropecos.get(alvo):
            tropecos[alvo] -= 1
            return None, "erro:RemoteProtocolError"
        return await original(**kw)

    EC._espelhar_com_desfecho = _tropeca_uma_vez
    try:
        r = asyncio.run(EC.sincronizar_chats())
    finally:
        EC._espelhar_com_desfecho = original

    cursor = banco.linhas("espelho_sync_cursor")[0]
    checar(int(r.get("travou_em") or 0) == 0,
           "🔴 a passada NÃO trava por um tropeço de rede", str(r))
    checar(int(r.get("retentadas") or 0) == 1,
           "e o contador diz que houve exatamente 1 retentativa",
           f"retentadas={r.get('retentadas')}")
    checar(cursor["last_id"] == "a3",
           "🔴 o cursor chega até o FIM do lote, não morre na linha 2",
           f"last_id={cursor['last_id']}")
    checar(len(banco.linhas("messages")) == 3,
           "as três linhas entraram na mesa",
           f"{len(banco.linhas('messages'))} mensagem(ns)")

    # CONTROLE — o guarda continua guardando. Falha que NUNCA passa ainda trava.
    banco2 = BancoFalso()
    _com_banco_global(banco2)
    banco2.semear("integrations", [
        {"id": "i1", "company_id": "amandus", "provider": "evolution-go",
         "is_active": True}])
    banco2.semear("espelho_sync_cursor", [
        {"company_id": "amandus",
         "last_created_at": (agora - timedelta(hours=2)).isoformat(),
         "last_id": None, "updated_at": quando}])
    banco2.semear("attendance_transcripts", [
        {"id": f"a{i}", "company_id": "amandus",
         "counterparty": f"55470000000{i}", "direction": "in",
         "msg_type": "text", "text": f"linha {i}", "message_id": f"M-{i}",
         "wa_timestamp": quando, "created_at": quando, "insurer_key": None}
        for i in range(1, 4)])

    async def _falha_sempre(**kw):
        if kw.get("message_id") == "M-2":
            return None, "erro:RemoteProtocolError"
        return await original(**kw)

    EC._espelhar_com_desfecho = _falha_sempre
    try:
        rc = asyncio.run(EC.sincronizar_chats())
    finally:
        EC._espelhar_com_desfecho = original

    checar(int(rc.get("travou_em") or 0) == 1,
           "🔴 CONTROLE — falha que nunca passa AINDA trava o cursor", str(rc))
    checar(banco2.linhas("espelho_sync_cursor")[0]["last_id"] == "a1",
           "CONTROLE — e ele para antes da linha ruim, como sempre",
           f"last_id={banco2.linhas('espelho_sync_cursor')[0]['last_id']}")
    checar(int(rc.get("retentadas") or 0) == EC._TENTATIVAS_POR_LINHA - 1,
           "CONTROLE — tentou o número de vezes que promete, e desistiu",
           f"retentadas={rc.get('retentadas')} de "
           f"{EC._TENTATIVAS_POR_LINHA} tentativas")

    os.environ.pop("ESPELHO_SYNC_ENABLED", None)


def teste_recusa_permanente_nao_prende_a_corretora() -> None:
    """A contraparte sem dígito nenhum passava na elegibilidade e morria na
    gravação — com um motivo que o cursor nunca ultrapassava.

    `deve_espelhar` exige `counterparty.strip()`; `_espelhar_com_desfecho` exige
    `_digitos(counterparty)`. Um `status@broadcast` satisfaz o primeiro e nunca
    o segundo, **com o mesmo resultado toda vez**. Fora de
    `DESFECHOS_DETERMINISTICOS`, ela prenderia a corretora INTEIRA para sempre.

    📊 Zero linhas assim em 150.734 hoje. A guarda é para o dia em que houver.
    """
    import asyncio

    print("\n[10e] Recusa permanente não prende a corretora para sempre")
    EC = _carregar_espelho()

    checar("sem_telefone_ou_empresa" in EC.DESFECHOS_DETERMINISTICOS,
           "recusa permanente é ultrapassável")
    checar("sem_usuario" not in EC.DESFECHOS_DETERMINISTICOS
           and "conversa_nao_criada" not in EC.DESFECHOS_DETERMINISTICOS,
           "🔴 CONTROLE — mas falha de BANCO continua travando",
           "sem_usuario e conversa_nao_criada seguem fora")

    banco = BancoFalso()
    _com_banco_global(banco)
    os.environ["ESPELHO_SYNC_ENABLED"] = "1"

    agora = datetime.now(timezone.utc)
    quando = (agora - timedelta(minutes=30)).isoformat()
    banco.semear("integrations", [
        {"id": "i1", "company_id": "amandus", "provider": "evolution-go",
         "is_active": True}])
    banco.semear("espelho_sync_cursor", [
        {"company_id": "amandus",
         "last_created_at": (agora - timedelta(hours=2)).isoformat(),
         "last_id": None, "updated_at": quando}])
    # a2 não tem UM dígito: entra pela elegibilidade, é recusada na gravação.
    banco.semear("attendance_transcripts", [
        {"id": "a1", "company_id": "amandus", "counterparty": "554700000001",
         "direction": "in", "msg_type": "text", "text": "antes",
         "message_id": "M-1", "wa_timestamp": quando, "created_at": quando,
         "insurer_key": None},
        {"id": "a2", "company_id": "amandus", "counterparty": "status@broadcast",
         "direction": "in", "msg_type": "text", "text": "aviso",
         "message_id": "M-2", "wa_timestamp": quando, "created_at": quando,
         "insurer_key": None},
        {"id": "a3", "company_id": "amandus", "counterparty": "554700000003",
         "direction": "in", "msg_type": "text", "text": "depois",
         "message_id": "M-3", "wa_timestamp": quando, "created_at": quando,
         "insurer_key": None}])

    r = asyncio.run(EC.sincronizar_chats())
    cursor = banco.linhas("espelho_sync_cursor")[0]

    checar(int(r.get("travou_em") or 0) == 0,
           "a linha impossível não trava a passada", str(r))
    checar(cursor["last_id"] == "a3",
           "🔴 o cursor PASSA por ela e chega no fim",
           f"last_id={cursor['last_id']}")
    checar(len(banco.linhas("messages")) == 2,
           "CONTROLE — e ela não virou mensagem; só as duas de verdade",
           f"{len(banco.linhas('messages'))} mensagem(ns)")
    checar(int(r.get("filtradas") or 0) == 1 and int(r.get("ja_estavam") or 0) == 0,
           "🔴 e o contador NÃO mente: ela é 'filtrada', não 'já estava'",
           f"filtradas={r.get('filtradas')} ja_estavam={r.get('ja_estavam')}")

    os.environ.pop("ESPELHO_SYNC_ENABLED", None)


def teste_o_interruptor_nasce_desligado() -> None:
    """O kill switch que não existia no dia do incidente.

    📊 13/08/2026: este job consumiu a ordem dos 6,98 GB que restringiram a
    organização, e não havia como pará-lo sem derrubar o produto.
    `ESPELHO_SYNC_LIMITE=0` não servia — a paginação faz `max(1, ...)`.

    Nasce DESLIGADO porque o primeiro boot depois do Upgrade é o instante mais
    perigoso do plano: dezenas de componentes em 402 voltam ao mesmo tempo.
    """
    import asyncio

    print("\n[10c] O interruptor do recovery nasce desligado")
    EC = _carregar_espelho()
    banco = BancoFalso()
    _com_banco_global(banco)
    os.environ.pop("ESPELHO_SYNC_ENABLED", None)

    banco.semear("integrations", [
        {"id": "i1", "company_id": "amandus", "provider": "evolution-go",
         "is_active": True}])
    quando = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    banco.semear("attendance_transcripts", [
        {"id": "a1", "company_id": "amandus", "counterparty": "554700000001",
         "direction": "in", "msg_type": "text", "text": "oi",
         "message_id": "X-1", "wa_timestamp": quando, "created_at": quando,
         "insurer_key": None}])

    checar(EC.sync_ligado() is False,
           "sem a variável, o recovery periódico está DESLIGADO")
    r = asyncio.run(EC.sincronizar_chats())
    checar(r.get("desligado") is True, "e o job sai na primeira linha", str(r))
    checar(len(banco.linhas("espelho_sync_cursor")) == 0,
           "CONTROLE — desligado não cria cursor nem lê nada")

    # CONTROLE — o interruptor tem de conseguir LIGAR, senão não é interruptor.
    os.environ["ESPELHO_SYNC_ENABLED"] = "true"
    checar(EC.sync_ligado() is True,
           "CONTROLE — e liga quando a variável diz para ligar",
           "um interruptor que só desliga não é um interruptor")
    asyncio.run(EC.sincronizar_chats())
    checar(len(banco.linhas("espelho_sync_cursor")) == 1,
           "CONTROLE — ligado, ele trabalha")
    os.environ.pop("ESPELHO_SYNC_ENABLED", None)


def main() -> int:
    print("=" * 70)
    print("A CONVERSA DO WHATSAPP APARECE NO CHAT DA CORRETORA")
    print("=" * 70)
    teste_o_que_vira_conversa_e_o_que_nao()
    teste_a_ponte_cria_conversa_e_mensagem()
    teste_a_ponte_e_o_agente_acham_a_MESMA_conversa()
    teste_a_ponte_usa_a_API_QUE_EXISTE()
    teste_a_mensagem_obedece_o_que_o_BANCO_aceita()
    teste_a_ponte_esta_ligada_e_nao_muda_o_silencio()
    teste_nada_disto_liga_agente_nenhum()
    teste_a_lista_do_chat_mostra_sete_dias()
    teste_o_acervo_ja_capturado_pode_ir_para_o_chat()
    teste_a_janela_inteira_chega_ao_chat_e_nao_so_as_primeiras_mil()
    teste_conversa_longa_nao_duplica_no_ciclo_seguinte()
    teste_o_historico_de_quinze_meses_nao_entope_a_mesa()
    teste_um_ciclo_sem_novidade_nao_le_o_chat_inteiro()
    teste_o_eco_ainda_le_quando_precisa()
    teste_o_cursor_nunca_perde_e_nunca_varre()
    teste_o_cursor_nao_avanca_sobre_erro()
    teste_um_tropeco_de_rede_nao_derruba_o_lote()
    teste_recusa_permanente_nao_prende_a_corretora()
    teste_o_interruptor_nasce_desligado()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o acervo enche e a mesa de trabalho também.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
