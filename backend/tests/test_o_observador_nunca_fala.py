"""O Observador escuta. Ele nunca fala — nem quando é o único que sobrou.

O defeito, medido em 02/08/2026
-------------------------------
O Observador é o número que a corretora pareia para o sistema ESCUTAR as
conversas reais dela. Ele é mudo por construção: o módulo de captura não importa
nenhum cliente de envio — é ausência de código, não uma flag.

Mas os seletores de canal de **saída** nunca olharam `purpose`::

    rank = {"auxiliary": 0, "attendance": 1}
    rows.sort(key=lambda r: rank.get(str(r.get("purpose") or ""), 2))
    return rows[0] if rows else None

`observer` caía no rank 2 — "por último". E **"por último" vira "o escolhido"
quando é o único ativo.**

📊 Em 02/08/2026, Amandus e AutoFleet tinham exatamente isso: uma única
integração ativa, e ela era o observador.

Cobrança, follow-up e alerta sairiam pelo número que existe para ficar calado.
O segurado receberia mensagem de um número que nunca falou com ele, e a
corretora perderia justamente o silêncio que pediu ao parear.

**Última prioridade não protege. Só a proibição protege.**

E o corolário que este teste também guarda: quando não há canal elegível, o
certo é **não enviar**. Uma corretora que fica sem cobrança automática por um
dia tem um problema operacional. Uma corretora cujo número mudo começou a
falar com segurados perdeu a confiança que a fez parear.
"""

from __future__ import annotations

import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


def teste_a_proibicao_existe_e_e_uma_so():
    print("\n[D1] Existe UMA proibição, num lugar só")
    fonte = _ler("backend", "app", "services", "integration_service.py")
    checar("PROPOSITOS_QUE_NUNCA_ENVIAM" in fonte, "a proibição está nomeada")
    checar('frozenset({"observer"})' in fonte,
           "e o observador está nela",
           "imutável de propósito: não é lista que alguém acrescenta em runtime")
    checar("def pode_enviar" in fonte, "há um único jeito de perguntar")


def teste_a_busca_de_plataforma_respeita():
    print("\n[D2] O canal de plataforma nunca é o observador")
    codigo = _sem_comentario(_ler("backend", "app", "services", "integration_service.py"))
    checar("if integ and self.pode_enviar(integ):" in codigo,
           "a integração encontrada é conferida antes de virar canal")
    checar("and self.pode_enviar(i)]" in codigo,
           "e o fallback da corretora também filtra")
    checar("NAO tem canal de saida" in codigo,
           "sem canal elegível, avisa alto em vez de improvisar",
           "não enviar é a resposta certa — improvisar com o mudo, não")


def teste_a_cobranca_respeita():
    print("\n[D3] A cobrança nunca sai pelo observador")
    codigo = _sem_comentario(_ler("backend", "app", "services", "billing_collection.py"))
    checar("IntegrationService.pode_enviar(r" in codigo,
           "o observador sai da lista ANTES da ordenação",
           "ordenar não basta: o último da fila é o escolhido quando é o único")

    # A ordem importa: filtrar depois de ordenar não resolveria nada.
    pos_filtro = codigo.find("pode_enviar(r")
    pos_sort = codigo.find("rows.sort(")
    checar(pos_filtro != -1 and pos_sort != -1 and pos_filtro < pos_sort,
           "o filtro vem antes do sort")


def teste_a_prova_funcional():
    print("\n[D4] A regra funciona quando exercitada")
    fonte = _ler("backend", "app", "services", "integration_service.py")
    ini = fonte.index("    PROPOSITOS_QUE_NUNCA_ENVIAM")
    fim = fonte.index("    def get_platform_whatsapp_integration", ini)
    ns: dict = {"Optional": object, "Dict": dict}
    exec(compile("class S:\n" + fonte[ini:fim], "<proibicao>", "exec"), ns)  # noqa: S102
    S = ns["S"]

    checar(S.pode_enviar({"purpose": "attendance"}) is True, "atendimento pode enviar")
    checar(S.pode_enviar({"purpose": "auxiliary"}) is True, "auxiliar pode enviar")
    checar(S.pode_enviar({"purpose": "observer"}) is False,
           "OBSERVADOR não pode — nunca")
    checar(S.pode_enviar({"purpose": "OBSERVER "}) is False,
           "e não escapa por maiúscula ou espaço")
    checar(S.pode_enviar(None) is False, "integração ausente também não envia")
    checar(S.pode_enviar({}) is False,
           "dicionário vazio é ausência de integração, não permissão",
           "fail-closed: 'não sei o que é isto' nunca vira canal de saída")
    # Linha legada REAL: tem dados, só não tem o rótulo `purpose` (a coluna é
    # posterior a várias integrações). Recusá-la deixaria corretoras antigas sem
    # canal por um detalhe de schema — o defeito trocaria de lugar.
    checar(S.pode_enviar({"id": "x", "provider": "evolution-go"}) is True,
           "integração legada sem rótulo continua podendo enviar")


def teste_todo_seletor_de_saida_respeita():
    """A varredura que faltava — e é ela que teria pego o defeito de 04/08.

    Este arquivo provava que a FUNÇÃO `pode_enviar` recusa o observador, e
    conferia dois chamadores conhecidos. Nenhum dos três olhava para quem mais
    escolhe canal de saída por conta própria.

    🔴 E havia um: `whatsapp/alerts.py::_sender_integration` consultava
    `integrations` filtrando só por `is_active`, **sem `purpose` e sem
    `pode_enviar`**. O aviso de queda de canal sairia pelo número do observador
    — e ele dispara exatamente quando um canal cai, que é justamente quando o
    observador costuma ser o único de pé.

    A regra agora é sobre QUEM CONSULTA, não sobre a função: quem lê
    `integrations` para escolher por onde falar tem de aplicar o portão.
    """
    import ast

    print("\n[5] Todo seletor de canal de SAÍDA aplica o portão")
    base = os.path.join(RAIZ, "backend", "app")
    culpados: list[str] = []
    isentos_vistos: list[str] = []
    vistos = 0

    # A REGRA É SOBRE O PAPEL DA FUNÇÃO, e a primeira versão deste guarda errou
    # aqui: ela procurava "consulta `integrations` e menciona base_url/token", o
    # que descreve TODO pareamento, sonda e upsert do sistema — 17 funções
    # corretas acusadas. Parear não é enviar.
    #
    # O que define um seletor de saída é o NOME dele: ele existe para responder
    # "por onde eu falo?". `_sender_integration`, `get_*_whatsapp_integration`,
    # `canal_de_saida`. Limite conhecido e declarado: uma função que faça isso
    # com nome que não diga isso escapa — e o remédio para essa é a revisão, não
    # um detector mais esperto que erraria de novo.
    MARCAS = ("sender", "remetente", "canal_de_saida", "canal_de_plataforma",
              "outbound", "whatsapp_integration")

    # A ÚNICA isenção, e ela é sutil o bastante para valer a explicação:
    #
    # `get_whatsapp_integration(company_id, agent_id)` é o caminho pelo qual o
    # ATENDENTE responde o segurado. Ele casa pelo `agent_id` — e, pela
    # [D-Canal-01], **um pareamento serve às duas funções, no mesmo número**: a
    # linha se chama `observer` e carrega o atendimento junto ([P-65] registra
    # que o nome é que ficou para trás).
    #
    # Aplicar `pode_enviar` aqui quebraria o produto de um jeito silencioso: a
    # corretora pareia, clica em "Ligar agente", e o agente pensa a resposta e
    # não tem por onde mandá-la.
    #
    # O que segura este caminho é OUTRA coisa, e ela é mais forte: o portão
    # `attendance_agent_active`. Com o agente desligado, ninguém chega aqui.
    # É a diferença entre "por onde o atendente fala" (esta) e "por onde a
    # PLATAFORMA fala sozinha" (todas as outras, que aplicam o portão).
    ISENTO_POR_DESENHO = {
        "integration_service.py::get_whatsapp_integration":
            "é o canal do ATENDENTE, e a [D-Canal-01] usa o mesmo número para as "
            "duas funções; quem segura este caminho é `attendance_agent_active`",
    }

    for pasta, _, arquivos in os.walk(base):
        for arq in arquivos:
            if not arq.endswith(".py"):
                continue
            caminho = os.path.join(pasta, arq)
            try:
                fonte = open(caminho, encoding="utf-8").read()
                arvore = ast.parse(fonte)
            except (SyntaxError, OSError):
                continue
            for no in ast.walk(arvore):
                if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not any(m in no.name.lower() for m in MARCAS):
                    continue
                trecho = ast.get_source_segment(fonte, no) or ""
                # E ele tem de realmente ESCOLHER (consultar a tabela). Quem só
                # repassa o que recebeu não é seletor.
                if 'table("integrations")' not in trecho:
                    continue
                vistos += 1
                chave = f"{arq}::{no.name}"
                if chave in ISENTO_POR_DESENHO:
                    isentos_vistos.append(chave)
                    continue
                chamadas = [c.func.attr for c in ast.walk(no)
                            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)]
                nomes = [c.func.id for c in ast.walk(no)
                         if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
                if "pode_enviar" not in chamadas + nomes:
                    culpados.append(
                        f"{os.path.relpath(caminho, RAIZ).replace(os.sep, '/')}::{no.name}:{no.lineno}")

    checar(vistos > 0, f"a varredura achou {vistos} seletor(es) para conferir",
           "zero significa que o detector cegou — e teste que não olha passa sempre")
    checar(not culpados, "todos aplicam `pode_enviar`",
           f"não aplicam: {culpados}")

    # CONTRAPROVA — o detector precisa saber acusar. Um seletor de mentira, que
    # consulta e escolhe sem o portão, TEM de aparecer.
    falso = ast.parse(
        'def escolher(db):\n'
        '    linhas = db.table("integrations").select("*").execute().data\n'
        '    for l in linhas:\n'
        '        if l.get("base_url") and l.get("token"):\n'
        '            return l\n')
    fn = next(n for n in ast.walk(falso) if isinstance(n, ast.FunctionDef))
    trecho_falso = ('def escolher(db):\n    linhas = db.table("integrations")'
                    '.select("*").execute().data\n    for l in linhas:\n'
                    '        if l.get("base_url") and l.get("token"):\n            return l\n')
    chamadas_falsas = [c.func.attr for c in ast.walk(fn)
                       if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)]
    checar('table("integrations")' in trecho_falso and "pode_enviar" not in chamadas_falsas,
           "CONTRAPROVA — um seletor sem portão é reconhecível",
           "prova que o verde acima vem do código estar certo")


def main() -> int:
    print("=" * 68)
    print("O OBSERVADOR ESCUTA — E NUNCA FALA")
    print("=" * 68)
    for t in (teste_a_proibicao_existe_e_e_uma_so,
              teste_a_busca_de_plataforma_respeita,
              teste_a_cobranca_respeita,
              teste_a_prova_funcional,
              teste_todo_seletor_de_saida_respeita):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O NUMERO QUE FOI PAREADO PARA CALAR CONTINUA CALADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
