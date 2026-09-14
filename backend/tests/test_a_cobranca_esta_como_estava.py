# -*- coding: utf-8 -*-
"""O Auxiliar de Cobranca funciona EXATAMENTE como funcionava em 17/08/2026.

POR QUE ESTE ARQUIVO EXISTE

O Founder: *"A COBRANÇA ESTÁ FUNCIONANDO DA MESMA FORMA QUE ANTES? NÃO PODEMOS
FALHAR NESSE AUXILIAR. É OBRIGATÓRIO QUE ISSO FUNCIONE."*

Ele tem razão em desconfiar. Em 18/08 eu recomendei `PORTAL_REAL_ENABLED=false`
para trancar o portal de vidros, e essa recomendação teria **desligado a
Cobrança junto** -- `poll_loop` devolve antes do laço com esse gate off
(`worker.py:975`), e a Cobrança enfileira `portal_jobs` igual aos vidros
(`billing_collection.py:568`). Ele desconfiou antes de aplicar.

📊 O QUE A COBRANCA FEZ EM 17/08, e que precisa continuar fazendo igual:

    Jobs: 1 | inadimplentes: 3 | boletos baixados: 3
    Podem ser cobrados: 3 | retidos: 0
    Modo teste ativo: 3 simulacao(oes) enviada(s) para ...7463
    Boletos anexados como PDF: 3

O CAMINHO INTEIRO, e o que este arquivo verifica em cada elo:

    routine -> _enqueue_job -> portal_jobs(journey='cobranca_sweep')
            -> portal-worker poll_loop -> _run_job -> journey
            -> boletos no bucket
            -> send_message(numero, texto, integracao)   [texto]
            -> send_document(...)                        [o PDF]

Nenhum desses elos pode ter mudado. Os cinco commits de 18/08 tocaram nove
arquivos de produção; **dois** deles estão neste caminho, e este guarda existe
para provar que os dois passam reto.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import os
import sys

NL = chr(10)
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
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


def carregar(rotulo, caminho):
    spec = importlib.util.spec_from_file_location(rotulo, os.path.join(RAIZ, caminho))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


J = carregar("journeys_cob", "portal_worker/journeys/__init__.py")
BAL = carregar("balloons_cob", "app/services/whatsapp/balloons.py")
BILL = carregar("billing_cob", "app/services/billing_collection.py")

with open(os.path.join(RAIZ, "app/services/whatsapp_service.py"), encoding="utf-8") as fh:
    FONTE_WS = fh.read()
with open(os.path.join(RAIZ, "app/services/billing_collection.py"), encoding="utf-8") as fh:
    FONTE_BILLING = fh.read()
with open(os.path.join(RAIZ, "portal_worker/worker.py"), encoding="utf-8") as fh:
    FONTE_WORKER = fh.read()

PORTAIS = ["allianz_corretor", "hdi_corretor", "tokiomarine_corretor",
           "yelum_corretor", "mapfre_corretor", "zurich_corretor"]

# ==========================================================================
print("\n[1] O elo do FREIO -- a Cobranca nao e barrada, com o freio armado")
# ==========================================================================

os.environ.pop("PORTAL_EFEITO_MATERIAL_LIBERADO", None)  # o estado de amanha

for portal in PORTAIS:
    check(f"{portal}.cobranca_sweep passa",
          J.motivo_para_barrar(portal, "cobranca_sweep") == "")
    check(f"{portal}.login_check passa",
          J.motivo_para_barrar(portal, "login_check") == "")

# 🔴 CONTROLE -- o freio EXISTE e barra alguma coisa. Sem esta linha, um
# `motivo_para_barrar` que devolvesse "" sempre passaria em tudo acima.
check("CONTROLE: o freio barra o vidro (logo, ele funciona)",
      bool(J.motivo_para_barrar("vidros_lanternas", "abrir_atendimento")))

# 🔴 E o erro que eu quase cometi: o freio NAO pode estar no laco do worker.
check("o freio nao entrou no `poll_loop` (la ele mataria a Cobranca)",
      "motivo_para_barrar" not in FONTE_WORKER[FONTE_WORKER.index("async def poll_loop"):])

# ==========================================================================
print("\n[2] O elo do ENVIO -- `send_message` de 3 argumentos e o de antes")
# ==========================================================================
#
# A Cobranca chama `send_message(number, text, integration)` -- tres
# posicionais (`billing_collection.py:1010`). O parametro `bloco_unico` que
# entrou em 18/08 e keyword-only COM DEFAULT: quem nao passa nada continua no
# caminho antigo, letra por letra.

arvore = ast.parse(FONTE_WS)
assinatura = next(n for n in ast.walk(arvore)
                  if isinstance(n, ast.FunctionDef) and n.name == "send_message")

check("os 3 primeiros parametros continuam posicionais e na mesma ordem",
      [a.arg for a in assinatura.args.args] == ["self", "to_number", "text", "integration"],
      [a.arg for a in assinatura.args.args])
check("`bloco_unico` e keyword-only (nao empurra nenhum posicional)",
      [a.arg for a in assinatura.args.kwonlyargs] == ["bloco_unico"],
      [a.arg for a in assinatura.args.kwonlyargs])
check("e o default dele e False -- omitir = comportamento antigo",
      len(assinatura.args.kw_defaults) == 1
      and getattr(assinatura.args.kw_defaults[0], "value", None) is False)

# A prova de comportamento, e nao so de assinatura -- MIGRADA em 13/09/2026
# (SPEC-EXTRA-001.6 §12.3; CLAUDE.md §9.3 e §9.4).
#
# 📊 Este bloco afirmava "o inadimplente recebe UMA mensagem, como sempre
# recebeu" medindo uma constante de 292 caracteres ESCRITA AQUI DENTRO, que o
# produto nao envia. O texto que o produto MONTA tem 332 caracteres e virava 2
# baloes -- o guarda estava verde e a atendente recebia picotado. E o helper
# `caminho_de_hoje` reimplementava o `if bloco_unico` do produto: provava que o
# fatiador funciona, nao que alguem o usa.
#
# Agora: o texto vem do MOTOR (`build_customer_message` sobre o template
# padrao), a decisao vem do PRODUTO (`e_documento(kind)`, em `platform_outbound`)
# e os baloes sao CONTADOS por um provider duble no seam REAL de `send_message`.
import app.services.platform_outbound as _PO
import app.services.whatsapp.registry as _REG
import app.services.whatsapp.voz_propria as _VP
import app.services.whatsapp_service as _WS


class _Res:
    ok = True
    success = True


class _Provider:
    def __init__(self):
        self.textos = []

    def send_text(self, to_number, text):
        self.textos.append(str(text))
        return _Res()


_duble = _Provider()
_REG.resolve_provider = lambda integration: _duble
_VP.registrar_nossa_fala = lambda *a, **k: None
_WS._dormir = lambda *a, **k: None
_INTEG = {"provider": "evolution-go", "company_id": "aaaaaaaa-0000-0000-0000-00000000a1fa"}
_ITEM = {"cliente_nome": "Segurado Exemplo", "numero_parcela": "3/12", "vencimento": "2026-09-03",
         "valor": 733.13, "numero_apolice": "APOL-B1", "portal": "tokiomarine_corretor",
         "recibo": "B-0001"}
_CFG = BILL.normalize_billing_config({"send_mode": "equipe", "team_number": "5500900000009",
                                      "attendant_name": "Atendente Alfa",
                                      "brokerage_name": "Corretora Alfa"})
# 📊 A mensagem REAL que a Cobranca manda -- montada pelo motor, nao copiada.
MSG_DA_COBRANCA = BILL.build_customer_message(_ITEM, BILL.DEFAULT_MESSAGE_TEMPLATE, _CFG)


def baloes_que_o_canal_recebe(texto, **kw):
    """`send_message` REAL; o duble conta o que o Evolution receberia."""
    _duble.textos.clear()
    _WS.WhatsappService().send_message("5500900000009", texto, _INTEG, **kw)
    return list(_duble.textos)


check("a Cobranca e DOCUMENTO para o produto (`e_documento('billing_equipe')`)",
      _PO.e_documento("billing_equipe") is True)
check("a mensagem REAL da Cobranca (%d ch) chega ao canal em UM balao pelo caminho de documento"
      % len(MSG_DA_COBRANCA),
      len(baloes_que_o_canal_recebe(MSG_DA_COBRANCA,
                                    bloco_unico=_PO.e_documento("billing_equipe"))) == 1)
check("  ... e chega inteira",
      baloes_que_o_canal_recebe(MSG_DA_COBRANCA, bloco_unico=True) == [MSG_DA_COBRANCA])

# 🔴 CONTROLE -- os dois caminhos precisam CONSEGUIR ser diferentes, e o
# proprio texto da Cobranca ja e a prova: como conversa, ele parte em dois.
check("CONTROLE: a MESMA mensagem, como conversa (`bloco_unico=False`), parte em 2+",
      len(baloes_que_o_canal_recebe(MSG_DA_COBRANCA)) >= 2,
      len(baloes_que_o_canal_recebe(MSG_DA_COBRANCA)))
TEXTO_LONGO = (NL * 2).join([f"Paragrafo numero {i} " + "palavra " * 12
                             for i in range(6)])
check("CONTROLE: com texto longo, os dois caminhos DIVERGEM",
      baloes_que_o_canal_recebe(TEXTO_LONGO)
      != baloes_que_o_canal_recebe(TEXTO_LONGO, bloco_unico=True))
check("CONTROLE: e a humanizacao e a que parte em varios",
      len(baloes_que_o_canal_recebe(TEXTO_LONGO)) > 1)

check("`send_document` (o PDF do boleto) nao foi tocado",
      "def send_document" in FONTE_WS
      and "bloco_unico" not in FONTE_WS[FONTE_WS.index("def send_document"):
                                        FONTE_WS.index("def send_document") + 1500])

# ==========================================================================
print("\n[3] O elo da FILA -- o job da Cobranca sai igual")
# ==========================================================================

check("ainda insere em portal_jobs", '"portal_jobs"' in FONTE_BILLING)
check("com journey cobranca_sweep", '"journey": "cobranca_sweep"' in FONTE_BILLING)
check("pedindo download dos boletos", '"download_boletos": True' in FONTE_BILLING)
check("e exigindo os downloads", '"require_downloads": True' in FONTE_BILLING)
check("a constante do registro nao mudou", J.JOURNEY_COBRANCA == "cobranca_sweep")
check("os seis portais continuam no registro",
      all(f"{p}.cobranca_sweep" in J.JOURNEYS for p in PORTAIS))

# ==========================================================================
print("\n[4] O modo TESTE do Founder continua inteiro")
# ==========================================================================
#
# Os quatro consertos de 17/08 que fizeram a Cobranca funcionar pela primeira
# vez. Nenhum pode ter sido desfeito.

check("modo teste ainda existe", "modo_teste" in FONTE_BILLING)
check("o intervalo curto do governador continua",
      "para_numero_de_teste" in FONTE_BILLING)
# 19/08/2026 -- CLAUDE.md 9.3: este guarda afirmava a coisa certa e nao tinha
# como falhar. Ele checava `"already" in FONTE_BILLING and "_record_sent" in
# FONTE_BILLING`: as duas palavras existem no arquivo com a dedup ligada OU
# desligada, entao ele passava dos dois jeitos. A dedup saiu do papel nesse dia
# (`billing_sent_log` finalmente e lido e escrito); o que continua valendo e o
# PADRAO do modo teste, decidido em 17/08 -- e agora isso e perguntado a
# funcao, que consegue responder as duas coisas.
check("a dedup continua DESLIGADA por padrao no modo teste (o boleto reenviado amanha)",
      BILL.dedup_de_envio_ativa("test", env={}) is False)
check("CONTROLE: e o mecanismo existe de verdade -- live deduplica",
      BILL.dedup_de_envio_ativa("live", env={}) is True)
check("o erro ainda carrega o motivo real, nao so o tipo",
      "_motivo[:220]" in FONTE_BILLING or "str(e)" in FONTE_BILLING)
check("o PDF ainda e anexado", "send_document" in FONTE_BILLING)

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
