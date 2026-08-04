"""SPEC-020 P3 + SPEC-025 - portal_action logica pura (build_portal_params + format_result).

SPEC-025: os fatos (placa/veiculo/endereco/seguradora) vem da InfoCap (arg infocap);
o LLM nao fornece placa/local. normalize_insurer traduz Liberty->Yelum.

Rodar: python backend/tests/test_spec020_portal_action.py
"""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


# O QUE MUDOU NO CARREGAMENTO (bloco 7.5): `portal_params` passou a importar o
# catalogo de perguntas do portal. Os pacotes `app.*` continuam sendo stubs —
# `app/services/__init__.py` puxa langchain/qdrant/minio e esta suite roda sem
# eles —, entao as dependencias reais entram por CAMINHO, pre-registradas em
# sys.modules. E `backend/` vai para o sys.path porque o catalogo importa
# `identidade_peca` do `portal_worker`: o vocabulario de peca e UM SO, e ele
# mora la desde a SPEC-020.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for name in ("app", "app.agents", "app.agents.tools", "app.services"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []


def _carregar(dotted, rel):
    spec = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


_carregar("app.services.attendance_ficha", "app/services/attendance_ficha.py")
_carregar("app.services.perguntas_do_portal_de_vidros",
          "app/services/perguntas_do_portal_de_vidros.py")
pp = _carregar("app.agents.tools.portal_params", "app/agents/tools/portal_params.py")

PROFILE = {"nome": "Auto Fleet Corretora", "email": "operacional@autofleet.com.br", "telefone": "4833646664", "cpf_cnpj": "00000000000191"}

# Retorno REAL do vehicle lookup (formato do infocap_vehicle_item, dados do probe ao vivo)
INFOCAP = {
    "ok": True, "status": "found",
    "policy": {"numapo": "312520261149211", "codfil": "1", "nosnum": "99793",
               "seguradora": "LIBERTY SEGUROS S/A", "seguradora_abrev": "LIBE",
               "inivig": "04/05/2026", "fimvig": "04/05/2027", "active": True},
    "vehicle": {"placa": "QJQ0A91", "chassi": "98867513WJKH74022",
                "veiculo": "COMPASS LIMITED 2.0 4X2 16V AUT. (FLEX)", "fipe": "170470", "ano": "2018"},
    "client": {"nome": "RAFAEL LACAU DA SILVEIRA", "cpf_cnpj": "03074327936",
               "email": "rafael@resultaseguros.com.br", "telefone": "4832331732",
               "logradouro": "RUA CAPITÃO ROMUALDO DE BARROS", "numero": "705", "complemento": "CASA 20",
               "bairro": "SACO DOS LIMÕES", "cidade": "FLORIANÓPOLIS", "estado": "SC", "cep": "88040-600"},
}

FLAT = {"cpf_cnpj": "03074327936", "data_dano": "05/07/2026",
        "peca": "vidro de porta", "como_ocorreu": "encontrou o veiculo danificado", "onde_ocorreu": "urbano",
        "descricao": "o carro estava estacionado e o vidro da porta foi quebrado"}


def run():
    print("== SPEC-020/025 - portal_action (params) ==\n")

    # normalize_insurer (C2)
    check("LIBERTY SEGUROS S/A -> Yelum", pp.normalize_insurer("LIBERTY SEGUROS S/A") == "Yelum")
    check("LIBE -> Yelum", pp.normalize_insurer("LIBE") == "Yelum")
    check("Yelum -> Yelum", pp.normalize_insurer("YELUM SEGURADORA") == "Yelum")
    check("TOKIO MARINE -> Tokio Marine", pp.normalize_insurer("TOKIO MARINE SEGURADORA") == "Tokio Marine")
    check("PORTO -> Porto Seguro", pp.normalize_insurer("PORTO SEGURO CIA") == "Porto Seguro")
    check("desconhecida -> title", pp.normalize_insurer("ESSOR") == "Essor")

    # faltando dado obrigatorio -> erro
    p, e = pp.build_portal_params({"cpf_cnpj": "030"}, PROFILE, INFOCAP)
    check("faltando data -> erro", p is None and e and "Faltam dados" in e)

    # perfil de acionamento vazio -> erro instrutivo
    p, e = pp.build_portal_params(FLAT, {}, INFOCAP)
    check("sem perfil de acionamento -> erro", p is None and e and "Perfil de Acionamento" in e)

    # C1: fatos da InfoCap (LLM NAO fornece placa/local)
    p, e = pp.build_portal_params(FLAT, PROFILE, INFOCAP)
    check("valido -> sem erro", e is None and p is not None, e)
    check("insurer normalizado Liberty->Yelum", p["insurer_name"] == "Yelum")
    check("placa REAL da InfoCap", p["placa"] == "QJQ0A91")
    check("segurado.apolice da InfoCap", p["segurado"]["apolice"] == "312520261149211")
    check("segurado.chassi da InfoCap", p["segurado"]["chassi"] == "98867513WJKH74022")
    check("segurado.ultimos_6_chassi", p["segurado"]["ultimos_6_chassi"] == "H74022")
    check("segurado.veiculo da InfoCap", "COMPASS" in p["segurado"]["veiculo"])
    check("local do cadastro (ASCII-fold p/ digitar no portal)", p["local"]["estado"] == "SC" and p["local"]["cidade"] == "Florianopolis", p["local"])
    check("local.cep formatado", p["local"]["cep"] == "88040-600")
    check("endereco composto e ASCII-fold", "CAPITAO ROMUALDO" in p["segurado"]["endereco"] and "LIMOES" in p["segurado"]["endereco"], p["segurado"]["endereco"])
    check("solicitante = Corretor", p["solicitante"]["relacao"] == "Corretor")
    check("dano do LLM (julgamento)", p["dano"]["peca"] == "vidro de porta")
    check("confirm sempre False (nunca envia sozinha)", p["confirm"] is False)

    # sem placa na InfoCap -> pede placa_informada (fallback honesto, nunca inventa)
    sem_placa = {**INFOCAP, "vehicle": {**INFOCAP["vehicle"], "placa": ""}}
    p, e = pp.build_portal_params(FLAT, PROFILE, sem_placa)
    check("sem placa -> pede placa_informada", p is None and e and "placa_informada" in e)
    p, e = pp.build_portal_params({**FLAT, "placa_informada": "qjq0a91"}, PROFILE, sem_placa)
    check("placa_informada cobre o buraco (upper)", e is None and p["placa"] == "QJQ0A91")

    # sem seguradora -> erro (nunca chuta)
    p, e = pp.build_portal_params(FLAT, PROFILE, {**INFOCAP, "policy": {}})
    check("sem seguradora -> erro", p is None and e and "seguradora" in e.lower())

    # format_result
    check("done -> concluido", "concluido" in pp.format_result({"status": "done", "evidence": {"message": "protocolo 123"}}).lower())
    r80 = pp.format_result({"status": "needs_human", "evidence": {"message": "cheguei na confirmacao (80%) - aprove para enviar", "stage_80": "Confirme a peca"}})
    check("80% -> mensagem de pedido aberto", "confirmacao" in r80.lower() and "aberto" in r80.lower() or "abri o pedido" in r80.lower())
    nh = pp.format_result({"status": "needs_human", "evidence": {"campo": "peca", "opcoes": ["VIDRO DE PORTA", "PARABRISA"], "message": "escolha"}})
    check("needs_human lista opcoes", "VIDRO DE PORTA" in nh)
    check("failed -> nao consegui", "nao consegui" in pp.format_result({"status": "failed", "error": "x"}).lower())
    check("queued -> worker nao processou", "worker" in pp.format_result({"status": "queued"}).lower())

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
