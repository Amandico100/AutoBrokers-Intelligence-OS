# -*- coding: utf-8 -*-
"""SPEC-077 — o Portal Intelligence Lab, testado onde ele decide.

A disciplina é a mesma da 074 e da 075: **inspeção de fonte não prova
comportamento**. Cada afirmação sobre o que o código FAZ é executada, e cada
bloco prova três coisas — o caso bom passa, o ruim é negado, e os dois são
DIFERENTES.

E há uma coisa a mais aqui, que as SPECs anteriores não tinham: parte do que
este módulo produz é **conhecimento**. Um inferidor que devolve um OpenAPI
bonito e errado é pior que nenhum, porque alguém vai construir em cima. Por
isso os blocos I* rodam contra os HAR REAIS de `docs/intake/` — e comparam o
que a ferramenta acha com o que eu achei à mão nas SPECs 073 e 074.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS = FAIL = SKIP = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


def pular(nome, motivo):
    global SKIP
    SKIP += 1
    print(f"  [--] {nome} — {motivo}")


for _n in ("app", "app.services", "app.services.portals",
           "app.services.portals.lab"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = [str(ROOT / _n.replace(".", "/"))]


def _carregar(dotted, rel):
    sp = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    mo = importlib.util.module_from_spec(sp)
    sys.modules[dotted] = mo
    sp.loader.exec_module(mo)
    return mo


T = _carregar("app.services.portals.lab.trafego",
              "app/services/portals/lab/trafego.py")
I = _carregar("app.services.portals.lab.inferir",
              "app/services/portals/lab/inferir.py")
CI = _carregar("app.services.portals.lab.ciclo",
               "app/services/portals/lab/ciclo.py")

import portal_worker.deep_trace as DT   # noqa: E402
from portal_worker import profiler as PF  # noqa: E402

# Os HAR moram FORA do git (`docs/intake/` está no .gitignore, porque contêm
# PII de segurado). O teste degrada honestamente quando não os encontra: pula e
# diz por quê, nunca inventa um verde.
HARS = (ROOT.parents[1] / "AutoBrokers-Opus-Exec" / "docs" / "intake" /
        "MATERIAIS")


def _hars(sub: str = "") -> list:
    base = HARS / sub if sub else HARS
    if not base.exists():
        return []
    return sorted(base.rglob("*.har"))


# ==========================================================================
print("\n[T1] o formato unico: HAR e DeepTrace convergem")
# ==========================================================================
c_leitura = T.Chamada(metodo="GET", url="https://api.x.com/a?b=1",
                      status=200, content_type_resp="application/json")
c_escrita = T.Chamada(metodo="POST", url="https://api.x.com/a", status=201)
check("T1: GET nao e escrita", not c_leitura.escreve)
check("T1 CONTROLE: POST e escrita", c_escrita.escreve)
check("T1: host e caminho saem da URL",
      c_leitura.host == "api.x.com" and c_leitura.caminho == "/a")
check("T1: query e lida", c_leitura.query == {"b": "1"})
check("T1: URL quebrada nao levanta",
      T.Chamada(metodo="GET", url="http://[").host == "")

ev = [{"requestId": "r1", "url": "https://api.x.com/a", "method": "GET",
       "status": 200, "mime_type": "application/json"},
      {"requestId": "r1", "response_body": '{"ok":true}'}]
tr = T.importar_deep_trace(ev, host_portal="x.com", rotulo="t")
check("T1: o join do DeepTrace e por requestId, e funde os dois eventos",
      len(tr) == 1 and tr.chamadas[0].corpo_resp == '{"ok":true}')
ev2 = ev + [{"requestId": "r2", "url": "https://api.x.com/a", "method": "GET",
             "status": 500}]
check("T1 CONTROLE: mesma URL, requestId diferente -> DUAS chamadas",
      len(T.importar_deep_trace(ev2)) == 2)

# ==========================================================================
print("\n[T2] cabecalho sensivel NAO ENTRA — nao 'entra e e redigido'")
# ==========================================================================
for h in ("Authorization", "cookie", "Set-Cookie", "token_autorizacao",
          "X-Api-Key", "x-csrf-token"):
    check(f"T2: `{h}` e barrado na entrada", not T._cabecalho_entra(h))
check("T2 CONTROLE: cabecalho comum entra", T._cabecalho_entra("content-type"))
check("T2 CONTROLE: e um nome inventado tambem entra",
      T._cabecalho_entra("x-portal-versao"))

# ==========================================================================
print("\n[T3] forma acumulada: uma amostra nao decide obrigatoriedade")
# ==========================================================================
f1 = I.Forma()
f1.vista_em = 1
f1.de_um_total_de = 1
I.acumular(f1, {"a": 1, "b": "x"})
check("T3: com UMA amostra, nada e declarado obrigatorio",
      not f1.filhos["a"].obrigatoria, "obrigatorio com 1 amostra e um chute")

f2 = I.Forma()
for amostra in ({"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3}):
    f2.vista_em += 1
    f2.de_um_total_de += 1
    I.acumular(f2, amostra)
check("T3 CONTROLE: com 3 amostras, `a` (sempre presente) e obrigatoria",
      f2.filhos["a"].obrigatoria)
check("T3: e `b` (ausente numa) NAO e", not f2.filhos["b"].obrigatoria)
check("T3: os dois casos diferem",
      f2.filhos["a"].obrigatoria != f2.filhos["b"].obrigatoria)

f3 = I.Forma()
for v in ({"x": 1}, {"x": None}):
    f3.vista_em += 1
    f3.de_um_total_de += 1
    I.acumular(f3, v)
check("T3: campo que as vezes vem null vira anulavel", f3.filhos["x"].anulavel)
esq = I.para_json_schema(f3)
check("T3: e o schema declara a uniao",
      esq["properties"]["x"]["type"] == ["integer", "null"],
      esq["properties"]["x"])

# ==========================================================================
print("\n[T4] enum observado NAO vira enum de contrato")
# ==========================================================================
f4 = I.Forma()
for v in ("ABERTO", "FECHADO", "ABERTO", "FECHADO", "ABERTO"):
    f4.vista_em += 1
    f4.de_um_total_de += 1
    I.acumular(f4, v)
e4 = I.para_json_schema(f4)
check("T4: valores repetidos viram `x-enum-observado`", "x-enum-observado" in e4)
check("T4: 🔴 e NUNCA `enum` — nos so sabemos o que apareceu, nao o que existe",
      "enum" not in e4, e4)

# ==========================================================================
print("\n[T5] confianca mede EVIDENCIA, nao qualidade")
# ==========================================================================
ep_pobre = I.Endpoint(metodo="GET", caminho="/a", host="h", amostras=1)
ep_pobre.status_vistos[200] = 1
ep_rico = I.Endpoint(metodo="GET", caminho="/a", host="h", amostras=8)
ep_rico.status_vistos[200] = 7
ep_rico.status_vistos[400] = 1
ep_rico.formas_resp[200] = I.Forma()
ep_rico.formas_resp[400] = I.Forma()
ep_rico.headers_vistos["token_autorizacao"] = 8
c_pobre, c_rico = I.avaliar(ep_pobre), I.avaliar(ep_rico)
check("T5: 1 amostra tira nota baixa", c_pobre.nota < 40, c_pobre.nota)
check("T5 CONTROLE: 8 amostras com erro e auth tiram alta",
      c_rico.nota >= 80, c_rico.nota)
check("T5: os dois diferem muito", c_rico.nota - c_pobre.nota >= 40)
check("T5: amostra unica e nomeada como lacuna",
      any("amostra unica" in g.lower() for g in c_pobre.lacunas), c_pobre.lacunas)
check("T5: o cabecalho de autorizacao e IDENTIFICADO quando existe",
      any("autorizacao" in m for m in c_rico.motivos), c_rico.motivos)

ep_escreve = I.Endpoint(metodo="POST", caminho="/a", host="h", amostras=9)
ep_escreve.status_vistos[200] = 9
ep_escreve.formas_resp[200] = I.Forma()
ep_escreve.forma_req = I.Forma()
c_esc = I.avaliar(ep_escreve)
check("T5: 🔴 endpoint de ESCRITA sempre avisa que idempotencia nao se infere",
      any("idempotencia" in g.lower() for g in c_esc.lacunas), c_esc.lacunas)
check("T5 CONTROLE: leitura NAO recebe esse aviso",
      not any("idempotencia" in g.lower() for g in c_rico.lacunas))

# ==========================================================================
print("\n[T6] nada nasce aprovado, e nao ha salto de degrau")
# ==========================================================================
doc = I.openapi_candidato(T.Trafego(chamadas=[
    T.Chamada(metodo="GET", url="https://api.x.com/a", status=200,
              content_type_resp="application/json", corpo_resp='{"a":1}'),
    T.Chamada(metodo="GET", url="https://api.x.com/a", status=200,
              content_type_resp="application/json", corpo_resp='{"a":2}'),
], rotulo="t", host_portal="x.com"))
ops = [op for caminho in doc["paths"].values() for op in caminho.values()]
check("T6: todo endpoint nasce OBSERVED",
      ops and all(o["x-estado"] == I.OBSERVED for o in ops))
check("T6: e cada um carrega o aviso de que e candidato",
      all("candidato" in o["x-aviso"] for o in ops))
check("T6: o documento inteiro avisa, no info",
      "CANDIDATO" in doc["info"]["description"])
check("T6: nenhum endpoint sai APPROVED",
      not any("APPROVED" in str(o["x-estado"]) for o in ops))

todas = {e: True for e in CI.EXIGENCIAS[CI.APPROVED_MATERIAL]}
p = CI.promover(CI.OBSERVED, CI.APPROVED_MATERIAL, todas)
check("T6: 🔴 salto de OBSERVED a APPROVED_MATERIAL e recusado MESMO com "
      "todas as evidencias", not p.permitida, p.motivo)
check("T6: e o motivo explica que cada degrau produz a evidencia do proximo",
      "salto" in p.motivo.lower(), p.motivo)
check("T6 CONTROLE: um degrau de cada vez passa",
      CI.promover(CI.OBSERVED, CI.CANDIDATE,
                  {"revisado_por_humano": True}).permitida)
check("T6: sem a evidencia, o mesmo degrau e recusado",
      not CI.promover(CI.OBSERVED, CI.CANDIDATE, {}).permitida)
falta = CI.promover(CI.APPROVED_READONLY, CI.APPROVED_MATERIAL,
                    {"revisado_por_humano": True, "replay_verde": True,
                     "canario_readonly_verde": True, "host_allowlisted": True})
check("T6: material sem aprovacao do Founder e recusado", not falta.permitida)
check("T6: e diz exatamente o que falta",
      "aprovacao_do_founder" in falta.faltam, falta.faltam)
check("T6 CONTROLE: rebaixar e SEMPRE permitido — fechar tem de ser barato",
      CI.promover(CI.APPROVED_MATERIAL, CI.OBSERVED, {}).permitida)

check("T7: escrita exige APPROVED_MATERIAL, e nada abaixo",
      not CI.pode_usar_em_producao(CI.APPROVED_READONLY, para_escrever=True))
check("T7 CONTROLE: leitura aceita APPROVED_READONLY",
      CI.pode_usar_em_producao(CI.APPROVED_READONLY))
check("T7: estado desconhecido nao usa", not CI.pode_usar_em_producao("qualquer"))

# ==========================================================================
print("\n[T8] drift: some quebra, aparece nao quebra")
# ==========================================================================
def _op(props, obrig=(), req_obrig=()):
    return {
        "requestBody": {"content": {"application/json": {"schema": {
            "type": "object", "required": list(req_obrig)}}}},
        "responses": {"200": {"content": {"application/json": {"schema": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in props},
            "required": list(obrig)}}}}},
    }


d_some = CI.comparar_operacao(_op(["a", "b"]), _op(["a"]), endpoint="GET /x")
check("T8: campo que SUMIU da resposta quebra",
      d_some.classe == CI.QUEBRA_RESPOSTA and d_some.quebra, d_some.classe)
d_novo = CI.comparar_operacao(_op(["a"]), _op(["a", "b"]), endpoint="GET /x")
check("T8 CONTROLE: campo que APARECEU e aditivo — os dois diferem",
      d_novo.classe == CI.ADITIVA and not d_novo.quebra, d_novo.classe)
d_req = CI.comparar_operacao(_op(["a"]), _op(["a"], req_obrig=["novo"]),
                             endpoint="GET /x")
check("T8: obrigatorio NOVO na requisicao quebra",
      d_req.classe == CI.QUEBRA_REQUISICAO)
d_menos = CI.comparar_operacao(_op(["a"], req_obrig=["x"]), _op(["a"]),
                               endpoint="GET /x")
check("T8 CONTROLE: obrigatorio que virou opcional NAO quebra",
      not d_menos.quebra, d_menos.classe)
d_igual = CI.comparar_operacao(_op(["a"]), _op(["a"]), endpoint="GET /x")
check("T8 CONTROLE: sem mudanca, sem drift", d_igual.classe == CI.SEM_MUDANCA)

veredito, frase = CI.veredito_de_drift([d_novo, d_some, d_igual])
check("T8: 🔴 UM drift que quebra fecha, por mais aditivos que sejam os outros",
      veredito == CI.QUEBRA_RESPOSTA, veredito)
check("T8: e a frase manda fechar a capacidade", "fechada" in frase.lower(), frase)
check("T8 CONTROLE: so aditivos deixam seguir",
      CI.veredito_de_drift([d_novo])[0] == CI.ADITIVA)
check("T8: endpoint que sumiu avisa que pode ser captura curta",
      any("captura curta" in d.detalhes[0]
          for d in CI.comparar_contratos({"paths": {"/a": {"get": _op(["x"])}}},
                                         {"paths": {}})))

# ==========================================================================
print("\n[T9] DeepTrace nunca AGE — a allowlist e a garantia")
# ==========================================================================
for m in ("Input.dispatchMouseEvent", "Runtime.evaluate", "Page.navigate",
          "Network.setCookie", "Fetch.enable", "Storage.clearDataForOrigin",
          "Target.createTarget", "Emulation.setDeviceMetricsOverride"):
    try:
        DT.validar_metodo_cdp(m)
        check(f"T9: `{m}` e recusado", False, "PASSOU e nao devia")
    except DT.MetodoCdpProibido:
        check(f"T9: `{m}` e recusado", True)
for m in ("Network.enable", "Network.getResponseBody", "Page.enable"):
    try:
        DT.validar_metodo_cdp(m)
        check(f"T9 CONTROLE: `{m}` (leitura) passa", True)
    except Exception as e:  # noqa: BLE001
        check(f"T9 CONTROLE: `{m}` (leitura) passa", False, str(e))
check("T9: a lista e FECHADA (allowlist), nao blacklist",
      len(DT.METODOS_CDP_PERMITIDOS) <= 12, len(DT.METODOS_CDP_PERMITIDOS))
try:
    DT.validar_metodo_cdp("Metodo.QueNaoExiste")
    check("T9: metodo inventado e recusado", False)
except DT.MetodoCdpProibido:
    check("T9: metodo inventado e recusado", True)

check("T10: a flag do DeepTrace nasce DESLIGADA",
      DT.deep_trace_enabled() is False)
os.environ["PORTAL_DEEP_TRACE_ENABLED"] = "true"
check("T10 CONTROLE: e liga por env", DT.deep_trace_enabled() is True)
os.environ.pop("PORTAL_DEEP_TRACE_ENABLED", None)

# ==========================================================================
print("\n[T11] a telemetria da 073 aprendeu o que foi MEDIDO")
# ==========================================================================
for h in ("bf67246skn.bf.dynatrace.com", "c.go-mpulse.net",
          "www.google-analytics.com", "j.clarity.ms"):
    check(f"T11: `{h}` e telemetria",
          PF.classificar_origem(h, "portal.com", "xhr") == "telemetry")
check("T11 CONTROLE: o portal de verdade NAO e telemetria",
      PF.classificar_origem("api.autoglass.com.br", "portal.com", "xhr")
      != "telemetry")

# ==========================================================================
print("\n[I1] contra os HAR REAIS — a ferramenta acha o que eu achei a mao?")
# ==========================================================================
hars_vidros = _hars("PORTAL VIDROS")
if not hars_vidros:
    pular("I1", f"HAR nao encontrados em {HARS} (estao fora do git, por PII)")
else:
    tr = None
    for f in hars_vidros:
        t = T.importar_har(f)
        if tr is None:
            tr = t
        else:
            tr.chamadas.extend(t.chamadas)
    tr.rotulo = "Maxpar"

    api = T.hosts_de_api(tr)
    check("I1: o host da API do Maxpar e descoberto",
          api and api[0][0] == "api.autoglass.com.br", api[:2])
    check("I1: 🔴 e ele NAO e o host que o navegador visita",
          api[0][0] != tr.host_portal, (api[0][0], tr.host_portal))

    eps = I.agrupar(tr)
    chaves = set(eps)

    # Os endpoints que EU documentei a mao na SPEC-074, lendo 58 MB de HAR.
    CONHECIDOS_DA_074 = [
        "GET /atendimentos/api/web-app/seguradoras/",
        "GET /atendimentos/api/web-app/apolices",
        "GET /atendimentos/api/web-app/motivos-dano",
        "POST /atendimentos/api/web-app/atendimentos",
        "POST /atendimentos/api/web-app/questionarios",
        "POST /atendimentos/api/web-app/questionarios/perguntas",
        "POST /atendimentos/api/web-app/solicitantes",
        "PUT /atendimentos/api/web-app/atendimentos/corretores",
        "PATCH /atendimentos/api/web-app/atendimentos",
        "GET /atendimentos/api/web-app/atendimentos/atendimentos-abertos-existentes",
    ]
    achados = [k for k in CONHECIDOS_DA_074 if k in chaves]
    check(f"I1: acha os endpoints que eu mapeei a mao ({len(achados)}/"
          f"{len(CONHECIDOS_DA_074)})",
          len(achados) == len(CONHECIDOS_DA_074),
          [k for k in CONHECIDOS_DA_074 if k not in chaves])

    # 🔴 E os que eu NAO tinha mapeado — a prova de que a ferramenta acrescenta.
    # A SPEC-076 §2.2 declara estes DESCONHECIDOS e pede captura manual.
    NAO_SABIA = [
        "GET /atendimentos/api/web-app/agendamentos/datas-disponiveis",
        "GET /atendimentos/api/web-app/agendamentos/horarios-disponiveis",
        "GET /atendimentos/api/web-app/agendamentos/opcoes-disponiveis",
        "POST /atendimentos/api/web-app/lojas/consultar-distancias",
    ]
    novos = [k for k in NAO_SABIA if k in chaves]
    check(f"I1: 🔴 e acha os {len(NAO_SABIA)} que a SPEC-076 declara "
          f"DESCONHECIDOS ({len(novos)} achados)",
          len(novos) == len(NAO_SABIA),
          [k for k in NAO_SABIA if k not in chaves])

    check("I1: OPTIONS de CORS nao vira endpoint",
          not any(k.startswith("OPTIONS ") for k in chaves))
    check("I1 CONTROLE: mas o preflight foi REGISTRADO no endpoint real",
          any(e.exige_preflight for e in eps.values()))

    escrita = [e for e in eps.values() if e.escreve]
    check("I1: os endpoints de escrita sao identificados",
          len(escrita) >= 10, len(escrita))
    doc = I.openapi_candidato(tr, titulo="Maxpar")
    check("I1: e o OpenAPI gerado e JSON serializavel",
          isinstance(json.dumps(doc), str))
    check("I1: com nenhum endpoint aprovado",
          "APPROVED" not in json.dumps(doc))

    cob = I.relatorio_de_cobertura(tr)
    check("I1: o relatorio de cobertura nomeia os endpoints de escrita",
          "escrita" in cob.lower() and "lojas/consultar-distancias" in cob)

# ==========================================================================
print("\n[I2] os outros 5 portais tambem sao lidos")
# ==========================================================================
outros = [f for f in _hars() if "PORTAL VIDROS" not in str(f)]
if not outros:
    pular("I2", "HAR nao encontrados")
else:
    resultados = {}
    for f in outros:
        t = T.importar_har(f)
        api = T.hosts_de_api(t)
        resultados[f.name] = (len(t), api[0] if api else None, len(I.agrupar(t)))
    com_api = [n for n, (_, a, _e) in resultados.items() if a]
    check(f"I2: descobre host de API em {len(com_api)}/{len(outros)} HAR",
          len(com_api) >= len(outros) - 1, resultados)
    check("I2: 🔴 e descobre que a API da Yelum mora no dominio do grupo HDI",
          any("grupohdiseguros" in str(a) for _, a, _e in resultados.values()),
          [a for _, a, _e in resultados.values()])
    check("I2: e que a da MAPFRE mora em CloudFront",
          any("cloudfront" in str(a) for _, a, _e in resultados.values()))
    # 🔴 Este par nasceu de uma mutacao que NAO foi detectada.
    #
    # Remover o desconto de telemetria em `_host_predominante` deixou a bateria
    # 87/0 — verde. Eu tinha assercao sobre `hosts_de_api` (de onde vem o JSON)
    # e NENHUMA sobre `host_portal` (quem e a casa), que e o campo que alimenta
    # `classificar_origem`. Com ele errado, o portal real vira `third_party` e
    # o rastreador vira a casa.
    #
    # 📊 O caso e o HAR da MAPFRE: ZERO documentos (o `Preserve log` foi ligado
    # depois da navegacao) e 299 chamadas de Dynatrace contra 18 do portal.
    mapfre = [f for f in outros if "mapfre" in f.name.lower()]
    if mapfre:
        t_m = T.importar_har(mapfre[0])
        check("I2: 🔴 no HAR SEM documento, o host da casa NAO e a telemetria",
              "dynatrace" not in t_m.host_portal and "mpulse" not in t_m.host_portal,
              t_m.host_portal)
        check("I2 CONTROLE: e o HAR realmente nao tem documento nenhum "
              "(e por isso que o caminho de fallback e exercido)",
              not any(c.resource_type == "document" for c in t_m))
    else:
        pular("I2 host sem documento", "HAR da MAPFRE nao encontrado")

    check("I2 CONTROLE: nenhum deles elegeu telemetria como host de API",
          not any(a and ("dynatrace" in a[0] or "clarity" in a[0]
                         or "facebook" in a[0])
                  for _, a, _e in resultados.values()),
          [a for _, a, _e in resultados.values()])

# ==========================================================================
print("[P1] o artefato GERADO nao pode conter PII — ele vai para o Git")
# ==========================================================================
# 🔴 Este bloco inteiro nasceu de um vazamento MEU, medido.
#
# A primeira versao do inferidor guardava o valor cru em `Forma.exemplos` e o
# emitia como `examples`. Rodando sobre os HAR reais do Maxpar, o documento
# gerado saiu com **410 achados de PII**: 340 chassis, 16 placas, 4 CPFs, 2
# e-mails e 47 tokens — e o destino dele e `docs/generated/`, que e
# VERSIONADO, ao contrario de `docs/intake/`, que esta no .gitignore por isso.
#
# Construi o pipeline inteiro contra esse caminho e abri uma porta lateral pelo
# campo mais inocente do schema.
RPY = _carregar("app.services.portals.replay", "app/services/portals/replay.py")

if not _hars():
    pular("P1", "HAR nao encontrados")
else:
    for _nome, _sub in (("Maxpar", "PORTAL VIDROS"), ("MAPFRE", "MAPFRE"),
                        ("Yelum", "YELUM"), ("Zurich", "ZURICH"), ("Tokio", "TOKIO")):
        _tr = None
        for _f in _hars(_sub):
            _t = T.importar_har(_f)
            if _tr is None:
                _tr = _t
            else:
                _tr.chamadas.extend(_t.chamadas)
        if _tr is None:
            continue
        _tr.rotulo = _nome
        _txt = json.dumps(I.openapi_candidato(_tr, titulo=_nome), ensure_ascii=False)
        _bloq = [a for a in RPY.varredura_de_pii(_txt)
                 if getattr(a, "severidade", "") == "bloqueia"]
        check(f"P1: o candidato da {_nome} sai SEM PII bloqueante",
              not _bloq, [(a.tipo, getattr(a, "amostra", "")) for a in _bloq[:4]])

    # CONTROLE: o detector CONSEGUE acusar. Sem este par, um `varredura_de_pii`
    # que devolvesse sempre `[]` faria as cinco assercoes acima passarem.
    _sujo = json.dumps({"exemplo": "52998224725", "outro": "ABC1D23"})
    check("P1 CONTROLE: e o detector acusa um documento sujo de proposito",
          bool(RPY.varredura_de_pii(_sujo)))

# ==========================================================================
print("[P2] o caminho tambem e PII — e ele vira chave de endpoint")
# ==========================================================================
# 📊 A API da MAPFRE tem `/api/1.0.0/client/12097137725_1/interactions`. O
# `normalizar_path` da SPEC-073 preserva numero colado em palavra (a regra que
# distingue `passo5` de `passo6`), e por isso preservava o CPF.
check("P2: segmento com CPF vira parametro", I._segmento_e_pii("12097137725_1"))
check("P2: com ou sem sufixo", I._segmento_e_pii("12097137725"))
check("P2 CONTROLE: `passo5` NAO e PII — a regra da 073 continua valendo",
      not I._segmento_e_pii("passo5"))
check("P2 CONTROLE: nem `atendimentos`", not I._segmento_e_pii("atendimentos"))
check("P2 CONTROLE: nem um id curto", not I._segmento_e_pii("12345"))

# ==========================================================================
print("[P3] valor com PII nunca vira `example`")
# ==========================================================================
check("P3: CPF nao vira exemplo", I._seguro_para_exemplo("529.982.247-25") is None)
check("P3: CPF sem mascara tambem nao", I._seguro_para_exemplo("52998224725") is None)
check("P3: chassi nao vira exemplo",
      I._seguro_para_exemplo("98867513WJKH74022") is None)
check("P3: placa nao vira exemplo", I._seguro_para_exemplo("ABC1D23") is None)
check("P3: e-mail nao vira exemplo",
      I._seguro_para_exemplo("alguem@dominio.com.br") is None)
check("P3: valor longo demais nao vira exemplo",
      I._seguro_para_exemplo("x" * 200) is None)
check("P3 CONTROLE: vocabulario de negocio VIRA exemplo — senao o schema "
      "perde o que tem de util",
      I._seguro_para_exemplo("VIDRO DE PORTA") == "VIDRO DE PORTA")
check("P3 CONTROLE: e numero tambem", I._seguro_para_exemplo(195) == 195)


print("\n" + "=" * 70)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas · {SKIP} puladas")
print("=" * 70)
sys.exit(1 if FAIL else 0)
