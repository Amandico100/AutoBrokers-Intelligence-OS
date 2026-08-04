"""O portão do prompt é UM SÓ — e os três caminhos que o furavam passam por ele.

P-36. O portão existia e funcionava. O problema era ele estar em UM caminho.
-----------------------------------------------------------------------------
A SPEC-063 Bloco P construiu um portão que mede o prompt final E a
personalização em separado, e relê do banco depois de escrever: se voltar
vazio, o agente nasce DESLIGADO em vez de ativo e mudo. Ele foi instalado em
``lib/admin/provision-tenant.ts`` e só lá.

Outros três arquivos escreviam a MESMA coluna ``agents.agent_system_prompt``
sem passar por ele:

    lib/admin/tenant-agent-store.ts      salvar a tela de Personalização
    lib/admin/release-rollout-store.ts   descer uma release para a corretora
    lib/admin/blueprint-studio-store.ts  criar o Source Agent no Studio

📊 Medido em 02/08/2026 no banco de produção (auditoria do Bloco 0,
``docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md``, Parte C.6)::

    corretora    papel   blueprint              prompt
    Resulta      core    autobrokers-core-v1    650 chars
    AutoFleet    core    autobrokers-core-v1        0     <- ATIVO
    Amandus      core    core-v1                7.914 chars

Mesmo blueprint, mesmo papel, resultado diferente. **Foi por um destes três
caminhos que a AutoFleet ficou com o agente ativo e mudo** — e com o defeito
de resolução por antiguidade, era esse agente que responderia o segurado.

Por que a barra é dupla, e não "prompt não vazio"
-------------------------------------------------
``composeSystemPromptWithGuardrails('')`` devolve ~560 caracteres de cabeçalho
e regras, e nenhuma instrução sobre o que o agente é. Essa casca passa em
qualquer checagem de "não vazio" e continua muda. Por isso o portão mede o
prompt final (mínimo 400) e a personalização (mínimo 120) em separado.

E por que o Studio tem um portão PRÓPRIO
----------------------------------------
Lá o prompt é um TEMPLATE de autoria: ``{{placeholder}}`` é o ponto, não
defeito, e nada soma a casca de guardrails por cima. A medida dupla não se
aplica; o que sobra, e é o que mata, é o vazio. E vazio ali custa mais caro:
um Source Agent mudo vira release, e a release desce para TODAS as corretoras.

A linha de CONTROLE deste arquivo
---------------------------------
Um teste que lê código-fonte passa fácil demais. O caso [5] roda a MESMA
verificação sobre o código como ele era ANTES do conserto — copiado verbatim
para dentro deste arquivo. Se ele ficar verde, esta suíte inteira não está
guardando nada (CLAUDE.md §9.3).
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

PORTAO = ("lib", "admin", "provision-tenant.ts")
LOJA_TENANT = ("lib", "admin", "tenant-agent-store.ts")
LOJA_ROLLOUT = ("lib", "admin", "release-rollout-store.ts")
LOJA_STUDIO = ("lib", "admin", "blueprint-studio-store.ts")


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


def _corpo(fonte: str, assinatura: str) -> str:
    """Recorta o corpo de uma função até a próxima declaração de topo.

    Comparar posições no arquivo inteiro mentiria: o portão de uma função
    ficaria "antes" da escrita de outra e o caso passaria de graça.
    """
    if assinatura not in fonte:
        return ""
    depois = fonte.split(assinatura, 1)[1]
    for corte in ("\nexport async function ", "\nexport function ",
                  "\nasync function ", "\nfunction ", "\nexport const "):
        depois = depois.split(corte, 1)[0]
    return depois


def portao_antes_da_escrita(corpo: str, marca_portao: str, marca_escrita: str) -> bool:
    """A pergunta inteira: o portão roda ANTES de a coluna ser escrita?

    Portão depois da escrita documenta o defeito; não impede.
    """
    if marca_portao not in corpo or marca_escrita not in corpo:
        return False
    return corpo.index(marca_portao) < corpo.index(marca_escrita)


# ---------------------------------------------------------------------------
# CONTROLE — o código como ele era ANTES do conserto (verbatim de `git show`).
# Se o caso [5] ficar verde, a verificação não distingue nada.
# ---------------------------------------------------------------------------

CONTROLE_ANTES_DO_CONSERTO = """
export async function patchTenantAgentConfig(supabase, companyId, role, input) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  const v = validateTenantAgentInput(bp, input);
  if (!v.ok) return { ok: false as const, error: 'validation_failed', errors: v.errors };

  const upd = computeAgentConfigUpdate(bp, name, agent.context_package, v.clean);
  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };
  return { ok: true as const, rejected: upd.rejected, config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package) };
}
"""


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def teste_o_portao_e_uma_funcao_reutilizavel():
    print("\n[1] O portão virou função — deixou de ser um trecho copiável")
    codigo = _sem_comentario(_ler(*PORTAO))

    checar("export function problemasDoPrompt(" in codigo,
           "o portão original continua de pé")
    checar("export function problemasDoUpdate(" in codigo,
           "e ganhou a forma que os outros caminhos conseguem chamar",
           "cada um deles teria de remontar o par (prompt final, personalização) "
           "na mão — foi remontá-lo errado, ou não remontá-lo, que abriu o furo")
    checar("export function problemasDoPromptDeAutoria(" in codigo,
           "existe a variante de AUTORIA (Studio), onde {{placeholder}} é o ponto")
    checar("export async function conferirPromptGravado(" in codigo,
           "e a releitura pós-escrita saiu de dentro do provisionamento",
           "estava embutida em ensureAgentByRole e por isso não servia a ninguém")

    conf = _corpo(codigo, "export async function conferirPromptGravado(")
    checar("is_active: false" in conf and "agent_enabled: false" in conf,
           "a releitura DESLIGA o agente que ficou mudo",
           "reportar não basta: um agente ativo sem instrução responde sem trava")
    checar(".eq('company_id', companyId)" in conf,
           "e nunca escreve sem o filtro de tenant (CLAUDE.md §7)")

    # O portão não pode ser cópia colada em cada arquivo — seria três portões.
    for arquivo in (LOJA_TENANT, LOJA_ROLLOUT, LOJA_STUDIO):
        fonte = _sem_comentario(_ler(*arquivo))
        checar("from '@/lib/admin/provision-tenant'" in fonte,
               f"{arquivo[-1]} IMPORTA o portão em vez de reimplementá-lo")
        checar("PROMPT_MINIMO_CHARS =" not in fonte and "function problemasDoPrompt(" not in fonte,
               f"{arquivo[-1]} não tem um segundo portão ao lado (CLAUDE.md §5)")


def teste_a_tela_de_personalizacao_nao_emudece_o_agente():
    print("\n[2] Salvar a Personalização: o caminho mais quente dos três")
    codigo = _sem_comentario(_ler(*LOJA_TENANT))
    escrita = ".update({ ...upd.columns"

    for fn in ("export async function patchTenantAgentConfig(",
               "export async function resetTenantAgentConfig("):
        corpo = _corpo(codigo, fn)
        checar(bool(corpo), f"{fn[22:-1]} existe")
        checar(portao_antes_da_escrita(corpo, "problemasDoUpdate(bp, upd)", escrita),
               f"{fn[22:-1]}: o portão roda ANTES do update",
               "esta função reescreve o prompt INTEIRO a cada save")
        checar("conferirPromptGravado(supabase, companyId, agent.id" in corpo,
               f"{fn[22:-1]}: e o banco é relido depois",
               "'gravei' tem de ser fato lido de volta, não requisição enviada")
        i_escrita = corpo.index(escrita)
        checar(corpo.index("conferirPromptGravado(") > i_escrita,
               f"{fn[22:-1]}: a releitura vem DEPOIS da escrita",
               "antes dela, releria o estado velho e aprovaria o novo")

    # Resetar também reescreve tudo: era o botão capaz de apagar a voz do agente.
    reset = _corpo(codigo, "export async function resetTenantAgentConfig(")
    checar("'prompt_invalido'" in reset,
           "e o reset recusa com nome próprio quando o blueprint global não presta")


def teste_a_release_nao_desce_um_prompt_vazio():
    print("\n[3] Rollout de release: o de maior alcance")
    codigo = _sem_comentario(_ler(*LOJA_ROLLOUT))
    corpo = _corpo(codigo, "export async function applyRollout(")

    checar(bool(corpo), "applyRollout existe")
    checar(portao_antes_da_escrita(corpo, "problemasDoUpdate(bp, upd)", "supabase.rpc('apply_release_rollout'"),
           "o portão roda ANTES da RPC que grava",
           "o blueprint aqui não é o do código: vem dentro do artefato da "
           "release (artifactToBlueprint). Release publicada com template vazio "
           "materializa a casca de guardrails e a desce sobre um agente ATIVO")
    checar("conferirPromptGravado(supabase, companyId, agent.id" in corpo,
           "e o banco é relido depois da RPC",
           "quem escreve é uma função do Postgres — o que ela gravou não está "
           "em nenhuma variável do TypeScript")
    checar(corpo.index("conferirPromptGravado(") > corpo.index("supabase.rpc('apply_release_rollout'"),
           "a releitura vem DEPOIS da RPC")
    checar("'prompt_invalido'" in corpo,
           "e a recusa tem nome próprio, distinto de 'apply_failed'")


def teste_o_studio_nao_publica_um_source_agent_mudo():
    print("\n[4] Studio: o vazio que não fica numa corretora só")
    codigo = _sem_comentario(_ler(*LOJA_STUDIO))

    fonte_agent = _corpo(codigo, "async function ensureSourceAgent(")
    checar(portao_antes_da_escrita(fonte_agent, "problemasDoPromptDeAutoria(", ".insert(sourceAgentPayload("),
           "ensureSourceAgent: o portão de autoria roda antes do insert",
           "um Source Agent mudo vira release, e a release desce para TODAS "
           "as corretoras que a receberem")
    checar("PERSONALIZACAO_MINIMA_CHARS" in fonte_agent,
           "e a barra do Source Agent canônico é a da personalização (120)",
           "um template de blueprint abaixo disso está quebrado por definição")
    checar(".select('id, agent_system_prompt')" in fonte_agent,
           "o insert devolve o prompt gravado")
    checar("'prompt_vazio_apos_insert:source_agent_desligado'" in fonte_agent,
           "e vazio depois do insert é ERRO, com nome próprio")

    fonte_aux = _corpo(codigo, "export async function createSourceAuxiliary(")
    checar("const promptDeAutoria =" in fonte_aux,
           "o prompt do auxiliar sai de uma variável NOMEADA",
           "inline dentro do insert, não havia o que examinar antes de gravar")
    checar(portao_antes_da_escrita(fonte_aux, "problemasDoPromptDeAutoria(promptDeAutoria", "agent_system_prompt: promptDeAutoria"),
           "createSourceAuxiliary: o portão roda antes do insert")
    checar("problemasDoPromptDeAutoria(promptDeAutoria, 1)" in fonte_aux,
           "e a barra aqui é só 'não vazio', explicitamente",
           "auxiliar sem descrição nasce com um esboço de uma frase — isso é o "
           "produto. O que não pode existir é a linha com prompt em branco")


def teste_a_verificacao_tem_como_falhar():
    print("\n[5] CONTROLE — a mesma checagem, no código de ANTES")
    escrita = ".update({ ...upd.columns"
    antes = _corpo(_sem_comentario(CONTROLE_ANTES_DO_CONSERTO),
                   "export async function patchTenantAgentConfig(")

    checar(escrita in antes,
           "o controle é mesmo o caminho que gravava a coluna",
           "se nem a escrita estivesse lá, o controle não provaria nada")
    checar(not portao_antes_da_escrita(antes, "problemasDoUpdate(bp, upd)", escrita),
           "o código de ANTES REPROVA na verificação do caso [2]",
           "se este caso ficar vermelho, a verificação passa com ou sem o "
           "conserto — e não guarda nada (CLAUDE.md §9.3)")
    checar("conferirPromptGravado(" not in antes,
           "e o código de ANTES não relia o banco",
           "era exatamente o que faltava para o agente mudo ser percebido")

    # O inverso também precisa ser verdade: a checagem aprova o código de HOJE.
    hoje = _corpo(_sem_comentario(_ler(*LOJA_TENANT)),
                  "export async function patchTenantAgentConfig(")
    checar(portao_antes_da_escrita(hoje, "problemasDoUpdate(bp, upd)", escrita),
           "e APROVA o código de hoje — os dois lados conseguem ser diferentes")


def teste_nenhuma_escrita_do_prompt_ficou_de_fora():
    print("\n[6] Varredura: toda escrita da coluna passa por um portão")
    # Um conserto que fecha três portas e deixa a quarta aberta não conserta
    # nada. A varredura é sobre a coluna, não sobre as funções que eu lembrei.
    esperado = {
        "lib/admin/provision-tenant.ts": {"problemasDoUpdate(", "problemasDoPrompt(",
                                          "prompt_vazio_apos_insert"},
        "lib/admin/tenant-agent-store.ts": {"problemasDoUpdate(", "conferirPromptGravado("},
        "lib/admin/release-rollout-store.ts": {"problemasDoUpdate(", "conferirPromptGravado("},
        "lib/admin/blueprint-studio-store.ts": {"problemasDoPromptDeAutoria(", "conferirPromptGravado("},
    }
    for caminho, marcas in esperado.items():
        fonte = _sem_comentario(_ler(*caminho.split("/")))
        escreve = "agent_system_prompt:" in fonte or "upd.columns" in fonte
        checar(escreve, f"{caminho} de fato escreve o prompt",
               "se parou de escrever, este caso virou verdade vencida (§9.3)")
        for marca in sorted(marcas):
            checar(marca in fonte, f"{caminho} usa {marca}")


def main() -> int:
    print("=" * 70)
    print("O PORTÃO DO PROMPT É UM SÓ — P-36")
    print("=" * 70)

    for teste in (teste_o_portao_e_uma_funcao_reutilizavel,
                  teste_a_tela_de_personalizacao_nao_emudece_o_agente,
                  teste_a_release_nao_desce_um_prompt_vazio,
                  teste_o_studio_nao_publica_um_source_agent_mudo,
                  teste_a_verificacao_tem_como_falhar,
                  teste_nenhuma_escrita_do_prompt_ficou_de_fora):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("UM PORTAO SO, E OS TRES CAMINHOS PASSAM POR ELE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
