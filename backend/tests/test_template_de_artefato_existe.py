"""O template que o código usa tem de existir no banco. SPEC-057.

O defeito, medido em 30/07/2026
-------------------------------
    templates no catálogo Python .... 19
    templates no banco .............. 8
    faltando ........................ 11

`artifacts.template_key` é chave estrangeira para `report_templates`. Entre os
onze ausentes estavam `briefing.daily_operational` e `briefing.weekly_executive`
— exatamente os dois que o briefing diário usa, e os seis da família de pesquisa.

O efeito era silencioso e completo:

    artifacts ................. 0
    artifact_versions ......... 0
    briefing_publications ..... 17, todas em `pending`

Toda criação de artefato morria em violação de chave estrangeira. Os briefings
ficavam parados não porque a entrega falhava, mas porque **não havia o que
entregar**. Um zero explicava o outro, e nenhum dos dois reclamava.

Por que semear uma vez não basta
--------------------------------
A migration conserta o passado. O próximo template escrito em Python volta a
faltar no banco, e o defeito retorna igual — silencioso. Como a fonte da verdade
é o catálogo, é ele que precisa mandar no banco, e a hora de sincronizar é a
hora do uso.

Este arquivo trava as duas pontas: que o catálogo e a migration não divirjam, e
que o serviço garanta a linha antes de inserir.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.artifacts", ("app", "services", "artifacts"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m

_spec = importlib.util.spec_from_file_location(
    "app.services.artifacts.templates",
    os.path.join(RAIZ, "app", "services", "artifacts", "templates.py"))
T = importlib.util.module_from_spec(_spec)
# Registrar ANTES de executar: `@dataclass` procura o módulo em `sys.modules`
# pelo `__module__` da classe enquanto ela ainda está sendo criada, e recebe
# None se ele não estiver lá.
sys.modules["app.services.artifacts.templates"] = T
_spec.loader.exec_module(T)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _fonte(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def teste_o_catalogo_e_indexado_por_chave():
    print("\n[1] O catálogo tem índice por chave")
    checar(isinstance(getattr(T, "POR_CHAVE", None), dict),
           "`POR_CHAVE` existe e é dict")
    checar(len(T.POR_CHAVE) == len(T.CATALOGO),
           "toda entrada do catálogo está no índice",
           f"{len(T.CATALOGO)} no catálogo, {len(T.POR_CHAVE)} no índice")
    # Chave duplicada some no dict e o template vira invisível sem erro.
    chaves = [t.key for t in T.CATALOGO]
    checar(len(chaves) == len(set(chaves)), "não há chave duplicada")


#: 🔴 As migrations de SEED, em ordem. **Plural desde 03/09/2026.**
#:
#: Este teste lia UM arquivo, e a afirmação que ele guardava era "todo template
#: novo está na seed da 057". Essa verdade venceu quando a SPEC-094 acrescentou
#: o `executive.pulse360` ao catálogo: editar a seed da 057 para caber o novo é
#: proibido (CLAUDE.md §8 — migration aplicada não se altera; corrige-se com
#: migration nova), então o template novo mora numa migration nova, e o teste
#: ficaria vermelho por ARQUITETURA, não por defeito.
#:
#: ⚠️ Manter a leitura de um arquivo só ensinaria a ignorar este teste — que é
#: exatamente o que CLAUDE.md §9.3 proíbe: quando o fato muda, o teste muda com
#: ele, e a lição MIGRA em vez de morrer. A lição aqui é *"todo template do
#: catálogo tem linha semeada em ALGUMA migration versionada"*, e ela continua
#: sendo testada — agora sobre o conjunto das seeds. A próxima SPEC que criar
#: um template acrescenta o arquivo dela A ESTA LISTA.
SEEDS_DE_TEMPLATE = (
    "20260730_01_spec057_seed_templates.sql",
    "20260903_01_spec094_seed_template_pulse360.sql",
)


def teste_a_migration_cobre_o_que_o_banco_nao_tinha():
    print("\n[2] As migrations de seed cobrem o que o banco não tinha")
    fontes = {nome: _fonte("supabase", "migrations", nome)
              for nome in SEEDS_DE_TEMPLATE}
    sql = "\n".join(fontes.values())

    # Os oito que já estavam no banco antes de 30/07.
    ja_existiam = {
        "briefing.daily", "claims.performance", "commercial.pipeline",
        "executive.panorama", "financial.commissions",
        "portfolio.client_dossier", "renewals.radar", "research.market_brief"}
    faltavam = {t.key for t in T.CATALOGO} - ja_existiam

    for chave in sorted(faltavam):
        onde = [n for n, texto in fontes.items() if f"'{chave}'" in texto]
        checar(bool(onde), f"alguma migration semeia `{chave}`",
               f"nenhuma das {len(fontes)} seeds cita a chave")
        # 🔴 E semeia UMA vez só. Duas seeds com a mesma chave passariam pelo
        # `ON CONFLICT`, mas seriam duas descrições do mesmo template em dois
        # arquivos — e a segunda a rodar não teria efeito nenhum, o que é a
        # forma mais silenciosa de um texto errado sobreviver.
        checar(len(onde) <= 1, f"`{chave}` é semeada em UM arquivo só", onde)

    for nome, texto in fontes.items():
        checar("on conflict" in texto.lower(),
               f"`{nome}` é idempotente — não quebra se rodar duas vezes")
    checar(not any(f"('{k}'," in sql for k in ja_existiam),
           "nenhuma seed reescreve os que já existiam")

    # CONTROLE: o detector consegue reprovar. Uma chave que NÃO está em seed
    # nenhuma tem de ser vista como ausente — senão o laço acima passaria por
    # vacuidade e este teste voltaria a ser carimbo.
    checar(not any("'template.que.nao.existe'" in texto
                   for texto in fontes.values()),
           "CONTROLE: uma chave inventada NÃO é encontrada nas seeds")


def teste_o_servico_garante_antes_de_inserir():
    print("\n[3] Criar artefato garante o template primeiro")
    src = _fonte("app", "services", "artifacts", "service.py")
    corpo = src[src.find("def criar(self"):]
    corpo = corpo[:corpo.find("\n    def ", 10)]

    garante = corpo.find("_garantir_template")
    insere = corpo.find('table("artifacts").insert')
    checar(garante != -1, "`criar` chama `_garantir_template`")
    checar(garante != -1 and insere != -1 and garante < insere,
           "garante ANTES do insert",
           "depois do insert a chave estrangeira já teria estourado")

    guarda = src[src.find("def _garantir_template"):]
    guarda = guarda[:guarda.find("\n    def ", 10)]
    checar("POR_CHAVE" in guarda,
           "lê do índice do catálogo, não de uma lista paralela")
    checar("upsert" in guarda and "template_key" in guarda,
           "faz upsert por `template_key`")
    checar("_templates_conferidos" in guarda,
           "não repete o upsert a cada artefato do mesmo template")
    # Falhar aqui não pode impedir a criação: se o template já existir, o
    # insert seguinte funciona; se não existir, a FK dá o erro claro.
    checar("except Exception" in guarda,
           "falha do upsert não derruba a criação do artefato")


def teste_os_templates_que_o_briefing_usa():
    print("\n[4] Os templates que o briefing realmente pede")
    src = _fonte("app", "services", "intelligence", "workflows.py")
    usados = [k for k in ("briefing.daily_operational", "briefing.weekly_executive")
              if k in src]
    checar(len(usados) == 2, "o briefing usa os dois templates esperados",
           f"achei {usados}")
    for chave in usados:
        checar(chave in T.POR_CHAVE, f"`{chave}` existe no catálogo",
               "sem ele no catálogo, `_garantir_template` não tem o que semear")


if __name__ == "__main__":
    print("=" * 66)
    print("O TEMPLATE QUE O CÓDIGO USA TEM DE EXISTIR NO BANCO")
    print("=" * 66)
    teste_o_catalogo_e_indexado_por_chave()
    teste_a_migration_cobre_o_que_o_banco_nao_tinha()
    teste_o_servico_garante_antes_de_inserir()
    teste_os_templates_que_o_briefing_usa()
    print("\n" + "=" * 66)
    if FALHAS:
        print(f"FALHOU ({len(FALHAS)})")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TUDO VERDE")
