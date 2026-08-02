"""A corretora ajusta o Auxiliar dela, e o chat manda ele trabalhar.

Os dois defeitos, medidos em 02/08/2026
--------------------------------------
**Bloco F — não havia como configurar depois de instalar.**

    tenant_auxiliary_revisions ............ ZERO referências em código
    PATCH para tenant_auxiliaries.config .. NÃO EXISTE

As instalações gravavam `config` no momento da instalação **e nunca mais**. E o
lado da LEITURA estava pronto e esperando: `auxiliary_context.py::_read_contract`
prefere `tenant config.contract` sobre `template default_config.contract` — uma
sobreposição por corretora que nada no sistema conseguia escrever.

**Bloco G — o chat não executava Auxiliar.**

A decisão **D9** do plano dizia: *"o corretor pede no chat e recebe ali mesmo,
em vez de esperar a rotina"*. A SPEC-064 Bloco G cobria criar e editar.
**Executar caiu entre as SPECs.**

O que este teste protege
------------------------
1. que a escrita de configuração exista, com histórico de quem mudou o quê
2. que **a corretora A não afete a corretora B** (CLAUDE.md §7)
3. que a corretora não sobrescreva o que é do template global
4. que o chat execute pelo MESMO motor da Rotina — nunca um segundo executor
5. que ele não ligue Auxiliar desligado nem invente Auxiliar que não existe
6. e que a regra de quando OFERECER automação esteja escrita e seja achável
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO = os.path.dirname(RAIZ)
FALHAS: list[str] = []


def _pacote(nome: str, *partes: str) -> None:
    if nome in sys.modules:
        return
    m = types.ModuleType(nome)
    m.__path__ = [os.path.join(RAIZ, *partes)]
    m.__package__ = nome
    sys.modules[nome] = m


for _n, _p in (("app", ("app",)),
               ("app.agents", ("app", "agents")),
               ("app.agents.tools", ("app", "agents", "tools"))):
    _pacote(_n, *_p)


def carregar(nome: str):
    if nome in sys.modules and hasattr(sys.modules[nome], "__file__"):
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(REPO, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(fonte: str) -> str:
    sem = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*")))
    return re.sub(r"/\*.*?\*/", "", sem, flags=re.S)


# ---------------------------------------------------------------------------
# [1..3] Bloco F — a escrita de configuração
# ---------------------------------------------------------------------------

def teste_a_escrita_existe_com_historico():
    print("\n[1] A configuração da corretora pode ser escrita, e deixa rastro")
    store = _sem_comentario(_ler("lib", "auxiliaries", "config-store.ts"))

    checar("tenant_auxiliary_revisions" in store,
           "a tabela de revisões passou a ser usada",
           "ela existia com ZERO referências em código")
    checar("changed_fields" in store,
           "a revisão registra QUAIS campos mudaram",
           "revisão que só diz 'mudou' não responde 'quem mexeu no meu horário?'")
    checar("approved_by" in store and "approved_at" in store,
           "registra quem mudou e quando")

    # A revisão vem antes da escrita: revisão órfã é um registro a mais;
    # mudança sem história é uma pergunta sem resposta.
    pos_rev = store.find("tenant_auxiliary_revisions")
    pos_upd = store.find("from('tenant_auxiliaries')\n    .update")
    if pos_upd == -1:
        pos_upd = store.find(".update({\n      config: depois")
    checar(pos_rev != -1 and pos_upd != -1 and pos_rev < pos_upd,
           "a revisão é gravada ANTES da configuração",
           "se a ordem inverter, uma falha deixa mudança sem história")

    rota = _sem_comentario(
        _ler("app", "api", "dashboard", "auxiliaries", "[slug]", "config", "route.ts"))
    checar("export async function PATCH" in rota, "existe rota de escrita")
    checar("requireCompanyMember" in rota and "write: true" in rota,
           "a escrita exige papel administrativo da própria corretora")
    checar("assertSameOrigin" in rota, "a mutação exige same-origin")


def teste_a_corretora_nao_reescreve_o_global():
    print("\n[2] A corretora sobrepõe, nunca reescreve o template global")
    store = _sem_comentario(_ler("lib", "auxiliaries", "config-store.ts"))

    checar("CAMPOS_DA_CORRETORA" in store,
           "existe um escopo fechado do que a corretora pode ajustar")
    checar("campos_fora_do_escopo_da_corretora" in store,
           "campo fora do escopo é RECUSADO, não ignorado em silêncio")

    # `runtime` define o que o Auxiliar É. Deixar a corretora reescrevê-lo
    # transformaria "personalizar" em "trocar o motor por baixo".
    bloco = store.split("CAMPOS_DA_CORRETORA", 1)[1].split("]", 1)[0]
    for proibido in ("runtime", "system_prompt", "visibility"):
        checar(f"'{proibido}'" not in bloco,
               f"'{proibido}' não é ajustável pela corretora",
               "isso mudaria o que o Auxiliar é, não como ele se comporta")

    # E nenhuma escrita da corretora pode tocar auxiliary_templates.
    checar("auxiliary_templates" not in store,
           "a escrita da corretora nunca toca o catálogo global",
           "mudar a corretora NUNCA toca no global")


def teste_isolamento_entre_duas_corretoras():
    print("\n[3] A corretora A não alcança a instalação da corretora B")
    store = _sem_comentario(_ler("lib", "auxiliaries", "config-store.ts"))

    # CLAUDE.md §7 — o backend usa service role: RLS sem policy não protege
    # contra erro de filtro no código. O filtro TEM de estar aqui.
    leituras = store.count(".eq('company_id', companyId)")
    checar(leituras >= 3,
           "todo acesso filtra por company_id",
           f"{leituras} filtros encontrados — leitura, escrita e histórico")

    # O update final também: sem ele, conhecer o id da instalação de outra
    # corretora bastaria para reconfigurá-la.
    trecho_update = store.split("from('tenant_auxiliaries')", 2)[-1]
    checar(".eq('company_id', companyId)" in trecho_update,
           "o UPDATE também filtra por company_id",
           "conhecer o id de outra corretora não pode bastar")

    rota = _sem_comentario(
        _ler("app", "api", "dashboard", "auxiliaries", "[slug]", "config", "route.ts"))
    checar("auth.ctx.companyId" in rota and "body?.companyId" not in rota,
           "o company_id vem da SESSÃO, nunca do corpo da requisição")


# ---------------------------------------------------------------------------
# [4..5] Bloco G — o chat executa
# ---------------------------------------------------------------------------

class _R:
    def __init__(self, data=None):
        self.data = data


class _T:
    def __init__(self, banco, nome):
        self.banco, self.nome, self.filtros = banco, nome, {}

    def select(self, *a, **k):
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return _R(self.banco.responder(self.nome, self.filtros))


class BancoFalso:
    def __init__(self, instalado=None, template=None):
        self.instalado, self.template = instalado, template
        self.consultas: list[tuple[str, dict]] = []

    def table(self, nome):
        return _T(self, nome)

    def responder(self, tabela, filtros):
        self.consultas.append((tabela, dict(filtros)))
        if tabela == "tenant_auxiliaries":
            return self.instalado
        if tabela == "auxiliary_templates":
            return self.template
        return None


def teste_o_chat_executa_pelo_mesmo_motor():
    print("\n[4] O chat executa pelo MESMO workflow da Rotina")
    fonte = _ler("backend", "app", "agents", "tools", "auxiliary_run_tool.py")

    checar("bridge.auxiliary.execute" in fonte,
           "usa o workflow que a Rotina já usa",
           "um segundo executor seria motor paralelo (CLAUDE.md §5)")
    checar("WorkRunService" in fonte,
           "enfileira pelo serviço de Work Runs — não executa direto")
    checar('source_type="chat"' in fonte,
           "a origem fica registrada",
           "sem isso, 'rodou porque pedi' e 'rodou sozinho' viram a mesma coisa")
    checar("idempotency_key" in fonte,
           "pedido repetido no mesmo minuto não vira dois trabalhos")

    grafo = _ler("backend", "app", "agents", "graph.py")
    checar("AuxiliaryRunTool" in grafo, "a ferramenta está anexada ao grafo")
    # A regra que o próprio arquivo já documentava e que eu quase violei.
    trecho = grafo.split("AuxiliaryRunTool", 1)[1][:400]
    checar("user_id=" not in trecho,
           "o user_id NÃO é amarrado na montagem do grafo",
           "o grafo é cacheado por (empresa, agente): amarrar usuário faria o "
           "trabalho de uma pessoa nascer no nome de outra")


def teste_o_chat_nao_liga_o_que_esta_desligado():
    print("\n[5] O chat não liga Auxiliar desligado nem inventa o que não existe")
    mod = carregar("app.agents.tools.auxiliary_run_tool")

    # desligado → explica e não executa
    banco = BancoFalso(instalado={"id": "a1", "slug": "cobranca-feita",
                                  "name": "Cobrança Feita", "status": "inactive"})
    tool = mod.AuxiliaryRunTool(supabase_client=banco, company_id="empresa-A")
    r = tool._run("cobranca-feita")
    checar("desligado" in r.lower(), "diz que está desligado", f"resposta={r[:70]!r}")
    checar("Auxiliares" in r, "diz ONDE ligar")
    checar("você" in r.lower(),
           "deixa claro que quem decide é o corretor",
           "ligar sozinho seria criar trabalho que ninguém pediu")

    # em breve → explica o que falta
    banco2 = BancoFalso(instalado=None,
                        template={"name": "Caça-Comissão", "catalog_state": "coming_soon",
                                  "missing_for_launch": "Precisa da API da InfoCap."})
    r2 = mod.AuxiliaryRunTool(supabase_client=banco2, company_id="empresa-A")._run("caca-comissao")
    checar("não está pronto" in r2.lower() or "nao esta pronto" in r2.lower(),
           "diz que ainda não existe")
    checar("InfoCap" in r2, "repassa o que falta para existir")

    # inexistente → não inventa
    banco3 = BancoFalso(instalado=None, template=None)
    r3 = mod.AuxiliaryRunTool(supabase_client=banco3, company_id="empresa-A")._run("auxiliar-fantasma")
    checar("não encontrei" in r3.lower() or "nao encontrei" in r3.lower(),
           "não inventa Auxiliar que não existe")

    # e toda consulta filtrou pela corretora
    todas = [f for _, f in banco.consultas + banco2.consultas + banco3.consultas]
    com_empresa = [f for f in todas if f.get("company_id") == "empresa-A"]
    checar(len(com_empresa) >= 1,
           "a leitura da instalação filtra por corretora",
           f"consultas={todas}")


def teste_a_regra_de_oferecer_esta_escrita():
    print("\n[6] A regra de quando oferecer automação está escrita e é achável")
    caminho = os.path.join(REPO, "docs", "canon", "QUANDO-OFERECER-AUTOMACAO.md")
    checar(os.path.isfile(caminho), "docs/canon/QUANDO-OFERECER-AUTOMACAO.md existe")
    if not os.path.isfile(caminho):
        return

    doc = _ler("docs", "canon", "QUANDO-OFERECER-AUTOMACAO.md")

    checar("AJUSTE" in doc and "OFERTA" in doc,
           "separa ajuste de oferta",
           "a SPEC original confundia os dois numa pergunta só")
    checar("hierarquia" in doc.lower() and "catálogo" in doc.lower(),
           "olha o catálogo antes de propor construir",
           "oferecer criar o que já existe acumula auxiliares duplicados")

    # As travas anti-chatice — a parte que o Founder pediu explicitamente.
    for trava, porque in (
        ("PRIMEIRA vez", "a primeira vez é para fazer o trabalho"),
        ("já disse NÃO", "o não é gravado e vale para sempre"),
        ("UMA por conversa", "teto por conversa"),
    ):
        checar(trava.lower() in doc.lower(), f"trava: {trava.lower()} — {porque}")

    checar("É sempre assim?" in doc,
           "registra por que a pergunta antiga era ruim",
           "sem o motivo, alguém a reescreve igual")
    checar("CLAUDE.md" in _ler("CLAUDE.md") and "QUANDO-OFERECER-AUTOMACAO" in _ler("CLAUDE.md"),
           "CLAUDE.md aponta para a regra")


def main() -> int:
    print("=" * 68)
    print("A CORRETORA CONFIGURA O QUE É DELA, E O CHAT MANDA TRABALHAR")
    print("=" * 68)
    for teste in (teste_a_escrita_existe_com_historico,
                  teste_a_corretora_nao_reescreve_o_global,
                  teste_isolamento_entre_duas_corretoras,
                  teste_o_chat_executa_pelo_mesmo_motor,
                  teste_o_chat_nao_liga_o_que_esta_desligado,
                  teste_a_regra_de_oferecer_esta_escrita):
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
    print("O QUE É DA CORRETORA A CORRETORA MUDA, E SÓ PARA ELA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
