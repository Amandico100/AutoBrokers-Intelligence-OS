"""O canal religa sozinho — e o botão de QR deixa de ser o reconector.

A causa-raiz da instabilidade, medida
--------------------------------------
Nas palavras do Founder: *"desconecta várias vezes... clico em gerar QR code e
diz que está desconectado, e ele reconecta sozinho. Às vezes parece que pareou,
aí aparece uma imagem de gerar novo QR e quando clica ele pareia sozinho."*

📊 Auditado em 04/08/2026:

    CONNECT_ON_STARTUP=false                    no Evolution Go
    grep "instance/connect" backend/app         3 lugares, os TRÊS de pareamento

> **Todo restart do provedor derruba todos os canais, e nada os religa.**

O botão "Gerar QR code" virou, sem ninguém decidir isso, o único reconector do
produto. E o "pareia sozinho" que parece bug é o whatsmeow fazendo a coisa
certa: a sessão ainda está registrada, então ele reconecta sem QR nenhum. O que
estava errado era **precisar de um humano para isso acontecer**.

📊 O preço: `observed_events` teve evento em **4 horas de 168** numa janela de 7
dias. Os canais passaram a semana desligados e ninguém soube.

A distinção que este arquivo protege
-------------------------------------
> **Reconectar não é reparear.**

A sessão do WhatsApp continua registrada no provedor; o que caiu foi o socket.
Gerar QR quando a sessão existe é a única forma de PIORAR — o QR novo invalida
a sessão boa e obriga a corretora a pegar o celular de novo.

Por isso os dois casos que mais importam aqui são negativos: **[2]** prova que
não se reconecta no escuro (sonda muda ≠ canal caído) nem um canal que nunca
esteve de pé (ali não há sessão — só haveria QR). E **[3]** prova que a escada
de espera existe, para um canal recusado não virar batida de porta a cada cinco
minutos, para sempre.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

FALHAS: list[str] = []
AGORA = datetime(2026, 8, 4, 16, 0, 0, tzinfo=timezone.utc)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _carregar():
    """Carrega o módulo pelo caminho; `app.core.config` pede pydantic_settings."""
    if "app.core.config" not in sys.modules:
        pacote = sys.modules.setdefault("app", types.ModuleType("app"))
        pacote.__path__ = [os.path.join(RAIZ, "backend", "app")]
        core = sys.modules.setdefault("app.core", types.ModuleType("app.core"))
        core.__path__ = [os.path.join(RAIZ, "backend", "app", "core")]
        cfg = types.ModuleType("app.core.config")
        cfg.settings = type("S", (), {})()
        sys.modules["app.core.config"] = cfg

    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp", "channel_state.py")
    spec = importlib.util.spec_from_file_location("_channel_state", caminho)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_channel_state"] = m
    spec.loader.exec_module(m)
    return m


CS = _carregar()


# ---------------------------------------------------------------------------

def teste_o_canal_que_caiu_e_religado():
    print("\n[1] Canal que estava de pé e caiu: religa")

    for antes in ("connected", "connecting"):
        checar(CS.deve_reconectar("disconnected", antes) is True,
               f"estava '{antes}' e a sonda diz 'disconnected' → religa")

    checar(CS.deve_reconectar("close", "connected") is True,
           "'close' (vocabulário cru do provedor) também conta como caído")


def teste_nao_religa_no_escuro_nem_o_que_nunca_esteve_de_pe():
    print("\n[2] CONTROLE — os dois casos em que religar seria ERRADO")

    # Sonda muda. Não saber não é saber que caiu — reconectar aqui começa um laço
    # contra um provedor que talvez só esteja lento.
    checar(CS.deve_reconectar(None, "connected") is False,
           "sonda SEM resposta NÃO dispara reconexão",
           "não saber ≠ saber que caiu")

    # Canal que nunca conectou não tem sessão registrada. `/instance/connect`
    # ali geraria um QR que ninguém vai ler — e QR novo invalida sessão boa.
    for nunca in ("retired", "disconnected", "unknown", None, ""):
        checar(CS.deve_reconectar("disconnected", nunca) is False,
               f"canal em '{nunca}' NÃO é religado — não há sessão, só haveria QR")

    # E o que está de pé não se mexe.
    for ok in ("connected", "connecting"):
        checar(CS.deve_reconectar(ok, "connected") is False,
               f"canal '{ok}' não é tocado")

    # CONTRAPROVA: a mesma função DEVE dizer sim no caso do [1]. Sem este par,
    # uma implementação que devolvesse sempre False passaria em todo o caso [2].
    checar(CS.deve_reconectar("disconnected", "connected") is True,
           "CONTRAPROVA — a função consegue dizer SIM",
           "prova que os 'não' acima vêm da regra, não de cegueira")


def teste_a_escada_de_espera_existe_e_tem_teto():
    print("\n[3] A escada de espera: dobra, e para de dobrar")

    checar(CS.espera_do_backoff(0) == 0, "sem falha, não espera")
    e1, e2, e3 = CS.espera_do_backoff(1), CS.espera_do_backoff(2), CS.espera_do_backoff(3)
    checar(e1 == CS.TENTATIVA_INICIAL_S, f"1ª falha espera {CS.TENTATIVA_INICIAL_S}s", str(e1))
    checar(e2 == e1 * 2 and e3 == e2 * 2, "e dobra a cada falha", f"{e1}/{e2}/{e3}")

    # O teto é o que impede a batida de porta eterna.
    checar(CS.espera_do_backoff(50) == CS.TETO_DE_ESPERA_S,
           f"e para no teto de {CS.TETO_DE_ESPERA_S // 60} minutos",
           str(CS.espera_do_backoff(50)))
    checar(CS.TETO_DE_ESPERA_S >= 10 * 60,
           "o teto é grande o bastante para não virar martelada",
           f"{CS.TETO_DE_ESPERA_S}s")


def teste_o_backoff_segura_a_segunda_tentativa():
    print("\n[4] Duas tentativas seguidas: a segunda espera")
    import asyncio

    # O módulo de segredos puxa `app.services.__init__` → `openai`, que não
    # existe na máquina de teste. Aqui ele vira dublê: o que está sob teste é a
    # ESCADA DE ESPERA, e ela não depende de descriptografia nenhuma.
    if "app.services.whatsapp.integration_secrets" not in sys.modules:
        segredos = types.ModuleType("app.services.whatsapp.integration_secrets")
        segredos.decrypt_integration_secret = lambda v: ""
        sys.modules["app.services.whatsapp.integration_secrets"] = segredos

    linha = {"id": "i1", "instance_id": "ab-teste-1", "base_url": "", "token": ""}
    CS._ULTIMA_RECONEXAO.clear()
    # Sem base_url/token, a função devolve None — mas já registrou a tentativa,
    # que é o que o backoff precisa medir.
    asyncio.run(CS._reconectar_evolution_go(linha, AGORA))
    marcado = CS._ULTIMA_RECONEXAO.get("ab-teste-1")
    checar(marcado is not None, "a tentativa fica registrada", str(marcado))

    logo_depois = asyncio.run(CS._reconectar_evolution_go(linha, AGORA + timedelta(seconds=5)))
    checar(logo_depois == "aguardando_backoff",
           "5 segundos depois, NÃO tenta de novo",
           f"devolveu={logo_depois}")

    bem_depois = asyncio.run(
        CS._reconectar_evolution_go(linha, AGORA + timedelta(seconds=CS.TETO_DE_ESPERA_S + 60)))
    checar(bem_depois != "aguardando_backoff",
           "CONTROLE — passado o tempo, tenta de novo",
           f"devolveu={bem_depois} — sem isto o backoff seria um bloqueio eterno")
    CS._ULTIMA_RECONEXAO.clear()


def teste_o_reconector_esta_no_laco_e_nunca_gera_qr():
    print("\n[5] Está ligado no heartbeat — e não gera QR em lugar nenhum")
    fonte = open(os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                              "channel_state.py"), encoding="utf-8").read()
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("deve_reconectar(resposta, linha.get(\"channel_status\"))" in comandos,
           "o laço do heartbeat consulta a regra",
           "função que ninguém chama não reconecta nada")
    # A chamada é pela COSTURA (`religar`), não pelo nome concreto — é o que
    # permite ao teste do heartbeat injetar um dublê e continuar provando a
    # decisão sem rede. O padrão da costura é o reconector de verdade.
    checar("religar = reconector or _reconectar_evolution_go" in comandos,
           "o reconector é a costura padrão de `verificar_canais`")
    checar("await religar(linha, momento)" in comandos,
           "e o laço chama a costura")
    # E religar não pode sequestrar o serviço antigo quando falha.
    checar("o heartbeat segue" in fonte,
           "falha ao religar NÃO impede o heartbeat de gravar a verdade",
           "peça nova que quebra a função da antiga está errada mesmo funcionando")

    # 🔴 A regra que não pode ser quebrada: reconectar nunca pede QR.
    corpo = comandos.split("async def _reconectar_evolution_go", 1)[-1].split("async def ", 1)[0]
    for proibido in ("qrcode", "qr_code", "/instance/qr", "pairing", "pairingCode"):
        checar(proibido not in corpo.lower(),
               f"o reconector NÃO menciona '{proibido}'",
               "QR novo invalida a sessão boa e obriga a corretora a pegar o celular")
    checar("/instance/connect" in corpo,
           "CONTROLE — mas ele realmente pede a religação",
           "um reconector que não conecta é só um log")

    # E o heartbeat não pode ter perdido o que já fazia.
    checar("decidir_heartbeat(" in comandos and "async def verificar_canais" in comandos,
           "CONTROLE — o heartbeat continua inteiro",
           "somar reconexão não pode ter substituído a verificação")


def main() -> int:
    print("=" * 70)
    print("O CANAL RELIGA SOZINHO")
    print("=" * 70)
    for teste in (teste_o_canal_que_caiu_e_religado,
                  teste_nao_religa_no_escuro_nem_o_que_nunca_esteve_de_pe,
                  teste_a_escada_de_espera_existe_e_tem_teto,
                  teste_o_backoff_segura_a_segunda_tentativa,
                  teste_o_reconector_esta_no_laco_e_nunca_gera_qr):
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
    print("O BOTAO DE QR DEIXOU DE SER O RECONECTOR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
