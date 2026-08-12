# -*- coding: utf-8 -*-
"""A Cobranca alcanca todas as seguradoras, e nenhuma cai em silencio.

Este arquivo e UTF-8, e nao ASCII como os vizinhos, por um motivo: a secao [11]
compara o TEXTO das mensagens que a equipe le no WhatsApp. Elas sao escritas
para gente, com acento e emoji -- e um teste que so consegue afirmar sobre o
texto sem acento nao guarda o texto que sai de verdade.

O defeito que estes testes seguram
==================================
Antes deste bloco, a cobranca era Allianz-only por TRES caminhos diferentes, e
nenhum deles dava erro:

    1. journeys/__init__.py .... if/elif com 4 entradas
    2. billing_collection.py ... DEFAULT_PORTAL_KEYS = ["allianz_corretor"]
    3. rotinas/page.tsx ........ um checkbox fixo que SUBSTITUIA a lista

E dois defeitos que faziam inadimplente sumir sem uma linha de aviso:

    4. items[:max_boletos_por_execucao] no ENVIO
       (teto de download aplicado como teto de mensagem)
    5. portal selecionado sem journey era `continue` mudo

CLAUDE.md 9.3 -- um guarda que nao tem como falhar nao guarda nada. Cada teste
aqui usa DOIS portais que conseguem ser diferentes, ou uma quantidade maior que
o teto antigo. Se alguem reintroduzir o hardcode, estes testes ficam vermelhos.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:200] if extra else ""))


def _load(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, str(ROOT / caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bc = _load("billing_collection", "app/services/billing_collection.py")
hdi = _load("hdi_corretor", "portal_worker/journeys/hdi_corretor.py")
from portal_worker.journeys import JOURNEYS, get_journey, portais_com_cobranca, tem_cobranca  # noqa: E402

# O HTML REAL da HDI, com os dados trocados. Estrutura identica a de producao.
sys.path.insert(0, str(ROOT / "tests"))
from fixtures.hdi_parcelas import AGUARDE, RESULTADO, PONTE, SELECT_TIPO  # noqa: E402

RESULTADO_P = RESULTADO

AGORA = datetime.now(timezone.utc)


def _dias_atras(n):
    return (AGORA - timedelta(days=n)).strftime("%Y-%m-%d")


def _horas_atras(n):
    return (AGORA - timedelta(hours=n)).strftime("%Y-%m-%d")


def _norm_ascii(texto):
    import unicodedata
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()


# ---------------------------------------------------------------- registro
print("\n[1] O registro de journeys conhece mais de um portal")

check("registro tem Allianz e HDI",
      tem_cobranca("allianz_corretor") and tem_cobranca("hdi_corretor"))
check("DOIS portais com cobranca, nao um",
      len(portais_com_cobranca()) >= 2, portais_com_cobranca())
check("portal sem journey responde False, nao explode",
      tem_cobranca("bradesco_corretor") is False)
check("journey inexistente devolve None (worker grava erro legivel)",
      get_journey("nao_existe", "cobranca_sweep") is None)
check("resolve funcao real da HDI", callable(get_journey("hdi_corretor", "cobranca_sweep")))
check("resolve funcao real da Allianz", callable(get_journey("allianz_corretor", "cobranca_sweep")))
check("mapa nao tem entrada apontando para modulo/funcao inexistente",
      all(get_journey(*k.rsplit(".", 1)) is not None for k in JOURNEYS))


# ------------------------------------------------------- servico multi-portal
print("\n[2] O servico nao volta a ser Allianz-only")

cfg_vazio = bc.normalize_billing_config({"kind": bc.BILLING_KIND})
check("default varre TODAS as seguradoras automatizadas, nao so uma",
      len(bc.selected_portal_keys(cfg_vazio)) >= 2, bc.selected_portal_keys(cfg_vazio))
check("default inclui HDI", "hdi_corretor" in bc.selected_portal_keys(cfg_vazio))
check("config explicita com DOIS portais e preservada",
      bc.selected_portal_keys({"portal_keys": ["allianz_corretor", "hdi_corretor"]})
      == ["allianz_corretor", "hdi_corretor"])
check("DEFAULT_PORTAL_KEYS nao e uma lista de tamanho 1 fixa",
      len(bc.DEFAULT_PORTAL_KEYS) >= 2, bc.DEFAULT_PORTAL_KEYS)

print("\n[3] Cada seguradora tem nome proprio na mensagem ao segurado")
check("Allianz", bc._portal_insurer_name({"portal": "allianz_corretor"}, {}) == "ALLIANZ")
check("HDI", bc._portal_insurer_name({"portal": "hdi_corretor"}, {}) == "HDI SEGUROS")
check("Porto", bc._portal_insurer_name({"portal": "porto_corretor"}, {}) == "PORTO SEGURO")
check("portal novo nao vira a palavra generica 'seguradora'",
      bc._portal_insurer_name({"portal": "sancor_corretor"}, {}) == "SANCOR")
check("dois portais dao nomes DIFERENTES (o guarda consegue falhar)",
      bc._portal_insurer_name({"portal": "allianz_corretor"}, {})
      != bc._portal_insurer_name({"portal": "hdi_corretor"}, {}))


# ------------------------------------------------------------------ a fila
print("\n[4] A fila de cobranca: carencia, ordem e nada sumindo")

itens = [
    {"portal": "hdi_corretor", "recibo": "H-velho", "vencimento": _dias_atras(60), "whatsapp": "5547999990001"},
    {"portal": "allianz_corretor", "recibo": "A-medio", "vencimento": (AGORA - timedelta(days=20)).strftime("%d/%m/%Y"), "whatsapp": "5547999990002"},
    {"portal": "hdi_corretor", "recibo": "H-novo", "vencimento": _dias_atras(5), "whatsapp": "5547999990003"},
    {"portal": "hdi_corretor", "recibo": "H-ontem", "vencimento": _horas_atras(10), "whatsapp": "5547999990004"},
    {"portal": "hdi_corretor", "recibo": "H-semfone", "vencimento": _dias_atras(30), "whatsapp": ""},
    {"portal": "allianz_corretor", "recibo": "A-semdata", "vencimento": "", "whatsapp": "5547999990006"},
]
fila, retidos = bc.fila_de_cobranca(itens)
ordem = [i["recibo"] for i in fila]

check("carencia de 48h segura quem venceu ha 10h", "H-ontem" not in ordem)
check("quem venceu ha 5 dias entra", "H-novo" in ordem)
check("fila sai do MAIS VELHO para o mais novo",
      ordem == ["H-velho", "A-medio", "H-novo"], ordem)
check("ordem mistura dd/mm/aaaa com aaaa-mm-dd corretamente",
      ordem.index("H-velho") < ordem.index("A-medio") < ordem.index("H-novo"), ordem)
check("a fila junta portais DIFERENTES (nao e uma seguradora so)",
      len({i["portal"] for i in fila}) == 2, ordem)
check("nada some: fila + retidos == tudo que foi colhido",
      len(fila) + len(retidos) == len(itens))
check("sem telefone vira RETIDO com motivo, nao silencio",
      any("sem telefone" in r["retido_por"] for r in retidos))
check("sem data legivel vira RETIDO (nao saber nunca vira permissao)",
      any("sem data" in r["retido_por"] for r in retidos))
check("todo retido tem motivo escrito", all(r.get("retido_por") for r in retidos))

vinte = [
    {"portal": "hdi_corretor", "recibo": "R%02d" % n, "vencimento": _dias_atras(90 - n),
     "whatsapp": "554799999%04d" % n}
    for n in range(20)
]
fila20, _ = bc.fila_de_cobranca(vinte)
check("20 atrasados geram fila de 20 (o teto de download nao corta o envio)",
      len(fila20) == 20, len(fila20))
check("fila de 20 e estavel entre duas execucoes (retomada previsivel)",
      [i["recibo"] for i in bc.fila_de_cobranca(vinte)[0]] == [i["recibo"] for i in fila20])

fonte = (ROOT / "app" / "services" / "billing_collection.py").read_text(encoding="utf-8")
check("o envio NAO fatia mais a lista por max_boletos_por_execucao",
      "items[: int(cfg[\"max_boletos_por_execucao\"])]" not in fonte
      and "a_enviar = ordenar_para_entrega(items)" in fonte)
check("portal sem automacao vira aviso no relatorio, nao `continue` mudo",
      "ainda NAO tem automacao de cobranca" in fonte)


# ------------------------------------------------------------------- HDI
print("\n[5] HDI: leitura da tela Parcela")

TABELA = """<table>
<tr><th>Documento/Parcela</th><th>Vencto.</th><th>Nome cliente</th><th>Valor</th><th>Posicao</th><th>Forma</th><th>Gerar</th></tr>
<tr><td>01.008.119.003755.000000 - 02 de 06</td><td>09/08/26</td><td>CONDOMINIO HORIZON RESIDENCIAL</td>
<td>1.006,02</td><td>Parcela a Vencer</td><td>Boleto</td>
<td><a href="/web/hdidigital/dsp_boleto.htm?p=abc">2&ordf; via</a></td></tr>
<tr><td>01.008.425.005607.000000 - 03 de 04</td><td>08/03/26</td><td>AMORATTO INDUSTRIA</td>
<td>1.479,91</td><td>Parcela em Atraso</td><td>D&eacute;bito</td>
<td>Parcela diferente de Boleto Banc&aacute;rio.</td></tr>
<tr><td>01.008.777.001111.000000 - 05 de 10</td><td>01/05/26</td><td>MARIA DA SILVA</td>
<td>340,00</td><td>Parcela em Atraso</td><td>Boleto</td>
<td><a href="/web/hdidigital/dsp_boleto.htm?p=zzz">2&ordf; via</a></td></tr>
</table>"""

parcelas = hdi.extrair_parcelas(TABELA)
por_doc = {p["documento"][-13:]: p for p in parcelas}
check("le as 3 linhas e ignora o cabecalho", len(parcelas) == 3, len(parcelas))
check("separa 'em Atraso' de 'a Vencer'",
      sum(1 for p in parcelas if p["em_atraso"]) == 2)
check("decodifica entidade HTML: D&eacute;bito vira debito",
      por_doc["005607.000000"]["forma_pagamento"] == "debito")
check("sem-boleto fica MARCADO com o motivo, nao sumido",
      "nao emite 2a via de boleto" in por_doc["005607.000000"]["sem_boleto_motivo"],
      por_doc["005607.000000"]["sem_boleto_motivo"])
check("boleto de verdade tem link de 2a via",
      por_doc["001111.000000"]["link_segunda_via"].endswith("dsp_boleto.htm?p=zzz"))
check("valor em real brasileiro vira numero", por_doc["001111.000000"]["valor"] == 340.0)
check("vencimento dd/mm/aa vira ISO", por_doc["001111.000000"]["vencimento"] == "2026-05-01")
check("nome do cliente e lido", por_doc["001111.000000"]["cliente_nome"] == "MARIA DA SILVA")

atrasados = hdi.apenas_atrasados(parcelas)
check("so os atrasados entram", len(atrasados) == 2)
check("e saem do mais velho para o mais novo",
      [a["vencimento"] for a in atrasados] == ["2026-03-08", "2026-05-01"])

campos = hdi.extrair_campos_do_form(
    '<form><input type="hidden" name="m_cod_corretor" value="500027665" />'
    '<input type="hidden" name="c_pc" value="K659709550002_4420" />'
    '<input type="hidden" name="l_s" value="008" /></form>')
check("colhe a identidade da sessao do formulario do passo 1",
      campos.get("m_cod_corretor") == "500027665" and campos.get("c_pc") == "K659709550002_4420")

janela = hdi.janela_de_vencimento(dias_atras=365, horas_minimas=48)
check("a janela de busca ja aplica a carencia no FIM do periodo",
      datetime.strptime(janela["data_fim"], "%d/%m/%Y").date()
      < (AGORA - timedelta(hours=24)).date())

caminho = hdi.build_boleto_storage_path(
    company_id="c1", job_id="j1", portal_key="hdi_corretor", recibo="8119003755-3")
check("path do boleto nao carrega nome nem CPF do segurado",
      caminho == "c1/hdi_corretor/j1/boleto-8119003755-3.pdf", caminho)


# ------------------------------------------------- a trava do que ESCREVE
print("\n[6] O robo nunca aperta um botao que mexe no contrato do segurado")

fonte_hdi = (ROOT / "portal_worker" / "journeys" / "hdi_corretor.py").read_text(encoding="utf-8")

# O teste que estava aqui procurava a palavra "click" perto do nome do botao no
# CODIGO -- heuristica sobre texto-fonte, que da falso positivo a cada comentario
# novo. Trocado por prova de COMPORTAMENTO contra o HTML real: as quatro acoes
# perigosas moram na MESMA linha do boleto, e o extrator tem de recusar as
# quatro e aceitar so o boleto.
ACOES_NO_HTML = (
    ("reprogParcela", "<td onclick=\"reprogParcela('01.008.119.003755.000000','false')\">x</td>"),
    ("termoAdimplencia", "<td onclick=\"termoAdimplencia('01.008.119.003755.000000')\">x</td>"),
    ("checkAntecipa", "<td onclick=\"checkAntecipa('01.008.119.003755.000000','false')\">x</td>"),
    ("checkAlterar", "<td onclick=\"checkAlterar('01.008.119.003755.000000','R','false')\">x</td>"),
)
for nome, celula in ACOES_NO_HTML:
    check("nunca confunde %s com o boleto" % nome,
          hdi._link_segunda_via("<tr>" + celula + "</tr>") == "")

check("a lista de acoes proibidas existe e esta cheia", len(hdi.ACOES_PROIBIDAS) == 4)
check("aceita o alvo certo (window.open do dsp_boleto)",
      hdi._link_segunda_via(
          "<tr><td onclick=\"window.open('dsp_boleto.htm?p=abc','boleto')\">2a via</td></tr>"
      ).endswith("dsp_boleto.htm?p=abc"))
check("o guarda CONSEGUE falhar: aceita um, recusa outro",
      hdi._link_segunda_via("<tr><td onclick=\"window.open('dsp_boleto.htm?p=1')\">x</td></tr>")
      != hdi._link_segunda_via("<tr><td onclick=\"reprogParcela('1')\">x</td></tr>"))
check("na linha REAL, com as 4 acoes juntas, so o boleto e extraido",
      "dsp_boleto" in (hdi.extrair_parcelas(RESULTADO_P)[1].get("link_segunda_via") or "")
      and not any(a in (hdi.extrair_parcelas(RESULTADO_P)[1].get("link_segunda_via") or "")
                  for a in ("reprog", "termo", "antecipa", "alterar")))


# --------------------------------------------------------------- segredo
print("\n[7] Nada de segredo em evidencia")

check("a journey guarda so os NOMES das chaves de sessao, nunca o valor",
      "sorted(credenciais_de_sessao(" in fonte_hdi)
check("a URL e mascarada antes de virar evidencia",
      "chaveUsuario|tokenSec)=[^&]+" in fonte_hdi)
check("tokenSec nao e escrito em evidencia",
      '"tokenSec": campos' not in fonte_hdi.replace('"tokenSec": campos.get("tokenSec") or ""', ""))

# ------------------------------------------- debito automatico sem boleto
print("\n[8] Debito automatico: avisa o segurado E abre tarefa para a equipe")

DEBITO = {
    "portal": "hdi_corretor", "recibo": "D1", "vencimento": _dias_atras(30),
    "whatsapp": "5547999990009", "cliente_nome": "CLIENTE TESTE",
    "parcela": "3/4", "apolice_susep": "01008425005607000000",
    "sem_boleto_motivo": ("pagamento em debito automatico - a HDI nao emite "
                          "2a via de boleto para esta parcela"),
}
COM_BOLETO = {
    "portal": "hdi_corretor", "recibo": "B1", "vencimento": _dias_atras(30),
    "whatsapp": "5547999990010", "cliente_nome": "OUTRO CLIENTE",
    "parcela": "5/10", "apolice_susep": "01008777001111000000", "sem_boleto_motivo": "",
}
FALHA_DOWNLOAD = {
    "portal": "hdi_corretor", "recibo": "F1", "vencimento": _dias_atras(30),
    "whatsapp": "5547999990011", "cliente_nome": "TERCEIRO",
    "sem_boleto_motivo": "linha sem link de 2a via",
}

# CLAUDE.md 9.3 -- estes checks diziam que o robo MANDAVA mensagem ao segurado
# em debito automatico, prometendo contato da atendente. Era verdade ate
# 12/08/2026, quando o founder decidiu o contrario: sem boleto, o robo se cala e
# quem fala e a pessoa. A licao migra -- continuamos provando que o caso e
# tratado, agora provando que ele NAO vira mensagem.

check("reconhece 'a seguradora nao emite boleto' pelo motivo escrito",
      bc.sem_boleto_por_regra(DEBITO) is True)
check("NAO confunde com falha de download (o guarda consegue falhar)",
      bc.sem_boleto_por_regra(FALHA_DOWNLOAD) is False)
check("parcela normal tem boleto", bc.sem_boleto_por_regra(COM_BOLETO) is False)

cfg_msg = bc.normalize_billing_config({"kind": bc.BILLING_KIND})
fila_d, retidos_d = bc.fila_de_cobranca([DEBITO, COM_BOLETO])
recibos_fila = [i["recibo"] for i in fila_d]

check("sem boleto NAO entra na fila de envio -- o robo nao fala com esse segurado",
      "D1" not in recibos_fila, recibos_fila)
check("quem TEM boleto continua entrando", "B1" in recibos_fila, recibos_fila)
check("o guarda CONSEGUE falhar (um entra, o outro nao)",
      len(fila_d) == 1 and len(retidos_d) == 1)
check("o retido explica que a equipe assume",
      "tarefa para a equipe" in (retidos_d[0].get("retido_por") or ""),
      retidos_d[0].get("retido_por"))
check("o retido deixa explicito que o segurado NAO recebe mensagem do sistema",
      "NAO recebe mensagem" in (retidos_d[0].get("retido_por") or ""))

check("nao existe mais template de mensagem para debito",
      not hasattr(bc, "MENSAGEM_DEBITO_SEM_BOLETO"))
check("a mensagem normal continua intacta (a decisao nao estragou o envio bom)",
      "Segue o boleto" in bc.build_customer_message(COM_BOLETO, cfg_msg["message_template"], cfg_msg))

tarefas = bc.tarefas_para_a_equipe([DEBITO, COM_BOLETO, FALHA_DOWNLOAD])
check("abre UMA tarefa, so para o caso da regra da seguradora", len(tarefas) == 1, tarefas)
check("a tarefa diz o que a atendente tem que fazer",
      "Converter para boleto no portal" in tarefas[0]["acao"], tarefas[0]["acao"])
# A tarefa antes carregava so apolice e parcela, e a atendente tinha de abrir o
# sistema de gestao para descobrir o telefone. Agora ela leva TUDO que decide.
for campo in ("cliente_nome", "whatsapp", "nome_seguradora", "item_segurado",
              "apolice_susep", "parcela", "vencimento", "valor", "motivo", "acao"):
    check("a tarefa carrega `%s` (a atendente nao vai atras)" % campo,
          campo in tarefas[0], sorted(tarefas[0]))

teste_debito = bc._format_test_message(DEBITO, cfg_msg, None, "")
check("a rede de seguranca da simulacao diz que o segurado NAO deveria receber",
      "nao deveria receber mensagem" in _norm_ascii(teste_debito), teste_debito[-140:])
check("a simulacao de falha de download continua dizendo que nao baixou",
      "nao baixado" in _norm_ascii(bc._format_test_message(FALHA_DOWNLOAD, cfg_msg, None, "")))

# ------------------------------ o HTML REAL da HDI (fixture anonimizada)
print("\n[10] A tela Parcela da HDI, como ela e de verdade")

# --- a armadilha 1: a busca e assincrona
check("reconhece a sala de espera do portal", hdi.esta_processando(AGUARDE) is True)
check("reconhece o resultado de verdade", hdi.esta_processando(RESULTADO) is False)
check("o guarda CONSEGUE falhar (distingue as duas telas)",
      hdi.esta_processando(AGUARDE) != hdi.esta_processando(RESULTADO))
reenvio = hdi.formulario_de_reenvio(AGUARDE)
check("colhe o formulario de reenvio da sala de espera", len(reenvio) >= 10, len(reenvio))
check("o reenvio carrega o numero da requisicao",
      reenvio.get("m_num_requisicao") == "1331319740")
check("PARAR na sala de espera le ZERO linhas (o defeito que isto seguraria)",
      len(hdi.extrair_parcelas(AGUARDE)) == 0)

# --- a armadilha 2: uma tabela por documento, HTML malformado
parcelas_reais = hdi.extrair_parcelas(RESULTADO)
check("le as DUAS parcelas, mesmo em tabelas separadas e <tbody> sem fechar",
      len(parcelas_reais) == 2, len(parcelas_reais))
por_doc = {p["documento"]: p for p in parcelas_reais}
check("ignora o cabecalho <thead>", all(p["documento"] for p in parcelas_reais))

vencer = por_doc.get("01.008.005.065191.000000") or {}
atraso = por_doc.get("01.008.119.003755.000000") or {}
check("separa 'Parcela a Vencer' de 'Parcela em Atraso'",
      vencer.get("em_atraso") is False and atraso.get("em_atraso") is True)
check("le o nome do cliente", atraso.get("cliente_nome") == "CONDOMINIO EXEMPLO RESIDENCIAL")
check("le o valor em real", atraso.get("valor") == 1006.02, atraso.get("valor"))
check("le o vencimento dd/mm/aa -> ISO", atraso.get("vencimento") == "2026-08-09")
check("le a parcela x de y como o portal escreve", atraso.get("parcela") == "02/06",
      atraso.get("parcela"))

# --- a armadilha 3: o boleto nao e um <a href>
check("acha o boleto DENTRO do onclick window.open",
      "dsp_boleto.htm?p=" in (atraso.get("link_segunda_via") or ""),
      atraso.get("link_segunda_via"))
check("o link do boleto vira URL absoluta",
      str(atraso.get("link_segunda_via") or "").startswith("https://www.hdi.com.br/web/hdidigital/"))
check("CREDITO tambem fica sem boleto (nao so debito)",
      vencer.get("forma_pagamento") == "credito" and not vencer.get("link_segunda_via"),
      vencer.get("forma_pagamento"))
check("o motivo de sem-boleto cita a regra da seguradora",
      "nao emite 2a via de boleto" in (vencer.get("sem_boleto_motivo") or ""))
check("o guarda do link CONSEGUE falhar: uma linha tem, a outra nao",
      bool(atraso.get("link_segunda_via")) != bool(vencer.get("link_segunda_via")))

# --- os quatro botoes que ESCREVEM estao na mesma linha, e nao viram boleto
check("reprogParcela NAO e confundido com o boleto",
      "reprog" not in (atraso.get("link_segunda_via") or "").lower())
check("checkAlterar (Alteracoes Financeiras) NAO e confundido com o boleto",
      "alterar" not in (atraso.get("link_segunda_via") or "").lower())

# --- a ponte e o filtro
check("a ponte entrega a identidade da sessao",
      hdi.extrair_campos_do_form(PONTE).get("m_cod_corretor") == "500027665")
check("s_tipo=3 e mesmo 'Atrasadas' (lido do <select> real)",
      'value="3">Atrasadas' in SELECT_TIPO.replace("\n", "") and hdi.S_TIPO_ATRASADAS == "3")
check("o padrao NAO e mais 1 ('A vencer', que trazia justamente quem nao interessa)",
      hdi.S_TIPO_ATRASADAS != "1")

# --- a janela de 30 dias
blocos = hdi.janelas_de_vencimento(dias_atras=90, horas_minimas=48)
check("90 dias viram varios blocos, nao um pedido unico", len(blocos) >= 3, len(blocos))
check("nenhum bloco passa dos 30 dias que o portal aceita",
      all((datetime.strptime(b["data_fim"], "%d/%m/%Y")
           - datetime.strptime(b["data_ini"], "%d/%m/%Y")).days < hdi.JANELA_MAX_DIAS
          for b in blocos), blocos)
_datas_ini = [datetime.strptime(b["data_ini"], "%d/%m/%Y") for b in blocos]
check("os blocos saem do mais ANTIGO para o mais recente",
      _datas_ini == sorted(_datas_ini), [b["data_ini"] for b in blocos])
check("os blocos nao deixam buraco entre um e o seguinte",
      all((datetime.strptime(blocos[i + 1]["data_ini"], "%d/%m/%Y")
           - datetime.strptime(blocos[i]["data_fim"], "%d/%m/%Y")).days == 1
          for i in range(len(blocos) - 1)), [(b["data_ini"], b["data_fim"]) for b in blocos])
check("o bloco mais recente ja aplica a carencia de 48h",
      datetime.strptime(blocos[-1]["data_fim"], "%d/%m/%Y").date()
      < (AGORA - timedelta(hours=24)).date())

# --- ponta a ponta do parser: da tabela ate a fila
atrasados_reais = hdi.apenas_atrasados(parcelas_reais, horas_minimas=48)
check("so a parcela em atraso entra", len(atrasados_reais) == 1, len(atrasados_reais))
check("e ela e a que TEM boleto", bool(atrasados_reais[0].get("link_segunda_via")))


# ------------------------------------ nao afirmar carteira em dia sem ler
print("\n[9] 'Nenhum inadimplente' so pode ser dito quando a tela foi LIDA")

fonte_sweep = fonte_hdi.split("async def cobranca_sweep")[-1]
check("existe o guarda do falso 'esta tudo em dia'",
      "lista_nao_lida" in fonte_sweep)
check("o guarda compara o TAMANHO da resposta (servidor falou, parser nao leu)",
      "maior_resposta" in fonte_sweep and "hdi_buscas" in fonte_sweep)
check("a mensagem diz explicitamente que NAO afirma carteira em dia",
      "NAO afirmo que a carteira esta em dia" in fonte_sweep)
check("resposta vazia de verdade ainda pode terminar `done`",
      'status="done"' in fonte_sweep)

# ---------------------------------- as mensagens do grupo de suporte humano
print("\n[11] As mensagens que a equipe le no WhatsApp")

av = _load("billing_avisos", "app/services/billing_avisos.py")

TAREFA = {
    "cliente_nome": "CONDOMINIO EXEMPLO RESIDENCIAL",
    "whatsapp": "5547999990001",
    "nome_seguradora": "HDI SEGUROS",
    "item_segurado": "Condominio",
    "apolice_susep": "01.008.119.003755.000000",
    "parcela": "02/06",
    "vencimento": _dias_atras(3),
    "valor": 1006.02,
    "motivo": "Debito automatico recusado",
    "acao": "Converter para boleto no portal e enviar ao segurado",
}
msg = av.aviso_de_tarefas("Resulta Seguros", [TAREFA])

check("tem TITULO proprio de cobranca", msg.startswith("\U0001F534 *COBRAN"), msg[:40])
check("o titulo diz PRECISA DE VOCE", "PRECISA DE VOC" in msg)
check("traz o WhatsApp EM NEGRITO (o que a atendente toca primeiro)",
      "*(47) 99999-0001*" in msg, msg)
check("traz a seguradora", "HDI SEGUROS" in msg)
check("traz o ramo", "Condominio" in msg)
check("traz a apolice inteira", "01.008.119.003755.000000" in msg)
check("traz a parcela", "02/06" in msg)
check("diz ha quantos dias venceu (a pessoa nao conta de cabeca)",
      "(ha 3 dias)" in msg.replace("á", "a").replace("_", ""), msg)
check("traz o valor em real", "R$ 1.006,02" in msg, msg)
check("traz o motivo", "Debito automatico recusado" in msg)
check("termina com a ACAO em negrito",
      "*Converter para boleto no portal e enviar ao segurado*" in msg)
check("cada informacao em SUA linha (nao e uma linha so com barras)",
      "|" not in msg and msg.count("\n") >= 10, msg.count("\n"))
check("NAO tem a frase do robo que o founder mandou tirar",
      "o robo" not in _norm_ascii(msg) and "quem fala e voce" not in _norm_ascii(msg))
check("o rodape explica sem se justificar",
      "O contato" in msg and "seu" in msg)

sem_fone = av.aviso_de_tarefas("Resulta", [{**TAREFA, "whatsapp": ""}])
check("sem telefone, DIZ que nao tem (nao esconde a linha)",
      "sem telefone no cadastro" in sem_fone, sem_fone)
check("o guarda do telefone CONSEGUE falhar (com e sem dao textos diferentes)",
      sem_fone != msg)

com_obs = av.aviso_de_tarefas("Resulta", [{**TAREFA, "observacao": "3a tentativa de debito falhou"}])
check("observacao aparece quando existe", "3a tentativa" in com_obs)
check("e NAO aparece quando nao existe", "\U0001F4CC" not in msg)

dois = av.aviso_de_tarefas("Resulta", [TAREFA, {**TAREFA, "cliente_nome": "MARIA DA SILVA"}])
import re as _re  # noqa: E402

# Casar por "*1 " solto pegava a linha de resumo ("*2 segurados em atraso...").
# O bloco do segurado e `*N · NOME*` -- e e esse padrao que tem de estar em ordem.
_blocos = _re.findall(r"^\*(\d+) . (.+)\*$", dois, _re.MULTILINE)
check("numera os segurados, em ordem, um bloco por pessoa",
      [n for n, _ in _blocos] == ["1", "2"], _blocos)
check("cada bloco traz o nome de UM segurado diferente",
      len({nome for _, nome in _blocos}) == 2, _blocos)
check("concorda o plural com a quantidade",
      "2 segurados" in dois and "1 segurado em atraso" in msg)

prob = av.aviso_de_portal("Resulta Seguros", "HDI SEGUROS", "nao consegui ler a lista")
check("o aviso de portal tem TITULO diferente do de tarefa",
      prob.startswith("\U0001F7E0") and not prob.startswith("\U0001F534"))
check("o guarda diz que NAO afirma carteira em dia",
      "Não estou afirmando que a carteira está em dia" in prob, prob)
check("o guarda manda conferir na mao", "Conferir na mão" in prob)
check("o guarda NAO fala com segurado (nao tem telefone de cliente)",
      "99999" not in prob)

res = av.aviso_de_resumo("Resulta", seguradoras=["HDI SEGUROS", "ALLIANZ"],
                         enviados=8, pendentes=3, tarefas=2,
                         sem_telefone=[{"cliente_nome": "JOAO SOUZA", "apolice_susep": "01.008"}])
check("o resumo tem o TERCEIRO titulo", res.startswith("\U0001F535"))
check("os tres titulos sao diferentes entre si",
      len({msg[:2], prob[:2], res[:2]}) == 3)
check("o resumo diz quantos foram e quantos ficaram",
      "8 boleto" in res and "3 ficam para amanh" in res)
check("o resumo aponta para a mensagem de tarefas", "precisam de voc" in _norm_ascii(res))
check("o resumo nomeia quem ficou sem telefone", "JOAO SOUZA" in res)

vazio = av.aviso_de_resumo("Resulta", seguradoras=["HDI SEGUROS"], enviados=0,
                           pendentes=0, tarefas=0, sem_telefone=[])
check("rodada sem inadimplente diz isso, e nao fica muda",
      "Nenhum inadimplente" in vazio)
check("nenhuma tarefa nao gera mensagem vazia", av.aviso_de_tarefas("X", []) == "")

check("telefone brasileiro vira formato legivel",
      av.telefone_legivel("5547988087463") == "(47) 98808-7463",
      av.telefone_legivel("5547988087463"))
check("telefone fixo de 10 digitos tambem",
      av.telefone_legivel("4733701234") == "(47) 3370-1234")
check("numero estranho aparece como veio (melhor estranho que escondido)",
      av.telefone_legivel("123") == "123")

fonte_bc = (ROOT / "app" / "services" / "billing_collection.py").read_text(encoding="utf-8")
check("o aviso resolve o grupo por company_id (nunca grupo fixo no codigo)",
      "human_support_destinations" in fonte_bc and 'eq("company_id"' in fonte_bc)
check("sem grupo cadastrado NAO derruba a colheita",
      "return False" in fonte_bc.split("async def avisar_suporte_humano")[1][:2200])
check("o guarda do portal avisa a EQUIPE, nao o segurado",
      "aviso_de_portal" in fonte_bc)

print("\nPASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
