"""O portão do prompt vale no BACKEND — e é o mesmo portão, não um segundo.

P-38. Fechamos quatro portas de TypeScript e deixamos duas de Python abertas.
-----------------------------------------------------------------------------
P-36 levou o portão aos quatro arquivos ``.ts`` que escrevem
``agents.agent_system_prompt``. A varredura que deveria provar que não sobrou
nenhuma era um DICIONÁRIO FIXO de quatro caminhos ``.ts`` — não varria o
repositório e não olhava ``.py``. Um quinto escritor era invisível por
construção, e havia dois:

    backend/app/services/agent_service.py   update_agent / create_agent
    backend/app/api/agent_config.py         companies.agent_system_prompt

📊 Provado por execução em 04/08/2026::

    AgentUpdate(agent_system_prompt='').model_dump(exclude_unset=True)
    → {'agent_system_prompt': ''}

Uma string vazia por cima de um prompt que funcionava. Sem validação de
tamanho, sem releitura pós-escrita, sem desativação fail-closed — e sem sequer
``.eq("company_id", ...)``, o que fazia o update ser escopado só por ``id``
num backend que roda com service role (CLAUDE.md §7).

E o caminho é alcançável pela UI de super-admin::

    app/admin/companies/[companyId]/agents/page.tsx
      → app/api/admin/proxy/agents/[[...path]]/route.ts   (repassa cego)
        → backend/app/api/agents.py   PUT /{agent_id}  ·  POST /

É a hipótese mais forte para a AutoFleet ter ficado com o agente CORE **ATIVO
e com prompt de ZERO caracteres** (📊 auditoria de 02/08/2026,
``docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md``, Parte C.6).

Por que não é um segundo portão (CLAUDE.md §5)
----------------------------------------------
Um portão em Python não pode ser um ``import`` de TypeScript. O que se espelha
é o CONTRATO — as medidas, os marcadores de bloco, os nomes dos motivos —, e
ele mora num arquivo só: ``lib/admin/portao-do-prompt.contract.json``.

O TypeScript o importa. O Python NÃO consegue: 📊 ``backend/Dockerfile`` é
construído com contexto ``backend/`` (``COPY . .``) e a imagem do backend não
enxerga ``lib/``. Ler o arquivo em runtime daria um módulo que funciona no
repositório e explode em produção. Então os valores são declarados nos dois
lados e o caso [4] deste arquivo prova que são os MESMOS — número por número,
nome por nome, cabeçalho por cabeçalho, nos QUATRO lugares onde eles aparecem.

O jeito de este teste ser honesto
---------------------------------
Ler código-fonte prova que alguém escreveu o nome certo, não que a regra
funciona. Então os casos [1] a [3] **carregam o módulo Python de verdade e
executam a regra**, inclusive contra a casca de guardrails — o caso que uma
checagem de "não vazio" deixa passar — e inclusive contra um cliente de banco
falso, para ver o UPDATE de desligamento sair.

E o caso [6] é a linha de CONTROLE (CLAUDE.md §9.2/§9.3): a mesma verificação,
rodada sobre o código como ele era ANTES do conserto (verbatim), e sobre um
contrato deliberadamente adulterado. Se ele ficar verde, esta suíte inteira não
está guardando nada.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

CONTRATO_JSON = ("lib", "admin", "portao-do-prompt.contract.json")
PORTAO_PY = ("backend", "app", "services", "portao_do_prompt.py")
SAUDE_TS = ("lib", "admin", "agent-health.ts")
CANONICO_TS = ("lib", "admin", "agent-blueprints-canonical.ts")
PORTAO_TS = ("lib", "admin", "provision-tenant.ts")
SERVICE_PY = ("backend", "app", "services", "agent_service.py")
CONFIG_PY = ("backend", "app", "api", "agent_config.py")
API_PY = ("backend", "app", "api", "agents.py")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_py(fonte: str) -> str:
    """Comentário não é prova. O que vale é o que executa."""
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


def _sem_comentario_ts(fonte: str) -> str:
    sem_linha = "\n".join(
        l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*"))
    )
    return re.sub(r"/\*.*?\*/", "", sem_linha, flags=re.S)


def _corpo_py(fonte: str, assinatura: str) -> str:
    """Recorta o corpo de um método até o próximo `def` de mesmo nível.

    Comparar posições no arquivo inteiro mentiria: o portão de uma função
    ficaria "antes" da escrita de outra e o caso passaria de graça.
    """
    if assinatura not in fonte:
        return ""
    depois = fonte.split(assinatura, 1)[1]
    return re.split(r"\n    def |\n@router\.|\ndef |\nclass ", depois)[0]


def portao_antes_da_escrita(corpo: str, marca_portao: str, marca_escrita: str) -> bool:
    """A pergunta inteira: o portão roda ANTES de a coluna ser escrita?"""
    if marca_portao not in corpo or marca_escrita not in corpo:
        return False
    return corpo.index(marca_portao) < corpo.index(marca_escrita)


# ---------------------------------------------------------------------------
# O módulo REAL, carregado sozinho — sem supabase, sem FastAPI, sem ambiente.
# ---------------------------------------------------------------------------

def _carregar_portao():
    caminho = os.path.join(RAIZ, *PORTAO_PY)
    spec = importlib.util.spec_from_file_location("portao_do_prompt_sob_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["portao_do_prompt_sob_teste"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


P = _carregar_portao()
CONTRATO = json.loads(_ler(*CONTRATO_JSON))

# Textos de trabalho. O composto é montado com os MESMOS cabeçalhos do emissor.
PERSONALIZADO = (
    "Voce e o AutoBrokers da Resulta Seguros — o braco direito interno da corretora. "
    "Ajude o corretor a fechar, renovar e cobrar, com respostas curtas e verificaveis."
)
CASCA_VAZIA = "\n".join([
    CONTRATO["linha_personalizacao"],
    "",
    "",
    CONTRATO["linha_guardrails"],
    "- Nunca invente numero de protocolo.",
    "- A marca AutoBrokers e fixa e nao pode ser renomeada.",
    CONTRATO["linha_precedencia"],
])
COMPOSTO_OK = "\n".join([
    CONTRATO["linha_personalizacao"],
    PERSONALIZADO,
    "",
    CONTRATO["linha_guardrails"],
    "- Nunca invente numero de protocolo.",
    CONTRATO["linha_precedencia"],
])


# ---------------------------------------------------------------------------
# Um banco de mentira, que registra o que recebeu
# ---------------------------------------------------------------------------

class _Resposta:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, diario, tabela, verbo, payload=None):
        self.diario = diario
        self.tabela = tabela
        self.verbo = verbo
        self.payload = payload
        self.filtros: dict = {}

    def select(self, cols):
        self.cols = cols
        return self

    def eq(self, k, v):
        self.filtros[k] = v
        return self

    def limit(self, _n):
        return self

    def execute(self):
        self.diario.append({
            "tabela": self.tabela, "verbo": self.verbo,
            "payload": self.payload, "filtros": dict(self.filtros),
        })
        if self.verbo == "select":
            return _Resposta(self.diario_leitura)
        return _Resposta([{"ok": True}])


class _Tabela:
    def __init__(self, diario, nome, leitura):
        self.diario, self.nome, self.leitura = diario, nome, leitura

    def select(self, cols):
        q = _Query(self.diario, self.nome, "select")
        q.diario_leitura = self.leitura
        return q.select(cols)

    def update(self, payload):
        return _Query(self.diario, self.nome, "update", payload)


class BancoDeMentira:
    """Só o suficiente para ver o portão agir: o que ele leu e o que ele escreveu."""

    def __init__(self, prompt_no_banco):
        self.diario: list = []
        self.leitura = [{"agent_system_prompt": prompt_no_banco}]

    def table(self, nome):
        return _Tabela(self.diario, nome, self.leitura)

    def updates(self):
        return [e for e in self.diario if e["verbo"] == "update"]


# ===========================================================================
# Casos
# ===========================================================================

def teste_a_regra_roda_de_verdade():
    print("\n[1] O portao Python EXECUTA — nao e um nome escrito num arquivo")

    # O caso medido: string vazia gravada por cima de um prompt que funcionava.
    checar(P.problemas_da_escrita_de_prompt("") == ["prompt_de_autoria_vazio"],
           "'' e RECUSADO, com nome proprio",
           str(P.problemas_da_escrita_de_prompt("")))
    checar(P.problemas_da_escrita_de_prompt("   \n  ") == ["prompt_de_autoria_vazio"],
           "e espaco em branco tambem — nao e 'nao vazio', e 'tem instrucao'")

    # AUSENCIA nao e escrita: um PATCH de llm_model nao pode ser recusado por
    # causa de um campo que ele nem tocou.
    checar(P.problemas_da_escrita_de_prompt(None) == [],
           "None (chave ausente) NAO e recusado",
           "senao trocar o modelo do agente passaria a exigir reenviar o prompt")

    curto = P.problemas_da_escrita_de_prompt("Voce e um assistente.")
    checar(len(curto) == 1 and curto[0].startswith("prompt_de_autoria_curto:"),
           "texto curto demais e recusado E o tamanho vai no motivo", str(curto))
    checar(P.problemas_da_escrita_de_prompt(PERSONALIZADO) == [],
           "e um prompt de verdade PASSA — os dois lados conseguem ser diferentes",
           str(P.problemas_da_escrita_de_prompt(PERSONALIZADO)))

    # O segundo jeito de ser mudo, o que passa em qualquer checagem de tamanho.
    checar(len(CASCA_VAZIA) > P.PERSONALIZACAO_MINIMA_CHARS,
           "a casca de guardrails e LONGA (por isso 'nao vazio' nao basta)",
           f"{len(CASCA_VAZIA)} chars")
    checar(P.problemas_da_escrita_de_prompt(CASCA_VAZIA) == ["prompt_so_guardrails"],
           "e mesmo assim ela e RECUSADA: moldura sem instrucao e mudez",
           str(P.problemas_da_escrita_de_prompt(CASCA_VAZIA)))

    # Os tres estados da voz, executados.
    checar(P.estado_da_voz("") == "vazio", "estado_da_voz('') == vazio")
    checar(P.estado_da_voz(CASCA_VAZIA) == "so_guardrails",
           "estado_da_voz(casca) == so_guardrails", P.estado_da_voz(CASCA_VAZIA))
    checar(P.estado_da_voz(COMPOSTO_OK) == "ok",
           "estado_da_voz(prompt real) == ok", P.estado_da_voz(COMPOSTO_OK))
    checar(P.estado_da_voz(PERSONALIZADO) == "ok",
           "e prompt escrito A MAO, sem a moldura, tambem e voz",
           "quem digitou a instrucao na unha instruiu de verdade")
    checar(P.personalizacao_do_prompt(COMPOSTO_OK) == PERSONALIZADO,
           "a personalizacao e extraida de dentro do composto",
           repr(P.personalizacao_do_prompt(COMPOSTO_OK))[:90])


def teste_a_releitura_desliga_de_verdade():
    print("\n[2] A releitura pos-escrita DESLIGA quem ficou mudo (UPDATE observado)")

    banco = BancoDeMentira("")
    r = P.conferir_prompt_gravado(banco, "co-1", "ag-1", "teste")
    checar(not r.ok, "prompt vazio no banco reprova a escrita", str(r))
    ups = banco.updates()
    checar(len(ups) == 1, "e sai EXATAMENTE um update de desligamento", str(ups))
    checar(ups and ups[0]["payload"] == {"is_active": False, "agent_enabled": False},
           "que desliga is_active E agent_enabled",
           "reportar nao basta: um agente ativo sem instrucao responde sem trava")
    checar(ups and ups[0]["filtros"].get("company_id") == "co-1",
           "e a escrita leva o filtro de tenant (CLAUDE.md §7)",
           str(ups and ups[0]["filtros"]))
    checar("agente_desligado" in (r.reason or ""),
           "e o motivo diz que desligou", str(r.reason))

    # A casca de guardrails tambem e mudez DEPOIS de gravada.
    banco2 = BancoDeMentira(CASCA_VAZIA)
    r2 = P.conferir_prompt_gravado(banco2, "co-1", "ag-1", "teste")
    checar(not r2.ok and len(banco2.updates()) == 1,
           "casca gravada tambem desliga o agente", str(r2))

    # E o contrario: prompt bom nao desliga ninguem.
    banco3 = BancoDeMentira(COMPOSTO_OK)
    r3 = P.conferir_prompt_gravado(banco3, "co-1", "ag-1", "teste")
    checar(r3.ok and r3.chars == len(COMPOSTO_OK), "prompt bom APROVA", str(r3))
    checar(banco3.updates() == [],
           "e nao escreve nada — a releitura nao pode ter efeito colateral")

    # A camada legada (`companies`) desliga por agent_enabled: `is_active` numa
    # empresa significa a corretora existir, e nao a voz do agente.
    banco4 = BancoDeMentira("")
    P.conferir_prompt_gravado(banco4, "co-1", "co-1", "teste", tabela="companies")
    ups4 = banco4.updates()
    checar(ups4 and ups4[0]["payload"] == {"agent_enabled": False},
           "companies desliga so agent_enabled", str(ups4 and ups4[0]["payload"]))
    checar(ups4 and "company_id" not in ups4[0]["filtros"],
           "e nao filtra companies por company_id — o id JA E o tenant",
           str(ups4 and ups4[0]["filtros"]))


def teste_agente_mudo_nasce_desligado():
    print("\n[3] Insert: a chave que SOME do JSON nao produz mais agente ativo")
    # 📊 lib/admin/agent-blueprints.ts:40 fazia `s(...) || undefined`, e em JSON
    # `undefined` faz a chave sumir. A linha 41 mandava `is_active: true`.
    sem_prompt = P.desligar_se_nascer_mudo({"name": "Auxiliar", "is_active": True})
    checar(sem_prompt["is_active"] is False and sem_prompt["agent_enabled"] is False,
           "payload SEM a chave nasce desligado", str(sem_prompt))

    vazio = P.desligar_se_nascer_mudo({"agent_system_prompt": "", "is_active": True})
    checar(vazio["is_active"] is False, "payload com prompt vazio nasce desligado")

    # O auxiliar de uma frase e o PRODUTO — o minimo aqui e 1, nao 120.
    esboco = P.desligar_se_nascer_mudo(
        {"agent_system_prompt": "Voce cuida de cobranca.", "is_active": True})
    checar(esboco["is_active"] is True,
           "e o esboco de uma frase continua nascendo LIGADO",
           "auxiliar sem descricao nasce assim de proposito; o que nao pode "
           "existir e a linha com prompt em branco E ativa")


def teste_o_contrato_e_um_so():
    print("\n[4] UM contrato, quatro lugares — e eles sao iguais")
    py = _ler(*PORTAO_PY)
    saude = _sem_comentario_ts(_ler(*SAUDE_TS))
    canonico = _ler(*CANONICO_TS)
    portao_ts = _sem_comentario_ts(_ler(*PORTAO_TS))

    # a) numeros: JSON x Python
    checar(P.PROMPT_MINIMO_CHARS == CONTRATO["prompt_minimo_chars"],
           f"prompt_minimo_chars igual nos dois runtimes ({P.PROMPT_MINIMO_CHARS})",
           f"py={P.PROMPT_MINIMO_CHARS} json={CONTRATO['prompt_minimo_chars']}")
    checar(P.PERSONALIZACAO_MINIMA_CHARS == CONTRATO["personalizacao_minima_chars"],
           f"personalizacao_minima_chars igual ({P.PERSONALIZACAO_MINIMA_CHARS})",
           f"py={P.PERSONALIZACAO_MINIMA_CHARS} json={CONTRATO['personalizacao_minima_chars']}")
    checar(P.PLACEHOLDER_PENDENTE == CONTRATO["placeholder_pendente"],
           "e a regex de placeholder pendente e a mesma string")

    # b) o TypeScript LE o contrato em vez de repetir os numeros
    checar("portao-do-prompt.contract.json" in portao_ts,
           "provision-tenant.ts IMPORTA o contrato")
    checar("CONTRATO.prompt_minimo_chars" in portao_ts
           and "CONTRATO.personalizacao_minima_chars" in portao_ts,
           "e tira as DUAS medidas de la, em vez de escrever o numero",
           "numero escrito em dois lugares diverge no dia em que um deles muda")
    checar(not re.search(r"PROMPT_MINIMO_CHARS\s*=\s*\d", portao_ts),
           "e nao sobrou nenhum literal numerico no portao TS",
           "era daqui que os 400 saiam antes do contrato existir")

    # c) motivos: JSON x Python, nome por nome
    checar(P.MOTIVOS == CONTRATO["motivos"],
           "os NOMES DOS MOTIVOS sao identicos nos dois lados",
           f"so em py: {set(P.MOTIVOS) - set(CONTRATO['motivos'])} · "
           f"so em json: {set(CONTRATO['motivos']) - set(P.MOTIVOS)}")
    for chave, valor in CONTRATO["motivos"].items():
        checar(chave == valor,
               f"motivo '{chave}' e a propria string (sem apelido para divergir)")

    # d) cabecalhos: JSON x Python x detector TS x EMISSOR TS
    for nome, esperado in (
        ("CABECALHO_PERSONALIZACAO", CONTRATO["cabecalho_personalizacao"]),
        ("CABECALHO_GUARDRAILS", CONTRATO["cabecalho_guardrails"]),
    ):
        checar(getattr(P, nome) == esperado, f"{nome}: Python == contrato")
        checar(f"const {nome} = '{esperado}'" in saude,
               f"{nome}: agent-health.ts == contrato",
               "se os dois lados divergirem, a casca volta a passar por voz")

    for chave in ("linha_personalizacao", "linha_guardrails", "linha_precedencia"):
        checar(f"'{CONTRATO[chave]}'" in canonico,
               f"o EMISSOR emite exatamente {chave}",
               "o detector procura por esta linha; reescreve-la aqui cega os dois")

    # E a ponte entre os dois: o cabeçalho curto (que o detector procura) tem de
    # ser o começo da linha inteira (que o emissor escreve).
    checar(CONTRATO["linha_personalizacao"].startswith(CONTRATO["cabecalho_personalizacao"]),
           "a linha emitida COMECA pelo cabecalho procurado (personalizacao)")
    checar(CONTRATO["linha_guardrails"].startswith(CONTRATO["cabecalho_guardrails"]),
           "a linha emitida COMECA pelo cabecalho procurado (guardrails)")

    # e) o Python NAO le o JSON em runtime — a imagem do backend nao tem `lib/`.
    # A prova e sobre o que EXECUTA: nenhum open/json.load/Path no modulo.
    codigo_py = _sem_comentario_py(py.split('"""', 2)[-1])
    for proibido in ("open(", "json.load", "Path(", "read_text("):
        checar(proibido not in codigo_py,
               f"o modulo Python nao usa {proibido} para achar o contrato",
               "📊 backend/Dockerfile roda `COPY . .` com contexto backend/: um "
               "read de lib/ funcionaria aqui e explodiria em producao")
    checar("import json" not in codigo_py,
           "e nem importa json — os valores sao declarados, e o teste e que compara")


def teste_o_backend_passa_pelo_portao():
    print("\n[5] Os dois escritores Python passam pelo portao — e releem depois")

    servico = _sem_comentario_py(_ler(*SERVICE_PY))
    corpo = _corpo_py(servico, "def update_agent(")
    escrita = '.update(update_data)'

    checar(bool(corpo), "update_agent existe")
    checar(portao_antes_da_escrita(corpo, "problemas_da_escrita_de_prompt(", escrita),
           "update_agent: o portao roda ANTES do update",
           "📊 AgentUpdate(agent_system_prompt='') vira {'agent_system_prompt': ''} "
           "e ia direto para a coluna")
    checar('if "agent_system_prompt" in update_data' in corpo,
           "e ele so age quando o prompt FOI enviado",
           "exclude_unset separa 'mandou vazio' de 'nao mandou'")
    checar("conferir_prompt_gravado(" in corpo, "update_agent: e o banco e relido depois")
    checar(corpo.index("conferir_prompt_gravado(") > corpo.index(escrita),
           "e a releitura vem DEPOIS da escrita",
           "antes dela, releria o estado velho e aprovaria o novo")
    checar('.eq("company_id", str(tenant))' in corpo,
           "e o update passou a levar o filtro de tenant (CLAUDE.md §7)",
           "o backend usa service role: RLS sem policy nao protege contra "
           "erro de filtro no codigo")

    criar = _corpo_py(servico, "def create_agent(")
    checar(portao_antes_da_escrita(criar, "desligar_se_nascer_mudo(", '.insert(data)'),
           "create_agent: agente mudo nasce DESLIGADO, antes do insert")

    # O tenant precisa CHEGAR aqui — a API ja o tinha na mao e nao passava.
    api = _sem_comentario_py(_ler(*API_PY))
    checar("company_id=tenant" in api,
           "e a rota PUT repassa o company_id que ja tinha buscado",
           "ele era lido so para invalidar cache; o update ignorava")

    # A camada LEGADA (companies) — lida pelo runtime em nodes.py:438.
    config = _sem_comentario_py(_ler(*CONFIG_PY))
    salvar = _corpo_py(config, "async def save_agent_config(")
    checar(portao_antes_da_escrita(salvar, "problemas_da_escrita_de_prompt(",
                                   '.table("companies")'),
           "save_agent_config: o portao roda antes do update em companies")
    checar('update_data["agent_system_prompt"] = config.agent_system_prompt' in salvar,
           "e a chave so entra no update quando o prompt FOI enviado",
           "o dicionario a incluia SEMPRE: um PUT que so trocasse o modelo "
           "gravava NULL na coluna e a empresa perdia a instrucao")
    checar('"agent_system_prompt": config.agent_system_prompt,' not in salvar,
           "a linha incondicional saiu do dicionario",
           "era ela que transformava omissao em apagamento")
    checar('tabela="companies"' in salvar,
           "e a releitura sabe que a tabela e outra")


def teste_o_guarda_tem_como_falhar():
    print("\n[6] CONTROLE — a mesma verificacao reprova o codigo de ANTES")

    # Verbatim de `git show 5c84444:backend/app/services/agent_service.py`.
    ANTES = '''
    def update_agent(self, agent_id: UUID, agent_data: AgentUpdate) -> AgentResponse:
        try:
            update_data = agent_data.model_dump(exclude_unset=True)

            if update_data.get("name") or update_data.get("slug"):
                name_ref = update_data.get("slug") or update_data.get("name")
                if name_ref:
                    update_data["slug"] = slugify(name_ref)

            result = (
                self.supabase.client.table("agents")
                .update(update_data)
                .eq("id", str(agent_id))
                .execute()
            )

            if not result.data:
                raise Exception("Failed to update agent")

            invalidate_agent_cache(str(agent_id))
            return self._map_to_response(result.data[0])
'''
    antes = _corpo_py(_sem_comentario_py(ANTES), "def update_agent(")
    escrita = ".update(update_data)"

    checar(escrita in antes,
           "o controle e mesmo o caminho que gravava a coluna",
           "se nem a escrita estivesse la, ele nao provaria nada")
    checar(not portao_antes_da_escrita(antes, "problemas_da_escrita_de_prompt(", escrita),
           "o codigo de ANTES REPROVA na verificacao do caso [5]",
           "se este caso ficar vermelho, a verificacao passa com ou sem o conserto")
    checar("conferir_prompt_gravado(" not in antes,
           "e o codigo de ANTES nao relia o banco")
    checar('.eq("company_id"' not in antes,
           "nem escopava o update por tenant — era so `.eq(\"id\")`")

    # E o contrario: a verificacao APROVA o codigo de hoje.
    hoje = _corpo_py(_sem_comentario_py(_ler(*SERVICE_PY)), "def update_agent(")
    checar(portao_antes_da_escrita(hoje, "problemas_da_escrita_de_prompt(", escrita),
           "e APROVA o de hoje — os dois lados conseguem ser diferentes")

    # O caso [4] tambem precisa poder ficar vermelho: um contrato adulterado
    # NAO pode passar. Sem isto, "os numeros sao iguais" seria uma afirmacao
    # que nunca foi testada contra a desigualdade.
    adulterado = dict(CONTRATO)
    adulterado["prompt_minimo_chars"] = CONTRATO["prompt_minimo_chars"] + 1
    checar(P.PROMPT_MINIMO_CHARS != adulterado["prompt_minimo_chars"],
           "um contrato com UM numero trocado reprova a comparacao do caso [4]",
           "se isto fosse verdade, a igualdade la seria decorativa")

    motivos_adulterados = dict(CONTRATO["motivos"])
    motivos_adulterados["prompt_vazio"] = "prompt_vazio_v2"
    checar(P.MOTIVOS != motivos_adulterados,
           "e um motivo renomeado tambem reprova")

    # E a regra em si: ela distingue: recusa o vazio e aprova o bom.
    checar(P.problemas_da_escrita_de_prompt("") != P.problemas_da_escrita_de_prompt(PERSONALIZADO),
           "o portao devolve respostas DIFERENTES para vazio e para prompt real",
           "um guarda que responde a mesma coisa aos dois nao guarda nada (§9.3)")


def main() -> int:
    print("=" * 74)
    print("O PORTAO DO PROMPT VALE NO BACKEND — P-38")
    print("=" * 74)

    for teste in (teste_a_regra_roda_de_verdade,
                  teste_a_releitura_desliga_de_verdade,
                  teste_agente_mudo_nasce_desligado,
                  teste_o_contrato_e_um_so,
                  teste_o_backend_passa_pelo_portao,
                  teste_o_guarda_tem_como_falhar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("UM PORTAO SO, NOS DOIS RUNTIMES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
