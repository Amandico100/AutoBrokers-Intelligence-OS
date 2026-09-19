# -*- coding: utf-8 -*-
r"""🔴 M-C1 · A EXTRAÇÃO NÃO PUBLICA SEM GENTE.

SPEC-EXTRA-001.5 · BLOCO C (§7.1). O pior desfecho possível desta SPEC não é a
base ficar vazia — é ela encher sozinha. Uma linha `publicado` diz ao segurado
*"seu plano tem carro reserva por 7 dias"* com a autoridade de um contrato. Quem
responde por essa frase é uma pessoa, e o único jeito de garantir isso é que
**nada** no caminho da máquina consiga chegar lá.

```
o extrator PROPÕE      -> 'proposto'
o verificador REPROVA  -> 'rascunho', com o motivo
a pessoa PUBLICA       -> 'publicado' + revisado_por + revisado_em
```

🔴 **O guarda chama o MOTOR** (CLAUDE.md §9.4): roda
`assistance_plans_extractor.processar_documento` de ponta a ponta — com um PDF
de verdade (gerado aqui e lido pelo mesmo `fitz`), um MinIO duplo e um modelo
duplo — e olha o ESTADO das linhas que sobraram no banco. Não há regex sobre o
código; há um documento sendo extraído.

⚠️ E a **linha de controle** é o que dá direito à conclusão: o mesmo duplo, na
mesma rodada, publica quando uma PESSOA manda. Sem ela, "nada ficou publicado"
poderia ser só um duplo que não sabe publicar.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

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


# ---------------------------------------------------------------------------
# O cenário: um PDF DE VERDADE, com duas páginas e frases conhecidas.
# ---------------------------------------------------------------------------
TRECHO_BOM = "O guincho esta incluido ate 200 km por evento, sem carencia."
TRECHO_INVENTADO = "O guincho e ilimitado em todo o territorio nacional."

DOC = "11111111-1111-1111-1111-111111111111"
#: 🔴 o revisor e o ID do usuario autenticado (uuid), nunca um rotulo livre:
#: `revisado_por="robo"` passaria pelo CHECK do banco, que so exige nao nulo.
REVISOR = "11111111-2222-3333-4444-555555555555"


def _pdf_de_duas_paginas() -> bytes:
    import fitz  # o MESMO leitor do corpus

    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((60, 90), "Condicoes gerais - Plano Essencial")
    p1.insert_text((60, 120), TRECHO_BOM)
    p2 = doc.new_page()
    p2.insert_text((60, 90), "Definicoes e glossario.")
    return doc.tobytes()


class MinioDuplo:
    def __init__(self, corpo: bytes) -> None:
        self._corpo = corpo

    def download_file(self, _caminho: str):
        import io

        return io.BytesIO(self._corpo)


class ModeloDuplo:
    """Devolve propostas fixas — uma boa e quatro que o verificador tem de pegar.

    ⚠️ O modelo duplo é o ÚNICO duplo do caminho de decisão: o PDF é real, a
    leitura é a do `fitz`, o verificador é o de produção e a escrita é a do
    contrato da fatia 1.
    """

    def __init__(self) -> None:
        self.chamadas = 0

    def invoke(self, _mensagens):
        self.chamadas += 1
        if self.chamadas > 1:
            return type("R", (), {"content": json.dumps({"linhas": []})})()
        linhas = [
            # ① boa: o trecho ESTÁ na página 1
            {"produto": "Auto Total", "plano": "Essencial", "nivel": 1, "servico": "guincho",
             "coberto": "sim", "limite_valor": 200, "limite_unidade": "km",
             "trecho": TRECHO_BOM, "confianca": "alta"},
            # ② o trecho não está na página (o modelo reescreveu)
            {"produto": "Auto Total", "plano": "Essencial", "nivel": 1, "servico": "carro_reserva",
             "coberto": "sim", "trecho": TRECHO_INVENTADO, "confianca": "media"},
            # ③ serviço fora do vocabulário
            {"produto": "Auto Total", "plano": "Essencial", "nivel": 1, "servico": "spa_do_pet",
             "coberto": "sim", "trecho": TRECHO_BOM, "confianca": "alta"},
            # ④ limite com valor e SEM unidade
            {"produto": "Auto Total", "plano": "Essencial", "nivel": 1, "servico": "vidros",
             "coberto": "sim", "limite_valor": 3, "limite_unidade": None,
             "trecho": TRECHO_BOM, "confianca": "alta"},
            # ⑤ nível duplicado: outro plano no MESMO nível do mesmo produto
            {"produto": "Auto Total", "plano": "Premium", "nivel": 1, "servico": "chaveiro",
             "coberto": "sim", "trecho": TRECHO_BOM, "confianca": "alta"},
        ]
        return type("R", (), {"content": json.dumps({"linhas": linhas})})()


def _banco_com_o_documento() -> BaseEmMemoria:
    db = BaseEmMemoria()
    # 🔴 `effective_from` é obrigatório desde 18/09: a vigência do PLANO é a da
    # VERSÃO do documento, e sem ela o extrator PULA o documento em vez de
    # inventar `date.today()` (que duplicaria a base a cada rodada).
    db.tabelas["normative_document_versions"] = [
        {"document_id": DOC, "version": 1, "storage_ref": "acervo/x.pdf",
         "effective_from": "2019-06-01"}
    ]
    return db


print("\n[0] o vocabulário se acha sozinho — e, sem ele, o erro DIZ onde procurou")
checar(B.caminho_do_vocabulario().is_file() and len(B.servicos_declarados()) > 0,
       "o vocabulário resolve nesta árvore (e tem serviços declarados)",
       str(B.caminho_do_vocabulario()))
_copia = tempfile.mkdtemp(prefix="so_backend_")
try:
    os.makedirs(os.path.join(_copia, "app", "services", "knowledge"), exist_ok=True)
    shutil.copy(os.path.join(RAIZ, "app", "services", "knowledge", "assistance_plans_base.py"),
                os.path.join(_copia, "app", "services", "knowledge", "assistance_plans_base.py"))
    programa = (
        "import importlib.util,sys,os\n"
        "os.environ.pop('AUTOBROKERS_REPO_ROOT', None)\n"
        "spec=importlib.util.spec_from_file_location('apb', r'%s')\n"
        # 🔴 o módulo entra em `sys.modules` ANTES de executar: os `@dataclass`
        # dele resolvem o próprio módulo pelo nome durante o import, e sem isso
        # o erro que aparece é de `dataclasses` — a cópia mentiria sobre o que
        # quebrou, e o guarda ficaria vermelho pelo motivo errado.
        "m=importlib.util.module_from_spec(spec)\nsys.modules['apb']=m\n"
        "spec.loader.exec_module(m)\n"
        "try:\n"
        "    m.vocabulario_de_servicos(); print('ACHOU')\n"
        "except m.VocabularioNaoEncontrado as e: print('ERRO:', e)\n"
        "except Exception as e: print('OUTRO:', type(e).__name__, e)\n"
        % os.path.join(_copia, "app", "services", "knowledge", "assistance_plans_base.py")
    )
    _r = subprocess.run([sys.executable, "-c", programa], capture_output=True, text=True,
                        cwd=_copia)
    saida = (_r.stdout or "").strip() or ("SEM STDOUT | " + (_r.stderr or "")[-1500:])
    # ⚠️ O que se exige é o ERRO CERTO com o caminho ESCRITO — não um caminho em
    # particular. `parents[4]` cai no diretório temporário do sistema, e é
    # exatamente essa a informação que faltava a quem lia `FileNotFoundError` e
    # tinha de refazer a aritmética de `parents[n]`.
    #
    # 🔴 O RÓTULO MUDOU EM 19/09/2026, E A LIÇÃO MIGROU (CLAUDE.md §9.3).
    # Ele dizia *"numa cópia só de `backend/`"*. Desde a SPEC-EXTRA-001.5.1 isso
    # deixou de ser verdade — e é justamente o conserto: o vocabulário mora em
    # `backend/app/data/`, então uma cópia de `backend/` **acha** o arquivo (é o
    # que `test_o_vocabulario_viaja_na_imagem.py` exige). Esta cópia aqui tem UM
    # arquivo só, sem `app/data/`, e o que ela continua provando — a mensagem que
    # NOMEIA onde procurou — segue valendo. Manter a afirmação vencida só
    # ensinaria a ignorar teste.
    checar(saida.startswith("ERRO:") and "servicos-de-assistencia.json" in saida
           and ("/" in saida or "\\" in saida),
           "🔴 numa cópia SEM o vocabulário (nem no pacote, nem em `docs/`), o "
           "erro NOMEIA os caminhos procurados",
           saida[:300])
finally:
    shutil.rmtree(_copia, ignore_errors=True)


print("\n[1] o VERIFICADOR reprova cada defeito, e nomeia qual")
db = _banco_com_o_documento()
minio = MinioDuplo(_pdf_de_duas_paginas())
niveis = {}
propostas = json.loads(ModeloDuplo().invoke(None).content)["linhas"]
for p in propostas:
    p["pagina"] = 1
motivos = [X.verificar(p, insurer="porto", documento_id=DOC, niveis_por_produto=niveis,
                       db=db, minio=minio) for p in propostas]
checar(motivos[0] is None, "🔴 CONTROLE: a proposta cujo trecho ESTÁ na página PASSA",
       repr(motivos[0]))
checar(motivos[1] == "trecho_nao_esta_na_pagina",
       "trecho reescrito pelo modelo -> `trecho_nao_esta_na_pagina`", repr(motivos[1]))
checar(motivos[2] == "servico_fora_do_vocabulario",
       "serviço que não existe -> `servico_fora_do_vocabulario`", repr(motivos[2]))
checar(motivos[3] == "limite_sem_unidade",
       "limite com valor e sem unidade -> `limite_sem_unidade`", repr(motivos[3]))
checar(motivos[4] == "nivel_duplicado",
       "outro plano no MESMO nível do produto -> `nivel_duplicado`", repr(motivos[4]))
checar(X.verificar({"servico": "guincho", "coberto": "sim", "trecho": TRECHO_BOM, "pagina": 99},
                   insurer="porto", documento_id=DOC, niveis_por_produto={},
                   db=db, minio=minio) == "pagina_inexistente",
       "🔴 página que não existe no PDF -> `pagina_inexistente` (o PDF tem 2)")

print("\n[2] a ONDA INTEIRA, pelo motor: nada chega a `publicado`")
db = _banco_com_o_documento()
doc = {"id": DOC, "insurer_key": "porto", "product_line": "auto", "title": "Auto Total",
       "content_hash": "abc", "susep_process": None}
resumo = X.processar_documento(doc, aplicar=True, llm=ModeloDuplo(), db=db,
                               minio=MinioDuplo(_pdf_de_duas_paginas()))
servicos = db.tabelas.get("insurer_assistance_services") or []
planos = db.tabelas.get("insurer_assistance_plans") or []
estados = sorted({str(l.get("curadoria")) for l in servicos + planos})
checar(bool(servicos) and "publicado" not in estados,
       "🔴 depois da onda inteira, NENHUMA linha está `publicado`",
       f"estados={estados} servicos={len(servicos)} planos={len(planos)}")
checar(any(str(l.get("curadoria")) == "proposto" for l in servicos),
       "as aprovadas ficaram `proposto` — a fila que a pessoa vai revisar",
       f"{[l.get('curadoria') for l in servicos]}")
rascunhos = [l for l in servicos if str(l.get("curadoria")) == "rascunho"]
checar(bool(rascunhos) and all("[reprovado]" in str(l.get("condicao") or "") for l in rascunhos),
       "🔴 as reprovadas que o contrato aceita ficaram `rascunho` COM o motivo escrito",
       f"{[l.get('condicao') for l in rascunhos]}")
checar(all(not l.get("revisado_por") for l in servicos),
       "nenhuma linha saiu da máquina com revisor — revisor é pessoa",
       f"{[l.get('revisado_por') for l in servicos]}")
checar(resumo.recusadas.get("servico_fora_do_vocabulario") == 1
       and resumo.recusadas.get("limite_sem_unidade") == 1,
       "as que o contrato recusa nem viraram linha, e foram CONTADAS por motivo",
       str(resumo.recusadas))

print("\n[3] e o caminho para `publicado` não existe neste módulo")
fonte = open(os.path.join(RAIZ, "app", "services", "knowledge",
                          "assistance_plans_extractor.py"), encoding="utf-8").read()
chamadas = [l for l in fonte.splitlines()
            if ("publicar_servico(" in l or "publicar_plano(" in l) and "#" not in l.split("publicar")[0]]
checar(not chamadas, "🔴 o extrator NÃO chama `publicar_servico`/`publicar_plano`", str(chamadas))
# 🔴 CONTROLE da varredura: ela CONSEGUE acusar — senão ficaria verde por cegueira.
_mutada = fonte + "\nBASE.publicar_servico('x', 'y')\n"
checar(any("publicar_servico(" in l for l in _mutada.splitlines()[-3:]),
       "🔴 CONTROLE: com a chamada acrescentada, a varredura a ENXERGA")

print("\n[4] 🔴 CONTROLE do duplo: com uma PESSOA, a MESMA base publica")
alvo = [l for l in servicos if str(l.get("curadoria")) == "proposto"][0]
B.publicar_servico(str(alvo["id"]), REVISOR, db=db)
depois = [l for l in db.tabelas["insurer_assistance_services"] if str(l["id"]) == str(alvo["id"])][0]
checar(str(depois.get("curadoria")) == "publicado" and depois.get("revisado_por")
       and depois.get("revisado_em"),
       "🔴 CONTROLE: `publicar_servico` COM revisor publica — logo, o [2] mediu o código, não o duplo",
       f"{depois.get('curadoria')} / {depois.get('revisado_por')}")
try:
    B.publicar_servico(str(alvo["id"]), "", db=db)
    checar(False, "publicar SEM revisor tinha de levantar")
except B.RevisorObrigatorio:
    checar(True, "e publicar SEM revisor continua recusado antes do banco")

print("\n[4b] 🔴 PUBLICAR UMA LINHA PUBLICA O PLANO DELA — senão o segurado não ouve")
# 📊 18/09/2026: a leitura que chega ao segurado parte do PLANO
# (`planos_publicados` -> `buscar_servico`). Um serviço `publicado` pendurado num
# plano `proposto` é INVISÍVEL: o Founder publicava dez linhas pela tela e o
# segurado continuava ouvindo "ainda não sei" — trabalho feito que não aparece.
db4 = BaseEmMemoria()
pid4 = db4.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Essencial",
                 nivel=1, curadoria="proposto")
sid4 = db4.servico(pid4, "guincho", "sim", curadoria="proposto")
antes4 = B.buscar_servico("hdi", "auto", "Auto Total", "Essencial", "guincho", db=db4)
checar(antes4 is None, "   (antes de publicar, a base não responde — controle do par)")
B.publicar_servico(sid4, REVISOR, db=db4)
plano4 = db4.tabelas["insurer_assistance_plans"][0]
checar(str(plano4.get("curadoria")) == "publicado" and plano4.get("revisado_por") == REVISOR,
       "🔴 publicar o serviço publicou o PLANO pai, com o MESMO revisor",
       f"{plano4.get('curadoria')} / {plano4.get('revisado_por')}")
checar(B.buscar_servico("hdi", "auto", "Auto Total", "Essencial", "guincho", db=db4) is not None,
       "🔴 e AGORA `buscar_servico` acha — é isto que chega ao segurado")

# 🔴 CONTROLE do par: serviço publicado com o plano ainda `proposto` (gravado
#    direto no duplo, sem passar pelo módulo) continua INVISÍVEL.
db4b = BaseEmMemoria()
pid4b = db4b.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Essencial",
                   nivel=1, curadoria="proposto")
db4b.servico(pid4b, "guincho", "sim", curadoria="publicado")
checar(B.buscar_servico("hdi", "auto", "Auto Total", "Essencial", "guincho", db=db4b) is None,
       "🔴 CONTROLE: serviço `publicado` sob plano `proposto` NÃO responde")
# 🔴 REPUBLICAR É RECUSADO — senão o segundo clique troca QUEM revisou.
# 📊 18/09: o patch sobrescrevia `revisado_por`/`revisado_em`, e a linha passava a
# dizer que foi a segunda pessoa quem a leu. É a prova de proveniência da base.
_antes_revisor = [l for l in db4.tabelas["insurer_assistance_services"]
                  if str(l["id"]) == str(sid4)][0].get("revisado_por")
try:
    B.publicar_servico(sid4, "99999999-9999-9999-9999-999999999999", db=db4)
    checar(False, "republicar uma linha já publicada tinha de levantar")
except B.BaseDePlanosRecusa as exc:
    checar("já está publicada" in str(exc),
           "🔴 republicar uma linha já publicada é RECUSADO, com o motivo escrito",
           str(exc)[:110])
_depois_revisor = [l for l in db4.tabelas["insurer_assistance_services"]
                   if str(l["id"]) == str(sid4)][0].get("revisado_por")
checar(_antes_revisor == _depois_revisor == REVISOR,
       "🔴 e quem revisou continua sendo quem revisou (nada foi sobrescrito)",
       f"{_antes_revisor} -> {_depois_revisor}")
db4c = BaseEmMemoria()
pid4c = db4c.plano(insurer_key="hdi", ramo="auto", produto="Auto", plano="X", nivel=1,
                   curadoria="proposto")
sid4c = db4c.servico(pid4c, "guincho", "sim", curadoria="rejeitado")
try:
    B.publicar_servico(sid4c, REVISOR, db=db4c)
    checar(False, "publicar a partir de `rejeitado` tinha de levantar")
except B.BaseDePlanosRecusa as exc:
    checar("proposto" in str(exc),
           "🔴 e não se publica a partir de `rejeitado` — desfazer recusa é outro ato")

print("\n[5] §7.4 — o documento MUDOU: as linhas publicadas voltam para a fila")
db5 = _banco_com_o_documento()
pid = db5.plano(insurer_key="porto", ramo="auto", produto="Auto Total", plano="Essencial",
                nivel=1, documento_id=DOC)
sid = db5.servico(pid, "guincho", "sim", documento_id=DOC)
for linha in db5.tabelas["insurer_assistance_services"]:
    linha["revisado_por"] = REVISOR
antes = [l["curadoria"] for l in db5.tabelas["insurer_assistance_services"]]
# 🔴 pelo MOTOR do corpus — a mesma funcao que a ingestao chama quando o
# `content_hash` muda. Chamar `derrubar_para_proposto` direto mediria a base;
# chamar esta mede o ELO, que e o que a mutacao (d) ataca.
from app.services.knowledge.insurance_corpus import devolver_linhas_a_fila  # noqa: E402
n = devolver_linhas_a_fila(DOC, db5, motivo="content_hash mudou")
servico = db5.tabelas["insurer_assistance_services"][0]
plano = db5.tabelas["insurer_assistance_plans"][0]
checar(antes == ["publicado"] and servico["curadoria"] == "proposto"
       and plano["curadoria"] == "proposto",
       "🔴 publicado -> proposto quando o documento muda (plano e servico)",
       f"antes={antes} depois={servico['curadoria']}/{plano['curadoria']} {n}")
checar(len(db5.tabelas["insurer_assistance_services"]) == 1
       and str(sid) == str(servico["id"]),
       "🔴 a linha NAO foi apagada — o trecho e a pagina ja conferidos continuam la")
checar("content_hash mudou" in str(servico.get("condicao") or ""),
       "e o MOTIVO ficou escrito na linha, para quem for revisar",
       repr(servico.get("condicao")))
checar(str(servico.get("revisado_por")) == REVISOR,
       "⚠️ e o revisor anterior e PRESERVADO — e ele que deve ser chamado para reconferir")

print("\n[6] e o gancho esta LIGADO no ponto onde o hash e comparado")
corpus = open(os.path.join(RAIZ, "app", "services", "knowledge", "insurance_corpus.py"),
              encoding="utf-8").read()
pos_hash = corpus.find("novo_hash = _hash(texto)")
pos_queda = corpus.find("devolver_linhas_a_fila(", pos_hash if pos_hash >= 0 else 0)
pos_susep = corpus.find("susep = doc.get(", pos_hash if pos_hash >= 0 else 0)
checar(pos_hash >= 0 and pos_queda > pos_hash and pos_queda < pos_susep,
       "🔴 `devolver_linhas_a_fila` e chamada DEPOIS da comparacao de hash e "
       "ANTES de a ingestao seguir",
       f"hash@{pos_hash} queda@{pos_queda} susep@{pos_susep}")
# 🔴 CONTROLE: a varredura CONSEGUE acusar a ausencia.
_sem = corpus.replace("devolver_linhas_a_fila(", "nada_a_fazer(")
checar(_sem.find("devolver_linhas_a_fila(", pos_hash) == -1,
       "🔴 CONTROLE: sem a chamada, a varredura FICA VERMELHA")

print("\n[7] a VIGÊNCIA do plano é a do DOCUMENTO, nunca a de hoje")
# 📊 18/09/2026: a onda gravou `date.today()` em 38 de 38 planos. A vigência entra
# nas chaves únicas: rodar amanhã DUPLICARIA a base inteira.
db7 = _banco_com_o_documento()
db7.tabelas["normative_document_versions"][0]["effective_from"] = "2021-03-01"
# 🔴 CONTROLE do bloco: documento SEM vigencia nenhuma nao propoe nada — em vez
# de inventar a data de hoje, que e o defeito que se esta consertando.
db_sem = _banco_com_o_documento()
db_sem.tabelas["normative_document_versions"][0].pop("effective_from", None)
r_sem = X.processar_documento(
    {"id": DOC, "insurer_key": "porto", "product_line": "auto", "title": "X",
     "content_hash": "abc"},
    aplicar=True, llm=ModeloDuplo(), db=db_sem, minio=MinioDuplo(_pdf_de_duas_paginas()))
checar(r_sem.motivo == "documento_sem_vigencia"
       and not db_sem.tabelas.get("insurer_assistance_plans"),
       "🔴 CONTROLE: documento sem vigencia NAO propoe nada (nada de `date.today()`)",
       r_sem.motivo)
doc7 = {"id": DOC, "insurer_key": "porto", "product_line": "auto",
        "title": "Auto Total.pdf", "content_hash": "abc", "susep_process": None}
X.processar_documento(doc7, aplicar=True, llm=ModeloDuplo(), db=db7,
                      minio=MinioDuplo(_pdf_de_duas_paginas()))
vigencias = {str(p.get("vigencia_inicio")) for p in db7.tabelas["insurer_assistance_plans"]}
checar(vigencias == {"2021-03-01"},
       "🔴 a vigência é a `effective_from` da versão do documento",
       repr(vigencias))
import datetime as _dt  # noqa: E402
checar(_dt.date.today().isoformat() not in vigencias,
       "🔴 CONTROLE: e NÃO é a data de hoje (era isso que duplicava a base)",
       _dt.date.today().isoformat())

print("\n[8] `produto` e `plano` normalizados — senão o gancho nunca acha o superior")
checar(X.produto_canonico("Bradesco Seguro Residencial CC-RESIDENCIAL POP.pdf")
       == "Bradesco Seguro Residencial",
       "nome de ARQUIVO vira nome de produto legível")
checar(X.produto_canonico("Mapfre condominio") == X.produto_canonico("Mapfre Condominio"),
       "🔴 'Mapfre condominio' e 'Mapfre Condominio' viram UM produto — duas caixas "
       "eram dois produtos, cada um com um nível 1, e o gancho não achava o superior")
checar(X.nome_de_plano_valido("Essencial") == "Essencial",
       "um nome de plano continua sendo um nome de plano")
checar(X.nome_de_plano_valido("Cobertura Basica + Vendaval + Danos Eletricos + Roubo") is None
       and X.nome_de_plano_valido("x" * 70) is None,
       "🔴 e a LISTA de coberturas não é nome de plano (📊 4 dos 38 eram)")

print("\n[9] exclusão de risco dentro de OUTRA cobertura NÃO vira 'nao' do serviço")
# 📊 2 de 6 linhas da amostra: a cláusula de riscos excluídos da cobertura de
# Vendaval/Granizo virou `alagamento = nao` do plano inteiro — e o segurado com
# direito desistiria de acionar.
db9 = _banco_com_o_documento()
minio9 = MinioDuplo(_pdf_de_duas_paginas())
excl = {"servico": "alagamento", "coberto": "nao", "pagina": 1, "produto": "P", "plano": "Y",
        "trecho": "Riscos excluidos: inundacao decorrente de transbordamento de rios."}
checar(X.verificar(excl, insurer="porto", documento_id=DOC, niveis_por_produto={},
                   db=db9, minio=minio9) == "exclusao_de_risco_nao_e_nao_do_servico",
       "🔴 cláusula de exclusão de risco com `coberto=nao` é REPROVADA")
# 🔴 CONTROLE: a negação DO SERVIÇO continua passando por esta regra.
nega = {"servico": "alagamento", "coberto": "nao", "pagina": 1, "produto": "P", "plano": "Y",
        "trecho": "Este plano nao inclui cobertura para alagamento em nenhuma hipotese."}
checar(X.verificar(nega, insurer="porto", documento_id=DOC, niveis_por_produto={},
                   db=db9, minio=minio9) != "exclusao_de_risco_nao_e_nao_do_servico",
       "🔴 CONTROLE: a negação DO SERVIÇO não é barrada por esta regra")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
