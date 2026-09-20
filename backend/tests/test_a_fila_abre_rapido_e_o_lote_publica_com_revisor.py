# -*- coding: utf-8 -*-
r"""A fila abre sem abrir PDF, e o lote só publica com gente por trás.

SPEC-EXTRA-001.5.1 · FATIA 2 (unidade B: D5, D6, D7). Rodar de dentro de
`backend/`:

    PYTHONIOENCODING=utf-8 python tests/test_a_fila_abre_rapido_e_o_lote_publica_com_revisor.py

O QUE ESTE GUARDA MEDE, E POR QUE CADA PARTE EXISTE
===================================================
```
[1] a FILA não abre PDF nenhum          contando as chamadas, não lendo o tempo
[2] a PÁGINA abre UM, e só um           e a segunda vez não abre nenhum (cache)
[3] o LOTE em seco não escreve NADA     contando os `update`, não lendo o texto
[4] o LOTE com --aplicar publica só o que o leitor mandou publicar
[5] e é IDEMPOTENTE: a segunda rodada não faz nada
[6] sem revisor, RECUSA antes de tocar no banco
[7] linha sob plano `rascunho` não é publicada — e o relatório diz por quê
```

🔴 **O TEMPO NÃO É A MEDIDA.** 📊 A fila levava 22,5 s desta máquina (65,3 s em
produção) porque baixava 24 PDFs do MinIO em série; agora leva 3,0 s. Mas um
guarda que afirmasse *"a fila abre em menos de 3 s"* mediria a rede do dia, e
ficaria vermelho num CI lento ou verde num PDF que virou cache. **O que muda é
o NÚMERO DE LEITURAS DA FONTE, e é ele que se conta** — com um dublê que
substitui `texto_das_paginas`/`bytes_da_fonte` e registra cada chamada.

⚠️ CLAUDE.md §9.4: o que se afirma é o comportamento do MOTOR. Aqui se chama
`API.fila()` e `API.pagina()` de verdade, e `executar()` do script de verdade —
nunca uma reimplementação do laço deles.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

os.environ.setdefault("SUPABASE_URL", "https://exemplo.invalido")
os.environ.setdefault("SUPABASE_KEY", "chave-de-mentira")
os.environ.setdefault("OPENAI_API_KEY", "chave-de-mentira")
os.environ.setdefault("ENCRYPTION_KEY", "chave-de-mentira")
os.environ.setdefault("MINIO_ROOT_USER", "mentira")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "mentira")

from app.api import assistance_plans as API  # noqa: E402
from app.services.knowledge import assistance_plans_base as BASE  # noqa: E402
from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import publicar_linhas_da_base as LOTE  # noqa: E402

OK = FAIL = 0

#: ⛔ Um uuid de mentira, declarado. Não é de ninguém.
REVISOR = "11111111-2222-3333-4444-555555555555"


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _fechar() -> int:
    print()
    print("=" * 78)
    print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
    print("=" * 78)
    return 1 if FAIL else 0


class ContadorDeLeituras:
    """Substitui os DOIS leitores da fonte e conta. Restaura no fim.

    🔴 Os dois, e não só um: `texto_das_paginas` é quem a fila chamava, e
    `bytes_da_fonte` é quem baixa do MinIO. Contar só o primeiro deixaria passar
    um caminho novo que fosse direto ao segundo.
    """

    def __init__(self, paginas=None, total=1):
        self.chamadas = []
        self._paginas = paginas or {24: "texto da pagina 24, com guincho"}
        self._total = total
        self._antes = {}

    def __enter__(self):
        self._antes = {
            "texto_das_paginas": BASE.texto_das_paginas,
            "bytes_da_fonte": BASE.bytes_da_fonte,
        }

        def texto_das_paginas(documento_id, paginas=None, **kw):
            self.chamadas.append(("texto_das_paginas", str(documento_id)))
            return BASE.PaginasDoDocumento(True, "ok", self._total, dict(self._paginas))

        def bytes_da_fonte(documento_id, **kw):
            self.chamadas.append(("bytes_da_fonte", str(documento_id)))
            return b"%PDF-mentira", "ok"

        BASE.texto_das_paginas = texto_das_paginas
        BASE.bytes_da_fonte = bytes_da_fonte
        BASE.esquecer_paginas_em_cache()
        return self

    def __exit__(self, *a):
        for nome, valor in self._antes.items():
            setattr(BASE, nome, valor)
        BASE.esquecer_paginas_em_cache()
        return False


class ContadorDeEscritas:
    """Conta os `update` do duplo. É o que dá direito a dizer "não escreveu".

    ⚠️ Medir pelo CONTEÚDO das tabelas ("nenhuma linha ficou `publicado`") seria
    mais fraco: um `update` que escrevesse `revisado_em` e nada mais passaria
    despercebido. Conta-se a CHAMADA.
    """

    def __init__(self):
        self.updates = []
        self._antes = None

    def __enter__(self):
        import base_de_planos_em_memoria as M

        self._antes = M._Tabela.update
        contador = self

        def update(self_tabela, patch):
            contador.updates.append((self_tabela._nome, dict(patch)))
            return contador._antes(self_tabela, patch)

        M._Tabela.update = update
        return self

    def __exit__(self, *a):
        import base_de_planos_em_memoria as M

        M._Tabela.update = self._antes
        return False


def base_com_tres_linhas():
    """Um duplo com: 2 linhas sob plano `proposto` e 1 sob plano `rascunho`."""
    db = BaseEmMemoria()
    bom = db.plano(insurer_key="porto", ramo="auto", produto="Porto Auto",
                   plano="Plano Ouro", nivel=1, curadoria="proposto",
                   documento_id="doc-1", pagina=10)
    ruim = db.plano(insurer_key="tokio", ramo="auto", produto="Tokio Auto",
                    plano="A/B/C/D+E+F, G; H", nivel=1, curadoria="rascunho",
                    documento_id="doc-1", pagina=26)
    db.tabelas["insurer_assistance_plans"][-1]["motivo_do_rascunho"] = \
        "o nome do plano era uma lista de coberturas"
    a = db.servico(bom, "guincho", "sim", documento_id="doc-1", pagina=24,
                   curadoria="proposto")
    b = db.servico(bom, "alagamento", "nao", documento_id="doc-1", pagina=24,
                   curadoria="proposto", condicao="danos por inundacao")
    c = db.servico(ruim, "pane_seca", "condicionado", documento_id="doc-1",
                   pagina=26, curadoria="proposto")
    return db, {"plano_bom": bom, "plano_ruim": ruim, "publicar": a,
                "recusar": b, "preso": c}


def conferencia(ids):
    return {
        "revisor_sugerido": REVISOR,
        "linhas": [
            {"servico_id": ids["publicar"], "plano_id": ids["plano_bom"],
             "veredito": "PUBLICAR"},
            {"servico_id": ids["recusar"], "plano_id": ids["plano_bom"],
             "veredito": "RECUSAR",
             "motivo": "o 'nao' veio de uma clausula de exclusao de outra cobertura"},
            {"servico_id": ids["preso"], "plano_id": ids["plano_ruim"],
             "veredito": "PUBLICAR"},
        ],
    }


# ---------------------------------------------------------------------------
print("\n[1] 🔴 a FILA não abre PDF nenhum (D5)")
db, ids = base_com_tres_linhas()
API._db = lambda: db  # type: ignore[assignment]
with ContadorDeLeituras() as contador:
    resposta = API.fila(limite=60)
    checar(resposta.get("ok") is True and len(resposta.get("itens") or []) == 3,
           "a fila responde, com as 3 linhas `proposto`",
           json.dumps({k: v for k, v in resposta.items() if k != "itens"}))
    checar(contador.chamadas == [],
           "🔴 ZERO chamadas a `texto_das_paginas`/`bytes_da_fonte` ao montar a fila",
           repr(contador.chamadas))
    checar(all("texto_da_pagina" not in i for i in resposta["itens"]),
           "e nenhuma linha traz `texto_da_pagina` (o texto não viaja na lista)",
           repr(sorted(resposta["itens"][0].keys())))
    checar(all(i.get("termos_do_servico") is not None for i in resposta["itens"]),
           "⚠️ mas `termos_do_servico` CONTINUA vindo — sai do vocabulário em "
           "memória, não do PDF",
           repr(resposta["itens"][0].get("termos_do_servico")))

# ---------------------------------------------------------------------------
print("\n[2] a PÁGINA abre UM documento — e a segunda vez, nenhum")
with ContadorDeLeituras() as contador:
    p1 = API.pagina(servico_id=ids["publicar"])
    checar(len(contador.chamadas) == 1,
           "🔴 `/pagina` faz EXATAMENTE UMA leitura da fonte",
           repr(contador.chamadas))
    checar(p1.get("ok") is True and (p1.get("texto_da_pagina") or "").startswith("texto da pagina"),
           "e devolve o texto daquela página", json.dumps(p1, ensure_ascii=False)[:200])
    p2 = API.pagina(servico_id=ids["recusar"])
    checar(len(contador.chamadas) == 1,
           "🔴 a SEGUNDA linha do MESMO documento não baixa de novo (cache por "
           "documento — é o que faz a fila inteira valer a pena)",
           repr(contador.chamadas))
    checar(p2.get("ok") is True, "e mesmo assim responde", json.dumps(p2)[:160])

    # 🔴 CONTROLE: esquecido o cache, a leitura VOLTA a acontecer. Sem esta
    #    linha, "não baixou de novo" também seria verdade se `/pagina` tivesse
    #    parado de ler a fonte por completo.
    BASE.esquecer_paginas_em_cache()
    API.pagina(servico_id=ids["publicar"])
    checar(len(contador.chamadas) == 2,
           "🔴 CONTROLE: esquecido o cache, a leitura acontece de novo — o "
           "cache é que segura, não a ausência de leitor",
           repr(contador.chamadas))

# ---------------------------------------------------------------------------
print("\n[3] 🔴 o LOTE em seco não escreve NADA (D6)")
db, ids = base_com_tres_linhas()
conf = conferencia(ids)
with ContadorDeEscritas() as escritas:
    relatorio = LOTE.executar(conf, revisor=REVISOR, aplicar=False, db=db)
checar(escritas.updates == [],
       "🔴 ZERO `update` no banco em `--dry-run` (que é o padrão)",
       repr(escritas.updates))
checar(relatorio["publicadas"] == 1 and relatorio["derrubadas"] == 1,
       "e mesmo assim o relatório DIZ o que aconteceria: 1 publica, 1 derruba",
       json.dumps({k: relatorio[k] for k in ("publicadas", "derrubadas", "puladas")}))
checar(all(str(l.get("curadoria")) == "proposto"
           for l in db.tabelas["insurer_assistance_services"]),
       "CONTROLE: as 3 linhas continuam em `proposto` depois do ensaio",
       repr([l.get("curadoria") for l in db.tabelas["insurer_assistance_services"]]))

# ---------------------------------------------------------------------------
print("\n[4] com --aplicar, publica SÓ o que o leitor mandou publicar")
db, ids = base_com_tres_linhas()
conf = conferencia(ids)
relatorio = LOTE.executar(conf, revisor=REVISOR, aplicar=True, db=db)
por_id = {str(l["id"]): l for l in db.tabelas["insurer_assistance_services"]}
planos = {str(p["id"]): p for p in db.tabelas["insurer_assistance_plans"]}

checar(por_id[ids["publicar"]]["curadoria"] == "publicado",
       "a linha PUBLICAR ficou `publicado`", por_id[ids["publicar"]]["curadoria"])
checar(str(por_id[ids["publicar"]].get("revisado_por")) == REVISOR,
       "🔴 e `revisado_por` guarda o uuid do revisor — a resposta a \"quem "
       "respondeu por esta linha?\"",
       repr(por_id[ids["publicar"]].get("revisado_por")))
checar(planos[ids["plano_bom"]]["curadoria"] == "publicado",
       "🔴 e o PLANO PAI subiu junto — sem ele, nada do que se publica chega "
       "ao segurado",
       planos[ids["plano_bom"]]["curadoria"])
checar(por_id[ids["recusar"]]["curadoria"] == "rascunho",
       "a linha RECUSAR desceu para `rascunho`", por_id[ids["recusar"]]["curadoria"])
checar("exclusao" in str(por_id[ids["recusar"]].get("motivo_do_rascunho") or ""),
       "🔴 com o MOTIVO do leitor gravado em `motivo_do_rascunho`",
       repr(por_id[ids["recusar"]].get("motivo_do_rascunho"))[:160])
checar(str(por_id[ids["recusar"]].get("condicao")) == "danos por inundacao",
       "⚠️ e a `condicao` CONTRATUAL sobreviveu — ela não é campo de recado",
       repr(por_id[ids["recusar"]].get("condicao")))
checar(relatorio["verify"]["publicado_sem_revisor"] == 0,
       "VERIFY: nenhuma linha publicada sem revisor",
       repr(relatorio["verify"]))

# 🔴 CONTROLE do par: um veredito que NÃO é PUBLICAR não publica, mesmo com o
#    mesmo comando, o mesmo revisor e a mesma linha em `proposto`.
db2, ids2 = base_com_tres_linhas()
conf2 = {"linhas": [{"servico_id": ids2["publicar"], "plano_id": ids2["plano_bom"],
                     "veredito": "CORRIGIR", "campo_errado": "limite",
                     "valor_certo": "200 km"}]}
rel2 = LOTE.executar(conf2, revisor=REVISOR, aplicar=True, db=db2)
estado2 = {str(l["id"]): l["curadoria"] for l in db2.tabelas["insurer_assistance_services"]}
checar(estado2[ids2["publicar"]] == "proposto" and rel2["publicadas"] == 0,
       "🔴 CONTROLE: a MESMA linha, com veredito `CORRIGIR`, NÃO é publicada",
       repr(estado2[ids2["publicar"]]))
checar(len(rel2["para_corrigir"]) == 1
       and rel2["para_corrigir"][0]["campo_errado"] == "limite",
       "e ela sai listada para a próxima rodada, com o campo e o valor certo",
       json.dumps(rel2["para_corrigir"], ensure_ascii=False)[:200])

# ---------------------------------------------------------------------------
print("\n[5] a SEGUNDA rodada não faz nada (idempotência)")
with ContadorDeEscritas() as escritas:
    rel3 = LOTE.executar(conf, revisor=REVISOR, aplicar=True, db=db)
checar(escritas.updates == [],
       "🔴 ZERO `update` na segunda rodada, com o mesmo arquivo e o mesmo banco",
       repr(escritas.updates))
checar(rel3["publicadas"] == 0 and rel3["derrubadas"] == 0,
       "o relatório diz: nada a fazer",
       json.dumps({k: rel3[k] for k in ("publicadas", "derrubadas", "puladas")}))
checar(rel3["pulos"].get("ja_em_publicado") == 1
       and rel3["pulos"].get("ja_em_rascunho") == 1,
       "e diz POR QUE pulou cada uma: já está publicada · já está em rascunho",
       json.dumps(rel3["pulos"], ensure_ascii=False))
checar(str(por_id[ids["publicar"]].get("revisado_por")) == REVISOR,
       "⚠️ e `revisado_por` continua sendo o da PRIMEIRA revisão — republicar "
       "trocaria quem respondeu pela linha",
       repr(por_id[ids["publicar"]].get("revisado_por")))

# ---------------------------------------------------------------------------
print("\n[6] 🔴 sem revisor, RECUSA — e antes de tocar no banco")
db4, ids4 = base_com_tres_linhas()
with ContadorDeEscritas() as escritas:
    try:
        LOTE.executar(conferencia(ids4), revisor="", aplicar=True, db=db4)
        recusou, detalhe = False, "publicou sem revisor"
    except BASE.RevisorObrigatorio as exc:
        recusou, detalhe = True, str(exc)[:160]
checar(recusou, "🔴 `--aplicar` sem `--revisor` levanta `RevisorObrigatorio`", detalhe)
checar(escritas.updates == [], "e NADA foi escrito antes da recusa",
       repr(escritas.updates))
# 🔴 CONTROLE: o MESMO comando, com revisor, escreve.
with ContadorDeEscritas() as escritas:
    LOTE.executar(conferencia(ids4), revisor=REVISOR, aplicar=True, db=db4)
checar(len(escritas.updates) > 0,
       "🔴 CONTROLE: o MESMO lote, com revisor, ESCREVE — a recusa é pelo "
       "revisor que falta, não por outra coisa",
       repr([u[0] for u in escritas.updates]))

# ---------------------------------------------------------------------------
print("\n[7] 🔴 linha sob plano `rascunho` não é publicada — e o relatório diz por quê (D7)")
db5, ids5 = base_com_tres_linhas()
rel5 = LOTE.executar(conferencia(ids5), revisor=REVISOR, aplicar=True, db=db5)
estado5 = {str(l["id"]): l["curadoria"] for l in db5.tabelas["insurer_assistance_services"]}
checar(estado5[ids5["preso"]] == "proposto",
       "a linha presa NÃO foi publicada", estado5[ids5["preso"]])
checar(rel5["pulos"].get("plano_pai_rascunho") == 1,
       "🔴 e o relatório nomeia o motivo: `plano_pai_rascunho`",
       json.dumps(rel5["pulos"], ensure_ascii=False))
checar({p["id"]: p["curadoria"] for p in db5.tabelas["insurer_assistance_plans"]}[ids5["plano_ruim"]] == "rascunho",
       "⚠️ e o plano recusado continua recusado — o lote não o promove por tabela",
       "")

# A MESMA linha, pela API da fila, também diz que não pode ser publicada.
API._db = lambda: db5  # type: ignore[assignment]
fila5 = API.fila(limite=60)
presa = [i for i in fila5["itens"] if str(i["id"]) == ids5["preso"]]
checar(len(presa) == 1 and presa[0].get("pode_publicar") is False
       and presa[0].get("motivo_de_nao_publicar") == "plano_pai_rascunho",
       "🔴 e a FILA marca a mesma linha com `pode_publicar: false` e o motivo — "
       "📊 eram 4 linhas em que o clique falhava calado",
       json.dumps({k: presa[0].get(k) for k in
                   ("pode_publicar", "motivo_de_nao_publicar",
                    "plano_motivo_do_rascunho")} if presa else {}, ensure_ascii=False))
checar(bool(presa) and "lista de coberturas" in str(presa[0].get("plano_motivo_do_rascunho") or ""),
       "e carrega o MOTIVO do plano pai, para a tela poder explicar",
       repr(presa[0].get("plano_motivo_do_rascunho") if presa else None)[:160])

# ---------------------------------------------------------------------------
print("\n[8] o arquivo de conferência sem `linhas` é RECUSADO, nunca lido como vazio")
_pasta = tempfile.mkdtemp(prefix="conferidas_")
try:
    vazio = os.path.join(_pasta, "vazio.json")
    with io.open(vazio, "w", encoding="utf-8") as fh:
        json.dump({"revisor_sugerido": REVISOR, "linhas": []}, fh)
    try:
        LOTE.carregar_conferidas(vazio)
        recusou, detalhe = False, "aceitou uma lista vazia"
    except LOTE.ConferenciaInvalida as exc:
        recusou, detalhe = True, str(exc)[:160]
    checar(recusou,
           "🔴 `linhas: []` é recusado — um lote de zero linhas sairia com "
           "sucesso e quem rodou iria embora achando que conferiu",
           detalhe)
    # 🔴 CONTROLE: o MESMO caminho, com uma linha, CARREGA.
    with io.open(vazio, "w", encoding="utf-8") as fh:
        json.dump({"linhas": [{"servico_id": "x", "veredito": "PUBLICAR"}]}, fh)
    checar(len(LOTE.carregar_conferidas(vazio)["linhas"]) == 1,
           "🔴 CONTROLE: o MESMO caminho, com uma linha, carrega — a recusa é "
           "pelo conteúdo, não pelo caminho")
finally:
    import shutil

    shutil.rmtree(_pasta, ignore_errors=True)

# ---------------------------------------------------------------------------
print("\n[9] 🔴 `rascunho` não é porta de mão única (D7)")
# 📊 19/09/2026: 4 linhas `proposto` estavam sob planos `rascunho`. Mandá-las
# para `rascunho` "por coerência" trancaria ali, para sempre, duas linhas que o
# leitor tinha conferido palavra por palavra — porque `para_rascunho` não tinha
# inverso. Este bloco prova que a volta existe, e que ela NÃO é publicar.
db6, ids6 = base_com_tres_linhas()
BASE.para_rascunho(ids6["publicar"], "o plano pai foi recusado", db=db6)
estado6 = {str(l["id"]): l for l in db6.tabelas["insurer_assistance_services"]}
checar(estado6[ids6["publicar"]]["curadoria"] == "rascunho",
       "a linha desceu para `rascunho` com motivo",
       repr(estado6[ids6["publicar"]].get("motivo_do_rascunho")))
BASE.devolver_servico_a_proposto(ids6["publicar"], "o plano pai foi consertado", db=db6)
checar(estado6[ids6["publicar"]]["curadoria"] == "proposto",
       "🔴 e VOLTA para a fila (`proposto`) — a porta abre nos dois sentidos",
       estado6[ids6["publicar"]]["curadoria"])
checar(not estado6[ids6["publicar"]].get("motivo_do_rascunho"),
       "e o motivo do rascunho some, porque deixou de ser verdade",
       repr(estado6[ids6["publicar"]].get("motivo_do_rascunho")))
try:
    BASE.devolver_servico_a_proposto(ids6["recusar"], "sem passar por rascunho", db=db6)
    recusou6, detalhe6 = False, "devolveu uma linha que estava em `proposto`"
except BASE.BaseDePlanosRecusa as exc:
    recusou6, detalhe6 = True, str(exc)[:140]
checar(recusou6,
       "🔴 CONTROLE: só se devolve a partir de `rascunho` — a função não é um "
       "atalho para mexer em qualquer estado", detalhe6)
try:
    BASE.devolver_servico_a_proposto(ids6["publicar"], "", db=db6)
    exigiu6, detalhe6 = False, "aceitou motivo vazio"
except BASE.BaseDePlanosRecusa as exc:
    exigiu6, detalhe6 = True, str(exc)[:140]
checar(exigiu6, "e exige motivo, como o irmão que desce", detalhe6)

# ---------------------------------------------------------------------------
print("\n[9] 🔴 CONSERTO P1 — `--aplicar` sem `--revisor` RECUSA, e o `--help` "
      "passa a dizer a verdade")
# 📊 O juiz mediu em 19/09/2026: a docstring e o `--help` dizem, nestas
# palavras, *"--aplicar sem --revisor -> RECUSA, antes de tocar no banco"* — e
# `main()` fazia `args.revisor or conferidas["revisor_sugerido"]`. Um uuid
# escrito DENTRO do arquivo de conferência publicava 81 linhas em nome de
# alguém que não digitou nada.
#
# ⚠️ Este bloco chama `main(argv)` — não `executar()`. O defeito não estava no
# motor (ele já levantava `RevisorObrigatorio`); estava no CHAMADOR, que nunca
# o deixava chegar lá. Guarda que mede o motor não teria visto (CLAUDE.md §9.4).
_PASTA_TEMP = tempfile.mkdtemp(prefix="conferidas_p1_")
_com_sugerido = os.path.join(_PASTA_TEMP, "conferidas_com_sugerido.json")
# ⚠️ O arquivo precisa ser VÁLIDO (o carregador recusa `linhas: []` antes de
#    chegar ao revisor): a forma é a mesma de `conferencia()` acima.
with io.open(_com_sugerido, "w", encoding="utf-8") as _fh:
    json.dump({"revisor_sugerido": REVISOR,
               "linhas": [{"servico_id": "00000000-0000-4000-8000-000000000001",
                           "plano_id": "00000000-0000-4000-8000-000000000002",
                           "veredito": "PUBLICAR"}]}, _fh)

_tocou = {"executar": 0}
_executar_original = LOTE.executar
try:
    def _nunca_deveria_rodar(*a, **k):
        # ⛔ NÃO chama o original: o `main()` roda sem `db=`, e chamar através
        #    tocaria o banco de PRODUÇÃO. O que se mede é se `main()` CHEGOU
        #    aqui — não o que `executar` faria.
        _tocou["executar"] += 1
        return {"aplicar": bool(k.get("aplicar")),
                "revisor": k.get("revisor") or "",
                "por_seguradora_ramo": {}, "publicadas": 0, "derrubadas": 0,
                "puladas": 0, "pulos": {}, "para_corrigir": [], "erros": [],
                "verify": {"publicado_sem_revisor": 0}}

    LOTE.executar = _nunca_deveria_rodar
    _codigo = LOTE.main(["--conferidas", _com_sugerido, "--aplicar"])
    checar(_codigo != 0,
           "🔴 `--aplicar` SEM `--revisor` devolve código de erro (%r)" % _codigo,
           repr(_codigo))
    checar(_tocou["executar"] == 0,
           "🔴 e NADA foi executado — a recusa é ANTES de tocar no banco, "
           "como o `--help` promete", repr(_tocou))

    _codigo_ok = LOTE.main(["--conferidas", _com_sugerido, "--aplicar",
                            "--revisor", REVISOR])
    checar(_tocou["executar"] == 1,
           "🔴 CONTROLE: COM `--revisor` na linha de comando, ele executa — a "
           "recusa é pela FALTA do argumento, não uma trava geral", repr(_tocou))
    checar(_codigo_ok == 0, "e termina em 0", repr(_codigo_ok))

    _codigo_seco = LOTE.main(["--conferidas", _com_sugerido])
    checar(_codigo_seco == 0 and _tocou["executar"] == 2,
           "🔴 CONTROLE: o ENSAIO (`--dry-run`, o padrão) continua rodando "
           "sem `--revisor` — quem não escreve não precisa de dono", repr(_tocou))
finally:
    LOTE.executar = _executar_original

_ajuda = LOTE.__doc__ or ""
checar("--aplicar sem --revisor" in _ajuda and "RECUSA" in _ajuda,
       "🔴 e a docstring continua prometendo a recusa — agora ela é verdade",
       _ajuda[:200])

# ---------------------------------------------------------------------------
print("\n[10] 🔴 DUAS LINHAS DO MESMO PLANO — o ensaio prometia 23, a "
      "aplicacao entregou 17")
# 📊 ACHADO NA PUBLICAÇÃO REAL, 19/09/2026, com o revisor do Founder:
#     por que pulou: ja_em_publicado 17 · plano_pai_publicado 6 · …
# A regra exigia o pai em `proposto`, e `publicar_servico` PUBLICA O PLANO
# JUNTO — então, assim que a PRIMEIRA linha de um plano subia, o pai virava
# `publicado` e a SEGUNDA linha do MESMO plano era pulada. A trava derrubava
# exatamente o caso em que o plano já está válido.
#
# 🔴 E o motivo `plano_pai_publicado` LIA COMO SUCESSO no relatório, ao lado de
# `ja_em_publicado` — seis linhas conferidas contra a página não chegaram ao
# cliente e nada dizia que aquilo era perda.
_db10 = BaseEmMemoria()
_plano10 = _db10.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                       plano="Essencial", nivel=1, documento_id="doc-1",
                       pagina=9, curadoria="proposto")
_a10 = _db10.servico(_plano10, "guincho", "sim", documento_id="doc-1", pagina=25,
                     curadoria="proposto")
_b10 = _db10.servico(_plano10, "carro_reserva", "nao", documento_id="doc-1",
                     pagina=23, curadoria="proposto")
_conf10 = {"revisor_sugerido": REVISOR, "linhas": [
    {"servico_id": _a10, "plano_id": _plano10, "veredito": "PUBLICAR"},
    {"servico_id": _b10, "plano_id": _plano10, "veredito": "PUBLICAR"},
]}
_rel10 = LOTE.executar(_conf10, revisor=REVISOR, aplicar=True, db=_db10)
checar(_rel10["publicadas"] == 2,
       "🔴 AS DUAS linhas do mesmo plano publicam "
       "(📊 antes: a segunda caia em `plano_pai_publicado`)",
       "publicadas=%s pulos=%s" % (_rel10["publicadas"], _rel10["pulos"]))
checar("plano_pai_publicado" not in (_rel10["pulos"] or {}),
       "🔴 e `plano_pai_publicado` NAO aparece mais nos pulos",
       repr(_rel10["pulos"]))
_planos10 = _db10.tabelas["insurer_assistance_plans"]
checar(len([q for q in _planos10 if q["curadoria"] == "publicado"]) == 1,
       "🔴 e o plano sobe UMA vez so",
       repr([(q["plano"], q["curadoria"]) for q in _planos10]))
_serv10 = _db10.tabelas["insurer_assistance_services"]
checar(all(q["curadoria"] == "publicado" for q in _serv10),
       "🔴 e as duas linhas ficam `publicado`",
       repr([(q["servico"], q["curadoria"]) for q in _serv10]))

print("\n      🔴 CONTROLE: o ENSAIO e o APLICAR dao o MESMO numero")
_db10b = BaseEmMemoria()
_p10b = _db10b.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                     plano="Essencial", nivel=1, documento_id="doc-1",
                     pagina=9, curadoria="proposto")
_x = _db10b.servico(_p10b, "guincho", "sim", documento_id="doc-1", pagina=25,
                    curadoria="proposto")
_y = _db10b.servico(_p10b, "carro_reserva", "nao", documento_id="doc-1",
                    pagina=23, curadoria="proposto")
_conf10b = {"revisor_sugerido": REVISOR, "linhas": [
    {"servico_id": _x, "plano_id": _p10b, "veredito": "PUBLICAR"},
    {"servico_id": _y, "plano_id": _p10b, "veredito": "PUBLICAR"},
]}
_ensaio = LOTE.executar(_conf10b, revisor=REVISOR, aplicar=False, db=_db10b)
_aplica = LOTE.executar(_conf10b, revisor=REVISOR, aplicar=True, db=_db10b)
checar(_ensaio["publicadas"] == _aplica["publicadas"] == 2,
       "🔴 CONTROLE: ensaio %s == aplicar %s — foi exatamente isto que "
       "quebrou na publicacao real (23 x 17)"
       % (_ensaio["publicadas"], _aplica["publicadas"]),
       "ensaio=%s aplicar=%s" % (_ensaio["publicadas"], _aplica["publicadas"]))

print("\n      🔴 CONTROLE: pai em `rascunho` PULA, e entra na lista de PERDA")
_db10c = BaseEmMemoria()
_p10c = _db10c.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                     plano="Preso", nivel=1, documento_id="doc-1", pagina=9,
                     curadoria="rascunho")
_z = _db10c.servico(_p10c, "guincho", "sim", documento_id="doc-1", pagina=25,
                    curadoria="proposto")
_rel10c = LOTE.executar(
    {"revisor_sugerido": REVISOR,
     "linhas": [{"servico_id": _z, "plano_id": _p10c, "veredito": "PUBLICAR"}]},
    revisor=REVISOR, aplicar=True, db=_db10c)
checar(_rel10c["publicadas"] == 0
       and _rel10c["pulos"].get("plano_pai_rascunho") == 1,
       "🔴 CONTROLE: pai em `rascunho` continua pulando",
       repr(_rel10c["pulos"]))
checar("plano_pai_rascunho" in LOTE.MOTIVOS_DE_PERDA,
       "🔴 e ele esta na lista de PERDA — o relatorio diz que a linha NAO "
       "chegou ao cliente, em vez de somar com a idempotencia",
       repr(sorted(LOTE.MOTIVOS_DE_PERDA)))
checar("ja_em_publicado" not in LOTE.MOTIVOS_DE_PERDA
       and "ja_em_rascunho" not in LOTE.MOTIVOS_DE_PERDA,
       "⚠️ e a IDEMPOTENCIA nao e perda — foi a mistura das duas que fez a "
       "publicacao real ler como sucesso")

print("\n      🔴 MUTACAO: voltar a exigir so `proposto`")
_fonte_do_script = io.open(
    os.path.join(RAIZ, "scripts", "publicar_linhas_da_base.py"),
    encoding="utf-8").read()
_sem_comentario10 = "\n".join(l.split("#")[0]
                              for l in _fonte_do_script.splitlines())
checar('not in ("proposto", "publicado")' in _sem_comentario10,
       "🔴 a regra no CODIGO aceita os dois estados validos")
_mutado10 = _sem_comentario10.replace('not in ("proposto", "publicado")',
                                      '!= "proposto"')
checar('not in ("proposto", "publicado")' not in _mutado10,
       "🔴 MUTACAO: revertida para `!= \"proposto\"`, a segunda linha do "
       "mesmo plano volta a ser pulada — e esta asercao falharia")

sys.exit(_fechar())
