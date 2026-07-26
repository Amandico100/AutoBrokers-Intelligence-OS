"""SPEC-061 §8 — quem pode o quê no Portal Admin.

Por que este arquivo existe
---------------------------
Hoje o Admin autoriza por um bit: `master` ou não. Quem entra vê 39 telas e
pode acionar 114 rotas. As regras da §8.5 —

    "o financeiro não acessa conteúdo sensível de corretora"
    "o auditor é somente leitura"
    "o suporte não altera cobrança"
    "o curador não acessa secrets"

— não estavam mal implementadas: **não tinham onde ser escritas**.

Agora têm, e o perigo mudou de lugar. Uma permission de escrita que caia por
descuido no conjunto do auditor não produz erro visível: produz um auditor que
age, e ninguém descobre até ele agir. Uma matriz de permissão erra em silêncio.

Por isso cada regra da §8.5 é um caso aqui.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.control_plane", ("app", "services", "control_plane"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
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


R = carregar("app.services.control_plane.rbac")
AGORA = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)

# Todo verbo que MUDA alguma coisa. É a lista que define "somente leitura".
ESCRITA = frozenset(p for p in R.PERMISSIONS if not (
    p.endswith(".read") or p.endswith("_read") or ".read" in p))


def teste_matriz_integra():
    print("\n[1] A matriz não cita permission que não existe")
    checar(len(R.PERMISSIONS) == len(R.CONJUNTO_DE_PERMISSIONS),
           "nenhuma permission repetida na lista")
    for papel, dados in R.PAPEIS.items():
        orfas = set(dados["permissions"]) - R.CONJUNTO_DE_PERMISSIONS
        checar(not orfas, f"'{papel}' não concede permission inexistente",
               str(sorted(orfas)))
    checar(all(r in R.PAPEIS for r in R.PAPEL_LEGADO.values()),
           "o mapeamento do papel histórico aponta para papel que existe")


def teste_auditor_e_somente_leitura():
    print("\n[2] §8.5 — o auditor é somente leitura")
    do_auditor = R.permissions_do_papel("platform_auditor")
    escrita = sorted(do_auditor & ESCRITA)
    checar(not escrita,
           "o auditor não tem NENHUM verbo de escrita",
           f"teria: {escrita}")
    checar("audit.read" in do_auditor, "mas lê a trilha de auditoria")
    checar("work_runs.read" in do_auditor, "e lê os trabalhos")


def teste_financeiro_nao_ve_conteudo_da_corretora():
    print("\n[3] §8.5 — o financeiro não acessa conteúdo sensível")
    fin = R.permissions_do_papel("platform_finance")
    for proibida in ("knowledge.read", "intelligence.read", "artifacts.read",
                     "memory.metadata.read", "memory.sensitive.read",
                     "research.read"):
        checar(proibida not in fin,
               f"financeiro NÃO tem '{proibida}' — nem em leitura")
    checar("finance.manage" in fin, "mas gerencia cobrança")
    checar("companies.read" in fin, "e vê quais corretoras existem")


def teste_suporte_nao_mexe_em_cobranca():
    print("\n[4] §8.5 — o suporte não altera billing")
    sup = R.permissions_do_papel("platform_support")
    for proibida in ("finance.manage", "finance.read",
                     "companies.suspend", "companies.manage"):
        checar(proibida not in sup, f"suporte NÃO tem '{proibida}'")
    checar("companies.support_access" in sup,
           "mas abre sessão de suporte na corretora que precisa de ajuda")


def teste_curador_nao_acessa_segredo():
    print("\n[5] §8.5 — o curador não acessa secrets")
    cur = R.permissions_do_papel("platform_curator")
    for proibida in ("connections.read", "connections.manage",
                     "connections.rotate", "security.manage"):
        checar(proibida not in cur, f"curador NÃO tem '{proibida}'")
    checar("knowledge.publish" in cur, "mas publica conhecimento")


def teste_seguranca_nao_le_conversa_sem_justificativa():
    print("\n[6] §8.5 — security não vê conteúdo sensível sem justificativa")
    sec = R.permissions_do_papel("platform_security")
    checar("memory.sensitive.read" not in sec,
           "nem o papel de segurança recebe memória sensível de graça")
    checar("connections.rotate" in sec, "mas gira segredo — é a função dele")
    checar("companies.suspend" in sec, "e pode suspender diante de risco")


def teste_so_o_dono_muda_as_regras_do_jogo():
    print("\n[7] Configuração de sistema e jurídico ficam com o dono")
    for papel in R.PAPEIS:
        tem = R.permissions_do_papel(papel)
        if papel == "platform_owner":
            checar("system.manage" in tem and "legal.manage" in tem,
                   "o dono tem as duas")
        else:
            checar("system.manage" not in tem and "legal.manage" not in tem,
                   f"'{papel}' não tem system.manage nem legal.manage")


def teste_papel_desconhecido_nao_concede_nada():
    print("\n[8] Fail-closed: na dúvida, nega")
    checar(R.permissions_do_papel("platform_deus") == frozenset(),
           "papel inexistente não concede nada")

    d = R.decidir(permission_key="inventada.qualquer",
                  papeis=["platform_owner"], agora=AGORA)
    checar(not d.permitido,
           "permission desconhecida é negada MESMO para o dono", d.motivo)

    d2 = R.decidir(permission_key="companies.suspend", papeis=[], agora=AGORA)
    checar(not d2.permitido, "sem papel nenhum, nada é concedido")


def teste_deny_vence_papel():
    print("\n[9] Uma remoção nominal não é anulada pelo papel")
    override_deny = [{"permission_key": "companies.suspend", "effect": "deny",
                      "starts_at": (AGORA - timedelta(days=1)).isoformat(),
                      "expires_at": (AGORA + timedelta(days=1)).isoformat()}]
    d = R.decidir(permission_key="companies.suspend",
                  papeis=["platform_owner"], overrides=override_deny, agora=AGORA)
    checar(not d.permitido,
           "o `deny` contém até o dono — é o instrumento de conter alguém "
           "no meio de um incidente", d.motivo)
    checar(d.origem == "override", "e a origem da negativa é declarada", d.origem)


def teste_override_expirado_nao_vale():
    print("\n[10] Exceção com prazo vencido deixa de valer sozinha")
    vencido = [{"permission_key": "finance.manage", "effect": "allow",
                "starts_at": (AGORA - timedelta(days=10)).isoformat(),
                "expires_at": (AGORA - timedelta(days=1)).isoformat()}]
    d = R.decidir(permission_key="finance.manage", papeis=["platform_support"],
                  overrides=vencido, agora=AGORA)
    checar(not d.permitido, "allow vencido não concede", d.motivo)

    vigente = [{"permission_key": "finance.manage", "effect": "allow",
                "starts_at": (AGORA - timedelta(hours=1)).isoformat(),
                "expires_at": (AGORA + timedelta(hours=1)).isoformat()}]
    d2 = R.decidir(permission_key="finance.manage", papeis=["platform_support"],
                   overrides=vigente, agora=AGORA)
    checar(d2.permitido, "allow vigente concede", d2.motivo)
    checar(d2.origem == "override", "e fica registrado que veio de exceção")

    futuro = [{"permission_key": "finance.manage", "effect": "allow",
               "starts_at": (AGORA + timedelta(days=1)).isoformat(),
               "expires_at": (AGORA + timedelta(days=2)).isoformat()}]
    d3 = R.decidir(permission_key="finance.manage", papeis=["platform_support"],
                   overrides=futuro, agora=AGORA)
    checar(not d3.permitido, "allow que ainda não começou também não concede")

    ilegivel = [{"permission_key": "finance.manage", "effect": "allow",
                 "starts_at": "data-quebrada", "expires_at": "??"}]
    d4 = R.decidir(permission_key="finance.manage", papeis=["platform_support"],
                   overrides=ilegivel, agora=AGORA)
    checar(not d4.permitido,
           "data ilegível é tratada como vencida — erro de formatação não "
           "abre acesso")


def teste_acumulo_de_papeis():
    print("\n[11] Quem tem dois papéis soma os dois")
    d = R.decidir(permission_key="finance.manage",
                  papeis=["platform_support", "platform_finance"], agora=AGORA)
    checar(d.permitido, "suporte + financeiro passa a poder gerenciar cobrança")
    checar(d.origem == "role", "pelo papel, não por exceção")


def teste_step_up_e_risco():
    print("\n[12] Ação que muda a vida da corretora pede confirmação")
    for critica in ("companies.suspend", "connections.rotate",
                    "finance.manage", "memory.sensitive.read"):
        checar(R.exige_step_up(critica), f"'{critica}' exige step-up")
    checar(not R.exige_step_up("work_runs.read"),
           "leitura simples não interrompe o operador o tempo todo")

    checar(R.risco_de("companies.suspend") == "critical",
           "suspender corretora é crítico", R.risco_de("companies.suspend"))
    checar(R.risco_de("work_runs.read") == "low", "leitura é baixo risco")
    checar(R.risco_de("permission.que.nao.existe") == "low",
           "desconhecida é baixo risco — ela não concede nada mesmo")

    # O CHECK do banco exige motivo escrito em ação crítica. Se uma permission
    # crítica não estivesse no mapa de risco, a auditoria a gravaria como
    # `low` e o motivo deixaria de ser cobrado.
    for critica in R.EXIGEM_STEP_UP:
        checar(R.risco_de(critica) in ("high", "critical"),
               f"'{critica}' tem risco declarado alto o bastante",
               R.risco_de(critica))


def teste_403_nao_vaza_a_matriz():
    print("\n[13] O 403 não conta ao curioso o que ele não pode ver")
    d = R.decidir(permission_key="finance.manage", papeis=["platform_viewer"],
                  agora=AGORA)
    corpo = d.como_403()
    checar(corpo.get("error") == "forbidden", "resposta estável")
    checar("papeis" not in corpo and "roles" not in corpo,
           "sem a lista de papéis de quem tentou")
    texto = str(corpo).lower()
    checar("platform_finance" not in texto,
           "e sem dizer qual papel teria o poder — isso é mapa para quem sonda")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 §8 — QUEM PODE O QUÊ NO PORTAL ADMIN")
    print("=" * 68)
    for teste in (
        teste_matriz_integra,
        teste_auditor_e_somente_leitura,
        teste_financeiro_nao_ve_conteudo_da_corretora,
        teste_suporte_nao_mexe_em_cobranca,
        teste_curador_nao_acessa_segredo,
        teste_seguranca_nao_le_conversa_sem_justificativa,
        teste_so_o_dono_muda_as_regras_do_jogo,
        teste_papel_desconhecido_nao_concede_nada,
        teste_deny_vence_papel,
        teste_override_expirado_nao_vale,
        teste_acumulo_de_papeis,
        teste_step_up_e_risco,
        teste_403_nao_vaza_a_matriz,
    ):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} REGRA(S) QUEBRADA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("CADA PAPEL PODE SÓ O QUE DEVE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
