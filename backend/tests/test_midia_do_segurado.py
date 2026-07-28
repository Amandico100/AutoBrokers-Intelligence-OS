"""O agente precisa VER a mídia — e ninguém transcreve 9.002 sem mandar.\n\nO que foi medido em 28/07/2026\n------------------------------\nNenhum áudio, foto ou documento do Espelho foi lido. Nem um:\n\n    document 3.572   image 2.685   audio 2.631   video 114     = 9.002\n\n    9.002 do history_sync ... nunca entraram na fila\n       23 ao vivo .......... tentaram e falharam, TODAS\n\nEm seguro isso é caro de um jeito que não aparece: o áudio é onde o cliente\nexplica o sinistro, e o documento é a apólice.\n\nDuas descobertas mudaram o desenho\n----------------------------------\n**1. São dois wires, não um.** O Swagger do próprio fork\n(`/swagger/doc.json`) mostra `POST /message/downloadmedia` com corpo\n`{message: waE2E.Message}`, e responde 404 em `/chat/getBase64FromMediaMessage`\n— que é o wire do Baileys. O caminho do Evolution GO no webhook estava\nmarcado "shape a confirmar" e devolvia `None`: com o agente ligado, toda foto\ndo segurado seria invisível.\n\n**2. A mídia antiga só existe durante o sync.** O download exige o\n`waE2E.Message` inteiro — `mediaKey`, `directPath`, `fileEncSha256` — e nada\ndisso é gravado. `media_meta` guarda tipo, nome e legenda. Depois que a\ningestão retorna, aquela foto é inalcançável para sempre.\n\nPor isso o orçamento existe\n---------------------------\n> Founder, 28/07/2026: "NÃO FAÇA A ANÁLISE DAS 9565 MÍDIAS VIA API NUNCA.
>  APENAS AS 20 QUE VC FALOU."\n\nQuem autoriza é o Admin; quem gasta é o webhook do sync, que chega depois e\nvárias vezes. O contador é um `DECR` no Redis: sem crédito aberto ele devolve\n-1, e a recusa sai de graça do próprio Redis.\n"""

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


def _ler(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _so_codigo(fonte: str) -> str:
    aspas3 = chr(34) * 3
    sem_doc = re.sub(aspas3 + r"(?:.|\n)*?" + aspas3, "", fonte)
    return "\n".join(l for l in sem_doc.split("\n") if not l.lstrip().startswith("#"))


def _funcao(fonte: str, nome: str) -> str:
    i = fonte.find(f"def {nome}")
    if i < 0:
        return ""
    resto = fonte[i:]
    prox = re.search(r"\n(?:async\s+)?def\s", resto[1:])
    return resto[:prox.start() + 1] if prox else resto


def teste_o_orcamento_nasce_fechado():
    print("\n[1] Sem alguém mandar, nenhuma mídia é transcrita")
    fonte = _so_codigo(_ler("app", "services", "atlas", "observer_media.py"))
    gasto = _funcao(fonte, "_pode_gastar_midia")
    checar(bool(gasto), "existe a função que consome o orçamento")
    checar("decr(" in gasto,
           "o consumo é um DECR atômico",
           "ler-e-depois-gravar deixaria duas ingestões simultâneas gastarem "
           "o mesmo crédito")
    checar(">= 0" in gasto,
           "e só gasta quando o crédito ainda era positivo")
    checar("return False" in gasto,
           "Redis fora do ar = nada é gasto",
           "falha ABERTA aqui viraria conta de transcrição sem autorização")


def teste_abrir_o_orcamento_e_ato_humano_e_limitado():
    print("\n[2] Abrir o crédito é ato humano, e tem teto")
    fonte = _so_codigo(_ler("app", "services", "atlas", "observer_media.py"))
    abrir = _funcao(fonte, "abrir_orcamento_de_midia")
    checar(bool(abrir), "existe a função que autoriza")
    checar("min(" in abrir and "500" in abrir,
           "um pedido absurdo é aparado", "digitar 9000 por engano não pode "
           "disparar 9.000 transcrições")
    checar("ex=" in abrir, "o crédito expira sozinho",
           "crédito esquecido aberto é o mesmo que não ter teto")
    checar("delete(" in abrir, "e pedir zero FECHA o crédito")

    rota = _so_codigo(_ler("app", "api", "admin_atlas.py"))
    checar("media-budget" in rota, "a rota do Admin existe")
    i = rota.find("media-budget")
    checar("require_master_admin" in rota[i:i + 700],
           "e só a plataforma abre o crédito")


def teste_a_ingestao_so_enfileira_com_credito():
    print("\n[3] A ingestão não enfileira mídia por conta própria")
    hist = _so_codigo(_ler("app", "services", "atlas", "history_ingest.py"))
    checar("enqueue_observer_media" in hist,
           "a ingestão do histórico oferece a mídia à fila")
    checar("_pode_gastar_midia" not in hist,
           "e NÃO checa o orçamento por conta própria",
           "checar aqui e na fila gastaria dois créditos por mídia: "
           "o teto de 20 viraria 10")


def teste_o_agente_enxerga_a_midia_no_wire_certo():
    print("\n[4] São dois wires — confundir é ficar cego")
    fonte = _so_codigo(_ler("app", "api", "webhook.py"))
    f = _funcao(fonte, "_download_evolution_media")
    checar(bool(f), "a função de download existe")
    checar("raw_message" in f,
           "o caminho do GO recebe a mensagem crua",
           "`/message/downloadmedia` exige o waE2E inteiro; só o id é o wire "
           "do Baileys, e o fork responde 404 nele")
    checar("_download_media" in f,
           "e reusa o download do Observador — um motor só")
    checar("return None" not in f.split("evolution-go")[1].split("if not raw_message")[0]
           if "evolution-go" in f and "if not raw_message" in f else False,
           "o GO não devolve None antes de tentar",
           "era o que fazia toda foto do segurado sumir com o agente ligado")
    checar("getBase64FromMediaMessage" in f,
           "o wire do Baileys continua para quem é Baileys")

    normaliza = _so_codigo(_ler("app", "services", "whatsapp", "evolution_inbound.py"))
    checar('"raw_message"' in normaliza, "o inbound passa a carregar a mensagem crua")


def teste_a_mensagem_crua_nunca_e_gravada():
    print("\n[5] A mensagem crua é do cliente — não fica guardada")
    # Ela traz o conteúdo inteiro e as chaves de mídia. Serve para UMA chamada
    # de download, em memória, e acaba ali.
    webhook = _so_codigo(_ler("app", "api", "webhook.py"))
    for perigo in ("insert(normalized", "json.dumps(normalized",
                   'record["raw_message"]', '"raw_message": normalized'):
        checar(perigo not in webhook, f"o webhook não persiste `{perigo}...`")

    hist = _so_codigo(_ler("app", "services", "atlas", "history_ingest.py"))
    i = hist.find("record = {")
    registro = hist[i:i + 700] if i >= 0 else ""
    checar("raw" not in registro and "msg," not in registro.replace("msg_type", ""),
           "o registro gravado no banco não leva a mensagem crua",
           registro[:120])
    checar('"media_meta": media_meta' in registro,
           "guarda só o metadado (tipo, nome, legenda)")


def teste_observacao_nao_transcreve_sozinha():
    print("\n[6] Agente desligado não gasta dinheiro com mídia")
    # Consertar o download ligaria a transcrição automática de toda foto e
    # todo áudio que chegasse — para sempre, sem ninguém pedir. Nos caminhos
    # de OBSERVAÇÃO ninguém está esperando resposta: o agente está desligado
    # e a mídia só está sendo arquivada.
    #
    # Quando o agente está LIGADO é outro caso: o webhook baixa, descreve e
    # responde na mesma requisição, e não passa por esta fila. Aí gastar é o
    # serviço sendo prestado.
    midia = _so_codigo(_ler("app", "services", "atlas", "observer_media.py"))
    fila = _funcao(midia, "enqueue_observer_media")
    checar("_pode_gastar_midia()" in fila,
           "a fila de observação passa pelo orçamento",
           "sem isso, cada mídia recebida vira transcrição paga")
    checar("return False" in fila.split("_pode_gastar_midia()")[1][:80],
           "e sem crédito ela apenas ARQUIVA, sem ler")

    # A trava tem de estar num lugar SÓ. Checar na ingestão e na fila gastaria
    # dois créditos por mídia, e o teto de 20 viraria 10.
    hist = _so_codigo(_ler("app", "services", "atlas", "history_ingest.py"))
    checar("_pode_gastar_midia" not in hist,
           "a ingestão não checa de novo",
           "duas checagens = dois créditos por mídia")
    checar("enqueue_observer_media" in hist,
           "ela continua enfileirando; quem decide é o portão")

    # E o portão vale para TODOS os caminhos de observação.
    for arq in ("attendance_capture.py", "observer_intake.py"):
        f = _so_codigo(_ler("app", "services", "atlas", arq))
        if "enqueue_observer_media" in f:
            checar("_pode_gastar_midia" not in f,
                   f"{arq} também confia no portão único")


def main() -> int:
    print("=" * 70)
    print("O AGENTE VÊ A MÍDIA; NINGUÉM TRANSCREVE 9.002 SEM MANDAR")
    print("=" * 70)
    for teste in (teste_o_orcamento_nasce_fechado,
                  teste_abrir_o_orcamento_e_ato_humano_e_limitado,
                  teste_a_ingestao_so_enfileira_com_credito,
                  teste_o_agente_enxerga_a_midia_no_wire_certo,
                  teste_a_mensagem_crua_nunca_e_gravada,
                  teste_observacao_nao_transcreve_sozinha):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("MÍDIA LIDA QUANDO PRECISA, E SÓ QUANDO ALGUÉM AUTORIZA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
