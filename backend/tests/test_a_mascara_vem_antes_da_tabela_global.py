# -*- coding: utf-8 -*-
"""A máscara vem ANTES da tabela global — SPEC-087, BLOCO C.

📊 **O problema, medido em 26/08/2026:**

```
route_drift ............... 16 linhas · company_id: A COLUNA NÃO EXISTE
  todas sem máscara {{slot}}
playbook_overlays ......... 0 linhas · sem company_id
anchor_from_text .......... gravava re.escape(texto[:60]) CRU
note ...................... gravava texto[:120] CRU
```

> **Tráfego de UMA corretora → tabela global → lida por TODAS.**

✅ **A chave global está CERTA** — o Atlas é um só, e é decisão registrada
(`O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`). ⛔ **O vazamento não é a chave: é a carga.**

⚠️ É o mesmo furo que a SPEC-063 fechou nos mapas (115 nós com nome de segurado),
num escritor que ela não cobriu.

## 🔴 E o gate ② é o que decide se a máscara SERVE

Mascarar é fácil; mascarar **sem matar o casamento** é o problema:

```
cru        "Digite seu CPF 123.456.789-00 para continuar"
mascarado  "Digite seu CPF [CPF] para continuar"
re.escape  "Digite\\ seu\\ CPF\\ \\[CPF\\]..."          ← NÃO casa nada
```

> **Um mascarador que troca o menu por `{{texto}}` é perfeito em privacidade e
> inútil como âncora.**

⛔ **E nenhum mascarador novo foi criado** (`CLAUDE.md` §5). 📊 Existiam dois:
`redaction_service.py` (texto livre, importa só `re`) e `pii_da_sessao.py`
(dicionário de **slots**). O segundo tem a forma errada para texto de tela. O
escolhido ganhou o inverso — `ancora_permissiva` — que devolve o casamento.
"""
from __future__ import annotations

import importlib.util as _u
import re
import sys
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _carregar(rel: str, nome: str):
    """Carrega um módulo por caminho — sem subir o pacote `app` inteiro."""
    spec = _u.spec_from_file_location(nome, str(RAIZ / rel))
    mod = _u.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


@contextmanager
def _com_o_pacote_app():
    """`app` e os subpacotes em `sys.modules` **durante a chamada**.

    🔴 Sem isto o teste passa por IGNORÂNCIA: `_mascarar_texto` faz import
    local, o import falha, ele devolve `[TEXTO NAO MASCARAVEL]` — e uma
    asserção de "o CPF sumiu" fica verde porque o TEXTO INTEIRO sumiu.

    ⚠️ É a mesma armadilha que a SPEC-085 pagou com `ModuleNotFoundError`
    engolido por `try/except`.
    """
    import types

    nomes = ("app", "app.services", "app.services.intelligence",
             "app.services.atlas")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        yield
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


with _com_o_pacote_app():
    RS = _carregar("app/services/intelligence/redaction_service.py", "_rs_087")

#: 🔴 Um sha256 REAL cujos dígitos casam o padrão de telefone — é o que torna o
#: teste da `signature` capaz de falhar. ⚠️ Sem um valor assim, o guarda usa
#: `"abc123"`, que nenhum padrão alcança, e a asserção vira tautologia.
SHA_QUE_CASA_TELEFONE = (
    "27cd12345678901adc8092a45f9a65c4fa302f1278103ce040a14c9d60567ce8")
TAILOR_PY = RAIZ / "app" / "services" / "playbook_tailor.py"
SENTINEL_PY = RAIZ / "app" / "services" / "atlas" / "route_sentinel.py"


# ---------------------------------------------------------------------------
# ① texto com nome, CPF, placa ou telefone → sai mascarado
# ---------------------------------------------------------------------------

@_u.util.__class__ if False else (lambda f: f)  # noqa: E731  (sem decorador)
def _noop(f):
    return f


#: 🔴 O TERCEIRO ELEMENTO É O VALOR SENSÍVEL, NÃO A MARCA.
#:
#: ⚠️ A primeira versão guardava a marca esperada e conferia o resíduo com
#: `re.findall(r"[\d]{4,}")`. 📊 Medido: esse padrão devolve `[]` para CPF
#: pontuado, placa e e-mail — **o laço não rodava em 3 das 7 telas**, e a única
#: coisa que sobrava era "a marca apareceu". Encurtar o padrão de CPF em um
#: token deixaria `"… [CPF]-00"` e passaria verde, com dois dígitos de cada CPF
#: indo para três tabelas.
#:
#: Agora o teste pergunta o que importa: **este valor sumiu por inteiro?**
TELAS_COM_PII = [
    ("cpf", "Informe o CPF do segurado: 123.456.789-00", "123.456.789-00"),
    # 📊 Onze dígitos seguidos casam o padrão de CPF ANTES do de documento —
    # e está certo: a ordem de `PADROES_PII` é do mais específico para o menos.
    # A marca importa menos que o fato de o dado ter sumido.
    ("cpf_sem_pontos", "Documento 12345678901 confere?", "12345678901"),
    ("telefone", "Confirma o telefone (11) 98765-4321?", "98765-4321"),
    ("placa", "A placa ABC1D23 esta correta?", "ABC1D23"),
    ("email", "Enviamos para fulano.silva@exemplo.com.br", "fulano.silva@exemplo.com.br"),
    ("apolice", "Apolice n 4471-XY localizada", "4471-XY"),
    ("cnpj", "CNPJ 12.345.678/0001-90 da corretora", "12.345.678/0001-90"),
    # 🔴 AS SEIS QUE `redigir` SOZINHO DEIXAVA PASSAR.
    #
    # 📊 Medido em 26/08/2026 (entradas sintéticas): `redigir` pega 1 de 8;
    # `templatize` pega 6 das 7 restantes. A SPEC-087 mandou escolher entre
    # DOIS mascaradores e listou os dois errados — o certo para texto de tela é
    # `atlas/templater`, que a SPEC-063 já usava nos nós do Atlas.
    ("endereco", "Confirme o endereco: Rua das Palmeiras, 1450, apto 32", "1450"),
    ("nascimento", "Data de nascimento 07/09/1984 confere?", "07/09/1984"),
    ("placa_minuscula", "Veiculo de placa abc1d23", "abc1d23"),
    ("cpf_com_espacos", "CPF 123 456 789 00 confere?", "123 456 789 00"),
    ("cep_solto", "Local 01310100 SP confirmado", "01310100"),
    ("chassi", "Chassi 9BWZZZ377VT004251 do veiculo", "9BWZZZ377VT004251"),
]


def test_a_CASCATA_esta_de_pe_antes_de_qualquer_assercao():
    """🔴 A prova de que os testes abaixo medem o mascarador CERTO.

    ⚠️ `mascara_de_tela` chama `templatize` dentro de um `try`. Se o import
    falhar, ela degrada para `redigir` sozinho **em silêncio** — e metade das
    asserções deste arquivo passaria a medir o mascarador fraco sem ninguém ver.

    📊 Medido: `redigir` sozinho pega 1 de 8 telas sintéticas; a cascata pega 7.
    """
    so_templatize = "Confirme o endereco: Rua das Palmeiras, 1450, apto 32"
    with _com_o_pacote_app():
        assert RS.mascara_de_tela(so_templatize) != so_templatize, (
            "a cascata degradou para `redigir` sozinho — o import de "
            "`templatize` falhou e este arquivo inteiro passaria a medir o "
            "mascarador fraco")


def test_GATE_1_texto_com_PII_sai_MASCARADO():
    """⛔ Nada disto pode chegar cru numa tabela que todas as corretoras leem.

    🔴 A pergunta é **"este valor sumiu por inteiro?"**, e não "apareceu uma
    marca" — ver o comentário de `TELAS_COM_PII`.
    """
    sobreviveram = []
    for nome, cru, sensivel in TELAS_COM_PII:
        with _com_o_pacote_app():
            saida = RS.mascara_de_tela(cru)
        if sensivel in saida:
            sobreviveram.append(nome)
        # e o texto TEM de ter mudado — sem isto, um mascarador que devolvesse a
        # entrada intacta passaria sempre que o valor não fosse encontrado.
        assert saida != cru, f"{nome}: o mascarador não tocou no texto"
    assert not sobreviveram, (
        f"o dado sensível sobreviveu à máscara em: {sobreviveram}")


def test_GATE_1b_a_ANCORA_tambem_sai_mascarada():
    """A âncora é o que vai para `playbook_overlays.anchor` — tabela GLOBAL cujo
    cache é compartilhado por todas as corretoras."""
    sobreviveram = []
    for nome, cru, sensivel in TELAS_COM_PII:
        with _com_o_pacote_app():
            ancora = RS.ancora_permissiva(cru)
        if ancora and sensivel in ancora:
            sobreviveram.append(nome)
    assert not sobreviveram, (
        f"a âncora carregou dado sensível para a tabela global em: {sobreviveram}")


# ---------------------------------------------------------------------------
# ② 🔴 a âncora mascarada AINDA casa com a tela real
# ---------------------------------------------------------------------------

def test_GATE_2_a_ancora_mascarada_AINDA_casa_a_tela_real():
    """🔴 **O gate que decide se a máscara serve.**

    ⚠️ Mascarar demais mata o casamento — e uma âncora que não casa é um passo
    que nunca dispara: o corredor fica cego exatamente onde a máscara passou.

    ## ⛔ E a RECUSA é um resultado legítimo, não uma falha

    Quando a identidade da tela **era** a PII, não há âncora honesta a criar — e
    `ancora_permissiva` devolve `""`. Este teste exige as duas coisas: **a que
    existe, casa; e a que não existe, é vazia** (nunca um regex fraco).
    """
    casou = recusou = 0
    for nome, cru, _ in TELAS_COM_PII:
        ancora = RS.ancora_permissiva(cru)
        if not ancora:
            recusou += 1
            continue
        assert re.search(ancora, cru, re.IGNORECASE | re.DOTALL), (
            f"{nome}: a âncora mascarada NÃO casa a tela real."
            + NL + f"  âncora: {ancora[:120]}")
        casou += 1

    # 🔴 CONTROLE DOS DOIS LADOS: nem tudo casa (senão a recusa não existe),
    # nem tudo recusa (senão a máscara matou o produto).
    assert casou >= 5, (
        f"só {casou} de {len(TELAS_COM_PII)} telas produziram âncora — a máscara "
        "está matando o casamento, que é o defeito que este gate existe para pegar")
    assert recusou >= 1, (
        "NENHUMA tela foi recusada — ou o corpus não tem o caso da PII no começo, "
        "ou a recusa parou de funcionar. As duas são defeito deste teste.")


def test_GATE_2b_a_ancora_casa_a_MESMA_tela_com_OUTRO_dado():
    """⚠️ É o caso de verdade: a âncora nasce de uma sessão e precisa casar a
    tela da sessão SEGUINTE, que tem o CPF de outra pessoa."""
    primeira = "Informe o CPF do segurado: 123.456.789-00"
    segunda = "Informe o CPF do segurado: 987.654.321-99"
    ancora = RS.ancora_permissiva(primeira)
    assert re.search(ancora, segunda, re.IGNORECASE | re.DOTALL), (
        "a âncora só casa a sessão que a criou — inútil como passo")


def test_GATE_2c_a_ancora_NAO_casa_uma_tela_DIFERENTE():
    """§9.3 — prove que o curinga não virou `.*`.

    🔴 Uma âncora que casa tudo é pior que âncora nenhuma: ela sequestra a
    resposta de outra tela.
    """
    ancora = RS.ancora_permissiva("Informe o CPF do segurado: 123.456.789-00")
    assert ancora, "esta tela TEM identidade fora da PII — deveria ter âncora"
    assert not re.search(ancora, "Deseja cancelar o atendimento? 1 - Sim 2 - Nao",
                         re.IGNORECASE | re.DOTALL), (
        "a âncora casou uma tela completamente diferente")


def test_GATE_2d_a_tela_cuja_IDENTIDADE_era_a_PII_nao_vira_ancora():
    """🔴 **O achado que este gate produziu, e ele mudou o desenho.**

    A primeira versão criava a âncora de qualquer jeito. 📊 Medido:

    ```
    tela    "123.456.789-00 confirmado com sucesso"
    âncora  .{0,40}\ confirmado\ com\ sucesso
    casa    "O protocolo 9988776655 confirmado com sucesso"   ← OUTRA TELA
    ```

    ⚠️ O curinga na borda ESQUERDA deixa a âncora sem fronteira, e o que sobra é
    um final genérico. O overlay sequestraria a resposta de qualquer tela que
    termine igual.

    > ⛔ **Mascarar pode custar a âncora — e quando custa, não se cria âncora.**

    🔴 E a recusa é `""`, não um regex fraco: quem chama já pula a vazia
    (`if not anchor: continue`). Devolver `.{0,40}...` seria pior que devolver
    nada, porque parece que funcionou.
    """
    assert RS.ancora_permissiva("123.456.789-00 confirmado com sucesso") == "", (
        "a tela que começa com PII virou âncora — ela sequestra tela alheia")

    # 🔴 CONTROLE: a MESMA frase, com identidade PRÓPRIA antes da PII, vira
    # âncora normalmente. Sem esta linha, uma recusa incondicional passaria.
    com_identidade = RS.ancora_permissiva(
        "Protocolo do atendimento 123.456.789-00 confirmado com sucesso")
    assert com_identidade, "a recusa virou incondicional — nada mais vira âncora"
    assert re.search(com_identidade,
                     "Protocolo do atendimento 987.654.321-99 confirmado com sucesso",
                     re.IGNORECASE | re.DOTALL)


def test_GATE_2e_ancora_curta_demais_tambem_e_recusada():
    """⚠️ Não é sobre privacidade — é sobre servir.

    Uma âncora de três letras casa meia URA, e o overlay dela responde por telas
    que ninguém examinou.
    """
    assert RS.ancora_permissiva("Ok 123.456.789-00") == ""
    # CONTROLE: com texto fixo suficiente, vira âncora
    assert RS.ancora_permissiva("Confirmacao recebida 123.456.789-00")


# ---------------------------------------------------------------------------
# ③ 🔴 LINHA DE CONTROLE: um texto sem PII passa intacto
# ---------------------------------------------------------------------------

def test_GATE_3_CONTROLE_texto_SEM_PII_passa_intacto():
    """🔴 Sem esta linha, um mascarador que apagasse tudo passaria no ① e no ②
    seria pego só por sorte."""
    limpo = "Escolha uma opcao: 1 - Guincho 2 - Chaveiro 3 - Falar com atendente"
    assert RS.redigir(limpo) == limpo, (
        "o mascarador mexeu num texto que não tem PII nenhuma")
    ancora = RS.ancora_permissiva(limpo)
    assert re.search(ancora, limpo), "a âncora de texto limpo não casa o próprio texto"
    assert ".{0,40}" not in ancora, (
        "apareceu curinga num texto sem PII — o mascarador está vendo PII onde "
        "não há, e cada curinga a mais é uma âncora menos específica")


# ---------------------------------------------------------------------------
# 🔴 OS ESCRITORES — sem isto, o mascarador guarda um caminho que ninguém usa
# ---------------------------------------------------------------------------

def test_o_ALFAIATE_mascara_ancora_E_nota():
    """📊 Os dois campos iam crus. Consertar só a âncora seria trancar a porta
    e deixar a janela aberta."""
    fonte = TAILOR_PY.read_text(encoding="utf-8")
    assert "ancora_permissiva(text)" in fonte, (
        "`anchor_from_text` voltou a escapar o texto CRU")
    assert "re.escape(snippet)" not in fonte
    i = fonte.index('"note":')
    linha = fonte[i:fonte.index("\n", i)]
    assert "_mascarar(t)" in linha, (
        f"a nota do overlay voltou a gravar texto cru: {linha.strip()[:80]}")


def test_o_SENTINELA_mascara_summary_E_detail():
    """⚠️ `detail` é um `jsonb` com listas dentro — mascarar só o topo deixaria
    `detail.added[0]` cru, que é exatamente onde o texto da tela mora."""
    fonte = SENTINEL_PY.read_text(encoding="utf-8")
    assert '"summary": _mascarar_texto(summary),' in fonte
    assert '"detail": _mascarar_fundo({' in fonte
    assert "def _mascarar_fundo(" in fonte


def test_a_mascara_do_SENTINELA_e_recursiva():
    """A prova de comportamento do parágrafo acima."""
    S = _carregar("app/services/atlas/route_sentinel.py", "_sent_087")
    with _com_o_pacote_app():
        fundo = S._mascarar_fundo({
            "added": ["Informe o CPF 123.456.789-00", {"tela": "placa ABC1D23"}],
            # 🔴 UM SHA256 QUE **CASA** O PADRÃO DE TELEFONE.
            #
            # ⚠️ A primeira versão usava `"abc123"` — um valor que nenhum padrão
            # de PII alcança, então `fundo["signature"] == "abc123"` **não tinha
            # como falhar**. §9.3 literal.
            #
            # 📊 E o defeito era real e JÁ ESTAVA EM PRODUÇÃO: o padrão de
            # telefone não tem `` e casa qualquer corrida de 10–11 dígitos
            # dentro do hex. Duas revisões independentes mediram ~17,9% de
            # 50.000 hashes destruídos — e uma linha de `route_drift` já está
            # com 58 caracteres em vez de 64. Foi o backfill desta SPEC.
            "signature": SHA_QUE_CASA_TELEFONE,
            "quantos": 4,
        })
    # 🔴 A PROVA DE QUE CHEGOU AO MASCARADOR. Sem ela, a asserção "o CPF sumiu"
    # ficaria verde com o texto inteiro trocado por `[TEXTO NAO MASCARAVEL]`.
    assert "[TEXTO NAO MASCARAVEL]" not in repr(fundo), (
        "o import do mascarador falhou — este teste estaria passando por "
        "ignorância, não por mascaramento")
    despejo = repr(fundo)
    assert "123.456.789-00" not in despejo, "o CPF sobreviveu dentro da lista"
    assert "ABC1D23" not in despejo, "a placa sobreviveu dentro do dicionário aninhado"
    # ⚠️ AS MARCAS SÃO DE CHAVE, e não de colchete: a cascata roda `templatize`
    # primeiro, e ele deixa `{CPF}`/`{PLACA}`. 📊 É o que permite pegar endereço,
    # data de nascimento, chassi e CEP solto, que `redigir` sozinho não vê.
    assert "{CPF}" in despejo and "{PLACA}" in despejo
    # ⚠️ e o que NÃO é texto continua intacto
    assert fundo["quantos"] == 4
    assert fundo["signature"] == SHA_QUE_CASA_TELEFONE, (
        "a `signature` foi MASCARADA — ela é a chave de dedupe do drift, e "
        "mutilada faz `_same_unresolved_drift` nunca casar: a linha duplica e o "
        "Founder recebe o mesmo alerta por WhatsApp a cada varredura")
    assert len(fundo["signature"]) == 64, (
        f"o digest saiu com {len(fundo['signature'])} caracteres em vez de 64")


def test_FALHA_FECHADA_nao_conseguir_mascarar_nao_grava_cru():
    """🔴 Não conseguir mascarar **nunca** vira permissão para gravar cru."""
    S = _carregar("app/services/atlas/route_sentinel.py", "_sent_087b")
    import builtins

    original = builtins.__import__

    def _sem_mascarador(nome, *a, **k):
        if "redaction_service" in nome:
            raise ImportError("mascarador fora do ar")
        return original(nome, *a, **k)

    builtins.__import__ = _sem_mascarador
    try:
        saida = S._mascarar_texto("Informe o CPF 123.456.789-00")
    finally:
        builtins.__import__ = original

    assert "123.456.789-00" not in saida, (
        "sem mascarador, o texto CRU foi gravado — falha ABERTA")
    assert saida == "[TEXTO NAO MASCARAVEL]"


# ---------------------------------------------------------------------------
# ⛔ NENHUM MASCARADOR NOVO — `CLAUDE.md` §5
# ---------------------------------------------------------------------------

def test_nenhum_TERCEIRO_mascarador_foi_criado():
    """📊 Existiam dois. O BLOCO C escolheu um e o estendeu; não criou o terceiro.

    ⚠️ `pii_da_sessao` NÃO foi o escolhido, e o motivo é medido: ele opera em
    **dicionário de slots** (`mascarar_slots`, `retrato_para_humano`), não em
    texto livre. Forma errada para tela de URA — não é preferência.
    """
    tailor = TAILOR_PY.read_text(encoding="utf-8")
    sentinel = SENTINEL_PY.read_text(encoding="utf-8")
    for fonte, nome in ((tailor, "playbook_tailor"), (sentinel, "route_sentinel")):
        assert "redaction_service" in fonte, (
            f"{nome} parou de usar o mascarador único")
        assert "PADROES_PII = [" not in fonte, (
            f"{nome} ganhou uma lista de padrões PRÓPRIA — duas listas divergem, "
            "e a que fica para trás é justamente a que deixa passar o CPF")

    # e o mascarador único continua sem importar o projeto
    rs = (RAIZ / "app" / "services" / "intelligence" / "redaction_service.py").read_text(
        encoding="utf-8")
    imports = [l for l in rs.splitlines() if l.startswith(("import ", "from "))]
    assert imports == ["from __future__ import annotations", "import re"], (
        f"`redaction_service` ganhou import do projeto: {imports}. Ele precisa "
        "poder ser carregado e testado sem subir banco, Redis ou LLM.")


def test_as_MARCAS_saem_dos_PADROES_e_nao_de_uma_lista_a_mao():
    """§9.3 — duas listas que precisam concordar divergem.

    Se alguém acrescentar um padrão novo em `PADROES_PII` e esquecer a marca,
    `ancora_permissiva` escaparia a marca em vez de virar curinga — e a âncora
    deixaria de casar em silêncio.
    """
    das_marcas = set(RS.MARCAS)
    dos_padroes = {m for _, m in RS.PADROES_PII}
    # ✅ A LIÇÃO MIGROU. `MARCAS` agora cobre DUAS famílias: a de colchete, que
    # `redigir` produz e sai de `PADROES_PII`, e a de chave, que `templatize`
    # produz. 🔴 Se a de colchete deixasse de ser derivada, a divergência que
    # este guarda existe para pegar voltaria.
    assert dos_padroes <= das_marcas, (
        f"marca de `PADROES_PII` que ficou fora de `MARCAS`: "
        f"{dos_padroes - das_marcas} — `ancora_permissiva` a escaparia em vez "
        "de virar curinga, e a âncora deixaria de casar em silêncio")
    de_chave = set(RS._MARCAS_DE_CHAVES)
    assert de_chave <= das_marcas
    assert das_marcas == dos_padroes | de_chave, (
        "apareceu marca em `MARCAS` que não vem de nenhuma das duas fontes")


def test_GATE_2f_o_curinga_NAO_atravessa_a_tela():
    """🔴 O risco real do `.*`: ele **engole telas inteiras**.

    ⚠️ As âncoras casam com `re.DOTALL` — um curinga ilimitado no meio atravessa
    quebras de linha e junta o começo de uma tela com o fim de outra, no meio de
    uma rajada. O overlay dispararia sobre uma tela que ninguém examinou.

    📊 `{0,40}` cobre CPF, telefone, placa e apólice com folga — e para aí.
    """
    ancora = RS.ancora_permissiva("Documento 12345678901 confere?")
    assert ancora and ".{0,40}" in ancora, (
        f"esperava um curinga limitado no meio da âncora: {ancora[:90]}")

    # ⚠️ A rajada NÃO contém a tela real — se contivesse, o casamento seria
    # legítimo e este teste estaria medindo outra coisa. O que ela tem são as
    # DUAS METADES da âncora, separadas por mais de 200 caracteres.
    rajada = ("Documento 11122233344 nao bate com o cadastro."
              + "\n" + "-" * 200 + "\n"
              + "Aguarde o atendente. Se confere?")
    assert not re.search(ancora, rajada, re.IGNORECASE | re.DOTALL), (
        "a âncora atravessou a rajada e casou o começo de uma tela com o fim de "
        "outra — o curinga virou `.*`")

    # 🔴 CONTROLE: a MESMA âncora casa a tela dela, sozinha.
    assert re.search(ancora, "Documento 99988877766 confere?",
                     re.IGNORECASE | re.DOTALL), (
        "ao limitar o curinga a âncora deixou de casar a própria tela")

# =========================================================================
# 🔴 OS TRÊS QUE A BATERIA DE MUTAÇÃO PEGOU VERDES
# =========================================================================

def test_o_CORTE_nunca_parte_uma_MARCA_ao_meio():
    """🔴 Cortar em 60 no meio de `{CEP}` deixa `\\{CE` pendurado.

    ⚠️ O fragmento não é reconhecido como marca, vira parte FIXA e é
    escapado — e a âncora resultante **nunca casa o texto cru**. O overlay
    entra em `playbook_overlays` morto, parecendo que funcionou, e o corredor
    continua travando na mesma tela.

    📊 Antes desta SPEC, `re.escape(cru[:60])` casava. Foi o conserto que
    criou a forma de quebrar.
    """
    # 60 caracteres de texto fixo, e aí a PII — o corte cai DENTRO da marca.
    cru = ("Prezado cliente, informe agora mesmo o seu CPF de titular "
           "123.456.789-00 obrigado")
    with _com_o_pacote_app():
        ancora = RS.ancora_permissiva(cru)

    # ⛔ A âncora ou casa, ou não existe. O que ela **não pode** é existir e
    #    não casar: isso é um overlay morto numa tabela global.
    if ancora:
        assert re.search(ancora, cru, re.IGNORECASE | re.DOTALL), (
            "a âncora existe e NÃO casa a tela que a gerou — o corte partiu uma "
            f"marca ao meio.{chr(10)}  âncora: {ancora[:120]}")
        # e não sobrou marca pela metade
        assert "\\{" not in ancora and "\\[" not in ancora, (
            f"sobrou um fragmento de marca escapado na âncora: {ancora[:120]}")


def test_CONTROLE_uma_tela_curta_com_PII_no_fim_AINDA_vira_ancora():
    """§9.3 — sem esta linha, um cortador que devolvesse `""` sempre passaria
    no teste acima."""
    with _com_o_pacote_app():
        ancora = RS.ancora_permissiva("Informe o CPF: 123.456.789-00")
    assert ancora, "o corte passou a recusar tudo"
    assert re.search(ancora, "Informe o CPF: 987.654.321-99",
                     re.IGNORECASE | re.DOTALL)


def test_ancora_com_curingas_DEMAIS_e_recusada():
    """🔴 Backtracking catastrófico — e o alvo é o acionamento de TODOS.

    ⚠️ `fixo.{0,40}fixo.{0,40}…` é exponencial quando os pedaços fixos são
    curtos. 📊 Medido pelo painel: uma âncora com 6 curingas e 14 caracteres
    fixos — que PASSA no `_MINIMO_FIXO` — contra um alvo de 1.200 chars que
    não casa **não terminou em 120 s**.

    🔴 E `match_ura_step` roda `re.search` SÍNCRONO dentro do laço de eventos,
    para toda mensagem que chega, com `playbook_overlays` em cache **global**.
    Uma âncora patológica congela o acionamento de todas as corretoras.
    """
    # seis campos de PII e pouco texto entre eles
    muitos = ("aa 123.456.789-00 bb (11)91234-5678 cc 12.345.678/0001-90 "
              "dd x@y.com.br ee CEP 01234-567 ff ABC1D23 gg")
    with _com_o_pacote_app():
        ancora = RS.ancora_permissiva(muitos, limite=200)
    # 🔴 A ÂNCORA PATOLÓGICA É RECUSADA. E o número é LITERAL, não a constante.
    #
    # ⚠️ A primeira versão fazia `quantos <= RS._MAX_CURINGAS` — os dois lados se
    # mexem juntos. O juiz mediu: `_MAX_CURINGAS = 3` → `99` deixava a âncora
    # patológica de seis curingas nascer, e o teste **reportava PASSA**. Pior: em
    # base a âncora é `""`, então o corpo do `if` nem executava — no-op no verde
    # e cego no vermelho.
    assert ancora == "", (
        "a âncora de SEIS campos de PII foi criada — ela é exatamente a forma "
        f"exponencial que o teto existe para barrar.{chr(10)}  âncora: {ancora[:140]}")


def test_CONTROLE_uma_ancora_com_POUCOS_curingas_passa():
    """§9.3 — o teto não pode ter virado uma recusa geral."""
    with _com_o_pacote_app():
        ancora = RS.ancora_permissiva("Confirme o telefone (11) 91234-5678 agora")
    assert ancora, "o teto de curingas passou a recusar âncora legítima"
    # ⚠️ NÚMERO LITERAL, pelo mesmo motivo do teste acima.
    assert ancora.count(".{0,40}") <= 3, (
        f"a âncora legítima saiu com {ancora.count('.{0,40}')} curingas")


def test_anchor_from_text_NUNCA_levanta():
    """🔴 Antes desta SPEC ela era `re.escape` puro e não tinha como falhar.

    ⚠️ Ao ganhar um import, ganhou uma forma de morrer — e 📊 quebrou
    `test_spec034_onda4`, um guarda que roda como SCRIPT sem o pacote `app`.
    Uma exceção aqui subiria por `apply_auto_overlays` e derrubaria o Alfaiate
    inteiro por causa de uma âncora.

    ⛔ A degradação é FECHADA: sem mascarador, âncora nenhuma — nunca o cru.
    """
    import builtins

    TAILOR = _carregar("app/services/playbook_tailor.py", "_tailor_087c")
    original = builtins.__import__

    def _sem_mascarador(nome, *a, **k):
        if "redaction_service" in nome:
            raise ImportError("mascarador fora do ar")
        return original(nome, *a, **k)

    builtins.__import__ = _sem_mascarador
    try:
        saida = TAILOR.anchor_from_text("vale lembrar: mantenha (seus) dados")
    except Exception as erro:                       # noqa: BLE001
        raise AssertionError(
            f"`anchor_from_text` LEVANTOU ({type(erro).__name__}) — uma exceção "
            "aqui derruba o Alfaiate inteiro por causa de uma âncora") from erro
    finally:
        builtins.__import__ = original

    assert saida == "", (
        f"sem mascarador devolveu {saida[:60]!r} — a degradação tem de ser "
        "FECHADA: âncora nenhuma, nunca o texto cru")
