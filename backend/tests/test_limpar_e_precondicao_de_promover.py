"""O mapa da URA só é promovido depois de limpo. Nessa ordem, e no código.

A HISTÓRIA
==========
📊 07/08/2026: `ura_maps` tinha 10 mapas `observed`, 279 `superseded`, 3
`retired` — e **ZERO `active`**.

A Sentinela de Rotas compara o menu de hoje com o menu ATIVO:

    active = await get_active_map(insurer_key, ramo)
    if not active or ...:
        return None          # ← sempre, porque não havia nenhum ativo

Três subsistemas morriam juntos, e todos foram medidos:
`route_drift` = 0 registros (nenhum alerta jamais foi gerado, **nem podia**),
`playbook_overlays` = 0 (o Alfaiate nunca rodou), e o aviso "a seguradora mudou
o menu" nunca chegou ao Founder.

O CONSERTO ÓBVIO ERA PROMOVER. ELE ESTAVA ERRADO.
=================================================
📊 115 nós carregam nome próprio de segurado (95 só na Porto) e 24 carregam
marca de corretora — a raiz do mapa `tokio` literalmente estampa o nome de uma
corretora, porque a URA da Tokio Marine é white-label.

O mapa é GLOBAL. Promovê-lo assim publicaria o nome de um cliente e a marca de
uma corretora dentro do conhecimento que as outras leem (CLAUDE.md §7).

Por isso limpar e promover moram na mesma função: **a ordem está no código, e
não na cabeça de quem clica.**
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _carregar():
    nome = "_teste_ura_map"
    if nome in sys.modules:
        return sys.modules[nome]
    for pai in ("app", "app.core", "app.services", "app.services.atlas"):
        if pai not in sys.modules:
            m = types.ModuleType(pai)
            m.__path__ = [os.path.join(RAIZ, "backend", *pai.split(".")[1:])]
            sys.modules[pai] = m
    # `templater` é carregado DE VERDADE: é ele que mascara, e um dublê
    # validaria a minha suposição em vez da regra real.
    real = "app.services.atlas.templater"
    if real not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            real, os.path.join(RAIZ, "backend/app/services/atlas/templater.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[real] = mod
        spec.loader.exec_module(mod)

    caminho = os.path.join(RAIZ, "backend", "app", "services", "ura_map_service.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _mapa(*textos: str) -> dict:
    return {"nodes": {f"n{i}": {"text": t, "opcoes": []}
                      for i, t in enumerate(textos)}}


# ---------------------------------------------------------------------------
def teste_o_mascarador_de_producao_limpa_os_nos_gravados():
    print("\n[1] Reaplica o mascarador de PRODUÇÃO nos nós já gravados")
    U = _carregar()

    mapa = _mapa(
        "Oi, sou assistente virtual da Porto Seguro\n\nJoao, estou aqui para ajudar",
        "Escolha uma opcao: 1 - Guincho 2 - Bateria",   # menu, não pode mudar
    )
    limpo, tocados = U._renomear_nos_sync(mapa)

    checar(tocados == 1, "mascarou exatamente o nó com nome", f"{tocados} nó(s)")
    checar("{NOME}" in limpo["nodes"]["n0"]["text"], "o nome virou {NOME}")
    checar(limpo["nodes"]["n1"]["text"] == mapa["nodes"]["n1"]["text"],
           "CONTROLE — o nó de MENU ficou intacto",
           "apagar o menu é perder o conhecimento que o mapa guarda")

    # CONTROLE — idempotente. Rodar de novo não muda nada, então pode viver no
    # agendador sem estragar o acervo a cada hora.
    _, de_novo = U._renomear_nos_sync(limpo)
    checar(de_novo == 0, "CONTROLE — rodar de novo não toca em nada",
           "é o que permite ligar no agendador sem medo")


def teste_marca_de_corretora_impede_a_promocao():
    print("\n[2] Marca de corretora BARRA a promoção")
    U = _carregar()

    # 📊 A raiz real do mapa `tokio`: a URA é white-label e ecoa a corretora.
    com_marca = _mapa("Ola, {NOME}  - Autofleet Seguros!\n\nDigite o CPF")
    limpo, _ = U._renomear_nos_sync(com_marca)
    checar(U._tem_marca_de_corretora(limpo) == 0,
           "a assinatura vira {NOME} - {CORRETORA} e a marca some",
           limpo["nodes"]["n0"]["text"].split("\n")[0])

    # CONTROLE — o detector CONSEGUE acusar. Um guarda que nunca acusa não
    # guarda nada, e este decide se um mapa entra no acervo global.
    cru = _mapa("Atendimento Resulta Seguros para o segurado")
    checar(U._tem_marca_de_corretora(cru) >= 1,
           "CONTROLE — marca que sobra É detectada",
           "senão a barreira da promoção seria decorativa")
    checar(U._tem_marca_de_corretora(_mapa("Digite 1 para guincho")) == 0,
           "CONTROLE — mapa sem marca não é acusado à toa")


def teste_limpar_vem_antes_de_promover():
    print("\n[3] A ordem está no CÓDIGO, não na cabeça de quem clica")
    U = _carregar()

    promovidos: list = []
    gravados: list = []

    class _Q:
        def __init__(self, banco, tabela):
            self.b, self.t, self.f, self.u = banco, tabela, [], None

        def select(self, *_a, **_k):
            return self

        def update(self, campos):
            self.u = dict(campos)
            return self

        def eq(self, c, v):
            self.f.append((c, v))
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            if self.u is not None:
                if self.u.get("status") == "active":
                    promovidos.append(dict(self.f))
                if "map" in self.u:
                    gravados.append(self.u["map"])
                return types.SimpleNamespace(data=[])
            linhas = [r for r in self.b.dados
                      if all(str(r.get(c)) == str(v) for c, v in self.f)]
            return types.SimpleNamespace(data=linhas)

    class Banco:
        def __init__(self, dados):
            self.dados, self.client = dados, self

        def table(self, nome):
            return _Q(self, nome)

    # Um mapa que fica limpo e um que continua com marca.
    banco = Banco([
        {"id": "m-porto", "insurer_key": "porto", "ramo": "todos", "status": "observed",
         "map": _mapa("Oi, sou assistente virtual da Porto\n\nJoao, estou aqui para ajudar")},
        {"id": "m-tokio", "insurer_key": "tokio", "ramo": "todos", "status": "observed",
         "map": _mapa("Bem-vindo a Autofleet Seguros, o seu atendimento")},
    ])
    U.get_supabase_client = lambda: banco
    sys.modules.setdefault("app.core.database", types.ModuleType("app.core.database"))
    sys.modules["app.core.database"].get_supabase_client = lambda: banco

    resultado = asyncio.run(U.higienizar_e_promover(aplicar=True))

    checar(resultado.get("ok") is True, "a higiene roda", str(resultado)[:80])
    checar(resultado["nos_mascarados"] >= 1,
           "mascarou o nó com nome antes de qualquer promoção",
           f"{resultado['nos_mascarados']} nó(s)")
    checar(len(resultado["barrados_por_marca"]) == 1,
           "o mapa com marca de corretora foi BARRADO",
           str(resultado["barrados_por_marca"]))
    checar(gravados, "e a versão limpa foi gravada no banco")

    # CONTROLE — sem `aplicar`, nada é escrito. É o que permite conferir antes.
    promovidos.clear()
    gravados.clear()
    seco = asyncio.run(U.higienizar_e_promover(aplicar=False))
    checar(not gravados and not promovidos,
           "CONTROLE — `aplicar=False` não escreve nada",
           f"lidos={seco.get('lidos')}, promovidos={seco.get('promovidos')}")


def teste_esta_no_agendador():
    print("\n[4] Roda sozinho — sem depender de alguém lembrar")
    caminho = os.path.join(RAIZ, "backend", "app", "tasks", "buffer_processor.py")
    with open(caminho, encoding="utf-8") as arquivo:
        fonte = arquivo.read()
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("higienizar_e_promover" in cmd and "ura_higiene_e_promocao" in cmd,
           "a higiene está registrada no agendador",
           "📊 os mapas ficaram 10 dias sem promoção esperando um clique")


def main() -> int:
    print("=" * 70)
    print("LIMPAR É PRÉ-CONDIÇÃO DE PROMOVER")
    print("=" * 70)
    teste_o_mascarador_de_producao_limpa_os_nos_gravados()
    teste_marca_de_corretora_impede_a_promocao()
    teste_limpar_vem_antes_de_promover()
    teste_esta_no_agendador()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o mapa entra no acervo global limpo, ou não entra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
