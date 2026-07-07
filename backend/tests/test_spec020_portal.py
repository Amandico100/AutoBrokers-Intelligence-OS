"""SPEC-020 P1 - Portal worker: logica pura (interpretador de login, gate, vault).

Rodar: python backend/tests/test_spec020_portal.py
Nao roda Playwright aqui (isso e journey contra fixture no CI do worker); testa a
DECISAO pura (interpret_login) + o gate + o round-trip do cofre (se cryptography).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


from portal_worker.journeys.vidros_lanternas import interpret_login, interpret_atendimento, match_option
from portal_worker.worker import portal_real_enabled
from portal_worker.journeys import get_journey
from portal_worker.adaptive import parse_action, is_confirm_screen


def run():
    print("== SPEC-020 P1 - Portal worker (logica pura) ==\n")

    # interpret_login: sucesso, falha, captcha->humano, desconhecido->humano
    ok = interpret_login("Bem-vindo! Meus Pedidos | Sair", "https://portal/painel")
    check("login sucesso -> done", ok.status == "done")
    check("login sucesso captura logged_in", ok.captured.get("logged_in") is True)

    bad = interpret_login("Erro: senha invalida. Tente novamente.")
    check("senha invalida -> failed", bad.status == "failed")

    cap = interpret_login("Por favor complete o CAPTCHA para continuar")
    check("captcha -> needs_human", cap.status == "needs_human")

    unk = interpret_login("Alguma tela estranha sem sinais conhecidos")
    check("tela desconhecida -> needs_human", unk.status == "needs_human")

    # interpret_atendimento (vidros publico): protocolo, erro, passo1, desconhecido
    proto = interpret_atendimento("https://x/#/allianz/passo5", "Protocolo 123456 gerado com sucesso")
    check("protocolo -> done", proto.status == "done")
    err = interpret_atendimento("https://x/#/allianz/passo1", "CPF nao encontrado na base")
    check("nao encontrado -> failed", err.status == "failed")
    p1 = interpret_atendimento("https://x/#/allianz/passo1", "Informe o CPF e a placa")
    check("passo1 -> needs_human", p1.status == "needs_human" and p1.captured.get("stage") == "passo1")

    # match_option (cerebro decide, journey casa a opcao do dropdown)
    pecas = ["VIDRO PARABRISA", "VIDRO DE PORTA", "VIDRO DE JANELA", "VIDRO VIGIA (TRASEIRO)"]
    check("match acento-insensivel", match_option("vidro de porta", pecas) == "VIDRO DE PORTA")
    check("match por palavras (parabrisa)", match_option("parabrisa", pecas) == "VIDRO PARABRISA")
    rel = ["O proprio", "Conjuge", "Filho", "Corretor", "Outros"]
    check("match relacao corretor", match_option("Corretor", rel) == "Corretor")
    check("sem match -> None", match_option("teto solar", pecas) is None)
    check("lista vazia -> None", match_option("x", []) is None)

    # Camada 2 (LLM-visao) — parse_action valida a decisao da LLM; is_confirm_screen para no 80%
    check("parse fill valido", parse_action({"action": "fill", "target": "cpf", "value": "1"})["action"] == "fill")
    check("parse acao invalida -> ask_human", parse_action({"action": "hack"})["action"] == "ask_human")
    check("parse nao-dict -> ask_human", parse_action("x")["action"] == "ask_human")
    check("confirm screen 80% detectada", is_confirm_screen({"heading": "Confirme a peca danificada", "text": ""}) is True)
    check("tela normal nao e confirm", is_confirm_screen({"heading": "Nos conte o que aconteceu", "text": "placa"}) is False)

    # registry resolve as journeys de vidros
    check("get_journey login_check", callable(get_journey("vidros_lanternas", "login_check")))
    check("get_journey abrir_atendimento", callable(get_journey("vidros_lanternas", "abrir_atendimento")))
    check("get_journey desconhecida -> None", get_journey("x", "y") is None)

    # gate PORTAL_REAL_ENABLED: default OFF; liga so com valores truthy
    os.environ.pop("PORTAL_REAL_ENABLED", None)
    check("gate default OFF", portal_real_enabled() is False)
    os.environ["PORTAL_REAL_ENABLED"] = "true"
    check("gate ON com 'true'", portal_real_enabled() is True)
    os.environ["PORTAL_REAL_ENABLED"] = "0"
    check("gate OFF com '0'", portal_real_enabled() is False)
    os.environ.pop("PORTAL_REAL_ENABLED", None)

    # _set_select: fallback JS quando o Playwright recusa o select_option
    # (Angular Material <select display:none> — causa do loop no acionamento real).
    import asyncio
    from portal_worker.adaptive import _set_select

    class _FakeSel:
        def __init__(self, opt_raises, eval_ret):
            self.opt_raises, self.eval_ret, self.eval_calls = opt_raises, eval_ret, 0

        async def select_option(self, **kw):
            if self.opt_raises:
                raise Exception("element is not visible")

        async def evaluate(self, js, *args):
            self.eval_calls += 1
            return self.eval_ret

    s1 = _FakeSel(opt_raises=False, eval_ret=None)
    check("_set_select caminho normal -> label", asyncio.run(_set_select(None, s1, "Comercial")) == "Comercial")
    s2 = _FakeSel(opt_raises=True, eval_ret=True)
    check("_set_select display:none -> fallback JS aplica", asyncio.run(_set_select(None, s2, "Comercial")) == "Comercial")
    check("_set_select fallback foi usado", s2.eval_calls == 1)
    s3 = _FakeSel(opt_raises=True, eval_ret=False)
    check("_set_select sem opcao casavel -> vazio", asyncio.run(_set_select(None, s3, "Comercial")) == "")

    # md-select (AngularJS Material): apply_action deve clicar o <md-option> certo
    # (setar o <select> nativo NAO atualiza o ng-model — causa real do loop).
    from portal_worker.adaptive import _apply_mdselect

    class _Opt:
        clicked = None
        def __init__(self, text, vis=True):
            self._t, self._v = text, vis
        async def is_visible(self):
            return self._v
        async def inner_text(self):
            return self._t
        async def click(self, **kw):
            _Opt.clicked = self._t

    class _Md:
        def __init__(self, name):
            self._name = name
        async def get_attribute(self, k):
            return self._name if k == "name" else ""
        async def scroll_into_view_if_needed(self, **kw):
            pass
        async def click(self, **kw):
            pass

    class _Kbd:
        async def press(self, k):
            pass

    def _n(t):
        import unicodedata
        return " ".join(unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower().split())

    class _Page:
        def __init__(self, mds, opts):
            self._mds, self._opts, self.keyboard = mds, opts, _Kbd()
        async def query_selector_all(self, sel):
            if "md-select" in sel:
                return self._mds
            if "md-option" in sel:
                return self._opts
            return []
        async def wait_for_timeout(self, ms):
            pass
        async def evaluate(self, js, *args):
            if "hit.click()" not in js:      # dump de diagnostico
                return []
            want = _n(args[0] if args else "")
            vis = [o for o in self._opts if o._v]
            real = [o for o in vis if "selecione" not in _n(o._t)]
            hit = None
            if want:
                for o in real:
                    t = _n(o._t)
                    if t == want or want in t or t in want:
                        hit = o; break
            if hit is None and real:
                hit = real[0]
            if hit is None:
                return {"ok": False, "n": len(vis)}
            await hit.click()
            return {"ok": True, "text": hit._t[:30]}

    _Opt.clicked = None
    p1 = _Page([_Md("TipoTelefoneSolicitante0")],
               [_Opt("Selecione uma opção"), _Opt("Comercial"), _Opt("Residencial")])
    r = asyncio.run(_apply_mdselect(p1, "TipoTelefoneSolicitante0", "Comercial"))
    check("md-select clica md-option por texto", r == "mdselect=comercial" and _Opt.clicked == "Comercial")

    _Opt.clicked = None
    p2 = _Page([_Md("segr")], [_Opt("Selecione uma opção"), _Opt("O próprio"), _Opt("Corretor")])
    r2 = asyncio.run(_apply_mdselect(p2, "segr", "Corretor"))
    check("md-select casa 'Corretor'", r2 == "mdselect=corretor" and _Opt.clicked == "Corretor")

    _Opt.clicked = None
    p3 = _Page([_Md("segr")], [_Opt("Selecione uma opção"), _Opt("O próprio")])
    r3 = asyncio.run(_apply_mdselect(p3, "segr", "valor-que-nao-existe"))
    check("md-select sem match -> 1a opcao real", r3 == "mdselect=o proprio" and _Opt.clicked == "O próprio")

    r4 = asyncio.run(_apply_mdselect(_Page([], []), "campo", "x"))
    check("sem md-select -> None (cai no nativo)", r4 is None)

    # vault round-trip (so se cryptography instalado localmente)
    try:
        from cryptography.fernet import Fernet
        from portal_worker import vault

        os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()
        token = vault.encrypt("senha-secreta-123")
        check("vault cifra != claro", token != "senha-secreta-123")
        check("vault round-trip", vault.decrypt(token) == "senha-secreta-123")
    except ImportError:
        print("  [skip] cryptography ausente localmente (vault testado no worker)")

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
