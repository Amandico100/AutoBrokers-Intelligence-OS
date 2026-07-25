"""SPEC-056 — garantias do Skill Registry e do Tool Gateway.

Roda offline com duplo do Supabase. O que se prova aqui é a **lógica de
decisão**: progressive disclosure, a capability como autoridade final, e
aprovação sempre pelo mais restritivo.

    python backend/tests/test_spec056_skill_registry_gateway.py
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FALHAS: list[str] = []


def _carregar(rel: str, nome: str):
    caminho = os.path.join(RAIZ, rel)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


registry = _carregar("app/services/skills/registry.py", "_t_registry")
gateway = _carregar("app/services/skills/gateway.py", "_t_gateway")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# --------------------------------------------------------------------------


class T:
    def __init__(self, dados, nome):
        self.dados, self.nome, self.f = dados, nome, {}
        self._in = None

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def in_(self, c, vs):
        self._in = (c, list(vs))
        return self

    def order(self, *_a, **_k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def execute(self):
        linhas = self.dados.get(self.nome, [])
        r = [x for x in linhas if all(x.get(k) == v for k, v in self.f.items())]
        if self._in:
            c, vs = self._in
            r = [x for x in r if x.get(c) in vs]
        if getattr(self, "_single", False):
            return type("R", (), {"data": r[0] if r else None})()
        return type("R", (), {"data": r})()


class DB:
    def __init__(self, dados):
        self.dados = dados

    def table(self, nome):
        return T(self.dados, nome)


def _base():
    return {
        "tool_definitions": [
            {"id": "t1", "tool_key": "knowledge.search", "name": "Base", "description": "d",
             "implementation_kind": "native", "capability_key": "knowledge.tenant.search",
             "risk_level": "low", "side_effect_class": "read",
             "requires_connection": False, "requires_approval": False, "is_active": True},
            {"id": "t2", "tool_key": "communication.whatsapp_send", "name": "WhatsApp", "description": "d",
             "implementation_kind": "adapter", "capability_key": "operational.whatsapp.send",
             "risk_level": "high", "side_effect_class": "communication",
             "requires_connection": True, "requires_approval": True, "is_active": True},
            {"id": "t3", "tool_key": "portal.execute", "name": "Portal", "description": "d",
             "implementation_kind": "portal", "capability_key": "tenant.portal.execute",
             "risk_level": "critical", "side_effect_class": "external_commitment",
             "requires_connection": True, "requires_approval": True, "is_active": True},
        ],
        "tool_releases": [
            {"id": "r1", "tool_id": "t1", "status": "published", "is_default": True, "input_schema": {}},
            {"id": "r2", "tool_id": "t2", "status": "published", "is_default": True, "input_schema": {}},
            {"id": "r3", "tool_id": "t3", "status": "published", "is_default": True, "input_schema": {}},
        ],
    }


class SkillFake:
    def __init__(self, tools, pack=None):
        self.skill_key = "s.test"
        self.release_id = "sr1"
        self.pack_key = pack
        self.tool_requirements = tools


# --------------------------------------------------------------------------


def teste_capability_e_autoridade():
    print("\n[1] A capability é a autoridade final")
    gw = gateway.ToolGateway(DB(_base()))
    skill = SkillFake([
        {"tool_key": "knowledge.search", "requirement": "required", "max_calls": 5},
        {"tool_key": "communication.whatsapp_send", "requirement": "required"},
    ])

    d = gw.selecionar(company_id="c1", agent_role="core", skill=skill,
                      active_capabilities={"knowledge.tenant.search": {"status": "active", "scope": {}}})

    checar("knowledge.search" in d.keys(), "tool com capability ativa é liberada")
    checar("communication.whatsapp_send" not in d.keys(),
           "tool sem capability ativa é NEGADA mesmo a Skill pedindo",
           "a Skill não pode conceder poder que o Registry nega")
    checar(any(x["tool_key"] == "communication.whatsapp_send" for x in d.denied),
           "negativa é registrada com motivo")


def teste_estados_nao_ativos_negam():
    print("\n[2] Estado não-ativo nega e explica")
    gw = gateway.ToolGateway(DB(_base()))
    skill = SkillFake([{"tool_key": "communication.whatsapp_send", "requirement": "required"}])

    for estado, esperado in [("needs_connection", "conectar"), ("disabled", "desligado"),
                             ("scope_missing", "configurado")]:
        d = gw.selecionar(company_id="c1", agent_role="core", skill=skill,
                          active_capabilities={"operational.whatsapp.send": {"status": estado, "scope": {}}})
        neg = d.denied[0] if d.denied else {}
        msg = (neg.get("mensagem_humana") or "").lower()
        checar(not d.granted and esperado in msg,
               f"estado '{estado}' nega com mensagem humana", msg[:60])


def teste_aprovacao_pelo_mais_restritivo():
    print("\n[3] Aprovação sempre pelo mais restritivo")
    gw = gateway.ToolGateway(DB(_base()))

    skill = SkillFake([{"tool_key": "knowledge.search", "requirement": "required"}])
    d = gw.selecionar(company_id="c1", agent_role="core", skill=skill,
                      active_capabilities={"knowledge.tenant.search":
                                           {"status": "active", "scope": {"requires_approval": True}}})
    checar(d.granted and d.granted[0].requires_approval,
           "scope da capability pode EXIGIR aprovação numa tool que não exigia")

    skill2 = SkillFake([{"tool_key": "knowledge.search", "requirement": "required",
                         "approval_override": "always"}])
    d2 = gw.selecionar(company_id="c1", agent_role="core", skill=skill2,
                       active_capabilities={"knowledge.tenant.search": {"status": "active", "scope": {}}})
    checar(d2.granted and d2.granted[0].requires_approval,
           "override da Skill pode EXIGIR aprovação (nunca remover)")


def teste_limite_pelo_menor():
    print("\n[4] Limite de chamadas pelo MENOR")
    gw = gateway.ToolGateway(DB(_base()))
    skill = SkillFake([{"tool_key": "knowledge.search", "requirement": "required", "max_calls": 10}])
    d = gw.selecionar(company_id="c1", agent_role="core", skill=skill,
                      active_capabilities={"knowledge.tenant.search":
                                           {"status": "active", "scope": {"max_calls_per_run": 3}}})
    checar(d.granted and d.granted[0].max_calls == 3,
           "Skill pede 10, escopo permite 3 → vale 3",
           f"obtido={d.granted[0].max_calls if d.granted else None}")


def teste_forbidden_e_respeitado():
    print("\n[5] Requisito 'forbidden'")
    gw = gateway.ToolGateway(DB(_base()))
    skill = SkillFake([{"tool_key": "knowledge.search", "requirement": "forbidden"}])
    d = gw.selecionar(company_id="c1", agent_role="core", skill=skill,
                      active_capabilities={"knowledge.tenant.search": {"status": "active", "scope": {}}})
    checar(not d.granted, "tool marcada como 'forbidden' não é sequer considerada")


def teste_teto_prioriza_menor_risco():
    print("\n[6] Teto de ferramentas prioriza menor risco")
    gw = gateway.ToolGateway(DB(_base()))
    skill = SkillFake([
        {"tool_key": "portal.execute", "requirement": "required"},
        {"tool_key": "communication.whatsapp_send", "requirement": "required"},
        {"tool_key": "knowledge.search", "requirement": "required"},
    ])
    d = gw.selecionar(
        company_id="c1", agent_role="core", skill=skill, max_tools=1,
        active_capabilities={
            "knowledge.tenant.search": {"status": "active", "scope": {}},
            "operational.whatsapp.send": {"status": "active", "scope": {}},
            "tenant.portal.execute": {"status": "active", "scope": {}},
        })
    checar(len(d.granted) == 1 and d.granted[0].tool_key == "knowledge.search",
           "com teto de 1, a leitura vence a ação de efeito externo",
           f"ficou={d.keys()}")


def teste_shortlist():
    print("\n[7] Progressive disclosure — shortlist por intenção")
    reg = registry.SkillRegistry(DB({}))
    cands = [
        registry.SkillCandidate("a", "Consultar Apólice", "consulta apolice", "insurance", "r1", "1.0.0",
                                triggers=["consultar apolice", "dados da apolice"]),
        registry.SkillCandidate("b", "Pesquisa com Fontes", "pesquisa web", "research", "r2", "1.0.0",
                                triggers=["pesquise", "noticia"]),
        registry.SkillCandidate("c", "Analisar Planilha", "csv", "analytics", "r3", "1.0.0",
                                triggers=["planilha", "csv"]),
    ]
    top = reg.shortlist(cands, "preciso consultar apolice do cliente", limite=2)
    checar(top[0].skill_key == "a", "gatilho correto vence", f"veio={top[0].skill_key}")
    checar(len(top) == 2, "shortlist respeita o limite")

    nenhum = reg.shortlist(cands, "bom dia tudo bem", limite=3)
    checar(all(c.confidence == 0 for c in nenhum),
           "conversa sem intenção de procedimento não força Skill",
           "forçar uma Skill onde não cabe piora a resposta")


def teste_content_hash():
    print("\n[8] Hash de conteúdo")
    a = registry.content_hash({"x": 1, "y": 2}, "instrucao")
    b = registry.content_hash({"y": 2, "x": 1}, "instrucao")
    c = registry.content_hash({"x": 1, "y": 3}, "instrucao")
    checar(a == b, "ordem das chaves não muda o hash")
    checar(a != c, "manifesto diferente gera hash diferente",
           "é o que obriga nova versão em vez de editar release publicada")


def main() -> int:
    print("=" * 68)
    print("SPEC-056 — SKILL REGISTRY E TOOL GATEWAY")
    print("=" * 68)
    teste_capability_e_autoridade()
    teste_estados_nao_ativos_negam()
    teste_aprovacao_pelo_mais_restritivo()
    teste_limite_pelo_menor()
    teste_forbidden_e_respeitado()
    teste_teto_prioriza_menor_risco()
    teste_shortlist()
    teste_content_hash()

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  X {f}")
        return 1
    print("TODAS AS GARANTIAS VERIFICADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
