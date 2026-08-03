"""A página de Corredores mostra o que o motor faz — e diz como cada um termina.

Havia DUAS coisas chamadas corredor, e a tela lia a errada:

    corridor_templates       TABELA no banco    2 linhas      ← a TELA lia isto
    corridor_playbooks.py    CÓDIGO            13 corredores  ← isto EXECUTA

📊 Banco de produção, 03/08/2026 (`select * from corridor_templates`): duas
linhas, "Allianz Residencial — Assistência Residencial" e "Allianz Residencial
— Eletricista". Os dez corredores de auto que rodam há meses e os dois
residenciais novos nunca apareceram na página. O founder fez deploy e continuou
vendo os mesmos dois nomes — porque o defeito nunca esteve no deploy.

O GLOSSARIO já dizia onde o corredor mora. A tela é que lia outro lugar.

C.1 · Quem executa é quem lista
-------------------------------
O catálogo passa a vir de `corridor_playbooks.py`, por
`GET /api/corridors/catalog`. Não há segunda lista em TypeScript, e é o ponto:
duas listas divergem, e foi divergindo que a tela encolheu o produto.

C.2 · `corridor_templates` deixa de ser o catálogo
--------------------------------------------------
Ela sobra como ÂNCORA DE ID — `tenant_corridors.corridor_template_id` é uuid
NOT NULL com FK, e sem migration a ativação precisa de uma linha para apontar.
Âncora não é catálogo: nome, ramo, subserviços e desfecho vêm do código. Por
isso nenhuma coluna de catálogo (display_name, macro_service, allowed_channels,
readiness, service_type, subcorridor_key) pode voltar a ser LIDA de lá.

C.3 · Um card por (seguradora × ramo)
-------------------------------------
Decisão do founder, literal:

    "o corretor não quer saber se tem subcorredores, subserviços... vai
     confundir ele. Allianz Residencial e aí já vai tudo no pacote. Ele só
     precisa saber que Allianz Residencial está sendo atendida."

São 13 cards, não 40. Os subserviços aparecem DENTRO do card, como texto —
nunca como coisa ligável, porque quem se liga e se desliga é o corredor.

C.4 · O card diz a verdade sobre o que faz
------------------------------------------
Nem todo corredor abre chamado. 📊 O vidro da Porto termina num FORMULÁRIO e o
da Zurich numa ORIENTAÇÃO (`outcome = encaminha` no playbook). Prometer
abertura onde só há encaminhamento é a mentira que a SPEC-063 acabou de tirar
da tela de Seguradoras; um card que não distingue os dois a traz de volta.

C.5 · E continua honesta sobre o que a ativação NÃO faz
-------------------------------------------------------
Ativar registra que a corretora usa o corredor. Quem aciona é o roteiro de
atendimento, e ele é o mesmo para todas. A frase tem de continuar escrita.
"""

from __future__ import annotations

import importlib.util
import io
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
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


def _sem_comentario_ts(fonte: str) -> str:
    """O TypeScript sem comentário nenhum.

    Comentário explica o defeito e cita `corridor_templates` de propósito. Se o
    teste lesse comentário, ele passaria por causa da explicação e falharia por
    causa dela também — nos dois casos medindo a prosa, não o código."""
    sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.DOTALL)
    return "\n".join(l for l in sem_bloco.split("\n") if not l.lstrip().startswith("//"))


# ---------------------------------------------------------------------------
# O catálogo do CÓDIGO, carregado como o backend o carrega
# ---------------------------------------------------------------------------
for _nome in ("app", "app.services", "app.api"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []

if "fastapi" not in sys.modules:
    try:  # o backend real tem fastapi; este teste não precisa dele para nada
        import fastapi  # noqa: F401
    except Exception:  # noqa: BLE001
        _fake = types.ModuleType("fastapi")
        _fake.APIRouter = lambda **_kw: type(
            "R", (), {"get": lambda self, *_a, **_k: (lambda fn: fn)}
        )()
        _fake.Header = lambda **_kw: None
        _fake.HTTPException = type("HTTPException", (Exception,), {})
        sys.modules["fastapi"] = _fake


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(BACKEND, rel))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
_carregar("app.services.insurer_registry", "app/services/insurer_registry.py")
API = _carregar("app.api.corridors", "app/api/corridors.py")

CATALOGO = API.build_corridor_catalog()

TS_CATALOGO = ("lib", "admin", "tenant-corridor-catalog.ts")
TS_STORE = ("lib", "admin", "tenant-corridor-store.ts")
TS_CLIENTE = ("app", "dashboard", "personalizacao", "corredores", "CorridorGalleryClient.tsx")
TS_PAGINA = ("app", "dashboard", "personalizacao", "corredores", "page.tsx")
TS_ROTA = ("app", "api", "dashboard", "corridors", "route.ts")
TS_ROTA_ACAO = ("app", "api", "dashboard", "corridors", "[templateId]", "route.ts")


def teste_o_catalogo_vem_de_quem_executa():
    print("\n[C1] A tela lê o CÓDIGO, não a tabela")
    api = _ler("backend", "app", "api", "corridors.py")
    checar("from app.services.corridor_playbooks import" in api,
           "a rota importa o módulo que EXECUTA os corredores")
    checar("list_playbooks()" in api and "get_playbook(" in api,
           "a lista sai de list_playbooks/get_playbook",
           "qualquer lista escrita à mão aqui já é a segunda fonte")

    main = _ler("backend", "app", "main.py")
    checar("from app.api.corridors import router as corridors_router" in main
           and "app.include_router(corridors_router" in main,
           "a rota está registrada no main",
           "sem registro a rota não existe em produção e a tela fica vazia")

    store = _sem_comentario_ts(_ler(*TS_STORE))
    checar("/api/corridors/catalog" in store,
           "o store do dashboard chama o catálogo do backend")
    checar("fetchCorridorCatalog" in store,
           "e há UMA função que busca o catálogo")

    checar(len(CATALOGO) == len(PB.list_playbooks()),
           f"o catálogo entrega os {len(PB.list_playbooks())} corredores do código",
           f"entregou {len(CATALOGO)}")
    checar(len(CATALOGO) >= 13,
           "são pelo menos os 13 de 03/08/2026 (10 auto + 3 residenciais)",
           f"{len(CATALOGO)} corredores")


def teste_a_tabela_nao_e_mais_o_catalogo():
    print("\n[C2] `corridor_templates` virou âncora de id, não catálogo")
    catalogo = _sem_comentario_ts(_ler(*TS_CATALOGO))
    checar("corridor_templates" not in catalogo,
           "a montagem pura não conhece mais a tabela")
    checar("CorridorTemplateRow" not in catalogo,
           "o tipo que representava a linha do catálogo sumiu",
           "era ele que fazia a tabela ser o catálogo")

    store = _sem_comentario_ts(_ler(*TS_STORE))
    checar("TEMPLATE_SELECT" not in store,
           "a constante que lia o catálogo inteiro da tabela sumiu")

    # As colunas de CATÁLOGO não podem voltar a ser LIDAS. O insert da âncora
    # escreve display_name (a linha precisa de um nome); ler é que é o defeito.
    lidos = re.findall(r"\.select\(\s*'([^']*)'", store)
    checar(len(lidos) >= 2, "o store ainda lê algo do banco (âncora + ativações)")
    for proibida in ("display_name", "macro_service", "allowed_channels",
                     "readiness", "service_type", "subcorridor_key"):
        culpados = [c for c in lidos if proibida in c]
        checar(not culpados,
               f"nenhum select traz `{proibida}`",
               f"select('{culpados[0]}') — coluna de catálogo lida da tabela" if culpados else "")

    checar("tenant_corridors" in store,
           "ativar/pausar continua gravando em tenant_corridors",
           "é o registro do que a corretora quer usar")


def teste_nao_ha_segunda_lista_em_typescript():
    print("\n[C3] Nenhuma lista de corredores foi copiada para o TypeScript")
    chaves_seguradora = sorted({str(c["insurer_key"]) for c in CATALOGO})
    chaves_subservico = sorted({
        str(s["key"]) for c in CATALOGO for s in c["subservices"]
    })
    checar(len(chaves_seguradora) >= 10 and len(chaves_subservico) >= 8,
           f"o código declara {len(chaves_seguradora)} seguradoras e "
           f"{len(chaves_subservico)} subserviços")

    for arquivo in (TS_CATALOGO, TS_STORE, TS_CLIENTE, TS_PAGINA, TS_ROTA, TS_ROTA_ACAO):
        codigo = _sem_comentario_ts(_ler(*arquivo)).lower()
        nome = arquivo[-1]
        achadas = [k for k in chaves_seguradora if k in codigo]
        subs = [k for k in chaves_subservico if k in codigo]
        # A ponte de identificador legado (uma corretora com ativação antiga) é
        # a ÚNICA seguradora que pode aparecer, e só no módulo puro.
        limite = 1 if arquivo is TS_CATALOGO else 0
        checar(len(achadas) <= limite,
               f"{nome} não traz lista de seguradoras",
               f"encontrou {achadas}")
        checar(not subs,
               f"{nome} não traz lista de subserviços",
               f"encontrou {subs}")


def teste_um_card_por_seguradora_e_ramo():
    print("\n[C4] Um card por (seguradora × ramo) — não um por subserviço")
    pares = [(c["insurer_key"], c["line_kind"]) for c in CATALOGO]
    checar(len(pares) == len(set(pares)),
           "cada (seguradora, ramo) aparece uma vez só",
           f"{len(pares)} corredores, {len(set(pares))} pares distintos")

    subservicos = {str(s["key"]) for c in CATALOGO for s in c["subservices"]}
    vazados = [c["corridor_id"] for c in CATALOGO
               if any(sub in str(c["corridor_id"]) for sub in subservicos)]
    checar(not vazados,
           "nenhum card é de subserviço",
           f"{vazados} — era isto que fazia 'Allianz Residencial — Eletricista' "
           f"virar um segundo card")

    com_subservico = [c for c in CATALOGO if c["subservices"]]
    checar(len(com_subservico) == len(CATALOGO),
           "todo card leva os subserviços dentro dele (o pacote)")

    cliente = _sem_comentario_ts(_ler(*TS_CLIENTE))
    checar("it.subservices.map" in cliente and "join(' · ')" in cliente,
           "a tela imprime os subserviços como uma linha de TEXTO")


def teste_o_subservico_nao_e_ligavel():
    print("\n[C5] Subserviço é texto — não liga nem desliga nada")
    cliente = _sem_comentario_ts(_ler(*TS_CLIENTE))

    linhas_com_click = [l.strip() for l in cliente.split("\n") if "onClick" in l]
    checar(bool(linhas_com_click), "a tela tem botões (ativar/pausar/retomar)")
    for linha in linhas_com_click:
        checar("act(it.corridor_id" in linha,
               "todo clique age sobre o CORREDOR",
               f"clique fora do corredor: {linha[:90]}")

    # O trecho que renderiza os subserviços não pode conter botão nenhum.
    ini = cliente.find("it.subservices.map")
    checar(ini > 0, "o trecho dos subserviços foi encontrado")
    trecho = cliente[ini:ini + 240]
    checar("button" not in trecho and "onClick" not in trecho,
           "o trecho dos subserviços não tem botão nem clique",
           trecho[:90])

    checar("checkbox" not in cliente.lower() and "toggle" not in cliente.lower(),
           "não há caixa de marcar nem chave por subserviço")


def teste_o_card_distingue_abre_de_encaminha():
    print("\n[C6] O card distingue ABRIR de ENCAMINHAR")
    encaminham = [c for c in CATALOGO if c["outcome_summary"] in ("encaminha", "misto")]
    checar(len(encaminham) >= 2,
           "📊 há corredores que NÃO abrem chamado (Porto e Zurich, vidros)",
           f"{[c['corridor_id'] for c in encaminham]}")
    tipos = {str(s.get("referral_kind")) for c in CATALOGO for s in c["subservices"]
             if s["outcome"] == PB.OUTCOME_ENCAMINHA}
    checar("formulario" in tipos and "orientacao" in tipos,
           "e o tipo do encaminhamento vem declarado (formulário / orientação)",
           f"{sorted(tipos)}")

    api = _ler("backend", "app", "api", "corridors.py")
    checar('"outcome"' in api and "OUTCOME_ABRE" in api,
           "o desfecho sai do playbook, não de um padrão escrito na rota")

    cliente = _sem_comentario_ts(_ler(*TS_CLIENTE))
    checar("'encaminha'" in cliente,
           "a tela conhece o desfecho `encaminha`")
    checar("s.outcome !== 'encaminha'" in cliente and "s.outcome === 'encaminha'" in cliente,
           "e separa quem abre de quem encaminha")
    checar("referral_kind" in cliente and "formulário" in cliente and "orientação" in cliente,
           "o card nomeia o que a seguradora entrega no lugar do chamado")
    checar("não abre chamado" in cliente,
           "e diz, em português, que ali não há abertura de chamado",
           "prometer abertura onde só há encaminhamento é a mentira que saiu "
           "da tela de Seguradoras")


def teste_a_tela_continua_honesta_sobre_a_ativacao():
    print("\n[C7] A tela não promete capacidade que a ativação não dá")
    cliente = _sem_comentario_ts(_ler(*TS_CLIENTE))
    checar("apenas o disponibiliza para a corretora" in cliente,
           "a frase que separa 'ativar' de 'passar a funcionar' continua lá")
    checar("Quem aciona a seguradora é o roteiro de atendimento" in cliente,
           "e diz quem aciona de fato")
    checar("nenhuma ação externa, envio ou portal é executado" in cliente,
           "e que esta tela não executa nada")

    checar("items.filter(" not in cliente,
           "a tela não esconde corredor nenhum",
           "corretora sem o corredor instalado precisa VER o card para "
           "descobrir o que pode ligar")
    checar("'available'" in cliente and "Disponível" in cliente,
           "corredor não instalado aparece como Disponível")

    checar("catalogo_indisponivel" in cliente,
           "catálogo ilegível vira aviso, não lista menor",
           "mostrar menos corredores do que a corretora tem é o defeito "
           "que estamos consertando")


def main() -> int:
    print("=" * 68)
    print("A PAGINA DE CORREDORES DIZ A VERDADE")
    print("=" * 68)
    for t in (teste_o_catalogo_vem_de_quem_executa,
              teste_a_tabela_nao_e_mais_o_catalogo,
              teste_nao_ha_segunda_lista_em_typescript,
              teste_um_card_por_seguradora_e_ramo,
              teste_o_subservico_nao_e_ligavel,
              teste_o_card_distingue_abre_de_encaminha,
              teste_a_tela_continua_honesta_sobre_a_ativacao):
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
    print("A TELA MOSTRA O QUE O MOTOR FAZ, E DIZ COMO CADA CORREDOR TERMINA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
