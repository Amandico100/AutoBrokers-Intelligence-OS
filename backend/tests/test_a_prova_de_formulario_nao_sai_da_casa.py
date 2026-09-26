# -*- coding: utf-8 -*-
"""A prova de formulário não sai de casa — SPEC-092, BLOCO F.2.

📊 **O que a rota `POST /api/whatsapp-integrations/prova-de-formulario` faz:**
manda, de um número nosso para outro, exatamente o tipo de mensagem que o
telefone de uma pessoa produz ao preencher um formulário. **Manda de verdade —
não é dry-run.** Foi assim que a prova de 03/08/2026 foi feita.

🔴 **E ela não passa por freio nenhum.** Não consulta `dispatch_live_enabled()`,
não consulta o freio de emergência. Só a chave interna.

📊 Até este bloco, o único motivo de ela ser segura era **a docstring dizer que
o destino é nosso**.

> **Uma premissa de segurança que existe só na docstring não é uma trava: é uma
> esperança.** Quem passasse o número de uma seguradora mandaria uma resposta de
> formulário para ela, fora de qualquer acionamento, sem freio e sem registro.

## O que este arquivo guarda

> **Destino que não é nosso: 400, e nenhuma mensagem sai.**

⚠️ E a metade que mais importa é a **positiva**: uma recusa que recusasse tudo
passaria em metade destes testes e deixaria a corretora sem diagnóstico nenhum.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ROTA_PY = RAIZ / "app" / "api" / "whatsapp_integrations.py"


def _carregar():
    """Só as funções puras/assíncronas de F.2 — sem subir o FastAPI inteiro.

    ⚠️ Importar o módulo de verdade puxa `app.core.database` e o resto da app;
    o `gate.yml` não roda `pip install`, e guarda que não roda não guarda.
    Então o que se carrega aqui é o TRECHO, compilado isolado.
    """
    fonte = ROTA_PY.read_text(encoding="utf-8")
    ini = fonte.index("_TETO_DE_NUMEROS_NOSSOS = 500")
    fim = fonte.index('@router.post("/prova-de-formulario")')
    modulo = types.ModuleType("_spec092_f2")
    modulo.__dict__["Any"] = object
    modulo.__dict__["AsyncSupabaseClient"] = object

    class _Log:
        def error(self, *a, **k):
            pass

        warning = info = error

    modulo.__dict__["logger"] = _Log()
    exec(compile(fonte[ini:fim], "<f2>", "exec"), modulo.__dict__)
    return modulo


F = _carregar()


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco):
        self.b = banco
        self._limite = None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, n):
        self._limite = int(n)
        return self

    async def execute(self):
        if self.b.explode:
            raise RuntimeError("banco fora do ar")
        linhas = [{"paired_phone_e164": n} for n in self.b.numeros]
        return _Resposta(linhas[: self._limite] if self._limite else linhas)

    # ⚠️ Este dublê ACEITA qualquer filtro de proposito: o assunto deste
    # arquivo e' a semantica da recusa. Quem prova que o filtro de corretora
    # existe de verdade e' `test_o_FILTRO_de_tenant_e_MESMO_aplicado`, com um
    # dublê que REGISTRA os `.eq()` — porque um que so' devolve `self` nao
    # consegue ficar vermelho quando o filtro sai.


class BancoFalso:
    def __init__(self, numeros, explode=False):
        self.numeros = list(numeros)
        self.explode = explode

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self)


#: A corretora deste arquivo. O ISOLAMENTO entre corretoras e' medido em
#: `test_o_painel_achou_e_nao_volta`, com um dublê que REGISTRA os filtros;
#: aqui o assunto e' a semantica da recusa.
EMPRESA = "empresa-de-teste"


def _e_nosso(destino, numeros, explode=False):
    """🔴 ASSINATURA MIGRADA no painel, e a mudança e' o conserto.

    Era `_destino_e_nosso(db, destino) -> bool`. O painel mediu que a lista de
    permissão era **global** — uma corretora alcançava o aparelho pareado de
    outra — e que a trava **comparava normalizado e enviava o cru**.

    Agora e' `(db, company_id, destino) -> (permitido, numero_gravado)`.
    """
    permitido, _ = asyncio.run(
        F._destino_e_nosso(BancoFalso(numeros, explode), EMPRESA, destino))
    return permitido


#: 💭 Números sintéticos. Nenhum telefone real entra num arquivo de teste.
NOSSO = "5511900000001"
OUTRO_NOSSO = "5547900000002"
SEGURADORA = "5511300034000"


# ---------------------------------------------------------------------------
# 1. A RECUSA
# ---------------------------------------------------------------------------

def test_destino_que_NAO_e_nosso_e_RECUSADO():
    assert _e_nosso(SEGURADORA, [NOSSO, OUTRO_NOSSO]) is False, (
        "🔴 o número de uma seguradora passou pela lista de permissão — esta "
        "rota manda de verdade e sem freio")


def test_CONTROLE_destino_NOSSO_e_LIBERADO():
    """🔴 A metade positiva, e é a que mais importa.

    Uma recusa que recusasse tudo passaria no teste acima e deixaria toda
    corretora sem o diagnóstico do próprio canal — que é a razão de esta rota
    existir como diagnóstico permanente.
    """
    assert _e_nosso(NOSSO, [NOSSO, OUTRO_NOSSO]) is True, (
        "o número da própria plataforma foi recusado — a prova deixou de "
        "poder ser feita por quem quer que seja")


@pytest.mark.parametrize("grafia", ["5547900000002", "47900000002",
                                    "4790000-0002", "+55 47 90000-0002"])
def test_o_MESMO_aparelho_em_QUALQUER_grafia_e_nosso(grafia):
    """`55 47 9000-0002` e `47 90000-0002` são o mesmo aparelho.

    ⚠️ Uma lista de permissão que erre por grafia recusa o próprio dono — e
    quem for desbloqueado depois vai afrouxá-la, não corrigi-la.
    """
    assert _e_nosso(grafia, [OUTRO_NOSSO]) is True, (
        f"a grafia {grafia!r} não foi reconhecida como nossa")


def test_numeros_DIFERENTES_nao_colidem():
    """🔴 REFORÇADO no painel: a chave era `DDD + 8 finais` e COLIDIA.

    📊 `47 9 3333-4444` (móvel) e `47 3333-4444` (FIXO) davam a mesma chave —
    e numa lista de PERMISSÃO que autoriza envio real sem freio, colisão é
    autorização indevida.

    §9.3 — e a chave de comparação tem de conseguir dizer NÃO: se ela
    colapsasse números distintos, todos os testes de liberação acima passariam
    e a trava não travaria nada.
    """
    assert F._chave_de_telefone("5547933334444") != F._chave_de_telefone("554733334444")
    assert F._chave_de_telefone(NOSSO) != F._chave_de_telefone(OUTRO_NOSSO)
    assert F._chave_de_telefone(SEGURADORA) != F._chave_de_telefone(NOSSO)
    assert _e_nosso(OUTRO_NOSSO, [NOSSO]) is False


# ---------------------------------------------------------------------------
# 2. FALHA FECHADO — os três caminhos
# ---------------------------------------------------------------------------

def test_banco_fora_do_ar_RECUSA():
    """Não conseguir PROVAR que é nosso não é permissão para enviar."""
    assert _e_nosso(NOSSO, [NOSSO], explode=True) is False


def test_varredura_no_TETO_recusa():
    """🔴 Truncar não é provar.

    Acima do teto, a lista devolvida é um pedaço arbitrário: o número certo
    pode estar fora dela, e o errado dentro. As duas respostas seriam a mesma.
    É a mesma lição do `_destino_e_compartilhado` da SPEC-085.
    """
    muitos = ["55119%08d" % i for i in range(F._TETO_DE_NUMEROS_NOSSOS + 10)]
    assert _e_nosso(muitos[0], muitos) is False, (
        "a varredura bateu no teto e mesmo assim liberou")


def test_destino_vazio_ou_sem_digito_RECUSA():
    for ruim in ("", "   ", "abc", None):
        assert _e_nosso(ruim, [NOSSO]) is False, f"{ruim!r} passou"


def test_integracao_sem_numero_pareado_nao_vira_curinga():
    """Uma linha com `paired_phone_e164` vazio não pode casar com um destino
    vazio — senão a lista de permissão libera o nada."""
    assert _e_nosso("", ["", None, NOSSO]) is False


# ---------------------------------------------------------------------------
# 3. A ROTA DIZ QUE RECUSOU, E QUE NADA SAIU
# ---------------------------------------------------------------------------

def test_a_rota_CHAMA_a_trava_antes_de_qualquer_envio():
    """Análise estática — a ordem importa: conferir depois de mandar não é
    conferir.

    ⚠️ **A âncora deste teste MIGROU, e o fato mudou com ela** (CLAUDE.md §9.3):
    a rota montava o corpo com `montar_nfm_reply` e o achatava à mão. Na SPEC-118
    passou a usar `corpo_do_flow_reply`, que é o montador do envio REAL. A lição
    é a mesma — a trava antes da montagem —, só a função mudou de nome. Manter a
    âncora vencida faria este teste estourar com `ValueError` de `str.index`, que
    não é vermelho de produto: é vermelho de teste desatualizado.
    """
    fonte = ROTA_PY.read_text(encoding="utf-8")
    i_trava = fonte.index("await _destino_e_nosso(db, company_id, para)")
    i_envio = fonte.index("corpo_do_flow_reply")
    assert i_trava < i_envio, (
        "a trava do destino roda DEPOIS da montagem/envio — nessa ordem ela "
        "não protege nada")


def test_a_recusa_DIZ_que_nada_foi_enviado():
    """🔴 Quem lê um 400 precisa saber se a mensagem saiu. *"Recusado"* sem essa
    frase deixa a corretora sem saber se ligou para a seguradora ou não."""
    fonte = ROTA_PY.read_text(encoding="utf-8")
    assert "aparelho desta corretora" in fonte, (
        "a recusa parou de dizer que o destino tem de ser DESTA corretora")
    assert "Nenhuma mensagem foi enviada." in fonte, (
        "a mensagem de recusa parou de dizer que nada saiu")


# ---------------------------------------------------------------------------
# 4. 🔴 A PROVA MEDE O CAMINHO DA PRODUÇÃO — SPEC-118, fatia F1b
# ---------------------------------------------------------------------------
# Esta rota existe para responder UMA pergunta: *"este canal consegue responder
# formulário?"*. Uma prova que bata num caminho que a produção não usa responde
# outra pergunta — e responde com a autoridade de um HTTP 200.
#
# 📊 **O defeito era SILENCIOSO, e é por isso que ele precisa de guarda.** Até
# 26/09/2026 a rota montava `url = f"{base_url}/send/interactiveResponse"` fixo,
# ignorando `rota_de_flow_reply()`. Os dois valores COINCIDEM hoje: a prova
# passava, o produto funcionava, e nada acusava. No dia em que alguém escrever
# `EVOLUTION_GO_FLOW_REPLY_PATH` para corrigir o caminho — que é exatamente o
# papel que a variável tem hoje — a prova continuaria dizendo "tudo bem" sobre a
# rota antiga.
#
# É a CLAUDE.md §9.4 na letra: *um padrão medido com um motor e aplicado com
# outro é um padrão sobre outra coisa.* ⚠️ O alvo aqui é a FORMA da declaração —
# qual função a rota chama —, que é o caso coberto pela exceção da §9.4: o
# comportamento do motor (`rota_de_flow_reply`, `corpo_do_flow_reply`) é medido
# em `test_o_transporte_do_formulario_e_conferido.py`, com o motor real.


def _funcao_da_prova():
    """Só a função `prova_de_formulario`, isolada do resto do arquivo."""
    arvore = ast.parse(ROTA_PY.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.AsyncFunctionDef, ast.FunctionDef)) and \
                no.name == "prova_de_formulario":
            return no
    raise AssertionError(
        "a função `prova_de_formulario` desapareceu de whatsapp_integrations.py "
        "— sem ela não existe prova de canal nenhuma")


def test_a_prova_pega_a_rota_NA_MESMA_FUNCAO_que_o_envio_real():
    """🔴 A `url` sai de `rota_de_flow_reply()`, nunca de uma string escrita aqui.

    ⚠️ Este teste fica VERMELHO se alguém voltar a escrever o caminho à mão —
    inclusive escrevendo o caminho CERTO, que é o que torna o defeito invisível.
    """
    funcao = _funcao_da_prova()

    chama_a_funcao = [
        no for no in ast.walk(funcao)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
        and no.func.id == "rota_de_flow_reply"
    ]
    assert chama_a_funcao, (
        "🔴 a prova parou de chamar `rota_de_flow_reply()`. Ela é a única coisa "
        "que sabe qual caminho o ENVIO REAL usa — sem ela a prova mede um "
        "caminho e a produção usa outro, e os dois coincidirem HOJE é o que "
        "deixa o defeito silencioso (CLAUDE.md §9.4)")

    atribuicoes = [
        no for no in ast.walk(funcao)
        if isinstance(no, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "url" for t in no.targets)
    ]
    assert len(atribuicoes) == 1, (
        f"a prova tem {len(atribuicoes)} atribuições de `url`; com mais de uma "
        "não se sabe qual vai ao fio")

    valor = atribuicoes[0].value
    assert isinstance(valor, ast.JoinedStr), (
        "🔴 `url` deixou de ser montada por interpolação. Se ela virou uma "
        "constante, a prova voltou a fixar o caminho por conta própria")
    nomes = {n.id for n in ast.walk(valor) if isinstance(n, ast.Name)}
    assert "rota" in nomes, (
        f"🔴 a `url` da prova não usa mais a variável `rota` (usa {sorted(nomes)}). "
        "O caminho voltou a ser escrito à mão nesta rota")
    literais = [
        n.value for n in ast.walk(valor)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.strip()
    ]
    assert not literais, (
        f"🔴 a `url` da prova carrega pedaço de caminho escrito à mão: {literais}. "
        "Mesmo o caminho CERTO escrito aqui é o defeito — ele para de acompanhar "
        "`EVOLUTION_GO_FLOW_REPLY_PATH` e a prova passa a medir outra rota")


def test_nenhum_caminho_de_envio_de_formulario_escrito_A_MAO_na_prova():
    """🔴 O caminho provado NÃO se repete aqui, nem como constante.

    📊 `/send/interactiveResponse` é o valor de `ROTA_DE_FLOW_REPLY_PROVADA` em
    `evolution_go.py` — 📊 26/09/2026, HTTP 200, ID 3EB02C9B1BFC57E46E3136. Duas
    cópias do mesmo caminho em dois arquivos divergem no dia em que uma das duas
    mudar, e a que fica para trás é sempre a do diagnóstico.

    ⚠️ Comentário não conta: explicar em prosa qual era o caminho antigo é
    exatamente o que este arquivo manda fazer. O que não pode é CÓDIGO.
    """
    fonte = ROTA_PY.read_text(encoding="utf-8")
    codigo = [
        ln for ln in fonte.splitlines()
        if not ln.lstrip().startswith("#") and "/send/interactiveResponse" in ln
    ]
    assert not codigo, (
        "🔴 o caminho do formulário voltou a ser escrito dentro de "
        f"whatsapp_integrations.py: {codigo}. Quem decide o caminho é "
        "`evolution_go.rota_de_flow_reply()`, e uma segunda cópia aqui é a "
        "divergência esperando o dia dela")


def test_o_corpo_da_prova_vem_do_MONTADOR_DE_PRODUCAO():
    """🔴 Um montador, não dois.

    A rota remontava `{number, name, paramsJSON, ...}` à mão, ao lado de
    `corpo_do_flow_reply`, que é quem monta no envio real. Dois montadores do
    mesmo corpo divergem — e a divergência aparece numa seguradora descartando a
    resposta em silêncio, com a prova dizendo 200 (CLAUDE.md §5).
    """
    funcao = _funcao_da_prova()
    chamadas = {
        no.func.id for no in ast.walk(funcao)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
    }
    assert "corpo_do_flow_reply" in chamadas, (
        "🔴 a prova parou de montar o corpo com `corpo_do_flow_reply` — o "
        "montador que o envio real usa. Remontar aqui é ter dois montadores")

    # E o embrulho NÃO é acrescentado à mão: ele vem do montador, sempre, e a
    # prova só o REMOVE na linha de controle. Se ele voltar a ser escrito aqui,
    # o montador pode perdê-lo sem que nada fique vermelho.
    fonte = ROTA_PY.read_text(encoding="utf-8")
    assert 'corpo["wrapInDocumentWithCaption"] = True' not in fonte, (
        "🔴 o embrulho voltou a ser acrescentado à mão na prova. 📊 Ele é a "
        "diferença entre 200 e 479 (03/08 e 26/09/2026): se a prova o põe por "
        "conta própria, ela passa mesmo que o envio real o tenha perdido")
    assert 'corpo.pop("wrapInDocumentWithCaption", None)' in fonte, (
        "a linha de CONTROLE sem embrulho desapareceu — sem ela o 200 da "
        "tentativa seguinte não prova que o embrulho é a causa (CLAUDE.md §9.2)")


def test_rota_DESLIGADA_recusa_em_vez_de_bater_na_raiz_do_servico():
    """🔴 `off` é recusa, não caminho vazio.

    `rota_de_flow_reply()` devolve `""` quando alguém desliga o envio pela
    `EVOLUTION_GO_FLOW_REPLY_PATH`. Sem guarda, `f"{base_url}{rota}"` viraria o
    `base_url` puro e a prova bateria na raiz do serviço — medindo qualquer coisa
    menos o que se quis medir, e provavelmente devolvendo um 404 que seria lido
    como *"a rota não existe mais"*.
    """
    fonte = ROTA_PY.read_text(encoding="utf-8")
    i_guarda = fonte.index("if not rota:")
    i_url = fonte.index('url = f"{base_url}{rota}"')
    assert i_guarda < i_url, (
        "a recusa de rota desligada vem DEPOIS de montar a url — nessa ordem "
        "ela não protege nada")
    assert "rota_desligada_por_configuracao" in fonte, (
        "a prova parou de DIZER que o motivo foi configuração. Um 'falhou' sem "
        "motivo manda a corretora procurar defeito onde não tem")


def test_o_404_da_prova_NAO_promete_versao_de_imagem():
    """🔴 A verdade vencida que custou um pedido de rebuild à toa (CLAUDE.md §9.3).

    📊 O texto anterior dizia *"a imagem precisa ser 0.7.2-autobrokers.2 ou mais
    nova"*. Em 26/09/2026 a rota respondeu **HTTP 200** na imagem que estava no ar
    (`vencedora: "embrulho DocumentWithCaption"`, ID 3EB02C9B1BFC57E46E3136) — ou
    seja, a explicação estava FALSA e era inalcançável. Quem a leu pediu
    autorização para reconstruir a imagem sem necessidade.
    """
    fonte = ROTA_PY.read_text(encoding="utf-8")
    i_404 = fonte.index("if r.status_code == 404:")
    j_404 = fonte.index("devolvido = r.json()", i_404)
    trecho = fonte[i_404:j_404]

    assert "0.7.2-autobrokers" not in trecho, (
        "🔴 o 404 da prova voltou a prometer versão de imagem. 📊 A rota não "
        "aparece no `swagger/doc.json` nem na imagem em que ela FUNCIONA — "
        "número de versão aqui é palpite com cara de instrução, e foi ele que "
        "gerou um pedido de rebuild desnecessário em 26/09/2026")
    assert "rota_ausente" not in trecho, (
        "o diagnóstico voltou a afirmar AUSÊNCIA. 📊 A rota foi provada no ar em "
        "26/09/2026; um 404 hoje diz que ela MUDOU ou foi DESLIGADA")
    assert "26/09/2026" in trecho, (
        "o 404 parou de citar a data da medição que o desmente — sem ela o "
        "próximo leitor volta a concluir que falta versão de imagem")
    assert "ENV_ROTA_FLOW_REPLY" in trecho, (
        "o 404 não diz o que CONFERIR. A variável que corrige o caminho é a "
        "primeira coisa a olhar, e ela tem de vir pelo NOME que o código usa")


def test_CONTROLE_as_ancoras_da_secao_4_CONSEGUEM_ficar_vermelhas():
    """§9.3 — um guarda que não tem como falhar não guarda nada.

    Os testes acima procuram texto e forma no arquivo real. Se as âncoras
    estivessem escritas erradas, eles passariam por vacuidade — *"não achei o
    caminho à mão"* é o que um `grep` num arquivo vazio também diz.

    Este teste prova que as duas perguntas têm respostas DIFERENTES sobre um
    conteúdo controlado: o mesmo detector acusa a versão com o defeito e absolve
    a versão sem ele.
    """
    com_defeito = '    url = f"{base_url}/send/interactiveResponse"'
    sem_defeito = '    url = f"{base_url}{rota}"'

    def _tem_caminho_a_mao(texto: str) -> bool:
        return [ln for ln in texto.splitlines()
                if not ln.lstrip().startswith("#")
                and "/send/interactiveResponse" in ln] != []

    assert _tem_caminho_a_mao(com_defeito) is True, (
        "o detector não vê o defeito nem quando ele está escrito na frente dele")
    assert _tem_caminho_a_mao(sem_defeito) is False, (
        "o detector acusa até a forma certa — ele não distingue nada")

    def _url_usa_rota(linha: str) -> bool:
        no = ast.parse(linha.strip()).body[0]
        nomes = {n.id for n in ast.walk(no.value) if isinstance(n, ast.Name)}
        return "rota" in nomes

    assert _url_usa_rota(sem_defeito) is True
    assert _url_usa_rota(com_defeito) is False
