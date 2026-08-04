"""O portal nunca abre duas vezes o mesmo pedido.

Por que este teste existe
-------------------------
📊 `docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §7, captura do Founder em
06/07/2026: o `Nº do atendimento` aparece no passo 7, **no topo da tela, antes
da escolha da loja**. O pedido já existe na seguradora antes de o fluxo
terminar. O próprio mapa escreve a consequência:

    "repetir o fluxo cria um segundo atendimento, não corrige o primeiro"

E nada impedia a repetição. 📊 Medido em 04/08/2026 no Supabase
`dcajcvlzcjbmyapmklil`:

    SELECT count(*), count(DISTINCT company||placa||data_dano||peca)
      FROM portal_jobs WHERE journey='abrir_atendimento';
    -->  39 jobs   para   5 pedidos distintos

Um único pedido — placa QJQ0A91, dano em 05/07/2026, "vidro de porta" — tem 30
jobs. Não machucou ninguém por um motivo que não vai durar: o gate do worker
está desligado e nenhum dos 39 chegou ao passo 7.

Quem chama a tool é um LLM. O segurado pergunta "e aí, abriu?" e o modelo pode
chamar `portal_action` de novo — 📊 ainda mais porque o poll do `_arun` desiste
em 150s (`POLL_TIMEOUT_S`) e responde "ainda não processou" com o job vivo.

O que este teste protege
------------------------
1. que a chave identifique o **pedido**, não o texto: descrição reformulada
   pelo segurado não pode virar um pedido novo;
2. que ela **continue sabendo separar** o que é de fato outro pedido — outra
   peça, outro lado, outra corretora;
3. que o `_arun` **procure antes de inserir**, e filtre por corretora;
4. que a corrida de dois inserts caia no caminho "achei um existente" em vez de
   estourar o atendimento;
5. que o predicado do índice único e a noção de "vivo" no código **não
   divirjam** — se divergirem, o insert estoura 23505 num caminho que a leitura
   jurava estar livre.

O controle, que é o que dá direito à conclusão
----------------------------------------------
Uma função que devolvesse sempre a mesma string passaria em todos os casos de
"mesma chave". Por isso cada bateria tem uma linha de CONTROLE: uma entrada que
**tem de** gerar chave diferente. Sem ela, o verde não significa nada
(CLAUDE.md §9.2 e §9.3).

Rodar: python backend/tests/test_o_portal_nao_abre_duas_vezes_o_mesmo_pedido.py
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
RAIZ_REPO = RAIZ_BACKEND.parent
FALHAS: list[str] = []


def checar(nome: str, condicao: bool, detalhe: str = "") -> None:
    if condicao:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# --- carga do módulo puro, sem arrastar langgraph nem o pacote `app` inteiro ---
#
# `app/__init__.py` puxa `app.agents.graph`, que importa langgraph — indisponível
# fora do contêiner. Por isso os três primeiros pacotes entram como casca vazia.
#
# `app.services`, ao contrário, entra com o caminho REAL: `portal_params` importa
# de lá o catálogo de perguntas do portal, e falsificá-lo esconderia a única
# coisa que este teste precisa ver de verdade — o FORMATO do `params` que sai de
# `build_portal_params`, que é de onde a chave é lida.
if str(RAIZ_BACKEND) not in sys.path:
    sys.path.insert(0, str(RAIZ_BACKEND))
for _nome in ("app", "app.agents", "app.agents.tools"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []
_svc = sys.modules.setdefault("app.services", types.ModuleType("app.services"))
_svc.__path__ = [str(RAIZ_BACKEND / "app" / "services")]

_spec = importlib.util.spec_from_file_location(
    "app.agents.tools.portal_params", RAIZ_BACKEND / "app/agents/tools/portal_params.py")
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)

# 📊 A corretora e o pedido são os reais do job duplicado 30 vezes.
EMPRESA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"
OUTRA_EMPRESA = "11111111-2222-3333-4444-555555555555"

PERFIL = {"nome": "Auto Fleet Corretora", "email": "operacional@autofleet.com.br",
          "telefone": "4833646664", "cpf_cnpj": "00000000000191"}

INFOCAP = {
    "ok": True, "status": "found",
    "policy": {"numapo": "312520261149211", "seguradora": "LIBERTY SEGUROS S/A",
               "seguradora_abrev": "LIBE", "active": True},
    "vehicle": {"placa": "QJQ0A91", "chassi": "98867513WJKH74022",
                "veiculo": "COMPASS LIMITED 2.0 4X2 16V AUT. (FLEX)"},
    "client": {"nome": "RAFAEL LACAU DA SILVEIRA", "cpf_cnpj": "03074327936",
               "logradouro": "RUA CAPITÃO ROMUALDO DE BARROS", "numero": "705",
               "bairro": "SACO DOS LIMÕES", "cidade": "FLORIANÓPOLIS",
               "estado": "SC", "cep": "88040-600"},
}


def pedido(peca="vidro de porta", data="05/07/2026", placa="QJQ0A91", descricao="") -> dict:
    """O formato mínimo que `chave_de_idempotencia` lê dos params."""
    return {"placa": placa, "data_dano": data,
            "dano": {"peca": peca, "descricao": descricao,
                     "como": "encontrou o veiculo danificado", "onde": "urbano"}}


def _ler(*partes: str) -> str:
    with open(os.path.join(str(RAIZ_REPO), *partes), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------

def teste_a_chave_identifica_o_pedido():
    print("\n[1] A chave é a impressão digital do PEDIDO, não do texto")

    base = pp.chave_de_idempotencia(pedido(), EMPRESA)
    checar("o mesmo pedido, chamado de novo, dá a mesma chave",
           base == pp.chave_de_idempotencia(pedido(), EMPRESA), base)

    # 🔴 O caso que motivou excluir a descrição livre: o segurado reconta a
    # mesma história com outras palavras quando o agente pergunta de novo.
    reformulado = pedido(descricao="quebraram o vidro do meu carro no estacionamento")
    outra_vez = pedido(descricao="encontrei o carro arrombado, o vidro estava no chao")
    checar("descrição reformulada NÃO cria pedido novo",
           pp.chave_de_idempotencia(reformulado, EMPRESA)
           == pp.chave_de_idempotencia(outra_vez, EMPRESA),
           "o mesmo fato contado com outras palavras viraria um SEGUNDO atendimento")

    # CONTROLE: sem esta linha, uma função que devolvesse sempre "" passaria em
    # tudo acima. Aqui ela é obrigada a discordar de si mesma.
    diferentes = {
        pp.chave_de_idempotencia(pedido(), EMPRESA),
        pp.chave_de_idempotencia(pedido(peca="parabrisa"), EMPRESA),
        pp.chave_de_idempotencia(pedido(data="06/07/2026"), EMPRESA),
        pp.chave_de_idempotencia(pedido(placa="ABC1D23"), EMPRESA),
    }
    checar("CONTROLE — a função consegue produzir chaves diferentes",
           len(diferentes) == 4,
           f"{len(diferentes)} chaves distintas de 4 entradas distintas: {sorted(diferentes)}")


def teste_o_que_e_outro_pedido_continua_sendo_outro():
    print("\n[2] CONTROLE — o que é de fato outro pedido gera outra chave")
    base = pp.chave_de_idempotencia(pedido(), EMPRESA)

    checar("peça diferente → chave diferente",
           pp.chave_de_idempotencia(pedido(peca="parabrisa"), EMPRESA) != base,
           "sem isto, o segundo vidro quebrado nunca seria aberto")

    # 📊 Mapa §3, texto literal do portal: "O atendimento web permite apenas a
    # SELEÇÃO de 1 (um) ITEM… Se o item possuir lateralidade, será necessário
    # abrir uma nova solicitação para o outro lado."
    dianteira = pp.chave_de_idempotencia(pedido(peca="vidro da porta dianteira"), EMPRESA)
    traseira = pp.chave_de_idempotencia(pedido(peca="vidro da porta traseira"), EMPRESA)
    checar("lateralidade/posição → pedidos separados", dianteira != traseira,
           "dois vidros = dois atendimentos; fundir deixaria um lado quebrado")

    esquerdo = pp.chave_de_idempotencia(pedido(peca="retrovisor esquerdo"), EMPRESA)
    direito = pp.chave_de_idempotencia(pedido(peca="retrovisor direito"), EMPRESA)
    checar("lado esquerdo ≠ lado direito", esquerdo != direito)

    checar("data do dano diferente → chave diferente",
           pp.chave_de_idempotencia(pedido(data="06/07/2026"), EMPRESA) != base)

    checar("placa diferente → chave diferente",
           pp.chave_de_idempotencia(pedido(placa="ABC1D23"), EMPRESA) != base,
           "o mesmo dano em dois carros da mesma família são dois pedidos")


def teste_o_isolamento_entre_corretoras():
    print("\n[3] Multi-tenant: a chave não atravessa corretora (CLAUDE.md §7)")
    a = pp.chave_de_idempotencia(pedido(), EMPRESA)
    b = pp.chave_de_idempotencia(pedido(), OUTRA_EMPRESA)
    checar("corretora diferente → chave diferente", a != b,
           "duas corretoras com a mesma placa bloqueariam o pedido uma da outra")
    checar("a corretora aparece na chave", EMPRESA in a, a)

    # A tool passa company_id por fora porque build_portal_params não o coloca
    # nos params. Aceitar as duas formas evita um buraco silencioso.
    embutido = pp.chave_de_idempotencia({**pedido(), "company_id": EMPRESA})
    checar("company_id embutido nos params vale o mesmo que por parâmetro",
           embutido == a, f"{embutido} != {a}")


def teste_a_grafia_nao_inventa_pedido():
    print("\n[4] Caixa, acento, pontuação e ligação não criam pedido novo")
    base = pp.chave_de_idempotencia(pedido(), EMPRESA)

    for variacao in ("Vidro da Porta", "VIDRO DE PORTA", "vidro  de   porta",
                     "vidro de porta.", "Vídro dá Pórta", "porta - vidro"):
        checar(f"'{variacao}' bate com 'vidro de porta'",
               pp.chave_de_idempotencia(pedido(peca=variacao), EMPRESA) == base,
               pp.chave_de_idempotencia(pedido(peca=variacao), EMPRESA))

    for placa in ("qjq0a91", "QJQ-0A91", " QJQ0A91 "):
        checar(f"placa '{placa}' bate com 'QJQ0A91'",
               pp.chave_de_idempotencia(pedido(placa=placa), EMPRESA) == base)

    for data in ("5/7/2026", "05-07-2026", "05.07.2026", "05/07/26"):
        checar(f"data '{data}' bate com '05/07/2026'",
               pp.chave_de_idempotencia(pedido(data=data), EMPRESA) == base,
               pp.chave_de_idempotencia(pedido(data=data), EMPRESA))

    # CONTROLE da normalização: ela não pode ser tão agressiva a ponto de
    # apagar a diferença entre dias e entre peças de verdade.
    checar("CONTROLE — a normalização não achata datas diferentes",
           pp.chave_de_idempotencia(pedido(data="07/05/2026"), EMPRESA) != base,
           "07/05 e 05/07 são dias diferentes")
    checar("CONTROLE — a normalização não achata peças diferentes",
           pp.chave_de_idempotencia(pedido(peca="vidro de janela"), EMPRESA) != base)


def teste_a_chave_nasce_dos_params_de_verdade():
    print("\n[5] A chave funciona sobre o params REAL, não só sobre o do teste")
    flat = {"cpf_cnpj": "03074327936", "data_dano": "05/07/2026",
            "peca": "vidro de porta", "como_ocorreu": "encontrou o veiculo danificado",
            "onde_ocorreu": "urbano",
            "descricao": "o carro estava estacionado e o vidro da porta foi quebrado"}
    params, erro = pp.build_portal_params(flat, PERFIL, INFOCAP)
    checar("build_portal_params produziu params", erro is None and params is not None, str(erro))
    if not params:
        return

    real = pp.chave_de_idempotencia(params, EMPRESA)
    checar("a chave do params real não é vazia", bool(real), real)
    checar("a chave do params real bate com a do pedido equivalente",
           real == pp.chave_de_idempotencia(pedido(), EMPRESA),
           f"{real} != {pp.chave_de_idempotencia(pedido(), EMPRESA)}")

    # Se alguém mudar o formato de `params` (renomear dano.peca, por exemplo),
    # a chave muda em silêncio e o guarda deixa de casar com os jobs já vivos.
    outro_relato = {**flat, "descricao": "passei numa pedra e o vidro quebrou, foi hoje de manha"}
    params2, _ = pp.build_portal_params(outro_relato, PERFIL, INFOCAP)
    checar("mudar só o relato não muda a chave do params real",
           pp.chave_de_idempotencia(params2, EMPRESA) == real)


def teste_a_chave_falha_aberta_quando_nao_ha_pedido():
    print("\n[6] Sem corretora, placa ou data não há pedido — e a chave é vazia")
    checar("sem corretora → sem chave", pp.chave_de_idempotencia(pedido(), "") == "")
    checar("sem placa → sem chave", pp.chave_de_idempotencia(pedido(placa=""), EMPRESA) == "")
    checar("sem data → sem chave", pp.chave_de_idempotencia(pedido(data=""), EMPRESA) == "")
    checar("params vazio → sem chave", pp.chave_de_idempotencia(None, EMPRESA) == "")

    # Fail-open de propósito: chave vazia vira NULL no banco, e o índice parcial
    # ignora NULL. O guarda nunca pode ser o motivo de um acionamento não sair.
    checar("CONTROLE — com os três dados, a chave existe",
           pp.chave_de_idempotencia(pedido(), EMPRESA) != "",
           "se esta falhar, os quatro casos acima passariam por engano")


def teste_a_frase_nao_mente_para_o_segurado():
    print("\n[7] A frase de 'já existe' pode ser repetida ao segurado sem mentir")
    concluido = pp.frase_de_pedido_ja_existente(
        {"status": "done", "evidence": {"message": "protocolo 22842291"}})
    checar("done: repassa o resultado real do job", "22842291" in concluido, concluido)
    checar("done: diz que NÃO abriu outro", "nao abri outro" in concluido.lower()
           or "não abri outro" in concluido.lower(), concluido)

    parado = pp.frase_de_pedido_ja_existente(
        {"status": "needs_human", "evidence": {"message": "cheguei na confirmacao (80%)",
                                               "stage_80": "Confirme a peca"}})
    checar("needs_human: diz que o pedido está aberto e em confirmação",
           "confirmacao" in parado.lower(), parado)

    # 🔴 Aqui morava a mentira possível: `format_result({"status": "queued"})`
    # começa com "Enfileirei o acionamento" — e quem se anexou a um job em curso
    # NÃO enfileirou nada nesta chamada.
    em_curso = pp.frase_de_pedido_ja_existente({"status": "queued"})
    checar("em curso: NÃO afirma ter enfileirado nesta chamada",
           "enfileirei" not in em_curso.lower(), em_curso)
    checar("em curso: diz que já existe um acionamento em andamento",
           "em andamento" in em_curso.lower(), em_curso)

    # A saída honesta para o caso legítimo do mapa §3.
    for frase in (concluido, parado, em_curso):
        checar("a frase ensina como pedir o OUTRO lado/peça",
               "separado" in frase.lower() and "lado" in frase.lower(), frase[:80])

    # CONTROLE: as três frases têm de ser distinguíveis entre si.
    checar("CONTROLE — as frases de done e de em-curso são diferentes",
           concluido != em_curso)


def teste_a_tool_procura_antes_de_inserir():
    print("\n[8] O `_arun` procura o pedido ANTES de criar outro")
    fonte = _ler("backend", "app", "agents", "tools", "portal_tool.py")

    checar("a tool importa a chave de idempotência",
           "chave_de_idempotencia" in fonte)

    i_chave = fonte.find("chave_de_idempotencia(params")
    i_busca = fonte.find("_buscar_pedido_vivo(chave)")
    i_insert = fonte.find('table("portal_jobs").insert(')
    checar("a chave é calculada antes do insert", 0 < i_chave < i_insert,
           f"chave={i_chave} insert={i_insert}")
    checar("a busca pelo pedido vivo acontece antes do insert", 0 < i_busca < i_insert,
           f"busca={i_busca} insert={i_insert}")

    # CLAUDE.md §7: a leitura tem de filtrar por corretora, mesmo com a chave já
    # embutindo a corretora. Guarda que depende do formato de uma string não é guarda.
    #
    # A fatia é do CORPO do método, delimitada pelos dois `def`. A primeira
    # versão deste teste cortava por `_buscar_pedido_vivo` — que aparece quatro
    # vezes no arquivo — e lia o trecho errado. Ele falhou, e foi assim que se
    # soube que estava olhando para o lugar errado.
    corpo_busca = fonte.split("def _buscar_pedido_vivo", 1)[-1].split("def _e_chave_duplicada", 1)[0]
    checar("a busca filtra por corretora",
           'eq("company_id", self.company_id)' in corpo_busca,
           "sem isto, a chave de uma corretora poderia casar com o job de outra")
    checar("a busca exclui só o que está morto",
           'neq("status", STATUS_MORTO)' in corpo_busca, corpo_busca[:160])
    checar("CONTROLE — a fatia lida é o corpo do método, não o arquivo inteiro",
           0 < len(corpo_busca) < len(fonte) and "def _arun" not in corpo_busca,
           f"{len(corpo_busca)} de {len(fonte)} caracteres")

    # O insert grava o que a migration criou.
    bloco_insert = fonte[i_insert:i_insert + 700]
    for coluna in ('"idempotency_key"', '"session_id"', '"agent_id"'):
        checar(f"o insert grava {coluna}", coluna in bloco_insert, bloco_insert[:200])

    checar("a corrida (23505) é tratada", "_e_chave_duplicada" in fonte and "23505" in fonte)
    i_23505 = fonte.find("if not self._e_chave_duplicada(e)")
    checar("a corrida é tratada dentro do except do insert", i_insert < i_23505,
           f"insert={i_insert} trata_23505={i_23505}")

    # CONTROLE do teste inteiro: se os marcadores não existissem, `find` devolveria
    # -1 e as comparações acima passariam por acidente em algumas ordens.
    checar("CONTROLE — os três marcadores existem de verdade",
           min(i_chave, i_busca, i_insert, i_23505) > 0,
           f"{i_chave} {i_busca} {i_insert} {i_23505}")


def teste_o_codigo_e_o_indice_concordam():
    print("\n[9] O predicado do índice e a noção de 'vivo' no código não divergem")
    caminho = os.path.join(str(RAIZ_REPO), "backend", "supabase", "migrations",
                           "20260804_02_spec065_o_pedido_nao_abre_duas_vezes.sql")
    checar("a migration existe", os.path.isfile(caminho), caminho)
    if not os.path.isfile(caminho):
        return
    sql = open(caminho, encoding="utf-8").read()

    for secao in ("APPLY:", "VERIFY:", "ROLLBACK:"):
        checar(f"a migration declara {secao}", secao in sql)
    checar("a migration é expand-first e não destrutiva",
           "EXPAND-FIRST: sim" in sql and "DESTRUTIVA:   nao" in sql)

    for coluna in ("idempotency_key", "session_id", "agent_id"):
        checar(f"a migration adiciona {coluna} de forma idempotente",
               f"ADD COLUMN IF NOT EXISTS {coluna}" in sql)

    checar("o índice é ÚNICO e idempotente",
           "CREATE UNIQUE INDEX IF NOT EXISTS idx_portal_jobs_pedido_vivo" in sql)

    # O predicado, palavra por palavra. Ele é a regra inteira do bloco.
    indice = sql.split("CREATE UNIQUE INDEX IF NOT EXISTS idx_portal_jobs_pedido_vivo", 1)[1]
    indice = indice.split(";", 1)[0]
    checar("chave nula não bloqueia nada", "idempotency_key IS NOT NULL" in indice, indice)
    checar("failed é a válvula de escape", "status <> 'failed'" in indice, indice)
    checar("o índice é composto com company_id",
           "(company_id, idempotency_key)" in indice, indice)

    # CONTROLE do predicado: a forma invertida bloquearia exatamente o que deve
    # liberar. Este guarda pega a troca de `<>` por `=`.
    checar("CONTROLE — o predicado NÃO é `status = 'failed'`",
           "status = 'failed'" not in indice, indice)

    # E o código tem de chamar de morto exatamente o mesmo status que o SQL libera.
    fonte = _ler("backend", "app", "agents", "tools", "portal_tool.py")
    morto = re.search(r'STATUS_MORTO\s*=\s*"([^"]+)"', fonte)
    checar("o código declara qual status está morto", morto is not None)
    if morto:
        checar("o status morto do código é o mesmo que o índice libera",
               f"status <> '{morto.group(1)}'" in indice,
               f"código={morto.group(1)}  índice={indice.strip()[:120]}")


def teste_o_banco_quando_a_migration_ja_estiver_aplicada():
    print("\n[10] O banco, depois que a migration for aplicada")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("      (sem credencial — caso pulado)")
        return
    try:
        import httpx
    except ImportError:
        print("      (sem httpx — caso pulado)")
        return
    try:
        r = httpx.get(f"{url.rstrip('/')}/rest/v1/portal_jobs",
                      params={"select": "id,idempotency_key,session_id", "limit": 1},
                      headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"      (banco inacessível: {type(exc).__name__} — caso pulado)")
        return

    if r.status_code != 200:
        # A migration ainda não foi aplicada. Isso NÃO é falha: o executor
        # escreve o arquivo, o Founder aplica. Fica registrado em voz alta para
        # não passar por verde silencioso.
        print("      MIGRATION AINDA NÃO APLICADA — as colunas não existem no banco.")
        print("      Este caso vira asserção real assim que ela for aplicada.")
        return

    checar("o banco já tem idempotency_key e session_id em portal_jobs", True)
    linhas = r.json() if r.content else []
    if linhas:
        checar("a leitura das colunas novas funciona",
               "idempotency_key" in linhas[0] and "session_id" in linhas[0], str(linhas[0])[:120])


def main() -> int:
    print("=" * 72)
    print("O PORTAL NUNCA ABRE DUAS VEZES O MESMO PEDIDO")
    print("=" * 72)
    for teste in (teste_a_chave_identifica_o_pedido,
                  teste_o_que_e_outro_pedido_continua_sendo_outro,
                  teste_o_isolamento_entre_corretoras,
                  teste_a_grafia_nao_inventa_pedido,
                  teste_a_chave_nasce_dos_params_de_verdade,
                  teste_a_chave_falha_aberta_quando_nao_ha_pedido,
                  teste_a_frase_nao_mente_para_o_segurado,
                  teste_a_tool_procura_antes_de_inserir,
                  teste_o_codigo_e_o_indice_concordam,
                  teste_o_banco_quando_a_migration_ja_estiver_aplicada):
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
    print("UM PEDIDO, UM ATENDIMENTO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
