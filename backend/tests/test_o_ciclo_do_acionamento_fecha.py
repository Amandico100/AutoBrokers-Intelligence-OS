"""O ciclo do acionamento fecha: avisa, deixa rastro, e encerra.

📊 03/08/2026. A auditoria de ponta a ponta mostrou que a corrente existia
inteira e arrebentava em seis pontos. Este teste guarda os que foram fechados.

**R1** — o segurado só era avisado com protocolo E (agendamento OU eta OU link).
O residencial da Allianz não captura eta nem link: protocolo sem agendamento
reconhecido significava que a pessoa com um cano estourando **nunca sabia** que
o serviço tinha sido aberto.

**R2** — e sem "capturado", a retomada automática **reabria um serviço já
aberto**. Dois guinchos para o mesmo carro.

**R5b** — a lista branca do repasse só deixava passar boa notícia. *"Não
encontramos prestador na sua região"* era engolido em silêncio.

**R4** — o motor falava com o cliente e não deixava rastro. O agente podia
prometer o protocolo que já fora entregue dois minutos antes.

**R5** — ninguém fechava. Depois do encerramento a sessão ficava viva até o TTL
de 24h, e o Vigia é cego a `monitoring`.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def _carregar(rel: str, nome: str):
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    for pkg in ("app", "app.services", "app.tasks"):
        if pkg not in sys.modules:
            casca = types.ModuleType(pkg)
            casca.__path__ = [str(RAIZ / pkg.replace(".", "/"))]  # type: ignore[attr-defined]
            sys.modules[pkg] = casca
    spec = importlib.util.spec_from_file_location(nome, RAIZ / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def r1_o_protocolo_sozinho_ja_avisa() -> None:
    fonte = (RAIZ / "app/services/insurer_dispatch_service.py").read_text(encoding="utf-8")
    checar(
        'if got.get("protocol") and (got.get("schedule")' not in fonte,
        "a exigencia de agendamento/eta/link para avisar SAIU",
    )
    checar(
        'if got.get("protocol") and not detect_handoff_trigger(' in fonte,
        "protocolo avisa sozinho — mas mensagem de HANDOFF nao vira captura",
    )


def r2_nao_reaciona_o_que_ja_esta_aberto() -> None:
    fonte = (RAIZ / "app/services/dispatch_router.py").read_text(encoding="utf-8")
    # A condição está partida em três linhas — recorto do `if` até o corpo dele,
    # em vez de contar caracteres para trás (que pegava o comentário e não o
    # código, e o comentário cita o protocolo sem ser a regra).
    i = fonte.index('if (reason == "insurer_closed"')
    bloco = fonte[i:fonte.index("await clear_active_dispatch", i) + 30]
    checar(
        'not (session.get("captured") or {}).get("protocol")' in bloco,
        "a retomada automatica so roda se NAO houver protocolo",
        "com protocolo, reabrir manda um SEGUNDO prestador",
    )


def r5b_ma_noticia_tambem_passa() -> None:
    fonte = (RAIZ / "app/services/dispatch_router.py").read_text(encoding="utf-8")
    i = fonte.index("_MONITOR_FORWARD_RE = (")
    j = fonte.index("\n)", i) + 2
    ns: dict = {}
    exec(fonte[i:j], ns)  # noqa: S102 — é o próprio regex do produto
    rx = ns["_MONITOR_FORWARD_RE"]

    boas = ["Prestador a caminho, faltam 30 minutos", "Agendado para 05/08 as 09h"]
    ruins = ["Nao encontramos prestador na sua regiao", "Seu servico foi cancelado",
             "Houve um problema com o atendimento", "O atendimento foi reagendado"]
    nao_rota = ["Qual a cor do veiculo?", "Voce confirma o endereco?"]

    for t in boas:
        checar(bool(re.search(rx, t, re.IGNORECASE)), f"boa noticia passa: {t[:34]}…")
    for t in ruins:
        checar(bool(re.search(rx, t, re.IGNORECASE)), f"MA noticia tambem passa: {t[:34]}…",
               "quem esta no acostamento precisa saber ANTES de desistir de esperar")
    for t in nao_rota:
        checar(not re.search(rx, t, re.IGNORECASE), f"e pergunta de coleta NAO vira aviso: {t[:30]}…")


def r4_o_aviso_deixa_rastro() -> None:
    fonte = (RAIZ / "app/services/dispatch_router.py").read_text(encoding="utf-8")
    checar("async def _registrar_fala_ao_cliente" in fonte,
           "existe o registro do que o motor diz ao segurado")
    checar("record_platform_send" in fonte,
           "e ele escreve onde a nota de contexto do atendente le")
    checar('"[AO CLIENTE] ' in fonte,
           "e a fala entra no transcript (Espelho, linha do tempo, dossie)")
    checar('session["client_notify_failed"]' in fonte,
           "falha de aviso fica MARCADA na sessao, nao so no log")
    checar("_support_alert_seguro" in fonte,
           "e o suporte e avisado — o segurado ficou sem o protocolo")


def r5_o_encerramento_encerra() -> None:
    fonte = (RAIZ / "app/tasks/dispatch_followup.py").read_text(encoding="utf-8")
    checar('session["state"] = "resolvido"' in fonte,
           "o encerramento marca a sessao como RESOLVIDA")
    checar("clear_active_dispatch" in fonte,
           "e libera a sessao em vez de deixa-la viva ate o TTL de 24h")
    checar("record_platform_send" in fonte,
           "a pergunta 'o prestador chegou?' deixa rastro para o agente da entrada")
    checar('"[AO CLIENTE] ' in fonte,
           "e entra no transcript, como o Vigia ja fazia")


def o_timer_do_followup_sobrevive() -> None:
    fonte = (RAIZ / "app/services/dispatch_router.py").read_text(encoding="utf-8")
    checar('dispatch_monitoring_com_followup' in fonte,
           "sessao em monitoring com follow-up pendente NAO e supersedida")
    checar('existing.get("followup_at") and not existing.get("followup_sent")' in fonte,
           "e o criterio e ter compromisso pendente, nao a idade da sessao",
           "o timer morria no mesmo instante em que nascia")


def o_followup_passa_pelo_governador() -> None:
    """P-70 item 5 — e a excecao que o torna possivel."""
    fup = (RAIZ / "app/tasks/dispatch_followup.py").read_text(encoding="utf-8")
    gov = (RAIZ / "app/services/platform_outbound.py").read_text(encoding="utf-8")

    checar("send_to_client_guarded" in fup,
           "o follow-up passa pelo canal GOVERNADO",
           "era o unico envio frio a segurado que furava o governador")
    checar('r.get("ok")' in fup,
           "e trata `queued` como SUCESSO, nao como falha",
           "senao reenviaria a cada 60s e empilharia copias da mesma pergunta")

    checar("_ESTADOS_QUE_NAO_OCUPAM" in gov and '"monitoring"' in gov,
           "e `monitoring` deixa de marcar o cliente como ocupado")
    # A prova de que a excecao E necessaria: sem ela, o estado em que o
    # follow-up roda seria o mesmo que o impediria de rodar.
    i = gov.index("_ESTADOS_QUE_NAO_OCUPAM = (")
    linha = gov[i:gov.index("\n", i)]
    checar("monitoring" in linha and "insurer_closed" in linha,
           "os tres estados estao na mesma tupla — um lugar so",
           linha)


def o_guarda_tem_como_falhar() -> None:
    """Um regex que casa tudo passaria em todos os checks de cima."""
    fonte = (RAIZ / "app/services/dispatch_router.py").read_text(encoding="utf-8")
    i = fonte.index("_MONITOR_FORWARD_RE = (")
    j = fonte.index("\n)", i) + 2
    ns: dict = {}
    exec(fonte[i:j], ns)  # noqa: S102
    rx = ns["_MONITOR_FORWARD_RE"]
    neutros = ["Bom dia", "Informe o CPF do titular", "1 - Sim 2 - Nao"]
    recusou = [t for t in neutros if not re.search(rx, t, re.IGNORECASE)]
    checar(len(recusou) == len(neutros),
           "o filtro RECUSA texto neutro — nao casa tudo",
           f"casou indevidamente: {[t for t in neutros if t not in recusou]}")


def main() -> int:
    print(__doc__)
    print("== R1: o protocolo sozinho ja avisa ==")
    r1_o_protocolo_sozinho_ja_avisa()
    print("== R2: nao reaciona o que ja esta aberto ==")
    r2_nao_reaciona_o_que_ja_esta_aberto()
    print("== R5b: ma noticia tambem passa ==")
    r5b_ma_noticia_tambem_passa()
    print("== R4: o aviso deixa rastro ==")
    r4_o_aviso_deixa_rastro()
    print("== R5: o encerramento encerra ==")
    r5_o_encerramento_encerra()
    print("== o timer do follow-up sobrevive ==")
    o_timer_do_followup_sobrevive()
    print("== o follow-up passa pelo governador ==")
    o_followup_passa_pelo_governador()
    print("== o guarda tem como falhar ==")
    o_guarda_tem_como_falhar()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O CICLO FECHA: AVISA, DEIXA RASTRO, E ENCERRA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
