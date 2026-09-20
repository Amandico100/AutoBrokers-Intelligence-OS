# -*- coding: utf-8 -*-
r"""🔴 O DOCUMENTO VIRA BASE SEM VIRAR ERRO — o teste do FIO da EXTRA-001.5.2.

📊 19/09/2026, o que este guarda existe para impedir: das **81 linhas** que a
onda 1 propôs, **25 estavam certas** (40 CORRIGIR, 16 RECUSAR). E o erro não era
aleatório — eram cinco padrões, medidos de novo aqui em 20/09/2026 sobre
`docs/canon/reports/SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json`:

```
60 das 81 linhas nasceram em "Plano único"   — e 48 delas eram CORRIGIR/RECUSAR
20 linhas com o campo `plano` errado
 6 com `coberto` errado (a exclusão de OUTRA cobertura virando "nao" do plano)
 6 com `limite` errado (o número sem a coluna que diz se é por evento ou vigência)
 4 com `produto` errado (nome de ARQUIVO, travessão solto, versão colada)
15 linhas em `vidros`: 7 residencial, 6 auto, 2 condomínio — a mesma chave para
   uma COBERTURA contratada e um SERVIÇO de assistência
```

🔴 **O FIO, de ponta a ponta** (CLAUDE.md §9.4 — o teste chama o MOTOR):

```
bytes do PDF (MinIO duplo) -> texto_das_paginas (fitz REAL) -> capa_do_documento
-> localizar_ancora_de_planos -> paginas_com_vocabulario -> propostas_da_pagina
-> escopo do limite -> caminho da cláusula -> verificar -> propor_plano/propor_servico
-> a linha que a pessoa vê na fila
```

Dublê só na BORDA: o MinIO, o modelo e o cliente do banco. O PDF é de verdade, o
leitor é o `fitz` do corpus, o verificador é o de produção e a escrita é a do
contrato da fatia 1.

⚠️ **E o texto dos PDFs vem do ACERVO** (CLAUDE.md §9.4): cada frase abaixo é um
`trecho` real do JSON do leitor humano, com a seguradora, a página e o veredito
que ele escreveu. Nenhuma foi inventada.

🔴 **Cada caso tem o seu CONTROLE oposto** (protocolo §5): sem ele, um verde não
dá direito a conclusão nenhuma — poderia ser o duplo respondendo bonito.
"""
from __future__ import annotations

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.knowledge import assistance_plans_base as B  # noqa: E402
from app.services.knowledge import assistance_plans_extractor as X  # noqa: E402
from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


DOC = "22222222-2222-2222-2222-222222222222"


# ---------------------------------------------------------------------------
# Os PDFs — texto REAL do acervo, escrito com o mesmo `fitz` que lê
# ---------------------------------------------------------------------------
def pdf(paginas):
    """Um PDF de verdade: uma lista de linhas por página."""
    import fitz

    doc = fitz.open()
    for linhas in paginas:
        p = doc.new_page()
        y = 60
        for linha in linhas:
            p.insert_text((50, y), linha)
            y += 16
    return doc.tobytes()


class MinioDuplo:
    def __init__(self, corpo):
        self._corpo = corpo

    def download_file(self, _caminho):
        import io

        return io.BytesIO(self._corpo)


class ModeloDuplo:
    """Responde à ÂNCORA e às PÁGINAS. Conta as chamadas — custo é medida.

    `linhas_por_pagina` é o que o modelo "vê"; `ancora` é o que ele responde na
    primeira passada (`None` = deixa o texto resolver sozinho).
    """

    def __init__(self, linhas_por_pagina=None, ancora=None):
        self.linhas_por_pagina = linhas_por_pagina or {}
        self.ancora = ancora
        self.chamadas = 0
        self.chamadas_de_ancora = 0
        self.prompts = []

    def invoke(self, mensagens):
        self.chamadas += 1
        sistema = str(getattr(mensagens[0], "content", ""))
        usuario = str(getattr(mensagens[-1], "content", ""))
        self.prompts.append((sistema, usuario))
        if '"planos"' in sistema and "linhas" not in sistema:
            self.chamadas_de_ancora += 1
            return type("R", (), {"content": json.dumps(self.ancora or {"planos": []})})()
        m = re.search(r"P[áa]gina (\d+) do documento", usuario)
        pagina = int(m.group(1)) if m else 0
        linhas = list(self.linhas_por_pagina.get(pagina) or [])
        return type("R", (), {"content": json.dumps({"linhas": linhas})})()


def banco():
    db = BaseEmMemoria()
    db.tabelas["normative_document_versions"] = [
        {"document_id": DOC, "version": 1, "storage_ref": "acervo/x.pdf",
         "effective_from": "2019-06-01"}
    ]
    return db


# ============================================================================
print("\n[A] A CLÁUSULA DE PLANOS É A ÂNCORA — e sem ela o extrator NÃO propõe")
# ---------------------------------------------------------------------------
# 📊 acervo: tokio/auto — "Assistencia 24 Horas - Plano Vip (a pagina 32 esta no
# item 9.5.9.2)"; "Plano Completo (a pagina 28 esta no item 9.5.9.1)". Os três
# planos e a numeração são os do documento conferido pelo leitor em 19/09.
TOKIO = [
    ["Tokio Marine Seguradora S.A.",
     "Condicoes Gerais do Seguro de Automovel",
     "Versao 3.2"],
    ["9.5.9 Assistencia 24 Horas",
     "Os servicos abaixo sao prestados conforme o plano contratado pelo Segurado:",
     "Plano Basico, Plano Completo e Plano Vip.",
     "9.5.9.1 Plano Completo",
     "Hospedagem: R$100,00 (cem reais) por dia, ate o limite de R$200,00 por passageiro"],
    ["9.5.9.2 Plano Vip",
     "II. Carro Reserva",
     "02 (duas) diarias para pane, Carro Reserva 1.0 popular durante 02 (dois) dias",
     "Limite de utilizacao: 1 (um) reboque por evento, de ate 200 km contados a partir do",
     "local do evento"],
]
LINHAS_TOKIO = {
    2: [{"produto": "Tokio Marine Auto", "plano": "Plano Completo", "nivel": 2,
         "servico": "hospedagem", "coberto": "sim", "limite_valor": 100,
         "limite_unidade": "reais",
         "trecho": "Hospedagem: R$100,00 (cem reais) por dia, ate o limite de R$200,00 por passageiro",
         "confianca": "alta"}],
    3: [{"produto": "Tokio Marine Auto", "plano": "Assistencia 24 Horas - Plano Vip",
         "nivel": 9, "servico": "carro_reserva", "coberto": "sim",
         "trecho": "02 (duas) diarias para pane, Carro Reserva 1.0 popular durante 02 (dois) dias",
         "confianca": "alta"},
        {"produto": "Tokio Marine Auto", "plano": "Plano Vip", "nivel": 3,
         "servico": "guincho", "coberto": "sim", "limite_valor": 200, "limite_unidade": "km",
         "trecho": "Limite de utilizacao: 1 (um) reboque por evento, de ate 200 km contados a partir do",
         "confianca": "alta"},
        # 🔴 o padrão 2 em pessoa: o modelo insiste num plano que o documento não tem
        {"produto": "Tokio Marine Auto", "plano": "Plano unico", "nivel": 1,
         "servico": "taxi", "coberto": "sim",
         "trecho": "local do evento", "confianca": "baixa"},
        # 🔴 e o trecho INVENTADO: existe plano, existe serviço, e a frase não
        # está em página nenhuma do documento. Vira `rascunho` — e é a linha que
        # o bloco [F] usa para exigir que até o rascunho carregue veredito.
        {"produto": "Tokio Marine Auto", "plano": "Plano Completo", "nivel": 2,
         "servico": "chaveiro", "coberto": "sim",
         "trecho": "O chaveiro atende em todo o territorio nacional sem limite de acionamentos",
         "confianca": "media"}],
}
DOC_TOKIO = {"id": DOC, "insurer_key": "tokio", "product_line": "auto",
             "title": "Tokio Auto CG V3.2.pdf", "content_hash": "h1", "susep_process": None}

db_a = banco()
modelo_a = ModeloDuplo(LINHAS_TOKIO)
r_a = X.processar_documento(DOC_TOKIO, aplicar=True, llm=modelo_a, db=db_a,
                            minio=MinioDuplo(pdf(TOKIO)))
planos_a = db_a.tabelas.get("insurer_assistance_plans") or []
servicos_a = db_a.tabelas.get("insurer_assistance_services") or []
nomes_a = sorted({str(p.get("plano")) for p in planos_a})
checar(r_a.ancora is not None and r_a.planos_da_ancora == 3,
       "a âncora do documento foi localizada, com os 3 planos da cláusula 9.5.9",
       f"{r_a.motivo} / {r_a.ancora}")
checar(r_a.ancora is not None and r_a.ancora.clausula.startswith("9.5.9"),
       "🔴 e a âncora sabe de QUAL cláusula veio (9.5.9)",
       str(r_a.ancora.clausula if r_a.ancora else None))
checar(bool(planos_a) and all("unico" not in B._norm_texto(n) for n in nomes_a),
       "🔴 NENHUM plano chamado 'Plano único' — era 60 das 81 linhas de 19/09",
       str(nomes_a))
checar(sorted(nomes_a) == ["Completo", "Vip"],
       "as linhas saíram nos planos que a cláusula nomeia (Completo e Vip)",
       str(nomes_a))
checar(any(str(p.get("plano")) == "Vip" and int(p.get("nivel")) == 3 for p in planos_a),
       "🔴 e o NÍVEL é a ordem da âncora (Vip=3), não o palpite do modelo (que disse 9)",
       str([(p.get("plano"), p.get("nivel")) for p in planos_a]))
checar(r_a.recusadas.get("plano_fora_da_ancora") == 1,
       "🔴 a linha que insistiu em 'Plano unico' foi REPROVADA, nomeando o motivo",
       str(r_a.recusadas))
checar(bool(servicos_a) and all(str(s.get("curadoria")) in ("proposto", "rascunho")
                                for s in servicos_a),
       "e nada disso chegou a `publicado` — publicar continua sendo ato humano",
       str([s.get("curadoria") for s in servicos_a]))

print("\n[A · CONTROLE] o documento SEM cláusula de planos não propõe NADA")
# 📊 acervo: allianz/residencial — a página 86 é de riscos excluídos, e não
# enumera plano nenhum. É o documento que produzia "Plano único".
SEM_ANCORA = [
    ["Allianz Seguros S.A.", "Condicoes Gerais do Seguro Residencial"],
    ["Definicoes e glossario.",
     "Riscos Excluidos: danos por inundacao ou alagamento decorrente de",
     "transbordamentos de rios, enchentes"],
]
db_b = banco()
modelo_b = ModeloDuplo({2: [{"produto": "Allianz Residencia", "plano": "Plano unico",
                             "nivel": 1, "servico": "alagamento", "coberto": "nao",
                             "trecho": "Riscos Excluidos: danos por inundacao ou alagamento decorrente de",
                             "confianca": "media"}]})
r_b = X.processar_documento(
    {"id": DOC, "insurer_key": "allianz", "product_line": "residencial",
     "title": "Allianz Residencial.pdf", "content_hash": "h2"},
    aplicar=True, llm=modelo_b, db=db_b, minio=MinioDuplo(pdf(SEM_ANCORA)))
checar(r_b.motivo == "clausula_de_planos_nao_localizada",
       "🔴 CONTROLE: sem cláusula de planos, o documento é REGISTRADO como tal",
       r_b.motivo)
checar(not (db_b.tabelas.get("insurer_assistance_plans") or [])
       and not (db_b.tabelas.get("insurer_assistance_services") or []),
       "🔴 CONTROLE: e ZERO linhas foram propostas (o extrator recusa, não inventa)",
       str(len(db_b.tabelas.get("insurer_assistance_services") or [])))
checar(modelo_b.chamadas == 0,
       "⚠️ e o modelo NEM FOI CHAMADO — página não lida é página não paga",
       str(modelo_b.chamadas))

print("\n[A · MUTAÇÃO] com a âncora desligada, o extrator recusa — não inventa")
_verdadeira = X.localizar_ancora_de_planos
try:
    X.localizar_ancora_de_planos = lambda *a, **k: None
    db_m = banco()
    r_m = X.processar_documento(DOC_TOKIO, aplicar=True, llm=ModeloDuplo(LINHAS_TOKIO),
                                db=db_m, minio=MinioDuplo(pdf(TOKIO)))
    checar(r_m.motivo == "clausula_de_planos_nao_localizada"
           and not (db_m.tabelas.get("insurer_assistance_services") or []),
           "🔴 MUTAÇÃO: âncora desligada → o MESMO documento do [A] não propõe nada",
           f"{r_m.motivo} / {len(db_m.tabelas.get('insurer_assistance_services') or [])}")
finally:
    X.localizar_ancora_de_planos = _verdadeira

print("\n[A · MODELO] a cláusula que o texto não acha, o modelo acha — e a MÁQUINA confere")
# 📊 acervo: hdi/auto — "o produto e o plano da Clausula 2 (Auto Protegido
# Essencial/Especial 1/Especial 2/VIP...)". A página não escreve "Plano X" antes
# de cada nome, então o regex não a resolve: é para ela que o modelo existe.
HDI = [
    ["HDI Seguros S.A.", "Condicoes Gerais Auto Protegido"],
    ["Clausula 2 - Dos Produtos e Planos",
     "O Auto Protegido e comercializado nas modalidades Essencial, Especial 1,",
     "Especial 2 e VIP, conforme o plano de assistencia contratado.",
     "Guincho | Sinistro e Pane: 300km, ou ate R$ 120,00 por evento e R$ 360,00 por vigencia"],
]
paginas_hdi = B.texto_das_paginas(DOC, db=banco(), minio=MinioDuplo(pdf(HDI))).paginas
modelo_hdi = ModeloDuplo(ancora={"planos": ["Essencial", "Especial 1", "Especial 2", "VIP",
                                            "Diamante"],
                                 "pagina": 2, "clausula": "2",
                                 "trecho": "O Auto Protegido e comercializado nas modalidades Essencial, Especial 1,"})
sem_modelo = X.localizar_ancora_de_planos(paginas_hdi, modelo=None)
com_modelo = X.localizar_ancora_de_planos(paginas_hdi, modelo=modelo_hdi)
checar(sem_modelo is None,
       "🔴 CONTROLE: só com o texto, esta cláusula NÃO é achada (por isso o modelo existe)",
       str(sem_modelo))
checar(com_modelo is not None and len(com_modelo.planos) == 4,
       "com o modelo, os 4 planos da Cláusula 2 aparecem", str(com_modelo))
checar(com_modelo is not None and "Diamante" not in com_modelo.planos,
       "🔴 e o plano INVENTADO pelo modelo é derrubado pela verificação de máquina "
       "(não está LITERALMENTE na página que ele citou)",
       str(com_modelo.planos if com_modelo else None))
checar(modelo_hdi.chamadas_de_ancora == 1,
       "⚠️ UMA chamada por documento, sobre as páginas candidatas achadas por texto",
       str(modelo_hdi.chamadas_de_ancora))
# 🔴 CONTROLE da verificação: página fora das candidatas → âncora recusada.
mentiroso = ModeloDuplo(ancora={"planos": ["Essencial", "Especial 1"], "pagina": 99,
                                "clausula": "2", "trecho": ""})
checar(X.localizar_ancora_de_planos(paginas_hdi, modelo=mentiroso) is None,
       "🔴 CONTROLE: âncora que cita página fora das candidatas é RECUSADA")


# ============================================================================
print("\n[B] O ESCOPO DA CLÁUSULA MANDA NO VEREDITO — e a linha carrega de onde saiu")
# 📊 acervo: bradesco/residencial, CORRIGIR — "COBERTURA 03 - VENDAVAL, FURACAO,
# CICLONE, TORNADO E GRANIZO, exclusivamente em consequencia de"; e
# allianz/residencial, RECUSAR — o `nao` de alagamento saiu de dentro dela.
BRADESCO = [
    ["Bradesco Seguros S.A.", "Bilhete Residencial Pop", "Versao 1.0"],
    ["4. Planos",
     "Este bilhete e comercializado no Plano Basico e no Plano Ampliado.",
     "COBERTURA 03 - VENDAVAL, FURACAO, CICLONE, TORNADO E GRANIZO",
     "exclusivamente em consequencia de fenomeno atmosferico",
     "Estao excluidos os danos por inundacao ou alagamento decorrente de",
     "transbordamentos de rios",
     "6. Plano Ampliado - Assistencia",
     "Nao ha cobertura para carro reserva neste bilhete residencial"],
]
paginas_br = B.texto_das_paginas(DOC, db=banco(), minio=MinioDuplo(pdf(BRADESCO))).paginas
ancora_br = X.localizar_ancora_de_planos(paginas_br)
pagina2 = paginas_br.get(2, "")
dentro_da_outra = {
    "produto": "Bradesco Bilhete Residencial Pop", "plano": "Plano Basico", "nivel": 1,
    "servico": "alagamento", "coberto": "nao", "pagina": 2,
    "trecho": "Estao excluidos os danos por inundacao ou alagamento decorrente de",
}
motivo_b = X.verificar(dentro_da_outra, insurer="bradesco", documento_id=DOC,
                       niveis_por_produto={}, db=banco(),
                       minio=MinioDuplo(pdf(BRADESCO)), ancora=ancora_br,
                       texto_da_pagina=pagina2)
checar(motivo_b in ("exclusao_de_risco_nao_e_nao_do_servico",
                    "nao_veio_de_clausula_de_outro_servico"),
       "🔴 `alagamento = nao` lido DENTRO da cláusula de Vendaval/Granizo NÃO vira "
       "'nao' do plano — é reprovado e nomeado",
       str(motivo_b))
# 🔴 CONTROLE: a exclusão que é MESMO do plano continua virando `nao`.
do_plano = {
    "produto": "Bradesco Bilhete Residencial Pop", "plano": "Plano Ampliado", "nivel": 2,
    "servico": "carro_reserva", "coberto": "nao", "pagina": 2,
    "trecho": "Nao ha cobertura para carro reserva neste bilhete residencial",
}
motivo_ctrl = X.verificar(do_plano, insurer="bradesco", documento_id=DOC,
                          niveis_por_produto={}, db=banco(),
                          minio=MinioDuplo(pdf(BRADESCO)), ancora=ancora_br,
                          texto_da_pagina=pagina2)
checar(motivo_ctrl is None,
       "🔴 CONTROLE: a negação que é MESMO do plano PASSA e continua sendo `nao`",
       str(motivo_ctrl))
caminho = X.caminho_da_clausula(pagina2, dentro_da_outra["trecho"], ancora=ancora_br,
                                plano="Basico", servico="alagamento")
checar("VENDAVAL" in caminho.upper() and "Plano" in caminho,
       "🔴 e a proposta carrega o CAMINHO DA CLÁUSULA de onde ela saiu — é o que "
       "mostra o erro sem abrir o PDF",
       caminho)
caminho_certo = X.caminho_da_clausula(pagina2, do_plano["trecho"], ancora=ancora_br,
                                      plano="Ampliado", servico="carro_reserva")
checar("VENDAVAL" not in caminho_certo.upper() and caminho_certo != caminho,
       "🔴 CONTROLE: a linha que saiu da cláusula do PLANO tem outro caminho",
       caminho_certo)


# ============================================================================
print("\n[C] NÚMERO DE TABELA VEM COM A COLUNA, OU NÃO VEM")
# 📊 acervo: hdi/residencial, CORRIGIR — "R$ 300,00 por evento e R$ 600,00 por
# vigencia, 2 utilizacoes (tabela da pagina 56)". O número sozinho não diz qual.
COM_CABECALHO = "Eletricista | Ate R$ 300,00 por evento e R$ 600,00 por vigencia | 2 utilizacoes"
pagina_c = "Tabela de servicos\n" + COM_CABECALHO + "\n"
p_com = X.aplicar_escopo_do_limite(
    {"servico": "eletricista", "limite_valor": 300, "limite_unidade": "reais",
     "pagina": 56, "trecho": COM_CABECALHO}, pagina_c)
checar(p_com.get("limite_valor") == 300
       and "por_evento" in (p_com.get("limite_escopo") or [])
       and "por_vigencia" in (p_com.get("limite_escopo") or []),
       "🔴 com o cabeçalho, o limite fica COM unidade e COM escopo (evento E vigência)",
       str(p_com))
checar("evento" in str(p_com.get("limite_texto") or ""),
       "e o escopo fica ESCRITO na linha, não só num campo que ninguém lê",
       str(p_com.get("limite_texto")))
# 🔴 CONTROLE: a mesma tabela sem cabeçalho → campo VAZIO, com o motivo.
SEM_CABECALHO = "Super Luxo | R$ 70.000,00"
p_sem = X.aplicar_escopo_do_limite(
    {"servico": "vidros", "limite_valor": 70000, "limite_unidade": "reais",
     "pagina": 12, "trecho": SEM_CABECALHO}, "Tabela\n" + SEM_CABECALHO + "\n")
checar(p_sem.get("limite_valor") is None and p_sem.get("limite_unidade") is None,
       "🔴 CONTROLE: sem cabeçalho legível, o limite fica VAZIO — não um número solto",
       str(p_sem))
checar("escopo" in str(p_sem.get("limite_texto") or "")
       and "12" in str(p_sem.get("limite_texto") or ""),
       "🔴 e a linha DIZ por que ficou vazia, com a página",
       str(p_sem.get("limite_texto")))
# 🔴 CONTROLE do par: o guarda CONSEGUE ficar vermelho — um número com escopo
#    não é apagado, senão "campo vazio" seria só o comportamento de sempre.
checar(p_com.get("limite_valor") != p_sem.get("limite_valor"),
       "🔴 CONTROLE: os dois caminhos dão resultados DIFERENTES (o guarda distingue)")


# ============================================================================
print("\n[D] O PRODUTO E A VERSÃO VÊM DA CAPA")
# 📊 acervo: mapfre/residencial, CORRIGIR — "Mapfre Residencial (o nome gravado
# e o do documento; e a versao declarada, v2.9, nao e a do PDF, versao 3.2)".
MAPFRE = [
    ["Mapfre Seguros Gerais S.A.",
     "Seguro Residencial Danos ao Conteudo",
     "Condicoes Contratuais - Versao 3.2",
     "Processo SUSEP 15414.900000/2015-00"],
    ["10. COBERTURA ADICIONAL DE VENDAVAL, GRANIZO",
     "b) Granizo: acao mecanica do granizo (pedras de gelo)"],
]
paginas_d = B.texto_das_paginas(DOC, db=banco(), minio=MinioDuplo(pdf(MAPFRE))).paginas
capa = X.capa_do_documento(paginas_d)
checar(capa.produto and "Mapfre" in capa.produto and "V1.2" not in capa.produto,
       "o produto é lido da CAPA — não do nome do arquivo", str(capa))
checar(capa.versao == "3.2", "e a versão também vem da capa/rodapé", str(capa.versao))
checar(X.versao_declarada("Mapfre Residencial — Condições Contratuais V2.9") == "2.9",
       "a versão do CADASTRO é lida do título que o cadastro guarda")
db_d = banco()
r_d = X.processar_documento(
    {"id": DOC, "insurer_key": "mapfre", "product_line": "residencial",
     "title": "Mapfre residencial — Seguro Residencial Conteudo_V2.9",
     "content_hash": "h3"},
    aplicar=True, llm=ModeloDuplo({}), db=db_d, minio=MinioDuplo(pdf(MAPFRE)))
checar(any("versao_da_capa_diverge" in a for a in r_d.alertas),
       "🔴 capa 3.2 × cadastro 2.9 → ALERTA, não silêncio", str(r_d.alertas))
checar(r_d.produto_da_capa and "Conteudo_V" not in str(r_d.produto_da_capa),
       "e o nome de ARQUIVO ('Seguro Residencial Conteudo_V1.2') não vira produto",
       str(r_d.produto_da_capa))
# 🔴 CONTROLE: quando as duas batem, nada acende.
r_d2 = X.processar_documento(
    {"id": DOC, "insurer_key": "mapfre", "product_line": "residencial",
     "title": "Mapfre Residencial — Condicoes Contratuais V3.2", "content_hash": "h3"},
    aplicar=True, llm=ModeloDuplo({}), db=banco(), minio=MinioDuplo(pdf(MAPFRE)))
checar(not any("versao_da_capa_diverge" in a for a in r_d2.alertas),
       "🔴 CONTROLE: cadastro V3.2 e capa 3.2 → NENHUM alerta (o guarda distingue)",
       str(r_d2.alertas))


# ============================================================================
print("\n[E] COBERTURA NÃO É ASSISTÊNCIA — `vidros` residencial tem chave própria")
# 📊 20/09/2026, medido no JSON do leitor: 15 linhas usam `vidros` — 7
# residencial, 6 auto, 2 condomínio. A residencial é COBERTURA contratada
# ("mediante pagamento de Premio adicional", mapfre/condominio, PUBLICAR).
checar(X.servico_do_ramo("vidros", "residencial") == "vidros_residencial"
       and X.servico_do_ramo("vidros", "condominio") == "vidros_residencial",
       "🔴 `vidros` em residencial/condomínio vira `vidros_residencial`")
checar(X.servico_do_ramo("vidros", "auto") == "vidros",
       "🔴 CONTROLE: em AUTO continua `vidros` — lá é assistência de verdade")
checar(B.tipo_do_servico("vidros_residencial") == "cobertura"
       and B.tipo_do_servico("vidros") == "assistencia",
       "e o vocabulário sabe a diferença: uma é cobertura, a outra é assistência",
       f"{B.tipo_do_servico('vidros_residencial')} / {B.tipo_do_servico('vidros')}")
checar(B.servico_canonico("quebrou o parabrisa") == "vidros"
       and B.servico_canonico("quebrou o vidro da janela de casa") == "vidros_residencial",
       "🔴 e a pergunta do segurado continua caindo na chave certa dos dois lados",
       f"{B.servico_canonico('quebrou o parabrisa')} / "
       f"{B.servico_canonico('quebrou o vidro da janela de casa')}")

# E pelo MOTOR, de ponta a ponta: o mesmo serviço, dois ramos, duas chaves.
VIDROS = [
    ["Mapfre Seguros Gerais S.A.", "Condominio - Condicoes Gerais", "Versao 1.0"],
    ["3. Planos", "Este seguro e comercializado no Plano Basico e no Plano Master.",
     "Quebra de Vidros",
     "mediante pagamento de Premio adicional, danos causados por acidente de origem externa"],
]
LINHA_VIDROS = {2: [{"produto": "Mapfre Condominio", "plano": "Plano Master", "nivel": 2,
                     "servico": "vidros", "coberto": "condicionado",
                     "trecho": "mediante pagamento de Premio adicional, danos causados por acidente de origem externa",
                     "confianca": "alta"}]}
db_e = banco()
X.processar_documento(
    {"id": DOC, "insurer_key": "mapfre", "product_line": "condominio",
     "title": "Mapfre Condominio.pdf", "content_hash": "h4"},
    aplicar=True, llm=ModeloDuplo(LINHA_VIDROS), db=db_e, minio=MinioDuplo(pdf(VIDROS)))
chaves_e = [str(s.get("servico")) for s in (db_e.tabelas.get("insurer_assistance_services") or [])]
checar(chaves_e == ["vidros_residencial"],
       "🔴 pelo MOTOR: a linha de condomínio foi gravada como `vidros_residencial`",
       str(chaves_e))
db_e2 = banco()
X.processar_documento(
    {"id": DOC, "insurer_key": "mapfre", "product_line": "auto",
     "title": "Mapfre Auto.pdf", "content_hash": "h5"},
    aplicar=True, llm=ModeloDuplo(LINHA_VIDROS), db=db_e2, minio=MinioDuplo(pdf(VIDROS)))
chaves_e2 = [str(s.get("servico")) for s in (db_e2.tabelas.get("insurer_assistance_services") or [])]
checar(chaves_e2 == ["vidros"],
       "🔴 CONTROLE: o MESMO documento em AUTO grava `vidros` — o ramo é que decide",
       str(chaves_e2))

# ============================================================================
print("\n[F] A LINHA NASCE CONFERIDA — e o veredito CHEGA à fila")
# 🔴 Unidade F: o que o leitor humano fez à mão em 19/09 (135 campos conferidos
# contra a página) vira PASSO DO CANO. Sem isto, curar 81 linhas obriga o
# Founder a abrir 27 PDFs — e foi por isso que 58 das linhas ficaram paradas.
db_f = banco()
r_f = X.processar_documento(DOC_TOKIO, aplicar=True, llm=ModeloDuplo(LINHAS_TOKIO),
                            db=db_f, minio=MinioDuplo(pdf(TOKIO)))
linhas_f = db_f.tabelas.get("insurer_assistance_services") or []
propostas_f = [l for l in linhas_f if str(l.get("curadoria")) == "proposto"]
rascunhos_f = [l for l in linhas_f if str(l.get("curadoria")) == "rascunho"]
checar(bool(linhas_f) and all(str(l.get("veredito_do_conferente") or "")
                              in ("CONFERE", "DIVERGE", "NAO_CONSEGUI") for l in linhas_f),
       "🔴 TODA linha gravada sai com veredito do conferente — nenhuma sem parecer",
       str([(l.get("servico"), l.get("veredito_do_conferente")) for l in linhas_f]))
checar(all(isinstance(l.get("conferencia"), dict)
           and "campos" in l["conferencia"] and "motivos" in l["conferencia"]
           for l in linhas_f),
       "e o parecer inteiro viaja junto (`campos` + `motivos`), não só o rótulo",
       str([l.get("conferencia") for l in linhas_f][:1]))
checar(all(str(l.get("caminho_da_clausula") or "").strip() for l in linhas_f),
       "🔴 e cada linha diz de QUAL cláusula ela saiu (unidade B, gravado)",
       str([l.get("caminho_da_clausula") for l in linhas_f]))
checar(all(l.get("conferido_em") for l in linhas_f),
       "e quando foi conferida")
checar(any(str(l.get("veredito_do_conferente")) == "CONFERE" for l in propostas_f),
       "🔴 CONTROLE: a linha boa (trecho na página, plano da âncora, número da "
       "página) sai CONFERE — senão o selo seria sempre o mesmo",
       str([(l.get("servico"), l.get("veredito_do_conferente")) for l in propostas_f]))
checar(bool(rascunhos_f) and all(str(l.get("veredito_do_conferente") or "")
                                 in ("CONFERE", "DIVERGE", "NAO_CONSEGUI")
                                 for l in rascunhos_f),
       "🔴 PAR: a linha do trecho INVENTADO não virou `proposto` — e o rascunho "
       "dela também carrega veredito",
       str([(l.get("servico"), l.get("curadoria"), l.get("veredito_do_conferente"))
            for l in rascunhos_f]))
checar(any(str(l.get("veredito_do_conferente")) == "DIVERGE" for l in rascunhos_f),
       "🔴 e o veredito dela é DIVERGE: a página não sustenta a frase",
       str([(l.get("servico"), l.get("veredito_do_conferente")) for l in rascunhos_f]))
checar(all(str(l.get("curadoria")) != "publicado" for l in linhas_f),
       "⛔ e o conferente NÃO publica nada — ele anota",
       str({str(l.get("curadoria")) for l in linhas_f}))

fila_f = B.fila_de_curadoria(limite=50, curadorias=("proposto", "rascunho"), db=db_f)
checar(bool(fila_f) and all(
    set(("veredito_do_conferente", "conferencia", "conferido_em",
         "caminho_da_clausula")).issubset(item.keys()) for item in fila_f),
       "🔴 e a FILA repassa as quatro chaves — é o que a tela mostra ao curador",
       str(sorted(fila_f[0].keys())) if fila_f else "fila vazia")
checar(any(item.get("veredito_do_conferente") for item in fila_f),
       "🔴 CONTROLE: e o veredito chega PREENCHIDO na fila (não é chave vazia)",
       str([(i.get("servico"), i.get("veredito_do_conferente")) for i in fila_f]))

print("\n[F · CONTROLE] o conferente que quebra NÃO derruba a extração")
# 🔴 P-F04: uma exceção no conferente não pode custar a onda inteira. A linha
# nasce com NAO_CONSEGUI e o motivo escrito — que é diferente de DIVERGE.
import app.services.knowledge.assistance_plans_conferente as CONF  # noqa: E402
_bom = CONF.conferir_linha


def _explode(*_a, **_k):
    raise RuntimeError("o conferente quebrou")


try:
    CONF.conferir_linha = _explode
    db_g = banco()
    r_g = X.processar_documento(DOC_TOKIO, aplicar=True, llm=ModeloDuplo(LINHAS_TOKIO),
                                db=db_g, minio=MinioDuplo(pdf(TOKIO)))
    linhas_g = db_g.tabelas.get("insurer_assistance_services") or []
    checar(bool(linhas_g) and r_g.servicos_propostos > 0,
           "🔴 CONTROLE: com o conferente quebrado, a extração CONTINUA gravando",
           f"{r_g.motivo} / {len(linhas_g)}")
    checar(all(str(l.get("veredito_do_conferente")) == "NAO_CONSEGUI" for l in linhas_g),
           "🔴 e as linhas saem NAO_CONSEGUI — não CONFERE por omissão nem DIVERGE",
           str([l.get("veredito_do_conferente") for l in linhas_g]))
    checar(all("conferente" in " ".join((l.get("conferencia") or {}).get("motivos") or [])
               for l in linhas_g),
           "e o motivo da falha fica escrito na linha",
           str([(l.get("conferencia") or {}).get("motivos") for l in linhas_g][:1]))
finally:
    CONF.conferir_linha = _bom

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
