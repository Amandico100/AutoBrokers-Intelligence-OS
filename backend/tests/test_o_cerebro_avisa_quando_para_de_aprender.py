"""O cérebro avisa quando para de aprender.

A HISTÓRIA
----------
📊 Em 05/08/2026 o AutoBrokers tinha três peças paradas ao mesmo tempo:

    23 documentos normativos presos há oito dias, invisíveis
     0 mapas de URA promovidos a referência — desde sempre
     0 fontes externas jamais lidas

E **todas as telas pintavam verde**, porque o critério de saúde era *"o laço
rodou"* e não *"o laço produziu"*. Um vigia que só sabe dizer que acordou não
vigia nada.

POR QUE ISTO NÃO É UM AGENTE NOVO
---------------------------------
Duas razões, e as duas são medidas:

1. **CLAUDE.md §5.** A Caixa de Entrada já é o lugar onde o que precisa de
   atenção humana aparece. Um vigia próprio seria motor paralelo.
2. 📊 O destino óbvio, `intelligence_signals`, tem `company_id NOT NULL`. Um
   aviso de plataforma **não tem corretora** — teria de escolher uma, e essa
   corretora receberia manutenção da AutoBrokers na caixa dela.
   `ItemDaCaixa.company_id` é opcional. É por isso que o lugar é este.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
Todo cenário tem o par: o estado ruim **e** o estado bom. Um vigia que acusa
sempre é tão inútil quanto um que nunca acusa — e só o par prova que ele
distingue os dois.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
ALVO = os.path.abspath(os.path.join(
    AQUI, "..", "app", "services", "control_plane", "inbox.py"))

FALHAS: list = []


def checar(condicao: bool, descricao: str, porque: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  X     {descricao}")
        if porque:
            print(f"        {porque}")
        FALHAS.append(descricao)


def _carregar():
    for _p in ("app", "app.services", "app.services.control_plane"):
        sys.modules.setdefault(_p, types.ModuleType(_p))
    spec = importlib.util.spec_from_file_location("_inbox_sob_teste", ALVO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_inbox_sob_teste"] = mod
    spec.loader.exec_module(mod)
    return mod


inbox = _carregar()

AGORA = datetime.now(timezone.utc)


def _iso(delta: timedelta) -> str:
    return (AGORA + delta).isoformat()


class _CaixaFalsa(inbox.CaixaDeEntrada):
    """Substitui só a leitura do banco. O julgamento continua sendo o real."""

    def __init__(self, tabelas: dict):
        self._tabelas = tabelas

    def _ler(self, tabela, colunas, filtros=None, limite=200):  # noqa: D102
        linhas = self._tabelas.get(tabela, [])
        if filtros:
            for k, v in filtros.items():
                linhas = [l for l in linhas if l.get(k) == v]
        return linhas[:limite]


# --------------------------------------------------------------------- #
def teste_documento_preso_vira_cartao() -> None:
    print("\n[1] Documento preso no meio da leitura")

    ruim = _CaixaFalsa({"normative_documents": [
        {"id": "1", "status": "fetching", "updated_at": _iso(-timedelta(days=8))},
        {"id": "2", "status": "fetching", "updated_at": _iso(-timedelta(days=8))},
    ]})
    itens = ruim._cerebro_parado()
    presos = [i for i in itens if i.chave == "corpus_preso"]
    checar(len(presos) == 1, "um cartão, não um por documento",
           "trinta cartões enterrariam o incidente que está embaixo")
    checar(presos and presos[0].itens_agrupados == 2,
           "e ele diz quantos são")
    checar(presos and presos[0].company_id is None,
           "sem corretora — é aviso de plataforma",
           "escolher um tenant faria a corretora receber manutenção nossa")
    checar(presos and "não afirmo que o conteúdo mudou" in presos[0].detalhe.lower(),
           "e não afirma o que não sabe")

    # CONTROLE: o mesmo vigia, com o estado saudável.
    bom = _CaixaFalsa({"normative_documents": [
        {"id": "1", "status": "fetching", "updated_at": _iso(-timedelta(minutes=1))},
        {"id": "2", "status": "ingested", "updated_at": _iso(-timedelta(days=8))},
    ]})
    checar(not [i for i in bom._cerebro_parado() if i.chave == "corpus_preso"],
           "CONTROLE: leitura recém-iniciada NÃO vira alarme",
           "sem esta linha, um vigia que acusa sempre passaria no teste")


def teste_atlas_sem_referencia_vira_cartao() -> None:
    print("\n[2] O vigia das rotas sem mapa de referência")

    ruim = _CaixaFalsa({"ura_maps": [
        {"id": "a", "status": "observed"}, {"id": "b", "status": "observed"},
        {"id": "c", "status": "superseded"},
    ]})
    achados = [i for i in ruim._cerebro_parado() if i.chave == "atlas_sem_mapa_ativo"]
    checar(len(achados) == 1, "acusa quando não há nenhum mapa de referência")
    checar(achados and achados[0].itens_agrupados == 2,
           "e conta quantos estão desenhados esperando")

    # CONTROLE 1: com um mapa ativo, cala.
    bom = _CaixaFalsa({"ura_maps": [
        {"id": "a", "status": "active"}, {"id": "b", "status": "observed"},
    ]})
    checar(not [i for i in bom._cerebro_parado() if i.chave == "atlas_sem_mapa_ativo"],
           "CONTROLE: com um mapa ativo, não acusa")

    # CONTROLE 2: sem mapa nenhum, também cala — corretora nova não é defeito.
    vazio = _CaixaFalsa({"ura_maps": []})
    checar(not [i for i in vazio._cerebro_parado() if i.chave == "atlas_sem_mapa_ativo"],
           "CONTROLE: instalação sem nenhum mapa não é acusada",
           "quem nunca observou nada não está com o vigia cego — está começando")


def teste_esteira_de_cartas_parada() -> None:
    print("\n[3] A esteira de cartas parou")

    ruim = _CaixaFalsa({"knowledge_cards": [
        {"id": "1", "status": "published", "published_at": _iso(-timedelta(days=40))},
    ]})
    checar([i for i in ruim._cerebro_parado() if i.chave == "cartas_paradas"],
           "acusa 40 dias sem carta nova")

    bom = _CaixaFalsa({"knowledge_cards": [
        {"id": "1", "status": "published", "published_at": _iso(-timedelta(days=40))},
        {"id": "2", "status": "published", "published_at": _iso(-timedelta(days=1))},
    ]})
    checar(not [i for i in bom._cerebro_parado() if i.chave == "cartas_paradas"],
           "CONTROLE: uma carta de ontem cala o alarme")


def teste_data_ilegivel_nao_vira_alarme() -> None:
    print("\n[4] Carimbo ilegível falha FECHADO")
    checar(inbox._antes_de("banana", AGORA) is False,
           "data ilegível responde NÃO")
    checar(inbox._antes_de(None, AGORA) is False, "e ausência também")
    checar(inbox._antes_de(_iso(-timedelta(days=3)), AGORA) is True,
           "CONTROLE: uma data legível e antiga responde SIM",
           "sem isto, um `_antes_de` que sempre devolve False passaria")


def teste_o_vigia_entra_na_caixa() -> None:
    print("\n[5] E ele está ligado na caixa de verdade")
    with open(ALVO, encoding="utf-8") as fh:
        fonte = fh.read()
    corpo = fonte[fonte.find("def montar("):]
    corpo = corpo[:corpo.find("\n    def ", 10)]
    checar("_cerebro_parado()" in corpo,
           "`montar()` chama o vigia",
           "um método que ninguém chama é o defeito que ele foi criado "
           "para denunciar")


def main() -> int:
    print("=" * 72)
    print("O CEREBRO AVISA QUANDO PARA DE APRENDER")
    print("=" * 72)
    for teste in (teste_documento_preso_vira_cartao,
                  teste_atlas_sem_referencia_vira_cartao,
                  teste_esteira_de_cartas_parada,
                  teste_data_ilegivel_nao_vira_alarme,
                  teste_o_vigia_entra_na_caixa):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"FALHOU — {len(FALHAS)} verificacoes")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O VIGIA ACUSA O QUE PAROU, E CALA QUANDO ESTA TUDO ANDANDO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
