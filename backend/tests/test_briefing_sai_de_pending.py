"""Publicar não é entregar — e `pending` mudo é proibido.

O defeito, medido em 02/08/2026
-------------------------------
    briefing_publications ......... 26
    delivery_status = 'pending' ... 26   (100%)
    delivery_policy.decidir() ..... ZERO chamadores em producao

A política de entrega existia: pura, bem escrita, com quiet hours, teto de
push por dia, severidade que fura silêncio e o motivo em português. E
**ninguém a chamava.** O sistema publicava, gravava `pending`, e ficava assim
para sempre.

Não havia bug. Havia um fio solto entre duas peças prontas — que é o defeito
mais caro que existe, porque nada quebra e nada acontece.

O que este teste protege
------------------------
1. que a política volte a ser chamada
2. que **nenhuma publicação termine em `pending`** — nem quando falha
3. que canal indisponível vire MOTIVO ESCRITO, não silêncio
4. que o WhatsApp não saia antes do governador de envio existir
5. que a falha de um canal não derrube os outros nem a publicação

O caso [4] é o que evita repetir um defeito conhecido: a cobrança percorre
até 50 destinatários **sem pausa nenhuma** (SPEC-063 C.1), e o governador que
resolve isso ainda não existe. Mandar briefing por WhatsApp antes dele seria
multiplicar o problema por outro canal.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
FALHAS: list[str] = []


def _pacote(nome: str, *partes: str) -> None:
    if nome in sys.modules:
        return
    caminho = os.path.join(RAIZ, *partes)
    m = types.ModuleType(nome)
    m.__path__ = [caminho]
    m.__package__ = nome
    sys.modules[nome] = m


for _nome, _partes in (
    ("app", ("app",)),
    ("app.services", ("app", "services")),
    ("app.services.intelligence", ("app", "services", "intelligence")),
):
    _pacote(_nome, *_partes)


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


# ---------------------------------------------------------------------------
# Um banco falso, mínimo: registra o que foi gravado.
# ---------------------------------------------------------------------------

class _Resposta:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class _Tabela:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self._update = None

    def update(self, valores):
        self._update = valores
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        if self._update is not None:
            self.banco.gravados.append((self.nome, dict(self._update)))
            self._update = None
        return self

    def in_(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self.banco.explodir_no_update:
            raise RuntimeError("banco fora do ar")
        return _Resposta(count=self.banco.pushes_hoje)


class BancoFalso:
    def __init__(self, *, pushes_hoje=0, explodir_no_update=False):
        self.gravados: list[tuple[str, dict]] = []
        self.pushes_hoje = pushes_hoje
        self.explodir_no_update = explodir_no_update

    def table(self, nome):
        return _Tabela(self, nome)


PUBLICACAO = {
    "id": "pub-1",
    "company_id": "empresa-1",
    "briefing_type": "daily_operational",
    "headline": "3 coisas precisam de você hoje",
    "summary_text": "resumo",
    "critical_count": 1,
    "recommendation_count": 2,
}

# O vocabulário que a coluna aceita, copiado do CHECK do banco:
#
#   briefing_publications_delivery_ck
#   CHECK (delivery_status = ANY (ARRAY['pending','sent','partial',
#                                       'failed','skipped','not_applicable']))
#
# Este conjunto existe aqui porque o banco falso NÃO valida constraint. A
# primeira versão do executor escrevia 'delivered' e 'delivered_partial', os
# testes passaram, e o Postgres recusou na hora de aplicar o backfill.
#
# Estado que o schema não conhece não é estado: é exceção esperando acontecer,
# no meio de uma publicação que já deu certo.
STATUS_QUE_O_BANCO_ACEITA = {
    "pending", "sent", "partial", "failed", "skipped", "not_applicable",
}


# ---------------------------------------------------------------------------

def teste_a_politica_volta_a_ser_chamada():
    print("\n[1] A publicação chama a política de entrega")
    fonte_servico = open(
        os.path.join(RAIZ, "app", "services", "intelligence", "briefing_service.py"),
        encoding="utf-8").read()

    checar("DeliveryExecutor" in fonte_servico,
           "briefing_service chama o executor de entrega",
           "sem isto a publicação nasce 'pending' e morre 'pending'")

    fonte_exec = open(
        os.path.join(RAIZ, "app", "services", "intelligence", "delivery_executor.py"),
        encoding="utf-8").read()
    checar("from .delivery_policy import" in fonte_exec and "decidir(" in fonte_exec,
           "o executor usa a política que já existia",
           "escrever uma segunda política ao lado seria motor paralelo (CLAUDE.md §5)")

    # A chamada precisa vir DEPOIS de a publicação existir: entregar algo que
    # ainda não foi gravado não teria o que registrar.
    pos_insert = fonte_servico.find('table("briefing_publications").insert')
    pos_entrega = fonte_servico.find("self._entregar(")
    checar(pos_insert != -1 and pos_entrega != -1 and pos_insert < pos_entrega,
           "a entrega acontece depois da publicação estar gravada")


def teste_nunca_termina_em_pending():
    print("\n[2] Nenhuma publicação termina em 'pending'")
    mod = carregar("app.services.intelligence.delivery_executor")

    for nome_caso, perfil in (
        ("perfil vazio", {}),
        ("só dashboard", {"channels": ["dashboard"]}),
        ("dashboard + e-mail sem provedor", {"channels": ["dashboard", "email"],
                                             "recipient_refs": {"email": ["a@b.com"]}}),
        ("com whatsapp", {"channels": ["dashboard", "whatsapp"]}),
        ("canal inventado", {"channels": ["pombo-correio"]}),
    ):
        banco = BancoFalso()
        r = mod.DeliveryExecutor(banco).entregar(dict(PUBLICACAO), perfil=perfil)
        status = r.get("delivery_status")
        checar(status and status != "pending",
               f"{nome_caso} → estado final '{status}'",
               "pending é a ausência de resposta, não uma resposta")

        # O caso que o banco falso sozinho não pegaria.
        checar(status in STATUS_QUE_O_BANCO_ACEITA,
               f"{nome_caso} → '{status}' é um estado que a coluna aceita",
               f"fora do CHECK do banco: {sorted(STATUS_QUE_O_BANCO_ACEITA)}")

        gravou = [g for g in banco.gravados if g[0] == "briefing_publications"]
        checar(bool(gravou), f"{nome_caso} → o estado foi gravado")
        if gravou:
            detalhe = gravou[-1][1].get("delivery_detail") or {}
            checar(bool(detalhe.get("motivo_da_politica")),
                   f"{nome_caso} → o motivo da política ficou registrado")


def teste_canal_indisponivel_vira_motivo_escrito():
    print("\n[3] Canal indisponível vira motivo, não silêncio")
    mod = carregar("app.services.intelligence.delivery_executor")
    banco = BancoFalso()
    mod.DeliveryExecutor(banco).entregar(
        dict(PUBLICACAO),
        perfil={"channels": ["dashboard", "email", "whatsapp"],
                "recipient_refs": {"email": ["corretor@exemplo.com"]}})

    detalhe = banco.gravados[-1][1]["delivery_detail"]
    por_canal = {c["canal"]: c for c in detalhe["canais"]}

    checar("email" in por_canal, "o canal de e-mail aparece no registro")
    if "email" in por_canal:
        motivo = por_canal["email"]["motivo"]
        checar(bool(motivo) and len(motivo) > 10,
               "o e-mail diz POR QUE não saiu",
               f"motivo={motivo!r}")
        checar("P-13" in motivo or "não configurado" in motivo or "indisponível" in motivo,
               "o motivo do e-mail aponta a pendência",
               f"motivo={motivo!r}")

    checar(por_canal.get("dashboard", {}).get("ok") is True,
           "o dashboard sempre entrega — a publicação está na tela",
           "dizer 'não entregue' para algo visível seria mentir para o corretor")


def teste_whatsapp_nao_sai_sem_governador():
    print("\n[4] O briefing não sai por WhatsApp antes do governador existir")
    mod = carregar("app.services.intelligence.delivery_executor")
    banco = BancoFalso()
    mod.DeliveryExecutor(banco).entregar(
        dict(PUBLICACAO), perfil={"channels": ["whatsapp"]})

    detalhe = banco.gravados[-1][1]["delivery_detail"]
    wpp = next((c for c in detalhe["canais"] if c["canal"] == "whatsapp"), None)

    checar(wpp is not None, "o canal de WhatsApp aparece no registro")
    if wpp:
        checar(wpp["ok"] is False, "não enviou")
        checar("governador" in wpp["motivo"].lower(),
               "o motivo é a ausência do governador de envio",
               f"motivo={wpp['motivo']!r}")

    # A guarda é por IMPORT, não por flag: flag se liga por engano.
    fonte = open(os.path.join(RAIZ, "app", "services", "intelligence",
                              "delivery_executor.py"), encoding="utf-8").read()
    checar("outbound_governor" in fonte,
           "a guarda depende do módulo do governador existir",
           "uma flag de configuração pode ser ligada sem o governador existir")


def teste_falha_de_canal_nao_derruba_o_resto():
    print("\n[5] Um canal que explode não derruba os outros")
    mod = carregar("app.services.intelligence.delivery_executor")

    class CanalQueExplode(mod.DeliveryExecutor):
        def _email(self, publicacao, perfil):
            raise RuntimeError("provedor caiu")

    banco = BancoFalso()
    r = CanalQueExplode(banco).entregar(
        dict(PUBLICACAO),
        perfil={"channels": ["dashboard", "email"],
                "recipient_refs": {"email": ["a@b.com"]}})

    checar(r.get("delivery_status") == "partial",
           "o estado reflete entrega parcial",
           f"veio={r.get('delivery_status')}")

    detalhe = banco.gravados[-1][1]["delivery_detail"]
    email = next((c for c in detalhe["canais"] if c["canal"] == "email"), None)
    checar(email is not None and email["ok"] is False,
           "a falha do e-mail ficou registrada")
    checar(email is not None and "RuntimeError" in email["motivo"],
           "o tipo da exceção está no motivo",
           "sem isso, investigar depois é adivinhação")

    # E o pior caso: nem gravar o estado funciona. Não pode explodir na cara
    # de quem publicou — o briefing continua publicado.
    banco2 = BancoFalso(explodir_no_update=True)
    try:
        r2 = mod.DeliveryExecutor(banco2).entregar(dict(PUBLICACAO), perfil={})
        checar(r2.get("ok") is True,
               "banco fora do ar não derruba a publicação",
               "a entrega é best-effort; a publicação já aconteceu")
    except Exception as exc:  # noqa: BLE001
        checar(False, "banco fora do ar não derruba a publicação",
               f"explodiu: {type(exc).__name__}")


def main() -> int:
    print("=" * 68)
    print("PUBLICAR NÃO É ENTREGAR — E 'PENDING' MUDO É PROIBIDO")
    print("=" * 68)
    for teste in (teste_a_politica_volta_a_ser_chamada,
                  teste_nunca_termina_em_pending,
                  teste_canal_indisponivel_vira_motivo_escrito,
                  teste_whatsapp_nao_sai_sem_governador,
                  teste_falha_de_canal_nao_derruba_o_resto):
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
    print("TODA PUBLICAÇÃO TERMINA COM UM ESTADO E UM MOTIVO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
