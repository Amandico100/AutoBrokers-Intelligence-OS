# -*- coding: utf-8 -*-
"""A anotação da Regina e da Saionara entra no produto — SPEC-090, BLOCO C.

> 🔴 **É o bloco que decide se o piloto vira conserto ou vira conversa de
> WhatsApp perdida.** Sem porta, o que as duas observarem no primeiro dia
> se perde.

## 🔴 O QUE A MEDIÇÃO DERRUBOU DO DESENHO DA SPEC

A SPEC manda a atendente escrever `#nota …` **na conversa do segurado** e diz
que *"o prefixo é consumido: a mensagem é capturada, gravada e não reenviada"*.
O gate ② dela é *"🔴 ZERO chance de o `#nota` chegar ao segurado"*.

📊 **Medido em 26/08 — nesse caminho, esse gate é inalcançável:**

```
evolution_go_events.py:47   force_from_me = ev in ("sendmessage", "send.message")
evolution_inbound.py:847    if from_me: return {**out, "skip": True,
                                                "skip_reason": "from_me"}
```

⛔ **`fromMe` é o ECO de uma mensagem que o WhatsApp JÁ ENTREGOU.** O produto
não é o remetente e não está no caminho. A SPEC trata isso como o risco *"se o
prefixo escapar uma vez"* — **não é risco, é o comportamento padrão.**

✅ **E existe um caminho onde o gate ② é real:** `POST /api/webhook/send-message`
(`webhook.py:1475`), o envio do painel, onde o produto **é** o remetente.

Então os dois caminhos são tratados diferente, e a coluna `origem` guarda a
diferença — sem ela, o relatório diria *"12 notas, nenhuma vazou"* sobre um dia
em que sete foram lidas pelo segurado.
"""
from __future__ import annotations

import importlib.util as _u
import re
import sys
import types
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEBHOOK_PY = RAIZ / "app" / "api" / "webhook.py"
INBOUND_PY = RAIZ / "app" / "services" / "whatsapp" / "evolution_inbound.py"
MIGRATION = (RAIZ / "supabase" / "migrations"
             / "20260826_03_spec090_blocoC_notas_da_atendente.sql")


@contextmanager
def _com_o_pacote_app():
    """`app` e subpacotes em `sys.modules` — sem isto o mascarador não carrega e
    o arquivo passaria por IGNORÂNCIA (a lição da SPEC-087)."""
    nomes = ("app", "app.services", "app.services.intelligence",
             "app.services.atlas", "app.core")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / nome.replace(".", "/"))]
            sys.modules[nome] = mod
        yield
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


def _carregar(rel: str, nome: str):
    spec = _u.spec_from_file_location(nome, RAIZ / rel)
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NOTA = _carregar("app/services/a_nota_da_atendente.py", "_nota_090C")


# =============================================================================
# 🔴 SÓ O CÓDIGO — e esta é a TERCEIRA vez nesta SPEC que a prosa engana
# =============================================================================
#
# 📊 Aconteceu três vezes, sempre igual:
#   · `.eq("company_id"` apagado da consulta → passava, porque a docstring
#     da função diz a frase;
#   · `UNIQUE (id, company_id)` virando `UNIQUE (id)` → passava, porque o
#     bloco VERIFY repete a frase num comentário;
#   · a interceptação da nota vindo DEPOIS do envio → o teste apontou o erro
#     ao contrário, porque o COMENTÁRIO acima dela cita
#     `whatsapp_service.send_message` e o `find` achou o comentário primeiro.
#
# ⚠️ Nos três, o guarda estava lendo a explicação de por que o código deveria
# existir, e concluindo que ele existia. §9.3.


def _so_o_codigo(fonte: str) -> str:
    """O Python sem comentários `#` e sem docstrings — preservando o TAMANHO.

    🔴 Cada caractere removido vira espaço, então os `find()` continuam
    apontando para a posição real no arquivo. Um corte que encurta bagunçaria
    exatamente a comparação de ordem que este arquivo faz.
    """
    saida = []
    for linha in fonte.split(chr(10)):
        antes, marca, depois = linha.partition("#")
        saida.append(antes + " " * (len(marca) + len(depois)) if marca else linha)
    sem_comentario = chr(10).join(saida)
    # e as docstrings, pelo mesmo critério de tamanho preservado
    partes = sem_comentario.split('"""')
    for i in range(1, len(partes), 2):
        partes[i] = " " * len(partes[i])
    return '"""'.join(partes)


# =============================================================================
# 🔴 CONTROLE DE CARGA — e o da CASCATA, que a 087 pagou para aprender
# =============================================================================

def test_CONTROLE_o_modulo_carregou():
    assert callable(NOTA.e_nota)
    assert callable(NOTA.linha_da_nota)
    assert NOTA.ORIGENS == ("painel", "whatsapp")


def test_CONTROLE_o_MASCARADOR_esta_de_pe_antes_de_qualquer_assercao():
    """🔴 §9.3 — na SPEC-087 um arquivo inteiro passou por IGNORÂNCIA.

    ⛔ Se o mascarador não carregar, `linha_da_nota` devolve `None` **sempre**,
    e todo teste de "a nota foi gravada mascarada" fica verde por vacuidade.
    """
    with _com_o_pacote_app():
        from app.services.intelligence.redaction_service import mascara_de_tela
        saida = mascara_de_tela("o CPF 123.456.789-00 apareceu duas vezes")
    assert "123.456.789-00" not in saida, (
        f"o mascarador não mascarou: {saida!r} — todo teste abaixo é vácuo")


# =============================================================================
# ① 🔴 A ESTREITEZA DO PREFIXO — é ela que é o guarda
# =============================================================================

def test_a_nota_e_reconhecida_no_COMECO():
    assert NOTA.e_nota("#nota o robô perguntou a placa duas vezes")
    assert NOTA.texto_da_nota("#nota o robô perguntou a placa duas vezes") == (
        "o robô perguntou a placa duas vezes")


def test_MAIUSCULA_tambem_conta_e_a_razao_e_o_teclado():
    """⚠️ 📊 Teclado de celular capitaliza a primeira letra.

    ⛔ Com a regra sensível a maiúscula, a Regina digita `#nota`, o teclado
    manda `#Nota`, e a anotação dela vira INTERVENÇÃO: pausa o robô **e** vai
    para o segurado. **Errar para o lado estrito custa as duas coisas.**
    """
    for forma in ("#Nota o robô errou", "#NOTA o robô errou", "#NoTa o robô errou"):
        assert NOTA.e_nota(forma), f"{forma!r} não foi reconhecida"


def test_o_PREFIXO_NO_MEIO_nao_e_nota():
    """Gate ⑤ — *"o robô errou #nota"* é intervenção, e PAUSA.

    ⚠️ Uma exceção larga vira o buraco que a regra de 14/08 fechou.
    """
    for entrada in ("o robô errou #nota", "olha isso #nota aqui",
                    "  #nota com espaço antes", "\n#nota depois de quebra",
                    "\t#nota depois de tab"):
        assert not NOTA.e_nota(entrada), f"{entrada!r} passou como nota"


def test_NOTAS_e_outra_palavra():
    assert not NOTA.e_nota("#notas do dia")
    assert not NOTA.e_nota("#notavel")
    assert NOTA.e_nota("#nota: dois pontos servem")
    assert NOTA.e_nota("#nota- traço serve")


def test_so_o_PREFIXO_sem_texto_nao_vira_nota():
    """⛔ Um prefixo sozinho é engano de digitação, não observação. 📊 E o banco
    também recusa (`ck_notas_atendente_texto`)."""
    for entrada in ("#nota", "#nota   ", "#nota:", "#nota :  "):
        assert NOTA.texto_da_nota(entrada) == "", f"{entrada!r} virou texto"
        assert NOTA.linha_da_nota(company_id="c", texto_bruto=entrada,
                                  origem="painel") is None


def test_mensagem_normal_da_atendente_NAO_e_nota():
    """Gate ④ — a LINHA DE CONTROLE. Sem ela, um `return True` fixo passaria em
    tudo acima, e toda mensagem da atendente deixaria de pausar a IA."""
    for entrada in ("Bom dia, já estou vendo seu caso",
                    "Oi! Consegui falar com a seguradora", "", None,
                    "nota: sem cerquilha", "# nota com espaço no meio"):
        assert not NOTA.e_nota(entrada), f"{entrada!r} virou nota"


# =============================================================================
# ② 🔴 ZERO CHANCE DE CHEGAR AO SEGURADO — e o gate mede o CÓDIGO que envia
# =============================================================================

def test_o_painel_INTERCEPTA_ANTES_de_enviar():
    """🔴 Gate ②, no único caminho em que ele é alcançável.

    ⛔ **A ordem é o guarda inteiro:** gravar depois de enviar seria enviar. O
    `return` da anotação tem de vir ANTES da primeira chamada a `send_message`.
    """
    # 🔴 SÓ O CÓDIGO. 📊 Sem isto o teste apontava o erro AO CONTRÁRIO: o
    #    comentário acima da interceptação cita `whatsapp_service.send_message`,
    #    e o `find` achava o comentário — 300 caracteres antes do envio real.
    fonte = _so_o_codigo(WEBHOOK_PY.read_text(encoding="utf-8"))
    corpo = fonte.split("async def admin_send_message", 1)[1].split("\n@router", 1)[0]

    pos_nota = corpo.find("_e_uma_anotacao(payload.message)")
    pos_envio = corpo.find("whatsapp_service.send_message")
    assert pos_nota != -1, "o painel não reconhece a anotação"
    assert pos_envio != -1, "o teste está lendo o bloco errado"
    assert pos_nota < pos_envio, (
        "🔴 a checagem da anotação vem DEPOIS do envio — a nota sai para o "
        "segurado e só então é gravada")

    # e o caminho da nota RETORNA, em vez de cair no envio
    trecho = corpo[pos_nota:pos_envio]
    assert "return await _consumir_anotacao_do_painel" in trecho, (
        "a anotação não interrompe o fluxo — ela continua até o envio")


def test_o_consumidor_do_painel_NAO_TEM_caminho_de_envio():
    """🔴 O gate ② de novo, agora sobre a função que executa.

    ⚠️ Ler *"ela retorna antes"* não basta: se `_consumir_anotacao_do_painel`
    chamasse `send_message` por dentro, o `return` não protegeria nada.
    """
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    corpo = fonte.split("async def _consumir_anotacao_do_painel", 1)[1]
    corpo = corpo.split("\nasync def ", 1)[0].split("\ndef ", 1)[0]
    corpo_sem_doc = '"""'.join(corpo.split('"""')[::2])   # ⛔ sem a prosa

    for proibido in ("send_message", "send_image", "send_audio",
                     "platform_sends", "whatsapp_service"):
        assert proibido not in corpo_sem_doc, (
            f"🔴 `{proibido}` dentro do consumidor da anotação — o gate ② cai")


def test_o_painel_responde_ANOTADA_e_nao_SENT():
    """⚠️ Se a tela disser *"enviado"*, a atendente vai achar que o cliente leu."""
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    corpo = fonte.split("async def _consumir_anotacao_do_painel", 1)[1]
    corpo = corpo.split("\nasync def ", 1)[0]
    assert '"status": "anotada"' in corpo
    assert '"enviada": False' in corpo
    assert '"status": "sent"' not in corpo


def test_o_caminho_do_WHATSAPP_e_ECO_e_a_SPEC_esta_errada_sobre_ele():
    """🔴 A afirmação que derruba o gate ② da SPEC, verificada NO CÓDIGO.

    📊 `from_me` devolve `skip=True` — o produto não é o remetente, só observa.
    ⛔ Não existe ponto de interceptação nesse caminho, e prometer que existe
    seria a promessa que o segurado paga.
    """
    inbound = INBOUND_PY.read_text(encoding="utf-8")
    assert 'return {**out, "skip": True, "skip_reason": "from_me"}' in inbound, (
        "a forma do `from_me` mudou — refaça a medição antes de confiar no "
        "desenho do BLOCO C")


def test_a_origem_separa_o_que_saiu_do_que_nao_saiu():
    """🔴 Sem esta coluna, o relatório diria *"nenhuma vazou"* sobre um dia em
    que sete foram lidas pelo segurado."""
    with _com_o_pacote_app():
        do_painel = NOTA.linha_da_nota(
            company_id="c1", texto_bruto="#nota travou na placa",
            origem=NOTA.ORIGEM_PAINEL)
        do_whats = NOTA.linha_da_nota(
            company_id="c1", texto_bruto="#nota travou na placa",
            origem=NOTA.ORIGEM_WHATSAPP)
    assert do_painel["origem"] == "painel"
    assert do_whats["origem"] == "whatsapp"
    assert do_painel["origem"] != do_whats["origem"]


def test_origem_INVENTADA_e_recusada_antes_do_banco():
    with _com_o_pacote_app():
        assert NOTA.linha_da_nota(company_id="c1", texto_bruto="#nota x",
                                  origem="caderno") is None


# =============================================================================
# ③ 🔴 A NOTA NÃO PAUSA A IA — *"o mais fácil de errar"*, diz a SPEC
# =============================================================================

def test_a_nota_NAO_pausa_e_a_mensagem_normal_PAUSA():
    """Gate ③ **e** gate ④ na mesma leitura — os dois lados do mesmo `if`.

    ⛔ Testar só o gate ③ deixaria passar um conserto que nunca pausa nada, e
    isso reabriria o buraco de 14/08: duas vozes na mesma conversa.
    """
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    bloco = fonte.split('if normalized.get("skip_reason") == "from_me"', 1)[1]
    bloco = bloco.split("return {\"status\": \"ignored\"", 1)[0]
    sem_doc = "#".join(l.split("#", 1)[0] for l in bloco.splitlines())

    pausa = "await pausar_por_intervencao_humana"
    assert pausa in sem_doc, "o caminho que PAUSA sumiu — 14/08 reaberto"

    # a nota entra num ramo que NÃO chama a pausa
    assert "elif _e_nota:" in sem_doc, (
        "não há ramo próprio para a anotação — ela cai no `else` e pausa a IA")
    ramo = sem_doc.split("elif _e_nota:", 1)[1].split("else:", 1)[0]
    assert pausa not in ramo, "🔴 o ramo da anotação PAUSA a IA — anotar virou assumir"


def test_a_nota_NAO_marca_assuncao_humana():
    """🔴 O SEGUNDO lugar onde *"anotar viraria assumir"* — e a SPEC só viu o
    primeiro.

    📊 `note_manual_outbound(foi_humano=True)` faz três escritas duráveis
    (SPEC-093 C.1), entre elas `work_runs.unblock_state='assumido_por_humano'`.
    ⛔ E ela dispara no cenário exato do piloto: a Regina está olhando a
    conversa com a SEGURADORA, que é onde a URA trava.

    ⚠️ `foi_humano=False` seria pior: creditaria ao ROBÔ uma mensagem que uma
    pessoa escreveu — o BLOCO C.1 ao contrário.
    """
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    pos = fonte.find("await note_manual_outbound(")
    assert pos != -1
    antes = fonte[max(0, pos - 400):pos]
    sem_doc = "#".join(l.split("#", 1)[0] for l in antes.splitlines())
    assert "if not _e_nota:" in sem_doc, (
        "🔴 a anotação chega a `note_manual_outbound` — ela marcaria o "
        "acionamento como assumido por humano")


def test_e_nota_NASCE_FORA_do_try():
    """🔴 A lição do juiz da SPEC-093, migrada (§9.3).

    📊 Lá `_fomos_nos` só era atribuído DENTRO do bloco do Espelho: se o bloco
    estourasse antes, a chamada seguinte levantava `NameError` e a intervenção
    humana deixava de ser registrada POR INTEIRO. **Eu escrevi `_e_nota` com o
    mesmo defeito na primeira versão.**
    """
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    bloco = fonte.split('if normalized.get("skip_reason") == "from_me"', 1)[1][:9000]
    pos_decl = bloco.find("_e_nota = False")
    pos_try = bloco.find("            try:")
    assert pos_decl != -1, "`_e_nota` não tem inicialização"
    assert pos_decl < pos_try, (
        "🔴 `_e_nota` nasce DENTRO do `try` — se o Espelho cair antes, o "
        "`elif _e_nota` levanta NameError e a pausa some junto")
    # e a inicialização é a segura
    assert "_e_nota = False" in bloco and "_e_nota = True" not in bloco.split(
        "if not _fomos_nos", 1)[0]


# =============================================================================
# ④ a nota é MASCARADA pelo mascarador único
# =============================================================================

def test_a_nota_e_MASCARADA_antes_de_gravar():
    """🔴 Uma nota é escrita por gente com pressa: *"o robô perguntou a placa
    ABC1D23 duas vezes"*."""
    with _com_o_pacote_app():
        linha = NOTA.linha_da_nota(
            company_id="c1", origem="painel",
            texto_bruto=("#nota o robô pediu o CPF 123.456.789-00 e a placa "
                         "ABC1D23 duas vezes seguidas"))
    assert linha is not None
    assert "123.456.789-00" not in linha["texto"], f"CPF cru: {linha['texto']!r}"
    assert "ABC1D23" not in linha["texto"], f"placa crua: {linha['texto']!r}"
    # ⚠️ e o SENTIDO sobrevive — mascarar não pode apagar a observação.
    #    📊 A saída real é: "o robô pediu o CPF {CPF} e a placa {PLACA} duas
    #    vezes seguidas" — a PII vira marca e a observação fica de pé.
    assert "robô" in linha["texto"], f"a observação sumiu: {linha['texto']!r}"
    assert "duas vezes seguidas" in linha["texto"], (
        f"a máscara comeu a observação: {linha['texto']!r}")


def test_o_mascarador_e_o_UNICO_da_casa():
    """§5 — dois mascaradores que precisam concordar divergem, e o que fica
    para trás é justamente o que deixa passar o CPF."""
    fonte = (RAIZ / "app" / "services" / "a_nota_da_atendente.py").read_text("utf-8")
    assert "redaction_service import mascara_de_tela" in fonte
    assert not re.search(r"^PADROES|^_CPF|^_PLACA", fonte, re.M), (
        "o módulo da nota tem os próprios padrões de PII — é um segundo mascarador")


def test_SEM_mascarador_a_nota_NAO_e_gravada():
    """⛔ A degradação é FECHADA. Uma nota perdida é um incômodo que a Regina
    reescreve; uma placa crua numa tabela nova não se desfaz."""
    import builtins
    original = builtins.__import__

    def _sem(nome, *a, **k):
        if "redaction_service" in nome:
            raise ImportError("mascarador fora do ar")
        return original(nome, *a, **k)

    builtins.__import__ = _sem
    try:
        linha = NOTA.linha_da_nota(company_id="c1", origem="painel",
                                   texto_bruto="#nota a placa ABC1D23")
    finally:
        builtins.__import__ = original
    assert linha is None, (
        f"gravou sem mascarador: {linha} — a degradação tem de ser FECHADA")


# =============================================================================
# ⑤ 🔴 DOIS TENANTS + o CHECK, no banco
# =============================================================================

def test_a_migration_tem_company_id_RLS_e_FK_COMPOSTA():
    sql = "\n".join(l.split("--", 1)[0] for l in
                    MIGRATION.read_text(encoding="utf-8").splitlines())
    assert "company_id        uuid NOT NULL" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FOREIGN KEY (conversation_id, company_id)" in sql, (
        "a FK não é composta — a nota de uma corretora poderia apontar para "
        "conversa de outra")
    assert "REFERENCES public.conversations (id, company_id)" in sql


def test_a_migration_LISTA_os_valores_do_CHECK():
    """🔴 Exigência do protocolo: *"toda migration lista os valores do CHECK no
    APPLY"*."""
    sql = MIGRATION.read_text(encoding="utf-8")
    codigo = "\n".join(l.split("--", 1)[0] for l in sql.splitlines())
    assert "CHECK (origem IN ('painel', 'whatsapp'))" in codigo
    assert "CHECK (length(btrim(texto)) > 0)" in codigo
    # e os valores estão escritos no APPLY, para quem lê o arquivo
    assert "'painel'" in sql and "'whatsapp'" in sql


def test_o_VERIFY_tem_o_CONTROLE_com_a_linha_que_ACEITA():
    """§9.2 — provar que o banco RECUSA não vale nada se ele recusar tudo."""
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "nota valida ACEITA" in sql or "nota VALIDA" in sql.upper()
    assert "origem invalida RECUSADA" in sql
    assert "cross-tenant RECUSADO" in sql


def test_o_gravador_poe_company_id_em_TODA_linha():
    """🔴 §7 — o backend usa service role e atravessa a RLS. Quem protege é
    este campo."""
    with _com_o_pacote_app():
        linha = NOTA.linha_da_nota(company_id="empresa-1", origem="painel",
                                   texto_bruto="#nota travou")
    assert linha["company_id"] == "empresa-1"
    fonte = (RAIZ / "app" / "services" / "a_nota_da_atendente.py").read_text("utf-8")
    corpo = fonte.split("async def travamento_mais_recente", 1)[1]
    assert '.eq("company_id", str(company_id))' in corpo, (
        "a consulta do travamento recente não filtra por corretora — a nota "
        "de uma corretora ganharia a rota da outra")


def test_a_conversa_AMBIGUA_vira_NULO_como_no_bloco_A():
    """⚠️ 📊 2 pares (corretora, telefone) têm mais de uma conversa, e o pior
    caso tem 57. Uma nota pendurada na conversa errada é pior que uma solta —
    a solta ainda aparece na leitura do dia."""
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    corpo = fonte.split("async def _conversa_do_telefone", 1)[1]
    corpo = corpo.split("\n@router", 1)[0].split("\nasync def ", 1)[0]
    assert "len(linhas) == 1" in corpo, (
        "a resolução da conversa escolhe uma entre várias — é adivinhar")
    assert '.eq("company_id", str(company_id))' in corpo


# =============================================================================
# ⑥ o Claude Code lê as notas de um dia numa query
# =============================================================================

def test_existe_indice_para_a_leitura_do_DIA():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ix_notas_atendente_dia" in sql
    assert "(company_id, created_at DESC)" in sql


def test_a_gravacao_NUNCA_levanta():
    """⛔ A nota é o item menos crítico do caminho; ela não pode ser quem quebra
    o atendimento."""
    fonte = (RAIZ / "app" / "services" / "a_nota_da_atendente.py").read_text("utf-8")
    corpo = fonte.split("async def gravar_nota", 1)[1].split("\nasync def ", 1)[0]
    assert "except Exception" in corpo
    assert "return False" in corpo
    assert "raise" not in "#".join(l.split("#", 1)[0] for l in corpo.splitlines())


def test_o_texto_nem_o_telefone_aparecem_em_LOG():
    """⛔ A trava do Founder: nunca imprimir telefone nem conteúdo.

    🔴 **A primeira versão deste guarda não pegava a mutação óbvia.** Ela
    procurava `{texto` e a mutação escrevia `{linha['texto']}` — a mesma família
    do defeito que apareceu três vezes nesta SPEC: o guarda mede uma forma
    específica em vez da propriedade.

    ⚠️ Agora a regra é a propriedade: **nenhum `logger` interpola um nome que
    carrega conteúdo**, escrito de qualquer jeito.
    """
    fonte = (RAIZ / "app" / "services" / "a_nota_da_atendente.py").read_text("utf-8")
    perigosos = ("texto", "autor_telefone", "mensagem", "corpo", "mascarado",
                 "texto_bruto", "phone", "telefone")
    for chamada in re.findall(r"logger\.\w+\((?:[^()]|\([^()]*\))*\)", fonte):
        # ⛔ f-string em log é proibido aqui: ela interpola ANTES de o logger
        #    decidir se vai emitir, e é como o conteúdo escapa.
        if re.search(r'logger\.\w+\(\s*f["\']', chamada):
            raise AssertionError(
                f"f-string dentro de logger — ela interpola sempre: {chamada[:100]}")
        # nenhum nome perigoso aparece como argumento OU dentro de chaves
        dentro_de_chaves = re.findall(r"\{([^{}]*)\}", chamada)
        argumentos = chamada.split("(", 1)[1]
        for nome in perigosos:
            for pedaco in dentro_de_chaves:
                assert nome not in pedaco, (
                    f"vaza `{nome}` interpolado em: {chamada[:100]}")
            assert not re.search(rf"[,(]\s*{nome}\s*[,)\[]", argumentos), (
                f"vaza `{nome}` como argumento em: {chamada[:100]}")


def test_CONTROLE_o_guarda_de_LOG_consegue_flagrar_um_vazamento():
    """§9.3 — *"prove que as duas coisas CONSEGUEM ser diferentes"*.

    📊 A bateria de mutação pegou este guarda VERDE na primeira rodada. Sem esta
    linha, ele voltaria a ser um `assert` que nunca falha e ninguém veria.
    """
    import re as _re

    def _o_guarda_reprova(fonte: str) -> bool:
        perigosos = ("texto", "autor_telefone", "mensagem")
        for chamada in _re.findall(r"logger\.\w+\((?:[^()]|\([^()]*\))*\)", fonte):
            if _re.search(r'logger\.\w+\(\s*f["\']', chamada):
                return True
            for pedaco in _re.findall(r"\{([^{}]*)\}", chamada):
                if any(n in pedaco for n in perigosos):
                    return True
            argumentos = chamada.split("(", 1)[1]
            if any(_re.search(rf"[,(]\s*{n}\s*[,)\[]", argumentos) for n in perigosos):
                return True
        return False

    # 🔴 as três formas de vazar, e o guarda tem de pegar as TRÊS
    assert _o_guarda_reprova('logger.info(f"[NOTA] {linha[\'texto\']}")'), (
        "não pega a f-string — é exatamente a mutação que ficou verde")
    assert _o_guarda_reprova('logger.info("[NOTA] %s", texto)'), (
        "não pega o argumento posicional")
    assert _o_guarda_reprova('logger.warning("x {texto}")'), (
        "não pega a chave direta")
    # e a linha de controle: um log honesto PASSA
    assert not _o_guarda_reprova(
        'logger.info("[NOTA] registrada origem=%s", linha["origem"])'), (
        "o guarda reprova log honesto — ele viraria ruído e alguém o desligaria")


# ===========================================================================
# 🔴 OS CONTROLES QUE DAO DIREITO AS CONCLUSOES ACIMA
# ===========================================================================

def test_CONTROLE_o_cortador_de_comentario_realmente_corta():
    """§9.3 — se `_so_o_codigo` devolvesse a fonte intocada, o teste de ordem
    do gate ② voltaria a ler o comentário e ninguém notaria.

    ⚠️ E o TAMANHO tem de ser preservado: um corte que encurta bagunçaria
    exatamente a comparação de posição que aquele teste faz.
    """
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    limpo = _so_o_codigo(fonte)

    assert len(limpo) == len(fonte), (
        f"o corte mudou o tamanho ({len(fonte)} -> {len(limpo)}) — as posições "
        "deixam de apontar para o arquivo real")
    assert limpo != fonte, "o cortador não cortou NADA"

    # 🔴 a frase exata que enganou o guarda some, e o código fica
    enganosa = "# chama `whatsapp_service.send_message` logo abaixo"
    assert enganosa in fonte, "a frase-sentinela sumiu do arquivo — troque-a"
    assert enganosa not in limpo, (
        "o comentário que causou o defeito sobreviveu ao corte")
    assert "success = whatsapp_service.send_message(payload.phone" in limpo, (
        "o cortador comeu CÓDIGO de verdade — ele está cortando demais")


def test_CONTROLE_o_cortador_tambem_apaga_DOCSTRING():
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    limpo = _so_o_codigo(fonte)
    alvo = "o produto é o remetente"
    assert alvo in fonte and alvo not in limpo


# ===========================================================================
# 🔴 ② DE EXECUÇÃO — a SPEC manda CONTAR, não ler código
# ===========================================================================

class _BancoQueAnota:
    """Um Supabase de mentira que ANOTA toda tabela tocada.

    🔴 É assim que o gate ② vira medição em vez de leitura: se o gravador
    encostar em `platform_sends`, ou em qualquer coisa que envie, aparece aqui.
    """

    def __init__(self):
        self.tocou = []
        self.inseriu = []
        self.client = self

    def table(self, nome):
        self.tocou.append(nome)
        self._tabela = nome
        return self

    def insert(self, linha):
        self.inseriu.append((self._tabela, linha))
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    async def execute(self):
        class R:
            data = []
        return R()


def test_EXECUTANDO_o_gravador_nao_encosta_em_NADA_que_envie():
    """🔴 Gate ②: *"o teste conta `platform_sends` — não confia em leitura
    de código"*.

    ⚠️ Este teste EXECUTA `gravar_nota` e olha o que ela tocou. Um `import`
    escondido, uma chamada dentro de um `except`, um caminho que o `grep` não
    veria — tudo apareceria aqui.
    """
    import asyncio

    banco = _BancoQueAnota()
    with _com_o_pacote_app():
        gravou, motivo = asyncio.run(NOTA.gravar_nota(
            banco, company_id="empresa-1", origem="painel",
            texto_bruto="#nota o robô pediu o CPF 123.456.789-00 duas vezes"))

    assert gravou is True, f"não gravou: {motivo}"
    assert banco.tocou == ["notas_da_atendente"], (
        f"o gravador tocou em {banco.tocou} — só pode tocar na tabela da nota")
    assert len(banco.inseriu) == 1
    tabela, linha = banco.inseriu[0]
    assert tabela == "notas_da_atendente"
    assert linha["company_id"] == "empresa-1"     # 🔴 §7
    assert linha["origem"] == "painel"
    assert "123.456.789-00" not in linha["texto"], "o CPF foi gravado CRU"


def test_CONTROLE_o_banco_de_mentira_CONSEGUE_flagrar_um_envio():
    """§9.3 — prove que o detector detecta.

    ⛔ Sem esta linha, um `_BancoQueAnota` que nunca registrasse nada faria o
    teste acima passar por vacuidade — `[] == ["notas_da_atendente"]` falharia,
    mas um `tocou` que sempre devolvesse a lista certa, não.
    """
    import asyncio

    banco = _BancoQueAnota()

    async def _finge_um_envio():
        await banco.client.table("platform_sends").insert({"x": 1}).execute()

    asyncio.run(_finge_um_envio())
    assert "platform_sends" in banco.tocou, (
        "o banco de mentira NÃO flagra um envio — o teste acima não prova nada")


def test_EXECUTANDO_uma_mensagem_NORMAL_nao_grava_nota_nenhuma():
    """A linha de controle do gravador: sem prefixo, nada acontece."""
    import asyncio

    banco = _BancoQueAnota()
    with _com_o_pacote_app():
        gravou, motivo = asyncio.run(NOTA.gravar_nota(
            banco, company_id="empresa-1", origem="painel",
            texto_bruto="Bom dia, já estou vendo seu caso"))
    assert gravou is False
    assert banco.inseriu == [], "gravou uma nota a partir de mensagem normal"
