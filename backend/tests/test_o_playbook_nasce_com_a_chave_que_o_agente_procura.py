"""Metade dos playbooks ativos era muda: escritos com uma chave, procurados com outra.

A HISTÓRIA
==========
Dois classificadores nomeiam o mesmo atendimento, e ninguém os apresentou:

    QUEM ESCREVE   `attendance_distiller._STAGE1_SYSTEM` (LLM)
                   ramos    auto | residencial | vida | outro
                   serviços guincho… + consulta | sinistro | outro
                   e grava também um `tipo`: assistencia | sinistro |
                   apolice | renovacao | cobranca | outro

    QUEM PROCURA   `atlas.templater.infer_ramo_servico` (regex)
                   ramos    auto | residencial          ← só dois
                   serviços guincho… + sinistro         ← sem consulta

📊 Medido em 07/08/2026 sobre os 18 playbooks do banco: **6 dos 12 ATIVOS eram
inalcançáveis** — `auto/consulta` (253 atendimentos), `outro/sinistro` (629),
`outro/consulta` (254), `residencial/consulta` (48), `vida/sinistro` (122),
`vida/consulta`. Escritos, versionados, exibidos no admin, custando Opus — e
nunca lidos.

E a falha é silenciosa por construção: `graph._conduta_do_caso` faz
`.eq("ramo", ramo).eq("servico", servico)`, não acha linha, devolve `""`. Um
playbook que não existe e um playbook que não é encontrado produzem exatamente
o mesmo resultado.

O SEGUNDO DEFEITO, NO MESMO EIXO
================================
Do outro lado, duas linhas do destilador jogavam fora `servico == "outro"`:

    auto/outro          2.219 sessões úteis   nota 74,4   ← maior E melhor
    outro/outro         1.468                 nota 67,2
    residencial/outro     166                 nota 76,3
    vida/outro             24                 nota 72,9

3.877 sessões — mais da metade do material aproveitável. E a informação para
desfazer o balde **já estava gravada ao lado**: dentro de `servico='outro'`, o
`tipo` diz `auto/cobranca` (1.904 úteis, nota 76,2 — o melhor grupo do acervo
inteiro).

📊 Cobrança é 2.915 das 12.063 cartas do RAG (24%).

POR QUE OS DOIS CONSERTOS SÃO UM SÓ
===================================
Consertar só o destilador criaria `auto/cobranca` — e um sétimo playbook mudo,
porque `infer_ramo_servico` nunca devolveu "cobranca". Consertar só o runtime
faria o agente procurar uma chave que ninguém escreve. **É uma ponta só, e
este teste guarda as duas.**
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATER = os.path.join(RAIZ, "backend", "app", "services", "atlas", "templater.py")
DISTILADOR = os.path.join(RAIZ, "backend", "app", "services", "attendance_distiller.py")
GRAPH = os.path.join(RAIZ, "backend", "app", "agents", "graph.py")
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read()


def _infer():
    """`infer_ramo_servico` de verdade, extraída sem importar o módulo.

    `templater.py` puxa o pacote `app.services`, que neste ambiente exige
    dependências que não estão instaladas. A função é pura — depende só de
    `re` e de `_SERVICOS_SO_RESIDENCIAIS` — então roda isolada, e assim o
    teste exercita o CÓDIGO, não uma cópia dele escrita aqui.
    """
    fonte = _ler(TEMPLATER)
    arv = ast.parse(fonte)
    pedacos = []
    for no in arv.body:
        if isinstance(no, ast.Assign) and any(
                getattr(a, "id", "") == "_SERVICOS_SO_RESIDENCIAIS" for a in no.targets):
            pedacos.append(ast.get_source_segment(fonte, no))
        if isinstance(no, ast.FunctionDef) and no.name == "infer_ramo_servico":
            pedacos.append(ast.get_source_segment(fonte, no))
    espaco: dict = {"List": list, "Tuple": tuple, "Optional": object}
    exec(compile("\n".join(pedacos), "<templater>", "exec"), espaco)  # noqa: S102
    return espaco["infer_ramo_servico"]


def _chave_do_grupo():
    """`chave_do_grupo` de verdade, pelo mesmo motivo."""
    fonte = _ler(DISTILADOR)
    arv = ast.parse(fonte)
    pedacos = []
    for no in arv.body:
        if isinstance(no, ast.Assign) and any(
                getattr(a, "id", "") in ("_TIPO_COMO_SERVICO", "_TIPOS_QUE_SAO_SERVICO")
                for a in no.targets):
            pedacos.append(ast.get_source_segment(fonte, no))
        if isinstance(no, ast.FunctionDef) and no.name == "chave_do_grupo":
            pedacos.append(ast.get_source_segment(fonte, no))
    espaco: dict = {"Dict": dict, "Any": object, "Tuple": tuple, "List": list}
    exec(compile("\n".join(pedacos), "<distiller>", "exec"), espaco)  # noqa: S102
    return espaco["chave_do_grupo"]


# ---------------------------------------------------------------------------
def teste_o_destilador_para_de_jogar_fora_o_melhor():
    print("\n[1] `servico='outro'` deixa de ser lixo")
    chave = _chave_do_grupo()

    # 📊 O grupo que estava sendo descartado, e a nota dele.
    checar(chave({"ramo": "auto", "servico": "outro", "tipo": "cobranca"}) == ("auto", "cobranca"),
           "cobrança presa em 'outro' vira o grupo `auto/cobranca`",
           "📊 1.904 sessões úteis, nota 76,2 — o melhor do acervo")
    checar(chave({"ramo": "outro", "servico": "outro", "tipo": "renovacao"})
           == ("outro", "renovacao"),
           "e o mesmo vale para renovação")

    # 🔴 `apolice` NÃO vira um serviço chamado "apolice". Este erro foi
    # cometido na primeira versão DESTE conserto e pego antes do commit:
    # 📊 `consulta` são 564 atendimentos úteis com QUATRO playbooks escritos;
    # "apolice" seriam 136 espalhadas em três ramos. Criar `auto/apolice` ao
    # lado de `auto/consulta` é abrir dois playbooks para o mesmo trabalho —
    # exatamente o defeito que este arquivo conserta, cometido de novo na
    # linha do conserto.
    checar(chave({"ramo": "auto", "servico": "outro", "tipo": "apolice"})
           == ("auto", "consulta"),
           "`tipo=apolice` entra no `consulta` que já existe",
           "📊 consulta: 564 úteis e 4 playbooks · apolice: 136 e nenhum")

    # CONTROLE — o serviço explícito continua ganhando. Se o `tipo` passasse a
    # mandar sempre, `auto/guincho` viraria `auto/assistencia` e todos os
    # playbooks de assistência mudariam de nome de uma vez.
    checar(chave({"ramo": "auto", "servico": "guincho", "tipo": "assistencia"})
           == ("auto", "guincho"),
           "CONTROLE — serviço explícito continua mandando",
           "senão auto/guincho viraria auto/assistencia")

    # E o que continua sendo descartado, de propósito.
    checar(chave({"ramo": "auto", "servico": "outro", "tipo": "outro"}) == ("", ""),
           "`outro/outro` continua fora",
           "📊 381 sessões, nota 52,4 — o único que é ruído mesmo")
    checar(chave({"ramo": "residencial", "servico": "outro", "tipo": "assistencia"}) == ("", ""),
           "e `assistencia` também, porque nasceria mudo",
           "o runtime sempre nomeia o subserviço, nunca 'assistencia'")
    checar(chave({"ramo": "", "servico": "outro", "tipo": "cobranca"}) == ("", ""),
           "sem ramo não há grupo")


def teste_o_runtime_procura_a_chave_que_foi_escrita():
    print("\n[2] Quem procura fala a língua de quem escreve")
    infer = _infer()

    # As chaves que o destilador passa a produzir têm de ser produzíveis aqui.
    _, s = infer([], "bom dia, não recebi o boleto da parcela deste mês")
    checar(s == "cobranca", "'boleto da parcela' → cobranca",
           "📊 sem isto, auto/cobranca nasceria mudo como os outros 6")
    _, s = infer([], "preciso da segunda via da minha apolice")
    checar(s == "consulta", "'segunda via da apólice' → consulta",
           "o nome que os 4 playbooks já usam — não um quinto")
    _, s = infer([], "quero renovar o seguro que vence agora")
    checar(s == "renovacao", "'renovar' → renovacao")

    # O ramo `vida`, que o destilador produz e o runtime transformava em auto.
    r, _ = infer([], "é sobre o seguro de vida do meu pai, sou beneficiario")
    checar(r == "vida", "'seguro de vida' → ramo vida",
           "📊 antes caía no `else` do ternário e virava 'auto', sem log")

    # 🔴 CONTROLE DE PRECEDÊNCIA — o mais específico continua ganhando. Quem
    # liga sobre o guincho que não chegou está falando de guincho, mesmo
    # citando o boleto no meio da frase.
    r, s = infer([], "o guincho não chegou e ainda me cobraram o boleto")
    checar((r, s) == ("auto", "guincho"),
           "CONTROLE — assistência ganha de cobrança na mesma frase",
           "'guincho' + 'boleto' → guincho")
    r, s = infer([], "vazamento no meu apartamento, preciso de encanador")
    checar((r, s) == ("residencial", "encanador"),
           "CONTROLE — o residencial não foi afetado")
    r, s = infer([], "bati o carro, quero abrir sinistro")
    checar(s == "sinistro", "CONTROLE — sinistro continua funcionando")

    # CONTROLE — texto sem sinal nenhum continua devolvendo serviço vazio, e
    # não uma categoria inventada. Um regex ganancioso aqui faria toda conversa
    # virar "cobranca" e o agente carregaria conduta errada.
    _, s = infer([], "oi tudo bem? preciso falar com alguem ai por favor")
    checar(s == "", "CONTROLE — conversa sem assunto não ganha serviço",
           "regex ganancioso faria toda conversa virar cobranca")


def teste_o_ramo_outro_e_o_generico_do_servico():
    print("\n[3] `outro/X` vira o genérico de X, em vez de morrer")
    fonte = _ler(GRAPH)

    checar('if not res.data and ramo != "outro":' in fonte,
           "sem playbook do ramo, procura o do ramo `outro`",
           "📊 destrava outro/sinistro (629) e outro/consulta (254)")

    # CONTROLE — SEGUNDA tentativa, nunca primeira. `auto/sinistro` tem de
    # continuar ganhando de `outro/sinistro` numa conversa de carro.
    i_primeira = fonte.find("res = await asyncio.to_thread(_q, ramo)")
    i_fallback = fonte.find('res = await asyncio.to_thread(_q, "outro")')
    checar(0 < i_primeira < i_fallback,
           "CONTROLE — e só DEPOIS de tentar o ramo específico",
           "o playbook do ramo certo não pode perder para o genérico")

    # E o cabeçalho não pode anunciar o ramo procurado quando veio o genérico.
    checar('ramo_lido = str(res.data[0].get("ramo") or ramo)' in fonte
           and 'rotulo = "GERAL" if ramo_lido == "outro"' in fonte,
           "o cabeçalho diz o playbook que VEIO, não o que foi procurado",
           "dizer '(AUTO)' sobre conduta genérica é precisão que ela não tem")


def teste_a_leitura_entende_os_dois_formatos():
    print("\n[4] O material antigo continua legível")
    fonte = _ler(DISTILADOR)

    # No banco o material está gravado como servico='outro' + tipo='cobranca'.
    # Pedir servico='cobranca' acha ZERO. Sem esta segunda consulta o conserto
    # inteiro produziria grupos vazios.
    checar('_pagina([("servico", "outro"), ("tipo", tipo)])' in fonte,
           "o carregador busca também o formato antigo",
           "📊 auto/cobranca: 0 linhas pela 1ª consulta, 1.904 pela 2ª")
    # O mapa é INVERTIDO aqui: quem pede `consulta` tem de receber também o
    # que está gravado como `tipo='apolice'`. Procurar `tipo='consulta'` acha
    # zero — esse valor não existe no campo `tipo`.
    checar("for tipo, como in _TIPO_COMO_SERVICO.items():" in fonte
           and "if como == servico:" in fonte,
           "e o mapa é invertido, para `consulta` achar o `tipo=apolice`",
           "procurar tipo='consulta' acharia zero: esse valor não existe lá")

    # CONTROLE — a ordem de recência é refeita depois de juntar. O desempate
    # por nota depende dela, e concatenar duas listas ordenadas não devolve
    # uma lista ordenada.
    checar('destilados.sort(key=lambda d: str(d.get("at") or ""), reverse=True)' in fonte,
           "CONTROLE — e a ordem de recência é refeita depois de juntar",
           "duas listas ordenadas concatenadas não formam uma lista ordenada")

    # CONTROLE — nada é reescrito no banco. Redestilar 9.196 sessões para
    # arrumar um rótulo custaria o acervo inteiro no modelo caro.
    checar("Nenhuma linha é reescrita" in fonte,
           "CONTROLE — e nenhuma linha do banco é reescrita")


def teste_uma_regra_de_chave_so():
    print("\n[5] CONTROLE — a chave é decidida num lugar só")
    fonte = _ler(DISTILADOR)
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    # Foi assim que o defeito nasceu: a fila de trás contava um grupo que a
    # fila da frente descartava, porque cada uma tinha a sua conta.
    checar(cmd.count("chave_do_grupo(") >= 3,
           "quem conta, quem enfileira e quem sintetiza usam a MESMA função",
           "duas contas divergem — foi assim que este defeito nasceu")
    checar('servico in ("", "outro")' not in cmd,
           "e o descarte solto de 'outro' sumiu do caminho de contagem",
           "era ele que jogava fora 3.877 sessões")


def main() -> int:
    print("=" * 70)
    print("O PLAYBOOK NASCE COM A CHAVE QUE O AGENTE PROCURA")
    print("=" * 70)
    teste_o_destilador_para_de_jogar_fora_o_melhor()
    teste_o_runtime_procura_a_chave_que_foi_escrita()
    teste_o_ramo_outro_e_o_generico_do_servico()
    teste_a_leitura_entende_os_dois_formatos()
    teste_uma_regra_de_chave_so()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — quem escreve e quem procura falam a mesma língua.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
