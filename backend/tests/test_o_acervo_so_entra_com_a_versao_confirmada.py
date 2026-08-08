# -*- coding: utf-8 -*-
"""Só entra no acervo o que o registro oficial confirmou. SPEC-070 §3.2.1 e §9.

O defeito que este arquivo existe para impedir
----------------------------------------------
📊 12 de 13 documentos indexados hoje são versões **revogadas** (SPEC-070 §1).
O condomínio da Porto é de dezembro/2012 e o vigente é de dezembro/2025.

E o erro é invisível: um contrato revogado tem o logotipo certo, a linguagem
certa e o número de processo certo. O segurado age sobre a resposta e ninguém
percebe. Não existe alerta possível depois — só antes.

    "Não consegui perguntar" NUNCA pode virar "não mudou".

🔴 O CONTROLE QUE DÁ DIREITO A CONFIAR NO RESTO
------------------------------------------------
Um script que **sempre indexa** passaria numa bateria mal feita: todo caso de
sucesso ficaria verde e ninguém notaria que a recusa nunca acontece. Por isso o
teste central aqui não é "o vigente entra" — é **"o que não pôde ser
confirmado NÃO entra"**, alimentado com a resposta vazia real da SUSEP
(`tests/fixtures/susep_rep2/`), e com a linha de CONTROLE ao lado provando que
o mesmo caminho SABE dizer sim quando o registro responde.

    📊 A resposta vazia real tem 11.545 bytes e HTTP 200. A cheia tem 95.861.
    Nenhuma mensagem de erro distingue as duas — só a ausência do bloco
    "Detalhes do Produto".

O que mais é guardado aqui
--------------------------
2. Produto cancelado não entra, mesmo com tabela de versões cheia.
3. 🔴 **Duas versões em aberto = recusa.** A peça de baixo escolhe a de início
   mais recente e avisa no motivo; a §3.2.1 item 3 proíbe escolher. Aqui o
   aviso vira recusa.
4. Versão com Data de Fim preenchida é revogada, e revogada não entra.
5. O `unit_id` volta ao ponto no índice **por aritmética** — é assim que a
   carta destilada reencontra o trecho de origem (migration 03).
6. Quem indexa e quem exporta enumeram os pedaços do MESMO jeito. Se
   divergirem, a carta aponta para o trecho errado, que é pior que apontar
   para lugar nenhum.
7. A faceta é decidida da FOLHA para a raiz.
8. O progresso mora no banco, não no filesystem — 📊 109 minutos, 08/08/2026.

Cada afirmação tem CONTROLE ao lado (CLAUDE.md §9.2).
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import sys
import types
from dataclasses import replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "tests" / "fixtures" / "susep_rep2"
SCRIPT = RAIZ / "scripts" / "acervo" / "coletar_seguradora.py"
QDRANT = RAIZ / "app" / "services" / "qdrant_service.py"

for _n in ("app", "app.services", "app.services.knowledge"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


rep2 = _carregar("app.services.knowledge.susep_rep2",
                 RAIZ / "app" / "services" / "knowledge" / "susep_rep2.py")
corpus = _carregar("app.services.knowledge.insurance_corpus",
                   RAIZ / "app" / "services" / "knowledge" / "insurance_corpus.py")
maestro = _carregar("coletar_seguradora", SCRIPT)

FALHAS: list = []


def checar(condicao: bool, nome: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X     {nome}  {detalhe}")


def _pagina(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8", errors="replace")


def _produto(consulta, *, ramo="auto", processo="15414.100233/2004-59",
             nosso=None):
    p = maestro.Produto(processo=processo, entnome="PORTO SEGURO COMPANHIA",
                        ramo_oficial="05 | AUTOMÓVEL - CASCO",
                        subramo="VALOR DE MERCADO", product_line=ramo)
    p.consulta = consulta
    p.nosso = nosso or []
    maestro.montar_ficha(p)
    return p


# ══════════════════════════════════════════════════════════════════════════
# 1. 🔴 O CONTROLE MAIS IMPORTANTE — o que não foi confirmado não entra
# ══════════════════════════════════════════════════════════════════════════

def teste_a_resposta_vazia_da_susep_nao_indexa_nada():
    print("\n[1] 🔴 200 com página vazia NÃO pode virar documento no acervo")

    vazia = rep2.interpretar_consulta(
        _pagina("tokio_auto_truncado_vazio.html"), "15414.100335/2004")
    checar(vazia.estado == rep2.INDETERMINADO,
           "a resposta vazia REAL da SUSEP é lida como `indeterminado`",
           f"{vazia.estado} / {vazia.motivo}")

    p = _produto(vazia, processo="15414.100335/2004")
    checar(p.veredito == maestro.PULA,
           "🔴 e o documento NÃO ENTRA — o script pula e registra",
           f"veredito={p.veredito} motivo={p.motivo}")
    checar(any("indeterminado" in f for f in p.faltando),
           "o motivo diz `indeterminado`, e não 'sem alteração'", str(p.faltando))
    checar(bool(p.ficha),
           "e a ficha é impressa mesmo assim — o pulo é auditável, não silencioso")

    # 🔴 CONTROLE — o MESMO caminho, com a resposta cheia real, diz SIM.
    # Sem esta linha, um `montar_ficha` que recusasse tudo passaria em todos os
    # casos acima, e a bateria estaria medindo a própria paralisia.
    cheia = rep2.interpretar_consulta(_pagina("porto_auto_vigente.html"),
                                      "15414.100233/2004-59")
    ok = _produto(cheia)
    checar(ok.veredito == maestro.ENTRA,
           "CONTROLE: com a resposta CHEIA real, o mesmo caminho aprova",
           f"veredito={ok.veredito} motivo={ok.motivo}")
    checar(not ok.faltando, "CONTROLE 2: e nenhuma linha da ficha ficou vazia",
           str(ok.faltando))

    # CONTROLE 3 — a segunda página vazia (a circular) também é recusada. Uma
    # recusa que só funciona para um arquivo é sorte, não regra.
    circular = rep2.interpretar_consulta(
        _pagina("circular_710_2024_vazio.html"), "15414.621724/2024-82")
    checar(_produto(circular).veredito == maestro.PULA,
           "CONTROLE 3: a outra página vazia real também não entra",
           circular.estado)


def teste_produto_cancelado_nao_entra():
    print("\n[2] Produto morto tem tabela de versões cheia — e não entra")
    c = rep2.interpretar_consulta(_pagina("azul_residencial_cancelado.html"),
                                  "15414.000743/2005-16")
    checar(c.estado == rep2.PRODUTO_MORTO,
           "a situação lida do registro não é 'Passível de comercialização'",
           f"{c.estado} · situacao={c.situacao!r}")
    checar(len(c.versoes) > 0,
           "📊 e ele TEM versões — é isso que torna o caso perigoso",
           f"{len(c.versoes)} versões")

    p = _produto(c, ramo="residencial", processo="15414.000743/2005-16")
    checar(p.veredito == maestro.PULA,
           "🔴 mesmo com versão baixável, o produto morto não entra", p.motivo)
    checar(any("situação" in f for f in p.faltando),
           "e a linha que reprovou é a da situação", str(p.faltando))

    # CONTROLE — a ficha CONSEGUE aprovar situação. Sem isto, "reprovou por
    # situação" seria indistinguível de "reprova sempre por situação".
    vivo = rep2.interpretar_consulta(_pagina("porto_auto_vigente.html"),
                                     "15414.100233/2004-59")
    checar(not any("situação" in f for f in _produto(vivo).faltando),
           "CONTROLE: com situação viva, essa linha passa")


# ══════════════════════════════════════════════════════════════════════════
# 2. As duas armadilhas da própria regra
# ══════════════════════════════════════════════════════════════════════════

def teste_duas_versoes_em_aberto_nao_sao_escolha_nossa():
    print("\n[3] 🔴 §3.2.1 item 3 — duas vigentes é defeito da FONTE")
    real = rep2.interpretar_consulta(_pagina("porto_auto_vigente.html"),
                                     "15414.100233/2004-59")
    abertas = [v for v in real.versoes if v.vigente]
    checar(len(abertas) == 1,
           "📊 no registro real da Porto auto há exatamente UMA versão em aberto",
           f"{len(abertas)} de {len(real.versoes)}")

    # Duas em aberto, montadas a partir das linhas REAIS do portal: a segunda é
    # uma versão fechada de verdade com a Data de Fim apagada.
    fechada = next(v for v in real.versoes if not v.vigente)
    duas = replace(real, versoes=tuple(list(abertas) + [replace(fechada, fim=None)]),
                   motivo="2_versoes_em_aberto")
    p = _produto(duas)
    checar(p.veredito == maestro.PULA,
           "🔴 com duas em aberto o script RECUSA — não escolhe a mais recente",
           f"{p.veredito} / {p.motivo}")
    checar(any("em_aberto" in f for f in p.faltando),
           "e o motivo nomeia o defeito da fonte", str(p.faltando))

    # CONTROLE — com UMA em aberto (o caso real), entra. Sem esta linha, uma
    # recusa por qualquer motivo passaria como se fosse por este.
    checar(_produto(real).veredito == maestro.ENTRA,
           "CONTROLE: com uma só em aberto, o mesmo documento entra")


def teste_versao_com_data_de_fim_e_revogada():
    print("\n[4] Data de Fim preenchida = revogada. Não entra por nenhum motivo")
    real = rep2.interpretar_consulta(_pagina("porto_auto_vigente.html"),
                                     "15414.100233/2004-59")
    revogada = replace(real, vigente=replace(real.vigente, fim="30/06/2026"))
    p = _produto(revogada)
    checar(p.veredito == maestro.PULA,
           "🔴 a versão escolhida tem Data de Fim — o documento não entra", p.motivo)
    linha_fim = dict(p.ficha).get("fim", "")
    checar("REVOGADA" in linha_fim,
           "e a ficha grita na linha `fim`, que é a que o olho pula", linha_fim)

    # CONTROLE — a mesma linha, com fim vazio, diz `(vazio)` e aprova.
    checar(dict(_produto(real).ficha).get("fim") == "(vazio)",
           "CONTROLE: com fim vazio a ficha imprime `(vazio)` e aprova",
           dict(_produto(real).ficha).get("fim"))


def teste_a_ficha_cobre_as_sete_linhas_da_spec():
    print("\n[5] A ficha de conferência tem as 7 linhas da §3.2.1")
    real = rep2.interpretar_consulta(_pagina("porto_auto_vigente.html"),
                                     "15414.100233/2004-59")
    rotulos = [r for r, _ in _produto(real).ficha]
    for exigida in ("produto", "situação", "versão baixada", "início", "fim",
                    "total de versões", "o que tínhamos"):
        checar(exigida in rotulos, f"a ficha traz `{exigida}`", str(rotulos))

    # CONTROLE — "o que tínhamos" muda quando temos algo. É a única linha que é
    # fato NOSSO, e "nada" é preenchimento válido só nela.
    com = _produto(real, nosso=[{"title": "CG140", "effective_from": "2026-01-01",
                                 "chunk_count": 863, "product_line": "auto",
                                 "doc_kind": "condicoes_gerais"}])
    checar("CG140" in dict(com.ficha)["o que tínhamos"],
           "CONTROLE: com documento nosso, a linha mostra qual e de quando",
           dict(com.ficha)["o que tínhamos"])
    checar(dict(_produto(real).ficha)["o que tínhamos"] == "nada",
           "CONTROLE 2: sem documento nosso, ela diz `nada` — e isso não reprova")


# ══════════════════════════════════════════════════════════════════════════
# 3. O caminho de volta: da carta para o trecho
# ══════════════════════════════════════════════════════════════════════════

def _ponto_do_qdrant(document_id: str, indice: int) -> int:
    """A MESMA conta de `QdrantService.insert_embeddings`, reescrita aqui.

    Reescrever é o ponto: se ela mudar lá e não aqui, este teste reprova — e é
    isso que impede o `unit_id` de virar um endereço que não endereça nada.
    """
    return int(hashlib.sha256(f"{document_id}_{indice}".encode()).hexdigest()[:16], 16)


def teste_o_unit_id_volta_ao_ponto_por_aritmetica():
    print("\n[6] Do `source_unit_id` da carta ao ponto no índice, sem tabela de-para")
    doc_id = "norm-d24fa589-e261-48c6-bfee-983097b15873-v2"
    uid = corpus.unit_id_de(doc_id, 42)
    checar(uid == f"{doc_id}#0042", "o `unit_id` é derivado, não sorteado", uid)

    endereco, _, indice = uid.rpartition("#")
    checar(endereco == doc_id and int(indice) == 42,
           "e ele se desmonta de volta em (documento-versão, índice)",
           f"{endereco} / {indice}")
    checar(_ponto_do_qdrant(endereco, int(indice)) > 0,
           "de onde sai o id do ponto pela conta do `insert_embeddings`")

    # 🔴 CONTROLE — a conta que este teste reescreve é a que o Qdrant usa de
    # verdade. Se `insert_embeddings` trocar a fórmula, o `unit_id` continuaria
    # bonito e deixaria de apontar para coisa nenhuma.
    fonte = QDRANT.read_text(encoding="utf-8")
    checar('point_id_str = f"{document_id}_{idx}"' in fonte,
           "CONTROLE: o Qdrant ainda monta o id do ponto com `document_id_idx`",
           "se mudou lá, o unit_id deixou de ser reencontrável")
    checar('hashlib.sha256(point_id_str.encode()).hexdigest()[:16], 16' in fonte,
           "CONTROLE 2: e ainda é sha256 truncado em 16 hex")

    # CONTROLE 3 — a busca CONSEGUE não achar.
    checar("uma_formula_que_nao_existe" not in fonte,
           "CONTROLE 3: a conferência sabe dizer NÃO")

    # CONTROLE 4 — índices diferentes dão pontos diferentes. Um `unit_id` que
    # colidisse levaria a carta ao trecho vizinho, e ninguém veria.
    checar(_ponto_do_qdrant(doc_id, 42) != _ponto_do_qdrant(doc_id, 43),
           "CONTROLE 4: pedaços diferentes têm endereços diferentes")
    checar(corpus.unit_id_de(doc_id, 42) != corpus.unit_id_de(doc_id + "x", 42),
           "CONTROLE 5: e versões diferentes também")


TEXTO_DE_MENTIRA = """CLÁUSULA 12 - COBERTURA DE VIDROS
1. Riscos Cobertos
A cobertura garante a substituição de vidros, retrovisores, lanternas e faróis
do veículo segurado, quando houver quebra ou trinca, respeitados os limites
estabelecidos na apólice e as condições descritas nesta cláusula do contrato.
2. Riscos Excluídos
Não estão cobertos riscos, manchas e arranhões de qualquer natureza, ainda que
decorrentes de evento coberto por outra garantia contratada pelo segurado, nem
os danos preexistentes à contratação do seguro de que trata este documento.
3. Franquia
Para cada acionamento da cobertura haverá participação obrigatória do segurado,
cujo valor consta da apólice e varia conforme a peça substituída e o modelo do
veículo, conforme tabela vigente na data do evento coberto pelo contrato.
"""


def teste_quem_indexa_e_quem_exporta_contam_igual():
    print("\n[7] 🔴 O pedaço nº N do `.jsonl` é o ponto nº N do índice")
    doc = {"id": "x", "insurer_key": "porto", "insurer_name": "Porto Seguro",
           "product_line": "auto", "title": "CG144", "doc_kind": "condicoes_gerais"}
    det = corpus.pedacos_detalhados(doc, TEXTO_DE_MENTIRA, "15414.100233/2004-59",
                                    "2026-07-01", "norm-x-v1")
    chunks = corpus.montar_pedacos(doc, TEXTO_DE_MENTIRA, "15414.100233/2004-59",
                                   "2026-07-01")
    checar(len(det) == len(chunks) and [p["texto"] for p in det] == chunks,
           "as duas saídas são a MESMA lista, na mesma ordem",
           f"{len(det)} × {len(chunks)}")
    checar(all(p["indice"] == i for i, p in enumerate(det)),
           "e o índice de cada pedaço é a posição dele")
    checar(all(p["unit_id"] == f"norm-x-v1#{i:04d}" for i, p in enumerate(det)),
           "o `unit_id` acompanha essa posição",
           str([p["unit_id"] for p in det][:3]))

    # 🔴 CONTROLE — `montar_pedacos` é INVÓLUCRO de `pedacos_detalhados`, e não
    # uma irmã. Duas funções percorrendo a mesma regra concordam hoje e
    # divergem no dia em que uma mudar; a divergência apontaria a carta para o
    # trecho errado, e procedência falsa é pior que procedência ausente.
    fonte = (RAIZ / "app" / "services" / "knowledge" / "insurance_corpus.py") \
        .read_text(encoding="utf-8")
    corpo = fonte.split("def montar_pedacos(")[1].split("\ndef ")[0]
    checar("pedacos_detalhados(" in corpo,
           "CONTROLE: `montar_pedacos` chama `pedacos_detalhados`",
           "se ele voltar a picar por conta própria, as duas contagens divergem")
    checar("partir_documento(" not in corpo,
           "CONTROLE 2: e não percorre `partir_documento` por conta própria")

    # CONTROLE 3 — a comparação CONSEGUE reprovar. Um texto que produzisse um
    # pedaço só faria a igualdade acima passar sem medir nada.
    checar(len(det) > 1 and det[0]["texto"] != det[1]["texto"],
           "CONTROLE 3: há mais de um pedaço, e eles são diferentes entre si",
           f"{len(det)} pedaços")

    # CONTROLE 4 — `parent_id` agrupa irmãos da mesma seção e separa seções.
    pais = {p["caminho"]: p["parent_id"] for p in det}
    checar(len(set(pais.values())) == len(pais),
           "CONTROLE 4: seções diferentes têm `parent_id` diferentes",
           str(pais))


def teste_a_faceta_e_decidida_da_folha_para_a_raiz():
    print("\n[8] `COBERTURA DE VIDROS > Riscos Excluídos` é exclusão, não escopo")
    raiz = "CLÁUSULA 12 - COBERTURA DE VIDROS"
    corpo = "Não estão cobertos riscos, manchas e arranhões."
    checar(corpus.faceta_do_pedaco([raiz, "2. Riscos Excluídos"], corpo) == "exclusao",
           "🔴 a folha manda: a faceta é `exclusao`",
           str(corpus.faceta_do_pedaco([raiz, "2. Riscos Excluídos"], corpo)))
    checar(corpus.faceta_do_pedaco([raiz, "3. Franquia"], corpo) == "franquia",
           "a mesma raiz com folha de franquia dá `franquia`")

    # CONTROLE — a RAIZ sozinha dá `escopo`. É essa diferença que prova que a
    # direção da leitura importa: quem lê da raiz para a folha rotularia as
    # exclusões inteiras como escopo, e "por que negaram?" perderia o trecho
    # que responde.
    checar(corpus.faceta_do_pedaco([raiz], corpo) == "escopo",
           "CONTROLE: a raiz sozinha é `escopo` — a direção é o que decide",
           str(corpus.faceta_do_pedaco([raiz], corpo)))

    # CONTROLE 2 — o classificador CONSEGUE não achar, e `None` nunca elimina.
    checar(corpus.faceta_do_pedaco(["ANEXO IV"], "Tabela de valores. 630 882 1054")
           is None,
           "CONTROLE 2: sem pista, a faceta é None (e None passa em todo filtro)")

    # CONTROLE 3 — as 8 facetas da §5.1, e nenhuma nona.
    nomes = {n for n, _ in corpus._FACETAS}
    checar(nomes == {"escopo", "exclusao", "limite", "franquia", "carencia",
                     "prazo", "documento", "definicao"},
           "CONTROLE 3: são exatamente as 8 da Circular SUSEP 621/2021",
           str(sorted(nomes)))


def teste_o_payload_da_53_chega_na_raiz_pedaco_a_pedaco():
    print("\n[9] O que filtra tem de estar na RAIZ, e `unit_id` muda por pedaço")
    fonte = QDRANT.read_text(encoding="utf-8")
    checar("isinstance(knowledge_extras, list)" in fonte,
           "`insert_embeddings` aceita um `knowledge_extras` POR PEDAÇO",
           "sem isso `unit_id` e `faceta` só caberiam em `metadata`, "
           "que o filtro não lê")

    corpo = (RAIZ / "app" / "services" / "knowledge" / "insurance_corpus.py") \
        .read_text(encoding="utf-8").split("def _ingerir_sync(")[1].split("\nclass ")[0]
    for campo in ('"namespace"', '"vigente"', '"doc_kind"', '"susep_process"',
                  '"effective_from"', '"unit_id"', '"parent_id"', '"faceta"'):
        checar(campo in corpo, f"e `_ingerir_sync` grava {campo} na raiz")
    checar("knowledge_extras=extras" in corpo,
           "passando a LISTA por pedaço, não um dicionário só")

    # CONTROLE — a busca CONSEGUE não achar.
    checar('"um_campo_que_ninguem_grava"' not in corpo,
           "CONTROLE: a conferência sabe dizer NÃO")

    # CONTROLE 2 — `faceta` só entra quando existe. Chave ausente é o que a
    # §5.1 chama de "passa em todo filtro"; gravar a string "None" a
    # transformaria num rótulo que elimina candidato.
    checar('if p["faceta"] else {}' in corpo,
           "CONTROLE 2: faceta ausente vira chave AUSENTE, não a palavra None")


# ══════════════════════════════════════════════════════════════════════════
# 4. As costuras do maestro
# ══════════════════════════════════════════════════════════════════════════

def teste_a_url_do_registro_oficial_e_tratada_como_arquivo():
    print("\n[10] A fonte oficial não termina em `.pdf` — e é um PDF")
    url = f"{rep2.URL_DOWNLOAD}/508497"
    checar(corpus._e_download_do_registro(url),
           "a URL de download do REP2 é reconhecida como arquivo direto", url)
    checar(".pdf" not in url.lower(),
           "📊 e ela não tem `.pdf` no nome — era por isso que caía no crawler")

    # CONTROLE — a conferência CONSEGUE dizer não.
    checar(not corpus._e_download_do_registro(
        "https://www.portoseguro.com.br/algum/documento"),
        "CONTROLE: uma URL qualquer não é tratada como registro oficial")
    checar(not corpus._e_download_do_registro(None),
           "CONTROLE 2: e `None` também não")

    # 🔴 CONTROLE 3 — a cópia de segurança do prefixo tem de continuar igual à
    # constante de verdade. Cópia sem guarda é a que envelhece sozinha, e esta
    # decide se a fonte oficial é baixada ou entregue ao crawler.
    checar(corpus._PADRAO_DOWNLOAD_REP2 == rep2.URL_DOWNLOAD,
           "CONTROLE 3: a cópia local do prefixo é idêntica à do `susep_rep2`",
           f"{corpus._PADRAO_DOWNLOAD_REP2} × {rep2.URL_DOWNLOAD}")


class BancoDeMentira:
    """Um Supabase de mentira que responde `normative_document_versions`.

    Ele guarda linhas de verdade e sabe filtrá-las. É isso que dá direito de
    afirmar "não achou" quando não achou: sem um duplo capaz de achar, "não
    achou" e "o duplo não sabe procurar" são a mesma frase.
    """

    def __init__(self, linhas):
        self._linhas = list(linhas)
        self._filtros: dict = {}

    def table(self, _nome):
        self._filtros = {}
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self

    def is_(self, campo, _valor):
        self._filtros[campo] = None
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        saida = [dict(l) for l in self._linhas
                 if all(l.get(k) == v for k, v in self._filtros.items())]
        return types.SimpleNamespace(data=saida)


def teste_o_progresso_mora_no_banco_e_nao_no_filesystem():
    print("\n[11] 📊 O arquivo de progresso morreu num deploy e custou 109 min")
    linhas = [{"id": "v-1", "document_id": "doc-1", "version": 2,
               "susep_version_id": "508497", "superseded_at": None,
               "qdrant_doc_id": "norm-doc-1-v2"}]
    achou = maestro._ja_coletado(BancoDeMentira(linhas), "doc-1", "508497")
    checar(achou is not None and achou["version"] == 2,
           "uma versão ABERTA com o `susep_version_id` da SUSEP = já coletado",
           str(achou))

    # CONTROLE — versão diferente na SUSEP: NÃO está coletado. Sem esta linha,
    # um `_ja_coletado` que devolvesse sempre a primeira linha passaria — e o
    # lote pularia justamente o documento que precisava ser atualizado.
    checar(maestro._ja_coletado(BancoDeMentira(linhas), "doc-1", "999999") is None,
           "CONTROLE: com id de download novo, o documento NÃO conta como feito")
    # CONTROLE 2 — versão já superada não vale como progresso.
    superada = [dict(linhas[0], superseded_at="2026-08-08T00:00:00Z")]
    checar(maestro._ja_coletado(BancoDeMentira(superada), "doc-1", "508497") is None,
           "CONTROLE 2: versão fechada não conta — ela não é a de hoje")
    # CONTROLE 3 — de outro documento também não.
    checar(maestro._ja_coletado(BancoDeMentira(linhas), "doc-2", "508497") is None,
           "CONTROLE 3: e a versão de outro documento não conta")

    # 🔴 E o progresso não pode viver num arquivo: o EasyPanel recria o
    # contêiner a cada deploy e leva o filesystem junto.
    fonte = SCRIPT.read_text(encoding="utf-8")
    checar(not re.search(r"\.reindexacao_feita|progresso\.txt|feitos\.txt", fonte),
           "o script NÃO guarda progresso em arquivo")
    checar("normative_document_versions" in fonte,
           "ele lê o progresso de `normative_document_versions`")


def teste_o_script_nao_escolhe_quando_ha_dois_documentos_nossos():
    print("\n[12] Ambiguidade da fonte não vira decisão nossa — nem aqui")
    base = {"id": "a", "product_line": "auto", "doc_kind": "condicoes_gerais"}
    p = maestro.Produto(processo="15414.001055/2004-84", entnome="AZUL",
                        ramo_oficial="05 | AUTOMÓVEL - CASCO", subramo="",
                        product_line="auto")

    p.nosso = [base, dict(base, id="b")]
    alvo, motivo = maestro._documento_alvo(p)
    checar(alvo is None and motivo and "nao escolho" in motivo,
           "🔴 dois documentos nossos com o mesmo processo: o script não escolhe",
           str(motivo))

    # CONTROLE — com UM, ele escolhe. Sem isto, "não escolhe" seria
    # indistinguível de "nunca acha nada".
    p.nosso = [base]
    alvo, motivo = maestro._documento_alvo(p)
    checar(alvo is not None and alvo["id"] == "a" and motivo is None,
           "CONTROLE: com um só, ele resolve", str(alvo))

    # CONTROLE 2 — condições gerais ganham do manual do segurado. 📊 A Azul tem
    # os dois sob o mesmo processo, e o contrato é o que manda no *que é* (§6).
    p.nosso = [dict(base, id="manual", doc_kind="manual_do_segurado"), base]
    alvo, _ = maestro._documento_alvo(p)
    checar(alvo is not None and alvo["id"] == "a",
           "CONTROLE 2: entre manual e condições gerais, vence o contrato",
           str(alvo))

    # CONTROLE 3 — nenhum documento nosso é resposta válida (documento novo).
    p.nosso = []
    alvo, motivo = maestro._documento_alvo(p)
    checar(alvo is None and motivo is None,
           "CONTROLE 3: sem documento nosso não há ambiguidade — só é novo")


def teste_riscos_diversos_sozinho_nao_e_equipamento():
    print("\n[13] 📊 O erro que a primeira rodada real cometeu na minha frente")
    checar(maestro._ramo_de_varejo("01 | RISCOS DIVERSOS",
                                   "OUTROS - NÃO-FINANCEIROS") is None,
           "🔴 `RISCOS DIVERSOS` sem subramo de equipamento NÃO é varejo nosso",
           "senão a CG de um seguro de evento entra etiquetada `equipamentos`")
    checar(maestro._ramo_de_varejo("07 | RISCOS DIVERSOS - FINANCEIROS",
                                   "NÃO APLICÁVEL") is None,
           "e o de aluguel garantido também não")

    # CONTROLE — o subramo certo CASA. Sem esta linha, um filtro que recusasse
    # tudo passaria nas duas asserções acima.
    checar(maestro._ramo_de_varejo("01 | RISCOS DIVERSOS", "EQUIPAMENTOS")
           == "equipamentos",
           "CONTROLE: 📊 `01 | RISCOS DIVERSOS` + subramo EQUIPAMENTOS casa "
           "(110 produtos no dump inteiro)")
    checar(maestro._ramo_de_varejo("05 | AUTOMÓVEL - CASCO", "VALOR DE MERCADO")
           == "auto",
           "CONTROLE 2: e o ramo de auto continua casando")
    checar(maestro._ramo_de_varejo("CAP | MODALIDADE INCENTIVO", "PAGAMENTO ÚNICO")
           is None,
           "CONTROLE 3: capitalização não é seguro e fica de fora")


def main() -> int:
    print("=" * 74)
    print("SÓ ENTRA NO ACERVO O QUE O REGISTRO OFICIAL CONFIRMOU")
    print("=" * 74)
    for teste in (teste_a_resposta_vazia_da_susep_nao_indexa_nada,
                  teste_produto_cancelado_nao_entra,
                  teste_duas_versoes_em_aberto_nao_sao_escolha_nossa,
                  teste_versao_com_data_de_fim_e_revogada,
                  teste_a_ficha_cobre_as_sete_linhas_da_spec,
                  teste_o_unit_id_volta_ao_ponto_por_aritmetica,
                  teste_quem_indexa_e_quem_exporta_contam_igual,
                  teste_a_faceta_e_decidida_da_folha_para_a_raiz,
                  teste_o_payload_da_53_chega_na_raiz_pedaco_a_pedaco,
                  teste_a_url_do_registro_oficial_e_tratada_como_arquivo,
                  teste_o_progresso_mora_no_banco_e_nao_no_filesystem,
                  teste_o_script_nao_escolhe_quando_ha_dois_documentos_nossos,
                  teste_riscos_diversos_sozinho_nao_e_equipamento):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O QUE NÃO PÔDE SER CONFIRMADO NÃO ENTRA — E O QUE ENTRA SABE VOLTAR")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
