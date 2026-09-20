# -*- coding: utf-8 -*-
r"""🔴 O CONFERENTE CONCORDA COM O LEITOR — o fio inteiro, do PDF ao veredito.

SPEC-EXTRA-001.5.2 · unidade F. O que este guarda prova:

```
O FIO   bytes de PDF -> BASE.texto_das_paginas (o MESMO fitz de producao)
        -> CONFERENTE.conferir_linha -> veredito
```

🔴 O GUARDA CHAMA O MOTOR (CLAUDE.md §9.4). Nenhuma asserção roda regex sobre a
declaração: o que se afirma é o comportamento de `conferir_linha` sobre o texto
que o `fitz` devolve. E o texto das páginas é montado com **trechos REAIS** do
gabarito de 19/09 (`SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json`), com o acento que
o PDF tem e que o gabarito perdeu — que é o dialeto do §9.4 em pessoa.

PARES: mesma superfície, veredito oposto.

```
trecho na pagina certa      -> CONFERE   |  mesmo trecho em OUTRA pagina -> DIVERGE
limite com unidade na pagina-> ok        |  numero solto, sem unidade    -> diverge
exclusao DENTRO de Vendaval -> diverge   |  recusa do proprio servico    -> ok
```

CONTROLES (§9.3): um conferente que responde sempre `CONFERE` e um que responde
sempre `DIVERGE` têm de **reprovar** no GATE F. Sem isso o gate não é gate.
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)

from app.services.knowledge import assistance_plans_base as B  # noqa: E402
from app.services.knowledge import assistance_plans_conferente as C  # noqa: E402

GABARITO = os.path.join(
    REPO, "docs", "canon", "reports", "SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json")

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
# O acervo: trechos REAIS do gabarito, com o acento que o PDF tem
# ---------------------------------------------------------------------------
def _do_gabarito(servico_id):
    for l in json.load(open(GABARITO, encoding="utf-8"))["linhas"]:
        if l["servico_id"] == servico_id:
            return l
    raise SystemExit("gabarito sem a linha %s" % servico_id)


#: allianz/residencial/eletricista, p.117 — CORRIGIR (campo `plano`).
ELETRICISTA = _do_gabarito("989ffe36-a1e9-460e-a88e-140937d6c1e9")
#: allianz/residencial/alagamento, p.86 — RECUSAR (exclusão dentro de Vendaval).
ALAGAMENTO = _do_gabarito("cd1e5fa2-36a0-4222-b1f2-fb93123e8537")

#: O texto como o PDF o tem: COM acento. 📊 o gabarito guardou sem — e é por
#: isso que `BASE.normalizar_trecho` (a régua do HASH) não serve aqui.
PAGINAS_DO_PDF = {
    1: "Condições Gerais — Allianz Residência\nÍndice e definições.",
    2: ("Assistência Completo\n"
        "Reparos Elétricos. Evento Gerador: Danos elétricos, curto circuito ou "
        "mau funcionamento das tomadas da residência segurada."),
    3: "Página de definições, sem serviço nenhum descrito.",
    4: ("Tabela de limites do plano Essencial\n"
        "Hospedagem / Até R$ 100,00 por evento e R$ 200,00 por Vigência"),
    5: ("Condição Especial 13 — Vendaval, Furacão, Ciclone, Tornado e Granizo\n"
        "Riscos Excluídos: danos por inundação ou alagamento decorrente de "
        "transbordamentos de rios, enchentes."),
    6: ("Carro Reserva\n"
        "Este plano não possui cobertura para carro reserva em caso de pane."),
}


def _pdf_com(paginas):
    """Um PDF de verdade, escrito com o `fitz` que produção usa para LER."""
    import fitz

    doc = fitz.open()
    for numero in sorted(paginas):
        pagina = doc.new_page()
        pagina.insert_textbox(fitz.Rect(40, 40, 555, 780), paginas[numero],
                              fontsize=11, fontname="helv")
    corpo = doc.tobytes()
    doc.close()
    return corpo


def _lidas(corpo):
    """🔴 O MESMO leitor de produção. Nenhum segundo extrator (CLAUDE.md §5)."""
    r = B.texto_das_paginas("documento-de-teste", None, corpo=corpo)
    if not r.ok:
        raise SystemExit("o fio quebrou antes do conferente: %s" % r.motivo)
    return r.paginas


print("=" * 74)
print("  O CONFERENTE CONCORDA COM O LEITOR — SPEC-EXTRA-001.5.2 · unidade F")
print("=" * 74)

CORPO = _pdf_com(PAGINAS_DO_PDF)
PAGINAS = _lidas(CORPO)

print("\n[0] o fio existe: bytes de PDF -> fitz -> texto")
checar(len(PAGINAS) == 6 and "Reparos El" in PAGINAS[2],
       "as 6 páginas do PDF voltaram por `BASE.texto_das_paginas`",
       str(sorted(PAGINAS))[:120])
checar(B.normalizar_trecho(ELETRICISTA["trecho"]) not in B.normalizar_trecho(PAGINAS[2]),
       "🔴 CONTROLE DO DIALETO: a régua do HASH (`normalizar_trecho`) NÃO acha "
       "o trecho sem acento na página com acento — por isso existe outra régua",
       ELETRICISTA["trecho"][:70])

# ---------------------------------------------------------------------------
print("\n[1] PAR — o trecho está NAQUELA página × está em OUTRA")
LINHA_CERTA = {
    "servico": "eletricista", "coberto": "condicionado", "pagina": 2,
    "produto": "Allianz Residência", "plano": "Assistência Completo",
    "trecho": ELETRICISTA["trecho"],
}
v = C.conferir_linha(LINHA_CERTA, PAGINAS)
checar(v.veredito == C.CONFERE,
       "o trecho REAL na página certa -> CONFERE", f"{v.veredito} {v.motivos}")
checar(v.campos["trecho"] == C.OK and v.campos["pagina"] == C.OK,
       "e os campos `trecho` e `pagina` saem `ok`", str(v.campos))

v = C.conferir_linha(dict(LINHA_CERTA, pagina=3), PAGINAS)
checar(v.veredito == C.DIVERGE and v.campos["pagina"] == C.DIVERGE_CAMPO,
       "o MESMO trecho apontando a página 3 -> DIVERGE no campo `pagina`",
       f"{v.veredito} {v.campos}")
checar(any("página 2" in m for m in v.motivos),
       "e o motivo DIZ em qual página o trecho está de verdade", str(v.motivos))

v = C.conferir_linha(dict(LINHA_CERTA, trecho="frase que nao existe em documento nenhum"), PAGINAS)
checar(v.veredito == C.DIVERGE and v.campos["trecho"] == C.DIVERGE_CAMPO,
       "trecho que não está em página NENHUMA -> DIVERGE no campo `trecho` "
       "(defeito diferente de página errada)", str(v.campos))

v = C.conferir_linha(dict(LINHA_CERTA, pagina=99), PAGINAS)
checar(v.veredito == C.DIVERGE and v.campos["pagina"] == C.DIVERGE_CAMPO,
       "página que não existe no PDF -> DIVERGE", str(v.motivos))
checar(C.conferir_linha(LINHA_CERTA, {}).veredito == C.NAO_CONSEGUI,
       "🔴 e PDF que não abriu -> NAO_CONSEGUI, nunca DIVERGE: "
       "'o arquivo falhou' e 'a página não confirma' mandam fazer coisas opostas")

# ---------------------------------------------------------------------------
print("\n[2] PAR — limite com unidade na página × número solto")
LIMITE = {"servico": "hospedagem", "coberto": "sim", "pagina": 4,
          "produto": "Auto Básico", "plano": "Essencial",
          "trecho": "Hospedagem / Ate R$ 100,00 por evento e R$ 200,00 por Vigencia",
          "limite_valor": 100, "limite_unidade": "reais",
          "limite_texto": "Até R$ 100,00 por evento e R$ 200,00 por Vigência"}
v = C.conferir_linha(LIMITE, PAGINAS)
checar(v.campos["limite"] == C.OK,
       "limite com unidade e com os números NA página -> `ok`",
       f"{v.campos} {v.motivos}")

v = C.conferir_linha(dict(LIMITE, limite_valor=300, limite_unidade=None,
                          limite_texto=""), PAGINAS)
checar(v.campos["limite"] == C.DIVERGE_CAMPO and v.veredito == C.DIVERGE,
       "número solto, sem unidade -> `diverge` (💭 '200' vira '200 dias')",
       f"{v.campos} {v.motivos}")

v = C.conferir_linha(dict(LIMITE, limite_valor=None, limite_texto=(
    "CONFORME DESCRITOS NA CLAUSULA 2 - PLANOS, PRODUTOS E LIMITES DA ASSISTENCIA")),
    PAGINAS)
checar(v.campos["limite"] == C.DIVERGE_CAMPO,
       "📊 o limite da HDI que é uma REFERÊNCIA a outra cláusula -> `diverge` "
       "(a fila mostrava limite preenchido e a promessa era vazia)",
       str(v.motivos))

v = C.conferir_linha(dict(LIMITE, limite_valor=750, limite_unidade="reais",
                          limite_texto="Até R$ 750,00 por evento"), PAGINAS)
checar(v.campos["limite"] == C.DIVERGE_CAMPO,
       "número que NÃO está na página -> `diverge`", str(v.motivos))

# ---------------------------------------------------------------------------
print("\n[3] PAR — exclusão DENTRO de outra cobertura × recusa do próprio serviço")
EXCLUSAO = {"servico": "alagamento", "coberto": "nao", "pagina": 5,
            "produto": "Allianz Residência", "plano": "Assistência Completo",
            "trecho": ALAGAMENTO["trecho"]}
v = C.conferir_linha(EXCLUSAO, PAGINAS)
checar(v.campos["coberto"] == C.DIVERGE_CAMPO and v.veredito == C.DIVERGE,
       "📊 'Riscos Excluídos' DENTRO de Vendaval/Granizo -> `coberto` diverge "
       "(o pior erro da SPEC: o segurado desiste de um direito que tem)",
       f"{v.campos} {v.motivos}")

PROPRIA = {"servico": "carro_reserva", "coberto": "nao", "pagina": 6,
           "produto": "Allianz Residência", "plano": "Assistência Completo",
           "trecho": "Este plano não possui cobertura para carro reserva"}
v = C.conferir_linha(PROPRIA, PAGINAS)
checar(v.campos["coberto"] == C.OK,
       "🔴 CONTROLE: a recusa que é MESMO do serviço ('não possui cobertura "
       "para carro reserva') continua sendo um `nao` legítimo -> `ok`",
       f"{v.campos} {v.motivos}")

v = C.conferir_linha(dict(LIMITE, coberto="sim", pagina=5,
                          trecho="Trata-se de coberturas adicionais e opcionais"),
                     PAGINAS)
checar(v.campos["coberto"] == C.DIVERGE_CAMPO,
       "e o 'sim' numa cobertura ADICIONAL E OPCIONAL -> `diverge` "
       "(prometer o que só existe se contratado)", str(v.motivos))

# ---------------------------------------------------------------------------
print("\n[4] o plano e o produto")
v = C.conferir_linha(dict(LINHA_CERTA, plano="Plano único"), PAGINAS)
checar(v.campos["plano"] == C.DIVERGE_CAMPO,
       "📊 'Plano único' é o PLACEHOLDER do extrator, não um nome lido do "
       "documento -> `diverge` (o Bradesco Auto tem 9 planos e virou um)",
       str(v.motivos))
v = C.conferir_linha(dict(LINHA_CERTA, plano="Plano único"), PAGINAS,
                     planos_da_ancora=["Essencial", "Completo", "VIP"])
checar(v.campos["plano"] == C.DIVERGE_CAMPO and "cláusula de planos" in " ".join(v.motivos),
       "com a ÂNCORA (unidade A), o motivo passa a citar a cláusula de planos",
       str(v.motivos))
v = C.conferir_linha(dict(LINHA_CERTA, plano="Completo"), PAGINAS,
                     planos_da_ancora=["Essencial", "Completo", "VIP"])
checar(v.campos["plano"] == C.OK,
       "🔴 CONTROLE: plano QUE ESTÁ na âncora -> `ok` (a âncora consegue "
       "aprovar, senão não seria âncora)", str(v.campos))

for ruim in ("Mapfre residencial — Seguro Residencial Conteúdo_V1.2",
             "Bradesco Seguros Residencial —",
             "Mapfre Residencial — Condições Contratuais V2.9"):
    v = C.conferir_linha(dict(LINHA_CERTA, produto=ruim), PAGINAS)
    checar(v.campos["produto"] == C.DIVERGE_CAMPO,
           "📊 produto medido como nome de ARQUIVO/versão -> `diverge`: %r" % ruim[:44],
           str(v.motivos))
checar(C.conferir_linha(LINHA_CERTA, PAGINAS).campos["produto"] == C.OK,
       "🔴 CONTROLE: um produto lido da capa continua `ok` "
       "(o guarda CONSEGUE aprovar — §9.3)")

# ---------------------------------------------------------------------------
print("\n[5] 🔴 CONTROLE DO GATE — um conferente burro TEM de reprovar")
GAB = json.load(open(GABARITO, encoding="utf-8"))["linhas"]


def _sempre(veredito):
    return [(g, C.Veredito(veredito, {c: (C.DIVERGE_CAMPO if veredito == C.DIVERGE
                                          else C.OK) for c in C.CAMPOS}, [], 1))
            for g in GAB]


m_confere = C.medir(_sempre(C.CONFERE))
m_diverge = C.medir(_sempre(C.DIVERGE))
print("      sempre CONFERE: %d/%d = %.1f%%" % (
    m_confere["linhas_concordantes"], m_confere["linhas"],
    100 * m_confere["concordancia_de_linha"]))
print("      sempre DIVERGE: %d/%d = %.1f%%" % (
    m_diverge["linhas_concordantes"], m_diverge["linhas"],
    100 * m_diverge["concordancia_de_linha"]))
checar(m_confere["linhas_concordantes"] == 25 and m_confere["concordancia_de_linha"] < 0.80,
       "quem responde sempre CONFERE acerta 25/81 (31%) e REPROVA no gate de 80%",
       str(m_confere["concordancia_de_linha"]))
checar(m_diverge["linhas_concordantes"] == 56 and m_diverge["concordancia_de_linha"] < 0.80,
       "quem responde sempre DIVERGE acerta 56/81 (69%) e REPROVA também",
       str(m_diverge["concordancia_de_linha"]))
checar(m_diverge["campos_comparaveis"] == 38,
       "📊 o leitor nomeou o campo errado em 42 linhas; 38 são COMPARÁVEIS — as "
       "outras 4 dizem `condicao`, e o conferente não tem checagem de `condicao` "
       "(o que falta é declarado, não contado como erro)",
       str(m_diverge["campos_comparaveis"]))
checar(C.concorda_no_campo("condicao", C.Veredito(C.DIVERGE, {}, [], 1)) is None,
       "🔴 CONTROLE: um campo que o conferente NÃO olha devolve `None` "
       "(fora do denominador), nunca `False` (dentro, como erro)")

# ---------------------------------------------------------------------------
print("\n[6] 🔴 MUTAÇÃO — a régua da leitura é o que faz o fio funcionar")
_guardada = C._para_leitura
try:
    C._para_leitura = lambda t: B.normalizar_trecho(t).lower()  # sem tirar acento
    v = C.conferir_linha(LINHA_CERTA, PAGINAS)
    checar(v.veredito == C.DIVERGE,
           "trocada `_para_leitura` pela régua do HASH (que mantém acento), a "
           "linha CERTA passa a DIVERGIR — a normalização é load-bearing, "
           "não enfeite", f"{v.veredito} {v.campos}")
finally:
    C._para_leitura = _guardada
checar(C.conferir_linha(LINHA_CERTA, PAGINAS).veredito == C.CONFERE,
       "e, restaurada, volta a CONFERIR")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
