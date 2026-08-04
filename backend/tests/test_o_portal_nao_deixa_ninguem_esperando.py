"""Nenhum acionamento de vidros morre em silêncio.

Por que este teste existe
-------------------------
📊 Medido em 04/08/2026: `dispatch_watchdog.py` e `handoff_watchdog.py` — os
dois vigias do sistema — têm **zero** menções a "portal".

Eles vigiam `dispatch_sessions`, o corredor de WhatsApp com a seguradora. O
portal de vidros é outro caminho (`portal_jobs`), e ninguém olhava para ele.

O ponto cego era estreito e fatal: a `portal_action` espera o worker por **150
segundos** e conta ao segurado o que aconteceu. Depois disso, **não existe
ninguém**. O job chega em `needs_human` mais tarde e a conversa nunca fica
sabendo. O segurado mandou "meu vidro quebrou", ouviu *"já vou abrir, um
minutinho"* — e o minutinho não acaba nunca.

📊 E é o caso mais comum, não a exceção: **33 dos 39** acionamentos de vidros
terminaram em `needs_human`.

O guarda que importa mais aqui é o [4]
---------------------------------------
Um Vigia que acusa tudo é tão inútil quanto um que não acusa nada — vira ruído,
e ruído se ignora. Metade deste arquivo prova que ele **fica quieto**: job novo
na fila, job entregue ao atendimento, job já avisado. Sem esses controles, uma
função que devolvesse achado sempre passaria em todo o resto.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

FALHAS: list[str] = []
AGORA = datetime(2026, 8, 4, 15, 0, 0, tzinfo=timezone.utc)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _carregar():
    """Carrega o módulo pelo caminho: `app.tasks` puxa dependências de runtime
    que não existem na máquina de teste, e a parte que decide é pura."""
    import importlib.util

    caminho = os.path.join(RAIZ, "backend", "app", "tasks", "vigia_do_portal.py")
    spec = importlib.util.spec_from_file_location("_vigia_do_portal", caminho)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


VIGIA = _carregar()


def _job(status, *, minutos_atras=0, iniciado_ha=None, evidence=None, error=None,
         peca="vidro de porta", placa="QJQ0A91"):
    criado = AGORA - timedelta(minutes=minutos_atras)
    return {
        "id": "job-1", "company_id": "empresa-1", "status": status,
        "session_id": "whatsapp:5547999999999:empresa-1",
        "params": {"placa": placa, "dano": {"peca": peca}},
        "evidence": evidence or {},
        "error": error,
        "created_at": criado.isoformat(),
        "started_at": (AGORA - timedelta(minutes=iniciado_ha)).isoformat() if iniciado_ha else None,
    }


# ---------------------------------------------------------------------------

def teste_o_worker_que_nao_pega_vira_handoff():
    print("\n[1] Job parado na fila: o worker não vai pegar — isso é handoff")

    # É o que acontece com PORTAL_REAL_ENABLED desligado: `poll_loop` devolve na
    # hora, não fica em loop, e os jobs se empilham em silêncio.
    achado = VIGIA.diagnosticar(_job("queued", minutos_atras=6), AGORA)
    checar(bool(achado), "acionamento parado 6min na fila é acusado")
    if achado:
        checar(achado["motivo"] == "nunca_pegou", "motivo = nunca_pegou", achado["motivo"])
        checar("PORTAL_REAL_ENABLED" in achado["para_o_suporte"],
               "o alerta diz onde olhar (o gate do worker)")
        # O segurado não pode ouvir "aguarde" quando ninguém está trabalhando.
        texto = achado["para_o_segurado"].lower()
        checar("equipe" in texto, "o segurado é avisado de que um humano assumiu")
        checar("vidro de porta" in texto and "qjq0a91" in texto.lower(),
               "a mensagem diz de QUAL pedido está falando",
               achado["para_o_segurado"][:100])


def teste_o_worker_que_cai_no_meio_vira_handoff():
    print("\n[2] Job rodando há tempo demais: o worker caiu no meio")

    # A recuperação de órfãos roda POR DENTRO do worker. Se ele caiu, ela não
    # roda — e é exatamente aí que alguém precisa olhar de fora.
    achado = VIGIA.diagnosticar(_job("running", minutos_atras=12, iniciado_ha=11), AGORA)
    checar(bool(achado) and achado["motivo"] == "travado_rodando",
           "acionamento rodando há 11min é acusado",
           str(achado))


def teste_o_que_termina_depois_da_janela_chega_ao_segurado():
    print("\n[3] Terminou depois dos 150s do atendimento — o Vigia conta")

    parou = VIGIA.diagnosticar(_job("needs_human", minutos_atras=9, evidence={
        "pergunta": "Qual o lado do item danificado?",
        "opcoes": ["Não sabe", "Lado do carona", "Lado do motorista"],
        "pedido_do_segurado": {"peca": "vidro da porta", "como": "quebraram de noite"},
    }), AGORA)
    checar(bool(parou) and parou["motivo"] == "parou_e_ninguem_soube",
           "acionamento que parou esperando decisão é acusado", str(parou))
    if parou:
        # Um dossiê só vale se um humano resolver sem reabrir o portal.
        checar("Lado do carona" in parou["para_o_suporte"],
               "o dossiê traz as OPÇÕES que o portal ofereceu")
        checar("quebraram de noite" in parou["para_o_suporte"],
               "o dossiê traz o que o SEGURADO disse",
               "sem isso ninguém sabe qual opção casa")

    falhou = VIGIA.diagnosticar(_job("failed", minutos_atras=9, error="apolice nao localizada"), AGORA)
    checar(bool(falhou) and falhou["motivo"] == "falhou_e_ninguem_soube",
           "acionamento que falhou é acusado", str(falhou))

    # `done` também: boa notícia não entregue continua sendo silêncio.
    ok = VIGIA.diagnosticar(_job("done", minutos_atras=9), AGORA)
    checar(bool(ok) and ok["motivo"] == "concluiu_e_ninguem_soube",
           "acionamento CONCLUÍDO que ninguém entregou também é acusado",
           "o segurado ficou sem saber que deu certo")


def teste_o_vigia_fica_quieto_quando_esta_tudo_bem():
    print("\n[4] CONTROLE — o Vigia fica QUIETO (metade do valor dele está aqui)")

    # (a) job novo na fila: o worker pega em segundos. Acusar aqui seria acusar
    # o funcionamento normal.
    checar(VIGIA.diagnosticar(_job("queued", minutos_atras=1), AGORA) is None,
           "job de 1min na fila NÃO é acusado",
           "o worker ainda vai pegar — alarme aqui é ruído")

    # (b) rodando há pouco: o adaptativo leva minutos por natureza.
    checar(VIGIA.diagnosticar(_job("running", minutos_atras=3, iniciado_ha=2), AGORA) is None,
           "job rodando há 2min NÃO é acusado")

    # (c) O CONTROLE PRINCIPAL: o atendimento JÁ contou ao segurado. Avisar de
    # novo entrega duas versões da mesma coisa e ele não sabe qual vale.
    entregue = _job("needs_human", minutos_atras=9, evidence={"entregue_ao_agente": True})
    checar(VIGIA.diagnosticar(entregue, AGORA) is None,
           "job JÁ ENTREGUE ao atendimento NÃO é acusado",
           "duplicar aviso é pior que não avisar")

    # (d) dispara UMA vez.
    avisado = _job("failed", minutos_atras=30, evidence={"vigia_avisou_em": "2026-08-04T14:00:00+00:00"})
    checar(VIGIA.diagnosticar(avisado, AGORA) is None,
           "job JÁ AVISADO não é acusado de novo",
           "vigia que repete vira ruído, e ruído se ignora")

    # (e) e a prova de que (c) e (d) não estão silenciando tudo: o MESMO job,
    # sem as marcas, TEM de ser acusado. Sem este par, um `return None` no topo
    # da função passaria neste teste inteiro.
    sem_marca = _job("needs_human", minutos_atras=9)
    checar(VIGIA.diagnosticar(sem_marca, AGORA) is not None,
           "CONTRAPROVA — o mesmo job SEM as marcas é acusado",
           "prova que os silêncios acima vêm das marcas, não de a função ser cega")


def teste_o_vigia_esta_agendado_e_nao_e_paralelo():
    print("\n[5] O Vigia do portal roda — e no MESMO scheduler do outro")
    with open(os.path.join(RAIZ, "backend", "app", "tasks", "buffer_processor.py"),
              encoding="utf-8") as fh:
        fonte = fh.read()
    sem_com = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("varrer_portal" in sem_com, "a varredura do portal está agendada",
           "código que ninguém chama não vigia nada")
    checar('id="vigia_do_portal"' in sem_com, "tem id próprio no scheduler")
    checar("check_dispatch_watchdog" in sem_com,
           "CONTROLE — o vigia dos acionamentos continua agendado",
           "somar varredura não pode substituir a que já existia")

    # CLAUDE.md §5: consolidar antes de duplicar. Um scheduler, duas varreduras.
    checar(sem_com.count("AsyncIOScheduler(") <= 1,
           "não nasceu um segundo scheduler",
           "seria motor paralelo — proibido por CLAUDE.md §5")


def main() -> int:
    print("=" * 70)
    print("O PORTAL NAO DEIXA NINGUEM ESPERANDO")
    print("=" * 70)
    for teste in (teste_o_worker_que_nao_pega_vira_handoff,
                  teste_o_worker_que_cai_no_meio_vira_handoff,
                  teste_o_que_termina_depois_da_janela_chega_ao_segurado,
                  teste_o_vigia_fica_quieto_quando_esta_tudo_bem,
                  teste_o_vigia_esta_agendado_e_nao_e_paralelo):
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
    print("NENHUM ACIONAMENTO DE VIDROS MORRE EM SILENCIO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
