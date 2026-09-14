# -*- coding: utf-8 -*-
r"""G7 — SLOT JA CONFIRMADO PELO CLIENTE NAO SE PERGUNTA DE NOVO.

SPEC-EXTRA-001.2 BLOCO C (§7.2 e §7.3). Replay ESTRUTURAL do encanador de
10/09: a ficha ja tinha `agua_escorrendo` respondido pelo cliente ("nao, fechei
o registro") e a atendente perguntou a mesma coisa pela terceira vez.

```
ficha com origem  ->  bloco_para_o_prompt      (o MOTOR: "JA CONFIRMADO")
resposta gerada   ->  slots_reperguntados      (o MOTOR, puro)
                  ->  agent_node               (o MOTOR: UMA regeneracao,
                                                depois ENVIA e registra)
```

🔴 O VERMELHO DE PARTIDA (gate zero, AAA §8 / SPEC §12.1) — saida REAL de
14/09/2026, com o codigo ANTES do bloco C, rodando este mesmo arquivo:

```
[GC7a] O bloco do prompt separa 'o cliente disse' de 'veio do sistema de gestao'
  [FALHOU] GC7a EXPLODIU  AttributeError: module
           'app.services.attendance_ficha' has no attribute 'ORIGEM_CLIENTE'
[GC7b] slots_reperguntados ve a pergunta que volta — e so ela
  [FALHOU] GC7b EXPLODIU  AttributeError: ... 'ORIGEM_CLIENTE'
[GC7c] Cada ancora ou E a do corredor, ou casa o texto do produto de onde saiu
  [FALHOU] GC7c EXPLODIU  ImportError: cannot import name
           'ancoras_de_pergunta' from 'app.services.attendance_ficha'
[GC7d] A resposta que repergunta provoca UMA regeneracao — e depois SAI
  [FALHOU] GC7d EXPLODIU  AttributeError: ... 'ORIGEM_CLIENTE'
  0 assercoes verdes - 4 vermelhas
```

⚠️ A ficha NAO TINHA como dizer de onde veio uma confirmacao: `confirmados`
guardava o valor cru. Sem origem, cadastro e boca do cliente valem o mesmo — e
`slots_reperguntados` nem existia.

⚠️ **O dialeto do regex e o do motor** (CLAUDE.md §9.4): as ancoras sao
aplicadas sobre `corridor_playbooks._norm(texto)` com `IGNORECASE|DOTALL` —
o MESMO de `match_ura_step`. Ancora medida num motor e aplicada em outro e
ancora sobre outra coisa.

⛔ SEGURANCA: sem rede, sem banco, sem modelo, sem PII. A ficha e sintetica e
o modelo e um dublê.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_slot_confirmado_nao_se_pergunta.py
    ... --so GC7b   ·   ... --medir   ·   ... --mutar [M-C7a]
"""
from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile

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
MEDIDAS: dict = {}

#: ⛔ SINTETICO. Nenhum dado de segurado real entra num arquivo de teste.
EMPRESA = "empresa-sintetica"
SESSAO = "sessao-sintetica"


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


def _ficha_do_encanador():
    """A ficha do caso de 10/09, em ESTRUTURA — sem uma palavra de gente real."""
    import app.services.attendance_ficha as F

    return F.fundir(F.ficha_vazia(), {
        "ramo": "residencial", "servico": "encanador", "seguradora": "allianz",
        "confirmados": {
            "agua_escorrendo": {"valor": "nao, fechei o registro",
                                "origem": F.ORIGEM_CLIENTE,
                                "em": "2026-09-10T12:00:00+00:00"},
            "titular_nome": {"valor": "Fulano de Tal Sintetico",
                             "origem": F.ORIGEM_SISTEMA_DE_GESTAO,
                             "em": "2026-09-10T12:00:00+00:00"},
            # PAR de compatibilidade: o valor SIMPLES de ontem continua valendo.
            "problema_descricao": "vazamento embaixo da pia",
        },
    }, [])


# --------------------------------------------------------------------- #
# GC7a — o bloco do prompt diz a ORIGEM de cada confirmacao
# --------------------------------------------------------------------- #

def gc7a_o_bloco_diz_de_onde_veio():
    _p("\n[GC7a] O bloco do prompt separa 'o cliente disse' de 'veio do sistema de gestao'")
    import app.services.attendance_ficha as F

    bloco = F.bloco_para_o_prompt(_ficha_do_encanador(), ["telefone_contato"])

    check("o bloco separa o que o CLIENTE disse",
          "não pergunte de novo" in bloco and F.rotulo("agua_escorrendo") in bloco,
          "origem nenhuma: o bloco trata cadastro e cliente igual\n%s" % bloco[:400])
    check("e mostra a resposta dele",
          "fechei o registro" in bloco, bloco[:400])
    check("o que veio do sistema de gestao pode ser CONFIRMADO, nao perguntado do zero",
          "sistema de gestão" in bloco and "confirmar" in bloco,
          "um dado de cadastro pode precisar de confirmacao; um dado que o "
          "segurado disse NAO pode ser perguntado de novo\n%s" % bloco[:600])
    check("o valor simples de ontem continua sendo lido",
          "vazamento embaixo da pia" in bloco,
          "ficha gravada antes desta SPEC nao pode sumir do prompt")
    check("e o que falta continua aparecendo",
          F.rotulo("telefone_contato") in bloco, bloco[:600])


# --------------------------------------------------------------------- #
# GC7b — o motor puro que enxerga a pergunta repetida
# --------------------------------------------------------------------- #

def gc7b_a_pergunta_repetida_e_vista():
    _p("\n[GC7b] slots_reperguntados ve a pergunta que volta — e so ela")
    import app.services.attendance_ficha as F

    ficha = _ficha_do_encanador()

    repetiu = F.slots_reperguntados(
        "Entendi. Só para confirmar: a água ainda está escorrendo?",
        ficha, corredor="encanador")
    check("a terceira pergunta do encanador e vista",
          repetiu == ["agua_escorrendo"], "devolveu %s" % repetiu)

    # PAR — resposta que NAO repergunta. Sem este par, devolver tudo passaria.
    limpa = F.slots_reperguntados(
        "Perfeito. Já vou acionar a assistência e te aviso o protocolo.",
        ficha, corredor="encanador")
    check("resposta que nao repergunta nao acusa nada",
          limpa == [], "devolveu %s" % limpa)

    # PAR — o que veio do sistema de gestao PODE ser confirmado.
    cadastro = F.slots_reperguntados(
        "Só confirmando o nome do titular da apólice, por favor.",
        ficha, corredor="encanador")
    check("dado de cadastro pode ser confirmado sem virar defeito",
          "titular_nome" not in cadastro, "devolveu %s" % cadastro)

    # PAR — slot que o cliente NAO confirmou pode ser perguntado.
    vazia = F.slots_reperguntados(
        "A água ainda está escorrendo?", F.ficha_vazia(), corredor="encanador")
    check("slot nao confirmado pode ser perguntado a vontade",
          vazia == [], "devolveu %s" % vazia)

    # ⚠️ O DIALETO (CLAUDE.md §9.4): as ancoras do corredor sao medidas sobre
    # `_norm` — sem acento e sem o `*` do negrito. Aplicar sobre o texto CRU
    # perderia a mesma frase.
    negrito = F.slots_reperguntados(
        "*A ÁGUA ainda está escorrendo?*", ficha, corredor="encanador")
    check("acento e negrito nao escondem a repeticao",
          negrito == ["agua_escorrendo"],
          "o guarda tem de falar o dialeto de match_ura_step: devolveu %s" % negrito)


# --------------------------------------------------------------------- #
# GC7c — as ancoras sao texto do PRODUTO, nunca da imaginacao
# --------------------------------------------------------------------- #

def gc7c_as_ancoras_vem_do_produto():
    _p("\n[GC7c] Cada ancora ou E a do corredor, ou casa o texto do produto de onde saiu")
    import re

    from app.services import corridor_playbooks as CP
    from app.services.attendance_ficha import ancoras_de_pergunta, slots_do_atendimento

    mapa = ancoras_de_pergunta()
    universo = slots_do_atendimento()
    sem = sorted(s for s in universo if not mapa.get(s))
    medir("ancoras.slots", len(universo))
    medir("ancoras.com_ancora", len(universo) - len(sem))
    medir("ancoras.sem_ancora", len(sem))
    _p("       📊 %d slots · %d com ancora · %d SEM ancora: %s"
       % (len(universo), len(universo) - len(sem), len(sem), sem))

    check("o arquivo de ancoras existe e nao esta vazio",
          len(mapa) > 0 and any(mapa.values()),
          "sem ancora nenhuma o guarda vira carimbo")

    # ================================================================== #
    # \U0001F534 O PRODUTO NAO LE DE `tests/` (J9, 14/09/2026)
    # ================================================================== #
    #
    # As ancoras nasceram como fixture, e `attendance_ficha._ler_ancoras`
    # abria `backend/tests/fixtures/...`. \u26d4 Um diretorio de testes nao tem
    # promessa nenhuma de existir na imagem que roda: no dia em que ele nao
    # for copiado, o fiscal da pergunta repetida se DESLIGA sozinho e em
    # silencio (o `except` da funcao devolve `{}`).
    import os as _os

    from app.services import attendance_ficha as AF

    caminho = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(AF.__file__))),
        "resources", AF._ANCORAS_ARQUIVO)
    check("\U0001F534 o caminho do produto esta sob `app/`, nunca sob `tests/`",
          _os.sep + "app" + _os.sep in caminho
          and _os.sep + "tests" + _os.sep not in caminho, caminho)
    check("e o arquivo existe LA", _os.path.isfile(caminho), caminho)
    fonte = io.open(AF.__file__, encoding="utf-8").read()
    check('\u26d4 `_ler_ancoras` nao monta mais um caminho com "tests"',
          '"tests", "fixtures"' not in fonte,
          "produto que le de tests/ funciona ate alguem enxugar a imagem")
    check("e os TESTES leem do mesmo arquivo (uma copia seria uma 2a verdade)",
          not _os.path.isfile(_os.path.join(RAIZ, "tests", "fixtures",
                                            AF._ANCORAS_ARQUIVO)),
          "sobrou uma copia em tests/fixtures")

    try:
        from app.agents.tools.insurer_dispatch_tool import InsurerDispatchInput
        descricoes = {k: (v.description or "")
                      for k, v in InsurerDispatchInput.model_fields.items()}
    except Exception:  # noqa: BLE001
        descricoes = {}

    orfas, mortas = [], []
    for slot, entradas in mapa.items():
        for e in entradas:
            padrao, origem = e.get("padrao"), e.get("origem")
            if origem == "corredor":
                pb = CP._PLAYBOOKS.get(e.get("playbook") or "")
                # ⚠️ O MESMO nome de passo aparece mais de uma vez no mesmo
                # playbook (a URA repete a tela com outra redação): basta que
                # UM deles ainda declare esta âncora.
                iguais = [s for s in (pb or {}).get("ura_steps") or []
                          if s.get("step") == e.get("passo")
                          and s.get("anchor") == padrao]
                if not iguais:
                    orfas.append((slot, e.get("playbook"), e.get("passo")))
                continue
            fonte = e.get("fonte_texto") or ""
            no_produto = (fonte and fonte in (descricoes.get(slot, "") if origem == "tool"
                                              else CP._COMO_PERGUNTAR.get(slot, "")))
            if not no_produto:
                orfas.append((slot, origem, "texto nao encontrado no produto"))
            elif not re.search(padrao, CP._norm(fonte), re.IGNORECASE | re.DOTALL):
                mortas.append((slot, padrao))

    check("nenhuma ancora de corredor divergiu do playbook que a declara",
          not orfas, "orfas: %s" % orfas[:6])
    check("nenhuma ancora escrita deixou de casar o proprio texto do produto",
          not mortas,
          "ancora que nao casa a frase de onde saiu e ancora imaginada "
          "(CLAUDE.md §9.4): %s" % mortas[:6])


# --------------------------------------------------------------------- #
# GC7d — em producao: UMA regeneracao, e depois ENVIA
# --------------------------------------------------------------------- #

class _ModeloQueRepete:
    """Dublê do LLM. Responde `textos[i]` na i-esima chamada, repetindo o ultimo."""

    def __init__(self, textos):
        self.textos = list(textos)
        self.chamadas = []

    async def ainvoke(self, mensagens, config=None):
        from langchain_core.messages import AIMessage

        self.chamadas.append(mensagens)
        i = min(len(self.chamadas) - 1, len(self.textos) - 1)
        return AIMessage(content=self.textos[i])


def _rodar_turno(textos):
    """Roda o agent_node REAL com a ficha do encanador e um modelo dublê."""
    import app.services.activity_log as AL
    from langchain_core.messages import HumanMessage

    from app.agents import nodes as N

    feed: list = []

    async def _log(company_id, category, title, detail=""):
        feed.append({"company_id": company_id, "category": category,
                     "title": title, "detail": detail})

    modelo = _ModeloQueRepete(textos)
    estado = {
        "messages": [HumanMessage(content="e ai, vem hoje?")],
        "company_id": EMPRESA, "session_id": SESSAO, "user_id": "u",
        "company_config": {}, "agent_data": {"agent_role": "attendance"},
        "system_prompt": "prompt sintetico", "static_prompt": "prompt sintetico",
        "dynamic_context": "", "ficha_atendimento": _ficha_do_encanador(),
    }
    _log_real = AL.log_activity
    AL.log_activity = _log
    try:
        saida = asyncio.run(N.agent_node(estado, None, modelo))
    finally:
        AL.log_activity = _log_real
    texto = ""
    for m in saida.get("messages") or []:
        texto = getattr(m, "content", "") or texto
    return modelo, texto, feed, saida


def gc7d_uma_regeneracao_e_depois_envia():
    _p("\n[GC7d] A resposta que repergunta provoca UMA regeneracao — e depois SAI")
    repetida = "Só para eu confirmar: a água ainda está escorrendo?"
    boa = "Perfeito, com o registro fechado já estou acionando a assistência."

    # (1) o modelo insiste duas vezes -> uma regeneracao, e a resposta SAI.
    modelo, texto, feed, _ = _rodar_turno([repetida, repetida])
    check("a resposta repetida provocou UMA regeneracao",
          len(modelo.chamadas) == 2,
          "chamadas ao modelo: %d (o fiscal nao existe)" % len(modelo.chamadas))
    # A lista tem de trazer o RÓTULO e a RESPOSTA que o cliente deu — regenerar
    # sem dizer o que repetiu e torcer para o modelo adivinhar.
    ultima = " ".join(str(getattr(m, "content", ""))
                      for m in (modelo.chamadas[-1] if len(modelo.chamadas) > 1 else []))
    check("a segunda chamada levou a lista explicita do que NAO perguntar",
          "escorrendo" in ultima.lower() and "fechei o registro" in ultima.lower(),
          "a instrucao que voltou ao modelo: %r" % ultima[-400:])
    check("insistiu, mas a resposta SAI assim mesmo",
          texto.strip() == repetida.strip(),
          "travar a resposta do segurado para proteger estilo troca um defeito "
          "silencioso por um barulhento (CLAUDE.md §9.5): saiu %r" % texto[:120])
    linhas = [f for f in feed if "pergunta" in (f.get("title") or "").lower()
              or "pergunta_repetida" in (f.get("detail") or "")]
    check("e o feed registra `pergunta_repetida` com o slot",
          bool(linhas) and "agua_escorrendo" in str(linhas[0]),
          "feed: %s" % feed)
    check("o registro fica na corretora certa",
          bool(linhas) and linhas[0].get("company_id") == EMPRESA, "feed: %s" % feed)

    # (2) PAR — o modelo se corrige na regeneracao: a boa sai, e nada e registrado.
    modelo2, texto2, feed2, _ = _rodar_turno([repetida, boa])
    check("quando a regeneracao conserta, a resposta boa e que sai",
          texto2.strip() == boa.strip(), "saiu %r" % texto2[:120])
    check("e nada vira defeito no feed",
          not feed2, "feed: %s" % feed2)

    # (3) PAR — resposta limpa nao custa uma segunda chamada ao modelo.
    modelo3, texto3, feed3, _ = _rodar_turno([boa])
    check("resposta que nao repergunta nao paga regeneracao nenhuma",
          len(modelo3.chamadas) == 1 and texto3.strip() == boa.strip() and not feed3,
          "chamadas=%d feed=%s" % (len(modelo3.chamadas), feed3))


GATES = {
    "GC7a": gc7a_o_bloco_diz_de_onde_veio,
    "GC7b": gc7b_a_pergunta_repetida_e_vista,
    "GC7c": gc7c_as_ancoras_vem_do_produto,
    "GC7d": gc7d_uma_regeneracao_e_depois_envia,
}

MUTACOES = [
    # (a) a ficha chega vazia a montagem -> o bloco nao diz o que ja se sabe.
    ("M-C7a", "app/services/attendance_ficha.py",
     '    confirmados = ficha.get("confirmados") or {}\n'
     '    linhas = ["=== 📋 FICHA DESTE ATENDIMENTO (já apurado) ==="]',
     '    confirmados = {}\n'
     '    linhas = ["=== 📋 FICHA DESTE ATENDIMENTO (já apurado) ==="]',
     "GC7a"),
    # (b) as ancoras somem -> o guarda de pergunta repetida vira carimbo.
    ("M-C7b", "app/services/attendance_ficha.py",
     "        _ANCORAS_CACHE = _ler_ancoras()",
     "        _ANCORAS_CACHE = {}",
     "GC7b"),
    # (c) o fiscal deixa de regenerar -> a pergunta repetida sai na primeira.
    ("M-C7c", "app/agents/nodes.py",
     "    if not repetidos:\n        return texto, []",
     "    if repetidos or not repetidos:\n        return texto, []",
     "GC7d"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
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
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0012c7").name
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
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  G7 -- SLOT CONFIRMADO NAO SE PERGUNTA  (SPEC-EXTRA-001.2 BLOCO C)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-700:]))

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_slot_confirmado_nao_se_pergunta():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
