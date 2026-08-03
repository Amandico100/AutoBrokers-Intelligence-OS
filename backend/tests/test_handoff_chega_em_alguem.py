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
    checar("Não consegui abrir a transferência" in trecho_nao_achou,
           "conversa não encontrada admite que não conseguiu")
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
    checar("get_whatsapp_service" in fonte, "que de fato ENVIA",
           "a versão antiga não tinha um único import de envio")
    checar("_montar_dossie" in fonte, "existe um dossiê")
    for campo in ("user_name", "user_phone", "Motivo", "Últimas mensagens"):
        checar(campo in fonte, f"o dossiê leva {campo}")
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

    tool = _ler("backend", "app", "agents", "tools", "human_handoff.py")
    checar('alvo.get("recusa")' in tool, "a ferramenta respeita a recusa do resolvedor")


def teste_o_resolvedor_le_a_tabela_que_a_ui_grava():
    print("\n[B5] O backend lê a tabela onde a UI grava")
    router = _ler("backend", "app", "services", "dispatch_router.py")
    corpo = router.split("async def resolver_destino_de_suporte", 1)[-1].split("\nasync def ", 1)[0]

    pos_tabela = corpo.find("human_support_destinations")
    pos_legado = corpo.find("acionamento_profile")
    checar(pos_tabela != -1, "lê human_support_destinations",
           "📊 esta tabela não aparecia UMA VEZ em backend/app/")
    checar(pos_tabela != -1 and pos_legado != -1 and pos_tabela < pos_legado,
           "e ela vem ANTES do perfil legado",
           "a corretora configura na tela; a tela tem de ganhar")
    checar('.eq("is_active", True)' in corpo, "só destino ativo")
    checar('.order("is_primary", desc=True)' in corpo,
           "respeita o destino marcado como principal")


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
