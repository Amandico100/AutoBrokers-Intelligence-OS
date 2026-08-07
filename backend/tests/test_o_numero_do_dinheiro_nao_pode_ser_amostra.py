"""O número que vira dinheiro tem de ser o total — nunca uma amostra silenciosa.

A HISTÓRIA
==========
O PostgREST devolve no máximo **1.000 linhas por resposta** e ignora o
`.limit(N)` pedido acima disso. Não há erro nem aviso: o código recebe 1.000 e
não tem como distinguir "só existem 1.000" de "existem 5.000 e você viu um
quinto".

📊 06/08/2026, medido no projeto de produção `dcajcvlzcjbmyapmklil`:

    onde                                   no banco   chegava   o que estragava
    ─────────────────────────────────────────────────────────────────────────
    token_usage_logs 30 d (Resulta)         4.648      1.000    consumo do CLIENTE
    usage_events 30 d (todas)               4.406      1.000    relatório de custo
    token_usage_logs por cobrar             5.646      1.000    débito de créditos
    usage_events do mês (Resulta)           4.267      1.000    alerta de orçamento
    attendance_sessions 30 d                1.577      1.000    memória do agente

O PIOR DELES NÃO ERA O LIMITE — ERA O DETECTOR
==============================================
`unit_economics` tentou se proteger. Lia com `.limit(TETO)`, `TETO = 5000`, e
concluía "truncou?" com `len(linhas) >= TETO`. Como chegam 1.000, a conta era
sempre `1000 >= 5000` → **False**, e o relatório declarava ATIVAMENTE que tinha
lido tudo. O aviso escrito no próprio arquivo ("O custo real do período é MAIOR
que o mostrado") nunca teve como aparecer.

Um detector de truncamento cujo limiar está acima do teto do servidor é pior que
nenhum detector: o primeiro deixaria alguém desconfiado; este dava certeza
errada.

E O ALERTA DE ORÇAMENTO SE CALAVA ONDE MAIS IMPORTAVA
=====================================================
Quanto MAIS a corretora consome, mais eventos ela tem, e mais a soma truncada
subestima o gasto. O aviso que existe para avisar antes do estouro ficava calado
justamente no maior cliente. O contrário exato do que ele existe para fazer.

O QUE ESTE ARQUIVO GUARDA
=========================
Que essas cinco leituras leem o ACERVO INTEIRO, que a paginação é estável, e que
quando ela para no teto **quem chamou fica sabendo** — porque um teto que avisa
não é o mesmo defeito com outro nome.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []

# 📊 Quantas linhas o PostgREST entrega por resposta, doa a quem doer o
# `.limit()` pedido. Medido em 06/08/2026 pelo número redondo que apareceu no
# chat da AutoFleet: 1.570 linhas na janela, exatamente 1.000 no chat.
TETO_DO_SERVIDOR = 1000


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _carregar_leitura():
    """Carrega `app.leitura_completa` sem arrastar `app.services`.

    O módulo é puro (só o laço de paginação), então carrega direto do arquivo.
    Importar pelo pacote traria a cadeia inteira e o `openai` junto.
    """
    nome = "_teste_leitura_completa"
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, "backend", "app", "leitura_completa.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# --------------------------------------------------------------------------
# Um PostgREST de mentira que MENTE DO MESMO JEITO que o de verdade.
#
# 🔴 O ponto inteiro deste dublê é o corte em 1.000. Um dublê que obedece o
# `.limit()` ao pé da letra não tem como reproduzir esta classe de bug: no teste
# viriam 5.000 e em produção vêm 1.000, e o teste ficaria verde sobre um defeito
# vivo. Foi exatamente assim que o backfill do espelho passou verde enquanto
# perdia 570 mensagens.
# --------------------------------------------------------------------------
class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros: list = []
        self._ordem: list = []
        self._faixa = None
        self._limite = None

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros.append(("eq", campo, valor))
        return self

    def gte(self, campo, valor):
        self.filtros.append(("gte", campo, valor))
        return self

    def lte(self, campo, valor):
        self.filtros.append(("lte", campo, valor))
        return self

    def order(self, campo, desc=False, **_k):
        self._ordem.append((campo, bool(desc)))
        return self

    def limit(self, n):
        self._limite = n
        return self

    def range(self, inicio, fim):
        self._faixa = (int(inicio), int(fim))
        return self

    def _casa(self, linha) -> bool:
        for tipo, campo, valor in self.filtros:
            atual = linha.get(campo)
            if tipo == "eq" and str(atual) != str(valor):
                return False
            if tipo == "gte" and str(atual or "") < str(valor):
                return False
            if tipo == "lte" and str(atual or "") > str(valor):
                return False
        return True

    def execute(self):
        self.banco.idas += 1
        linhas = [l for l in self.banco.dados.get(self.tabela, []) if self._casa(l)]
        for campo, desc in reversed(self._ordem):
            linhas = sorted(linhas, key=lambda l: str(l.get(campo) or ""), reverse=desc)
        # 🔴 O SERVIDOR NÃO PROMETE ORDEM ENTRE LINHAS EMPATADAS.
        #
        # O `sorted` do Python é estável e devolveria os empatados sempre na
        # mesma ordem — o que faria uma paginação por data (que empata) parecer
        # segura no teste e perder linha em produção. Foi assim que uma
        # paginação por `created_at` perdeu 12 cartas e repetiu 12 em 11.640.
        #
        # Aqui os empatados rodam de posição a cada ida ao banco. Determinístico
        # (nada de sorteio), mas suficiente para que só uma chave ÚNICA
        # sobreviva à paginação — que é a verdade do servidor real.
        if self._ordem:
            campo = self._ordem[0][0]
            grupos: dict = {}
            for linha in linhas:
                grupos.setdefault(str(linha.get(campo) or ""), []).append(linha)
            baralhadas = []
            for chave in sorted(grupos, reverse=self._ordem[0][1]):
                grupo = grupos[chave]
                giro = self.banco.idas % len(grupo) if len(grupo) > 1 else 0
                baralhadas.extend(grupo[giro:] + grupo[:giro])
            linhas = baralhadas
        if self._faixa:
            inicio, fim = self._faixa
            linhas = linhas[inicio:fim + 1]
        if self._limite:
            linhas = linhas[: self._limite]
        return types.SimpleNamespace(data=linhas[:TETO_DO_SERVIDOR])


class BancoFalso:
    def __init__(self, dados=None):
        self.dados = dados or {}
        self.client = self
        self.idas = 0

    def table(self, nome):
        return _Consulta(self, nome)


def _linhas(tabela_prefixo: str, quantas: int, **campos) -> list:
    saida = []
    for i in range(quantas):
        linha = {"id": f"{tabela_prefixo}-{i:06d}"}
        for chave, valor in campos.items():
            linha[chave] = valor(i) if callable(valor) else valor
        saida.append(linha)
    return saida


# --------------------------------------------------------------------------
def teste_a_leitura_atravessa_o_teto_do_servidor():
    print("\n[1] A leitura passa das mil linhas — que é onde o servidor para")
    L = _carregar_leitura()

    # 📊 4.648 é o número real do consumo de 30 dias da Resulta.
    banco = BancoFalso({"token_usage_logs": _linhas(
        "t", 4648, company_id="resulta", total_cost_usd=0.002056)})

    linhas, incompleto = L.ler_paginado(
        lambda: banco.client.table("token_usage_logs").select("*").eq("company_id", "resulta"),
        chave_unica="id", rotulo="teste")

    checar(len(linhas) == 4648, "leu as 4.648 linhas do acervo",
           f"leu {len(linhas)} — o servidor corta em {TETO_DO_SERVIDOR}")
    checar(incompleto is False, "e diz que a leitura está COMPLETA")
    soma = round(sum(float(l["total_cost_usd"]) for l in linhas), 4)
    checar(abs(soma - 9.5563) < 0.01, "e a soma bate com o total, não com a amostra",
           f"US$ {soma:.4f} — a amostra de 1.000 daria US$ 2,06")

    # CONTROLE — o dublê CONSEGUE cortar em 1.000. Sem esta linha eu teria
    # "provado" o conserto contra um servidor que nunca recusa nada.
    de_uma_vez = banco.client.table("token_usage_logs").select("*").limit(5000).execute().data
    checar(len(de_uma_vez) == TETO_DO_SERVIDOR,
           f"CONTROLE — uma leitura sem paginar ainda para em {TETO_DO_SERVIDOR}",
           f"pediu 5.000, recebeu {len(de_uma_vez)} — é o teto que o conserto vence")


def teste_o_teto_que_avisa_nao_e_o_mesmo_defeito():
    print("\n[2] Quando a leitura para no teto, quem chamou FICA SABENDO")
    L = _carregar_leitura()

    banco = BancoFalso({"usage_events": _linhas("e", 7000, company_id="x")})
    linhas, incompleto = L.ler_paginado(
        lambda: banco.client.table("usage_events").select("*").eq("company_id", "x"),
        chave_unica="id", teto=5000, rotulo="teste")

    checar(incompleto is True,
           "parou no teto de 5.000 sobre 7.000 e AVISOU",
           "era exatamente este aviso que nunca disparava")
    checar(len(linhas) >= 5000, "e devolveu o que já tinha lido",
           f"{len(linhas)} linhas — o que veio não se joga fora")

    # CONTROLE — o aviso tem de conseguir ser False. Um sinalizador que é sempre
    # True não informa nada; seria o defeito antigo espelhado.
    pequeno = BancoFalso({"usage_events": _linhas("e", 30, company_id="x")})
    _, tranquilo = L.ler_paginado(
        lambda: pequeno.client.table("usage_events").select("*").eq("company_id", "x"),
        chave_unica="id", teto=5000, rotulo="teste")
    checar(tranquilo is False,
           "CONTROLE — 30 linhas dentro do teto: NÃO avisa",
           "aviso que sempre dispara é aviso que se aprende a ignorar")

    # 🔴 O DEFEITO ORIGINAL, reproduzido para nunca mais voltar.
    #
    # A conta antiga era `len(recebidas) >= TETO` com TETO=5000. Como o servidor
    # devolve 1.000, ela dava False mesmo com 7.000 linhas no banco: o relatório
    # dizia "li tudo" sobre um sétimo do mês.
    recebidas_antes = TETO_DO_SERVIDOR
    checar((recebidas_antes >= 5000) is False,
           "CONTROLE — a conta ANTIGA daria 'não truncou' com 7.000 no banco",
           "1000 >= 5000 é False; era assim que o relatório afirmava estar completo")


def teste_a_paginacao_nao_perde_nem_repete_com_datas_empatadas():
    print("\n[3] Datas empatam — e paginar por data perde linha")
    L = _carregar_leitura()

    # 📊 O caso real que este repositório já documenta em `curadoria_cartas.py`:
    # paginar por `created_at` perdeu 12 linhas e repetiu 12 em 11.640.
    # Aqui TODAS as 3.000 linhas têm o MESMO instante — o pior caso possível.
    banco = BancoFalso({"usage_events": _linhas(
        "e", 3000, company_id="x", occurred_at="2026-08-06T12:00:00+00:00")})

    linhas, _ = L.ler_paginado(
        lambda: banco.client.table("usage_events").select("*").eq("company_id", "x"),
        chave_unica="id", rotulo="teste")

    ids = [l["id"] for l in linhas]
    checar(len(ids) == 3000, "leu as 3.000", str(len(ids)))
    checar(len(set(ids)) == 3000, "sem repetir nenhuma",
           f"{len(ids) - len(set(ids))} repetida(s)")
    checar(len(set(ids)) == len(set(l["id"] for l in banco.dados["usage_events"])),
           "e sem perder nenhuma",
           "é o que a chave única garante e a data não garantiria")


def teste_o_dinheiro_e_a_memoria_usam_a_leitura_completa():
    print("\n[4] Os cinco lugares que importam usam a peça — e não uma cópia")
    alvos = [
        ("backend/app/api/billing.py",
         "consumo que o CLIENTE vê, com multiplicador de venda"),
        ("backend/app/workers/billing_tasks.py",
         "débito de créditos"),
        ("backend/app/services/control_plane/unit_economics.py",
         "relatório de custo por corretora"),
        ("backend/app/services/intelligence/detectors/conexoes.py",
         "alerta de orçamento"),
        ("backend/app/services/agent_memory.py",
         "o que o agente lembra"),
    ]
    for caminho, o_que in alvos:
        with open(os.path.join(RAIZ, caminho), encoding="utf-8") as arquivo:
            fonte = arquivo.read()
        cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
        checar("ler_paginado" in cmd, f"{o_que} lê o acervo inteiro",
               os.path.basename(caminho))

    # CONTROLE — a peça é UMA. Cinco cópias do mesmo laço seria cinco lugares
    # para o próximo defeito morar (CLAUDE.md §5: consolidar, não duplicar).
    with open(os.path.join(RAIZ, "backend/app/leitura_completa.py"),
              encoding="utf-8") as arquivo:
        peca = arquivo.read()
    checar("TAMANHO_DA_PAGINA = 1000" in peca,
           "CONTROLE — a página tem o tamanho exato do teto do servidor",
           "é o que torna 'página curta = acabou' verdadeiro")
    checar("chave_unica" in peca and "chave_unica: str," in peca,
           "CONTROLE — a chave única é obrigatória, sem padrão adivinhado",
           "paginar por data que empata perde linha, e já perdeu 12 em 11.640")


def teste_nenhuma_das_protecoes_legitimas_foi_removida():
    print("\n[5] O que protegia o CUSTO continua protegendo")
    # Estes limites não são descuido: são teto de token e de trabalho por ciclo.
    # Liberar qualquer um deles aumenta a conta de IA — que é o oposto do que
    # este trabalho existe para fazer.
    protecoes = [
        ("backend/app/agents/tools/human_handoff.py", "_MSGS_NO_DOSSIE",
         "mensagens do dossiê que vai para um humano"),
        ("backend/app/services/memory_fabric.py", "MAX_MENSAGENS_POR_SESSAO",
         "mensagens que entram no prompt de resumo"),
        ("backend/app/api/auxiliaries.py", "DEFAULT_MAX_MESSAGES",
         "mensagens que o Auxiliar manda a LLM resumir"),
    ]
    for caminho, constante, o_que in protecoes:
        with open(os.path.join(RAIZ, caminho), encoding="utf-8") as arquivo:
            fonte = arquivo.read()
        checar(constante in fonte, f"teto de token intacto: {o_que}", constante)

    # E o destilador continua cortando o transcript antes da LLM.
    with open(os.path.join(RAIZ, "backend/app/services/attendance_distiller.py"),
              encoding="utf-8") as arquivo:
        distiller = arquivo.read()
    checar(".limit(400)" in distiller or "limit(400)" in distiller,
           "e o destilador ainda corta o transcript em 400 linhas",
           "📊 só 13 das 12.968 sessões passam disso — o teto quase nunca morde")


def main() -> int:
    print("=" * 70)
    print("O NÚMERO DO DINHEIRO NÃO PODE SER UMA AMOSTRA")
    print("=" * 70)
    teste_a_leitura_atravessa_o_teto_do_servidor()
    teste_o_teto_que_avisa_nao_e_o_mesmo_defeito()
    teste_a_paginacao_nao_perde_nem_repete_com_datas_empatadas()
    teste_o_dinheiro_e_a_memoria_usam_a_leitura_completa()
    teste_nenhuma_das_protecoes_legitimas_foi_removida()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o número que vira dinheiro é o total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
