"""O agente pode ficar calado — e calar não gasta a chance dele.

A HISTÓRIA
----------
📊 Medido em 05/08/2026 sobre 11.631 mensagens reais de seguradora:

    43,2% NÃO TÊM MARCA DE PERGUNTA NENHUMA
    e o passo `noop`, que é o silêncio escrito à mão, cobre 14,8% delas.

Os outros 85% caíam no cérebro, viravam `NAO_SEI`, e **duas telas de aviso
seguidas chamavam um humano**:

    URA:  "Termo de Privacidade: ao prosseguir você concorda..."
          → não pergunta nada. Responder quebra o menu.
          → dizer "não sei" gasta 1 de 2 chances.
    URA:  "Você está na posição 3 da fila."
          → gastou a segunda.
          → HUMANO CHAMADO. Por dois avisos.

E havia um segundo defeito no mesmo contador: 📊 CINCO motivos de recusa
alimentavam UM limite. Uma resposta **certa** com 401 caracteres contava igual
a "não sei". O agente acertava e era punido por prolixidade.

E um terceiro, que era defeito VIVO: quando o corredor calava de propósito, a
última entrada do transcript continuava sendo `in`. Trinta segundos depois o
Vigia diagnosticava trava e o Sentinela **escrevia numa tela que pedia
silêncio** — o que na URA costuma voltar ao menu inicial.

O QUE ESTE TESTE GUARDA
-----------------------
1. `SEM_RESPOSTA` é aceito quando a tela não pede nada — e **só então**.
2. Quem cala numa tela que PEDE algo é tratado como recusa e gasta a chance.
3. Erro de redação ganha uma nova tentativa; recusa conta na hora.
4. O Vigia respeita o silêncio deliberado, e só enquanto ele vale.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
Cada guarda tem o seu par: o caso que deve passar E o caso que deve reprovar.
Um guarda que só recebe caso fácil não guarda nada — e aqui o risco é
exatamente esse, porque `SEM_RESPOSTA` sem verificação seria só um jeito mais
educado de travar.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

FALHAS: list = []


def checar(condicao: bool, descricao: str, porque: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  X     {descricao}")
        if porque:
            print(f"        {porque}")
        FALHAS.append(descricao)


def _carregar_por_caminho(nome_modulo: str, caminho_rel: str):
    """Carrega um módulo pelo caminho, registrando-o no nome que os outros usam.

    Importar `app.services.insurer_dispatch_service` pelo pacote puxa a cadeia
    inteira do backend — `openai`, `pydantic_settings` — que não existe numa
    máquina de desenvolvimento. O teste reprovaria por ausência de dependência,
    não por defeito, e essa é a pior espécie de vermelho: ela ensina a ignorar
    o teste.

    📊 Os dois módulos aqui só importam biblioteca padrão no topo (e um ao
    outro). Registrar `corridor_playbooks` sob o nome do pacote ANTES faz o
    `from app.services.corridor_playbooks import ...` do outro resolver sozinho.
    """
    caminho = os.path.join(RAIZ, *caminho_rel.split("/"))
    spec = importlib.util.spec_from_file_location(nome_modulo, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome_modulo] = mod
    spec.loader.exec_module(mod)
    return mod


def _motor():
    """O `insurer_dispatch_service` real, sem a cadeia pesada do pacote."""
    if "_motor_sob_teste" in sys.modules:
        return sys.modules["_motor_sob_teste"]
    for p in ("app", "app.services", "app.tasks", "app.core"):
        sys.modules.setdefault(p, types.ModuleType(p))
    _carregar_por_caminho("app.services.corridor_playbooks",
                          "app/services/corridor_playbooks.py")
    mod = _carregar_por_caminho("_motor_sob_teste",
                                "app/services/insurer_dispatch_service.py")
    return mod


def _carregar_vigia():
    """Carrega o Vigia pelo caminho — `diagnose` é função pura e não precisa
    do pacote inteiro, que puxa dependência que a máquina de dev não tem."""
    for p in ("app", "app.tasks", "app.services", "app.core"):
        sys.modules.setdefault(p, types.ModuleType(p))
    caminho = os.path.join(RAIZ, "app", "tasks", "dispatch_watchdog.py")
    spec = importlib.util.spec_from_file_location("_vigia_sob_teste", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_vigia_sob_teste"] = mod
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001
        return None


def _agora(delta_s: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_s)).isoformat()


# --------------------------------------------------------------------- #
# [1] O guarda: silêncio só onde ele cabe
# --------------------------------------------------------------------- #
TELAS_QUE_NAO_PEDEM_NADA = (
    "Termo de Privacidade: ao prosseguir com o atendimento voce concorda com "
    "o tratamento dos seus dados.",
    "Voce esta na posicao 3 da fila. Aguarde que ja vamos te atender.",
    "Aguarde um momento, estamos localizando um prestador na sua regiao.",
    "Ok",
    "Vou transferir seu caso para um especialista.",
)

TELAS_QUE_PEDEM_ALGO = (
    "Informe a placa do veiculo por favor",
    "Qual servico voce precisa? 1- Guincho 2- Bateria 3- Pneu",
    "Digite o CPF do titular",
    "Podemos confirmar a abertura do chamado?",
    "Me passe o endereco onde o veiculo esta",
)


def teste_o_silencio_e_aceito_onde_cabe() -> None:
    print("\n[1] SEM_RESPOSTA numa tela que nao pede nada")
    guard_human_phase_reply = _motor().guard_human_phase_reply

    sessao = {"playbook_ref": "allianz-auto-whatsapp@v1", "slots": {}, "captured": {}}
    for tela in TELAS_QUE_NAO_PEDEM_NADA:
        v = guard_human_phase_reply("SEM_RESPOSTA", sessao, insurer_message=tela)
        checar(v.get("silencio") is True and v.get("reason") == "silencio",
               f"cala em: \"{tela[:44]}...\"",
               f"veio {v.get('reason')!r}")


def teste_o_silencio_e_RECUSADO_onde_nao_cabe() -> None:
    """CONTROLE. Sem isto, um guarda que aceita tudo passaria no teste acima."""
    print("\n[2] CONTROLE: numa tela que PEDE algo, calar vira recusa")
    guard_human_phase_reply = _motor().guard_human_phase_reply

    sessao = {"playbook_ref": "allianz-auto-whatsapp@v1", "slots": {}, "captured": {}}
    for tela in TELAS_QUE_PEDEM_ALGO:
        v = guard_human_phase_reply("SEM_RESPOSTA", sessao, insurer_message=tela)
        checar(v.get("reason") == "model_declined" and not v.get("silencio"),
               f"NAO cala em: \"{tela[:44]}...\"",
               f"veio {v.get('reason')!r} — o modelo calaria numa tela que pergunta")

    # E sem a tela, o silencio tambem e recusado: falha fechada.
    v = guard_human_phase_reply("SEM_RESPOSTA", sessao)
    checar(v.get("reason") == "model_declined",
           "sem a tela em maos, o silencio e recusado (falha fechada)",
           "aceitar silencio no escuro seria aceitar qualquer coisa")


def teste_o_resto_do_guarda_continua_de_pe() -> None:
    print("\n[3] O que o guarda ja pegava, continua pegando")
    guard_human_phase_reply = _motor().guard_human_phase_reply

    s = {"playbook_ref": "allianz-auto-whatsapp@v1",
         "slots": {"veiculo_placa": "ABC1D23"}, "captured": {}}
    tela = "Informe a placa"
    checar(guard_human_phase_reply("", s, insurer_message=tela)["reason"] == "empty",
           "resposta vazia")
    checar(guard_human_phase_reply("NAO_SEI", s, insurer_message=tela)["reason"]
           == "model_declined", "NAO_SEI continua sendo recusa")
    checar(guard_human_phase_reply("x" * 401, s, insurer_message=tela)["reason"]
           == "too_long", "texto longo demais")
    checar(guard_human_phase_reply("o protocolo e 99887766", s, insurer_message=tela)["reason"]
           in ("protocol_without_capture", "invented_number"),
           "numero que nao esta no caso")
    checar(guard_human_phase_reply("ABC1D23", s, insurer_message=tela)["ok"] is True,
           "CONTROLE: a placa DO CASO passa",
           "se nem o dado certo passasse, o guarda estaria recusando tudo")


# --------------------------------------------------------------------- #
# [4] Redação não é recusa
# --------------------------------------------------------------------- #
def teste_erro_de_redacao_nao_e_recusa() -> None:
    print("\n[4] Erro de redacao ganha uma nova chance; recusa nao")
    m = _motor()
    MOTIVOS_DE_RECUSA = m.MOTIVOS_DE_RECUSA
    MOTIVOS_DE_REDACAO = m.MOTIVOS_DE_REDACAO
    checar("too_long" in MOTIVOS_DE_REDACAO,
           "texto longo demais e erro de REDACAO",
           "uma resposta certa com 401 caracteres nao e 'nao sei'")
    checar("invented_number" in MOTIVOS_DE_REDACAO, "numero inventado idem")
    checar("model_declined" in MOTIVOS_DE_RECUSA,
           "CONTROLE: NAO_SEI continua sendo RECUSA",
           "se tudo virasse redacao, o limite deixaria de existir")
    checar(not (MOTIVOS_DE_REDACAO & MOTIVOS_DE_RECUSA),
           "e os dois conjuntos nao se sobrepoem")


# --------------------------------------------------------------------- #
# [5] O Vigia respeita o silencio — e so enquanto ele vale
# --------------------------------------------------------------------- #
def teste_o_vigia_respeita_o_silencio() -> None:
    print("\n[5] O Vigia nao fala por cima de quem calou de proposito")
    vigia = _carregar_vigia()
    if vigia is None or not hasattr(vigia, "diagnose"):
        checar(False, "o Vigia carregou", "nao consegui importar dispatch_watchdog")
        return

    def sessao(quieto_ate=None):
        s = {"state": "ura", "created_at": _agora(-600),
             "transcript": [{"direction": "in", "text": "Aguarde um momento",
                             "at": _agora(-120)}]}
        if quieto_ate:
            s["silencio_deliberado_ate"] = quieto_ate
        return s

    # CONTROLE: sem a marca, o Vigia acusa trava — e tem de acusar.
    checar(vigia.diagnose(sessao()) == "stall_unanswered",
           "CONTROLE: sem a marca de silencio, o Vigia ACUSA trava",
           "se nao acusasse, o teste abaixo nao provaria nada")

    checar(vigia.diagnose(sessao(_agora(+45))) is None,
           "com o silencio VALENDO, o Vigia fica quieto")

    checar(vigia.diagnose(sessao(_agora(-5))) == "stall_unanswered",
           "e com o silencio VENCIDO, ele volta a acusar",
           "calar para sempre seria a nova forma de travar")

    checar(vigia.diagnose(sessao("banana")) == "stall_unanswered",
           "carimbo ilegivel nao protege ninguem")


def main() -> int:
    print("=" * 72)
    print("O AGENTE PODE FICAR CALADO")
    print("=" * 72)
    for teste in (teste_o_silencio_e_aceito_onde_cabe,
                  teste_o_silencio_e_RECUSADO_onde_nao_cabe,
                  teste_o_resto_do_guarda_continua_de_pe,
                  teste_erro_de_redacao_nao_e_recusa,
                  teste_o_vigia_respeita_o_silencio):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"FALHOU — {len(FALHAS)} verificacoes")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("CALAR NAO GASTA CHANCE — E SO CALA ONDE CABE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
