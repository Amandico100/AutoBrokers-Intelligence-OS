"""SPEC-055 — testes de comportamento do Work OS.

Roda offline, sem banco: os módulos de idempotência e aprovação são puros o
suficiente para serem exercitados com um duplo do Supabase. O que importa aqui
é a **lógica de garantia**, não a ida ao banco — o banco já foi testado
diretamente pelas migrations.

    python backend/tests/test_spec055_work_os.py
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _carregar(caminho_rel: str, nome: str):
    caminho = os.path.join(RAIZ, caminho_rel)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


efeitos = _carregar("app/services/work/effects.py", "_t_effects")

FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ---------------------------------------------------------------------------
# Duplo mínimo do cliente Supabase
# ---------------------------------------------------------------------------


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, store: dict, nome: str):
        self.store = store
        self.nome = nome
        self._filtros: dict = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        return self

    def in_(self, *_a, **_k):
        return self

    def lt(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def maybe_single(self):
        return self

    def insert(self, registro):
        self._pendente = registro
        return self

    def update(self, campos):
        self._update = campos
        return self

    def execute(self):
        linhas = self.store.setdefault(self.nome, [])
        if hasattr(self, "_pendente"):
            reg = dict(self._pendente)
            chave = (reg.get("company_id"), reg.get("idempotency_key"))
            if reg.get("idempotency_key") and any(
                (x.get("company_id"), x.get("idempotency_key")) == chave for x in linhas
            ):
                del self._pendente
                raise Exception("duplicate key value violates unique constraint")
            reg.setdefault("id", f"id-{len(linhas)+1}")
            linhas.append(reg)
            del self._pendente
            return FakeResult([reg])
        if hasattr(self, "_update"):
            for x in linhas:
                if all(x.get(k) == v for k, v in self._filtros.items()):
                    x.update(self._update)
            del self._update
            return FakeResult(linhas)
        achados = [x for x in linhas if all(x.get(k) == v for k, v in self._filtros.items())]
        return FakeResult(achados[0] if achados and "maybe" not in str(self._filtros) else achados)


class FakeDB:
    def __init__(self):
        self.store: dict = {}

    def table(self, nome):
        return FakeTable(self.store, nome)


# ---------------------------------------------------------------------------


def teste_chave_idempotencia():
    print("\n[1] Chave de idempotência")
    k1 = efeitos.build_idempotency_key("c1", "r1", "s1", "whatsapp.send", {"texto": "oi"})
    k2 = efeitos.build_idempotency_key("c1", "r1", "s1", "whatsapp.send", {"texto": "oi"})
    k3 = efeitos.build_idempotency_key("c1", "r1", "s1", "whatsapp.send", {"texto": "OUTRO"})
    k4 = efeitos.build_idempotency_key("c2", "r1", "s1", "whatsapp.send", {"texto": "oi"})

    checar(k1 == k2, "mesmo conteúdo gera a mesma chave")
    checar(k1 != k3, "conteúdo diferente gera chave diferente",
           "senão uma correção de texto viraria reenvio da mensagem antiga")
    checar(k1 != k4, "tenants diferentes nunca compartilham chave")
    checar(k1.startswith("c1:r1:s1:whatsapp.send:"), "formato canônico da SPEC-053 §10.5")


def teste_fingerprint():
    print("\n[2] Fingerprint de conteúdo")
    a = efeitos.fingerprint({"para": "5511999", "texto": "Boleto em anexo"})
    b = efeitos.fingerprint({"texto": "Boleto em anexo", "para": "5511999"})
    c = efeitos.fingerprint({"para": "5511888", "texto": "Boleto em anexo"})
    checar(a == b, "ordem das chaves não altera o fingerprint")
    checar(a != c, "destinatário diferente altera o fingerprint",
           "é o que impede aprovar para um e enviar para outro")


def teste_reserva_impede_repeticao():
    print("\n[3] Reserva de efeito impede repetição")
    db = FakeDB()
    svc = efeitos.WorkEffectService(db)
    chave = "c1:r1:s1:whatsapp.send:abc"

    executou = {"n": 0}
    try:
        with svc.reserve(company_id="c1", work_run_id="r1", effect_type="whatsapp.send",
                         provider="evolution", idempotency_key=chave,
                         request_payload={"t": 1}) as h:
            executou["n"] += 1
            h.confirmar("msg-123")
    except Exception as exc:  # noqa: BLE001
        FALHAS.append(f"primeira reserva falhou: {exc}")

    checar(executou["n"] == 1, "primeira execução acontece")

    bloqueou = False
    try:
        with svc.reserve(company_id="c1", work_run_id="r1", effect_type="whatsapp.send",
                         provider="evolution", idempotency_key=chave,
                         request_payload={"t": 1}) as h:
            executou["n"] += 1
            h.confirmar("msg-456")
    except efeitos.EffectAlreadyExecuted:
        bloqueou = True
    except Exception:  # noqa: BLE001
        pass

    checar(bloqueou, "segunda tentativa com a MESMA chave é bloqueada")
    checar(executou["n"] == 1, "o efeito externo NÃO foi executado duas vezes",
           "esta é a garantia que impede cobrar ou enviar em duplicidade")


def teste_crash_vira_unknown():
    print("\n[4] Crash entre reservar e confirmar")
    db = FakeDB()
    svc = efeitos.WorkEffectService(db)

    try:
        with svc.reserve(company_id="c1", work_run_id="r1", effect_type="portal.submit",
                         provider="allianz", idempotency_key="k-crash",
                         request_payload={"x": 1}):
            raise RuntimeError("worker morreu aqui")
    except RuntimeError:
        pass
    except Exception as exc:  # noqa: BLE001
        FALHAS.append(f"exceção inesperada: {exc}")

    linhas = db.store.get("work_effects", [])
    estado = linhas[0].get("status") if linhas else None
    checar(estado == "unknown", "efeito sem confirmação vira 'unknown'",
           f"estado={estado} — precisa de reconciliação, nunca repetição automática")


def teste_consulta_falha_e_fail_closed():
    print("\n[5] Fail-closed quando não dá para verificar")

    class DBQuebrado:
        def table(self, _n):
            raise RuntimeError("banco fora do ar")

    svc = efeitos.WorkEffectService(DBQuebrado())
    fechou = False
    try:
        svc.buscar("c1", "k1")
    except efeitos.EffectNeedsReconciliation:
        fechou = True
    except Exception:  # noqa: BLE001
        pass

    checar(fechou, "não saber se o efeito já ocorreu impede executar",
           "fail-open aqui produziria envio duplicado durante instabilidade")


def main() -> int:
    print("=" * 66)
    print("SPEC-055 — GARANTIAS DO WORK OS")
    print("=" * 66)
    teste_chave_idempotencia()
    teste_fingerprint()
    teste_reserva_impede_repeticao()
    teste_crash_vira_unknown()
    teste_consulta_falha_e_fail_closed()

    print("\n" + "=" * 66)
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  X {f}")
        return 1
    print("TODAS AS GARANTIAS VERIFICADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
