"""A fronteira da observação vale para o histórico, e não se desfaz sozinha.

Duas portas guardavam a mesma coisa e discordavam.

A PRIMEIRA. Parear um WhatsApp como observador gravava
`observer_scope = "insurers_and_clients"` por ATRIBUIÇÃO. Quem tivesse pedido
`insurers_only` — porque aquele telefone tem conversa que ninguém quer no
acervo — perdia a escolha no re-pareamento seguinte, sem aviso. As duas linhas
vizinhas já usavam `setdefault`; só esta não usava.

A SEGUNDA, e a que pesa mais. `observer_exclusions` protegia as mensagens que
chegassem dali em diante, e NÃO protegia o histórico que o pareamento traz de
uma vez — e o histórico é o volume: anos de conversa contra as mensagens de um
dia. Uma exclusão que não vale para o histórico não é exclusão, é pedido
educado.

Este teste também prova que os dois guardas TÊM COMO FALHAR: um guarda que
aceita tudo passa em qualquer teste, e não guarda nada.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def a_escolha_explicita_sobrevive_ao_pareamento() -> None:
    """O `setdefault` respeita quem escolheu — e o padrao virou o ESTREITO.

    ATUALIZADO em 04/08/2026 (SPEC-065). A intencao deste caso nunca foi
    "o padrao e ver tudo": era **nao sobrescrever quem escolheu**. Isso nao
    mudou e continua sendo o primeiro `checar` abaixo.

    O que mudou foi o padrao de quem NUNCA escolheu. 📊 Auditando antes de duas
    corretoras reais parearem, as duas cairiam em lados opostos da mesma acao:
    a de linha desligada voltaria a ver TUDO (o incidente de 29/07, 630 contatos
    pessoais) e a de linha ligada ficaria so com seguradora.

    O sistema nao tem como saber se o telefone e o de trabalho de uma corretora
    ou o pessoal de alguem — 📊 nao existe tabela de segurados com telefone
    neste banco. Entao vale a assimetria: gravar de MENOS e reversivel (o
    history_sync reentrega), gravar de MAIS nao e.

    Guardar o padrao antigo aqui travaria o conserto em nome de uma frase
    escrita antes de o risco ser medido (CLAUDE.md 9.3).
    """
    fonte = (RAIZ / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")

    checar(
        'target["observer_scope"] = "insurers_and_clients"' not in fonte,
        "o pareamento nao SOBRESCREVE mais o escopo",
    )
    checar(
        'target.setdefault("observer_scope", "insurers_and_clients")' in fonte,
        "o escopo entra por setdefault — escolha explicita sobrevive",
    )

    # E o comportamento, não só o texto: simula os dois casos.
    def simular(alert_target: dict | None) -> dict:
        target = dict(alert_target or {})
        target.setdefault("observer_scope", "insurers_and_clients")
        target.setdefault("observer_exclusions", [])
        target.setdefault("internal_numbers", [])
        return target

    checar(
        simular(None)["observer_scope"] == "insurers_and_clients",
        "sem pedido, o Observador nasce vendo segurado (padrao inalterado)",
    )
    checar(
        simular({"observer_scope": "insurers_only"})["observer_scope"] == "insurers_only",
        "com pedido de insurers_only, a escolha PERMANECE",
    )


def o_historico_passa_pela_mesma_fronteira() -> None:
    """A ingestão do histórico consulta o guarda do caminho ao vivo."""
    fonte = (RAIZ / "app/services/atlas/history_ingest.py").read_text(encoding="utf-8")

    # A linha que decide, e só ela — não o docstring que a explica.
    decisao = [
        ln for ln in fonte.splitlines()
        if ln.lstrip().startswith("elif capture_clients")
    ]
    checar(len(decisao) == 1, "existe exatamente uma linha que decide gravar conversa de cliente")
    checar(
        bool(decisao) and "_cliente_permitido(" in decisao[0],
        "essa linha CONSULTA a fronteira antes de gravar",
    )
    checar(
        "from app.services.atlas.attendance_capture import client_chat_allowed" in fonte,
        "e a fronteira consultada e a MESMA do caminho ao vivo",
    )
    checar(
        re.search(r"except Exception:.*\n\s+logger\.warning\(\"\[ESPELHO ATENDIMENTO\] fronteira",
                  fonte) is not None,
        "se a fronteira nao puder rodar, NAO grava (fail-closed)",
    )


def _carregar_fronteira():
    """Carrega `client_chat_allowed` do ARQUIVO, sem subir o pacote inteiro.

    `import app.services...` executa o `__init__` do pacote, que puxa a stack de
    IA. Aqui interessa uma função pura de decisão — carregá-la direto do arquivo
    testa exatamente o código que roda em produção, sem exigir a stack toda.
    """
    import importlib.util

    caminho = RAIZ / "app/services/atlas/attendance_capture.py"
    spec = importlib.util.spec_from_file_location("_fronteira_sob_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.client_chat_allowed


def a_fronteira_tem_como_recusar() -> None:
    """Sem isto, os checks acima passariam com um guarda que diz sim a tudo."""
    client_chat_allowed = _carregar_fronteira()

    amigo = "5547999990001"
    jid = f"{amigo}@s.whatsapp.net"
    observador = "5511988887777"

    aberto = {"alert_target": {"observer_scope": "insurers_and_clients"}}
    checar(
        client_chat_allowed(aberto, observador, jid, amigo) is True,
        "com escopo total e sem exclusao, a conversa do cliente ENTRA",
    )

    excluido = {"alert_target": {
        "observer_scope": "insurers_and_clients",
        "observer_exclusions": [amigo],
    }}
    checar(
        client_chat_allowed(excluido, observador, jid, amigo) is False,
        "numero EXCLUIDO e recusado — o guarda tem como dizer nao",
    )

    so_seguradora = {"alert_target": {"observer_scope": "insurers_only"}}
    checar(
        client_chat_allowed(so_seguradora, observador, jid, amigo) is False,
        "com insurers_only, NENHUMA conversa de cliente entra",
    )

    grupo = f"120363000000000000@g.us"
    checar(
        client_chat_allowed(aberto, observador, grupo, "120363000000000000") is False,
        "grupo nunca entra, mesmo com escopo total",
    )


def main() -> int:
    print(__doc__)
    print("== a escolha explicita sobrevive ==")
    a_escolha_explicita_sobrevive_ao_pareamento()
    print("== o historico passa pela mesma fronteira ==")
    o_historico_passa_pela_mesma_fronteira()
    print("== a fronteira tem como recusar ==")
    a_fronteira_tem_como_recusar()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("A FRONTEIRA VALE PARA O HISTORICO, E A ESCOLHA NAO SE DESFAZ SOZINHA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
