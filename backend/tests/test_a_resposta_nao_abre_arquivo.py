# -*- coding: utf-8 -*-
r"""🔴 A RESPOSTA AO CLIENTE NÃO ABRE ARQUIVO — GATE E20 da SPEC-EXTRA-001.5.1.

O Founder levantou a preocupação, e ela merecia ser provada em vez de
respondida: *"a resposta baixa o PDF da apólice?"*

📊 **Não, e nunca baixou** (proposta §3). O caminho da resposta é: a pergunta
entra, `servico_canonico` reconhece o serviço (um JSON em memória),
`buscar_servico` faz **uma consulta ao Postgres** com índice, e a frase é
montada. **Zero download, zero MinIO, zero chamada ao modelo para consultar a
base.** Quem baixa PDF é outra coisa, e só duas:

```
a TELA DE CURADORIA   baixa a página para quem REVISA   ← é o D5, e foi consertado
o EXTRATOR            baixa UMA vez por documento       ← roda fora do atendimento
```

🔴 **Por que isto precisa de guarda e não de parágrafo.** Um parágrafo não fica
vermelho. Se alguém um dia "melhorar" a resposta lendo o trecho literal da
página para enriquecê-la, o segurado passa a esperar um download de MinIO no
meio de uma conversa de WhatsApp — e ninguém vai ligar a lentidão à mudança.

O QUE ESTE GUARDA MEDE
======================
```
[1] as 30 perguntas REAIS do acervo, pelo MOTOR, com os DOIS leitores da fonte
    substituídos por CONTADORES  ->  ZERO chamadas
[2] nos DOIS canais (corretor e segurado) — a voz muda, o I/O não
[3] 🔴 CONTROLE: `pagina_da_linha`, que é quem DEVE ler, conta 1
[4] 🔴 MUTAÇÃO: a Skill lendo a página na resposta -> o contador ACUSA
```

⚠️ Os leitores são substituídos em CÓPIA (o atributo do módulo) e restaurados no
`__exit__` — a mesma forma do `ContadorDeLeituras` da fatia 2, de onde ele vem.
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.services.knowledge import assistance_plans_base as BASE  # noqa: E402
from app.services.policy_answer_composer import compose_policy_answer_with_meta  # noqa: E402

OK = FAIL = 0


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
    print("=" * 74)
    print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
    print("=" * 74)
    return 1 if FAIL else 0


class ContadorDeLeituras:
    """Os DOIS leitores da fonte, substituídos e contados.

    🔴 Os dois, e não só um: `texto_das_paginas` é quem a fila chama, e
    `bytes_da_fonte` é quem baixa do MinIO. Contar só o primeiro deixaria passar
    um caminho novo que fosse direto ao segundo. (Vem da fatia 2,
    `test_a_fila_abre_rapido_e_o_lote_publica_com_revisor.py:82`.)
    """

    def __init__(self):
        self.chamadas = []
        self._antes = {}

    def __enter__(self):
        self._antes = {"texto_das_paginas": BASE.texto_das_paginas,
                       "bytes_da_fonte": BASE.bytes_da_fonte}

        def texto_das_paginas(documento_id, paginas=None, **kw):
            self.chamadas.append(("texto_das_paginas", str(documento_id)))
            return BASE.PaginasDoDocumento(True, "ok", 1, {23: "texto da pagina 23"})

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


# ---------------------------------------------------------------------------
# O acervo REAL — as mesmas 30 perguntas do guarda M-B2
# ---------------------------------------------------------------------------
CORPUS = os.path.join(RAIZ, "tests", "corpus",
                      "perguntas_de_cobertura_2026-09-17.json")
with open(CORPUS, "r", encoding="utf-8") as fh:
    PERGUNTAS = json.load(fh)["perguntas"]

db = BaseEmMemoria()
AUTO = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                plano="Essencial", nivel=1, documento_id="doc-hdi-auto", pagina=9)
AUTO_TOP = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                    plano="Completo", nivel=2, documento_id="doc-hdi-auto", pagina=9)
RESI = db.plano(insurer_key="hdi", ramo="residencial", produto="Residencial Total",
                plano="Essencial", nivel=1, documento_id="doc-hdi-resi", pagina=7)
db.servico(AUTO, "carro_reserva", "nao", documento_id="doc-hdi-auto", pagina=23)
db.servico(AUTO_TOP, "carro_reserva", "sim", documento_id="doc-hdi-auto", pagina=24,
           limite_valor=7, limite_unidade="dias")
db.servico(AUTO, "guincho", "sim", documento_id="doc-hdi-auto", pagina=25,
           limite_valor=200, limite_unidade="km")
db.servico(AUTO, "vidros", "condicionado", documento_id="doc-hdi-auto", pagina=26,
           condicao="só com a cobertura de vidros contratada")
db.servico(AUTO, "granizo", "sim", documento_id="doc-hdi-auto", pagina=31)
db.servico(RESI, "eletricista", "sim", documento_id="doc-hdi-resi", pagina=12)

RAMO_DA_CATEGORIA = {
    "carro_reserva": ("auto", "Auto Perfil", "Essencial", 1),
    "granizo": ("auto", "Auto Perfil", "Essencial", 1),
    "chaveiro_e_taxi": ("auto", "Auto Perfil", "Essencial", 1),
    "vidros": ("auto", "Auto Perfil", "Essencial", 1),
    "guincho": ("auto", "Auto Perfil", "Essencial", 1),
    "residencia": ("residencial", "Residencial Total", "Essencial", 1),
}


def _pack(ramo, produto, plano, nivel):
    return {
        "source": "infocap", "policy_ref": "999001", "insurer_detected": "hdi",
        "product_detected": produto, "line_kind_detected": ramo,
        "policy_status": "ativa", "active_now": True,
        "valid_from": "2026-01-01", "valid_to": "2027-01-01",
        "coverage_sections": [{"label": "Assistência 24h", "amount": None}],
        "structured_coverage_available": True, "structured_coverage_absent": False,
        "installments": [], "limitations": [],
        "assistance_plan": {"plano": plano, "nivel": nivel, "estado": "contratado"},
    }


def _result(pack):
    return {"ok": True, "status": "found",
            "selected": {"insurer_key": "hdi", "product": pack["product_detected"],
                         "policy_number": "1234567890", "numapo": "1234567890",
                         "holder_name": "Cliente Sintetico", "policy_status": "ativa",
                         "active_now": True, "valid_from": "2026-01-01",
                         "valid_to": "2027-01-01"},
            "policy_evidence_pack": pack}


def _rodar_as_trinta(cliente: bool):
    vereditos = 0
    with ContadorDeLeituras() as contador:
        for item in PERGUNTAS:
            ramo, produto, plano, nivel = RAMO_DA_CATEGORIA[item["categoria"]]
            meta = compose_policy_answer_with_meta(
                question=item["pergunta"],
                result=_result(_pack(ramo, produto, plano, nivel)),
                db=db, atendente=None, client_facing=cliente)
            if (meta.get("cobertura") or {}).get("estado"):
                vereditos += 1
    return contador.chamadas, vereditos


# ---------------------------------------------------------------------------
print(f"\n[1] as {len(PERGUNTAS)} perguntas REAIS, canal do CORRETOR")
chamadas_corretor, vereditos_corretor = _rodar_as_trinta(cliente=False)
checar(chamadas_corretor == [],
       f"🔴 ZERO leituras da fonte em {len(PERGUNTAS)} respostas — nem MinIO, "
       f"nem página, nem PDF", repr(chamadas_corretor[:4]))
checar(vereditos_corretor == len(PERGUNTAS),
       "🔴 CONTROLE: as 30 PRODUZIRAM veredito — a ausência de I/O não é "
       "ausência de resposta", f"{vereditos_corretor}/{len(PERGUNTAS)}")

print("\n[2] as mesmas 30, canal do SEGURADO — a voz muda, o I/O não")
chamadas_segurado, vereditos_segurado = _rodar_as_trinta(cliente=True)
checar(chamadas_segurado == [],
       "🔴 ZERO leituras da fonte também no WhatsApp",
       repr(chamadas_segurado[:4]))
checar(vereditos_segurado == len(PERGUNTAS),
       "🔴 CONTROLE: e as 30 também produziram veredito no canal do segurado",
       f"{vereditos_segurado}/{len(PERGUNTAS)}")

# ---------------------------------------------------------------------------
print("\n[3] 🔴 CONTROLE do contador: quem DEVE ler, lê — e ele conta")
#: ⚠️ `pagina_da_linha(servico_id, db=…)` é a função que a TELA DE CURADORIA
#: chama ao abrir uma linha — é ela que DEVE ler a fonte. O id vem do duplo.
_ID_DE_UMA_LINHA = str(db.tabelas["insurer_assistance_services"][0]["id"])
with ContadorDeLeituras() as contador:
    lido = BASE.pagina_da_linha(_ID_DE_UMA_LINHA, db=db)
checar(len(contador.chamadas) >= 1,
       "🔴 CONTROLE: `pagina_da_linha` (a tela de curadoria) conta "
       f"{len(contador.chamadas)} leitura(s) — o contador CONSEGUE ficar "
       "diferente de zero", repr(contador.chamadas))
checar(bool(lido),
       "e ela devolveu a página — o substituto responde de verdade", repr(lido)[:120])

# ---------------------------------------------------------------------------
print("\n[4] 🔴 MUTAÇÃO: a Skill lendo a página no meio da resposta")
from app.services.skills import cobertura_e_assistencia as SK  # noqa: E402

_texto_original = SK._texto_ao_corretor


def _texto_que_abre_o_pdf(*a, **k):
    """A mutação: 'enriquecer' a resposta com o trecho literal da página."""
    pagina = k.get("pagina")
    if pagina:
        BASE.texto_das_paginas("doc-hdi-auto", [int(pagina)])
    return _texto_original(*a, **k)


try:
    SK._texto_ao_corretor = _texto_que_abre_o_pdf
    chamadas_mutadas, _ = _rodar_as_trinta(cliente=False)
    checar(len(chamadas_mutadas) > 0,
           f"🔴 MUTAÇÃO: com a Skill lendo a página, o contador acusa "
           f"{len(chamadas_mutadas)} leitura(s) — o guarda do [1] ficaria "
           "VERMELHO", repr(chamadas_mutadas[:3]))
finally:
    SK._texto_ao_corretor = _texto_original

chamadas_de_volta, _ = _rodar_as_trinta(cliente=False)
checar(chamadas_de_volta == [],
       "🔴 CONTROLE: restaurada, a resposta volta a ZERO leituras",
       repr(chamadas_de_volta[:3]))

sys.exit(_fechar())
