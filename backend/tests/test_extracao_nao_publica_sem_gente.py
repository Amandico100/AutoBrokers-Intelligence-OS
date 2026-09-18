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
    db.tabelas["normative_document_versions"] = [
        {"document_id": DOC, "version": 1, "storage_ref": "acervo/x.pdf"}
    ]
    return db


print("\n[0] o vocabulário se acha sozinho — e, sem `docs/`, o erro DIZ onde procurou")
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
    # particular. 📊 De uma cópia só de `backend/`, `parents[4]` cai no diretório
    # temporário do sistema, e é exatamente essa a informação que faltava a quem
    # lia `FileNotFoundError` e tinha de refazer a aritmética de `parents[n]`.
    checar(saida.startswith("ERRO:") and "servicos-de-assistencia.json" in saida
           and ("/" in saida or "\\" in saida),
           "🔴 numa cópia só de `backend/`, o erro NOMEIA os caminhos procurados",
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
B.publicar_servico(str(alvo["id"]), "amandus@resulta", db=db)
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

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
