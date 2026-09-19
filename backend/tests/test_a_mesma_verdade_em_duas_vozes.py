# -*- coding: utf-8 -*-
r"""🔴 A MESMA VERDADE, DUAS VOZES — GATE C da SPEC-EXTRA-001.5.1 (D10, D11).

O que o CORRETOR lê no chat e o que o SEGURADO lê no WhatsApp são o mesmo
veredito, escrito para duas pessoas diferentes.

📊 O DEFEITO, MEDIDO EM 19/09/2026 (antes desta fatia)
======================================================
`_texto()` (`cobertura_e_assistencia.py:232`) montava UM texto só, na voz do
copiloto interno, e `_guard_infocap_policy_final_response` (`nodes.py:305`)
devolvia exatamente esse texto quando a LLM fugia do veredito — **sem saber o
canal**. O segurado recebia, pelo WhatsApp:

```
No plano dele, não. O Essencial da HDI não inclui vidros. (Condições gerais da HDI, p. 23.)
```

Três defeitos numa frase só: fala **sobre** ele em terceira pessoa, cita um
documento que ele não tem, e **não oferece saída nenhuma**.

O QUE ESTE GUARDA MEDE — PELO MOTOR, NUNCA PELA FRASE
=====================================================
```
[1] os SEIS estados × os DOIS canais, por `compose_policy_answer_with_meta`
[2] o do corretor: documento e página SEMPRE que `origem='base'`
[3] o do segurado: ZERO citação · ZERO "dele/dela" · ZERO cozinha ·
    <= 3 frases e <= 450 caracteres (o teto da 001.2)
[4] `nao_coberto` ao segurado SEMPRE oferece o caminho da equipe (OPÇÃO 1)
[5] `nao_sabemos_ainda` != `fonte_indisponivel` nos DOIS canais (M-B1 continua)
[6] o guarda de `nodes.py` com contrato de cliente devolve o texto do SEGURADO
[7] nenhum nome próprio escrito em código — sem fonte, é "nossa equipe"
[9] 🔴 B5 — a voz do segurado contra o DADO REAL da base (SELECT no acervo)
[10] 🔴 AS QUATRO MUTAÇÕES, em cópia do módulo, restauradas por cópia
```

⚠️ **Linha de controle em cada bloco.** Um guarda que só afirma o que o texto
NÃO tem passa por vácuo quando o texto fica vazio: por isso cada bloco prova
também que o texto do corretor **tem** o que o do segurado não pode ter.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.services.policy_answer_composer import compose_policy_answer_with_meta  # noqa: E402
from app.services.skills import cobertura_e_assistencia as SK  # noqa: E402

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


# ---------------------------------------------------------------------------
# A base sintética: um plano de cada coisa, para os SEIS estados existirem
# ---------------------------------------------------------------------------
db = BaseEmMemoria()
AUTO = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                plano="Essencial", nivel=1, documento_id="doc-hdi-auto", pagina=9)
AUTO_TOP = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                    plano="Completo", nivel=2, documento_id="doc-hdi-auto", pagina=9)
db.servico(AUTO, "guincho", "sim", documento_id="doc-hdi-auto", pagina=25,
           limite_valor=200, limite_unidade="km")
db.servico(AUTO, "vidros", "condicionado", documento_id="doc-hdi-auto", pagina=26,
           condicao="só com a cobertura de vidros contratada")
db.servico(AUTO, "carro_reserva", "nao", documento_id="doc-hdi-auto", pagina=23)
db.servico(AUTO_TOP, "carro_reserva", "sim", documento_id="doc-hdi-auto", pagina=24,
           limite_valor=7, limite_unidade="dias")
db.servico(AUTO_TOP, "hospedagem", "sim", documento_id="doc-hdi-auto", pagina=28)


def _pack(ramo="auto", produto="Auto Perfil", plano="Essencial", nivel=1):
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
            "selected": {"insurer_key": pack["insurer_detected"],
                         "product": pack["product_detected"],
                         "policy_number": "1234567890", "numapo": "1234567890",
                         "holder_name": "Cliente Sintetico", "policy_status": "ativa",
                         "active_now": True, "valid_from": "2026-01-01",
                         "valid_to": "2027-01-01"},
            "policy_evidence_pack": pack}


class _BaseQueQuebra(BaseEmMemoria):
    """A base fora do ar — é o que produz `fonte_indisponivel`, o SEXTO."""

    def table(self, nome):  # noqa: D102
        raise RuntimeError("base fora do ar")


#: 💭 A ATENDENTE do teste. ⛔ Ela é uma FIXTURE — o produto não conhece nome
#: nenhum, e o bloco [7] prova isso lendo o código-fonte.
ATENDENTE = "Marina"

#: `(rótulo, pergunta, base, plano contratado, nível)` — um por estado.
CASOS = [
    ("coberto", "tem guincho?", db, "Essencial", 1),
    ("condicionado", "cobre vidro trincado?", db, "Essencial", 1),
    ("nao_coberto", "tem carro reserva?", db, "Essencial", 1),
    ("nao_contratado", "tem hospedagem?", db, "Essencial", 1),
    ("nao_sabemos_ainda", "tem taxi?", db, "Essencial", 1),
    ("fonte_indisponivel", "tem guincho?", _BaseQueQuebra(), "Essencial", 1),
]

#: ⛔ A cozinha. Palavras que existem para quem constrói o produto e não
#: significam nada para quem tem o carro parado na estrada.
COZINHA = re.compile(
    r"(?<![a-zà-ú])(base|sistema|fonte|consulta(?:r|ndo|mos)?|extrator|"
    r"plano publicado|condi[çc][õo]es gerais|cl[áa]usula|ap[óo]lice)"
    r"(?![a-zà-ú])", re.IGNORECASE)
#: ⛔ A citação, em qualquer das formas que o motor sabe escrever.
CITACAO = re.compile(r"(p\.\s*\d|p[áa]g|p[áa]gina|condi[çc][õo]es gerais|documento)",
                     re.IGNORECASE)
#: ⛔ A terceira pessoa. "no plano dele" fala SOBRE o segurado, na cara dele.
TERCEIRA_PESSOA = re.compile(r"(?<![a-zà-ú])(dele|dela|deles|delas)(?![a-zà-ú])",
                             re.IGNORECASE)
#: O caminho da equipe: ou a atendente pelo nome, ou "nossa equipe".
EQUIPE = re.compile(r"(nossa equipe|%s)" % re.escape(ATENDENTE), re.IGNORECASE)


def _frases(texto: str) -> int:
    return len([p for p in re.split(r"[.!?]+", str(texto or "")) if p.strip()])


def _medir(pergunta, base, plano, nivel, *, cliente: bool):
    meta = compose_policy_answer_with_meta(
        question=pergunta, result=_result(_pack(plano=plano, nivel=nivel)),
        db=base, atendente=ATENDENTE, client_facing=cliente)
    return meta


# ---------------------------------------------------------------------------
print("\n[1] os SEIS estados × os DOIS canais, PELO MOTOR")
pares = {}
for rotulo, pergunta, base, plano, nivel in CASOS:
    do_corretor = _medir(pergunta, base, plano, nivel, cliente=False)
    do_segurado = _medir(pergunta, base, plano, nivel, cliente=True)
    estado = (do_corretor.get("cobertura") or {}).get("estado")
    checar(estado == rotulo,
           f"`{rotulo}` foi produzido pelo motor (estado={estado})",
           repr(do_corretor.get("text"))[:200])
    pares[rotulo] = (do_corretor, do_segurado)

print("\n      📊 OS DOZE TEXTOS, como saem do motor:")
for rotulo, (c, s) in pares.items():
    print(f"\n      ── {rotulo} · CORRETOR ──")
    for l in str(c.get("text") or "").splitlines():
        print("        " + l)
    print(f"      ── {rotulo} · SEGURADO ──")
    for l in str(s.get("text") or "").splitlines():
        print("        " + l)

# ---------------------------------------------------------------------------
print("\n[2] o do CORRETOR traz documento e página quando a resposta vem da base")
com_base = [(r, c) for r, (c, _s) in pares.items()
            if (c.get("cobertura") or {}).get("origem") == "base"]
checar(len(com_base) >= 3,
       "🔴 CONTROLE: pelo menos TRÊS casos vieram da BASE — o bloco não passa "
       "por vácuo", repr([r for r, _ in com_base]))
for rotulo, c in com_base:
    pagina = (c.get("cobertura") or {}).get("pagina")
    checar(pagina and ("p. %s" % pagina) in str(c.get("text") or ""),
           f"`{rotulo}` ao corretor cita a página (p. {pagina})",
           str(c.get("text") or "")[:160])

# ---------------------------------------------------------------------------
print("\n[3] o do SEGURADO: zero citação, zero 'dele', zero cozinha, e curto")
for rotulo, (_c, s) in pares.items():
    texto = str(s.get("text") or "")
    achou_cita = CITACAO.search(texto)
    checar(not achou_cita,
           f"`{rotulo}` ao segurado NÃO cita documento/página/condições gerais",
           f"{achou_cita.group(0)!r} em {texto!r}" if achou_cita else "")
    achou_3a = TERCEIRA_PESSOA.search(texto)
    checar(not achou_3a, f"`{rotulo}` ao segurado não diz 'dele/dela'",
           f"{achou_3a.group(0)!r} em {texto!r}" if achou_3a else "")
    achou_cozinha = COZINHA.search(texto)
    checar(not achou_cozinha,
           f"`{rotulo}` ao segurado não usa palavra de cozinha",
           f"{achou_cozinha.group(0)!r} em {texto!r}" if achou_cozinha else "")
    checar(_frases(texto) <= 3 and len(texto) <= 450,
           f"`{rotulo}` ao segurado cabe no WhatsApp "
           f"({_frases(texto)} frases · {len(texto)} caracteres)", texto)
    checar(not re.search(r"R\$", texto),
           f"`{rotulo}` ao segurado não fala em R$", texto)

print("\n      🔴 CONTROLE do [3]: o texto do CORRETOR **tem** o que o do "
      "segurado não pode ter")
cor_nao_coberto = str(pares["nao_coberto"][0].get("text") or "")
checar(bool(CITACAO.search(cor_nao_coberto)),
       "🔴 CONTROLE: o mesmo veredito, ao corretor, CITA — a ausência acima é "
       "do canal, não de um texto vazio", cor_nao_coberto[:160])
checar(bool(TERCEIRA_PESSOA.search(cor_nao_coberto)),
       "🔴 CONTROLE: e ele fala em terceira pessoa ('no plano dele')",
       cor_nao_coberto[:160])

# ---------------------------------------------------------------------------
print("\n[4] 🔴 a OPÇÃO 1 do Founder: o 'não' ao segurado abre um caminho")
for rotulo in ("nao_coberto", "nao_contratado"):
    texto = str(pares[rotulo][1].get("text") or "")
    checar(bool(EQUIPE.search(texto)),
           f"🔴 `{rotulo}` ao segurado oferece a equipe NA MESMA mensagem", texto)
    checar("?" in texto,
           f"e `{rotulo}` termina numa pergunta — a conversa continua", texto)
checar(not EQUIPE.search(str(pares["coberto"][1].get("text") or "")),
       "🔴 CONTROLE: `coberto` ao segurado NÃO chama a equipe — quem tem "
       "cobertura não precisa de intermediário",
       str(pares["coberto"][1].get("text") or ""))

# ---------------------------------------------------------------------------
print("\n[5] M-B1 continua: 'ainda não sabemos' nunca é 'não consegui abrir'")
for i, canal in enumerate(("corretor", "segurado")):
    a = str(pares["nao_sabemos_ainda"][i].get("text") or "").strip()
    b = str(pares["fonte_indisponivel"][i].get("text") or "").strip()
    checar(a and b and a != b,
           f"🔴 no canal do {canal}, os dois textos são DIFERENTES",
           f"nao_sabemos={a[:80]!r}\n        falha={b[:80]!r}")
    for rotulo, texto in (("nao_sabemos_ainda", a), ("fonte_indisponivel", b)):
        baixo = texto.lower()
        checar("não cobre" not in baixo and "nao cobre" not in baixo,
               f"e `{rotulo}` ao {canal} não vira um 'não cobre'", texto)

# ---------------------------------------------------------------------------
print("\n[6] o guarda de `nodes.py` devolve o texto DO CANAL que veio no contrato")
from app.agents.nodes import _guard_infocap_policy_final_response  # noqa: E402
from app.agents.tools.infocap_tool import InfocapPolicyLookupTool  # noqa: E402

for cliente in (False, True):
    meta = _medir("tem carro reserva?", db, "Essencial", 1, cliente=cliente)
    contrato = InfocapPolicyLookupTool._build_policy_response_contract(
        _result(_pack()), str(meta.get("text") or ""),
        meta.get("assistance_policy"), client_facing=cliente, meta=meta)
    # A LLM "fugiu do veredito": disse SIM ao que a base nega.
    fugiu = "Sim, o seu plano tem carro reserva sem problema nenhum."
    saiu = _guard_infocap_policy_final_response(fugiu, contrato)
    esperado = str(meta.get("texto_para_o_segurado" if cliente
                            else "texto_para_o_corretor") or "")
    checar(saiu.strip() and saiu.strip() != fugiu,
           f"client_facing={cliente}: o guarda ANULOU a fuga da LLM", saiu[:120])
    checar(esperado and esperado.strip() in saiu,
           f"🔴 client_facing={cliente}: o texto que sai é o do CANAL certo",
           f"saiu={saiu[:120]!r}\n        esperado={esperado[:120]!r}")
    if cliente:
        achou = CITACAO.search(saiu)
        checar(not achou,
               "🔴 e no WhatsApp ele sai SEM citação — o defeito D10 fechado",
               f"{achou.group(0)!r} em {saiu!r}" if achou else "")

# ---------------------------------------------------------------------------
print("\n[7] ⛔ nenhum nome próprio mora no código (o Founder exigiu)")
_fonte_da_skill = open(SK.__file__, encoding="utf-8").read()
_fonte_dos_prompts = open(
    os.path.join(RAIZ, "app", "core", "prompts.py"), encoding="utf-8").read()
_nomes = ("Regina", "Saionara", "Marina", "Amanda")
_achados = [n for n in _nomes
            if re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % n, _fonte_da_skill)
            or re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % n, _fonte_dos_prompts)]
checar(not _achados,
       "🔴 nenhum nome de pessoa escrito na Skill nem nos prompts", repr(_achados))
sem_nome = _medir("tem carro reserva?", db, "Essencial", 1, cliente=True)
_texto_sem_nome = str(sem_nome.get("text") or "")
checar("nossa equipe" in _texto_sem_nome.lower() or ATENDENTE in _texto_sem_nome,
       "e o gancho sai com a atendente OU com 'nossa equipe' — nunca vazio",
       _texto_sem_nome)
meta_anonima = compose_policy_answer_with_meta(
    question="tem carro reserva?", result=_result(_pack()), db=db,
    atendente=None, client_facing=True)
checar("nossa equipe" in str(meta_anonima.get("text") or "").lower(),
       "🔴 CONTROLE: SEM atendente na corretora, o texto diz 'nossa equipe'",
       str(meta_anonima.get("text") or ""))
checar(ATENDENTE not in str(meta_anonima.get("text") or ""),
       "🔴 e o nome da fixture NÃO aparece — ele veio do parâmetro, não do código",
       str(meta_anonima.get("text") or ""))

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
print("\n[9] 🔴 B5 — a VOZ DO SEGURADO contra o DADO REAL da base")
# 📊 O juiz mediu em 19/09/2026, e o gate acima NÃO pegava: ele usa uma fixture
# de 41 caracteres ("só com a cobertura de vidros contratada"), e a base real é
# outra coisa. Das 25 linhas conferidas como PUBLICAR, 1 estourava 450
# caracteres (495), 1 trazia citação e 3 falavam do "segurado" em terceira
# pessoa; nas 72 em `proposto`, 2 > 450 (a maior com 575), 2 com citação, 7 em
# terceira pessoa e 3 com jargão.
#
# 🔴 O ACERVO VEM DO BANCO, NÃO DA IMAGINAÇÃO (CLAUDE.md §9.4). O SELECT lê
# SÓ os campos de texto da LINHA (`condicao`, `limite_texto`) — dado de produto
# curado, não de pessoa. ⛔ Nenhuma coluna de segurado é tocada.
_DSN = os.environ.get("SUPABASE_DB_URL")
if not _DSN:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(RAIZ, ".env"))
        _DSN = os.environ.get("SUPABASE_DB_URL")
    except Exception:  # noqa: BLE001
        _DSN = None

_linhas_reais = []
if _DSN:
    try:
        import psycopg

        with psycopg.connect(_DSN, autocommit=True,
                             prepare_threshold=None) as _c, _c.cursor() as _cur:
            _cur.execute(
                "select servico, coberto, condicao, limite_texto, limite_valor, "
                "limite_unidade, curadoria from insurer_assistance_services "
                "where curadoria in ('proposto','publicado')")
            _linhas_reais = list(_cur.fetchall())
    except Exception as _exc:  # noqa: BLE001
        print("      \U0001F7E1 banco indisponível (%s) — o bloco [9] usa só o "
              "acervo embutido" % type(_exc).__name__)

#: 💭 Se o banco não responder, o guarda ainda mede — com as FORMAS que o juiz
#: descreveu. ⚠️ São ilustrativas: servem para o guarda não virar no-op, nunca
#: para substituir a medição.
_MOLDES = [
    ("vidros", "condicionado",
     "Cobertura válida somente se o segurado houver contratado a garantia "
     "adicional de vidros, faróis, lanternas e retrovisores, conforme item 4.2 "
     "das Condições Gerais, p. 23, observado o limite de dois acionamentos por "
     "vigência e a franquia prevista na apólice, sendo certo que o segurado "
     "deverá arcar com a diferença quando o valor exceder o limite máximo "
     "indenizável contratado para a referida garantia.", None, None, None, "molde"),
    ("guincho", "condicionado", "o segurado deve acionar a central antes",
     None, None, None, "molde"),
    ("carro_reserva", "condicionado", "só com a franquia paga", None, None, None,
     "molde"),
]
_acervo = _linhas_reais + _MOLDES
print("      📊 acervo medido: %d linha(s) reais + %d molde(s)"
      % (len(_linhas_reais), len(_MOLDES)))

_REGUA_CITACAO = re.compile(
    r"(p\.\s*\d|p[áa]g|p[áa]gina|condi[çc][õo]es gerais|cl[áa]usula|documento)",
    re.IGNORECASE)
_REGUA_TERCEIRA = re.compile(
    r"(?<![a-zà-ú])(segurad[oa]|del[ae]s?)(?![a-zà-ú])", re.IGNORECASE)
_REGUA_COZINHA = re.compile(
    r"(?<![a-zà-ú])(base|sistema|fonte|extrator|ap[óo]lice)(?![a-zà-ú])",
    re.IGNORECASE)


def _frases_do_texto(t):
    return len([p for p in re.split(r"[.!?]+", str(t or "")) if p.strip()])


_violacoes = []
for _linha_real in _acervo:
    (_servico, _coberto, _condicao, _limite_texto, _limite_valor,
     _limite_unidade, _cur) = _linha_real
    _estado = {"sim": "coberto", "nao": "nao_coberto",
               "condicionado": "condicionado"}.get(str(_coberto or ""), "coberto")
    _limite = SK._limite_em_palavras({"limite_texto": _limite_texto,
                                      "limite_valor": _limite_valor,
                                      "limite_unidade": _limite_unidade})
    # 🔴 PELO MOTOR, e pelo canal do SEGURADO.
    _texto_real = SK._texto(_estado, servico=str(_servico or "guincho"),
                            seguradora="HDI", plano="Essencial", pagina=23,
                            limite=_limite, condicao=_condicao,
                            atendente=None, para=SK.SEGURADO)
    _porques = []
    if len(_texto_real) > 450:
        _porques.append("%d caracteres" % len(_texto_real))
    if _frases_do_texto(_texto_real) > 3:
        _porques.append("%d frases" % _frases_do_texto(_texto_real))
    if _REGUA_CITACAO.search(_texto_real):
        _porques.append("citação %r" % _REGUA_CITACAO.search(_texto_real).group(0))
    if _REGUA_TERCEIRA.search(_texto_real):
        _porques.append("3ª pessoa %r" % _REGUA_TERCEIRA.search(_texto_real).group(0))
    if _REGUA_COZINHA.search(_texto_real):
        _porques.append("cozinha %r" % _REGUA_COZINHA.search(_texto_real).group(0))
    if _porques:
        _violacoes.append((str(_servico), _cur, " · ".join(_porques),
                           _texto_real[:120]))

checar(not _violacoes,
       "🔴 as %d linhas do acervo passam pela régua do segurado, PELO MOTOR"
       % len(_acervo),
       "\n        ".join("%s [%s] %s → %r" % v for v in _violacoes[:4]))

print("\n      🔴 CONTROLE do [9]: a régua CONSEGUE reprovar, e a fixture curta "
      "continua inteira")
_bruto = SK._texto("condicionado", servico="vidros", seguradora="HDI",
                   plano="Essencial", pagina=23,
                   condicao=_MOLDES[0][2], atendente=None, para=SK.SEGURADO)
checar("Cobertura válida somente se o segurado" not in _bruto,
       "🔴 CONTROLE: a condição de 495 caracteres NÃO sai crua ao segurado",
       _bruto[:160])
checar("algumas condições do seu contrato" in _bruto and "nossa equipe" in _bruto,
       "e vira a frase genérica HONESTA, com quem confirma", _bruto)
_curto = SK._texto("condicionado", servico="vidros", seguradora="HDI",
                   plano="Essencial", pagina=23,
                   condicao="só com a cobertura de vidros contratada",
                   atendente=None, para=SK.SEGURADO)
checar("só com a cobertura de vidros contratada" in _curto,
       "🔴 CONTROLE: a condição CURTA e limpa continua saindo INTEIRA — a régua "
       "não é uma mordaça", _curto)
_ao_corretor = SK._texto("condicionado", servico="vidros", seguradora="HDI",
                         plano="Essencial", pagina=23, condicao=_MOLDES[0][2],
                         para=SK.CORRETOR)
checar("Cobertura válida somente se o segurado" in _ao_corretor,
       "🔴 e o CORRETOR continua recebendo a condição INTEIRA — é ele quem "
       "precisa do texto contratual", _ao_corretor[:160])

print("\n      🔴 MUTAÇÃO do [9]: a régua desligada")
_regua_original = SK.condicao_que_o_cliente_entende
try:
    SK.condicao_que_o_cliente_entende = lambda c: (str(c or "").strip() or None)
    _mutado = SK._texto("condicionado", servico="vidros", seguradora="HDI",
                        plano="Essencial", pagina=23, condicao=_MOLDES[0][2],
                        atendente=None, para=SK.SEGURADO)
    checar(len(_mutado) > 450 and bool(_REGUA_CITACAO.search(_mutado)),
           "🔴 MUTAÇÃO: sem a régua, a condição real estoura o teto E leva "
           "citação ao WhatsApp (%d caracteres)" % len(_mutado), _mutado[:160])
finally:
    SK.condicao_que_o_cliente_entende = _regua_original

# ---------------------------------------------------------------------------
print("\n[10] 🔴 AS QUATRO MUTAÇÕES — o guarda CONSEGUE ficar vermelho")
# ⚠️ Mutadas em CÓPIA do módulo carregado (`SK`), restauradas por cópia do
# objeto original (protocolo §10). A ÁRVORE não é tocada em momento nenhum.
_originais = {
    "_texto": SK._texto,
    "_texto_ao_segurado": SK._texto_ao_segurado,
    "quem_cuida": SK.quem_cuida,
}


def _com_mutacao(nome, funcao, rotulo, condicao):
    try:
        setattr(SK, nome, funcao)
        meta = _medir("tem carro reserva?", db, "Essencial", 1, cliente=True)
        texto = str(meta.get("text") or "")
        checar(condicao(texto), rotulo, texto[:200])
    finally:
        setattr(SK, nome, _originais[nome])


# (a) o canal é IGNORADO — o motor sempre devolve o texto do corretor
_com_mutacao(
    "_texto",
    lambda *a, **k: _originais["_texto"](*a, **{**k, "para": SK.CORRETOR}),
    "🔴 MUTAÇÃO (a) canal ignorado → o texto do segurado ganha citação "
    "(o guarda ficaria VERMELHO)",
    lambda t: bool(CITACAO.search(t)))

# (b) a citação vaza para o texto do segurado
_com_mutacao(
    "_texto_ao_segurado",
    lambda *a, **k: _originais["_texto_ao_segurado"](*a, **k)
    + " (Condições gerais da HDI, p. 23.)",
    "🔴 MUTAÇÃO (b) citação vazando → o guarda VÊ a citação",
    lambda t: bool(CITACAO.search(t)))

# (c) o "não" ao segurado sem o caminho da equipe
_com_mutacao(
    "_texto_ao_segurado",
    lambda *a, **k: "No seu plano, não entra carro reserva.",
    "🔴 MUTAÇÃO (c) 'não' sem saída → o guarda NÃO acha o caminho da equipe",
    lambda t: not EQUIPE.search(t))

# (d) um nome próprio escrito no código, em vez de vir da fonte única
_com_mutacao(
    "quem_cuida",
    lambda atendente=None: "Regina",
    "🔴 MUTAÇÃO (d) nome hardcoded → aparece um nome que NÃO veio do parâmetro",
    lambda t: "Regina" in t)

# 🔴 CONTROLE das mutações: restaurado, o motor volta ao certo.
_de_volta = str(_medir("tem carro reserva?", db, "Essencial", 1,
                       cliente=True).get("text") or "")
checar(not CITACAO.search(_de_volta) and bool(EQUIPE.search(_de_volta))
       and "Regina" not in _de_volta,
       "🔴 CONTROLE: restauradas as quatro, o texto do segurado volta ao certo",
       _de_volta)

sys.exit(_fechar())
