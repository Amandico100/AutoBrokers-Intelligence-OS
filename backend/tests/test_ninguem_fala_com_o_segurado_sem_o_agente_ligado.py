"""Nenhum caminho fala com o segurado sem perguntar se o agente está ligado.

Por que este arquivo existe
----------------------------
O produto tem um modo em que a **atendente humana responde pelo celular** e o
sistema só observa (SPEC-045 / [D23]). Nesse modo o robô não pode dizer uma
palavra ao segurado — ele acha que está falando com uma pessoa, e está.

O portão que garante isso mora no `webhook.py`:

```python
_em_silencio = not await attendance_agent_active(company_id)
if _em_silencio:  ... captura e return
```

**E ele só protege quem passa por ali.** A auditoria de 04/08/2026 encontrou
dois caminhos que não passavam:

🔴 **`webhook.py`, no áudio.** Quando o Whisper falhava, o sistema respondia
*"Erro ao processar áudio."* ao segurado — **115 linhas ANTES do portão**. Áudio
é o formato mais comum de segurado no WhatsApp.
📊 Só não mordia porque a `ATTENDANT_INBOUND_ALLOWLIST` barrava antes. **Uma
trava que depende de outra trava não é trava — é sorte.** No dia em que a
allowlist for esvaziada, que é o dia do go-live, o caminho abriria sozinho.

🟠 **`vigia_do_portal.py`, no mesmo dia em que nasceu.** Ele roda em scheduler,
a cada 60s, e o portão do webhook não passa por lá. Escrito por mim, na mesma
sessão, e encontrado pela auditoria — o que é exatamente o motivo de a auditoria
existir.

A regra que este teste protege
-------------------------------
> **Quem fala com o segurado pergunta antes. Quem fala com a equipe, não.**

A distinção importa: o alerta que vai ao grupo de suporte da corretora DEVE sair
com o agente desligado — é ele que avisa a gente de que algo travou. Um teste
que exigisse a checagem de todo mundo mataria o handoff.

E fail-closed: erro de leitura da permissão = silêncio. Um `except` que deixasse
passar seria pior que não ter portão, porque pareceria protegido.
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

PERMISSAO = "attendance_agent_active"
# Módulos que conseguem alcançar o telefone de um segurado.
VIGIADOS = (
    ("app", "api", "webhook.py"),
    ("app", "tasks", "vigia_do_portal.py"),
    ("app", "tasks", "dispatch_followup.py"),
    ("app", "tasks", "dispatch_watchdog.py"),
)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _arvore(caminho: str) -> ast.Module:
    with open(caminho, encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _chamadas(no: ast.AST) -> list[str]:
    out = []
    for f in ast.walk(no):
        if isinstance(f, ast.Call):
            alvo = f.func
            if isinstance(alvo, ast.Name):
                out.append(alvo.id)
            elif isinstance(alvo, ast.Attribute):
                out.append(alvo.attr)
    return out


def _funcoes(arvore: ast.Module):
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield no


# A DISTINÇÃO QUE FAZ ESTA REGRA SER USÁVEL
# ------------------------------------------
# Nem todo envio precisa do portão, e exigir de todos mataria coisas certas.
# São três destinos diferentes, e só um deles é o segurado sendo abordado:
#
#   INICIA conversa com o segurado   -> PRECISA da permissão. É o robô se
#                                       intrometendo numa conversa que, no modo
#                                       observação, é entre ele e uma pessoa.
#
#   CONTINUA um acionamento em curso -> NÃO precisa, e não pode precisar. O
#                                       acionamento só existe porque o agente
#                                       estava ligado quando ele começou.
#                                       Emudecer no meio deixaria o segurado
#                                       esperando para sempre uma resposta da
#                                       seguradora que já chegou.
#
#   Fala com a SEGURADORA ou a EQUIPE -> NÃO precisa. É o corredor fazendo o
#                                       trabalho, e o handoff avisando a gente.
#                                       Travar isto apagaria justamente o aviso
#                                       de que algo travou.
#
# Cada entrada abaixo é uma isenção com MOTIVO escrito. Um sender novo que não
# esteja aqui reprova — que é o valor deste arquivo. Acrescentar uma linha aqui
# tem de ser uma decisão consciente, não um contorno.
ISENTOS = {
    "webhook.py::admin_send_message":
        "um humano do admin clicou para enviar — a permissão é a dele, não do agente",
    "webhook.py::_send_to_insurer":
        "o destino é a SEGURADORA (a URA), não o segurado",
    "webhook.py::_send_to_client":
        "repassa ao segurado o que a SEGURADORA acabou de responder, dentro de um "
        "acionamento ativo; cortar aqui deixaria a resposta que ele espera no vácuo",
    "dispatch_followup.py::check_dispatch_followups":
        "o 'o guincho chegou?' de um acionamento em curso — mesma razão acima",
    "dispatch_watchdog.py::_sentinela_recover":
        "responde à URA da SEGURADORA quando ela ficou esperando por nós",
    "dispatch_watchdog.py::check_dispatch_watchdog":
        "cutuca o humano da SEGURADORA e alerta a EQUIPE da corretora",
}


def _fala_com_segurado(fn: ast.AST, fonte: str) -> bool:
    """A função manda mensagem para um DESTINO derivado do segurado?"""
    trecho = ast.get_source_segment(fonte, fn) or ""
    if "send_message" not in _chamadas(fn):
        return False
    return any(p in trecho for p in ("payload.phone", "session_id", "sessao",
                                     "para_o_segurado", "phone,"))


# ---------------------------------------------------------------------------

def teste_todo_sender_para_o_segurado_pergunta_antes():
    print("\n[1] Quem fala com o segurado pergunta a permissão antes")
    culpadas: list[str] = []
    verificadas = 0

    isentos_vistos: list[str] = []
    for partes in VIGIADOS:
        caminho = os.path.join(RAIZ, "backend", *partes)
        if not os.path.isfile(caminho):
            continue
        fonte = open(caminho, encoding="utf-8").read()
        arvore = ast.parse(fonte)
        for fn in _funcoes(arvore):
            if not _fala_com_segurado(fn, fonte):
                continue
            verificadas += 1
            chave = f"{partes[-1]}::{fn.name}"
            if chave in ISENTOS:
                isentos_vistos.append(chave)
                continue
            if PERMISSAO not in _chamadas(fn):
                culpadas.append(f"{'/'.join(partes)}::{fn.name}:{fn.lineno}")

    checar(verificadas > 0, "o teste encontrou senders para conferir",
           "zero encontrados significa que o detector parou de enxergar — "
           "e um teste que não olha nada passa sempre")
    checar(not culpadas,
           f"dos {verificadas} senders, os {verificadas - len(isentos_vistos)} que "
           "INICIAM conversa perguntam antes",
           f"não perguntam: {culpadas}")

    # A isenção é uma decisão, não um esconderijo: cada nome na lista tem de
    # existir de verdade. Um isento que sumiu do código vira licença esquecida —
    # e no dia em que alguém criar uma função com aquele nome, ela nasce liberada.
    fantasmas = [c for c in ISENTOS if c not in isentos_vistos]
    checar(not fantasmas, "nenhuma isenção sobrou apontando para função que não existe",
           f"{fantasmas}")


def teste_o_audio_que_falha_nao_responde_sozinho():
    print("\n[2] O áudio que falha não responde por conta própria")
    fonte = open(os.path.join(RAIZ, "backend", "app", "api", "webhook.py"),
                 encoding="utf-8").read()

    # Procura o ENVIO, não a frase. A primeira versão deste guarda achou a
    # ocorrência dentro do comentário que explica o conserto, e reprovou o
    # código por causa da própria documentação — o mesmo erro que já cometi
    # duas vezes hoje. Comentário não envia mensagem; `send_message` envia.
    i = fonte.find('send_message(payload.phone, "Erro ao processar áudio."')
    checar(i > 0, "o caminho do áudio que falha existe",
           "se sumiu, o teste precisa saber por quê antes de ficar verde")
    if i <= 0:
        return

    # A checagem tem de estar ANTES do envio, na mesma vizinhança.
    janela = fonte[max(0, i - 1400):i]
    checar(PERMISSAO in janela,
           "a permissão é consultada ANTES de responder o áudio",
           "era o furo: 115 linhas antes do portão, o sistema falava")
    checar("_pode_falar = False" in janela,
           "e é fail-closed — erro de leitura vira silêncio",
           "um except permissivo é pior que portão nenhum: parece protegido")


def teste_o_que_vai_para_a_equipe_continua_saindo():
    print("\n[3] CONTROLE — o alerta para a EQUIPE não pode ter sido travado junto")
    fonte = open(os.path.join(RAIZ, "backend", "app", "tasks", "vigia_do_portal.py"),
                 encoding="utf-8").read()
    arvore = ast.parse(fonte)
    varrer = next((f for f in _funcoes(arvore) if f.name == "varrer_portal"), None)
    checar(varrer is not None, "a varredura do portal existe")
    if varrer is None:
        return

    trecho = ast.get_source_segment(fonte, varrer) or ""
    i_perm = trecho.find(PERMISSAO)
    i_sup = trecho.find("_support_alert")
    checar(i_sup > 0, "o alerta para a equipe continua existindo")
    checar(i_perm > 0, "e a permissão é consultada")
    # O alerta ao suporte vem DEPOIS e FORA do `if pode_falar` — ele tem de sair
    # justamente quando o agente está mudo, senão ninguém fica sabendo do travamento.
    if i_sup > 0 and i_perm > 0:
        entre = trecho[i_perm:i_sup]
        checar("pode_falar" not in entre.split("_support_alert")[0].split("\n")[-1],
               "o alerta à equipe NÃO está dentro do if de permissão",
               "se estivesse, o travamento ficaria invisível justamente no modo "
               "em que a equipe é quem atende")


def teste_o_detector_consegue_acusar():
    print("\n[4] CONTRAPROVA — o detector reprova um sender sem permissão")

    # Um módulo de mentira que faz exatamente o que o defeito fazia.
    culpado = ast.parse(
        "async def responde(payload, wa, integration):\n"
        "    wa.send_message(payload.phone, 'oi', integration)\n")
    fn = next(_funcoes(culpado))
    fonte = "async def responde(payload, wa, integration):\n    wa.send_message(payload.phone, 'oi', integration)\n"
    checar(_fala_com_segurado(fn, fonte) is True,
           "o detector reconhece um envio ao segurado")
    checar(PERMISSAO not in _chamadas(fn),
           "e vê que ele NÃO pergunta a permissão",
           "prova que o verde do caso [1] vem de o código estar certo")

    # E o inverso: quem só fala com a equipe não é acusado.
    inocente_src = ("async def avisa(company_id, wa, integration):\n"
                    "    await _support_alert(company_id, 'travou', wa, integration)\n")
    fn2 = next(_funcoes(ast.parse(inocente_src)))
    checar(_fala_com_segurado(fn2, inocente_src) is False,
           "e NÃO acusa quem só avisa a equipe",
           "exigir permissão do handoff mataria o handoff")


def main() -> int:
    print("=" * 70)
    print("NINGUEM FALA COM O SEGURADO SEM O AGENTE LIGADO")
    print("=" * 70)
    for teste in (teste_todo_sender_para_o_segurado_pergunta_antes,
                  teste_o_audio_que_falha_nao_responde_sozinho,
                  teste_o_que_vai_para_a_equipe_continua_saindo,
                  teste_o_detector_consegue_acusar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O MODO OBSERVACAO E MUDO DE VERDADE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
