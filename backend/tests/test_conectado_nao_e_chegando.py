""""Conectado" não é o mesmo que "chegando".

A HISTÓRIA
==========
📊 06/08/2026, medido no projeto `dcajcvlzcjbmyapmklil`:

    AutoFleet   channel_status='connected'   ultimo observed_event  44 h atras
    Resulta     channel_status='connected'   ultimo observed_event  68 h atras

O painel dizia Conectado e estava CERTO sobre o cabo. 📊 O socket estava mesmo
vivo — provado no mesmo dia com `GET /user/privacy` respondendo 200 em 0,3 s
contra o WhatsApp da corretora, com uma corretora sem sessao dando timeout como
linha de controle.

O que estava desligado era a ENTREGA: o reconector religava o canal mandando so
`{"immediate": True}`, e o Evolution Go gravava `Webhook = ""` por cima. O
provedor despachava as mensagens para lugar nenhum.

Ninguem descobriu por tres dias. E nao foi descuido — **nao havia o que olhar.**
O heartbeat media o cabo, e o cabo estava bom. `last_seen_at` avancava de cinco
em cinco minutos, verdinho, enquanto o acervo nao crescia uma linha.

O QUE ESTE ARQUIVO GUARDA
=========================
A pergunta que faltava: *"a corretora que se diz conectada gravou alguma
conversa recentemente?"*. E as tres regras que impedem o alarme de virar ruido —
porque alarme que grita a toa e alarme que se aprende a fechar sem ler.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _carregar_estado():
    nome = "_teste_channel_state"
    if nome in sys.modules:
        return sys.modules[nome]
    # `integration_secrets` puxa `app.services`, que puxa `openai`. O que esta
    # sob teste e decisao PURA — nao precisa de descriptografia nenhuma.
    if "app.services.whatsapp.integration_secrets" not in sys.modules:
        dublê = types.ModuleType("app.services.whatsapp.integration_secrets")
        dublê.decrypt_integration_secret = lambda v: v
        sys.modules["app.services.whatsapp.integration_secrets"] = dublê
    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp", "channel_state.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


AGORA = datetime(2026, 8, 6, 17, 0, tzinfo=timezone.utc)


def _ha(horas: float) -> str:
    return (AGORA - timedelta(hours=horas)).isoformat()


# ---------------------------------------------------------------------------
def teste_o_caso_que_custou_tres_dias():
    print("\n[1] O caso real: conectado e mudo")
    CS = _carregar_estado()

    autofleet = CS.decidir_alarme_de_entrega(
        estado_do_canal="connected", ultima_entrega=_ha(44), agora=AGORA)
    checar(autofleet["alarmar"] is True,
           "AutoFleet — conectada e 44 h sem gravar: ALARMA",
           f"motivo={autofleet['motivo']} horas={autofleet['horas']:.0f}")

    resulta = CS.decidir_alarme_de_entrega(
        estado_do_canal="connected", ultima_entrega=_ha(68), agora=AGORA)
    checar(resulta["alarmar"] is True,
           "Resulta — conectada e 68 h sem gravar: ALARMA",
           f"horas={resulta['horas']:.0f}")

    # CONTROLE — o guarda tem de conseguir NÃO alarmar. Sem esta linha, um
    # alarme que dispara sempre passaria neste arquivo inteiro.
    saudavel = CS.decidir_alarme_de_entrega(
        estado_do_canal="connected", ultima_entrega=_ha(0.5), agora=AGORA)
    checar(saudavel["alarmar"] is False,
           "CONTROLE — conectada e capturando há 30 min: SILÊNCIO",
           f"motivo={saudavel['motivo']}")


def teste_nao_grita_duas_vezes_a_mesma_noticia():
    print("\n[2] Canal que já se declara caído não recebe um segundo alarme")
    CS = _carregar_estado()

    for estado in ("disconnected", "unknown", "retired", "close"):
        decisao = CS.decidir_alarme_de_entrega(
            estado_do_canal=estado, ultima_entrega=_ha(200), agora=AGORA)
        checar(decisao["alarmar"] is False,
               f"canal '{estado}' e 200 h mudo: NÃO alarma de novo",
               "a queda já é dita pelo alarme do canal")

    # E `connecting` também não: quem acabou de parear ainda não gravou nada, e
    # alarmar ali transformaria todo pareamento novo num incidente.
    decisao = CS.decidir_alarme_de_entrega(
        estado_do_canal="connecting", ultima_entrega=None, agora=AGORA)
    checar(decisao["alarmar"] is False,
           "e 'connecting' também não — pareamento novo não é incidente")

    # CONTROLE — mas o MESMO silêncio, com o canal afirmando conexão, alarma.
    # É o que prova que o filtro acima é sobre o ESTADO, e não um "return False".
    decisao = CS.decidir_alarme_de_entrega(
        estado_do_canal="connected", ultima_entrega=None, agora=AGORA)
    checar(decisao["alarmar"] is True,
           "CONTROLE — conectado e nunca entregou: ALARMA",
           "é o pior caso, não um caso a ignorar")


def teste_a_conta_e_em_horas_e_o_limite_e_respeitado():
    print("\n[3] O limite é de horas — e as duas bordas valem")
    CS = _carregar_estado()

    limite = CS.LIMITE_SEM_ENTREGA_HORAS
    checar(limite >= 4,
           "o limite não é curto a ponto de virar ruído",
           f"{limite} h — uma corretora pode passar a manhã sem mensagem")
    checar(limite <= 12,
           "nem longo a ponto de perder um dia de trabalho",
           f"{limite} h")

    logo_antes = CS.decidir_alarme_de_entrega(
        estado_do_canal="connected", ultima_entrega=_ha(limite - 0.1), agora=AGORA)
    logo_depois = CS.decidir_alarme_de_entrega(
        estado_do_canal="connected", ultima_entrega=_ha(limite + 0.1), agora=AGORA)
    checar(logo_antes["alarmar"] is False and logo_depois["alarmar"] is True,
           "as duas bordas do limite se comportam de forma oposta",
           f"{limite - 0.1:.1f}h=silêncio · {limite + 0.1:.1f}h=alarme")


def teste_o_alarme_esta_no_laco_e_le_o_acervo():
    print("\n[4] Ligado ao heartbeat — e olhando o lugar certo")
    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp", "channel_state.py")
    fonte = open(caminho, encoding="utf-8").read()
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("decidir_alarme_de_entrega(" in cmd and "await alarmar_entrega(" in cmd,
           "o laço do heartbeat consulta a regra e alarma")
    checar('_ultima_entrega_por_corretora' in cmd,
           "e busca quando cada corretora gravou pela última vez")
    checar('.table("observed_events")' in cmd,
           "lê o ACERVO, não `integrations`",
           "`last_seen_at` mede a sonda — e foi a sonda que ficou verde à toa")

    # CONTROLE — a checagem precisa rodar ANTES do `continue` dos inalterados.
    # O canal que este alarme existe para pegar é justamente o que não muda de
    # estado: verde, confirmado e mudo, ciclo após ciclo.
    i_entrega = cmd.find("entrega = decidir_alarme_de_entrega")
    i_continue = cmd.find('resumo["inalterados"] += 1')
    checar(0 < i_entrega < i_continue,
           "CONTROLE — roda ANTES do `continue` dos canais inalterados",
           "depois dele, nunca rodaria para quem mais precisa")

    # E não pode derrubar o heartbeat: gravar a verdade continua sendo a
    # obrigação; alarmar é o bônus.
    checar("[ENTREGA] alarme não registrado" in fonte,
           "CONTROLE — falha ao alarmar não derruba o heartbeat")

    # Costurável, como as outras quatro — teste que não roda não protege.
    checar("alarme_de_entrega: Optional[Callable" in cmd,
           "a costura é injetável, como o resto do heartbeat")


def main() -> int:
    print("=" * 70)
    print('"CONECTADO" NÃO É O MESMO QUE "CHEGANDO"')
    print("=" * 70)
    teste_o_caso_que_custou_tres_dias()
    teste_nao_grita_duas_vezes_a_mesma_noticia()
    teste_a_conta_e_em_horas_e_o_limite_e_respeitado()
    teste_o_alarme_esta_no_laco_e_le_o_acervo()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o silêncio de uma corretora agora tem quem o note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
