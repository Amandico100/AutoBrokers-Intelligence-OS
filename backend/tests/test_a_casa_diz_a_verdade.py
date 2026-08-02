"""O admin tem um lugar por conceito, e a documentação para de mentir.

O que a auditoria mediu, em 02/08/2026
--------------------------------------
**Bloco I — o admin.** O submenu "Inteligência" tinha NOVE itens, e quatro
respondiam alguma variação de *"o que o sistema pode fazer"*: `capacidades`,
`central-agentes`, `auxiliares` e `blueprint-center`.

Isso não é um menu longo. É **um conceito sem lugar**: "o que o sistema sabe
fazer" é o CATÁLOGO, e catálogo tem uma casa só. Sem essa casa, cada peça nova
cai onde couber — e o menu vira lista.

**Bloco J — a documentação que contradiz o código.** Quatro casos medidos:

    EXECUTION-MASTER-PLAN     dizia 057 e 058 "NÃO INICIADO"
                              → 19 templates e tabelas vivas no banco
    graph.py                  comentário dizia "RAG global OFF p/ attendance"
                              → a linha ao lado INCLUI attendance
    prompts.py                cabeçalho "SPEC-013 P0"
                              → CLAUDE.md §4 declara a 013 não-autoridade,
                                e ela nem existe em docs/canon/specs/
    MIGRATIONS-AUTHORITY §9   "enquanto P1 pendente, nenhum write autorizado"
                              → P1 foi RESOLVIDA por D11 em 25/07

O que este teste protege
------------------------
Que a próxima pessoa — ou LLM — que abrir estes arquivos leia a verdade.

**Comentário que contradiz o código ao lado é pior que comentário nenhum:** ele
faz alguém "consertar" o que funciona. E documento canônico que descreve um
bloqueio já removido não protege — ensina a ignorar o documento.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_ts(fonte: str) -> str:
    sem = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*")))
    return re.sub(r"/\*.*?\*/", "", sem, flags=re.S)


def _sem_comentario_py(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


# ---------------------------------------------------------------------------
# BLOCO I — o admin
# ---------------------------------------------------------------------------

def teste_um_lugar_por_conceito():
    """O catálogo fica visível — SEM fazer o primeiro nível crescer.

    Eu cheguei a criar um nono hub "Catálogo", e o teste da SPEC-061 §10 me
    pegou. Ele está certo: §10 proíbe item de primeiro nível novo sem revisão
    canônica, e o Admin já chegou a QUINZE grupos antes de o Founder dizer
    *"é uma bagunça e não consigo entender de fato tudo"*.

    **Seria repetir, no admin, exatamente o que a SPEC-064 desfez no menu do
    corretor.** "O menu não cresce" vale para os dois lados — e a SPEC-064 não
    tem autoridade para desfazer, de passagem, uma estrutura que o Founder
    aprovou na SPEC-061.

    A separação acontece dentro do submenu, que é livre. A reorganização de
    primeiro nível que a SPEC-064 I.3 propõe fica registrada como decisão do
    Founder (CLAUDE.md §10 — conflito canônico).
    """
    print("\n[1] O catálogo fica visível sem o primeiro nível crescer")
    layout = _sem_comentario_ts(_ler("app", "admin", "layout.tsx"))

    bloco_intel = layout.split("label: 'Inteligência'", 1)[1].split("],", 1)[0]

    # As quatro continuam alcançáveis — e agora se anunciam pelo que são.
    for chave in ("/admin/auxiliares", "/admin/central-agentes",
                  "/admin/routine-templates", "/admin/capacidades"):
        checar(chave in bloco_intel, f"{chave} continua alcançável")

    rotulados = bloco_intel.count("Catálogo:")
    checar(rotulados >= 4,
           f"{rotulados} itens se anunciam como catálogo",
           "o rótulo é o que separa 'o que percebeu' de 'o que sabe fazer' "
           "sem precisar de um hub novo")

    # E o primeiro nível NÃO cresceu.
    topo = re.findall(r"icon:\s*\w+,\s*\n?\s*label:\s*'([^']+)'", layout)
    checar(len(topo) == 8,
           "o primeiro nível continua com 8 hubs",
           f"{len(topo)}: {topo}")


def teste_nenhum_rotulo_do_admin_se_repete():
    print("\n[2] Nenhum rótulo se repete no admin")
    layout = _ler("app", "admin", "layout.tsx")
    rotulos = re.findall(r"label: '([^']+)'", layout)
    repetidos = sorted({r for r in rotulos if rotulos.count(r) > 1})
    checar(not repetidos, "nenhum rótulo duplicado", f"{repetidos}")


# ---------------------------------------------------------------------------
# BLOCO J — a documentação
# ---------------------------------------------------------------------------

def teste_o_glossario_existe_e_e_a_autoridade():
    print("\n[3] Existe um glossário, e ele é a autoridade sobre os termos")
    caminho = os.path.join(RAIZ, "docs", "canon", "GLOSSARIO.md")
    checar(os.path.isfile(caminho), "docs/canon/GLOSSARIO.md existe")
    if not os.path.isfile(caminho):
        return

    doc = _ler("docs", "canon", "GLOSSARIO.md")
    for termo in ("Skill", "Rotina", "Auxiliar", "Artifact",
                  "Capability", "Conector", "Portal", "Corredor"):
        checar(f"**{termo}**" in doc, f"define {termo}")

    checar("este vence" in doc.lower(),
           "declara-se autoridade em caso de conflito",
           "glossário que não desempata não resolve contradição")

    # Os termos que não existem mais precisam estar listados: é o que impede
    # uma LLM nova de ressuscitar nomenclatura revogada.
    for morto in ("Jarvys", "Portal Browser", "Venda casada", "Auxiliares = Rotinas"):
        checar(morto in doc, f"registra que '{morto}' não se usa")

    checar("GLOSSARIO.md" in _ler("CLAUDE.md"), "CLAUDE.md §2 aponta para o glossário")


def teste_os_comentarios_pararam_de_mentir():
    print("\n[4] Comentário não contradiz mais o código ao lado")

    grafo = _ler("backend", "app", "agents", "graph.py")
    linha_rag = next((l for l in grafo.split("\n")
                      if "_rag_include_global," in l and "#" in l), "")
    checar("OFF p/ attendance" not in linha_rag,
           "o comentário do RAG não diz mais 'OFF p/ attendance'",
           f"linha={linha_rag.strip()[:80]}")
    # E o código continua incluindo attendance — é ele que está certo.
    checar('"attendance"' in grafo and "_rag_include_global =" in grafo,
           "o código continua incluindo attendance no RAG global",
           "são as 8.916 cartas destiladas de atendimento real")

    prompts = _ler("backend", "app", "core", "prompts.py")
    primeira_linha_cabecalho = next(
        (l for l in prompts.split("\n") if "CORE_BASE_PROMPT" in l), "")
    idx = prompts.find("CORE_BASE_PROMPT")
    cabecalho = prompts[max(0, idx - 600):idx]
    checar("SPEC-013 P0 — Base do CHAT PRINCIPAL" not in cabecalho,
           "o prompt do Core não se anuncia sob a SPEC-013",
           "CLAUDE.md §4 declara a 013 não-autoridade, e ela não existe no repo")
    checar("SPEC-052" in cabecalho,
           "o cabeçalho aponta a autoridade real")


def teste_o_master_plan_bate_com_o_que_existe():
    print("\n[5] O painel de execução para de dizer 'NÃO INICIADO' sobre o que existe")
    plano = _ler("docs", "canon", "EXECUTION-MASTER-PLAN.md")

    for spec, prova in (("SPEC-057", "19 templates em `report_templates`"),
                        ("SPEC-058", "`auxiliary_templates`")):
        linha = next((l for l in plano.split("\n")
                      if l.startswith("|") and f"{spec} —" in l), "")
        checar("NÃO INICIADO" not in linha,
               f"{spec} não é mais 'NÃO INICIADO'",
               f"linha={linha[:110]}")
        checar("PARCIAL" in linha,
               f"{spec} está marcada como PARCIAL, com o que falta nomeado")


def teste_o_documento_de_migrations_nao_bloqueia_o_que_ja_foi_liberado():
    print("\n[6] MIGRATIONS-AUTHORITY não descreve um bloqueio já removido")
    doc = _ler("docs", "canon", "MIGRATIONS-AUTHORITY.md")
    checar("P1 foi RESOLVIDA POR D11" in doc,
           "o documento registra que P1 foi resolvida",
           "quem lesse concluiria que não pode aplicar migration — e nove "
           "já foram aplicadas desde então")
    checar("está autorizado" in doc,
           "diz explicitamente que write em produção está autorizado")


def teste_os_indices_apontam_para_o_que_existe():
    print("\n[7] O bootstrap aponta só para documentos que existem")
    claude = _ler("CLAUDE.md")
    apontados = re.findall(r"\(docs/canon/([A-Z][A-Z0-9\-]+\.md)\)", claude)
    faltando = [d for d in set(apontados)
                if not os.path.isfile(os.path.join(RAIZ, "docs", "canon", d))]
    checar(not faltando, "todo documento citado no CLAUDE.md existe", f"{faltando}")
    print(f"      documentos no bootstrap: {sorted(set(apontados))}")


def main() -> int:
    print("=" * 68)
    print("UM LUGAR POR CONCEITO, E A DOCUMENTAÇÃO DIZ A VERDADE")
    print("=" * 68)
    for teste in (teste_um_lugar_por_conceito,
                  teste_nenhum_rotulo_do_admin_se_repete,
                  teste_o_glossario_existe_e_e_a_autoridade,
                  teste_os_comentarios_pararam_de_mentir,
                  teste_o_master_plan_bate_com_o_que_existe,
                  teste_o_documento_de_migrations_nao_bloqueia_o_que_ja_foi_liberado,
                  teste_os_indices_apontam_para_o_que_existe):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("QUEM ABRIR ESTES ARQUIVOS LE A VERDADE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
