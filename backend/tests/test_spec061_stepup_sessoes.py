"""SPEC-061 §7.3 e §7.4 — sessões e confirmação de identidade.

Duas perguntas que o Admin não sabia responder
----------------------------------------------
**"Quem está dentro agora?"** — não havia lista de sessões nem jeito de
encerrar a de alguém. Notebook perdido, pessoa que saiu da empresa, sessão
esquecida num computador emprestado: nada disso tinha resposta.

**"Você é você mesmo, agora?"** — suspender uma corretora exigia o mesmo que
abrir a tela de resumo: estar logado. Uma sessão aberta há oito horas num
computador destravado podia fazer as duas.
"""

from __future__ import annotations

import importlib.util
import os
import re
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


S = carregar("app.services.control_plane.sessoes")
AGORA = datetime.now(timezone.utc)


class FakeQ:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self._filtros: list[tuple] = []

    def select(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self._filtros.append((c, v))
        return self

    def upsert(self, linha, **_k):
        chave = (linha.get("admin_user_id"), linha.get("source_type"),
                 linha.get("source_id"))
        alvo = self.banco.linhas.setdefault(self.tabela, [])
        for i, l in enumerate(alvo):
            if (l.get("admin_user_id"), l.get("source_type"),
                    l.get("source_id")) == chave:
                alvo[i] = dict(linha)
                return self
        alvo.append(dict(linha))
        return self

    def execute(self):
        if self.tabela in self.banco.quebradas:
            raise RuntimeError("fora do ar")
        linhas = self.banco.linhas.get(self.tabela, [])
        for c, v in self._filtros:
            linhas = [l for l in linhas if str(l.get(c)) == str(v)]
        return types.SimpleNamespace(data=linhas)


class FakeDB:
    def __init__(self, quebradas=()):
        self.linhas: dict[str, list[dict]] = {}
        self.quebradas = set(quebradas)
        self.client = self

    def table(self, nome):
        return FakeQ(self, nome)


# SHA-256, o formato LEGADO que `lib/auth.ts` ainda aceita. Usado aqui de
# propósito: não depende de `bcrypt` instalado, e ao mesmo tempo prova que o
# caminho legado funciona — quem tem senha antiga consegue entrar E confirmar.
#
# O caminho bcrypt é coberto pelo caso [10], que confere o código-fonte.
def _hash(senha: str) -> str:
    import hashlib

    return hashlib.sha256(senha.encode()).hexdigest()


def teste_ip_nao_e_guardado_inteiro():
    print("\n[1] O IP completo não fica registrado")
    r = S._resumir_dispositivo(
        "Mozilla/5.0 (Windows NT 10.0) Chrome/120.0", "189.45.201.77")
    checar("189.45.201.77" not in r, "o IP inteiro some", r)
    checar("189.45" in r,
           "mas os dois primeiros octetos ficam — dizem provedor e região, "
           "e é o que faz alguém reconhecer 'esta não sou eu'", r)
    checar("Chrome" in r, "e o navegador aparece", r)

    checar("Edge" in S._resumir_dispositivo("Mozilla/5.0 Edg/120", None),
           "Edge não é confundido com Chrome — o UA dele contém 'chrome'")


def teste_revogar_exige_motivo():
    print("\n[2] Encerrar a sessão de alguém exige motivo escrito")
    db = FakeDB()
    s = S.SessoesAdministrativas(db)

    r = s.revogar_tudo(user_id="u1", motivo="x", revogado_por="admin")
    checar(not r.get("ok"), "motivo curto é recusado", str(r.get("erro"))[:60])

    r2 = s.revogar_tudo(user_id="u1", motivo="notebook perdido no aeroporto",
                        revogado_por="admin")
    checar(r2.get("ok"), "com motivo, aceito")
    checar("entrar de novo" in str(r2.get("mensagem", "")),
           "e a mensagem diz o que acontece com a pessoa")


def teste_revogacao_invalida_sessao_antiga():
    print("\n[3] Revogar é trocar a fechadura, não recolher a chave")
    db = FakeDB()
    s = S.SessoesAdministrativas(db)

    antiga = (AGORA - timedelta(hours=2)).isoformat()
    checar(s.sessao_ainda_vale(user_id="u1", emitida_em=antiga),
           "antes da revogação, a sessão vale")

    s.revogar_tudo(user_id="u1", motivo="pessoa saiu da empresa hoje",
                   revogado_por="admin")

    checar(not s.sessao_ainda_vale(user_id="u1", emitida_em=antiga),
           "depois, a sessão emitida ANTES do corte deixa de valer")

    nova = (AGORA + timedelta(minutes=5)).isoformat()
    checar(s.sessao_ainda_vale(user_id="u1", emitida_em=nova),
           "e uma sessão nova volta a valer — o corte é um instante, não um banimento")

    checar(s.sessao_ainda_vale(user_id="outra-pessoa", emitida_em=antiga),
           "a revogação atinge só quem foi revogado")


def teste_falha_de_leitura_nao_derruba_todo_mundo():
    print("\n[4] Erro de banco não expulsa quem estava dentro")
    db = FakeDB(quebradas={"admin_inbox_states"})
    s = S.SessoesAdministrativas(db)
    checar(s.sessao_ainda_vale(user_id="u1", emitida_em=AGORA.isoformat()),
           "leitura que falhou NÃO é prova de revogação — derrubar todo mundo "
           "por erro de banco troca um risco por outro maior")


def teste_step_up_valida_a_senha_real():
    print("\n[5] A confirmação usa a senha do login, não um segredo novo")
    db = FakeDB()
    db.linhas["admin_users"] = [
        {"id": "u1", "password_hash": _hash("senha-correta")}]
    c = S.ConfirmacaoDeIdentidade(db)

    checar(not c.confirmar(user_id="u1", senha="").get("ok"),
           "senha vazia é recusada")
    checar(not c.confirmar(user_id="u1", senha="chute").get("ok"),
           "senha errada é recusada")

    r = c.confirmar(user_id="u1", senha="senha-correta")
    checar(r.get("ok"), "senha certa confirma", str(r.get("erro")))
    checar(r.get("vale_por_minutos") == S.JANELA_DE_STEP_UP_MINUTOS,
           "e diz por quanto tempo vale")


def teste_step_up_nao_vaza_existencia_de_conta():
    print("\n[6] A mensagem de erro não conta quem existe")
    db = FakeDB()
    db.linhas["admin_users"] = [{"id": "u1", "password_hash": _hash("boa")}]
    c = S.ConfirmacaoDeIdentidade(db)

    erro_senha = str(c.confirmar(user_id="u1", senha="ruim").get("erro"))
    erro_inexistente = str(c.confirmar(user_id="nao-existe", senha="x").get("erro"))
    checar("não encontrado" not in erro_inexistente.lower()
           and "inexistente" not in erro_inexistente.lower(),
           "usuário inexistente não é revelado", erro_inexistente)
    checar(bool(erro_senha) and bool(erro_inexistente),
           "os dois casos devolvem erro")


def teste_janela_expira():
    print("\n[7] A confirmação vence sozinha")
    db = FakeDB()
    db.linhas["admin_users"] = [{"id": "u1", "password_hash": _hash("boa")}]
    c = S.ConfirmacaoDeIdentidade(db)

    checar(not c.confirmado_recentemente(user_id="u1"),
           "sem confirmar, não vale")

    c.confirmar(user_id="u1", senha="boa")
    checar(c.confirmado_recentemente(user_id="u1"), "logo depois, vale")

    # Vence a janela na marra, como o tempo faria.
    for l in db.linhas["admin_inbox_states"]:
        if l.get("source_type") == "step_up":
            l["snoozed_until"] = (AGORA - timedelta(minutes=1)).isoformat()
    checar(not c.confirmado_recentemente(user_id="u1"),
           "passada a janela, deixa de valer")

    checar(S.JANELA_DE_STEP_UP_MINUTOS <= 30,
           "a janela é curta — longa demais vira teatro",
           str(S.JANELA_DE_STEP_UP_MINUTOS))


def teste_step_up_falha_fechada():
    print("\n[8] Sem conseguir provar a confirmação, ela não vale")
    db = FakeDB(quebradas={"admin_inbox_states"})
    db.linhas["admin_users"] = [{"id": "u1", "password_hash": _hash("boa")}]
    c = S.ConfirmacaoDeIdentidade(db)
    checar(not c.confirmado_recentemente(user_id="u1"),
           "erro de leitura NEGA — o custo aqui é pedir a senha de novo, "
           "e o contrário é ação irreversível sem confirmação")


def teste_bcrypt_continua_sendo_o_caminho_principal():
    print("\n[10] bcrypt continua sendo o caminho principal")
    caminho = os.path.join(RAIZ, "app", "services", "control_plane", "sessoes.py")
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    checar("bcrypt.checkpw" in fonte, "bcrypt é usado para hash $2a$/$2b$")
    checar("startswith(\"$2\")" in fonte,
           "e o formato é escolhido pelo prefixo, não por tentativa")
    checar("compare_digest" in fonte,
           "o caminho legado compara em tempo constante — `==` vazaria, pelo "
           "tempo, o quanto do hash bateu")

    req = os.path.join(RAIZ, "requirements.txt")
    if os.path.exists(req):
        with open(req, encoding="utf-8") as fh:
            checar("bcrypt" in fh.read(),
                   "e bcrypt está declarado nas dependências — sem isso o "
                   "step-up falharia SÓ em produção")


def teste_gateway_exige_step_up_nas_criticas():
    print("\n[9] O Gateway pede a senha antes do que não se desfaz")
    caminho = os.path.join(os.path.dirname(RAIZ), "lib", "admin",
                           "control-plane", "command-gateway.ts")
    if not os.path.exists(caminho):
        checar(False, "command-gateway.ts existe", caminho)
        return
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()

    checar("identidadeConfirmada" in fonte, "o Gateway consulta a confirmação")
    checar("step_up_required" in fonte, "e devolve um código próprio")
    checar("428" in fonte,
           "com 428 (Precondition Required) — não é 403 'você não pode' "
           "nem 400 'pedido errado', é 'falta um passo antes'")
    # Fail-closed sem backend.
    checar(re.search(r"if\s*\(!b\)\s*return false", fonte) is not None,
           "sem serviço de controle, a confirmação NÃO é presumida")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 §7.3 e §7.4 — SESSÕES E CONFIRMAÇÃO DE IDENTIDADE")
    print("=" * 68)
    for teste in (teste_ip_nao_e_guardado_inteiro,
                  teste_revogar_exige_motivo,
                  teste_revogacao_invalida_sessao_antiga,
                  teste_falha_de_leitura_nao_derruba_todo_mundo,
                  teste_step_up_valida_a_senha_real,
                  teste_step_up_nao_vaza_existencia_de_conta,
                  teste_janela_expira,
                  teste_step_up_falha_fechada,
                  teste_bcrypt_continua_sendo_o_caminho_principal,
                  teste_gateway_exige_step_up_nas_criticas):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} GARANTIA(S) QUEBRADA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("SESSÃO SE ENCERRA E IDENTIDADE SE CONFIRMA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
