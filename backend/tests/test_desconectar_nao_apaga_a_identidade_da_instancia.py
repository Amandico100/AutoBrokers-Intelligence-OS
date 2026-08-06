"""Desconectar e uma pausa, nao um esquecimento — tambem para a instancia.

Rodar: python backend/tests/test_desconectar_nao_apaga_a_identidade_da_instancia.py

A HISTORIA
----------
06/08/2026. Uma atendente da Resulta passou horas tentando parear e a tela dizia
"O servico de conexao esta indisponivel no momento". O provedor estava DE PE:

    /server/ok        HTTP 200 em 40ms
    /instance/status  HTTP 200 · LoggedIn=false     (a instancia existe e esta sa)

O defeito estava do nosso lado, e a coincidencia que o denuncia e exata:

    _instance_name(Resulta, "observer") ....  ab-obs-04b5cdbc04-1
    a linha aposentada no banco ............  ab-obs-04b5cdbc04-1

`_integration()` filtra `is_active=True`. A linha da Resulta estava desativada,
entao a busca voltava vazia — e o codigo INVENTAVA um token novo
(`secrets.token_hex`) para um nome de instancia que ele mesmo gera de forma
DETERMINISTICA. Ou seja: o nome de sempre, com uma chave que o provedor nunca
viu. Resultado: 401.

E a porta trancava por dentro: o unico ramo que sabe consertar 401 exigia
`integration`, que era `None` justamente porque a linha estava desativada.

O MESMO DEFEITO JA TINHA ACONTECIDO NESTE ARQUIVO
-------------------------------------------------
`_escopo_lembrado` existe porque filtrar `is_active=True` apagava a escolha de
escopo da corretora. Mesma causa, campo ao lado, e ninguem viu na primeira vez.

A LINHA DE CONTROLE (CLAUDE.md 9.2)
-----------------------------------
"Sempre reusar a memoria" e "sempre inventar" acertam casos diferentes. Se o
teste so provasse o reuso, uma implementacao que devolvesse memoria ate quando
nao existe memoria nenhuma passaria — e a corretora NOVA, que precisa de uma
instancia de verdade, ficaria sem.

Por isso cada caso vem em par: com memoria reusa, sem memoria cria.
"""

import importlib.util
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FALHAS = []


def checar(nome, condicao, detalhe=None):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FALHAS.append((nome, detalhe))
        print(f"  [X] {nome}{': ' + str(detalhe) if detalhe else ''}")


for _n in ("app", "app.services", "app.services.whatsapp"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []

_spec = importlib.util.spec_from_file_location(
    "app.services.whatsapp.pairing_orchestrator",
    RAIZ / "app" / "services" / "whatsapp" / "pairing_orchestrator.py")
po = importlib.util.module_from_spec(_spec)
sys.modules["app.services.whatsapp.pairing_orchestrator"] = po
_spec.loader.exec_module(po)

NOME = "ab-obs-04b5cdbc04-1"      # o que `_instance_name` gera para a Resulta
TOKEN_VELHO = "a1b2c3d4e5f6a1b2"  # o que o provedor conhece
FONTE = (RAIZ / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")


def rodar():
    print("== desconectar nao apaga a identidade da instancia ==\n")
    f = po.identidade_da_instancia

    # ------------------------------------------------------------- bloco 1
    print("-- 1. o caso que travou a Resulta --")
    # O nome lembrado e DIFERENTE do deterministico de proposito. Na Resulta os
    # dois coincidem — e foi essa coincidencia que criou o defeito — mas um
    # teste que use os dois iguais NAO CONSEGUE distinguir "reusou a memoria" de
    # "gerou o nome de novo". A mutacao que apaga o reuso do nome passava verde
    # com `NOME` dos dois lados; com um nome diferente, ela reprova.
    LEMBRADO = "ab-obs-de-outro-tempo-7"
    nome, token, tem = f(NOME, None, (LEMBRADO, TOKEN_VELHO))
    checar("linha desativada: reusa o nome que o provedor conhece",
           nome == LEMBRADO, nome)
    checar("linha desativada: reusa a CHAVE, nao inventa outra",
           token == TOKEN_VELHO, "inventou" if token != TOKEN_VELHO else token[:4] + "…")
    checar("e ganha direito ao ramo que conserta 401/404", tem is True, tem)

    # ------------------------------------------------------------- bloco 2
    #
    # A LINHA DE CONTROLE. Sem ela, uma implementacao que sempre devolvesse
    # "tem identidade" passaria no bloco 1 inteiro — e a corretora nova nunca
    # teria uma instancia criada.
    print("\n-- 2. CONTROLE: quem nunca teve instancia --")
    nome2, token2, tem2 = f(NOME, None, None)
    checar("sem memoria: usa o nome deterministico", nome2 == NOME, nome2)
    checar("sem memoria: gera uma chave nova", token2 != TOKEN_VELHO and len(token2) >= 16, len(token2))
    checar("sem memoria: NAO tem identidade (vai criar do zero)", tem2 is False, tem2)
    checar("e duas chamadas sem memoria dao chaves DIFERENTES (e aleatoria mesmo)",
           f(NOME, None, None)[1] != f(NOME, None, None)[1])

    # ------------------------------------------------------------- bloco 3
    print("\n-- 3. a linha ATIVA continua mandando --")
    ativa = {"instance_id": "ab-obs-ativa-9", "token": "ffffffffffffffff"}
    nome3, token3, tem3 = f(NOME, ativa, (NOME, TOKEN_VELHO))
    checar("ativa vence a lembrada no nome", nome3 == "ab-obs-ativa-9", nome3)
    checar("ativa vence a lembrada na chave", token3 == "ffffffffffffffff", token3[:4] + "…")
    checar("e tem identidade", tem3 is True, tem3)

    # ------------------------------------------------------------- bloco 4
    #
    # Meia memoria e o que criou o defeito: nome velho com chave nova. A busca
    # so pode devolver memoria quando tem os DOIS.
    print("\n-- 4. meia memoria nao e memoria --")
    i = FONTE.index("async def _instancia_lembrada")
    corpo = FONTE[i:FONTE.index("async def _persist_integration", i)]
    checar("a busca exige instancia E token juntos",
           re.search(r"if\s+instancia\s+and\s+token", corpo) is not None)
    checar("e ela NAO filtra por is_active (era esse o esquecimento)",
           "is_active" not in corpo.split('"""')[-1])

    # ------------------------------------------------------------- bloco 5
    print("\n-- 5. a fiacao: quem decide o ramo do 401 --")
    j = FONTE.index("async def _prepare_and_connect")
    fluxo = FONTE[j:j + 4000]
    checar("o create so roda para quem NAO tem identidade",
           "if not tem_identidade:" in fluxo)
    checar("o conserto de 401/404 roda para ativa OU lembrada",
           "if tem_identidade and status_response.status_code in (401, 404):" in fluxo)
    checar("e ninguem mais decide isso por `integration` sozinho",
           "if integration and status_response.status_code" not in fluxo)

    print(f"\n{'=' * 60}")
    print(f"PASS={PASS} FAIL={FAIL}")
    if FALHAS:
        print("\nFALHAS:")
        for n, d in FALHAS:
            print(f"  - {n}: {d}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(rodar())
