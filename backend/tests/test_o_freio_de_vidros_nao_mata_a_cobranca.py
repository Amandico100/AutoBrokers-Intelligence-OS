# -*- coding: utf-8 -*-
"""Barrar o portal de VIDROS nao pode desligar o Auxiliar de COBRANCA.

O ERRO QUE ESTE ARQUIVO IMPEDE DE VOLTAR -- 18/08/2026.

O problema real era este: soltar o freio de emergencia para testar um
acionamento de ELETRICISTA no WhatsApp armava, no mesmo segundo, o portal de
VIDROS. `portal_tool.py:224` so consultava "agente ligado + freio solto" --
as mesmas duas condicoes do corredor de WhatsApp. Nao existia jeito de
liberar um sem liberar o outro. E o portal de vidros abre atendimento PAGO,
no nome de um segurado real, com placa e apolice puxadas da InfoCap -- fato
que nao se desfaz.

A MINHA PRIMEIRA RECOMENDACAO FOI `PORTAL_REAL_ENABLED=false`. Estava errada,
e o Founder desconfiou antes de aplicar:

    worker.py:975   `poll_loop` devolve ANTES do laco quando o gate esta off
    billing_collection.py:568   a Cobranca enfileira `portal_jobs` igual

Nao e "o portal de vidros para" -- e o portal-worker inteiro em standby. A
cobranca da manha seguinte morreria junto, e a causa estaria escondida atras
de uma variavel que parecia falar de outra coisa.

A LINHA CERTA JA ESTAVA NO REGISTRO, e nao precisava de variavel nova para
ser descoberta:

    cobranca_sweep ................ READ_ONLY             (le a carteira)
    login_check ................... READ_ONLY             (confere senha)
    vidros.abrir_atendimento ...... MATERIAL_SIDE_EFFECT  (abre chamado PAGO)

Entao o freio e por CLASSE DE EFEITO. Journey que so le continua rodando;
journey que cria fato no mundo precisa de autorizacao explicita -- e as que
ainda nao existem nascem barradas.

METADE DESTE ARQUIVO E CONTROLE. Um freio que barra tudo passaria em
qualquer teste que so verificasse "vidros esta barrado".
"""
from __future__ import annotations

import ast
import importlib.util
import os
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
        print("  [FALHOU] " + nome + ("  " + str(extra)[:260] if extra else ""))


spec = importlib.util.spec_from_file_location(
    "journeys_isolado", os.path.join(RAIZ, "portal_worker", "journeys", "__init__.py"))
J = importlib.util.module_from_spec(spec)
# `@dataclass` procura o modulo em `sys.modules` para resolver as anotacoes;
# carregar por caminho sem registrar quebra com AttributeError em NoneType.
sys.modules[spec.name] = J
spec.loader.exec_module(J)

VIDROS = ("vidros_lanternas", "abrir_atendimento")
COBRANCA = ("allianz_corretor", "cobranca_sweep")
LOGIN = ("allianz_corretor", "login_check")

# 📊 Os seis portais que o Auxiliar de Cobranca varre.
PORTAIS_DE_COBRANCA = ["allianz_corretor", "hdi_corretor", "tokiomarine_corretor",
                       "yelum_corretor", "mapfre_corretor", "zurich_corretor"]


def _com(valor):
    """Roda com a variavel nesse valor e devolve o ambiente ao que era."""
    antes = os.environ.get("PORTAL_EFEITO_MATERIAL_LIBERADO")

    class _Ctx:
        def __enter__(self):
            if valor is None:
                os.environ.pop("PORTAL_EFEITO_MATERIAL_LIBERADO", None)
            else:
                os.environ["PORTAL_EFEITO_MATERIAL_LIBERADO"] = valor

        def __exit__(self, *a):
            if antes is None:
                os.environ.pop("PORTAL_EFEITO_MATERIAL_LIBERADO", None)
            else:
                os.environ["PORTAL_EFEITO_MATERIAL_LIBERADO"] = antes

    return _Ctx()


# ==========================================================================
print("\n[1] Com o freio ARMADO (o estado de amanha)")
# ==========================================================================

with _com(None):  # variavel AUSENTE -- tem de ser o estado seguro
    check("ausencia da variavel ja barra o vidro",
          bool(J.motivo_para_barrar(*VIDROS)),
          "trava que precisa ser lembrada nao e trava")

    # 🔴 A ASSERCAO QUE ESTE ARQUIVO EXISTE PARA FAZER.
    check("e a COBRANCA continua passando",
          J.motivo_para_barrar(*COBRANCA) == "",
          "foi exatamente aqui que a minha primeira recomendacao errou")
    check("o login_check tambem continua passando",
          J.motivo_para_barrar(*LOGIN) == "")

    for portal in PORTAIS_DE_COBRANCA:
        check(f"cobranca em {portal} passa",
              J.motivo_para_barrar(portal, "cobranca_sweep") == "")

    check("o motivo da barragem e legivel, nao um booleano mudo",
          "efeito material" in J.motivo_para_barrar(*VIDROS).lower()
          or "PORTAL_EFEITO_MATERIAL_LIBERADO" in J.motivo_para_barrar(*VIDROS))

with _com("false"):
    check("`false` explicito barra igual", bool(J.motivo_para_barrar(*VIDROS)))
    check("e a cobranca segue passando", J.motivo_para_barrar(*COBRANCA) == "")

# ==========================================================================
print("\n[2] Com o freio SOLTO -- o vidro volta, e nada mais muda")
# ==========================================================================
#
# 🔴 CONTROLE. Sem este bloco, um `motivo_para_barrar` que devolvesse texto
# SEMPRE para vidros passaria em tudo acima -- e o portal de vidros nunca mais
# funcionaria, sem ninguem descobrir ate precisar dele.

with _com("true"):
    check("CONTROLE: o vidro CONSEGUE ser liberado",
          J.motivo_para_barrar(*VIDROS) == "",
          "um freio sem como soltar e um bug, nao uma trava")
    check("CONTROLE: a cobranca nao foi afetada pela liberacao",
          J.motivo_para_barrar(*COBRANCA) == "")

# ==========================================================================
print("\n[3] A regra e por CLASSE, nao por nome de portal")
# ==========================================================================
#
# Barrar "vidros" pelo nome deixaria a proxima journey material nascer solta.
# Estas assercoes leem o REGISTRO, entao uma journey nova entra coberta.

with _com(None):
    materiais = [k for k, d in J.JOURNEYS.items()
                 if d.effect_class == J.MATERIAL_SIDE_EFFECT]
    somente_leitura = [k for k, d in J.JOURNEYS.items()
                       if d.effect_class == J.READ_ONLY]

    check("existe ao menos uma journey material no registro", len(materiais) >= 1)
    check("existem journeys de leitura no registro", len(somente_leitura) >= 6,
          len(somente_leitura))
    check("TODA journey material esta barrada",
          all(J.motivo_para_barrar(*k.split(".", 1)) for k in materiais),
          [k for k in materiais if not J.motivo_para_barrar(*k.split(".", 1))])
    check("NENHUMA journey de leitura esta barrada",
          all(J.motivo_para_barrar(*k.split(".", 1)) == "" for k in somente_leitura),
          [k for k in somente_leitura if J.motivo_para_barrar(*k.split(".", 1))])

    # 🔴 CONTROLE do controle: as duas listas precisam ser DIFERENTES. Se todas
    # as journeys tivessem a mesma classe, as duas assercoes acima passariam
    # sem provar separacao nenhuma.
    check("CONTROLE: as duas listas sao mesmo diferentes",
          set(materiais) and set(somente_leitura)
          and not (set(materiais) & set(somente_leitura)))

    check("journey desconhecida nao e barrada por este freio "
          "(quem chama ja trata com outro erro)",
          J.motivo_para_barrar("portal_que_nao_existe", "nada") == "")

# ==========================================================================
print("\n[4] O freio esta ligado nos DOIS pontos")
# ==========================================================================
#
# Na criacao do job E na execucao. So na criacao deixaria rodar o que ja
# estava na fila quando alguem apertou o freio -- e e na emergencia que a fila
# esta cheia.


def chama_o_freio(caminho: str, funcao: str) -> bool:
    """Existe uma chamada REAL a `motivo_para_barrar` dentro desta funcao?

    Le a arvore, nao o texto. Casar a string pegaria o comentario que EXPLICA
    o freio -- ja aconteceu seis vezes nesta SPEC.
    """
    with open(os.path.join(RAIZ, caminho), encoding="utf-8") as fh:
        arvore = ast.parse(fh.read())
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if no.name != funcao:
            continue
        for x in ast.walk(no):
            if isinstance(x, ast.Call) and getattr(x.func, "id", "") == "motivo_para_barrar":
                return True
    return False


check("o portal-worker barra na EXECUCAO do job",
      chama_o_freio("portal_worker/worker.py", "_run_job"))
check("o agente barra na CRIACAO do pedido",
      chama_o_freio("app/agents/tools/portal_tool.py", "_envio_liberado"))

_SEM_A_CHAMADA = chr(10).join([
    "def _run_job(supa, job):",
    "    # motivo_para_barrar(portal, journey)",
    '    return "motivo_para_barrar"',
])
_FAKE = os.path.join(RAIZ, "..", "_fake_para_controle.py")
with open(_FAKE, "w", encoding="utf-8") as fh:
    fh.write(_SEM_A_CHAMADA)
try:
    check("CONTROLE: o detector nao acha a chamada onde ha so o comentario",
          not chama_o_freio(os.path.relpath(_FAKE, RAIZ), "_run_job"))
finally:
    os.remove(_FAKE)

# ==========================================================================
print("\n[5] A COBRANCA continua inteira -- nada do caminho dela mudou")
# ==========================================================================
#
# 🔴 O Founder: "VC NAO PODE TENTAR AJUSTAR UMA COISA E ESTRAGAR OUTRA."
# Estas assercoes olham o caminho da cobranca de ponta a ponta.

with open(os.path.join(RAIZ, "app/services/billing_collection.py"), encoding="utf-8") as fh:
    billing = fh.read()

check("a cobranca ainda enfileira portal_jobs", '"portal_jobs"' in billing)
check("com a journey cobranca_sweep", '"journey": "cobranca_sweep"' in billing)
check("e ainda pede o download dos boletos", '"download_boletos": True' in billing)
check("a constante do registro nao mudou de nome",
      J.JOURNEY_COBRANCA == "cobranca_sweep")
check("os seis portais de cobranca continuam registrados",
      all(f"{p}.cobranca_sweep" in J.JOURNEYS for p in PORTAIS_DE_COBRANCA),
      [p for p in PORTAIS_DE_COBRANCA if f"{p}.cobranca_sweep" not in J.JOURNEYS])

with open(os.path.join(RAIZ, "portal_worker/worker.py"), encoding="utf-8") as fh:
    worker = fh.read()

# 🔴 O erro exato que quase cometi: parar o laco em vez do job.
check("o freio de efeito material NAO foi parar no poll_loop",
      "motivo_para_barrar" not in worker[worker.index("async def poll_loop"):],
      "no poll_loop ele derrubaria a cobranca junto -- foi a recomendacao errada")
check("CONTROLE: mas ele ESTA em algum lugar do worker",
      "motivo_para_barrar" in worker)

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
