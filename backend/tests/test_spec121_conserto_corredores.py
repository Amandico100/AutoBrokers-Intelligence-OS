# -*- coding: utf-8 -*-
"""🔴 SPEC-121 · CONSERTO ÚNICO, parte Y (corredores e textos) — pelo MOTOR, com telas REAIS.

[B1] a COSTURA F5 × F1: o motivo que `antes_de_acionar` escreve atravessa o
     `HumanHandoffTool._avisar_suporte` REAL (dublê só em `enviar_ao_grupo`, a borda)
     e chega ao grupo como PEDIDO DE AJUDA — nunca "🚨 NOVO SINISTRO" (red team B1).
     CONTROLE: raio continua sinistro (D10).
[K2] `cr_outros_assuntos` ('4' = Sinistro/Informações) só decide DENTRO do carro
     reserva; com a tela real 39e395bb, nenhum outro serviço recebe '4'.
[K4] nada escrito PARA A EQUIPE vai ao segurado: todo `client_message` fala com o
     segurado; a Tokio (link de autoatendimento) vai a uma PESSOA com `para_a_equipe`.
[P3] azul: a tela "Não entendi… digite um CPF ou CNPJ válido" (ab045fdd) tem passo.
[K5] `_so_digitos` tem UMA definição (o número do endereço tem nome próprio).

⛔ Nenhum dado pessoal: slots fictícios; telas do acervo mascarado. Nada sai: o envio
ao grupo é dublê e `SUPABASE_URL` aponta para lugar nenhum.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import insurer_dispatch_service as IDS  # noqa: E402

OK = FAIL = 0
Q = chr(10)


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


CASO = {"titular_cpf": "11122233344", "telefone_contato": "48999998888",
        "problema_descricao": "batida, o carro está na oficina", "veiculo_placa": "QQQ1A11",
        "apolice_numero": "1234567", "carro_reserva_motivo": "sinistro", "sinistro_numero": "12345678",
        "carro_reserva_condutor_nome": "Pessoa Teste", "carro_reserva_condutor_cpf": "11122233344",
        "carro_reserva_cidade": "Cidade Teste", "carro_reserva_data_hora": "08/10 às 15h",
        "carro_reserva_telefone": "48999998888", "carro_reserva_cnh_e_cartao": "sim"}
TELAS_CR = json.load(open(os.path.join(RAIZ, "tests", "fixtures", "spec121_carro_reserva_telas.json"),
                          encoding="utf-8"))


def na_ura(ref, sub, slots):
    s = IDS.new_dispatch_session(case_id="t121y", company_id="co", playbook_ref=ref,
                                 subservice=sub, slots=dict(slots))
    s["state"] = "ura"
    return s


def saida(s, tela):
    n0 = len([x for x in s.get("transcript") or [] if x.get("direction") == "out"])
    s = IDS.handle_insurer_message(s, tela)
    outs = [x.get("text") for x in s.get("transcript") or [] if x.get("direction") == "out"][n0:]
    return s, (outs or [None])[-1]


print("=" * 74)
print("[B1] 🔴 a COSTURA: o motivo de antes_de_acionar pelo _avisar_suporte REAL")
print("=" * 74)
import datetime as _dt  # noqa: E402

from app.agents.tools import human_handoff as HH  # noqa: E402
from app.services import o_grupo_so_o_que_importa as G  # noqa: E402

_capturado = []


async def _dublê_do_grupo(db, **kw):  # a BORDA: nada sai
    _capturado.append(kw)
    return {"enviado": False, "calado": True, "motivo": "dublê"}


G.enviar_ao_grupo = _dublê_do_grupo
TERCA = _dt.datetime(2026, 10, 6, 11, 0)
CONVERSA = {"id": "00000000-0000-4000-8000-000000000001", "user_phone": "", "user_name": "",
            "ficha": {"servico": "assistencia"}}
PEDIDOS = [
    ("yelum sem nº do processo", CP.resolve_playbook_ref("yelum", "auto"), "carro_reserva",
     {**CASO, "sinistro_numero": "não tenho"}, {"INSURER_CONTACT_YELUM_CARRO_RESERVA": "5500000000000"}),
    ("yelum canal desligado", CP.resolve_playbook_ref("yelum", "auto"), "carro_reserva", CASO, {}),
    ("yelum motivo pane", CP.resolve_playbook_ref("yelum", "auto"), "carro_reserva",
     {**CASO, "carro_reserva_motivo": "pane depois do sinistro, bati o carro"}, {}),
    ("zurich por sinistro", CP.resolve_playbook_ref("zurich", "auto"), "carro_reserva", CASO, {}),
    ("zurich por PANE", CP.resolve_playbook_ref("zurich", "auto"), "carro_reserva",
     {**CASO, "carro_reserva_motivo": "pane mecânica"}, {}),
    ("hdi portão", CP.resolve_playbook_ref("hdi", "residencial"), "eletricista",
     {"problema_descricao": "o portão eletrônico não abre"}, {}),
]


def _avisar(reason):
    _capturado.clear()
    tool = HH.HumanHandoffTool.__new__(HH.HumanHandoffTool)
    try:
        tool.supabase_client = object()
    except Exception:  # noqa: BLE001 — pydantic congelado
        object.__setattr__(tool, "supabase_client", object())
    asyncio.run(tool._avisar_suporte("co", CONVERSA, reason, prova=G.PROVA_PEDIDO_DO_AGENTE))
    return _capturado[0] if _capturado else {}


for rot, ref, sub, slots, env in PEDIDOS:
    r = CP.antes_de_acionar(ref, sub, slots, agora=TERCA, env=env) or {}
    reason = CP.motivo_com_codigo(r) if r else ""
    kw = _avisar(reason)
    primeira = (str(kw.get("texto") or "").splitlines() or [""])[0]
    certo(kw.get("tipo") == G.TIPO_PEDIDO_DE_AJUDA and "SINISTRO" not in primeira,
          f"{rot} ({r.get('codigo')}) → o grupo recebe PEDIDO DE AJUDA",
          f"tipo={kw.get('tipo')!r} 1ª linha={primeira!r}")
r = CP.antes_de_acionar(CP.resolve_playbook_ref("hdi", "residencial"), "eletricista",
                        {"problema_descricao": "caiu um raio e queimou o motor do portão"}) or {}
kw = _avisar(CP.motivo_com_codigo(r))
certo(kw.get("tipo") == G.TIPO_SINISTRO,
      "🔴 CONTROLE D10: raio (sinistro_danos_eletricos) continua chegando como SINISTRO",
      f"tipo={kw.get('tipo')!r}")

print()
print("=" * 74)
print("[K2] 🔴 '4 - Sinistro (Informações…)' só no CARRO RESERVA — tela real 39e395bb")
print("=" * 74)
YL = CP.resolve_playbook_ref("yelum", "auto")
PB_YL = CP.get_playbook(YL)
_s39 = next(x for x in TELAS_CR if x["sessao"] == "39e395bb")["telas"]
OUTROS = next(t["texto"] for t in _s39 if "se quiser falar sobre outros assuntos" in t["texto"].lower())
FORA_DO_HORARIO = next(t["texto"] for t in _s39 if "fora do nosso hor" in t["texto"].lower())
st = CP.match_ura_step(PB_YL, OUTROS, subservice="carro_reserva")
certo((st or {}).get("step") == "cr_outros_assuntos"
      and CP.render_reply(st, CASO).get("reply") == "4",
      "carro reserva: a tela real → '4' (o caminho do carro reserva, 📊 10 de 10)", str((st or {}).get("step")))
for sub in ("guincho", "bateria", "chaveiro", "pneu", "socorro_mecanico", "sinistro", None):
    st = CP.match_ura_step(PB_YL, OUTROS, subservice=sub)
    certo((st or {}).get("step") != "cr_outros_assuntos",
          f"{sub or '(sem serviço)'}: o passo do carro reserva NÃO decide nesta tela",
          f"passo={(st or {}).get('step')!r}")
    s, r = saida(na_ura(YL, sub or "guincho", CASO), OUTROS)
    certo(r != "4", f"   e pelo MOTOR ({sub or 'guincho'}) a tecla '4' não sai", f"respondeu {r!r}")
st = CP.match_ura_step(PB_YL, FORA_DO_HORARIO, subservice="carro_reserva")
certo((st or {}).get("step") != "cr_outros_assuntos",
      "🔴 CONTROLE: o menu FORA DO HORÁRIO ('*4* - Informação de Sinistro') não é o do "
      "carro reserva — a âncora exige o rótulo ao lado do 4", f"passo={(st or {}).get('step')!r}")

print()
print("=" * 74)
print("[K4] 🔴 o que é escrito PARA A EQUIPE nunca vai ao segurado")
print("=" * 74)
# O que se lê aqui é o `client_message` que `dispatch_router` (estado `encaminhado`)
# manda AO SEGURADO. Texto da equipe tem forma: imperativo ao atendente, dossiê,
# "da corretora", "é tarefa de", marcador 🔴.
_RX_DA_EQUIPE = re.compile(
    r"(?i)dossi[êe]|🔴|\bencaminhe\b|\brepasse\b|pessoa da corretora|n[ãa]o [ée] tarefa|"
    r"endere[çc]o de mem[óo]ria|n[ãa]o h[áa] chamado aberto")
vistos = 0
for ref, pb in CP._PLAYBOOKS.items():
    for sub, d in (pb.get("subservices") or {}).items():
        ref_d = (d or {}).get("referral") or {}
        if not ref_d:
            continue
        vistos += 1
        texto = str(ref_d.get("client_message") or "")
        certo(texto and not _RX_DA_EQUIPE.search(texto),
              f"{ref.split('-whatsapp')[0]}/{sub}: o client_message fala com o SEGURADO",
              f"{_RX_DA_EQUIPE.search(texto).group(0) if _RX_DA_EQUIPE.search(texto) else ''!r} em {texto[:90]!r}")
certo(vistos >= 8, f"todos os encaminhamentos foram lidos ({vistos})")
TK = CP.resolve_playbook_ref("tokio", "auto")
for sub in ("guincho", "bateria", "pneu", "chaveiro"):
    rf = CP.subservice_referral(CP.get_playbook(TK), sub)
    certo(rf.get("exige_pessoa") and "PESSOA da corretora" in str(rf.get("para_a_equipe")),
          f"tokio/{sub}: a instrução da equipe mora em `para_a_equipe`, e o desenho exige pessoa")
s = na_ura(TK, "guincho", CASO)
s["referral"] = {**CP.subservice_referral(CP.get_playbook(TK), "guincho"), "aguardando": 0}
s = IDS._resolver_encaminhamento(s)
certo(s.get("state") == "needs_human" and str(s.get("reason")) == "handoff_trigger:encaminhamento_exige_pessoa",
      "tokio/guincho: o encaminhamento vai a uma PESSOA (nunca fecha 'resolvido' sem ninguém avisado)",
      f"state={s.get('state')!r} reason={s.get('reason')!r}")
certo("_" not in IDS.motivo_em_portugues(s.get("reason") or ""),
      "e o motivo chega em português à atendente", IDS.motivo_em_portugues(s.get("reason") or ""))
# CONTROLE: o encaminhamento que É do segurado (Porto vidros) continua fechando `encaminhado`
PT = CP.resolve_playbook_ref("porto", "auto")
s = IDS.start_dispatch(IDS.new_dispatch_session(
    case_id="t121y", company_id="co", playbook_ref=PT, subservice="vidros",
    slots={"titular_cpf": "11122233344", "veiculo_placa": "ABC1D23", "problema_descricao": "para-brisa trincado",
           "quando": "amanha", "telefone_contato": "48991234567"}))
for tela in ("O que você precisa? Guincho (reboque) Bateria Troca de pneu Conserto de vidro "
             "(Inclui retrovisor, farol ou lanterna) Chaveiro para o veículo Táxi",
             "Certo. Para conserto ou reparo de vidro, retrovisor, farol ou lanterna, é necessário "
             "*preencher o formulário* de sinistro de vidros abaixo", "https://porto.vc/reparovidros"):
    s = IDS.handle_insurer_message(s, tela)
certo(s.get("state") == "encaminhado" and "classe de bônus" in str((s.get("referral") or {}).get("client_message")),
      "🔴 CONTROLE: porto/vidros continua ENCAMINHADO ao segurado, com o texto do segurado",
      f"state={s.get('state')!r}")
_router = open(os.path.join(RAIZ, "app", "services", "dispatch_router.py"), encoding="utf-8").read()
_bloco = _router.split('if state == "encaminhado":', 1)[1].split('if state == "captured":', 1)[0]
certo('referral.get("exige_pessoa")' in _bloco and 'aviso = ""' in _bloco,
      "cinto no roteador: encaminhamento `exige_pessoa` não manda nada ao segurado")

print()
print("=" * 74)
print("[P3] azul: 'Não entendi… digite um CPF ou CNPJ válido' (📊 ab045fdd) tem passo")
print("=" * 74)
AZ = CP.resolve_playbook_ref("azul", "auto")
RECUSA = ("Não entendi a sua resposta. Por favor, digite um *CPF ou CNPJ válido*." + Q + Q +
          "Exemplo de CPF: {CPF}" + Q + "Exemplo de CNPJ: {CNPJ}")
s, r = saida(na_ura(AZ, "guincho", {**CASO, "titular_cpf": "111.222.333-44"}), RECUSA)
certo(r == "11122233344" and s.get("state") == "ura",
      "a recusa recebe UMA repetição, só com dígitos (📊 11 dígitos aceito 1/1)", f"respondeu {r!r}")
SEGUNDA = "Desculpe, ainda não entendi a sua resposta. Por favor, digite um *CPF ou CNPJ válido*, com números."
certo((CP.match_ura_step(CP.get_playbook(AZ), SEGUNDA, "guincho") or {}).get("step") != "cpf_invalido_azul",
      "🔴 CONTROLE: a SEGUNDA recusa ('ainda não entendi') não repete de novo")

print()
print("=" * 74)
print("[K5] uma extração de dígitos, dois nomes")
print("=" * 74)
_fonte = open(os.path.join(RAIZ, "app", "services", "corridor_playbooks.py"), encoding="utf-8").read()
certo(len(re.findall(r"^def _so_digitos\(", _fonte, re.M)) == 1, "`_so_digitos` tem UMA definição")
certo(CP._FORMATOS_DA_RESPOSTA["so_digitos"] is CP._so_digitos
      and CP._so_digitos("111.222.333-44", {}, "") == "11122233344",
      "o nome do módulo é o MESMO formato que o dicionário usa")
certo(CP._digitos_do_numero("0125") == "125" and CP._digitos_do_numero("s/n") == "",
      "o número do endereço compara sem zero à esquerda (comportamento de antes)")

print()
print("=" * 74)
print(f"  {OK} verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
