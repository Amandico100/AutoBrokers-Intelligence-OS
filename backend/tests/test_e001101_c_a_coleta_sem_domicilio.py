# -*- coding: utf-8 -*-
"""G9 — domicílio não trava mais; o contato é do SEGURADO com WhatsApp; as
preferências viram enum ANTES do portal.

SPEC-EXTRA-001.10.1 C2. Chama o MOTOR (`build_portal_params`,
`o_que_falta`, `trava_o_pedido`) — nunca um regex sobre a pergunta (CLAUDE.md
§9.4).

## Decisões do Founder que este guarda segura
- D-E001101-05: domicílio FORA — o robô não pergunta e não oferece.
- D-E001101-04: contato = Corretor ("6") + celular e e-mail do SEGURADO +
  WhatsApp marcado. 📊 B0.12: nas 6 capturas, só Tipo 20 com
  `StatusEnvioWhatsapp:true` fez o portal responder `PossuiTelefoneRecebeWhatsapp:true`.
- D-E001101-02: a preferência de agenda coletada ANTES, sem travar.
"""
from __future__ import annotations

import os
import sys
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.agents.tools import portal_params as PP  # noqa: E402
from app.services import perguntas_do_portal_de_vidros as P  # noqa: E402

PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:400] if extra else ""))


# 💭 Fictício (CLAUDE.md §13.9).
PERFIL = {"nome": "Corretora Exemplo", "email": "operacao@exemplo.test",
          "telefone": "4830000000", "cpf_cnpj": "00000000000191"}
INFOCAP = {
    "ok": True,
    "policy": {"numapo": "000000", "seguradora": "LIBERTY SEGUROS S/A"},
    "vehicle": {"placa": "AAA0A91", "veiculo": "MODELO EXEMPLO 1.0", "chassi": "9XX0000000000000"},
    "client": {"nome": "Segurado Exemplo", "cep": "88000-000", "cidade": "Florianopolis",
               "estado": "SC", "telefone": "48900000000", "email": "segurado@exemplo.test"},
}
BASE = {"cpf_cnpj": "52998224725", "data_dano": "05/07/2026", "peca": "vidro de porta",
        "como_ocorreu": "ENCONTROU O VEICULO DANIFICADO", "onde_ocorreu": "urbano",
        "descricao": "o carro estava estacionado e o vidro da porta foi quebrado"}
ESPECIFICOS = {"cidade_para_o_servico": "Joinville/SC", "pelicula": "sim",
               "porta_dianteira_ou_traseira": "dianteira",
               "lado_motorista_ou_carona": "do lado do carona"}
QUARTA = date(2026, 9, 23)  # 📊 23/09/2026 é uma quarta-feira


def g9_domicilio_nao_trava() -> None:
    print("\n[G9-domicilio] a modalidade saiu da coleta e do que trava")
    checar("onde_realizar_o_servico" not in PP.TRANSPORTAVEIS,
           "onde_realizar_o_servico NAO esta em TRANSPORTAVEIS")
    faltam = {p.campo for p in P.o_que_falta("vidro de porta", {})}
    checar("onde_realizar_o_servico" not in faltam,
           "e o motor nao a pergunta mais (o_que_falta)", sorted(faltam))
    params, erro = PP.build_portal_params({**BASE, "especificos": dict(ESPECIFICOS)},
                                          PERFIL, INFOCAP)
    checar(params is not None and erro is None,
           "sem a modalidade, o pedido NASCE", (erro or "")[:200])
    checar(params and params["especificos"].get("onde_realizar_o_servico") == "loja",
           "e vai 'loja' por padrao", (params or {}).get("especificos"))
    from portal_worker.journeys.vidros_lanternas import preferencia_de_atendimento

    checar(preferencia_de_atendimento("loja") == "loja",
           "📊 o caminho DOM (adaptive -> preferencia_de_atendimento) entende 'loja'",
           preferencia_de_atendimento("loja"))
    checar("onde_realizar_o_servico" not in PP.descricao_da_tool(),
           "a description gerada nao cobra mais a modalidade")


def g9_o_contato_e_do_segurado() -> None:
    print("\n[G9-contato] Corretor ('6') + celular/e-mail do SEGURADO + WhatsApp")
    params, _ = PP.build_portal_params({**BASE, "especificos": dict(ESPECIFICOS)},
                                       PERFIL, INFOCAP)
    c = (params or {}).get("contato") or {}
    checar(c.get("relacao") == "6", "relacao '6' (Corretor)", c.get("relacao"))
    checar(c.get("tipo_telefone") == "segurado", "tipo_telefone 'segurado'", c.get("tipo_telefone"))
    checar(c.get("recebe_whatsapp") is True, "recebe_whatsapp True", c.get("recebe_whatsapp"))
    checar(c.get("telefone") == INFOCAP["client"]["telefone"],
           "o telefone e o do SEGURADO, da InfoCap")
    checar(c.get("email_segurado") == INFOCAP["client"]["email"]
           and c.get("email_corretora") == PERFIL["email"],
           "e-mail do segurado (InfoCap) + e-mail da corretora (perfil, D-03)")
    # CONTROLE: sem celular do segurado, cai para a corretora COM o tipo dizendo
    # a verdade — e sem marcar WhatsApp no número da corretora.
    sem_tel = {**INFOCAP, "client": {**INFOCAP["client"], "telefone": ""}}
    p2, _ = PP.build_portal_params({**BASE, "especificos": dict(ESPECIFICOS)}, PERFIL, sem_tel)
    c2 = (p2 or {}).get("contato") or {}
    checar(c2.get("tipo_telefone") == "corretora" and c2.get("recebe_whatsapp") is False,
           "CONTROLE: sem celular do segurado => tipo 'corretora' e WhatsApp desmarcado", c2)


def g9_preferencia_de_agenda() -> None:
    print("\n[G9-agenda] 4 frases reais normalizam; 1 nao — e nenhuma trava")
    casos = (
        ("amanhã de manhã", {"a_partir_de": "24/09/2026", "periodo": "manha"}),
        ("pode ser sexta à tarde", {"a_partir_de": "25/09/2026", "periodo": "tarde"}),
        ("tanto faz", {"a_partir_de": "23/09/2026", "periodo": "qualquer"}),
        ("a partir do dia 30/09, de manhã", {"a_partir_de": "30/09/2026", "periodo": "manha"}),
    )
    for frase, esperado in casos:
        got = PP.normalizar_preferencia_agenda(frase, QUARTA)
        checar(got == esperado, f"'{frase}' -> {esperado}", got)
    checar(PP.normalizar_preferencia_agenda("sei lá, vou ver com meu marido", QUARTA) == {},
           "CONTROLE: 'sei la, vou ver…' NAO normaliza => nao vai ao portal")
    checar(PP.normalizar_preferencia_agenda("de noite", QUARTA) == {},
           "'de noite' nao e periodo do portal => nao vai")
    checar(PP.normalizar_preferencia_agenda("01/01/2020 de manhã", QUARTA) == {},
           "'a partir de' um dia que ja passou nao existe")

    params, erro = PP.build_portal_params(
        {**BASE, "especificos": {**ESPECIFICOS, "preferencia_agenda": "sexta à tarde"}},
        PERFIL, INFOCAP)
    pref = ((params or {}).get("especificos") or {}).get("preferencia_agenda")
    checar(isinstance(pref, dict) and set(pref) == {"a_partir_de", "periodo"}
           and pref["periodo"] == "tarde",
           "build_portal_params manda o ENUM do contrato §5", pref)
    p_ruim, _ = PP.build_portal_params(
        {**BASE, "especificos": {**ESPECIFICOS, "preferencia_agenda": "sei lá"}},
        PERFIL, INFOCAP)
    checar(p_ruim is not None and "preferencia_agenda" not in p_ruim["especificos"],
           "resposta que nao normaliza SAI (a frase crua nunca cruza a fronteira)",
           (p_ruim or {}).get("especificos"))

    pergunta = P.pergunta_do_campo("preferencia_agenda")
    checar(pergunta is not None and not PP.trava_o_pedido(pergunta),
           "preferencia_agenda NAO trava o pedido")
    for peca in ("vidro de porta", "para-brisa", "vigia", "lanterna", "farol", "retrovisor"):
        faltam = {p.campo for p in P.o_que_falta(peca, {})}
        checar("preferencia_agenda" in faltam, f"'{peca}': a preferencia de agenda e PEDIDA",
               sorted(faltam))
    checar("preferencia_agenda" not in {p.campo for p in P.o_que_falta("lataria", {})},
           "CONTROLE: a lataria nao agenda — nao pergunta agenda")
    # e pedida ANTES: aparece na mensagem ao agente quando algo ainda trava
    msg, err = PP.build_portal_params({**BASE, "especificos": {"cidade_para_o_servico": "Joinville/SC"}},
                                      PERFIL, INFOCAP)
    checar(msg is None and "preferencia_agenda" in (err or "") and "NAO travam" in (err or ""),
           "a mensagem ao agente pede a preferencia e diz que ela nao trava", (err or "")[-400:])


def g9_preferencia_de_vistoria() -> None:
    print("\n[G9-vistoria] so na lataria, link x loja, sem travar")
    faltam = {p.campo for p in P.o_que_falta("lataria", {})}
    checar("preferencia_vistoria" in faltam, "lataria: a preferencia de vistoria e pedida",
           sorted(faltam))
    checar("preferencia_vistoria" not in {p.campo for p in P.o_que_falta("para-brisa", {})},
           "CONTROLE: para-brisa nao pergunta vistoria")
    checar(not PP.trava_o_pedido(P.pergunta_do_campo("preferencia_vistoria")),
           "e ela NAO trava")
    for frase, esperado in (("prefiro receber o link no celular", "link"),
                            ("levo na loja", "loja"), ("tanto faz", ""),
                            ("link ou loja, qualquer um", "")):
        checar(PP.normalizar_preferencia_vistoria(frase) == esperado,
               f"'{frase}' -> '{esperado}'", PP.normalizar_preferencia_vistoria(frase))


if __name__ == "__main__":
    print("=" * 72)
    print("G9 — a coleta sem domicilio, com contato do segurado e preferencias")
    print("=" * 72)
    g9_domicilio_nao_trava()
    g9_o_contato_e_do_segurado()
    g9_preferencia_de_agenda()
    g9_preferencia_de_vistoria()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
