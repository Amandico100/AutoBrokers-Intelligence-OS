# -*- coding: utf-8 -*-
"""Um `ref` escrito errado na lista de finalização nunca fecha chamado — e nada avisa.

SPEC-118, fatia F5. O Founder pediu, em 26/09/2026, *"todas as seguradoras
liberadas, para não ter confusão depois"*. 🔴 **O que evita a confusão não é
liberar tudo: é a trava.**

## O defeito que este arquivo fecha

Com `DISPATCH_FINALIZE_MODE=test`, a variável `DISPATCH_FINALIZE_LIVE_PLAYBOOKS`
é a única coisa que autoriza um corredor a **concluir** o pedido na seguradora.
Um `ref` com uma letra trocada não casa corredor nenhum — e o efeito é o pior
possível: o acionamento anda até o fim, fala com a URA de verdade e **cancela na
última tela**. O segurado ouviu *"estou acionando"*, a seguradora registrou uma
conversa, e ninguém vem.

⚠️ **E o sintoma é indistinguível do estado legítimo.** Um corredor deixado de
fora de propósito e um corredor escrito errado produzem exatamente a mesma
saída em `finalize_abre_de_verdade`: ausência. Sem uma segunda pergunta, não há
como separar os dois — é o CLAUDE.md §9.5 aplicado a configuração.

## As duas perguntas, e por que uma não bastava

```
quem ABRE de verdade?      <- finalize_abre_de_verdade   (já existia)
quem foi ESCRITO e NÃO existe?  <- finalize_refs_fantasma  (nasce aqui)
```

## As linhas de CONTROLE

1. **lista com refs corretos → nenhum fantasma.** Se esta falhasse, o guarda
   acusaria qualquer configuração e ninguém o leria;
2. **lista vazia → nenhum fantasma** (e não "tudo é fantasma");
3. 🔴 **`DISPATCH_FINALIZE_MODE=live` não apaga o fantasma.** É a armadilha real:
   em `live` a lista deixa de decidir — e quem trocar o modo de volta para
   `test` herda a lista errada, calada. O aviso tem de sobreviver ao modo.

⚠️ Tudo aqui chama as funções REAIS de `insurer_dispatch_service` (CLAUDE.md
§9.4). Nenhum `ref` de corretora, nenhum nome de cliente: os `ref` são de
corredor, que é catálogo de produto (CLAUDE.md §13.9).
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"

VAR = "DISPATCH_FINALIZE_LIVE_PLAYBOOKS"
MODO = "DISPATCH_FINALIZE_MODE"

#: 📊 Os dois `ref` que estavam no `/health` de produção em 26/09/2026.
REF_PORTO = "porto-auto-whatsapp@v1"
REF_YELUM = "yelum-auto-whatsapp@v3"
#: O universo de corredores, encolhido ao que este arquivo precisa.
CONHECIDOS = (REF_PORTO, REF_YELUM, "allianz-auto-whatsapp@v1")
#: A letra trocada. `@v2` não existe, e a diferença é invisível a olho.
FANTASMA = "porto-auto-whatsapp@v2"


def _carregar(nome: str, caminho: Path):
    """O arquivo REAL de produção, sem subir os `__init__` da stack de IA."""
    nomes = ("app", "app.services")
    anteriores = {n: sys.modules.get(n) for n in nomes}
    injetados = [n for n in nomes if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


DS = _carregar("app.services.insurer_dispatch_service", MOTOR_PY)


def _com_lista(monkeypatch, valor: str, modo: str = "test"):
    monkeypatch.setenv(VAR, valor)
    monkeypatch.setenv(MODO, modo)
    # o freio de emergência é outro portão; aqui ele não pode mascarar nada
    monkeypatch.delenv("ACIONAMENTO_FREIO_DE_EMERGENCIA", raising=False)


def test_o_ref_escrito_errado_aparece_como_FANTASMA(monkeypatch):
    _com_lista(monkeypatch, "%s,%s" % (REF_PORTO, FANTASMA))
    fantasmas = DS.refs_de_finalizacao_sem_corredor(CONHECIDOS)
    assert fantasmas == [FANTASMA], fantasmas
    # 🔴 e a pergunta antiga, sozinha, NÃO via o defeito:
    abre = [r for r in CONHECIDOS if DS.finalize_live_for(r)]
    assert abre == [REF_PORTO], abre
    assert FANTASMA not in abre


def test_CONTROLE_lista_certa_nao_acusa_ninguem(monkeypatch):
    _com_lista(monkeypatch, "%s,%s" % (REF_PORTO, REF_YELUM))
    assert DS.refs_de_finalizacao_sem_corredor(CONHECIDOS) == []


def test_CONTROLE_lista_vazia_nao_acusa_ninguem(monkeypatch):
    _com_lista(monkeypatch, "")
    assert DS.refs_de_finalizacao_declarados() == []
    assert DS.refs_de_finalizacao_sem_corredor(CONHECIDOS) == []


def test_CONTROLE_o_aviso_sobrevive_ao_modo_live(monkeypatch):
    """Em `live` a lista deixa de decidir — e o fantasma continua lá, esperando."""
    _com_lista(monkeypatch, "%s,%s" % (REF_PORTO, FANTASMA), modo="live")
    assert DS.refs_de_finalizacao_sem_corredor(CONHECIDOS) == [FANTASMA]


def test_a_lista_e_lida_num_lugar_SO(monkeypatch):
    """Duas leituras divergem no dia em que uma aprender a aceitar espaço."""
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    assert fonte.count('getenv("%s"' % VAR) == 1, (
        "a variavel passou a ser lida em mais de um lugar de "
        "insurer_dispatch_service.py — a divergencia e questao de tempo")


def test_espaco_em_volta_do_ref_nao_cria_fantasma(monkeypatch):
    """Quem digita a lista na tela do EasyPanel põe espaço depois da vírgula."""
    _com_lista(monkeypatch, "  %s ,  %s  " % (REF_PORTO, REF_YELUM))
    assert DS.refs_de_finalizacao_declarados() == [REF_PORTO, REF_YELUM]
    assert DS.refs_de_finalizacao_sem_corredor(CONHECIDOS) == []


def test_o_health_publica_o_sinal(monkeypatch):
    """O guarda do PRODUTO: sem a linha em `main.py`, o defeito continua invisível.

    🔴 **Esta asserção nasceu FROUXA e a mutação a pegou.** A primeira versão
    perguntava se a string `sinais["finalize_refs_fantasma"]` aparecia em
    `main.py`. 📊 Medido em 26/09/2026: apagando a linha que CALCULA o sinal, o
    guarda continuou **verde** — porque o caminho de erro, logo abaixo, tem a
    mesma chave (`= None`). Era um guarda que não tinha como falhar
    (CLAUDE.md §9.3).

    Agora a asserção é sobre a **atribuição que chama o motor**, e não sobre a
    chave: só o caminho de sucesso a satisfaz.
    """
    fonte = (RAIZ / "app" / "main.py").read_text(encoding="utf-8")
    atribuicao = ('sinais["finalize_refs_fantasma"] = '
                  "refs_de_finalizacao_sem_corredor(")
    assert atribuicao in fonte, (
        "o /health nao CALCULA os refs fantasma — a trava existe e ninguem a ve. "
        "⚠️ a chave sozinha nao basta: o caminho de erro tambem a escreve")
    assert 'sinais["finalize_refs_fantasma"] = None' in fonte, (
        "o caminho de erro do /health precisa publicar None — lista vazia ali "
        "diria 'olhei e nao ha fantasma', e ninguem olhou")
