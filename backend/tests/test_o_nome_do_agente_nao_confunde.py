# -*- coding: utf-8 -*-
r"""G12 — O NOME DO AGENTE NAO CONFUNDE NINGUEM.

SPEC-EXTRA-001.2 BLOCO F (§10.2 nome vazio · §10.3 "especialista" · §10.5 a
recusa no SERVIDOR · §10.6 a assinatura do dossie).

```
build_composite_prompt   (o MOTOR do prompt)  -> duas corretoras, dois nomes
linha_da_apresentacao    (o MOTOR, puro)      -> nome vazio = "assistente virtual da X"
atendente_de_plantao     (o MOTOR, puro)      -> a pessoa REAL, ou NINGUEM
linha_de_quem_vai_atender(o MOTOR, puro)      -> ⛔ nunca o nome do agente
patchTenantAgentConfig   (a ROTA real, em TS) -> 400 + a frase, com db duble
_linha_da_conversa       (o MOTOR do dossie)  -> 🤖 no agente, nome puro na pessoa
```

🔴 O DEFEITO: o piloto mostrou o agente prometendo *"vou passar para a
especialista"* sem dizer quem — e 📊 `prompts.py` ENSINAVA nomes inventados
("a Ana", "o Marcos", "o analista"). Um nome que nao existe na corretora e pior
que nenhum: o segurado pergunta pela Ana e ninguem sabe quem e.

📊 14/09/2026: `company_members.role` so tem `admin_company` e `member` — **nao
existe papel `attendant`** (P-PILOTO-16). A regra (2) usa `member` ativo
nao-owner (D-E0012-02). O PLANTAO com horario e da EXTRA-001.3.

📊 14/09/2026: **0** colisoes agente x membro hoje (10 membros ativos em 3
corretoras). A trava nasce guardando o futuro.

⚠️ A ROTA e TypeScript. Este guarda a executa DE VERDADE: transpila
`lib/admin/tenant-agent-store.ts` com o `typescript` do repositorio e roda
`patchTenantAgentConfig` sobre um duble de Supabase, com o
`agent-blueprints-canonical` e o `tenant-overview-store` REAIS. ⚠️ Sao dublados
apenas `provision-tenant` (o portao do prompt, que nao e o assunto desta SPEC) e
o cliente de banco. Sem `node` no PATH, a parte TS e RECUSADA como falha — ⛔
guarda que se pula sozinho nao guarda nada.

⛔ SEGURANCA: sem rede, sem banco, sem modelo, sem PII. Nomes sinteticos.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_nome_do_agente_nao_confunde.py
    ... --so GF12c   ·   ... --medir   ·   ... --mutar [M-F12a]
"""
from __future__ import annotations

import io
import json
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
REPO = os.path.dirname(RAIZ)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

PASS = 0
FAIL = 0
MEDIDAS: dict = {}

#: ⛔ SINTETICO — duas corretoras, de propósito, no MESMO teste.
EMPRESA_A = "empresa-a-sintetica"
EMPRESA_B = "empresa-b-sintetica"
CORRETORA_A = "Alfa Corretora"
CORRETORA_B = "Beta Corretora"
AGENTE_A = "Aurora"
AGENTE_B = "Helena"
MEMBRO_A = "Saionara Sintetica"
MEMBRO_B = "Regina Sintetica"


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
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:900] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


# --------------------------------------------------------------------- #
# GF12a — duas corretoras, dois nomes, no MESMO teste
# --------------------------------------------------------------------- #

def gf12a_cada_corretora_com_o_seu_nome():
    _p("\n[GF12a] Duas corretoras no mesmo teste -> cada prompt com o SEU nome")
    from app.core import prompts as P

    a = P.build_composite_prompt("instrucoes A", agent_role="attendance",
                                 agent_display_name=AGENTE_A,
                                 company_display_name=CORRETORA_A)
    b = P.build_composite_prompt("instrucoes B", agent_role="attendance",
                                 agent_display_name=AGENTE_B,
                                 company_display_name=CORRETORA_B)
    check("o prompt da A tem o nome da A e a corretora da A",
          AGENTE_A in a and CORRETORA_A in a, a[-400:])
    check("o prompt da B tem o nome da B e a corretora da B",
          AGENTE_B in b and CORRETORA_B in b, b[-400:])
    check("🔴 §7: nada da B vaza no prompt da A",
          AGENTE_B not in a and CORRETORA_B not in a, a[-400:])
    check("e nada da A vaza no prompt da B",
          AGENTE_A not in b and CORRETORA_A not in b, b[-400:])

    # Nome VAZIO: o bloco NAO some mais (§10.2).
    from app.services import o_fim_do_atendimento as F

    vazio = P.build_composite_prompt("instrucoes", agent_role="attendance",
                                     agent_display_name="",
                                     company_display_name=CORRETORA_A)
    check("com nome vazio o agente continua tendo identidade",
          "assistente virtual" in vazio and CORRETORA_A in vazio,
          "antes desta SPEC o bloco inteiro sumia: %s" % vazio[-500:])
    linha = F.linha_da_apresentacao(F.MODO_PRIMEIRA, agent_name="",
                                    corretora=CORRETORA_A)
    check("e a apresentacao diz 'assistente virtual da {corretora}'",
          "assistente virtual da %s" % CORRETORA_A in linha, linha)
    # ⚠️ O prompt CONTINUA contendo a frase `NUNCA diga "da sua corretora"` — é
    #    a regra. O que não pode existir é a corretora se chamando assim.
    check("⛔ a apresentacao NUNCA diz 'da sua corretora'",
          "sua corretora" not in linha, linha)
    check("e o prompt so cita 'sua corretora' para PROIBIR",
          vazio.count("sua corretora") == vazio.count('NUNCA diga "da sua corretora"'),
          "ocorrencias=%d proibicoes=%d"
          % (vazio.count("sua corretora"), vazio.count('NUNCA diga "da sua corretora"')))


# --------------------------------------------------------------------- #
# GF12b — "especialista" e a atendente real, ou ninguem
# --------------------------------------------------------------------- #

def gf12b_a_especialista_e_uma_pessoa_de_verdade():
    _p("\n[GF12b] `atendente_de_plantao`: a pessoa real, ou NINGUEM — nunca o agente")
    from app.services import o_fim_do_atendimento as F

    dono = {"company_id": EMPRESA_A, "status": "active", "role": "admin_company",
            "is_owner": True, "name": "Dono Sintetico"}
    membro = {"company_id": EMPRESA_A, "status": "active", "role": "member",
              "is_owner": False, "name": MEMBRO_A}
    outro = {"company_id": EMPRESA_A, "status": "active", "role": "member",
             "is_owner": False, "name": "Outra Pessoa Sintetica"}
    inativo = {"company_id": EMPRESA_A, "status": "inactive", "role": "member",
               "is_owner": False, "name": "Ex Funcionaria Sintetica"}

    check("(2) exatamente UM member ativo nao-owner -> e ela",
          F.atendente_de_plantao(EMPRESA_A, [dono, membro, inativo]) == MEMBRO_A,
          F.atendente_de_plantao(EMPRESA_A, [dono, membro, inativo]))
    check("(3) DOIS members -> None (o agente nao escolhe por conta propria)",
          F.atendente_de_plantao(EMPRESA_A, [dono, membro, outro]) is None)
    check("(3) NENHUM member -> None",
          F.atendente_de_plantao(EMPRESA_A, [dono]) is None)
    check("(3) lista vazia -> None",
          F.atendente_de_plantao(EMPRESA_A, []) is None)
    check("(1) plantao declarado vence (a EXTRA-001.3 liga esta regra)",
          F.atendente_de_plantao(EMPRESA_A, [dono, membro, outro],
                                 plantao="Plantonista Sintetica")
          == "Plantonista Sintetica")
    check("🔴 §7: membro da corretora B nao vira atendente da A",
          F.atendente_de_plantao(
              EMPRESA_A, [dict(membro, company_id=EMPRESA_B, name=MEMBRO_B)]) is None)

    # A COPY — com nome e sem nome. ⛔ Nenhuma das duas diz o nome do AGENTE.
    com = F.linha_de_quem_vai_atender(MEMBRO_A)
    sem = F.linha_de_quem_vai_atender(None)
    check("com nome, a copy diz o nome da pessoa", MEMBRO_A in com, com)
    check("sem nome, a copy fala da EQUIPE e nao inventa ninguem",
          "nossa equipe" in sem and "Ana" not in sem and "Marcos" not in sem, sem)
    for copy in (com, sem):
        check("⛔ a copy NUNCA contem o nome do agente (%r)" % copy[:40],
              AGENTE_A not in copy and AGENTE_B not in copy,
              "o agente prometendo passar o caso para si mesmo: %s" % copy)


# --------------------------------------------------------------------- #
# GF12c — o SERVIDOR recusa nome igual ao de um membro da equipe
# --------------------------------------------------------------------- #

_NODE_JS = r"""
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const RAIZ = process.argv[2];
const ts = require(path.join(RAIZ, 'node_modules', 'typescript'));

function carregarTS(rel, resolver) {
  const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolver(id);
    if (r === undefined) throw new Error('import nao previsto no teste: ' + id);
    return r;
  };
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

// ---- duble de Supabase: thenable, com os filtros APLICADOS -----------------
function duble(linhasPorTabela, escritas) {
  function tabela(nome) {
    let filtros = [];
    const alvo = () => (linhasPorTabela[nome] || []).filter((l) =>
      filtros.every(([c, v]) => (Array.isArray(v) ? v.includes(String(l[c])) : String(l[c]) === String(v))));
    const q = {
      select() { return q; },
      eq(c, v) { filtros.push([c, v]); return q; },
      in(c, v) { filtros.push([c, v]); return q; },
      is() { return q; },
      order() { return q; },
      limit() { return q; },
      maybeSingle: async () => ({ data: alvo()[0] ?? null, error: null }),
      update(payload) {
        const u = {
          eq(c, v) { filtros.push([c, v]); return u; },
          then(res) { escritas.push({ tabela: nome, payload, filtros: [...filtros] }); res({ error: null }); },
        };
        return u;
      },
      then(res) { res({ data: alvo(), error: null }); },
    };
    return q;
  }
  return { from: tabela };
}

const CAMINHO = 'lib/admin/tenant-agent-store.ts';
const canonical = carregarTS('lib/admin/agent-blueprints-canonical.ts', () => undefined);
const overview = carregarTS('lib/admin/tenant-overview-store.ts', () => undefined);
const store = carregarTS(CAMINHO, (id) => {
  if (id.endsWith('agent-blueprints-canonical')) return canonical;
  if (id.endsWith('tenant-overview-store')) return overview;
  // ⚠️ DUBLADO de proposito: o portao do prompt vazio (P-36) nao e o assunto
  //    desta SPEC, e ele leria o banco de novo.
  if (id.endsWith('provision-tenant')) return { problemasDoUpdate: () => [], conferirPromptGravado: async () => ({ ok: true }) };
  if (id.endsWith('toggle-transicao')) return { decidirTransicaoDoToggle: () => ({}) };
  return {};
});

const EMPRESA_A = process.env.EMPRESA_A, EMPRESA_B = process.env.EMPRESA_B;
const MEMBRO_A = process.env.MEMBRO_A, MEMBRO_B = process.env.MEMBRO_B;

function banco() {
  return {
    companies: [{ id: EMPRESA_A, company_name: 'Alfa Corretora' }, { id: EMPRESA_B, company_name: 'Beta Corretora' }],
    agents: [
      { id: 'agente-a', company_id: EMPRESA_A, agent_role: 'attendance', context_package: {} },
      { id: 'agente-b', company_id: EMPRESA_B, agent_role: 'attendance', context_package: {} },
    ],
    company_members: [
      { company_id: EMPRESA_A, user_id: 'u-a', role: 'member', is_owner: false, status: 'active' },
      { company_id: EMPRESA_B, user_id: 'u-b', role: 'member', is_owner: false, status: 'active' },
    ],
    users_v2: [
      { id: 'u-a', first_name: MEMBRO_A.split(' ')[0], last_name: MEMBRO_A.split(' ').slice(1).join(' '), email: 'a@x', status: 'active' },
      { id: 'u-b', first_name: MEMBRO_B.split(' ')[0], last_name: MEMBRO_B.split(' ').slice(1).join(' '), email: 'b@x', status: 'active' },
    ],
  };
}

async function patch(companyId, nome) {
  const escritas = [];
  const db = duble(banco(), escritas);
  const out = await store.patchTenantAgentConfig(db, companyId, 'attendance', { variables: { attendant_name: nome } });
  return { out, escreveu: escritas.length };
}

const r = {};
r.colide_exato = await patch(EMPRESA_A, MEMBRO_A);
r.colide_primeiro_nome = await patch(EMPRESA_A, MEMBRO_A.split(' ')[0]);
r.colide_com_acento = await patch(EMPRESA_A, MEMBRO_A.split(' ')[0].toUpperCase());
r.livre = await patch(EMPRESA_A, 'Aurora');
r.membro_da_b_nao_bloqueia_a = await patch(EMPRESA_A, MEMBRO_B);
r.normalizador = {
  acento: store.nomeNormalizado('Saíonára  SILVA'),
  colide: store.colisaoComAEquipe('amanda', [{ name: 'Amanda Silva' }]),
  nao_colide: store.colisaoComAEquipe('Aurora', [{ name: 'Amanda Silva' }]),
};
console.log('__JSON__' + JSON.stringify(r));
"""


def _rodar_node():
    """Executa a rota REAL (TS) com db duble. Devolve `(ok, dados_ou_erro)`."""
    node = shutil.which("node")
    if not node:
        return False, "node nao esta no PATH — a metade TS deste guarda NAO rodou"
    if not os.path.isdir(os.path.join(REPO, "node_modules", "typescript")):
        return False, "node_modules/typescript ausente — rode `npm ci` antes"
    arq = tempfile.NamedTemporaryFile(delete=False, suffix=".mjs", mode="w",
                                      encoding="utf-8", newline="\n")
    try:
        arq.write(_NODE_JS)
        arq.close()
        r = subprocess.run(
            [node, arq.name, REPO], cwd=REPO, capture_output=True, text=True,
            timeout=300, encoding="utf-8", errors="replace",
            env={**os.environ, "EMPRESA_A": EMPRESA_A, "EMPRESA_B": EMPRESA_B,
                 "MEMBRO_A": MEMBRO_A, "MEMBRO_B": MEMBRO_B})
        for linha in (r.stdout or "").splitlines():
            if linha.startswith("__JSON__"):
                return True, json.loads(linha[len("__JSON__"):])
        return False, ((r.stdout or "") + (r.stderr or ""))[-900:]
    finally:
        try:
            os.unlink(arq.name)
        except OSError:
            pass


def gf12c_o_servidor_recusa_nome_colidente():
    _p("\n[GF12c] A ROTA REAL (TS, db duble) recusa nome igual ao de um membro")
    ok, dados = _rodar_node()
    if not check("a rota TS foi carregada e executada", ok, dados):
        return

    colide = dados["colide_exato"]["out"]
    check("nome IGUAL ao de um membro e RECUSADO",
          colide.get("ok") is False and colide.get("error") == "nome_colide_com_a_equipe",
          colide)
    check("e a resposta traz a FRASE que a tela mostra (nao um codigo)",
          "equipe" in str(colide.get("message") or "")
          and MEMBRO_A in str(colide.get("message") or ""), colide)
    check("⛔ e NADA foi escrito no banco",
          dados["colide_exato"]["escreveu"] == 0, dados["colide_exato"])

    check("o PRIMEIRO nome tambem colide ('Amanda' x 'Amanda Silva')",
          dados["colide_primeiro_nome"]["out"].get("error") == "nome_colide_com_a_equipe",
          dados["colide_primeiro_nome"]["out"])
    check("e a caixa nao esconde a colisao",
          dados["colide_com_acento"]["out"].get("error") == "nome_colide_com_a_equipe",
          dados["colide_com_acento"]["out"])

    # PAR — sem estes, recusar TUDO passaria.
    check("PAR: nome livre e ACEITO e escreve no banco",
          dados["livre"]["out"].get("ok") is True and dados["livre"]["escreveu"] == 1,
          dados["livre"])
    check("🔴 §7: membro da corretora B NAO bloqueia o nome na corretora A",
          dados["membro_da_b_nao_bloqueia_a"]["out"].get("ok") is True,
          dados["membro_da_b_nao_bloqueia_a"]["out"])

    n = dados["normalizador"]
    check("o normalizador tira acento, caixa e espaco duplo",
          n["acento"] == "saionara silva", n)
    check("e o mesmo normalizador acha a colisao por primeiro nome",
          n["colide"] == "Amanda Silva" and n["nao_colide"] is None, n)


# --------------------------------------------------------------------- #
# GF12d — o dossie: 🤖 no agente, nome puro na pessoa
# --------------------------------------------------------------------- #

def gf12d_a_assinatura_do_dossie():
    _p("\n[GF12d] No dossie o agente assina 🤖 {nome}; a atendente aparece pelo nome, sem emoji")
    from app.agents.tools.human_handoff import _linha_da_conversa

    quando = "2026-09-14T15:30:00+00:00"
    do_agente = _linha_da_conversa(
        {"role": "assistant", "content": "ja acionei a assistencia",
         "created_at": quando, "payload": {}}, AGENTE_A)
    da_pessoa = _linha_da_conversa(
        {"role": "assistant", "content": "eu assumo daqui", "created_at": quando,
         "payload": {"origem": "dashboard", "autor": MEMBRO_A}}, AGENTE_A)
    do_cliente = _linha_da_conversa(
        {"role": "user", "content": "bati o carro", "created_at": quando,
         "payload": {}}, AGENTE_A)

    check("o agente assina 🤖 com o NOME que a corretora escolheu",
          "🤖 %s" % AGENTE_A in do_agente, do_agente)
    check("a atendente aparece pelo NOME, SEM emoji",
          MEMBRO_A in da_pessoa and "🤖" not in da_pessoa
          and "👤" not in da_pessoa, da_pessoa)
    check("⛔ a assinatura nao se inverte: o robo nunca leva o nome puro",
          "🤖" in do_agente and MEMBRO_A not in do_agente, do_agente)
    check("o cliente continua sendo o cliente",
          "Cliente" in do_cliente and "🤖" not in do_cliente, do_cliente)

    # Sem nome configurado o dossie nao mente: ele diz "assistente virtual".
    sem_nome = _linha_da_conversa(
        {"role": "assistant", "content": "oi", "created_at": quando,
         "payload": {}}, "")
    check("sem nome configurado, o dossie diz 'assistente virtual' (nunca 'IA')",
          "🤖 assistente virtual" in sem_nome, sem_nome)


GATES = {
    "GF12a": gf12a_cada_corretora_com_o_seu_nome,
    "GF12b": gf12b_a_especialista_e_uma_pessoa_de_verdade,
    "GF12c": gf12c_o_servidor_recusa_nome_colidente,
    "GF12d": gf12d_a_assinatura_do_dossie,
}

MUTACOES = [
    # (a) o servidor ACEITA a colisao — o "Amanda, a assistente" x "Amanda, a atendente".
    ("M-F12a", "lib/admin/tenant-agent-store.ts",
     "  const colide = colisaoComAEquipe(nomePedido, members ?? []);",
     "  const colide = null as string | null;",
     "GF12c"),
    # (b) `atendente_de_plantao` devolve o proprio agente quando nao sabe.
    ("M-F12b", "app/services/o_fim_do_atendimento.py",
     "    return candidatos[0] if len(candidatos) == 1 else None",
     "    return candidatos[0] if candidatos else None",
     "GF12b"),
    # (c) a assinatura do dossie se inverte.
    ("M-F12c", "app/agents/tools/human_handoff.py",
     '        autor = "🤖 %s" % (str(agent_name or "").strip() or "assistente virtual")',
     '        autor = str(agent_name or "").strip() or "assistente virtual"',
     "GF12d"),
    # (d) o bloco de identidade volta a sumir quando o nome esta vazio (§10.2).
    ("M-F12d", "app/core/prompts.py",
     '    if role_norm in ("attendance", "insured_external"):',
     '    if role_norm in ("attendance", "insured_external") and display_name:',
     "GF12a"),
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
        # ⚠️ `lib/` mora na RAIZ do repositorio, nao em `backend/`.
        base_dir = REPO if relativo.startswith(("lib/", "app/api", "app/dashboard")) else RAIZ
        caminho = os.path.normpath(os.path.join(base_dir, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0012f12").name
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
        _p("  G12 -- O NOME DO AGENTE NAO CONFUNDE  (SPEC-EXTRA-001.2 BLOCO DF)")
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


def test_o_nome_do_agente_nao_confunde():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
