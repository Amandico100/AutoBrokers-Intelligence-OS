# -*- coding: utf-8 -*-
r"""G6 — TODO SLOT QUE O CORREDOR EXIGE ESTA NO VOCABULARIO E VAI PARA A FICHA.

SPEC-EXTRA-001.2 BLOCO C (§7.1). O laco que este guarda fecha:

```
corridor_playbooks.required_slots  ->  slots_do_atendimento()   (o MOTOR)
                                   ->  ROTULOS  (rotulo em portugues)
                                   ->  _gravar_ficha_do_turno   (o MOTOR)
                                   ->  bloco_para_o_prompt      (o MOTOR)
```

🔴 O VERMELHO DE PARTIDA (gate zero, AAA §8 / SPEC §12.1) — saida REAL de
14/09/2026, com o codigo ANTES do bloco C, rodando este mesmo arquivo:

```
[GC6a] Todo slot exigido por um corredor esta em slots_do_atendimento()
  [FALHOU] GC6a EXPLODIU (defeito do guarda ou do produto)
         ImportError: cannot import name 'CAMPOS_DE_CONTROLE' from
         'app.services.attendance_ficha'
[GC6b] Cada slot do universo tem rotulo em portugues em ROTULOS
  [FALHOU] GC6b EXPLODIU (defeito do guarda ou do produto)
         ImportError: cannot import name 'slots_do_atendimento' from
         'app.services.attendance_ficha'
[GC6c] _gravar_ficha_do_turno grava um slot de corredor, e ele volta no prompt
  [FALHOU] agua_escorrendo entrou na ficha
         o escritor gravou: ['problema_descricao', 'titular_cpf']
  [FALHOU] e os outros dois slots do encanador tambem
  [ok] o campo de controle NAO entrou como dado do cliente
  [FALHOU] o bloco do prompt mostra o slot do corredor de volta
  1 assercoes verdes - 5 vermelhas
```

⚠️ `agua_escorrendo`, `vazamento_local` e `risco_confirmado_registro_fechado`
sao os TRES slots do encanador: o corredor os exige, a tool os declara, o
cliente os responde — e nenhum chegava a ficha. Era o turno seguinte
perguntando tudo de novo.

📊 O que o motor mediu em 14/09/2026, antes do conserto (comando: este arquivo,
gate GC6a): **54** `required_slots` distintos nos 14 playbooks, **37** deles
fora de `ROTULOS`, e o escritor (`_SLOTS_DA_FICHA`, tupla literal) gravava
**15**. 📊 ⚠️ O relatorio do BLOCO 0 mediu 20/13 por AST do FONTE; o motor
conta 54/37 porque metade dos subservicos nasce em tempo de importacao
(`_ativar_subservico`, `_resid_slots`, os overlays de `tipo_imovel`). Regex
sobre o fonte e outro motor — CLAUDE.md §9.4.

⛔ SEGURANCA: sem rede, sem banco, sem PII. As fichas sao sinteticas.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_todo_slot_do_corredor_tem_ficha.py
    ... --so GC6a   ·   ... --medir   ·   ... --mutar [M-C6a]
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


def _exigidos_pelos_corredores() -> dict:
    """Todo `required_slots` de todo subservico de todo playbook — pelo MOTOR.

    ⛔ Nao e regex sobre o fonte: metade dos subservicos so existe depois que o
    modulo importa (`_ativar_subservico`, `_resid_slots`, o overlay de
    `tipo_imovel`). Ler o arquivo veria uma lista menor do que a que roda.
    """
    from app.services import corridor_playbooks as CP

    saida: dict = {}
    for ref, pb in CP._PLAYBOOKS.items():
        for sv, cfg in (pb.get("subservices") or {}).items():
            for slot in (cfg.get("required_slots") or []):
                saida.setdefault(slot, []).append("%s/%s" % (ref.split("@")[0], sv))
    return saida


# --------------------------------------------------------------------- #
# GC6a — o vocabulario cobre o que os corredores exigem
# --------------------------------------------------------------------- #

def gc6a_o_vocabulario_cobre_os_corredores():
    _p("\n[GC6a] Todo slot exigido por um corredor esta em slots_do_atendimento()")
    from app.services.attendance_ficha import CAMPOS_DE_CONTROLE, slots_do_atendimento

    exigidos = _exigidos_pelos_corredores()
    universo = slots_do_atendimento()
    medir("corredores.required_slots_distintos", len(exigidos))
    medir("ficha.slots_do_atendimento", len(universo))

    faltando = sorted(s for s in exigidos if s not in universo and s not in CAMPOS_DE_CONTROLE)
    check("nenhum slot de corredor fica fora da ficha",
          not faltando,
          "fora: %s (ex.: %s)" % (faltando, exigidos.get(faltando[0]) if faltando else ""))

    # PAR — campo de CONTROLE nao vira slot de cliente. Sem este par, bastaria
    # devolver "tudo" para o guarda acima ficar verde.
    check("campo de controle NAO vira slot",
          "dados_confirmados" not in universo,
          "`dados_confirmados` e a marca de que o modelo conferiu a apolice, "
          "nao um dado que o cliente disse")
    check("a lista de controle e fechada e pequena",
          0 < len(CAMPOS_DE_CONTROLE) <= 12,
          "CAMPOS_DE_CONTROLE = %s" % sorted(CAMPOS_DE_CONTROLE))


# --------------------------------------------------------------------- #
# GC6b — cada slot tem nome humano
# --------------------------------------------------------------------- #

def gc6b_cada_slot_tem_rotulo():
    _p("\n[GC6b] Cada slot do universo tem rotulo em portugues em ROTULOS")
    from app.services.attendance_ficha import ROTULOS, rotulo, slots_do_atendimento

    universo = sorted(slots_do_atendimento())
    sem_rotulo = [s for s in universo if s not in ROTULOS]
    medir("ficha.slots_sem_rotulo", len(sem_rotulo))
    check("nenhum slot chega ao modelo com a chave tecnica",
          not sem_rotulo,
          "sem rotulo: %s" % sem_rotulo)

    crus = [s for s in universo if ROTULOS.get(s) == s]
    check("nenhum rotulo e a propria chave",
          not crus, "chave repetida como rotulo: %s" % crus)

    check("o rotulo do slot que originou a SPEC esta escrito",
          "escorrendo" in rotulo("agua_escorrendo"),
          "rotulo('agua_escorrendo') = %r" % rotulo("agua_escorrendo"))
    check("e slot sem rotulo continua devolvendo a propria chave",
          rotulo("slot_que_ninguem_batizou") == "slot_que_ninguem_batizou",
          "nome bonito inventado esconderia um campo que ninguem batizou")


# --------------------------------------------------------------------- #
# GC6c — o ESCRITOR grava, e o turno seguinte mostra de volta
# --------------------------------------------------------------------- #

class _ClienteInerte:
    """Dublê do Supabase: o escritor nunca chega a ele (gravar e dublado)."""

    client = None


def gc6c_o_escritor_grava_o_slot_do_corredor():
    _p("\n[GC6c] _gravar_ficha_do_turno grava um slot de corredor, e ele volta no prompt")
    import app.core.database as _db
    import app.services.attendance_ficha as F
    from app.agents import nodes as N

    capturado: dict = {}

    async def _gravar_dublado(supabase, company_id, session_id, novidades, obrigatorios=None):
        capturado["company_id"] = company_id
        capturado["session_id"] = session_id
        capturado["novidades"] = novidades
        capturado["obrigatorios"] = list(obrigatorios or [])
        return F.fundir(F.ficha_vazia(), novidades, obrigatorios)

    _gravar_real, _cli_real = F.gravar, _db.get_supabase_client
    F.gravar = _gravar_dublado
    _db.get_supabase_client = lambda: _ClienteInerte()
    try:
        estado = {"company_id": "empresa-sintetica", "session_id": "sessao-sintetica"}
        # ⛔ SINTETICO: nada aqui e de gente real.
        args = {
            "insurer_key": "allianz", "line_kind": "residencial",
            "subservice": "encanador",
            "titular_cpf": "00000000191",
            "problema_descricao": "vazamento embaixo da pia",
            "agua_escorrendo": "nao, fechei o registro",
            "vazamento_local": "embaixo da pia da cozinha",
            "risco_confirmado_registro_fechado": "sim",
            "dados_confirmados": True,
        }
        asyncio.run(N._gravar_ficha_do_turno(estado, "insurer_dispatch", args, "ok"))
    finally:
        F.gravar, _db.get_supabase_client = _gravar_real, _cli_real

    confirmados = (capturado.get("novidades") or {}).get("confirmados") or {}
    check("agua_escorrendo entrou na ficha",
          "agua_escorrendo" in confirmados,
          "o escritor gravou: %s" % sorted(confirmados))
    check("e os outros dois slots do encanador tambem",
          {"vazamento_local", "risco_confirmado_registro_fechado"} <= set(confirmados),
          "gravou: %s" % sorted(confirmados))
    check("o campo de controle NAO entrou como dado do cliente",
          "dados_confirmados" not in confirmados,
          "ele so pode virar `apolice_confirmada`")

    ficha = F.fundir(F.ficha_vazia(), capturado.get("novidades") or {}, [])
    bloco = F.bloco_para_o_prompt(ficha, [])
    check("o bloco do prompt mostra o slot do corredor de volta",
          F.rotulo("agua_escorrendo") in bloco and "fechei o registro" in bloco,
          bloco[:400])


GATES = {
    "GC6a": gc6a_o_vocabulario_cobre_os_corredores,
    "GC6b": gc6b_cada_slot_tem_rotulo,
    "GC6c": gc6c_o_escritor_grava_o_slot_do_corredor,
}

#: Cada mutacao roda em SUBPROCESSO, sobre uma COPIA restaurada no `finally`.
#: ⛔ Nunca `git checkout` (CLAUDE.md §12 / AAA §10): o repositorio e
#: compartilhado com outro builder nesta mesma onda.
MUTACOES = [
    # (a) o escritor volta a ser a lista de 15 escrita a mao -> os 37 slots de
    #     corredor somem do vocabulario, e `agua_escorrendo` some da ficha.
    ("M-C6a", "app/services/attendance_ficha.py",
     "    base = set(ROTULOS) | _slots_dos_corredores()",
     '    base = {"titular_cpf", "titular_nome", "telefone_contato", "veiculo_placa",\n'
     '            "local_atual", "local_destino", "endereco_numero", "problema_descricao",\n'
     '            "periodo_preferido", "risco_confirmado_sem_fumaca",\n'
     '            "aparelho_marca_modelo", "aparelho_idade", "veiculo_em_garagem",\n'
     '            "veiculo_nivel_rua", "local_situacao"}',
     "GC6a"),
    # (b) o PAR: sem campo de controle, `dados_confirmados` viraria dado do
    #     cliente -- e a ficha declararia confirmado o que ninguem confirmou.
    ("M-C6b", "app/services/attendance_ficha.py",
     'CAMPOS_DE_CONTROLE = frozenset({\n    "dados_confirmados",\n})',
     "CAMPOS_DE_CONTROLE = frozenset()",
     "GC6a"),
    # (c) o rotulo do slot novo some -> o modelo leria `agua_escorrendo` cru.
    ("M-C6c", "app/services/attendance_ficha.py",
     '    "agua_escorrendo": "se a água ainda está escorrendo",',
     "",
     "GC6b"),
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
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0012c6").name
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
        _p("  G6 -- TODO SLOT DO CORREDOR TEM FICHA  (SPEC-EXTRA-001.2 BLOCO C)")
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


def test_todo_slot_do_corredor_tem_ficha():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
