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

    # `numero_pareado` é carregado DE VERDADE, não dublado: é ele que decide
    # qual telefone será gravado, e um dublê deixaria o teste verde enquanto o
    # número real saísse errado. O módulo é puro (sem I/O), então carrega sem
    # trazer o `openai` do pacote.
    if "app.services.whatsapp.numero_pareado" not in sys.modules:
        np_caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                                  "numero_pareado.py")
        np_spec = importlib.util.spec_from_file_location(
            "app.services.whatsapp.numero_pareado", np_caminho)
        np_mod = importlib.util.module_from_spec(np_spec)
        sys.modules[np_spec.name] = np_mod
        np_spec.loader.exec_module(np_mod)
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


def teste_o_telefone_pareado_e_gravado_para_TODAS_as_corretoras():
    print("\n[5] Quem pareou fica gravado — em qualquer corretora")
    import asyncio

    CS = _carregar_estado()

    class _Resp:
        def __init__(self, d):
            self.data = d

    class _Q:
        def __init__(self, banco, tabela):
            self.b, self.t, self.f, self.u = banco, tabela, [], None

        def update(self, campos):
            self.u = dict(campos)
            return self

        def eq(self, campo, valor):
            self.f.append((campo, valor))
            return self

        def execute(self):
            linhas = self.b.dados.setdefault(self.t, [])
            tocadas = [l for l in linhas
                       if all(str(l.get(c)) == str(v) for c, v in self.f)]
            for l in tocadas:
                l.update(self.u or {})
            return _Resp(tocadas)

    class Banco:
        def __init__(self):
            self.dados = {"integrations": [
                {"id": "i1", "company_id": "amandus", "paired_phone_e164": None},
                {"id": "i2", "company_id": "autofleet", "paired_phone_e164": "+554891759360"},
            ]}
            self.client = self

        def table(self, nome):
            return _Q(self, nome)

        def por_id(self, ident):
            return next(l for l in self.dados["integrations"] if l["id"] == ident)

    banco = Banco()
    # O que o `/instance/status` devolve quando a linha está logada.
    corpo = {"data": {"Connected": True, "LoggedIn": True,
                      "jid": "554799956540:12@s.whatsapp.net", "Name": "Amandus"}}

    ok = asyncio.run(CS._gravar_telefone_pareado(
        banco.por_id("i1"), corpo, db=banco))
    checar(ok is True, "gravou o telefone de uma corretora que não o tinha")
    checar(banco.por_id("i1")["paired_phone_e164"] == "+554799956540",
           "e é o número certo, em E.164",
           banco.por_id("i1")["paired_phone_e164"])

    # CONTROLE — silêncio da sonda NÃO apaga o que já está lá. Um refresh mudo
    # não pode desfazer o que o pareamento provou.
    antes = banco.por_id("i2")["paired_phone_e164"]
    asyncio.run(CS._gravar_telefone_pareado(
        banco.por_id("i2"), {"data": {"Connected": False, "LoggedIn": False}}, db=banco))
    checar(banco.por_id("i2")["paired_phone_e164"] == antes,
           "CONTROLE — sonda sem JID não apaga o telefone gravado")

    # CONTROLE — não reescreve o que já está igual. Sem isto seria um UPDATE
    # por corretora a cada cinco minutos, para sempre.
    de_novo = asyncio.run(CS._gravar_telefone_pareado(
        banco.por_id("i1"), corpo, db=banco))
    checar(de_novo is False,
           "CONTROLE — telefone que já está gravado não é reescrito")

    # E o gravador está no caminho que passa por TODAS as corretoras.
    fonte = _fonte_do_estado()
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
    checar("await _gravar_telefone_pareado(integracao, corpo)" in cmd,
           "a sonda do heartbeat grava o telefone",
           "é o único caminho que passa por toda corretora a cada 5 min")
    # A query do heartbeat precisa trazer `paired_phone_e164` — é com ele que o
    # gravador compara antes de escrever. Sem o campo, seria um UPDATE por
    # corretora a cada cinco minutos, para sempre.
    trecho_da_query = cmd.split('.eq("is_active", True)')[0][-500:]
    checar("paired_phone_e164" in trecho_da_query,
           "CONTROLE — e a query traz o campo para poder comparar antes",
           "sem ele, o gravador reescreveria o mesmo telefone a cada ciclo")


def _fonte_do_estado() -> str:
    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp", "channel_state.py")
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read()


def main() -> int:
    print("=" * 70)
    print('"CONECTADO" NÃO É O MESMO QUE "CHEGANDO"')
    print("=" * 70)
    teste_o_caso_que_custou_tres_dias()
    teste_nao_grita_duas_vezes_a_mesma_noticia()
    teste_a_conta_e_em_horas_e_o_limite_e_respeitado()
    teste_o_alarme_esta_no_laco_e_le_o_acervo()
    teste_o_telefone_pareado_e_gravado_para_TODAS_as_corretoras()

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
