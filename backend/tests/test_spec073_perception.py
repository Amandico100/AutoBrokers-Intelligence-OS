# -*- coding: utf-8 -*-
"""SPEC-073 Bloco E — a escada de percepcao e o validador, no detalhe.

A matriz de mutacoes prova que o validador RECUSA. Aqui se prova a mecanica da
escada: qual camada resolveu, quando ela sobe, e que o provedor de visao e
trocavel por configuracao — nao por arquitetura.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from portal_worker import guardrails as G  # noqa: E402
from portal_worker import perception as P  # noqa: E402

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


TELA = {
    "url": "https://p/passo6", "heading": "Confirme a peca",
    "inputs": [{"label": "Qual peca danificada"}, {"label": "E-mail do solicitante"}],
    "selects": [{"label": "Lado", "options": ["Motorista", "Carona"]},
                {"label": "Causa", "options": ["Vandalismo", "Pedra na estrada"]}],
    "buttons": [{"text": "Voltar"}, {"text": "Confirmar"}],
    "checkboxes": [{"label": "Aceito receber no WhatsApp"}],
}
DADOS = {"dano": {"peca": "vidro da porta", "lado": "motorista",
                  "relato": "pedra na estrada"},
         "solicitante": {"email": "corretora@teste.com.br"}}


def gd(**kw):
    base = {"material_liberado": True, "acao_material_esperada": "confirmar"}
    base.update(kw)
    return G.PortalActionGuard(**base)


# ==========================================================================
print("\n[1] A ESCADA — ordem, subida e registro")
# ==========================================================================
check("a escada tem os 6 degraus na ordem certa",
      P.ESCADA == (P.L0_FATO, P.L1_API, P.L2_DOM, P.L3_TEXTO, P.L4_VISAO, P.L5_HUMANO))
e = P.EscadaDePercepcao()
check("do fato sobe para API", e.proximo_degrau(P.L0_FATO) == P.L1_API)
check("do DOM sobe para o modelo textual", e.proximo_degrau(P.L2_DOM) == P.L3_TEXTO)
check("do textual sobe para visao", e.proximo_degrau(P.L3_TEXTO) == P.L4_VISAO)
check("do topo so sobra o humano", e.proximo_degrau(P.L4_VISAO) == P.L5_HUMANO)
check("do humano nao sobe mais", e.proximo_degrau(P.L5_HUMANO) == P.L5_HUMANO)
check("camada desconhecida cai no humano", e.proximo_degrau("xpto") == P.L5_HUMANO)

e.registrar(P.L0_FATO)
e.registrar(P.L0_FATO)
e.registrar(P.L3_TEXTO)
check("camada repetida nao entra duas vezes seguidas", e.usados == [P.L0_FATO, P.L3_TEXTO])
check("o resumo diz qual camada FECHOU", e.resumo()["layer_final"] == P.L3_TEXTO)
check("e quantas vezes precisou subir", e.resumo()["fallback_count"] == 1)

# ==========================================================================
print("\n[2] O QUE E CRITICO, MATERIAL E PROIBIDO")
# ==========================================================================
for rot in ("Qual peca danificada", "Lado do veiculo", "Causa do dano",
            "Cobertura", "Loja", "Horario", "Posicao do trincado"):
    check(f"`{rot}` e campo critico", P.e_campo_critico(rot))
check("CONTROLE: `E-mail do solicitante` NAO e critico",
      not P.e_campo_critico("E-mail do solicitante"))
check("CONTROLE: `Nome` NAO e critico", not P.e_campo_critico("Nome"))

for bt in ("Confirmar", "Agendar a domicilio", "Cancelar atendimento",
           "Finalizar", "Alterar pagamento", "Aceito"):
    check(f"`{bt}` e botao material", P.e_botao_material(bt))
check("CONTROLE: `Voltar` NAO e material", not P.e_botao_material("Voltar"))
check("CONTROLE: `Buscar` NAO e material", not P.e_botao_material("Buscar"))
check("CONTROLE: vazio NAO e material", not P.e_botao_material(""))

check("checkbox de WhatsApp e proibida", P.e_checkbox_proibida("Aceito receber no WhatsApp"))
check("checkbox de termo e proibida", P.e_checkbox_proibida("Li e aceito o termo"))
check("CONTROLE: checkbox comum NAO e proibida",
      not P.e_checkbox_proibida("Veiculo esta em movimento"))

# ==========================================================================
print("\n[3] LEITURA DA TELA")
# ==========================================================================
check("alvo existente e achado", P.alvo_existe("Lado", TELA)[0])
check("e o tipo dele e reportado", P.alvo_existe("Lado", TELA)[1] == "select")
check("botao e achado como button", P.alvo_existe("Confirmar", TELA)[1] == "button")
check("CONTROLE: alvo inexistente nao e inventado", not P.alvo_existe("Fantasma", TELA)[0])
check("CONTROLE: alvo vazio nao casa com tudo", not P.alvo_existe("", TELA)[0])
check("opcoes reais sao lidas do campo certo",
      P.opcoes_reais("Lado", TELA) == ["Motorista", "Carona"])
check("campo sem opcoes devolve lista vazia", P.opcoes_reais("Fantasma", TELA) == [])

# ==========================================================================
print("\n[4] O VALIDADOR, ACAO POR ACAO")
# ==========================================================================
def v(acao, **kw):
    return P.validar_acao(acao, TELA, collected=DADOS, guard=gd(), **kw)


check("acao desconhecida e recusada", not v({"action": "teleportar"}).ok)
check("done sempre passa", v({"action": "done"}).ok)
check("ask_human sempre passa", v({"action": "ask_human"}).ok)

check("select com opcao real passa", v({"action": "select", "target": "Causa",
                                        "value": "Pedra na estrada"}).ok)
check("select com opcao inventada e recusado",
      not v({"action": "select", "target": "Causa", "value": "Colisao"}).ok)
check("e a recusa pede para ESCALAR, nao so nega",
      v({"action": "select", "target": "Causa", "value": "Colisao"}).escalar)

check("fill em campo nao-critico passa",
      v({"action": "fill", "target": "E-mail do solicitante",
         "value": "corretora@teste.com.br"}).ok)
check("fill vazio e recusado",
      not v({"action": "fill", "target": "E-mail do solicitante", "value": ""}).ok)
check("fill critico com lastro passa",
      v({"action": "fill", "target": "Qual peca danificada",
         "value": "vidro da porta"}).ok)
check("fill critico inventado e recusado",
      not v({"action": "fill", "target": "Qual peca danificada",
             "value": "para-brisa"}).ok)

check("check em checkbox proibida e recusado",
      not v({"action": "check", "target": "Aceito receber no WhatsApp"}).ok)

check("click inofensivo passa", v({"action": "click", "target": "Voltar"}).ok)
check("click material declarado passa (origem journey)",
      P.validar_acao({"action": "click", "target": "Confirmar"}, TELA,
                     guard=gd(), origem="journey").ok)
check("click material por VISAO nunca passa",
      not P.validar_acao({"action": "click", "target": "Confirmar"}, TELA,
                         guard=gd(), origem=P.L4_VISAO).ok)
check("click material sem guard nenhum e recusado por construcao",
      not P.validar_acao({"action": "click", "target": "Confirmar"}, TELA, guard=None).ok)

hist = ["select Lado Motorista -> selected ok"]
check("repetir acao ja bem-sucedida e recusado",
      not P.validar_acao({"action": "select", "target": "Lado", "value": "Motorista"},
                         TELA, collected=DADOS, historico=hist, guard=gd()).ok)
check("CONTROLE: outra acao no mesmo historico continua passando",
      P.validar_acao({"action": "select", "target": "Causa", "value": "Vandalismo"},
                     TELA, collected=DADOS, historico=hist, guard=gd()).ok)

# ==========================================================================
print("\n[5] A ESCADA REGISTRA AS RECUSAS")
# ==========================================================================
e2 = P.EscadaDePercepcao()
ver = v({"action": "select", "target": "Causa", "value": "Colisao"})
e2.rejeitar({"action": "select", "target": "Causa"}, ver, camada=P.L3_TEXTO)
r = e2.resumo()["rejected_actions"][0]
check("a recusa vira registro", len(e2.resumo()["rejected_actions"]) == 1)
check("com a camada que propos", r["layer"] == P.L3_TEXTO)
check("com o motivo legivel", "nao existe" in r["reject_reason"])
check("e dizendo se pedia escalada", r["escalou"] is True)

# ==========================================================================
print("\n[6] O PROVEDOR DE VISAO E TROCAVEL POR CONFIG, NAO POR ARQUITETURA")
# ==========================================================================
os.environ.pop("PORTAL_VISION_ENABLED", None)
check("visao nasce desligada", P.visao_habilitada() is False)
os.environ["PORTAL_VISION_ENABLED"] = "true"
check("e liga por env", P.visao_habilitada() is True)
os.environ.pop("PORTAL_VISION_ENABLED", None)

os.environ.pop("PORTAL_VISION_PROVIDER", None)
check("existe um provider padrao", P.provider_de_visao() == "openai")
os.environ["PORTAL_VISION_PROVIDER"] = "gemini"
check("e ele troca por env, sem tocar em codigo", P.provider_de_visao() == "gemini")
os.environ.pop("PORTAL_VISION_PROVIDER", None)


class _Bom:
    async def decide(self, **kw):
        return {"action": "fill", "target": "x", "value": "y"}


class _Lixo:
    async def decide(self, **kw):
        return "isto nao e um dict"


class _Explode:
    async def decide(self, **kw):
        raise TimeoutError("provider caiu")


chamar = lambda prov, img=b"x": asyncio.run(  # noqa: E731
    P.decidir_com_visao(prov, imagem=img, state=TELA, goal="g", collected={}, history=[]))

check("provider bom devolve a acao dele", chamar(_Bom())["action"] == "fill")
check("resposta ilegivel vira ask_human", chamar(_Lixo())["action"] == "ask_human")
check("provider que explode vira ask_human", chamar(_Explode())["action"] == "ask_human")
check("e o motivo nomeia a falha", "TimeoutError" in chamar(_Explode())["reason"])
check("sem imagem vira ask_human", chamar(_Bom(), None)["action"] == "ask_human")
check("sem provider vira ask_human", chamar(None)["action"] == "ask_human")

# 🔴 E7 — o contrato recebe BYTES, nao uma `page`. E o que permitira, um dia, o
# mesmo interpretador olhar uma foto que o segurado mandou no WhatsApp sem
# duplicar motor multimodal. Nao liga nada ao WhatsApp agora; so evita que a
# decisao de hoje impeca a de amanha.
import inspect  # noqa: E402

sig = inspect.signature(P.decidir_com_visao)
check("E7: a funcao de visao recebe `imagem` (bytes), nao `page`",
      "imagem" in sig.parameters and "page" not in sig.parameters)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
