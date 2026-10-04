# -*- coding: utf-8 -*-
"""🔴 A TELA "AVALIAÇÃO" — a vistoria pelo celular: QUEM ESCOLHE É O SEGURADO.

O pedido (atendente da corretora, 24/09): o portal de vidros mostra a tela
"Avaliação" com dois botões — "Desejo inserir as fotos agora" e "Desejo receber
o link de acesso por E-mail" — e o segurado escolhe. O Founder: o segurado
ESCOLHE; nada irreversível sozinho; nunca aceitar custo.

📊 O que a tela é (bundle `app-332606d5f8.min.js` + `passo5.html`, HAR YELUM
para-brisa, lidos em 03/10/2026 — só nomes, nenhum dado pessoal):
  function E(o): conclusão → PermiteVistoriaAmbas → PermiteVistoriaLoja →
                 PermiteVistoriaMobile → V() → a tela "Avaliação"
  "inserir agora"  → GET /atendimentos/vistoriamobileonline → {Link} (iframe)
  "link por e-mail" → GET /atendimentos/vistoriamobile?telefone=… → conclusão
  ⚠️ ZERO exercícios dos dois em todo o acervo: CANDIDATE (SPEC-077).

O que se afirma, sempre pelo MOTOR (`ler_desfecho`, `fase_desfecho`,
`continuar_atendimento`, `pode_sair`, `texto_da_parada`, `format_result`):
  V1  o roteador nomeia o ramo NA ORDEM DO SPA (controle: ambas/loja vencem)
  V2  sem a escolha: PARA e PERGUNTA, com os dois botões literais; nada sai
  V3  os dois botões NÃO saem para a rede (antes: `/atendimentos` APPROVED
      deixava `vistoriamobileonline` sair por prefixo) — controle: o agregado sai
  V4  a resposta volta como continuação do MESMO pedido; com o botão CANDIDATE
      vai à equipe COM a escolha e o botão a apertar; 0 chamada, 0 POST
  V5  promovido (registro simulado): "agora" lê o LINK e o entrega; sem
      autorização ou sem e-mail no pedido, NÃO aperta; "email" aperta 1×
  V6  o que o segurado e a equipe leem (texto, normalização, destravador)

⛔ PII: tudo sintético (fixtures mascaradas). Nenhum HAR é lido aqui.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cryptography.fernet import Fernet  # noqa: E402

os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()

from fixtures.vidros import maxpar_atendimento as FX           # noqa: E402
from portal_worker import guardrails as G                      # noqa: E402
from portal_worker import vault                                # noqa: E402
from portal_worker.journeys import vidros_api as API           # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF       # noqa: E402
from portal_worker.journeys import vidros_continuacao as VC    # noqa: E402
from portal_worker.journeys import vidros_estado as ST         # noqa: E402
from portal_worker.journeys.vidros_sessao import SessaoVidros  # noqa: E402

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


# 📊 As 20 chaves medidas de `opcoes-disponiveis` (HAR YELUM [298]), com o ramo
# da tela "Avaliação" ligado: só `PermiteVistoriaMobile`.
OPCOES_CELULAR = {
    "DisponibilizarAgendamento": False, "IrParaConclusaoDeAtendimento": False,
    "ExibirAvisoVistoria": False, "ExibirAvisoVistoriaPorRegraDeFraude": False,
    "RealizarVistoria": False, "ExisteVistoriaCriada": False,
    "PermiteVistoriaMobile": True, "PermiteVistoriaLoja": False,
    "PermiteVistoriaAmbas": False, "MensagemVistoria": "", "VistoriaOnline": False,
    "VistoriaFinalizada": False, "ExisteAgendamento": False, "ExisteOrdemServico": False,
    "BloqueadoPorFraude": False, "BloqueadoIlhaNormal": False, "AceitaReparo": False,
    "PermiteOpcaoVistoria": False, "GerarOrdemServicoGenesis": False, "OpcoesAgendamento": [],
}
AGREGADO = copy.deepcopy(FX.ATENDIMENTO_POS_QUESTIONARIO)
LINK_SINTETICO = "https://vistoria.exemplo.invalid/app/#/intro/0000"
BOTAO_AGORA = "Desejo inserir as fotos agora"
BOTAO_EMAIL = "Desejo receber o link de acesso por E-mail"
EP_ONLINE = "/atendimentos/vistoriamobileonline"
EP_EMAIL = "/atendimentos/vistoriamobile"


class PaginaDoPortal:
    """A BORDA: responde como o portal, por caminho, e conta o que saiu."""

    def __init__(self, *, agregado=None):
        self.saidas: list = []
        self.agregado = agregado if agregado is not None else AGREGADO

    async def evaluate(self, _js, arg):
        caminho = str(arg["url"])[len(API.BASE_API):]
        base = caminho.split("?")[0]
        self.saidas.append((arg["metodo"], base))
        if base == "/agendamentos/opcoes-disponiveis":
            corpo = OPCOES_CELULAR
        elif base == "/atendimentos":
            corpo = self.agregado
        elif base == EP_ONLINE:
            corpo = {"Link": LINK_SINTETICO}
        elif base == EP_EMAIL:
            return {"ok": True, "status": 200, "text": ""}
        elif base.startswith("/atendimentos/emitir-atendimento-formalizado/"):
            corpo = {}
        else:
            return {"ok": False, "status": 404, "text": ""}
        return {"ok": True, "status": 200, "text": json.dumps(corpo)}

    def quantas(self, base):
        return sum(1 for _m, b in self.saidas if b == base)


class Runtime:
    def __init__(self, *, liberado=True):
        self.gravacoes: list = []
        self.guard = G.PortalActionGuard(material_liberado=liberado, _checkpoint=self.checkpoint)

    async def checkpoint(self, patch):
        self.gravacoes.append(json.loads(json.dumps(patch, default=str)))


def armou(rt):
    """O guard ARMOU o botao da vistoria? (o checkpoint de leitura do desfecho nao conta)"""
    return any(ST.FRONTEIRA_VISTORIA_PELO_CELULAR in json.dumps(g) for g in rt.gravacoes)


def execucao(page, *, escolha=None, liberado=True):
    rt = Runtime(liberado=liberado)
    params = {"especificos": ({"vistoria_pelo_celular": escolha} if escolha else {}),
              "confirm": liberado, "_runtime": rt}
    ev: dict = {}
    sessao = SessaoVidros(page=page, token="tok-de-teste", modo_continuacao=True)
    ex = AF.execucao_de(params, ev, sessao=sessao, guard=rt.guard, estado=ST.EstadoDoAtendimento())
    ex.continuacao = {"sessao_cifrada": "cifra-de-teste", "sessao_guardada": True,
                      "possivel": True, "etapa": ST.ETAPA_DESFECHO, "acao_esperada": "reler"}
    return ex, ev, rt


def desfecho(page, **kw):
    ex, ev, rt = execucao(page, **kw)
    r = asyncio.run(AF.fase_desfecho(ex))
    return r, ev, rt


# ==========================================================================
print("\n[V1] o roteador nomeia o ramo NA ORDEM DO SPA (function E)")
# ==========================================================================
d1 = ST.ler_desfecho(OPCOES_CELULAR, AGREGADO)
check("V1: PermiteVistoriaMobile sozinho -> vistoria, ramo `celular` (a tela Avaliacao)",
      d1.get("tipo") == ST.DESFECHO_VISTORIA and d1.get("ramo_vistoria") == "celular", d1.get("ramo_vistoria"))
check("V1 CONTROLE: Ambas vence Mobile (o SPA mostra loja x celular antes)",
      ST.ler_desfecho({**OPCOES_CELULAR, "PermiteVistoriaAmbas": True}, AGREGADO).get("ramo_vistoria") == "ambas")
check("V1 CONTROLE: Loja vence Mobile (o SPA vai para a agenda da loja)",
      ST.ler_desfecho({**OPCOES_CELULAR, "PermiteVistoriaLoja": True}, AGREGADO).get("ramo_vistoria") == "loja")

# ==========================================================================
print("\n[V2] sem a escolha: PARA e PERGUNTA — nada sai")
# ==========================================================================
p2 = PaginaDoPortal()
r2, ev2, rt2 = desfecho(p2)
check("V2: para em `decidir_vistoria_pelo_celular` (needs_human)",
      r2.status == "needs_human" and r2.captured.get("stage") == "decidir_vistoria_pelo_celular",
      (r2.status, r2.captured.get("stage")))
check("V2: as opcoes sao os DOIS botoes literais da tela",
      r2.captured.get("opcoes") == [BOTAO_AGORA, BOTAO_EMAIL], r2.captured.get("opcoes"))
check("V2: a continuacao espera a RESPOSTA dele (responder:vistoria_pelo_celular), possivel",
      (ev2.get("continuacao") or {}).get("acao_esperada") == "responder:vistoria_pelo_celular"
      and (ev2.get("continuacao") or {}).get("possivel") is True, ev2.get("continuacao"))
check("V2: nenhum dos dois botoes saiu, e nenhum efeito foi armado",
      p2.quantas(EP_ONLINE) == 0 and p2.quantas(EP_EMAIL) == 0 and not armou(rt2), p2.saidas)
check("V2: a tela da parada e a 'Avaliacao', com os dois botoes",
      (ev2.get("tela_da_parada") or {}).get("heading") == "Avaliação"
      and (ev2.get("tela_da_parada") or {}).get("rotulos") == [BOTAO_AGORA, BOTAO_EMAIL],
      ev2.get("tela_da_parada"))

# ==========================================================================
print("\n[V3] os botoes NAO saem para a rede (CANDIDATE)")
# ==========================================================================
check("V3: GET vistoriamobileonline NAO sai (antes saia: prefixo /atendimentos APPROVED)",
      API.pode_sair(EP_ONLINE, "GET") is False, API.endpoint_do_caminho(EP_ONLINE))
check("V3: GET vistoriamobile?telefone= NAO sai",
      API.pode_sair(EP_EMAIL + "?telefone=", "GET") is False)
check("V3: GET vistoriafinalizada e POST vistoriacredenciado NAO saem",
      API.pode_sair("/atendimentos/vistoriafinalizada", "GET") is False
      and API.pode_sair("/atendimentos/vistoriacredenciado", "POST") is False)
check("V3 CONTROLE: o agregado (GET /atendimentos) SAI — as duas respostas DIFEREM",
      API.pode_sair("/atendimentos?GerarPdf=false&RetornarImagemVeiculo=false", "GET") is True)

# ==========================================================================
print("\n[V4] a resposta volta como continuacao do MESMO pedido")
# ==========================================================================
origem_params = {"especificos": {}, "confirm": True}
sessao_origem = {**(ev2.get("continuacao") or {}), "sessao_cifrada": vault.encrypt("tok-de-teste"),
                 "sessao_guardada": True, "codigo_atendimento": str(AGREGADO["CodigoAtendimento"])}
p4 = PaginaDoPortal()
rt4 = Runtime(liberado=True)
params4 = {**origem_params, "_runtime": rt4,
           "_continuacao": {"job_origem": "job-de-origem", "operacao": "responder",
                            "escolha": {}, "respostas": {"vistoria_pelo_celular": "agora"},
                            "sessao": sessao_origem, "desfecho_anterior": ev2.get("desfecho")}}
ev4: dict = {}
r4 = asyncio.run(VC.continuar_atendimento(p4, params4, ev4))
check("V4: a escolha chega ao MESMO pedido e vai a equipe COM o botao (CANDIDATE)",
      r4.captured.get("stage") == "vistoria_pelo_celular_com_a_equipe"
      and r4.captured.get("vistoria_pelo_celular") == "agora", (r4.status, r4.captured))
check("V4: a mensagem a equipe nomeia o botao que o segurado escolheu",
      BOTAO_AGORA in (r4.message or ""), r4.message)
check("V4: 0 chamada aos botoes, 0 POST /atendimentos, nenhum efeito armado",
      p4.quantas(EP_ONLINE) == 0 and p4.quantas(EP_EMAIL) == 0
      and not [s for s in p4.saidas if s == ("POST", "/atendimentos")] and not armou(rt4), p4.saidas)
check("V4: a escolha fica gravada na evidence (a equipe e o painel a leem)",
      ev4.get("vistoria_pelo_celular") == "agora", ev4.get("vistoria_pelo_celular"))

# ==========================================================================
print("\n[V5] PROMOVIDO (registro simulado): o robo aperta o botao ESCOLHIDO")
# ==========================================================================
_original = dict(API.ESTADO_DO_ENDPOINT)
try:
    API.ESTADO_DO_ENDPOINT[API.EP_VISTORIA_MOBILE_ONLINE_NAO_MEDIDO] = API.APPROVED
    API.ESTADO_DO_ENDPOINT[API.EP_VISTORIA_MOBILE_NAO_MEDIDO] = API.APPROVED
    p5 = PaginaDoPortal()
    r5, ev5, rt5 = desfecho(p5, escolha="agora")
    check("V5: 'agora' -> 1 GET vistoriamobileonline e o LINK lido vai ao segurado",
          p5.quantas(EP_ONLINE) == 1 and ev5.get("link_vistoria") == LINK_SINTETICO
          and (ev5.get("desfecho") or {}).get("vistoria_pelo_celular") == "agora"
          and r5.status == "done", (r5.status, r5.captured.get("stage"), p5.saidas))
    check("V5: e o efeito foi ARMADO antes (guard da SPEC-073)",
          armou(rt5),
          rt5.gravacoes)
    check("V5: 'agora' NUNCA aperta tambem o do e-mail", p5.quantas(EP_EMAIL) == 0)

    p5b = PaginaDoPortal()
    r5b, ev5b, rt5b = desfecho(p5b, escolha="agora", liberado=False)
    check("V5: sem autorizacao (confirm off) NAO aperta: vai a equipe",
          p5b.quantas(EP_ONLINE) == 0
          and r5b.captured.get("stage") == "vistoria_pelo_celular_com_a_equipe", (r5b.captured, p5b.saidas))

    p5c = PaginaDoPortal(agregado={**AGREGADO, "Email": None})
    r5c, _ev5c, _ = desfecho(p5c, escolha="email")
    check("V5: 'email' sem e-mail no pedido NAO aperta (o link iria a lugar nenhum)",
          p5c.quantas(EP_EMAIL) == 0
          and r5c.captured.get("stage") == "vistoria_pelo_celular_com_a_equipe", (r5c.captured, p5c.saidas))

    p5d = PaginaDoPortal()
    r5d, ev5d, _ = desfecho(p5d, escolha="email")
    check("V5: 'email' com e-mail -> 1 GET vistoriamobile e conclui",
          p5d.quantas(EP_EMAIL) == 1 and p5d.quantas(EP_ONLINE) == 0 and r5d.status == "done"
          and (ev5d.get("desfecho") or {}).get("vistoria_pelo_celular") == "email",
          (r5d.status, r5d.captured, p5d.saidas))

    p5e = PaginaDoPortal()
    ex5e, _ev5e, _ = execucao(p5e, escolha="agora")
    r5e = asyncio.run(AF.fase_desfecho(ex5e, agendar_por_preferencia=False))
    check("V5: a RELEITURA nunca aperta botao (mesmo com a escolha na mao)",
          p5e.quantas(EP_ONLINE) == 0 and r5e.status == "needs_human", (r5e.captured, p5e.saidas))
finally:
    API.ESTADO_DO_ENDPOINT.clear()
    API.ESTADO_DO_ENDPOINT.update(_original)
check("V5: e o registro voltou (os dois botoes CANDIDATE de novo)",
      API.pode_sair(EP_ONLINE, "GET") is False and API.pode_sair(EP_EMAIL, "GET") is False)

# ==========================================================================
print("\n[V6] o que o segurado, o agente e a equipe leem")
# ==========================================================================
from app.agents.tools import portal_params as PP  # noqa: E402
from app.services import destravador as DT         # noqa: E402

for frase, esperado in (("pode mandar o link agora", "agora"), ("faço já, na hora", "agora"),
                        ("prefiro receber por e-mail", "email"), ("manda no email", "email"),
                        ("agora não, manda por e-mail", ""), ("não sei", ""), ("", ""),
                        # 🔴 o "não" sozinho: sem a regra, isto apertaria "fotos AGORA"
                        ("não consigo fazer agora", "")):
    check(f"V6: normaliza '{frase}' -> '{esperado}'",
          PP.normalizar_vistoria_pelo_celular(frase) == esperado,
          PP.normalizar_vistoria_pelo_celular(frase))

par = PP.texto_da_parada("decidir_vistoria_pelo_celular", True)
check("V6: o segurado le a escolha (agora pelo celular x link por e-mail) e o 'eu continuo'",
      bool(par) and "agora" in par[0] and "e-mail" in par[0] and PP._EU_CONTINUO in par[0], par)
check("V6: a equipe le os DOIS botoes literais", bool(par) and BOTAO_AGORA in par[1] and BOTAO_EMAIL in par[1])
check("V6: a parada e das que o SEGURADO responde",
      "decidir_vistoria_pelo_celular" in PP.ESTAGIOS_QUE_O_SEGURADO_RESPONDE)
job = {"status": "needs_human",
       "evidence": {"stage": "decidir_vistoria_pelo_celular", "continuacao": ev2.get("continuacao"),
                    "vidros_estado": ev2.get("vidros_estado"), "desfecho": ev2.get("desfecho")}}
texto = PP.format_result(job)
check("V6: o agente recebe a pergunta e ONDE devolver a resposta",
      "DIGA AO SEGURADO" in texto and "especificos.vistoria_pelo_celular" in texto, texto[-500:])
equipe = PP.texto_da_parada("vistoria_pelo_celular_com_a_equipe", True)
check("V6: com a equipe: nao promete continuacao e nomeia os botoes",
      bool(equipe) and PP._EU_CONTINUO not in equipe[0] and BOTAO_AGORA in equipe[1], equipe)
m_link = PP.mensagem_do_desfecho({"tipo": "analista", "codigo_atendimento": "99999999",
                                  "vistoria_pelo_celular": "agora", "link_vistoria": LINK_SINTETICO})
check("V6: promovido, o link vai ao segurado EXATO", LINK_SINTETICO in m_link, m_link)
m_mail = PP.mensagem_do_desfecho({"tipo": "analista", "codigo_atendimento": "99999999",
                                  "vistoria_pelo_celular": "email"})
check("V6: promovido, 'email' diz onde o link chega", "e-mail" in m_mail, m_mail)
check("V6: o destravador PERGUNTA ao segurado (nunca escolhe por ele)",
      DT.CLASSE_DA_PARADA_DO_PORTAL.get("decidir_vistoria_pelo_celular") == "perguntar_ao_segurado")
check("V6: e a parada da equipe e NUNCA sozinho",
      DT.CLASSE_DA_PARADA_DO_PORTAL.get("vistoria_pelo_celular_com_a_equipe") == "nunca_sozinho")

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
