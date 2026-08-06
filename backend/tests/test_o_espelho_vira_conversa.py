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


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Um Supabase de mentira, com o mínimo que a ponte usa. Existe para o teste
# rodar sem rede e sem banco — teste que não roda não protege ninguém.
# --------------------------------------------------------------------------
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

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limite = n
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
        return True

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        if self._insert is not None:
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
        if self._limite:
            achadas = achadas[: self._limite]
        return _Resposta(achadas)


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

        falso.integration_service = _Servico()
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

    from app.services.integration_service import integration_service

    usuario_do_pipeline = integration_service.get_or_create_user(
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


def teste_a_ponte_esta_ligada_e_nao_muda_o_silencio():
    print("\n[4] Ligada ao Observador — e o silêncio intacto")
    cmd = _comandos("backend/app/services/atlas/observer_intake.py")

    checar("espelhar_no_chat(" in cmd, "o tap chama a ponte")
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


def main() -> int:
    print("=" * 70)
    print("A CONVERSA DO WHATSAPP APARECE NO CHAT DA CORRETORA")
    print("=" * 70)
    teste_o_que_vira_conversa_e_o_que_nao()
    teste_a_ponte_cria_conversa_e_mensagem()
    teste_a_ponte_e_o_agente_acham_a_MESMA_conversa()
    teste_a_ponte_esta_ligada_e_nao_muda_o_silencio()
    teste_nada_disto_liga_agente_nenhum()
    teste_a_lista_do_chat_mostra_sete_dias()

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
