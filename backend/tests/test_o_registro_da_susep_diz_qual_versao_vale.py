# -*- coding: utf-8 -*-
"""O REP2 diz qual versão vale — e quando não diz, ele NÃO diz "não mudou".

Por que este arquivo existe
---------------------------
📊 Medido em 08/08/2026: 12 de 13 documentos indexados do acervo eram versões
revogadas. O condomínio da Porto era de dezembro/2012 e o vigente é de
dezembro/2025. Ninguém tinha errado de propósito — é que **não havia como
perguntar**. O `susep_rep2.py` é a peça que passa a perguntar.

E é exatamente aí que mora o defeito que este projeto já pagou caro. O portal
da SUSEP responde **HTTP 200 com a página em branco** quando o número não
existe: sem "Nenhum resultado", sem `alert`, sem nada — só o bloco "Detalhes do
Produto" que não veio. 📊 11.545 bytes contra 95.861 do caso cheio, e 📊 5 de 31
consultas de 08/08/2026 caíram nisso.

Um parser que só sabe dizer "ok" lê essa página, não acha versão nova, e conclui
**"não mudou"**. Existe um commit nesta branch chamado *"não consegui abrir não
pode se disfarçar de deve ser legado"* — é a mesma família de mentira, e desta
vez ela apagaria a única coisa que a SPEC-070 existe para descobrir.

O CONTROLE que dá direito a confiar em tudo aqui
------------------------------------------------
Todo caso deste arquivo é alimentado com **HTML real**, gravado do portal em
08/08/2026 e guardado em `fixtures/susep_rep2/`. O controle central é o par:

    tokio_auto_truncado_vazio.html   (o número truncado do nosso banco)
    tokio_auto_reparado.html         (o MESMO produto, com o dígito recuperado)

Mesma seguradora, mesmo produto, mesmo portal, mesmo dia. Um devolve
`indeterminado`, o outro devolve `vigente_encontrada`. Sem esse par, "o parser
disse indeterminado" seria indistinguível de "o parser diz indeterminado para
tudo" — e um guarda que não tem como falhar não guarda nada (CLAUDE.md §9.2).

📊 As medições deste dia, contra o portal ao vivo
--------------------------------------------------
    31 processos de `normative_documents` consultados
    25  vigente_encontrada
     1  produto_morto        (Azul residencial, "Cancelado pela empresa")
     5  indeterminado        (as 5 circulares/resoluções do regulador, que
                              📊 não são produto registrado no REP2)
    ---
    13  atrasado    ·   1 em_dia   ·   16 indeterminado por falta de data nossa

📊 **1 de 31 documentos está na versão vigente.** O `em_dia` é a residencial da
Porto, e ele só existe porque `effective_from` dela está preenchido: 📊 16 dos
31 vereditos são `indeterminado` porque a coluna é NULL no nosso banco. "Não sei
o que tenho" não é "está em dia" — é o LOTE 0 item 6 esperando.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
FIXTURES = os.path.join(AQUI, "fixtures", "susep_rep2")


def _carregar_servico(caminho_relativo: str, nome: str):
    """Carrega o módulo por caminho, como o resto da casa faz.

    `app.services.__init__` puxa `openai` e `app.core.__init__` puxa
    `pydantic-settings` — nenhum dos dois é necessário para o parser, e exigi-los
    aqui tornaria caro rodar justamente o controle que precisa ser barato.

    ⚠️ O registro em `sys.modules` vem ANTES do `exec_module`: sem ele o
    `@dataclass` do módulo explode procurando o próprio namespace.
    """
    caminho = os.path.join(RAIZ, caminho_relativo)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


S = _carregar_servico(os.path.join("app", "services", "knowledge", "susep_rep2.py"),
                      "susep_rep2")

FALHAS: list = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def html(nome: str) -> str:
    with open(os.path.join(FIXTURES, nome), encoding="utf-8") as fh:
        return fh.read()


# As cinco respostas reais, gravadas em 08/08/2026.
PORTO_AUTO = "porto_auto_vigente.html"                 # 95.861 bytes, 100 versões
TOKIO_VAZIO = "tokio_auto_truncado_vazio.html"         # 11.545 bytes, página em branco
TOKIO_REPARADO = "tokio_auto_reparado.html"            # 57.231 bytes, 50 versões
AZUL_CANCELADO = "azul_residencial_cancelado.html"     # produto morto
CIRCULAR_VAZIO = "circular_710_2024_vazio.html"        # circular não é produto REP2


# 📊 Os tamanhos medidos no dia da captura. Servem de guarda contra a fixture
# que chega truncada ou vazia num clone — 🔴 e ela quase chegou: o `.gitignore`
# deste repositório tem `*.html` na regra de "lixo de teste de rede", e sem a
# exceção `!backend/tests/fixtures/**/*.html` estes arquivos passariam a existir
# só na máquina de quem os baixou. Verde aqui, explosão no clone limpo.
TAMANHOS = {
    PORTO_AUTO: 95_861,
    TOKIO_VAZIO: 11_545,
    TOKIO_REPARADO: 57_231,
    AZUL_CANCELADO: 18_143,
    CIRCULAR_VAZIO: 11_548,
}


# ── 0. as fixtures são as respostas reais, inteiras ───────────────────────────

def teste_as_fixtures_sao_as_respostas_reais_e_inteiras():
    print("\n[0] O HTML do portal, do jeito que ele veio em 08/08/2026")
    for nome, tamanho in TAMANHOS.items():
        caminho = os.path.join(FIXTURES, nome)
        real = os.path.getsize(caminho) if os.path.exists(caminho) else -1
        checar(real == tamanho, f"{nome}: 📊 {tamanho} bytes", f"tem {real}")

    # CONTROLE: a página vazia e a cheia do MESMO produto têm tamanhos bem
    # diferentes — é essa diferença que o parser existe para não ignorar.
    checar(TAMANHOS[TOKIO_REPARADO] > 4 * TAMANHOS[TOKIO_VAZIO],
           "CONTROLE: 📊 a cheia da Tokio tem ~5× a vazia (57.231 × 11.545)")


# ── 1. o controle central: os três estados conseguem ser diferentes ───────────

def teste_a_pagina_vazia_real_nao_pode_dizer_que_nao_mudou():
    print("\n[1] 200 com página em branco é `indeterminado` — nunca `em_dia`")

    # A nossa Tokio Auto está em 07/06/2025 no banco. Se o parser tratasse
    # "não achei versão" como "não mudou", este seria o documento que ficaria
    # 📊 dez meses parado achando que estava em dia.
    vazio = S.interpretar_consulta(html(TOKIO_VAZIO), "15414.100335/2004",
                                   http_status=200)
    checar(vazio.estado == S.INDETERMINADO,
           "a resposta vazia REAL da Tokio vira `indeterminado`", vazio.estado)
    checar(vazio.motivo == "pagina_sem_detalhes_do_produto",
           "e o motivo diz o que faltou na página", str(vazio.motivo))
    checar(vazio.http_status == 200,
           "mesmo com HTTP 200 — o status não foi a evidência", str(vazio.http_status))

    veredito = vazio.comparar_com("2025-06-07")
    checar(veredito == S.INDETERMINADO,
           "e o veredito contra a nossa data é `indeterminado`", veredito)
    checar(veredito != S.EM_DIA,
           "🔴 NÃO é `em_dia` — 'não consegui perguntar' não é 'não mudou'",
           veredito)

    # CONTROLE — a linha que dá direito à conclusão. O MESMO produto da Tokio,
    # com o dígito verificador recuperado, no mesmo dia, pelo mesmo parser.
    # Se este passar a devolver `indeterminado`, o parser virou um carimbo e o
    # teste acima deixou de significar qualquer coisa.
    reparado = S.interpretar_consulta(html(TOKIO_REPARADO), "15414.100335/2004-74",
                                      http_status=200)
    checar(reparado.estado == S.VIGENTE_ENCONTRADA,
           "CONTROLE: o MESMO produto, com o dígito certo, acha a vigente",
           f"{reparado.estado} · {reparado.motivo}")
    checar(reparado.comparar_com("2025-06-07") == S.ATRASADO,
           "CONTROLE 2: e o veredito dele é `atrasado`, não `indeterminado`",
           reparado.comparar_com("2025-06-07"))
    checar(reparado.vigente is not None and reparado.vigente.inicio == "14/04/2026",
           "📊 a vigente da Tokio Auto começa em 14/04/2026",
           str(reparado.vigente.inicio if reparado.vigente else None))

    # CONTROLE 3: as 5 circulares do regulador. 📊 Elas dão a MESMA página vazia
    # — e isso é informação, não erro: circular não é produto registrado no
    # REP2 (SPEC-070 §3.3), e vem por URL direta.
    circular = S.interpretar_consulta(html(CIRCULAR_VAZIO), "15414.621724/2024-82",
                                      http_status=200)
    checar(circular.estado == S.INDETERMINADO,
           "CONTROLE 3: a circular do regulador também é `indeterminado`",
           circular.estado)


def teste_produto_morto_e_um_terceiro_estado_e_nao_um_dos_outros_dois():
    print("\n[2] Cancelado não é 'em dia' nem 'não sei' — é morto, e tem nome")
    morto = S.interpretar_consulta(html(AZUL_CANCELADO), "15414.000743/2005-16",
                                   http_status=200)
    checar(morto.estado == S.PRODUTO_MORTO,
           "a Azul Residencial é `produto_morto`", morto.estado)
    checar((morto.situacao or "").lower().startswith("cancelado"),
           "📊 e a situação lida do portal é 'Cancelado pela empresa'",
           str(morto.situacao))
    checar(morto.comparar_com("2013-12-01") == S.PRODUTO_MORTO,
           "o veredito não vira `atrasado` nem `em_dia`",
           morto.comparar_com("2013-12-01"))
    checar(morto.produto_vivo is False, "e `produto_vivo` é falso")

    # CONTROLE: os três estados são de fato TRÊS. Um parser que devolvesse
    # sempre o mesmo valor passaria em cada asserção isolada acima.
    vistos = {
        S.interpretar_consulta(html(PORTO_AUTO), "p").estado,
        S.interpretar_consulta(html(TOKIO_VAZIO), "t").estado,
        morto.estado,
    }
    checar(vistos == set(S.ESTADOS),
           "CONTROLE: as três páginas reais caem nos três estados distintos",
           str(sorted(vistos)))


def teste_sem_a_nossa_data_o_veredito_e_indeterminado():
    print("\n[3] 'Não sei o que tenho' também não é 'está em dia'")
    porto = S.interpretar_consulta(html(PORTO_AUTO), "15414.100233/2004-59")
    checar(porto.estado == S.VIGENTE_ENCONTRADA, "a consulta foi bem-sucedida")

    # 📊 `effective_from` é NULL em 16 dos 31 documentos. Achar a vigente e não
    # saber a nossa não autoriza nenhuma das duas conclusões.
    checar(porto.comparar_com(None) == S.INDETERMINADO,
           "sem data nossa, o veredito é `indeterminado`", porto.comparar_com(None))
    checar(porto.comparar_com("") == S.INDETERMINADO,
           "string vazia idem", porto.comparar_com(""))

    # CONTROLE: com data nossa, o MESMO objeto conclui — nas duas direções.
    checar(porto.comparar_com("2026-01-01") == S.ATRASADO,
           "CONTROLE: 📊 temos o CG140 de 01/01/2026 e a vigente é de 01/07/2026",
           porto.comparar_com("2026-01-01"))
    checar(porto.comparar_com("2026-07-01") == S.EM_DIA,
           "CONTROLE 2: com a data da própria vigente, é `em_dia`",
           porto.comparar_com("2026-07-01"))
    checar(porto.comparar_com("2026-12-31") == S.EM_DIA,
           "CONTROLE 3: data posterior também não é 'atrasado'",
           porto.comparar_com("2026-12-31"))


# ── 2. a regra da vigência ────────────────────────────────────────────────────

def teste_a_vigente_e_a_de_data_de_fim_vazia_e_nao_a_de_negrito():
    print("\n[4] A regra é a Data de Fim vazia; o negrito é só testemunha")
    porto = S.interpretar_consulta(html(PORTO_AUTO), "15414.100233/2004-59")

    checar(len(porto.versoes) == 100,
           "📊 o produto auto da Porto tem 100 versões registradas",
           str(len(porto.versoes)))
    checar(porto.vigente.arquivo == "3402 - Porto Seguro CG144_Susep.pdf",
           "📊 a vigente é o CG144 — 4 revisões à frente do CG140 que temos",
           porto.vigente.arquivo)
    checar(porto.vigente.inicio == "01/07/2026" and not porto.vigente.fim,
           "com início 01/07/2026 e Data de Fim vazia",
           f"{porto.vigente.inicio} / {porto.vigente.fim!r}")
    checar(porto.vigente.download_id == "508497",
           "e o id de download veio do onclick", str(porto.vigente.download_id))
    checar(porto.divergencia_negrito is False,
           "📊 negrito e data-de-fim concordam nas 26 páginas medidas hoje")

    checar(sum(1 for v in porto.versoes if v.vigente) == 1,
           "só UMA das 100 versões tem Data de Fim vazia",
           str(sum(1 for v in porto.versoes if v.vigente)))

    # CONTROLE: prove que a regra é a DATA e não o negrito, forçando os dois a
    # discordarem. Sem esta linha, um parser que escolhesse pelo `font-weight`
    # passaria em tudo acima — e quebraria calado no dia em que o portal mudar
    # a folha de estilo.
    trocado = html(PORTO_AUTO).replace(
        '<td style="font-weight:bold;">01/07/2026</td>',
        '<td style="">01/07/2026</td>')
    checar(trocado != html(PORTO_AUTO), "a mutação do controle foi aplicada")
    sem_negrito = S.interpretar_consulta(trocado, "15414.100233/2004-59")
    checar(sem_negrito.vigente is not None
           and sem_negrito.vigente.arquivo == porto.vigente.arquivo,
           "CONTROLE: tirando o negrito da linha vigente, a escolha não muda",
           str(sem_negrito.vigente.arquivo if sem_negrito.vigente else None))


def teste_produto_vivo_sem_versao_em_aberto_nao_vira_em_dia():
    print("\n[5] A combinação que a regra não prevê também é `indeterminado`")
    # Fecha a única versão em aberto do Porto. Produto continua "Passível de
    # comercialização" e nenhuma versão está valendo — é impossível pela regra
    # do portal, e é justamente por isso que chutar aqui seria o começo do erro.
    fechado = html(PORTO_AUTO).replace(
        '<td style="font-weight:bold;">01/07/2026</td>\n'
        '                                                    <td style="font-weight:bold;"></td>',
        '<td style="font-weight:bold;">01/07/2026</td>\n'
        '                                                    <td style="font-weight:bold;">31/07/2026</td>')
    r = S.interpretar_consulta(fechado, "15414.100233/2004-59")
    checar(r.estado == S.INDETERMINADO,
           "sem nenhuma versão em aberto, `indeterminado`", f"{r.estado} · {r.motivo}")
    checar(r.motivo == "produto_vivo_sem_versao_em_aberto",
           "e o motivo nomeia a combinação", str(r.motivo))
    checar(r.comparar_com("2026-01-01") == S.INDETERMINADO,
           "o veredito não é `em_dia`", r.comparar_com("2026-01-01"))
    # CONTROLE: a mutação precisa ter mudado alguma coisa de verdade.
    checar(fechado != html(PORTO_AUTO), "CONTROLE: a página foi mesmo alterada")


def teste_o_nome_do_arquivo_nao_carrega_a_palavra_download():
    print("\n[6] O nome do arquivo é a chave da versão — e ele vinha sujo")
    # ⚠️ A âncora traz `<span class="invisivel">Download</span>` para leitor de
    # tela. Sem tirá-la, TODA versão sai como "… CG144_Susep.pdf Download" e a
    # comparação com o que já está em `normative_document_versions` nunca casa.
    porto = S.interpretar_consulta(html(PORTO_AUTO), "15414.100233/2004-59")
    sujos = [v.arquivo for v in porto.versoes if "Download" in v.arquivo]
    checar(not sujos, "nenhum dos 100 nomes carrega 'Download'", str(sujos[:2]))
    checar(all(v.arquivo.lower().endswith(".pdf") for v in porto.versoes),
           "e todos terminam em .pdf",
           str([v.arquivo for v in porto.versoes if not v.arquivo.lower().endswith(".pdf")][:2]))
    # CONTROLE: os nomes existem mesmo. "Nenhum tem Download" seria trivialmente
    # verdadeiro se todos estivessem vazios.
    checar(len({v.arquivo for v in porto.versoes}) >= 90,
           "CONTROLE: e são nomes distintos de verdade",
           str(len({v.arquivo for v in porto.versoes})))


def teste_o_ramo_vem_numerado_do_regulador():
    print("\n[7] O ramo é o da SUSEP, não uma lista nossa (SPEC-070 §5.2)")
    porto = S.interpretar_consulta(html(PORTO_AUTO), "15414.100233/2004-59")
    checar(porto.ramo_codigo == "05", "📊 código oficial `05`", str(porto.ramo_codigo))
    checar(porto.ramo_nome == "AUTOMÓVEL - CASCO",
           "📊 nome oficial `AUTOMÓVEL - CASCO`", str(porto.ramo_nome))
    checar(porto.sociedade == "PORTO SEGURO COMPANHIA DE SEGUROS GERAIS",
           "e a sociedade sai inteira", str(porto.sociedade))

    # CONTROLE: o rótulo do portal vem prefixado com lixo (`DDD Sociedade:`,
    # `CCC Número do Processo:`). Se a leitura fosse por igualdade em vez de
    # sufixo, os campos acima viriam None.
    checar("DDD Sociedade" in html(PORTO_AUTO),
           "CONTROLE: o rótulo REAL é mesmo `DDD Sociedade:` no HTML do portal")

    # CONTROLE 2: outro produto, outro ramo. Um extrator que devolvesse
    # constante passaria nas três asserções de cima.
    empresarial = S.interpretar_consulta(html(AZUL_CANCELADO), "x")
    checar(empresarial.ramo_codigo not in (None, "05"),
           "CONTROLE 2: outra página devolve outro ramo",
           f"{empresarial.ramo_codigo} | {empresarial.ramo_nome}")


def teste_a_consulta_vazia_nao_entrega_datas_para_gravar():
    print("\n[7b] A armadilha 1 na camada de escrita: `None`, não dicionário vazio")
    porto = S.interpretar_consulta(html(PORTO_AUTO), "15414.100233/2004-59")
    vig = porto.vigencia_para_o_acervo()
    checar(vig is not None and vig["effective_from"] == "2026-07-01",
           "📊 a vigente da Porto Auto começa em 2026-07-01",
           str(vig and vig["effective_from"]))
    checar(vig["effective_until"] is None,
           "e não tem fim — é o que a torna vigente", str(vig["effective_until"]))
    checar(vig["version_label"] == "3402 - Porto Seguro CG144_Susep.pdf",
           "o rótulo da versão é o nome do arquivo no portal", str(vig["version_label"]))
    checar(vig["susep_version_id"] == "508497",
           "e o id serve para baixar o PDF depois", str(vig["susep_version_id"]))
    checar(vig["fim_da_anterior"] == "2026-06-30",
           "📊 a anterior (CG143) foi fechada em 30/06/2026 pelo regulador — "
           "é essa data que fecha a nossa linha, não 'hoje'",
           str(vig["fim_da_anterior"]))

    # CONTROLE — o que a escrita NÃO pode receber. Um dicionário de `None`s
    # seria gravado por cima da vigência boa e a apagaria, com a página vazia
    # como única "evidência".
    for pagina, proc in ((TOKIO_VAZIO, "15414.100335/2004"),
                         (AZUL_CANCELADO, "15414.000743/2005-16")):
        r = S.interpretar_consulta(html(pagina), proc)
        checar(r.vigencia_para_o_acervo() is None,
               f"CONTROLE: `{r.estado}` não entrega dicionário nenhum",
               str(r.vigencia_para_o_acervo()))


# ── 3. os processos malformados ───────────────────────────────────────────────

def teste_o_ponto_a_mais_da_porto_se_conserta_e_o_truncado_da_tokio_nao():
    print("\n[8] 📊 3 de 31 processos não casam com o formato — dois problemas")

    porto = S.analisar_processo("15414.100.233/2004-59")
    checar(porto.ok and porto.formatado == "15414.100233/2004-59",
           "porto/auto: ponto a mais, 17 dígitos → normaliza", str(porto.formatado))

    for gravado in ("15414.100335/2004", "15414.900584/2018"):
        p = S.analisar_processo(gravado)
        checar(p.precisa_reparo, f"tokio {gravado}: não normaliza sozinho",
               str(p.formatado))
        checar(p.motivo == "faltam_2_digitos",
               "e o motivo diz que falta o dígito verificador", str(p.motivo))
        # 🔴 O que NUNCA pode acontecer: inventar os dígitos. Um verificador
        # chutado casa com um processo válido de OUTRO produto, o portal
        # responde 200 com página cheia, e o acervo passa a acompanhar o
        # contrato errado — em silêncio, que é o pior lugar para errar.
        checar(p.formatado is None, "e nenhum dígito é inventado", str(p.formatado))

    # CONTROLE: um processo já canônico atravessa sem ser mexido. Sem esta
    # linha, uma função que devolvesse None para tudo passaria acima.
    ok = S.analisar_processo("15414.002216/2004-57")
    checar(ok.ok and ok.formatado == "15414.002216/2004-57",
           "CONTROLE: processo bem formado sai idêntico", str(ok.formatado))
    checar(S.normalizar_processo("  15414.002216/2004-57  ") == "15414.002216/2004-57",
           "CONTROLE 2: e espaço em volta não atrapalha")
    checar(S.normalizar_processo("") is None and S.normalizar_processo(None) is None,
           "CONTROLE 3: vazio e None não viram processo")
    checar(S.analisar_processo("154140022162004571").motivo == "sobram_1_digitos",
           "CONTROLE 4: dígito a mais também é recusado, com nome",
           S.analisar_processo("154140022162004571").motivo)


def _catalogo_falso(linhas):
    return [dict(zip(S.COLUNAS_CATALOGO, l)) for l in linhas]


TOKIO_AUTO_REAL = ("PLANO DE SEGURO DE DANOS", "TOKIO MARINE SEGURADORA S.A.",
                   "33164021000100", "15414.100335/2004-74", "05 | AUTOMÓVEL - CASCO",
                   "VALOR DETERMINADO E VALOR DE MERCADO REFERENCIADO")
TOKIO_EMPRESARIAL_REAL = ("PLANO DE SEGURO DE DANOS", "TOKIO MARINE SEGURADORA S.A.",
                          "33164021000100", "15414.900584/2018-68",
                          "01 | COMPREENSIVO EMPRESARIAL", "NÃO APLICÁVEL")
RUIDO = ("PLANO DE SEGURO DE DANOS", "PORTO SEGURO COMPANHIA DE SEGUROS GERAIS",
         "61198164000160", "15414.100233/2004-59", "05 | AUTOMÓVEL - CASCO",
         "VALOR DETERMINADO E VALOR DE MERCADO REFERENCIADO")


def teste_o_processo_truncado_e_achavel_pelo_catalogo():
    print("\n[9] O que não normaliza vira reparo com nome — não some")
    catalogo = _catalogo_falso([RUIDO, TOKIO_AUTO_REAL, TOKIO_EMPRESARIAL_REAL])

    esperado = {"15414.100335/2004": "15414.100335/2004-74",
                "15414.900584/2018": "15414.900584/2018-68"}
    checar(len(S.PENDENCIAS_DE_REPARO) == 2,
           "📊 a lista explícita tem os 2 casos do banco",
           str(len(S.PENDENCIAS_DE_REPARO)))

    for pend in S.PENDENCIAS_DE_REPARO:
        r = S.reparar_pelo_catalogo(pend, catalogo)
        checar(r.resolvido and r.processo == esperado[pend.gravado],
               f"{pend.gravado} → {esperado[pend.gravado]}",
               f"{len(r.candidatos)} candidato(s): {r.processo}")

    # CONTROLE 1: o mesmo prefixo com OUTRA companhia não é reparo. Se o nome
    # não entrasse na conta, o parser aceitaria o produto de qualquer um.
    impostor = dict(zip(S.COLUNAS_CATALOGO, TOKIO_AUTO_REAL))
    impostor["entnome"] = "SEGURADORA QUALQUER S.A."
    r = S.reparar_pelo_catalogo(S.PENDENCIAS_DE_REPARO[0], [impostor])
    checar(not r.resolvido and not r.candidatos,
           "CONTROLE: mesmo prefixo, outra companhia → não é reparo",
           str(r.processo))

    # CONTROLE 2: dois candidatos é ambiguidade, e ambiguidade NÃO resolve.
    gemeo = dict(zip(S.COLUNAS_CATALOGO, TOKIO_AUTO_REAL))
    gemeo["numeroprocesso"] = "15414.100335/2004-99"
    ambiguo = S.reparar_pelo_catalogo(S.PENDENCIAS_DE_REPARO[0],
                                      catalogo + [gemeo])
    checar(len(ambiguo.candidatos) == 2 and not ambiguo.resolvido,
           "CONTROLE 2: dois candidatos → segue pendente, sem escolher",
           str([c["numeroprocesso"] for c in ambiguo.candidatos]))
    checar(ambiguo.processo is None,
           "e nenhum número é devolvido no escuro", str(ambiguo.processo))

    # CONTROLE 3: sem catálogo não há reparo, e o motivo é dito.
    alvo, origem = S.processo_para_consultar({"susep_process": "15414.100335/2004"})
    checar(alvo is None and origem == "malformado:faltam_2_digitos",
           "CONTROLE 3: sem catálogo, falha com nome", f"{alvo} · {origem}")

    # CONTROLE 4: com catálogo, o MESMO documento resolve — e diz de onde veio.
    alvo, origem = S.processo_para_consultar({"susep_process": "15414.100335/2004"},
                                             catalogo)
    checar(alvo == "15414.100335/2004-74" and origem == "reparado_pelo_catalogo",
           "CONTROLE 4: com catálogo, resolve e a origem fica registrada",
           f"{alvo} · {origem}")

    # CONTROLE 5: o caminho normal continua marcado como normalizado — a
    # origem tem de distinguir os dois, senão ela não informa nada.
    alvo, origem = S.processo_para_consultar({"susep_process": "15414.100.233/2004-59"},
                                             catalogo)
    checar(alvo == "15414.100233/2004-59" and origem == "normalizado",
           "CONTROLE 5: o da Porto sai como `normalizado`", f"{alvo} · {origem}")


# ── 4. o catálogo ─────────────────────────────────────────────────────────────

def _csv_falso(n: int) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(S.COLUNAS_CATALOGO)
    for i in range(n):
        escritor.writerow(["PLANO DE SEGURO DE DANOS", "SEGURADORA TESTE S.A.",
                           "00000000000000", f"15414.{i:06d}/2020-00",
                           "05 | AUTOMÓVEL - CASCO", "NÃO APLICÁVEL"])
    return saida.getvalue()


def teste_o_catalogo_e_validado_pela_contagem_e_nao_pelo_status():
    print("\n[10] 📊 200 com 12 linhas é falha silenciosa — piso de 30.000")
    curto = S.analisar_catalogo_csv(_csv_falso(12))
    checar(len(curto) == 12, "o CSV curto é lido normalmente", str(len(curto)))
    try:
        S.conferir_contagem(curto)
        checar(False, "12 registros precisavam ser recusados", "passou")
    except S.CatalogoSuspeito as exc:
        checar("12" in str(exc) and str(S.PISO_REGISTROS) in str(exc),
               "12 registros levantam `CatalogoSuspeito`, dizendo o piso", str(exc))

    # CONTROLE: no piso, o MESMO caminho aceita. Um guarda que recusasse tudo
    # passaria na asserção de cima e derrubaria todos os lotes.
    cheio = S.analisar_catalogo_csv(_csv_falso(S.PISO_REGISTROS))
    checar(S.conferir_contagem(cheio) == S.PISO_REGISTROS,
           "CONTROLE: exatamente no piso, aceita e devolve a contagem",
           str(len(cheio)))
    checar(S.PISO_REGISTROS == 30_000,
           "📊 o piso é 30.000, contra os 31.871 medidos em 08/08/2026",
           str(S.PISO_REGISTROS))

    # CONTROLE 2: coluna faltando é recusa de outro tipo, com outro nome.
    quebrado = _csv_falso(3).replace("numeroprocesso", "processo")
    try:
        S.analisar_catalogo_csv(quebrado)
        checar(False, "colunas erradas precisavam ser recusadas", "passou")
    except S.CatalogoSuspeito as exc:
        checar("numeroprocesso" in str(exc),
               "CONTROLE 2: coluna ausente também é `CatalogoSuspeito`", str(exc))


def teste_o_ultimo_dump_bom_se_apresenta_como_cache():
    print("\n[11] Armadilha 3 — cache que se disfarça de resposta de hoje é mentira")
    import tempfile
    pasta = tempfile.mkdtemp(prefix="susep_cache_")
    antigo = os.environ.get("SUSEP_CACHE_DIR")
    os.environ["SUSEP_CACHE_DIR"] = pasta
    try:
        checar(S._ler_cache() is None, "sem arquivo guardado, não há cache")

        S._guardar_cache(_csv_falso(S.PISO_REGISTROS).encode("utf-8"))
        lido = S._ler_cache()
        checar(lido is not None and lido.origem == "cache",
               "o dump guardado volta marcado como `cache`",
               str(lido.origem if lido else None))
        checar(lido is not None and lido.baixado_em,
               "com a data de quando foi baixado", str(lido.baixado_em if lido else None))
        checar(len(lido) == S.PISO_REGISTROS, "e inteiro", str(len(lido)))

        # CONTROLE: um cache truncado NÃO volta. Cache curto é pior que cache
        # nenhum: ele já vem carimbado de "último dump bom".
        S._guardar_cache(_csv_falso(9).encode("utf-8"))
        checar(S._ler_cache() is None,
               "CONTROLE: cache abaixo do piso não é servido", str(S._ler_cache()))
    finally:
        if antigo is None:
            os.environ.pop("SUSEP_CACHE_DIR", None)
        else:
            os.environ["SUSEP_CACHE_DIR"] = antigo


# ── 5. a lista de atraso não perde ninguém ────────────────────────────────────

class ClienteDeMentira:
    """Devolve HTML real por processo, e registra o que foi perguntado."""

    def __init__(self, mapa):
        self.mapa = mapa
        self.perguntou: list = []

    def consultar(self, processo):
        self.perguntou.append(processo)
        arquivo = self.mapa.get(processo)
        if arquivo is None:
            return S.ConsultaProduto(S.INDETERMINADO, processo=processo,
                                     motivo="rede:ConnectError")
        return S.interpretar_consulta(html(arquivo), processo, http_status=200)


def teste_quem_nao_deu_para_consultar_continua_na_lista():
    print("\n[12] O documento que falhou não some do relatório")
    catalogo = _catalogo_falso([TOKIO_AUTO_REAL, TOKIO_EMPRESARIAL_REAL])
    cliente = ClienteDeMentira({
        "15414.100233/2004-59": PORTO_AUTO,
        "15414.100335/2004-74": TOKIO_REPARADO,
    })
    docs = [
        {"insurer_key": "porto", "product_line": "auto",
         "susep_process": "15414.100.233/2004-59", "effective_from": "2026-01-01"},
        {"insurer_key": "tokio", "product_line": "auto",
         "susep_process": "15414.100335/2004", "effective_from": "2025-06-07"},
        {"insurer_key": "susep", "product_line": "geral",
         "susep_process": "15414.621724/2024-82", "effective_from": "2024-12-24"},
    ]
    linhas = S.medir_atraso(docs, cliente=cliente, catalogo=catalogo, pausa_s=0)

    checar(len(linhas) == 3, "os três documentos saem na lista", str(len(linhas)))
    por_chave = {l.insurer_key: l for l in linhas}
    checar(por_chave["porto"].veredito == S.ATRASADO,
           "📊 porto/auto: CG140 contra CG144 → atrasado",
           por_chave["porto"].veredito)
    checar(por_chave["tokio"].processo_consultado == "15414.100335/2004-74",
           "tokio foi consultada pelo número reparado",
           str(por_chave["tokio"].processo_consultado))
    checar(por_chave["tokio"].origem_do_processo == "reparado_pelo_catalogo",
           "e o relatório diz que o número foi reparado",
           str(por_chave["tokio"].origem_do_processo))
    checar(por_chave["susep"].veredito == S.INDETERMINADO,
           "🔴 a que não respondeu fica com `indeterminado` e NÃO some",
           por_chave["susep"].veredito)
    checar(por_chave["susep"].veredito != S.EM_DIA,
           "e em nenhuma hipótese vira `em_dia`", por_chave["susep"].veredito)

    checar(por_chave["porto"].download_id == "508497",
           "o id do PDF vigente vem junto — é com ele que o LOTE 1 baixa",
           str(por_chave["porto"].download_id))

    # CONTROLE: a contagem por veredito precisa ter mais de um valor. Uma
    # função que devolvesse `indeterminado` para tudo passaria na linha do
    # `susep` — e seria exatamente o defeito ao contrário.
    vereditos = {l.veredito for l in linhas}
    checar(len(vereditos) >= 2,
           "CONTROLE: os vereditos da mesma rodada são diferentes entre si",
           str(sorted(vereditos)))


# ── 6. nenhum motor paralelo, e nenhuma saída sem guard ───────────────────────

def _so_codigo(fonte: str) -> str:
    """Tira comentários e literais de texto — sobra só o que executa.

    ⚠️ Sem isto o guarda abaixo mede a **prosa**: o docstring do módulo diz, de
    propósito, que ele não fala com Qdrant nem com Supabase. Um teste que
    procurasse a palavra no arquivo inteiro reprovaria a declaração de que a
    coisa não é feita — e a maneira de "passar" seria apagar a declaração.
    """
    import io as _io
    import tokenize as _tk

    pedacos = []
    for tok in _tk.generate_tokens(_io.StringIO(fonte).readline):
        if tok.type in (_tk.COMMENT, _tk.STRING):
            continue
        pedacos.append(tok.string)
    return " ".join(pedacos)


def teste_e_adaptador_de_fonte_e_nao_um_motor_novo():
    print("\n[13] Adaptador de fonte, como o Firecrawl (CLAUDE.md §5)")
    caminho = os.path.join(RAIZ, "app", "services", "knowledge", "susep_rep2.py")
    fonte = open(caminho, encoding="utf-8").read()
    codigo = _so_codigo(fonte)

    # Toda saída HTTP passa pelo guard da SPEC-054. São três, e são três.
    checar(codigo.count("check_url") == 3,
           "as 3 saídas (consulta, download, catálogo) passam pelo egress guard",
           str(codigo.count("check_url")))
    checar("from app . core import egress_guard" in codigo,
           "e o guard é o do projeto, não uma cópia")

    import re as _re
    for proibido in ("class .*Registry", "def agendar", "scheduler", "celery",
                     "qdrant", "supabase", "def indexar", "def chunk"):
        checar(not _re.search(proibido, codigo, _re.I),
               f"não cria/toca {proibido!r} — isso é do `insurance_corpus`",
               "seria motor paralelo")

    # CONTROLE do próprio filtro: ele tem de continuar sabendo ACHAR. Um
    # `_so_codigo` que devolvesse string vazia aprovaria tudo acima.
    checar("def interpretar_consulta" in codigo and "PISO_REGISTROS" in codigo,
           "CONTROLE: o filtro de prosa ainda enxerga o código de verdade")
    checar("qdrant" in fonte.lower() and "qdrant" not in codigo.lower(),
           "CONTROLE 2: 'qdrant' está na prosa e não no código — que é o ponto")

    # CONTROLE: o `insurance_corpus.py` continua sendo o dono do que este
    # módulo NÃO faz. Ausência aqui só prova reuso se o original tiver.
    corpus = open(os.path.join(RAIZ, "app", "services", "knowledge",
                               "insurance_corpus.py"), encoding="utf-8").read()
    for exigido in ("qdrant", "supabase"):
        checar(exigido in corpus.lower(),
               f"CONTROLE: `insurance_corpus.py` continua sendo o dono de {exigido!r}")

    checar("adaptador de fonte" in fonte.lower(),
           "e o docstring declara o que ele é (CLAUDE.md §5)")


def teste_o_download_recusa_html_disfarcado_de_pdf():
    print("\n[14] Um 'PDF' que é página de erro vira documento vazio no acervo")
    # 📊 A Tokio já devolveu 200 com 1 KB de HTML no lugar do arquivo
    # (SPEC-070 §3.4). Sem a conferência do `%PDF`, isso entra no MinIO como
    # condição geral e some do radar.
    fonte = open(os.path.join(RAIZ, "app", "services", "knowledge", "susep_rep2.py"),
                 encoding="utf-8").read()
    checar('startswith(b"%PDF")' in fonte,
           "o download confere a assinatura do arquivo, não só o status")
    checar("SusepIndisponivel" in fonte,
           "e recusa com um erro que o chamador sabe tratar")

    # CONTROLE: o nome do anexo é extraído do cabeçalho — 📊 medido hoje:
    # `attachment; filename="3402 - Porto Seguro CG144_Susep.pdf"`.
    real = 'attachment; filename="3402 - Porto Seguro CG144_Susep.pdf"'
    checar(S._nome_do_anexo(real) == "3402 - Porto Seguro CG144_Susep.pdf",
           "o nome sai do content-disposition real", str(S._nome_do_anexo(real)))
    checar(S._nome_do_anexo(None) is None and S._nome_do_anexo("") is None,
           "CONTROLE: sem cabeçalho, sem nome inventado")


def main() -> int:
    print("=" * 78)
    print("O REGISTRO DA SUSEP DIZ QUAL VERSÃO VALE — E O SILÊNCIO DELE TEM NOME")
    print("=" * 78)
    for teste in (teste_as_fixtures_sao_as_respostas_reais_e_inteiras,
                  teste_a_pagina_vazia_real_nao_pode_dizer_que_nao_mudou,
                  teste_produto_morto_e_um_terceiro_estado_e_nao_um_dos_outros_dois,
                  teste_sem_a_nossa_data_o_veredito_e_indeterminado,
                  teste_a_vigente_e_a_de_data_de_fim_vazia_e_nao_a_de_negrito,
                  teste_produto_vivo_sem_versao_em_aberto_nao_vira_em_dia,
                  teste_o_nome_do_arquivo_nao_carrega_a_palavra_download,
                  teste_o_ramo_vem_numerado_do_regulador,
                  teste_a_consulta_vazia_nao_entrega_datas_para_gravar,
                  teste_o_ponto_a_mais_da_porto_se_conserta_e_o_truncado_da_tokio_nao,
                  teste_o_processo_truncado_e_achavel_pelo_catalogo,
                  teste_o_catalogo_e_validado_pela_contagem_e_nao_pelo_status,
                  teste_o_ultimo_dump_bom_se_apresenta_como_cache,
                  teste_quem_nao_deu_para_consultar_continua_na_lista,
                  teste_e_adaptador_de_fonte_e_nao_um_motor_novo,
                  teste_o_download_recusa_html_disfarcado_de_pdf):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 78)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("A VERSÃO VIGENTE É LIDA DO REGISTRO — E 'NÃO CONSEGUI' NÃO VIRA 'NÃO MUDOU'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
