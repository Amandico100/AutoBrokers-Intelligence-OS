"""O Observador trabalha em silêncio — e o silêncio não depende de nada dar certo.

O cenário real (27/07/2026)
---------------------------
A corretora vai parear o WhatsApp **de produção** dela. O número é o mesmo em
que a Saionara (Resulta) e a Regina (AutoFleet) atendem segurados de verdade
todos os dias. Elas continuam trabalhando normalmente; o sistema observa em
silêncio por sete dias, monta o Atlas, as rotas e os mapas de URA. Só depois se
decide se o agente de atendimento pode ser ligado.

Nesse arranjo, os dois erros possíveis não têm o mesmo tamanho:

    responder sem poder   um segurado real recebe resposta de robô que ninguém
                          autorizou, no número da corretora. Não se desfaz, e
                          não há mensagem de desculpa que conserte.

    calar sem precisar    a atendente humana responde, como faz hoje.
                          Custa alguns minutos.

O que este teste protege
------------------------
Que **nenhuma falha técnica vire uma resposta**. Redis fora do ar, banco lento,
gravação do transcript com erro — nada disso pode terminar com o agente
falando. Silêncio é o estado seguro, e o código tem de cair para ele.

Havia três caminhos em que uma falha terminava em resposta. Todos vinham da
época em que o agente ligado era o normal e a observação, a exceção — e o
comentário no código dizia isso com todas as letras: *"na dúvida, fluxo
normal"*. Hoje é o contrário.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


def _corpo_da_funcao(fonte: str, assinatura: str) -> str:
    i = fonte.find(assinatura)
    if i == -1:
        return ""
    resto = fonte[i + len(assinatura):]
    fim = re.search(r"\n(async def |def |class )", resto)
    return resto[: fim.start()] if fim else resto


def teste_nao_ler_o_estado_do_agente_e_silencio():
    print("\n[1] Não conseguir LER o estado do agente vira SILÊNCIO")
    fonte = _sem_comentario(_ler("app", "services", "atlas", "attendance_capture.py"))
    corpo = _corpo_da_funcao(fonte, "async def attendance_observation_mode")
    checar(bool(corpo), "a função existe")

    # O `except` que envolve a consulta ao banco tem de devolver True
    # (silêncio). A janela é o trecho entre o `except` e o próximo `try`.
    i = corpo.find("await asyncio.to_thread(_query)")
    checar(i != -1, "a consulta ao banco está no lugar esperado")
    janela = corpo[i:]
    j = janela.find("except")
    janela = janela[j: j + 600] if j != -1 else ""
    k = janela.find("\n    try:")
    janela = janela[:k] if k != -1 else janela

    checar("return True" in janela,
           "falha ao consultar o banco devolve SILÊNCIO",
           "devolver False aqui é dizer 'na dúvida, pode falar'")
    checar("return False" not in janela,
           "e não devolve 'pode responder'",
           janela.strip()[:120])


def teste_o_portao_indisponivel_e_silencio():
    print("\n[2] Portão indisponível no webhook vira SILÊNCIO")
    fonte = _sem_comentario(_ler("app", "api", "webhook.py"))
    checar("_em_silencio = True" in fonte,
           "o webhook assume silêncio quando não consegue perguntar",
           "sem isto, uma exceção cai no fluxo de IA e o agente responde")
    # A frase que marcava o comportamento antigo não pode voltar.
    checar("na dúvida, fluxo normal" not in _ler("app", "api", "webhook.py"),
           "o comentário 'na dúvida, fluxo normal' não existe mais",
           "ele descrevia exatamente o defeito")


def teste_falha_de_captura_nao_libera_a_resposta():
    print("\n[3] Falhar ao GRAVAR não vira permissão para FALAR")
    # Era um `try` só: decidir e gravar juntos. Se a gravação do transcript
    # falhasse, o `except` engolia e o código seguia para o fluxo de IA — o
    # agente respondia um segurado porque o disco engasgou.
    fonte = _sem_comentario(_ler("app", "api", "webhook.py"))
    i = fonte.find("_em_silencio")
    checar(i != -1, "o bloco de observação existe")
    if i == -1:
        return
    bloco = fonte[i: i + 2200]

    pos_captura = bloco.find("capture_channel_message")
    pos_return = bloco.find("\n            return", pos_captura if pos_captura > 0 else 0)
    checar(pos_captura != -1 and pos_return != -1 and pos_return > pos_captura,
           "o `return` vem DEPOIS da captura e fora do try dela",
           "se o return morasse dentro do try, uma falha na gravação "
           "continuaria caindo no fluxo de IA")

    # Decidir e gravar precisam ser dois blocos, não um.
    checar(bloco.count("try:") >= 2,
           "decidir e gravar são blocos separados",
           "um try só faz duas falhas diferentes terminarem no mesmo lugar errado")


def teste_o_observador_e_mudo_por_construcao():
    print("\n[4] O Observador não tem como falar — é ausência de código")
    # A garantia mais forte não é uma flag: é não existir caminho de envio.
    for arq in ("observer_intake.py", "attendance_capture.py", "weaver.py",
                "history_ingest.py", "templater.py", "atlas_parser.py"):
        fonte = _sem_comentario(_ler("app", "services", "atlas", arq))
        envios = re.findall(
            r"\b(send_message|send_text|sendText|enviar_mensagem|start_live_dispatch)\s*\(",
            fonte)
        checar(not envios, f"{arq} não chama nenhum envio", str(set(envios)))


def teste_o_silencio_nao_depende_do_pareamento():
    print("\n[5] O silêncio vem do NASCIMENTO, não do pareamento")
    # Este caso já cobrou o oposto: que o pareamento desligasse o agente. A
    # intenção era boa e o efeito colateral era grave — **re-parear desligava um
    # agente que estava trabalhando**. E re-parear não é raro: telefone
    # desligado, logout, QR vencido, troca de aparelho. A corretora reconectava
    # e o agente ficava mudo sem aviso, com o painel dizendo "Observando em
    # silêncio" e ninguém entendendo o clique que faltava.
    #
    # Decisão do Founder (27/07/2026): "O AGENTE DE ATENDIMENTO NASCE
    # DESLIGADO. ELE SÓ É LIGADO SE CLICAR NO BOTÃO DEPOIS DE PAREADO."
    #
    # O silêncio de uma corretora nova passa a vir de onde deveria ter vindo
    # desde o começo: do nascimento do agente, em dois lugares independentes.
    fonte = _sem_comentario(_ler("app", "services", "whatsapp",
                                 "pairing_orchestrator.py"))
    checar(re.search(r'table\("agents"\)\.update\(\{"is_active"', fonte) is None,
           "o pareamento não mexe no estado do agente",
           "re-parear silenciaria um agente em produção")

    # Garantia 1 — o blueprint.
    caminho_bp = os.path.join(os.path.dirname(RAIZ), "lib", "admin",
                              "agent-blueprints-canonical.ts")
    with open(caminho_bp, encoding="utf-8") as fh:
        bp = fh.read()
    i = bp.find("export const EVEN_ATTENDANCE_BLUEPRINT")
    j = bp.find("export const ", i + 10) if i != -1 else -1
    atendimento = bp[i: j if j != -1 else len(bp)] if i != -1 else ""
    checar("default_active: false" in atendimento,
           "o blueprint do atendimento nasce inativo")

    # Garantia 2 — o banco, para qualquer caminho que não passe pelo blueprint.
    mig = os.path.join(RAIZ, "supabase", "migrations",
                       "20260727_08_atendimento_nasce_desligado.sql")
    checar(os.path.exists(mig), "há gatilho no banco cobrindo os outros caminhos",
           "a coluna is_active tem default true: sem gatilho, um insert "
           "direto criaria um agente LIGADO")


def teste_o_pareamento_liga_a_captura_de_clientes():
    print("\n[6] Parear liga a captura das conversas com SEGURADOS")
    # O default de `observer_scope` é `insurers_only`. Se o pareamento não
    # subisse para `insurers_and_clients`, o sistema observaria sete dias e não
    # teria NENHUMA conversa de atendimento para o agente aprender — o motivo
    # de todo o exercício.
    fonte = _sem_comentario(_ler("app", "services", "whatsapp",
                                 "pairing_orchestrator.py"))
    checar('"insurers_and_clients"' in fonte,
           "o pareamento sobe o escopo para seguradoras E clientes",
           "com o default, sete dias de observação renderiam zero conversa "
           "de atendimento")


def teste_o_cartografo_nao_explora_sozinho():
    print("\n[7] O Cartógrafo não sai mandando mensagem por conta própria")
    # `handle_cartographer_inbound` PODE enviar. Ele só age quando existe uma
    # exploração ativa — e exploração só nasce por ação do Admin.
    base = os.path.join(RAIZ, "app")
    chamadores: list[str] = []
    for pasta, _, arquivos in os.walk(base):
        for arq in arquivos:
            if not arq.endswith(".py"):
                continue
            caminho = os.path.join(pasta, arq)
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            if rel.endswith("services/cartographer_runner.py"):
                continue
            with open(caminho, encoding="utf-8") as fh:
                if re.search(r"\bstart_exploration\s*\(", _sem_comentario(fh.read())):
                    chamadores.append(rel)
    # Só a superfície de Admin pode iniciar. Nenhum worker, nenhum scheduler.
    indevidos = [c for c in chamadores if "/api/admin" not in c]
    checar(not indevidos,
           "só o Admin inicia exploração do Cartógrafo",
           f"iniciam também: {indevidos}")
    print(f"      quem inicia: {chamadores or '(ninguém)'}")


def main() -> int:
    print("=" * 68)
    print("O OBSERVADOR TRABALHA EM SILÊNCIO — MESMO QUANDO ALGO FALHA")
    print("=" * 68)
    for teste in (teste_nao_ler_o_estado_do_agente_e_silencio,
                  teste_o_portao_indisponivel_e_silencio,
                  teste_falha_de_captura_nao_libera_a_resposta,
                  teste_o_observador_e_mudo_por_construcao,
                  teste_o_silencio_nao_depende_do_pareamento,
                  teste_o_pareamento_liga_a_captura_de_clientes,
                  teste_o_cartografo_nao_explora_sozinho):
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
    print("NENHUMA FALHA TÉCNICA VIRA UMA RESPOSTA AO SEGURADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
