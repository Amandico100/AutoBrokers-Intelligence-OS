"""Devolver para humano só vale se o humano ficar sabendo.

O que a ferramenta fazia, medido em 02/08/2026
----------------------------------------------
Um `UPDATE conversations SET status='HUMAN_REQUESTED'`. Nada mais.

    sem envio         nenhum import de WhatsApp, e-mail ou push
    sem contexto      o humano reconstruiria a conversa sozinho
    sem company_id    `.eq("session_id", …)` — viola CLAUDE.md §7
    e MENTIA          "Um atendente foi solicitado." era devolvido também
                      quando o UPDATE não achava a conversa E quando
                      estourava exceção

A última é a que este teste mais protege. O segurado ouvia que um humano viria,
o humano nunca soube, e ninguém no sistema ficou sabendo que a promessa não foi
cumprida. **Falha declarando sucesso é pior que falha**: apaga o rastro que
levaria alguém a consertar.

E o defeito gêmeo, na direção oposta
------------------------------------
`ATTENDANCE_BASE_PROMPT` MANDA chamar humano em sinistro e em risco grave. Mas
a ferramenta só era anexada se `tools_config.human_handoff.enabled` fosse
verdadeiro — e 📊 `tools_config` estava vazio nos agentes de atendimento.

**O prompt prometia o que a ferramenta não tinha como cumprir.** O modelo dizia
"vou chamar um atendente" e não existia ferramenta para chamar.

E o destino que vazava entre corretoras
---------------------------------------
📊 Resulta e AutoFleet apontavam para o MESMO grupo de WhatsApp. O dossiê leva
nome, telefone e CPF do segurado. A regra é **recusar, não avisar**: um handoff
que não sai é problema operacional de minutos; um CPF na conversa da outra
corretora não se desfaz.
"""

from __future__ import annotations

import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with io.open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_py(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


# ===========================================================================
# O DUBLÊ DE SUPABASE — para chamar o MOTOR, não o texto-fonte dele
# ===========================================================================
#
# 🔴 CLAUDE.md §9.4, aplicado a este arquivo em 09/09/2026.
#
# O guarda [B5] procurava a string `human_support_destinations` DENTRO do
# corpo de `resolver_destino_de_suporte` e comparava a posição dela com a do
# perfil legado. Isso prova que as duas palavras estão escritas na ordem
# certa. Não prova que a corretora B, sem destino, recebe vazio — e foi
# exatamente isso que aconteceu na AutoFleet em 09/09: 5 handoffs sem destino,
# com o guarda verde o tempo todo.
#
# ⚠️ E provar isso pede DOIS tenants de verdade (CLAUDE.md §7): a pergunta
# "A resolve o destino de A?" só tem valor ao lado de "A nunca devolve o de B".
CO_ALFA = "co-alfa-0000-4000-8000-000000000001"     # tem destino
CO_BETA = "co-beta-0000-4000-8000-000000000002"     # NÃO tem — a AutoFleet de 09/09
CO_GAMA = "co-gama-0000-4000-8000-000000000003"     # só destino DESATIVADO
CO_DELTA = "co-delt-0000-4000-8000-000000000004"    # só o perfil legado

GRUPO_DE_ALFA = "120363000000000001@g.us"
GRUPO_SECUNDARIO_DE_ALFA = "120363000000000002@g.us"
GRUPO_DE_GAMA = "120363000000000003@g.us"
LEGADO_DE_ALFA = "5547900000001"                    # 💭 fictício — nunca PII real
LEGADO_DE_DELTA = "5547900000004"


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """Só o que o motor usa: `select/eq/in_/order/limit/execute` — assíncrono."""

    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self._iguais: list = []
        self._dentro: list = []
        self._ordens: list = []
        self._teto = None

    def select(self, *a, **k):
        return self

    def eq(self, campo, valor):
        self._iguais.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self._dentro.append((campo, list(valores)))
        return self

    def order(self, campo, desc=False):
        self._ordens.append((campo, bool(desc)))
        return self

    def limit(self, n):
        self._teto = int(n)
        return self

    async def execute(self):
        self.banco.registro.append((self.tabela, list(self._iguais)))
        if self.tabela in self.banco.falhar:
            raise RuntimeError("FONTE_INDISPONIVEL: %s (dublê)" % self.tabela)
        linhas = [dict(l) for l in (self.banco.mundo.get(self.tabela) or [])]
        for campo, valor in self._iguais:
            linhas = [l for l in linhas if l.get(campo) == valor]
        for campo, valores in self._dentro:
            linhas = [l for l in linhas if l.get(campo) in valores]
        # ⚠️ Em ordem INVERSA e com `sort` estável: é assim que `.order(a).order(b)`
        #    vira "a primeiro, b como desempate" — igual ao PostgREST.
        for campo, desc in reversed(self._ordens):
            linhas.sort(key=lambda l: (l.get(campo) is None, l.get(campo)
                                       if l.get(campo) is not None else 0),
                        reverse=desc)
        if self._teto is not None:
            linhas = linhas[:self._teto]
        return _Resposta(linhas)


class BancoDeDuasCorretoras:
    def __init__(self, mundo=None, falhar=()):
        self.mundo = mundo if mundo is not None else mundo_de_duas_corretoras()
        self.falhar = set(falhar or ())
        self.registro: list = []

    def table(self, nome):
        return _Consulta(self, nome)

    @property
    def client(self):
        return self


def mundo_de_duas_corretoras() -> dict:
    """O mundo medido em 09/09: uma corretora configurada, outra ligada e muda."""
    return {
        "human_support_destinations": [
            # ⚠️ O secundário vem PRIMEIRO na lista de propósito: se o motor não
            #    ordenar por `is_primary`, ele devolve este e o guarda fica vermelho.
            {"company_id": CO_ALFA, "destination_ref": GRUPO_SECUNDARIO_DE_ALFA,
             "is_primary": False, "priority_order": 2, "is_active": True},
            {"company_id": CO_ALFA, "destination_ref": GRUPO_DE_ALFA,
             "is_primary": True, "priority_order": 1, "is_active": True},
            # 🔴 A GAMA tem destino na tela — DESATIVADO. "Inativo" tem de valer.
            {"company_id": CO_GAMA, "destination_ref": GRUPO_DE_GAMA,
             "is_primary": True, "priority_order": 1, "is_active": False},
        ],
        "companies": [
            # 🔴 A ALFA tem os DOIS: a tela e o legado. A tela tem de ganhar.
            {"id": CO_ALFA, "acionamento_profile":
                {"suporte_humano_whatsapp": LEGADO_DE_ALFA}},
            {"id": CO_BETA, "acionamento_profile": {}},
            {"id": CO_GAMA, "acionamento_profile": {}},
            {"id": CO_DELTA, "acionamento_profile":
                {"suporte_humano_whatsapp": LEGADO_DE_DELTA}},
        ],
        "integrations": [],
        "agents": [],
        "agent_activities": [],
    }


def resolver_com_duble(banco, company_id: str) -> dict:
    """Roda o MOTOR real contra o dublê. Devolve `{destino, fonte, recusa}`."""
    import asyncio

    from app.core import database as _db
    from app.services import dispatch_router as DR

    async def _falso_cliente():
        return banco

    original = getattr(_db, "create_async_supabase_client", None)
    _db.create_async_supabase_client = _falso_cliente  # type: ignore[assignment]
    try:
        return asyncio.run(DR.resolver_destino_de_suporte(company_id))
    finally:
        if original is not None:
            _db.create_async_supabase_client = original  # type: ignore[assignment]


def teste_a_falha_nunca_declara_sucesso():
    print("\n[B1] Falha NUNCA devolve promessa de atendente")
    fonte = _ler("backend", "app", "agents", "tools", "human_handoff.py")
    codigo = _sem_comentario_py(fonte)

    # As frases que prometem só podem existir no ramo que REALMENTE avisou.
    depois_do_avisado = codigo.split('if aviso["avisado"]:', 1)
    checar(len(depois_do_avisado) == 2, "existe um ramo explícito para 'foi avisado'")
    if len(depois_do_avisado) != 2:
        return

    antes = depois_do_avisado[0]
    for frase in ("Já chamei um atendente", "entra aqui na conversa"):
        checar(frase not in antes,
               f"'{frase[:28]}…' não aparece antes de provar o aviso",
               "era exatamente o que a versão antiga devolvia no ramo de FALHA")

    # O ramo de conversa-não-encontrada não pode prometer nada.
    trecho_nao_achou = codigo.split("if not conversa:", 1)[-1][:900]
    # 🔴 ASSERCAO ATUALIZADA — SPEC-085 BLOCO B, 24/08/2026.
    #
    # Ela procurava o literal "Nao consegui abrir a transferencia". O ramo hoje
    # devolve `FALHA_DO_HANDOFF`, do `honestidade_do_handoff` — que diz mais e
    # diz melhor: "HANDOFF_FALHOU · ninguem da equipe recebeu este caso. Nada
    # foi enviado." e PROIBE verbo no passado sobre transferir.
    #
    # ⚠️ O comportamento guardado nao regrediu; ele MELHOROU, e o literal virou
    # constante compartilhada. Casar a frase antiga fazia o teste reprovar quem
    # consolidou a mensagem — o contrario do que ele existe para fazer
    # (`CLAUDE.md` §9.3). A licao migra: o ramo tem de ADMITIR a falha, e a
    # forma canonica de admitir e a constante.
    checar("FALHA_DO_HANDOFF" in trecho_nao_achou,
           "conversa não encontrada admite que não conseguiu",
           "tem de devolver FALHA_DO_HANDOFF, que carrega o carimbo negativo")
    checar("HANDOFF_OK" not in trecho_nao_achou,
           "e NAO carimba sucesso no ramo de falha",
           "o carimbo positivo e o que autoriza o agente a prometer humano")
    checar("atendente foi solicitado" not in trecho_nao_achou,
           "e não promete atendente nenhum")


def teste_o_company_id_e_obrigatorio():
    print("\n[B2] A conversa é filtrada por company_id — CLAUDE.md §7")
    fonte = _sem_comentario_py(_ler("backend", "app", "agents", "tools", "human_handoff.py"))
    trecho = fonte.split('.table("conversations")', 1)[-1][:400]
    checar('.eq("company_id", company_id)' in trecho,
           "o UPDATE filtra por company_id")
    checar('.eq("session_id", session_id)' in trecho,
           "e por session_id")
    checar("if not session_id or not company_id:" in fonte,
           "faltando qualquer um dos dois, não escreve nada")

    nodes = _sem_comentario_py(_ler("backend", "app", "agents", "nodes.py"))
    trecho_n = nodes.split('elif tool_name == "request_human_agent":', 1)[-1][:400]
    checar('"company_id": state.get("company_id")' in trecho_n,
           "o tool_node injeta company_id nos argumentos",
           "sem isso a ferramenta nunca receberia o tenant")


def teste_o_humano_e_avisado_com_contexto():
    print("\n[B3] O humano é avisado, e com o caso na mão")
    fonte = _ler("backend", "app", "agents", "tools", "human_handoff.py")
    checar("_avisar_suporte" in fonte, "existe um caminho de aviso")
    # 🔴 ASSERCAO MIGRADA — SPEC-EXTRA-001.3, 16/09/2026.
    #
    # Ela exigia `get_whatsapp_service` DENTRO de `human_handoff.py`, e a razao
    # era boa: 📊 a versao antiga nao tinha um unico import de envio — o caminho
    # de aviso existia e nao enviava nada.
    #
    # O ENVIO MUDOU DE CASA. Agora os 11 pontos saem por UMA porta,
    # `o_grupo_so_o_que_importa.enviar_ao_grupo`, que e onde a guarda, o
    # `bloco_unico`, o marcador e a contagem moram. `_avisar_suporte` virou
    # adaptador: ele MONTA o dossie e chama a porta.
    #
    # ⚠️ CLAUDE.md §9.3: o fato mudou, o teste muda com ele, e a licao MIGRA em
    # vez de morrer — continua sendo "prove que este caminho de fato ENVIA",
    # agora perguntando aos dois elos. Exigir o import antigo aqui so ensinaria
    # a equipe a ignorar o guarda.
    porta = _ler("backend", "app", "services", "o_grupo_so_o_que_importa.py")
    checar("enviar_ao_grupo" in fonte, "que chega na PORTA de envio",
           "sem isso o caminho de aviso volta a nao enviar nada")
    checar("get_whatsapp_service" in porta, "e a porta de fato ENVIA",
           "a porta sem import de envio seria o mesmo defeito, uma casa adiante")
    checar("_montar_dossie" in fonte, "existe um dossiê")
    # 🔴 ASSERCAO ATUALIZADA — SPEC-085 BLOCO B, 24/08/2026.
    #
    # Ela exigia o rotulo "Ultimas mensagens", que o dossie perdeu na reescrita
    # de 14/08 (SPEC-071 Bloco 3.4). Aquela reescrita consertou quatro defeitos
    # nomeados no docstring — faltava link, nao separava a IA de uma colega,
    # nao dizia o que fazer, e nao dizia se alguem ja assumiu.
    #
    # ⚠️ O que o guarda protege e que o dossie LEVE A CONVERSA, nao o rotulo
    # dela. A licao migra para a secao que existe hoje — e ganha a que mais
    # importa, que e a que a reescrita acrescentou.
    for campo in ("user_name", "user_phone", "*CONVERSA*"):
        checar(campo in fonte, f"o dossiê leva {campo}")
    checar("O QUE FAZER" in fonte,
           "e diz o que fazer, nao so o que aconteceu",
           "diretriz do Founder: 'ela olha a mensagem e ja sabe o que fazer'")
    checar("claimed_by_name" in fonte,
           "e diz se alguem JA assumiu",
           "sem isso duas atendentes correm para a mesma conversa")
    checar("Atendimentos → Conversas" in fonte,
           "e diz ao humano onde assumir a conversa")


def teste_destino_compartilhado_e_recusado():
    print("\n[B4] Destino usado por duas corretoras é RECUSADO, não avisado")
    router = _ler("backend", "app", "services", "dispatch_router.py")
    checar("_destino_e_compartilhado" in router, "existe a verificação de exclusividade")
    checar("resolver_destino_de_suporte" in router, "existe UM resolvedor canônico")

    corpo = router.split("async def _destino_e_compartilhado", 1)[-1].split("\nasync def ", 1)[0]
    checar("human_support_destinations" in corpo and "acionamento_profile" in corpo,
           "procura o conflito nas DUAS fontes",
           "olhar só uma deixaria o vazamento passar pela outra")
    checar("return \"não foi possível verificar" in corpo or "nao foi possivel verificar" in corpo,
           "não conseguir PROVAR exclusividade também recusa",
           "fail-closed: dúvida não é permissão para enviar CPF")

    # 🔴 MIGRADA JUNTO — SPEC-EXTRA-001.3, 16/09/2026. Quem consulta o
    # resolvedor (e portanto quem respeita a RECUSA de destino compartilhado)
    # passou a ser a porta unica, para os 11 pontos de uma vez. A pergunta e a
    # mesma; o arquivo em que ela se responde e outro.
    porta = _ler("backend", "app", "services", "o_grupo_so_o_que_importa.py")
    checar('achado.get("recusa")' in porta,
           "a porta respeita a recusa do resolvedor",
           "recusa ignorada = dossie com CPF do segurado no grupo da outra corretora")


def teste_o_resolvedor_le_a_tabela_que_a_ui_grava():
    """🔴 MIGRADO EM 09/09/2026 — de inspecionar texto-fonte para chamar o motor.

    A versão anterior procurava as palavras `human_support_destinations` e
    `acionamento_profile` dentro do corpo da função e comparava a POSIÇÃO
    delas. Ela ficou verde o dia inteiro em que a AutoFleet, com o agente
    ligado, não tinha destino nenhum e 5 pedidos de ajuda humana morreram sem
    ninguém saber. **Um teste que lê o código guarda o código; o que a
    corretora sente é o que o MOTOR devolve** (CLAUDE.md §9.4).

    O que ele passou a provar, com dois tenants reais (CLAUDE.md §7):
    a A resolve o destino da A · a B, sem destino, recebe VAZIO (e não o da A)
    · a tela vence o legado · inativo não vale · e as duas linhas de CONTROLE
    que dão direito à conclusão: uma corretora só com legado resolve pelo
    legado (o dublê não devolve vazio para tudo), e a A e a B não trocam de
    resposta quando a ordem das perguntas inverte.
    """
    print("\n[B5] O resolvedor RESOLVE — motor real, dois tenants, dublê de banco")
    try:
        banco = BancoDeDuasCorretoras()
        alfa = resolver_com_duble(banco, CO_ALFA)
        beta = resolver_com_duble(banco, CO_BETA)
        gama = resolver_com_duble(banco, CO_GAMA)
        delta = resolver_com_duble(banco, CO_DELTA)
    except Exception as exc:  # noqa: BLE001
        checar(False, "o motor roda contra o dublê", f"{type(exc).__name__}: {exc}")
        return

    checar(alfa.get("destino") == GRUPO_DE_ALFA,
           "A corretora COM destino resolve o dela",
           f"veio {alfa!r}")
    checar(alfa.get("fonte") == "human_support_destinations",
           "e pela tabela que a UI grava, não pelo perfil legado",
           "📊 a ALFA tem os dois; a tela tem de ganhar — veio "
           f"{alfa.get('fonte')!r}")
    checar(alfa.get("destino") != GRUPO_SECUNDARIO_DE_ALFA,
           "e é o marcado como PRINCIPAL, não o primeiro da lista",
           "o secundário vem antes no mundo do dublê de propósito")
    checar(alfa.get("recusa") is None, "sem recusa quando o destino é exclusivo")

    # 🔴 O DEFEITO DE 09/09, MEDIDO PELO MOTOR: a AutoFleet respondia VAZIO.
    checar(beta.get("destino") == "",
           "A corretora SEM destino recebe vazio — e é isso que trava o handoff",
           f"veio {beta!r}")
    checar(beta.get("recusa") is None,
           "e vazio não é recusa: são estados diferentes",
           "recusa = destino existe e é compartilhado; vazio = não existe")
    checar(GRUPO_DE_ALFA not in (beta.get("destino") or ""),
           "🔴 §7: a B NUNCA recebe o destino da A",
           "seria dossiê com CPF de segurado no grupo da outra corretora")
    checar(GRUPO_SECUNDARIO_DE_ALFA not in (beta.get("destino") or ""),
           "nem o secundário da A")

    checar(gama.get("destino") == "",
           "destino DESATIVADO não vale — 'desativar' desativa de verdade",
           f"veio {gama!r}")

    # ⚠️ AS LINHAS DE CONTROLE (§9.2): sem elas, um dublê que devolvesse vazio
    #    para tudo faria as asserções da B e da GAMA passarem por engano.
    checar(delta.get("destino") == LEGADO_DE_DELTA
           and delta.get("fonte", "").startswith("acionamento_profile"),
           "CONTROLE: corretora só com legado resolve PELO legado",
           f"veio {delta!r} — se este vier vazio, o dublê é que está mudo")
    banco2 = BancoDeDuasCorretoras()
    beta2 = resolver_com_duble(banco2, CO_BETA)
    alfa2 = resolver_com_duble(banco2, CO_ALFA)
    checar(beta2.get("destino") == "" and alfa2.get("destino") == GRUPO_DE_ALFA,
           "CONTROLE: invertida a ordem das perguntas, as respostas não trocam",
           f"beta={beta2!r} alfa={alfa2!r}")

    # E o fail-closed: não conseguir PROVAR exclusividade não é permissão.
    quebrado = BancoDeDuasCorretoras(falhar=("companies",))
    alfa_cego = resolver_com_duble(quebrado, CO_ALFA)
    checar(alfa_cego.get("destino") == "" and alfa_cego.get("recusa"),
           "consulta que falha RECUSA — dúvida não é permissão para enviar CPF",
           f"veio {alfa_cego!r}")


def teste_o_prompt_nao_promete_o_que_a_ferramenta_nao_tem():
    print("\n[B6] Quem fala com o segurado SEMPRE tem a ferramenta de humano")
    graph = _ler("backend", "app", "agents", "graph.py")
    checar('str(_agent_role or "").lower() in ("attendance", "insured_external")' in graph,
           "o papel de atendimento liga o handoff por si só")
    trecho = graph.split("if not allow_human_handoff and str(_agent_role", 1)[-1][:400]
    checar("allow_human_handoff = True" in trecho,
           "e liga de verdade, não só loga",
           "📊 tools_config = {} nos agentes de atendimento — o prompt manda "
           "chamar humano e não havia ferramenta")

    prompts = _ler("backend", "app", "core", "prompts.py")
    promete = any(p in prompts for p in ("atendente humano", "chamar humano",
                                         "request_human_agent", "humano"))
    checar(promete, "o prompt de atendimento realmente promete humano",
           "se parasse de prometer, esta trava perderia o sentido")


def teste_o_caminho_sincrono_nao_finge():
    print("\n[B7] Não existe atalho síncrono que só marca e não avisa")
    fonte = _ler("backend", "app", "agents", "tools", "human_handoff.py")
    corpo = fonte.split("    def _run(", 1)[-1]
    checar("raise RuntimeError" in corpo,
           "_run recusa em vez de fazer meio trabalho",
           "uma versão síncrona que só marcasse seria o defeito de volta")


def main() -> int:
    print("=" * 68)
    print("O HANDOFF CHEGA EM ALGUEM — E NUNCA MENTE QUE CHEGOU")
    print("=" * 68)
    for teste in (teste_a_falha_nunca_declara_sucesso,
                  teste_o_company_id_e_obrigatorio,
                  teste_o_humano_e_avisado_com_contexto,
                  teste_destino_compartilhado_e_recusado,
                  teste_o_resolvedor_le_a_tabela_que_a_ui_grava,
                  teste_o_prompt_nao_promete_o_que_a_ferramenta_nao_tem,
                  teste_o_caminho_sincrono_nao_finge):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O HANDOFF CHEGA, COM CONTEXTO, NO DESTINO CERTO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
