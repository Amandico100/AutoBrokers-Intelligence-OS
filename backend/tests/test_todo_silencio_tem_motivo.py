# -*- coding: utf-8 -*-
r"""G11 — TODO SILENCIO TEM MOTIVO, E A EXCECAO NAO FURA O TAKEOVER.
SPEC-EXTRA-001.2 BLOCO E (§9.3, §9.4).

🔴 **DOIS defeitos diferentes, e os dois entram aqui.**

**(1) A ORDEM.** `a_ia_deve_calar` consultava a lista de excecoes de telefone
**ANTES** de `pausar_ia` — logo, um numero na lista neutralizava `claimed_by` e
`HUMAN_REQUESTED`: **o robo falava por cima da atendente**. 📊 E
`grep -rn JANELA_SILENCIO_EXCECOES` devolvia **2 linhas, ambas dentro do proprio
motor**: a lista de excecoes nao tinha NENHUM teste. Este e o primeiro.

**(2) P-PILOTO-15.** `pausar_ia` devolvia `False` sempre que `resolvido_em`
estava preenchido: conversa encerrada, reaberta pelo segurado, com a atendente
dentro, **nao ficava protegida**.

**E o buraco do feed.** 📊 Medido em 13/09/2026: **8.574 silencios no meio de
conversa** (26,0% de 32.935 turnos de cliente) contra **6** motivos escritos no
banco inteiro. `anotar_silencio_no_feed` comecava com
`if not foi_a_janela(motivo): return False` — o takeover, a falta de corretora,
as duas falhas fail-closed e a NAO-calada por excecao nao viravam linha nenhuma.

```
 [GE3a] A ORDEM      telefone na lista + `claimed_by` -> CALA. E o PAR: sem
                     takeover, fora da janela -> RESPONDE
 [GE3b] OS MOTIVOS   cada motivo de silencio vira UMA linha no feed, em portugues
 [GE3c] A EXCECAO    a NAO-calada tambem vira linha, com titulo proprio
 [GE3d] UMA POR DIA  1 linha por conversa/classe-de-motivo/dia; motivo DIFERENTE
                     -> linha nova
 [GE3e] P-PILOTO-15  `claimed_at` DEPOIS de `resolvido_em` protege; e o PAR que
                     mantem morto o "calado para sempre" de 05/09
 [GE3f] `fantasma_lid` esta na lista fechada do produto (senao `marcar_fim` levanta)
```

⛔ SEGURANCA: sem rede, sem banco, sem Redis. Telefones 100% sinteticos, e
⛔ **nenhuma frase do feed carrega narrativa do segurado** (CLAUDE.md §7).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_todo_silencio_tem_motivo.py
    ... --so GE3a   ·   ... --mutar   ·   ... --mutar M-E3a
"""
from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

PASS = 0
FAIL = 0

#: ⛔ 100% SINTETICO.
TELEFONE_DE_TESTE = "5511900000001"
OUTRO_TELEFONE = "5511900000002"
EMPRESA = "empresa-A"
CONVERSA = "conv-1"

os.environ["JANELA_SILENCIO_EXCECOES"] = TELEFONE_DE_TESTE

import app.services.o_fim_do_atendimento as F  # noqa: E402


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O DUBLE DO FEED — `log_activity` e o escritor de verdade (CLAUDE.md §5:
# nenhuma tabela de silencio nova). Aqui ele so anota o que recebeu.
# ===========================================================================
FEED = []


async def _log_activity_duble(company_id, category, title, detail=""):
    FEED.append({"company_id": company_id, "category": category,
                 "title": title, "detail": detail})


def _ligar_o_duble_do_feed():
    modulo = types.ModuleType("app.services.activity_log")
    modulo.log_activity = _log_activity_duble
    sys.modules["app.services.activity_log"] = modulo


def _zerar():
    del FEED[:]
    F._SILENCIO_JA_ANOTADO.clear()


_ligar_o_duble_do_feed()


class _DbQueEstoura:
    """`janela_de_mensagens` fail-closed: nao conseguir LER nao e permissao."""

    @property
    def client(self):
        raise RuntimeError("banco fora do ar")


class _DbVazio:
    class _Q:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def order(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            return types.SimpleNamespace(data=[])

    class _C:
        def table(self, _n):
            return _DbVazio._Q()

    client = _C()


def conversa(**extra):
    base = {"id": CONVERSA, "status": "open", "claimed_by": None,
            "claimed_by_name": None, "claimed_at": None, "resolvido_em": None,
            "user_phone": TELEFONE_DE_TESTE}
    base.update(extra)
    return base


# ===========================================================================
# OS GATES
# ===========================================================================
def ge3a():
    _p("\n[GE3a] a ORDEM: a excecao de telefone NAO fura o takeover")
    _zerar()
    calar, motivo = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(claimed_by="u-1", claimed_by_name="Regina")))
    check("🔴 telefone na lista + `claimed_by` -> CALA", calar is True, (calar, motivo))
    check("e o motivo nomeia quem assumiu, em portugues",
          motivo.startswith("Regina assumiu esta conversa"), motivo)

    _zerar()
    calar2, motivo2 = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(status=F.HUMAN_REQUESTED)))
    check("🔴 telefone na lista + HUMAN_REQUESTED -> CALA", calar2 is True,
          (calar2, motivo2))

    # 🔴 O PAR — sem ele, este gate ficaria verde com uma funcao que cala sempre.
    _zerar()
    calar3, motivo3 = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA, conversa=conversa(), n_dias=0))
    check("PAR: sem takeover e com a janela desligada -> RESPONDE",
          calar3 is False and motivo3 == "", (calar3, motivo3))

    # E a excecao continua servindo para o que ela existe: a JANELA.
    _zerar()
    calar4, _ = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA, conversa=conversa(), n_dias=30))
    check("PAR: o telefone de teste continua pulando a janela de N dias",
          calar4 is False, calar4)


def ge3b():
    _p("\n[GE3b] cada motivo de silencio vira UMA linha no feed, em portugues")
    casos = [
        ("takeover", conversa(user_phone=OUTRO_TELEFONE, claimed_by="u-1",
                              claimed_by_name="Regina"), _DbVazio(), EMPRESA),
        ("pedido_de_pessoa", conversa(user_phone=OUTRO_TELEFONE,
                                      status=F.HUMAN_REQUESTED), _DbVazio(), EMPRESA),
        ("falha_ao_ler_o_historico", conversa(user_phone=OUTRO_TELEFONE),
         _DbQueEstoura(), EMPRESA),
    ]
    for classe, conv, db, empresa in casos:
        _zerar()
        calar, motivo = asyncio.run(F.a_ia_deve_calar(
            db, company_id=empresa, conversa=conv, n_dias=30))
        check("[%s] calou" % classe, calar is True, (calar, motivo))
        check("[%s] escreveu UMA linha no feed" % classe, len(FEED) == 1, FEED)
        if FEED:
            check("[%s] a linha e da corretora certa, na categoria certa" % classe,
                  FEED[0]["company_id"] == empresa
                  and FEED[0]["category"] == "atendimentos", FEED[0])
            check("[%s] com o motivo em PORTUGUES, nao um codigo" % classe,
                  FEED[0]["detail"] == motivo and " " in motivo
                  and motivo == motivo.lower() or motivo[0].isupper(), motivo)
            check("[%s] a classe do motivo e a esperada" % classe,
                  F.classe_do_silencio(motivo) == classe,
                  (classe, F.classe_do_silencio(motivo)))

    # A quarta: `pausar_ia` indisponivel -> fail-closed COM linha.
    # ⚠️ O `id` continua legivel de proposito: e o que permite anexar a linha a
    #    uma conversa. Linha sem `id` nao tem onde ser anotada, e isso e outro
    #    caso — o silencio continua acontecendo, e o log do chamador o registra.
    class _ConversaQueEstoura(dict):
        def __init__(self):
            dict.__init__(self, id=CONVERSA)

        def get(self, chave, _padrao=None):
            if chave == "id":
                return CONVERSA
            raise TypeError("linha ilegivel")

    _zerar()
    calar, motivo = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA, conversa=_ConversaQueEstoura()))
    check("[falha_ao_ler_o_takeover] calou (fail-closed)", calar is True, motivo)
    check("[falha_ao_ler_o_takeover] com linha no feed", len(FEED) == 1, FEED)

    # 🔴 A QUINTA, E A DIVERGENCIA DECLARADA: `sem corretora` NAO vira linha, e
    #    nao pode virar — `log_activity` escreve POR `company_id`, e o motivo
    #    desse silencio e justamente nao haver corretora. O motivo continua
    #    voltando ao chamador; o feed e que nao tem onde recebe-lo.
    _zerar()
    calar, motivo = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id="", conversa=conversa()))
    check("[sem_corretora] calou, e o motivo volta ao chamador",
          calar is True and motivo.startswith("sem corretora"), motivo)
    check("⚠️ DECLARADO: sem corretora nao ha feed onde escrever (0 linhas)",
          len(FEED) == 0, FEED)


def ge3c():
    _p("\n[GE3c] a NAO-calada por excecao de telefone tambem vira linha")
    _zerar()
    calar, motivo = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA, conversa=conversa(), n_dias=30))
    check("🔴 respondeu (a excecao vale para a janela)", calar is False, (calar, motivo))
    check("e a NAO-calada deixou UMA linha", len(FEED) == 1, FEED)
    if FEED:
        check("com titulo PROPRIO (nao e um silencio)",
              FEED[0]["title"] == "O agente respondeu mesmo com a conversa pausada",
              FEED[0]["title"])
        check("e a frase explica por que, em portugues",
              FEED[0]["detail"] == F.MOTIVO_EXCECAO_DE_TESTE
              and "teste" in FEED[0]["detail"], FEED[0]["detail"])
    # PAR: telefone FORA da lista nao produz esta linha.
    _zerar()
    asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(user_phone=OUTRO_TELEFONE), n_dias=0))
    check("PAR: telefone fora da lista -> nenhuma linha de excecao", len(FEED) == 0, FEED)


def ge3d():
    _p("\n[GE3d] uma linha por conversa, por CLASSE de motivo, por dia")
    _zerar()
    conv = conversa(user_phone=OUTRO_TELEFONE, claimed_by="u-1",
                    claimed_by_name="Regina")
    asyncio.run(F.a_ia_deve_calar(_DbVazio(), company_id=EMPRESA, conversa=conv))
    asyncio.run(F.a_ia_deve_calar(_DbVazio(), company_id=EMPRESA, conversa=conv))
    asyncio.run(F.a_ia_deve_calar(_DbVazio(), company_id=EMPRESA, conversa=conv))
    check("🔴 tres mensagens do segurado -> UMA linha", len(FEED) == 1, FEED)

    # 🔴 O PAR que o `motivo` na chave existe para garantir: a conversa MUDA de
    #    motivo no mesmo dia, e isso e uma linha NOVA. Antes da SPEC a chave era
    #    so `(empresa, conversa, dia)` e o segundo motivo sumia.
    asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(user_phone=OUTRO_TELEFONE, status=F.HUMAN_REQUESTED)))
    check("PAR: motivo de CLASSE diferente, mesmo dia -> linha NOVA",
          len(FEED) == 2, FEED)
    check("e as duas classes sao diferentes",
          F.classe_do_silencio(FEED[0]["detail"])
          != F.classe_do_silencio(FEED[1]["detail"]),
          [f["detail"] for f in FEED])

    # ⛔ E o nome de quem assumiu NAO entra na chave do memo (seria PII numa
    #    estrutura de processo, e uma chave nova a cada troca de atendente).
    _zerar()
    asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(user_phone=OUTRO_TELEFONE, claimed_by="u-1",
                          claimed_by_name="Regina")))
    asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(user_phone=OUTRO_TELEFONE, claimed_by="u-2",
                          claimed_by_name="Saionara")))
    check("⛔ trocar de atendente nao duplica a linha do dia", len(FEED) == 1, FEED)
    chaves = list(F._SILENCIO_JA_ANOTADO.keys())
    check("⛔ e nenhum nome de pessoa entra na chave do memo",
          all("Regina" not in k and "Saionara" not in k for k in chaves), chaves)


def ge3e():
    _p("\n[GE3e] P-PILOTO-15: a pausa vale sobre a conversa REABERTA")
    encerrada = conversa(claimed_by="u-1", claimed_by_name="Regina",
                         resolvido_em="2026-09-01T10:00:00+00:00",
                         claimed_at="2026-09-01T09:00:00+00:00")
    check("PAR (o defeito de 05/09 continua morto): assumiu ANTES e encerrou "
          "-> a pausa MORRE com o desfecho", F.pausar_ia(encerrada) is False,
          encerrada)

    reaberta = dict(encerrada, claimed_at="2026-11-02T08:00:00+00:00")
    check("🔴 assumiu DEPOIS do desfecho -> a conversa fica PROTEGIDA",
          F.pausar_ia(reaberta) is True, reaberta)

    check("sem `claimed_at` legivel, o comportamento e o de sempre (nao pausa)",
          F.pausar_ia(dict(encerrada, claimed_at="ontem de manha")) is False)
    check("e sem dono nenhum, nao pausa",
          F.pausar_ia(dict(reaberta, claimed_by=None)) is False)
    check("o helper de instantes e estrito (`>`, nao `>=`)",
          F._assumida_depois_do_desfecho("2026-09-01T10:00:00+00:00",
                                         "2026-09-01T10:00:00+00:00") is False)
    check("e ele le o `Z` do PostgREST",
          F._assumida_depois_do_desfecho("2026-11-02T08:00:00Z",
                                         "2026-09-01T10:00:00Z") is True)

    # E a porta inteira concorda com o helper.
    _zerar()
    calar, motivo = asyncio.run(F.a_ia_deve_calar(
        _DbVazio(), company_id=EMPRESA,
        conversa=conversa(**{k: reaberta[k] for k in
                             ("claimed_by", "claimed_by_name", "claimed_at",
                              "resolvido_em")})))
    check("🔴 `a_ia_deve_calar` na conversa reaberta -> CALA, e com linha no feed",
          calar is True and len(FEED) == 1, (calar, motivo, FEED))


def ge3f():
    _p("\n[GE3f] `fantasma_lid` na lista fechada do PRODUTO (M1 e o par no banco)")
    check("a constante existe", F.FANTASMA_LID == "fantasma_lid", F.FANTASMA_LID)
    check("🔴 esta em `MOTIVOS` (senao `marcar_fim` levanta ValueError)",
          F.FANTASMA_LID in F.MOTIVOS, F.MOTIVOS)
    check("e `e_motivo_valido` o aceita", F.e_motivo_valido(F.FANTASMA_LID) is True)
    check("⛔ e NAO e um desfecho de SUCESSO",
          F.FANTASMA_LID not in F.MOTIVOS_DE_SUCESSO, F.MOTIVOS_DE_SUCESSO)
    check("PAR: um motivo inventado continua sendo recusado",
          F.e_motivo_valido("motivo_que_nao_existe") is False)
    # 🔴 O outro lado do par: o script que vai escrever o valor tem de conhece-lo,
    #    senao ele recusa o `--vivo` para sempre.
    fonte = io.open(os.path.join(RAIZ, "scripts",
                                 "migrar_conversas_fantasma_lid.py"),
                    encoding="utf-8").read()
    check("o script das fantasmas ja aceita o valor",
          '"fantasma_lid",\n)' in fonte.replace(" ", "").replace('"fantasma_lid",)', '"fantasma_lid",\n)')
          or '"fantasma_lid"' in fonte.split("MOTIVOS_ACEITOS_PELO_BANCO")[-1][:300],
          "MOTIVOS_ACEITOS_PELO_BANCO nao tem `fantasma_lid`")
    check("e a migration M1 existe, com o valor no CHECK",
          "fantasma_lid" in io.open(
              os.path.join(RAIZ, "supabase", "migrations",
                           "20260914_07_spec_extra001_2_check_fantasma_lid.sql"),
              encoding="utf-8").read())


GATES = {"GE3a": ge3a, "GE3b": ge3b, "GE3c": ge3c, "GE3d": ge3d, "GE3e": ge3e,
         "GE3f": ge3f}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
_ORDEM_NOVA = """    if telefone_e_excecao_da_janela((conversa or {}).get("user_phone")):"""

MUTACOES = [
    # (a) 🔴 A MUTACAO DO CARD: reverter a ORDEM. A excecao volta para antes do
    #     takeover -> o robo fala por cima da atendente. E o estado de ANTES.
    ("M-E3a", "app/services/o_fim_do_atendimento.py",
     "    try:\n        if pausar_ia(conversa or {}):",
     "    if telefone_e_excecao_da_janela((conversa or {}).get(\"user_phone\")):\n"
     "        return False, \"\"\n"
     "    try:\n        if pausar_ia(conversa or {}):",
     "GE3a"),
    # (b) 🔴 o filtro `foi_a_janela` de volta -> so a janela vira linha, e o
    #     takeover, a falta de corretora e as duas falhas somem do feed.
    ("M-E3b", "app/services/o_fim_do_atendimento.py",
     "    empresa = str(company_id or \"\").strip()\n"
     "    conversa = str(conversation_id or \"\").strip()\n"
     "    if not empresa or not conversa or not str(motivo or \"\").strip():",
     "    if not foi_a_janela(motivo):\n        return False\n"
     "    empresa = str(company_id or \"\").strip()\n"
     "    conversa = str(conversation_id or \"\").strip()\n"
     "    if not empresa or not conversa or not str(motivo or \"\").strip():",
     "GE3b"),
    # (c) 🔴 `pausar_ia` volta a ignorar a pausa quando ha `resolvido_em`
    #     -> P-PILOTO-15 renasce.
    ("M-E3c", "app/services/o_fim_do_atendimento.py",
     "        if not _assumida_depois_do_desfecho(assumida_em, desfecho):\n"
     "            return False\n"
     "        return bool(str(dono or \"\").strip())",
     "        return False",
     "GE3e"),
    # (d) a classe sai da chave do memo -> o segundo motivo do dia some do feed.
    ("M-E3d", "app/services/o_fim_do_atendimento.py",
     "    return \"%s:%s:%s:%s\" % (company_id, conversation_id,\n"
     "                            classe_do_silencio(motivo), dia)",
     "    return \"%s:%s:%s\" % (company_id, conversation_id, dia)",
     "GE3d"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `text=True` sozinho decodifica com a codepage do Windows (cp1252) e
        # ESTOURA no primeiro emoji da saida — `r.stdout` volta VAZIO, `falhas`
        # fica vazia, e a mutacao vermelha e contada como verde. Medido em
        # 14/09/2026: M-E3b (4 linhas [FALHOU]) reportada como "NAO deixou
        # vermelho". ⚠️ Um harness que nao le a saida nao mede mutacao nenhuma.
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-e0012g11").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  G11 -- TODO SILENCIO TEM MOTIVO  (SPEC-EXTRA-001.2 E3/E4)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_todo_silencio_tem_motivo():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
