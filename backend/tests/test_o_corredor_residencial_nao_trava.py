# -*- coding: utf-8 -*-
"""O corredor Allianz RESIDENCIAL atravessa a URA sem pedir humano.

O DEFEITO, medido em 18/08/2026 no acervo de 24 sessoes Allianz reais.

A URA residencial manda DEZ vezes esta tela:

    "E para quando precisa do *Encanador*?  *1 -* Agora  *2 -* Quero agendar"

O passo que a responde existia SO no playbook de AUTOMOVEL, e a ancora de la
(reboque|guincho|servico|profissional) nao casa "*Eletricista*" nem
"*Encanador*" -- que sao os nomes que a URA usa no residencial.

Sem passo mapeado, a tela caia no cerebro adaptativo. E em modo TESTE o cerebro
recebe a regra "se a seguradora for CONFIRMAR/ABRIR o servico (agendar, ...),
responda NAO_SEI". Ele lia a palavra "agendar" NA PROPRIA TELA e travava. Duas
recusas e a sessao virava `needs_human`.

  O teste falhava POR SER TESTE, num passo que em modo real passaria.

Mesma coisa com as telas informativas (Termo de Privacidade 31x, "dicas
importantes" 15x, "oferece diversos tipos de seguro" 19x): o AUTO tinha `noop`,
o residencial nao. Responder nelas quebra o menu.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:240] if extra else ""))


# Carrega o modulo do playbook SOZINHO. `import app.services...` puxa o
# `__init__` do pacote, que importa o SDK da OpenAI -- ausente numa maquina de
# teste. O playbook e uma estrutura de dados pura e nao precisa de nada disso.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "corridor_playbooks_isolado",
    os.path.join(RAIZ, "app", "services", "corridor_playbooks.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
PB = _mod.ALLIANZ_RESIDENCIAL_WHATSAPP_V1

PASSOS = PB["ura_steps"]


def passo_que_casa(texto: str):
    """O primeiro passo cuja ancora casa -- a mesma ordem de `match_ura_step`."""
    for p in PASSOS:
        anc = p.get("anchor")
        if anc and re.search(anc, texto, re.IGNORECASE):
            return p
    return None


# 📊 TEXTOS REAIS da URA da Allianz, do acervo.
TELA_QUANDO_ELETRICISTA = "Certo! E para quando precisa do *Eletricista*? *1 -* Agora *2 -* Quero agendar *3 -* Voltar"
TELA_QUANDO_ENCANADOR = "Certo! E para quando precisa do *Encanador*? *1 -* Agora *2 -* Quero agendar *3 -* Voltar"
TELA_QUANDO_CHAVEIRO = "Certo! E para quando precisa do *Chaveiro*? *1 -* Agora *2 -* Quero agendar"
TELA_CONFIRMA = "RESUMO DO ATENDIMENTO ... Podemos confirmar o atendimento? *1 -* Sim *2 -* Nao"
TELA_PRIVACIDADE = "Antes de continuarmos, veja nosso Termo de Privacidade: https://allianz.com.br/privacidade"
TELA_DICAS = "Tenho algumas dicas importantes para conseguir te atender melhor!"
TELA_OFERTA = "Antes de prosseguirmos, voce sabia que a Allianz oferece diversos tipos de seguro?"
TELA_INVALIDA = "Opcao invalida."
TELA_COMPLEMENTO = "Por favor, informe o complemento do endereco"


# 📊 A TELA QUE TRAVOU O TESTE DE 18/08/2026 -- texto literal de
# `observed_events`, 01:51:33 e 01:59:07. Vista OITO vezes desde 28/07.
TELA_TIPO_DE_REPARO = (
    "*Importante:* Esse servico de eletricista esta disponivel apenas para "
    "reparos eletricos na residencia | *1 -* Preciso de reparo eletrico para "
    "residencia | *2 -* Preciso de reparos eletricos em aparelhos ou "
    "eletrodomesticos."
)
TELA_O_QUE_ACONTECEU = ("O que aconteceu? *1 -* Casa inteira ou parcial sem energia "
                        "*2 -* Curto circuito *3 -* Outros")
TELA_DESCREVA = "E para finalizar: descreva detalhadamente o que aconteceu"
TELA_DISJUNTOR = "*DICA:* verifique se o disjuntor esta na posicao ligado."
# 📊 As duas redacoes NOVAS da URA de 2026, que quebraram ancoras existentes.
TELA_QUAL_SEGURO_2026 = "Qual seguro deseja utilizar? *1 -* Residencial *2 -* Condominio"
TELA_CPF_2026 = "Que bom que voltou! Gostaria de continuar com o CPF/CNPJ 030.###.###-##?"

# ==========================================================================
print("\n[1] A tela do 'quando' e RESPONDIDA, para qualquer profissional")
# ==========================================================================

for rotulo, tela in (("Eletricista", TELA_QUANDO_ELETRICISTA),
                     ("Encanador", TELA_QUANDO_ENCANADOR),
                     ("Chaveiro", TELA_QUANDO_CHAVEIRO)):
    p = passo_que_casa(tela)
    check(f"{rotulo}: existe passo mapeado", p is not None and p.get("step") == "quando",
          f"casou com: {p.get('step') if p else 'NENHUM'}")
    check(f"{rotulo}: responde 1 (agora), nao agenda",
          bool(p) and p.get("reply") == "1", p.get("reply") if p else None)

# ==========================================================================
print("\n[2] A tela de CONFIRMACAO nao foi engolida por outra ancora")
# ==========================================================================
#
# 🔴 Esta e a assercao que protege o freio de teste. Se a ancora do `quando`
# ou a dos avisos casasse o RESUMO, o corredor responderia "1" nele -- e o
# "teste" abriria chamado de verdade.

p = passo_que_casa(TELA_CONFIRMA)
check("a confirmacao final casa com `confirmar_atendimento`, e nada antes",
      p is not None and p.get("step") == "confirmar_atendimento",
      f"casou com: {p.get('step') if p else 'NENHUM'}")

check("e a palavra 'agendar' NAO aparece na ancora do `quando` "
      "(senao ela casaria o RESUMO por acidente)",
      "agendar" not in str(next(x for x in PASSOS if x.get("step") == "quando")["anchor"]).lower())

# ==========================================================================
print("\n[3] Telas informativas NAO recebem resposta")
# ==========================================================================

for rotulo, tela in (("Termo de Privacidade", TELA_PRIVACIDADE),
                     ("dicas importantes", TELA_DICAS),
                     ("oferta de seguros", TELA_OFERTA),
                     ("opcao invalida", TELA_INVALIDA)):
    p = passo_que_casa(tela)
    check(f"{rotulo}: e tratada como `noop`",
          bool(p) and bool(p.get("noop")) and not p.get("reply"),
          f"casou com: {p.get('step') if p else 'NENHUM'}, reply={p.get('reply') if p else None!r}")

# ==========================================================================
print("\n[3.5] As telas de 18/08 que NAO existiam no playbook")
# ==========================================================================

p = passo_que_casa(TELA_TIPO_DE_REPARO)
check("a tela que TRAVOU o teste agora tem passo",
      bool(p) and p.get("step") == "tipo_de_reparo_eletrico",
      str(p)[:80])
check("e responde 1 -- reparo na RESIDENCIA, nao eletrodomestico",
      bool(p) and p.get("reply") == "1")

p = passo_que_casa(TELA_O_QUE_ACONTECEU)
check("`O que aconteceu?` tem passo", bool(p) and p.get("step") == "o_que_aconteceu")
# 🔴 Esta escolhe o TIPO DE DEFEITO. Constante aqui abriria chamado errado.
check("e ela NAO tem resposta fixa -- vem do caso",
      bool(p) and p.get("reply", "").startswith("{") and bool(p.get("requires")),
      str(p.get("reply") if p else None))

check("`descreva detalhadamente` tem passo",
      (passo_que_casa(TELA_DESCREVA) or {}).get("step") == "descricao_detalhada")
check("a DICA do disjuntor e silencio, nao resposta",
      bool((passo_que_casa(TELA_DISJUNTOR) or {}).get("noop")))

# As duas redacoes de 2026 que quebraram ancoras existentes.
check("a redacao NOVA de `Qual seguro deseja utilizar?` volta a casar",
      (passo_que_casa(TELA_QUAL_SEGURO_2026) or {}).get("step") == "menu_qual_seguro",
      str(passo_que_casa(TELA_QUAL_SEGURO_2026))[:80])
check("a redacao NOVA do CPF (`Que bom que voltou!`) volta a casar",
      (passo_que_casa(TELA_CPF_2026) or {}).get("step") == "cpf_anterior",
      str(passo_que_casa(TELA_CPF_2026))[:80])

# 🔴 CONTROLE -- a redacao ANTIGA nao pode ter sido perdida no afrouxamento.
check("CONTROLE: a redacao ANTIGA do `qual O seguro QUE deseja` ainda casa",
      (passo_que_casa("Qual o seguro que deseja utilizar? 1 - Residencia")
       or {}).get("step") == "menu_qual_seguro")
check("CONTROLE: a redacao ANTIGA do CPF ainda casa",
      (passo_que_casa("Em nossa ultima conversa, utilizamos o CPF 030...")
       or {}).get("step") == "cpf_anterior")

# 🔴 CONTROLE -- alarguei tres ancoras hoje. Nenhuma pode ter engolido a tela
# que importa nem a que travou.
check("CONTROLE: a confirmacao final continua sendo dela mesma",
      (passo_que_casa(TELA_CONFIRMA) or {}).get("step") == "confirmar_atendimento")
check("CONTROLE: o noop nao engoliu a tela que travou",
      not (passo_que_casa(TELA_TIPO_DE_REPARO) or {}).get("noop"))

# ==========================================================================
print("\n[4] CONTROLE -- o casador CONSEGUE nao casar, e nao casa tudo")
# ==========================================================================
#
# Sem estas linhas, um `passo_que_casa` que devolvesse sempre o primeiro passo
# (ou sempre None) faria metade das assercoes acima passar por engano.

check("CONTROLE: uma tela que nao existe no playbook nao casa com nada",
      passo_que_casa("mensagem que a URA nunca mandaria sobre zebras em marte") is None)
check("CONTROLE: uma tela conhecida e DIFERENTE casa com o passo dela",
      (passo_que_casa(TELA_COMPLEMENTO) or {}).get("step") == "complemento_referencia")
check("CONTROLE: as tres telas do 'quando' casam com o MESMO passo, "
      "e nao cada uma com um",
      len({(passo_que_casa(t) or {}).get("step")
           for t in (TELA_QUANDO_ELETRICISTA, TELA_QUANDO_ENCANADOR, TELA_QUANDO_CHAVEIRO)}) == 1)

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
