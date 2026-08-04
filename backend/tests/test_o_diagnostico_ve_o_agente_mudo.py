"""O diagnóstico enxerga o agente MUDO — o estado que a AutoFleet realmente teve.

P-37. Presente, único, ativo — e sem uma linha de instrução.
-------------------------------------------------------------
`lib/admin/agent-health.ts` detectava agente AUSENTE e agente DUPLICADO. E foi
por isso que ninguém percebeu a AutoFleet.

📊 Medido em 02/08/2026 no banco de produção (auditoria do Bloco 0,
`docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md`, Parte C.6)::

    corretora    papel   blueprint              prompt
    Resulta      core    autobrokers-core-v1    650 chars
    AutoFleet    core    autobrokers-core-v1        0     <- ATIVO
    Amandus      core    core-v1                7.914 chars

O agente da AutoFleet **estava lá**, era **único** e estava **ativo**. Passava
em todas as checagens que existiam. E com o defeito de resolução por
antiguidade, era ele que responderia o segurado — ativo, sem instrução e sem
nenhuma trava. A tela dizia "saudável".

E existe um segundo jeito de ser mudo
--------------------------------------
`composeSystemPromptWithGuardrails('')` devolve ~560 caracteres de cabeçalho e
regras imutáveis, e NENHUMA instrução sobre o que o agente é ou faz. Um agente
com essa casca tem prompt longo e continua mudo na prática — e passaria em
qualquer checagem de "prompt não vazio". Por isso a medida é a PERSONALIZAÇÃO
(o que está acima do bloco de regras), não o comprimento do texto.

O jeito de este teste ser honesto
----------------------------------
A lógica é TypeScript. Ler o arquivo e procurar palavras provaria que alguém
escreveu o nome certo, não que a detecção funciona. Então o caso [1] TRANSPILA
`agent-health.ts` com o próprio compilador do projeto e **executa a função de
verdade** (`scripts/agent-health.test.mjs`) — inclusive contra a casca de
guardrails, que é o caso que uma checagem ingênua deixa passar.

Aquele arquivo, por sinal, NÃO RODAVA: importava `.ts` direto do node, e morria
no import antes da primeira asserção. Foi consertado junto.

Os casos [2] em diante guardam o que a execução não alcança: que a coluna é
pedida no `select` (sem ela a detecção é cega por falta de dado, não por falta
de lógica), que o texto do prompt NÃO sai na resposta, e que a tela para de
dizer "ativa" para uma agente muda.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

SAUDE = ("lib", "admin", "agent-health.ts")
ROTA = ("app", "api", "admin", "companies", "[companyId]", "agent-health", "route.ts")
TELA = ("app", "admin", "companies", "[companyId]", "agents", "page.tsx")
CANONICO = ("lib", "admin", "agent-blueprints-canonical.ts")
PROVA_NODE = os.path.join("scripts", "agent-health.test.mjs")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(fonte: str) -> str:
    """Comentário não é prova. O que vale é o que executa."""
    sem_linha = "\n".join(
        l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*"))
    )
    return re.sub(r"/\*.*?\*/", "", sem_linha, flags=re.S)


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def teste_a_deteccao_roda_de_verdade():
    print("\n[1] A funcao REAL e executada, nao lida")
    caminho = os.path.join(RAIZ, PROVA_NODE)
    checar(os.path.exists(caminho), f"{PROVA_NODE} existe")
    try:
        r = subprocess.run(["node", caminho], cwd=RAIZ, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as exc:  # noqa: BLE001
        checar(False, "o node conseguiu rodar a prova", f"{type(exc).__name__}: {exc}")
        return

    saida = (r.stdout or "") + (r.stderr or "")
    checar(r.returncode == 0, "a prova em node passa inteira",
           saida.strip().split("\n")[-1] if saida.strip() else f"exit={r.returncode}")

    # Os casos que MEDEM o defeito precisam estar entre os que passaram — uma
    # prova verde que não testa o mudo não prova nada sobre P-37.
    for marca in ("core ativo com prompt vazio vira mute_core",
                  "e a corretora deixa de ser \"saudável\"",
                  "mas é classificada como so_guardrails",
                  "prompt real (com personalização) é \"ok\"",
                  "agente sem a coluna no select não é considerado mudo"):
        checar(f"ok   {marca}" in saida, f"executado e verde: {marca}",
               "se este caso sumir da prova, o verde deixa de significar isso")

    # E o arquivo tem de estar RODANDO — ele importava .ts direto do node e
    # morria no import, sem executar uma asserção sequer.
    fonte_mjs = _ler(*PROVA_NODE.split(os.sep))
    import_direto = [l for l in fonte_mjs.split("\n")
                     if l.lstrip().startswith("import ") and "agent-health.ts" in l]
    checar(not import_direto,
           "nao ha `import` de .ts (o node nao carrega TypeScript)",
           f"{import_direto} — era isso que matava o arquivo no import")
    checar("transpileModule" in fonte_mjs and "agent-health.ts" in fonte_mjs,
           "e ele transpila o modulo REAL antes de executar",
           "antes disso o arquivo existia e nunca executou nada")


def teste_a_mudez_derruba_a_saude():
    print("\n[2] Mudo deixa de ser 'saudavel'")
    codigo = _sem_comentario(_ler(*SAUDE))

    for peca in ("'mute_core'", "'mute_attendance'"):
        checar(peca in codigo, f"o diagnostico conhece {peca}")
    checar("export function isMute(" in codigo, "e existe o veredito por agente")

    corpo = codigo.split("export function isHealthy(", 1)[1].split("\n}", 1)[0]
    checar("'mute_core'" in corpo and "'mute_attendance'" in corpo,
           "e a mudez entra na SAUDE, nao na higiene",
           "um agente sem voz nao e imperfeicao de cadastro: e um agente que "
           "nao trabalha")

    # `is_active` é agravante, não requisito: mudo e desligado também precisa
    # de conserto — é o estado em que o portão de provisionamento o deixa.
    divs = codigo.split("export function buildAgentDivergences(", 1)[1].split("\n}", 1)[0]
    checar("if (!isMute(a)) continue;" in divs,
           "a divergencia sai da MUDEZ, nao de estar ativo",
           "exigir ativo esconderia o agente que o portao desligou por seguranca")


def teste_a_medida_e_a_personalizacao_nao_o_tamanho():
    print("\n[3] A medida e a personalizacao — a casca nao conta como voz")
    codigo = _sem_comentario(_ler(*SAUDE))
    canonico = _ler(*CANONICO)

    checar("export function personalizacaoDoPrompt(" in codigo,
           "a personalizacao e extraida do prompt composto")
    checar("'so_guardrails'" in codigo,
           "e 'so as regras imutaveis' e um estado com nome proprio",
           "~560 chars de cabecalho passam em qualquer checagem de nao-vazio")

    # A detecção inteira depende destes dois cabeçalhos serem os MESMOS que o
    # compositor emite. Se um lado mudar o texto, a extração devolve o prompt
    # inteiro, a casca vira "ok", e a mudez volta a ser invisível — em silêncio.
    for const, esperado in (
        ("CABECALHO_PERSONALIZACAO", "=== PERSONALIZACAO DA CORRETORA"),
        ("CABECALHO_GUARDRAILS", "=== REGRAS IMUTAVEIS DO AUTOBROKERS"),
    ):
        checar(f"const {const} = '{esperado}'" in codigo,
               f"{const} e o texto esperado")
        checar(esperado in canonico,
               f"e o mesmo texto que composeSystemPromptWithGuardrails emite: {esperado[:34]}…",
               "se os dois lados divergirem, a casca volta a passar por voz")


def teste_a_rota_pede_a_coluna_e_nao_devolve_o_texto():
    print("\n[4] Sem a coluna, a deteccao e cega por falta de DADO")
    rota = _sem_comentario(_ler(*ROTA))

    checar("agent_system_prompt" in rota.split(".select(", 1)[1].split(")", 1)[0],
           "o select pede agent_system_prompt",
           "a logica mais fina do mundo nao ve o que nao foi consultado")
    checar("agent_system_prompt: a.agent_system_prompt" in rota,
           "e o valor chega em buildAgentDivergences")

    # O prompt pode conter dado da corretora. Sai o VEREDITO, nunca o texto.
    # `rsplit`: a rota tem várias respostas de erro antes da de sucesso, e é a
    # ÚLTIMA — a que carrega o diagnóstico — que interessa.
    resposta = rota.rsplit("return NextResponse.json(", 1)[1]
    checar("voice:" in rota and "mute:" in rota,
           "a resposta traz o veredito de voz")
    checar("prompt_chars" in rota and "personalization_chars" in rota,
           "e as MEDIDAS, que e o que permite conferir sem ler")
    checar("agent_system_prompt" not in resposta,
           "e o TEXTO do prompt nao sai na resposta",
           "CLAUDE.md §13.3: presenca e medida, nunca o conteudo")


def teste_a_tela_para_de_dizer_ativa_para_quem_esta_mudo():
    print("\n[5] A tela nao pode chamar de 'ativa' uma agente muda")
    tela = _ler(*TELA)
    checar("health.even?.mute" in tela and "health.core?.mute" in tela,
           "as duas fichas consultam o veredito de voz")
    # A ordem importa: se `is_active` for avaliado antes de `mute`, a ficha
    # volta a dizer "ativa" exatamente no caso que este conserto existe para
    # mostrar.
    ficha = tela.split("Even ·", 1)[1].split("</div>", 1)[0]
    checar(ficha.index("mute") < ficha.index("is_active"),
           "e a mudez e avaliada ANTES de 'ativa'",
           "ativo e mudo era o estado da AutoFleet; 'ativa' era a palavra na tela")


def teste_o_guarda_tem_como_falhar():
    print("\n[6] CONTROLE — a versao de ANTES reprova")
    # `isHealthy` como era: quatro tipos, nenhum deles sobre voz.
    antes = ("return !divs.some((d) => ['missing_core', 'missing_attendance', "
             "'duplicate_core', 'duplicate_attendance'].includes(d.kind));")

    def cobre_mudez(fonte: str) -> bool:
        return "'mute_core'" in fonte and "'mute_attendance'" in fonte

    checar("missing_core" in antes,
           "o controle e mesmo a funcao de saude",
           "se nem os tipos antigos estivessem la, ele nao provaria nada")
    checar(not cobre_mudez(antes),
           "a versao de ANTES nao cobre mudez — e por isso a AutoFleet passava",
           "se este caso ficar vermelho, o caso [2] passaria com ou sem o "
           "conserto e nao guarda nada (CLAUDE.md §9.3)")

    hoje = _sem_comentario(_ler(*SAUDE)).split("export function isHealthy(", 1)[1].split("\n}", 1)[0]
    checar(cobre_mudez(hoje),
           "e a de hoje cobre — os dois lados conseguem ser diferentes")


def main() -> int:
    print("=" * 72)
    print("O DIAGNOSTICO VE O AGENTE MUDO — P-37")
    print("=" * 72)

    for teste in (teste_a_deteccao_roda_de_verdade,
                  teste_a_mudez_derruba_a_saude,
                  teste_a_medida_e_a_personalizacao_nao_o_tamanho,
                  teste_a_rota_pede_a_coluna_e_nao_devolve_o_texto,
                  teste_a_tela_para_de_dizer_ativa_para_quem_esta_mudo,
                  teste_o_guarda_tem_como_falhar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("AGENTE SEM VOZ NAO PASSA MAIS POR SAUDAVEL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
