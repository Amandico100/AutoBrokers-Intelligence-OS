"""SPEC-061 §9.3 — a trilha administrativa responde "por quê", sem vazar nada.

Por que este arquivo existe
---------------------------
Uma trilha de auditoria falha de dois jeitos, e os dois são silenciosos:

1. **guarda de menos** — registra "corretora suspensa" sem o motivo, e seis
   meses depois ninguém consegue responder à corretora por que foi suspensa;
2. **guarda demais** — copia o `before`/`after` de uma configuração de conexão
   e leva o segredo junto, criando um lugar novo onde a chave existe.

O segundo é pior, porque a trilha é justamente o lugar que ninguém apaga.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

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


carregar("app.services.control_plane.rbac")
A = carregar("app.services.control_plane.audit")


class FakeQ:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self._p = None

    def insert(self, linha):
        self._p = linha
        return self

    def select(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        if self._p is not None:
            self.banco.linhas.setdefault(self.tabela, []).append(dict(self._p))
            return types.SimpleNamespace(data=[self._p])
        return types.SimpleNamespace(data=self.banco.linhas.get(self.tabela, []))


class FakeDB:
    def __init__(self):
        self.linhas: dict[str, list[dict]] = {}
        self.client = self

    def table(self, nome):
        return FakeQ(self, nome)


def teste_segredo_nao_entra_na_trilha():
    print("\n[1] Segredo não vira linha de auditoria")
    antes = {"nome": "WhatsApp", "api_key": "tvly-abc123secreto", "limite": 10}
    depois = {"nome": "WhatsApp", "api_key": "tvly-xyz789novo", "limite": 20}

    d = A.diferenca(antes, depois)
    red_antes = A.redigir_objeto({k: v["de"] for k, v in d.items()})
    red_depois = A.redigir_objeto({k: v["para"] for k, v in d.items()})

    texto = f"{red_antes} {red_depois}"
    checar("abc123secreto" not in texto and "xyz789novo" not in texto,
           "o valor da chave não aparece em lado nenhum", texto)
    checar(red_antes.get("api_key") == "[redigido]",
           "e o campo é marcado como redigido, não apagado em silêncio")
    checar(red_antes.get("limite") == 10 and red_depois.get("limite") == 20,
           "mas o que mudou de verdade continua legível")
    checar("nome" not in d,
           "campo que não mudou nem entra — a mudança não some numa parede "
           "de campos idênticos")


def teste_segredo_dentro_de_texto_livre():
    print("\n[2] Motivo escrito por humano também é filtrado")
    motivo = ("girei a chave porque a antiga vazou: "
              "TAVILY_API_KEY=tvly-vazou123 estava no log")
    limpo = A.redigir_texto(motivo)
    checar("tvly-vazou123" not in limpo, "a chave colada no texto some", limpo)
    checar("[redigido]" in limpo, "e fica a marca de que havia algo ali")
    checar("porque a antiga vazou" in limpo,
           "o resto do motivo é preservado — é ele que explica a ação")


def teste_chaves_sensiveis_em_profundidade():
    print("\n[3] Segredo aninhado também não passa")
    objeto = {"conexao": {"config": {"password": "senha123",
                                     "host": "db.exemplo.com"}}}
    r = A.redigir_objeto(objeto)
    checar("senha123" not in str(r), "senha em terceiro nível é redigida", str(r))
    checar("db.exemplo.com" in str(r),
           "e o que não é segredo continua visível — host ajuda a diagnosticar")

    fundo = {"a": {"b": {"c": {"d": {"e": {"f": "muito fundo"}}}}}}
    checar("profundo demais" in str(A.redigir_objeto(fundo)),
           "objeto sem fim é cortado — auditoria ilegível não é lida")


def teste_acao_critica_exige_motivo():
    print("\n[4] Ação crítica sem motivo não entra")
    db = FakeDB()
    trilha = A.TrilhaAdministrativa(db)

    r = trilha.registrar(actor_user_id="u1", action_key="companies.suspend",
                         permission_key="companies.suspend",
                         target_type="company", result_status="succeeded")
    checar(not r.get("ok"), "recusada sem motivo", str(r.get("erro"))[:60])
    checar("motivo" in str(r.get("erro", "")).lower(),
           "e a frase explica o que falta, em português")
    checar(not db.linhas.get("admin_audit_events"),
           "nada foi gravado")

    r2 = trilha.registrar(actor_user_id="u1", action_key="companies.suspend",
                          permission_key="companies.suspend",
                          target_type="company", result_status="succeeded",
                          reason="corretora pediu suspensão por escrito no chamado 412")
    checar(r2.get("ok"), "com motivo, entra")
    linha = db.linhas["admin_audit_events"][0]
    checar(linha["risk_tier"] == "critical",
           "e o risco vem da permission, não de quem chamou",
           linha["risk_tier"])


def teste_risco_nao_e_informado_pelo_chamador():
    print("\n[5] Quem chama não escolhe o próprio risco")
    db = FakeDB()
    trilha = A.TrilhaAdministrativa(db)
    trilha.registrar(actor_user_id="u1", action_key="work_runs.read",
                     permission_key="work_runs.read", target_type="work_run",
                     result_status="succeeded")
    checar(db.linhas["admin_audit_events"][0]["risk_tier"] == "low",
           "leitura é baixo risco")

    trilha.registrar(actor_user_id="u1", action_key="connections.rotate",
                     permission_key="connections.rotate",
                     target_type="connection", result_status="succeeded",
                     reason="chave exposta em conversa, rotação preventiva")
    checar(db.linhas["admin_audit_events"][1]["risk_tier"] == "critical",
           "girar segredo é crítico — e por isso exigiu motivo")


def teste_falha_tambem_e_registrada():
    print("\n[6] A trilha responde 'o que foi TENTADO', não só o que deu certo")
    db = FakeDB()
    trilha = A.TrilhaAdministrativa(db)
    trilha.registrar(actor_user_id="u1", action_key="skills.publish",
                     permission_key="skills.publish", target_type="skill",
                     result_status="failed", result_code="validacao")
    linha = db.linhas["admin_audit_events"][0]
    checar(linha["result_status"] == "failed", "falha entra na trilha")
    checar(linha["result_code"] == "validacao", "com o código do que houve")


def teste_falha_de_auditoria_nao_derruba_a_acao():
    print("\n[7] Trilha indisponível não vira Admin indisponível")

    class DBQuebrado(FakeDB):
        def table(self, nome):
            raise RuntimeError("banco fora do ar")

    r = A.TrilhaAdministrativa(DBQuebrado()).registrar(
        actor_user_id="u1", action_key="work_runs.retry",
        permission_key="work_runs.retry", target_type="work_run",
        result_status="succeeded")
    checar(not r.get("ok"), "a falha é reportada")
    checar("registrar" in str(r.get("erro", "")).lower(),
           "com frase humana", str(r.get("erro")))


def teste_gateway_do_next_concorda_com_o_backend():
    print("\n[8] As duas listas de 'exige motivo' não divergem")
    caminho = os.path.join(os.path.dirname(RAIZ), "lib", "admin",
                           "control-plane", "command-gateway.ts")
    if not os.path.exists(caminho):
        checar(False, "command-gateway.ts existe", caminho)
        return
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()

    import re
    bloco = re.search(r"EXIGEM_MOTIVO\s*=\s*new Set\(\[(.*?)\]\)", fonte, re.S)
    checar(bloco is not None, "a lista existe no gateway do Next")
    if not bloco:
        return
    no_next = set(re.findall(r"'([^']+)'", bloco.group(1)))

    rbac = sys.modules["app.services.control_plane.rbac"]
    criticas = {p for p in rbac.PERMISSIONS if rbac.risco_de(p) == "critical"}

    checar(no_next == criticas,
           "o Next cobra motivo exatamente nas críticas do backend",
           f"só no Next: {sorted(no_next - criticas)} · "
           f"só no backend: {sorted(criticas - no_next)}")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 §9.3 — A TRILHA RESPONDE 'POR QUÊ' SEM VAZAR NADA")
    print("=" * 68)
    for teste in (
        teste_segredo_nao_entra_na_trilha,
        teste_segredo_dentro_de_texto_livre,
        teste_chaves_sensiveis_em_profundidade,
        teste_acao_critica_exige_motivo,
        teste_risco_nao_e_informado_pelo_chamador,
        teste_falha_tambem_e_registrada,
        teste_falha_de_auditoria_nao_derruba_a_acao,
        teste_gateway_do_next_concorda_com_o_backend,
    ):
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
    print("A TRILHA GUARDA O QUE PRECISA E NADA MAIS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
