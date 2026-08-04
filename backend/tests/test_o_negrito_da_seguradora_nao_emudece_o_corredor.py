"""O negrito do WhatsApp não emudece o corredor.

📊 03/08/2026. A URA da seguradora negrita o que quer destacar — `*Digite o
CPF*`, `*1* - Guincho`, `*PLACA*`. O corredor casa âncoras contra o texto
recebido. Medido varrendo `_PLAYBOOKS`: **272 das 426 ocorrências de âncora**
quebravam com uma única palavra em negrito. O corredor não errava — ele
emudecia, com o cronômetro da URA correndo.

O conserto que NÃO fecha a classe já existia: `\\*?` espalhado por 43 padrões
(`digite o \\*?cpf\\*? ou \\*?cnpj\\*?`). Ele blinda as palavras que alguém
lembrou de blindar. Negritar `*Digite*` em vez de `*CPF*` quebra de novo — e
esse é o caso 3 aqui embaixo, que é a prova de que o remendo era remendo.

O conserto que fecha: `_norm()` tira o `*` do TEXTO. Toda âncora, a de hoje e a
que nascer amanhã, passa a ser imune sem ninguém lembrar de nada.

E as três coisas que este teste tem de provar, não afirmar:

  1. o `\\*?` que já existe **continua casando** texto sem asterisco
     (senão o conserto trocaria 272 âncoras quebradas por 43 outras);
  2. o `*` some, mas o `_` **NÃO** — `normalize_insurer_key` depende de
     `tokio_marine` virar `tokio marine` para casar `\\btokio\\b`;
  3. nada que NÃO devia casar passou a casar — em especial o falso freio da
     Bradesco: *"envie a assistência agora ou prefere agendar"* é COLETA no meio
     do fluxo, não confirmação de abertura.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def _carregar(rel: str, nome: str):
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    for pkg in ("app", "app.services"):
        if pkg not in sys.modules:
            casca = types.ModuleType(pkg)
            casca.__path__ = [str(RAIZ / pkg.replace(".", "/"))]  # type: ignore[attr-defined]
            sys.modules[pkg] = casca
    spec = importlib.util.spec_from_file_location(nome, RAIZ / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


PB = _carregar("app/services/corridor_playbooks.py", "cp_negrito")


def _texto_de(padrao: str) -> str:
    """Desfaz as construções de regex e devolve um texto plano que o padrão casa.

    Serve para varrer o acervo inteiro sem escrever 400 frases à mão. O texto
    que sai NÃO tem asterisco — e é por isso que ele também prova a metade
    delicada do conserto: o `\\*?` casando zero vezes.
    """
    s = padrao.split("|")[0]
    s = re.sub(r"\(\?:[^()]*?\)\?", "", s)          # grupo opcional inteiro
    s = re.sub(r"\[([a-z\u00e0-\u00ff])[^\]]*\]", r"\1", s)  # [úu] -> u
    s = s.replace(r"\s*", " ").replace(r"\s+", " ").replace(r"\s", " ")
    s = s.replace(".*?", " ").replace(".*", " ").replace(".+", "x")
    s = re.sub(r"\\d\{[\d,]+\}", "123456", s)
    s = s.replace(r"\d+", "123456").replace(r"\d", "1")
    s = re.sub(r"\\[bWwSs]|\\", "", s)
    s = s.replace("*?", "").replace("?", "").replace("+", "")
    s = re.sub(r"[()\[\]^$]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _negritar(t: str) -> str:
    """Negrita a PRIMEIRA palavra de 4+ letras — o que a URA faz o tempo todo."""
    return re.sub(r"\b([a-z\u00e0-\u00ff]{4,})\b", r"*\1*", t, count=1, flags=re.IGNORECASE)


def _ancoras_de_texto() -> list[tuple[str, str, str]]:
    """(playbook_ref, tipo, padrão) de TODA âncora que casa texto de seguradora.

    `tracking_link` fica de fora de propósito: `extract_capture_anchors` o casa
    contra a mensagem ORIGINAL (URL preserva caixa), não contra o normalizado.
    """
    fora = []
    for ref, pb in PB._PLAYBOOKS.items():
        for st in pb.get("ura_steps") or []:
            if st.get("anchor"):
                fora.append((ref, f"ura:{st.get('step')}", st["anchor"]))
        for p in pb.get("finalize_anchors") or []:
            fora.append((ref, "finalize", p))
        for p in pb.get("handoff_triggers") or []:
            fora.append((ref, "handoff", p))
        for k, v in (pb.get("capture_anchors") or {}).items():
            if v and k != "tracking_link":
                fora.append((ref, f"capture:{k}", v))
        for fl in (pb.get("native_flows") or {}).values():
            if fl.get("prompt_anchor"):
                fora.append((ref, "flow", fl["prompt_anchor"]))
    return fora


def o_asterisco_sai_do_texto() -> None:
    checar(PB._norm("*Digite o CPF*") == "digite o cpf",
           "o `*` do negrito some na normalizacao")
    checar(PB._norm("Ol\u00e1, *N\u00daMERO*?") == "ola, numero?",
           "e o acento continua saindo junto (NFKD nao foi perdido)")


def o_underline_e_o_traco_ficam() -> None:
    """A regra tem LIMITE, e o limite protege a chave da seguradora."""
    checar("_" in PB._norm("tokio_marine"),
           "o `_` (italico do WhatsApp) NAO sai",
           "sem ele, `normalize_insurer_key` nao separa tokio_marine e a chave se funde")
    checar(PB.normalize_insurer_key("tokio_marine") == "tokio",
           "e a prova de que isso importa: tokio_marine ainda resolve para `tokio`")
    checar(PB.normalize_insurer_key("Tokio Marine") == "tokio",
           "assim como a forma com espaco")


def o_ancoras_sem_blindagem_passam_a_casar() -> None:
    """O caso que motivou tudo: âncora SEM `\\*?` casando texto negritado."""
    porto = PB.get_playbook("porto-auto-whatsapp@v1") or {}
    alvos = [
        ("allianz-residencial-whatsapp@v1",
         "*Assist\u00eancia 24h para qual seguro* voc\u00ea precisa?",
         "menu_tipo_seguro"),
        ("allianz-residencial-whatsapp@v1",
         "*Confirme o endere\u00e7o para atendimento*",
         "confirmar_endereco"),
    ]
    for ref, texto, passo in alvos:
        pb = PB.get_playbook(ref) or {}
        step = PB.match_ura_step(pb, texto)
        checar(step is not None and step.get("step") == passo,
               f"ancora SEM blindagem casa texto negritado: {passo}",
               f"casou: {step and step.get('step')}")
    checar(bool(porto), "o playbook da porto existe (o caso nao e so allianz)")


def o_remendo_pontual_nao_fechava_a_classe() -> None:
    """A prova de que `\\*?` era remendo: negritar OUTRA palavra quebrava igual.

    `digite o \\*?cpf\\*? ou \\*?cnpj\\*?` blinda exatamente `*CPF*` e `*CNPJ*` —
    as duas palavras que alguém lembrou de blindar. A URA que negrita o VERBO
    passava direto por ele.

    📊 Medido nas quatro posições possíveis de negrito nesta frase: só uma
    reprovava o código antigo, e é justamente a que ninguém previu.
    """
    pb = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    padrao = r"digite o \*?cpf\*? ou \*?cnpj\*?"

    def _norm_antigo(t: str) -> str:
        """O `_norm` de ontem: NFKD e minúscula, sem tirar o `*`."""
        import unicodedata
        n = unicodedata.normalize("NFKD", str(t or ""))
        return "".join(c for c in n if not unicodedata.combining(c)).lower()

    # A palavra que o autor da ancora blindou: o remendo AGUENTA.
    blindada = "Digite o *CPF* ou *CNPJ* do titular"
    checar(bool(re.search(padrao, _norm_antigo(blindada), re.IGNORECASE)),
           "o remendo `\\*?cpf\\*?` aguenta a palavra que ele previu (*CPF*)",
           "se nem isso funcionasse, o remendo nunca teria sido escrito")

    # A palavra que ele NAO blindou: o remendo CAI. Este e o guarda com como falhar.
    imprevista = "*Digite* o CPF ou CNPJ do titular"
    checar(not re.search(padrao, _norm_antigo(imprevista), re.IGNORECASE),
           "e CAI na palavra que ele nao previu (*Digite*) — o codigo ANTIGO reprova",
           "se isto passar, o teste nao tem como falhar e nao prova nada")
    checar(bool(re.search(padrao, PB._norm(imprevista), re.IGNORECASE)),
           "o codigo NOVO casa a mesma frase")
    step = PB.match_ura_step(pb, imprevista)
    checar(step is not None and step.get("step") == "pedir_cpf",
           "e pelo motor de verdade o passo volta a ser `pedir_cpf`",
           f"casou: {step and step.get('step')}")


def o_blindado_continua_casando_texto_limpo() -> None:
    """O risco do conserto: trocar 272 âncoras quebradas por 43 outras.

    `\\*?` é opcional, então texto SEM asterisco continua casando — mas isso é
    dedução, e dedução não é prova. Aqui as 43 rodam de verdade contra um texto
    plano, que é exatamente o que `_norm` passa a entregar.
    """
    com_blindagem = [(ref, tipo, p) for ref, tipo, p in _ancoras_de_texto() if r"\*" in p]
    checar(len(com_blindagem) >= 40,
           f"a varredura achou as ancoras blindadas ({len(com_blindagem)} ocorrencias)",
           "se isto zerar, o teste seguinte nao esta olhando nada")

    # Nenhuma delas pode EXIGIR o asterisco (`\*` sem `?` depois): se exigisse,
    # tirar o `*` do texto a mataria, e o conserto teria efeito colateral.
    exigem = []
    for ref, tipo, p in com_blindagem:
        for m in re.finditer(r"\\\*", p):
            if p[m.end():m.end() + 1] not in ("?", "*", "{"):
                exigem.append((ref, tipo, p))
    checar(not exigem,
           "NENHUMA ancora EXIGE o asterisco — todas usam `\\*?`",
           f"exigiriam: {exigem[:3]}")

    # E cada uma casa texto PLANO exatamente como casaria SEM a blindagem.
    #
    # Comparacao DIFERENCIAL, com linha de controle (CLAUDE.md 9.2): para cada
    # padrao P, monta-se P0 = P sem os `\*?`, e a mesma sonda vai nos dois. A
    # conclusao so vale quando P0 casa — se P0 nao casa, quem falhou foi o
    # gerador de sonda, nao o produto, e o caso e PULADO em vez de acusado.
    quebradas = []
    provadas = 0
    pulados = []
    for ref, tipo, p in com_blindagem:
        p0 = p.replace(r"\*?", "")
        sonda = PB._norm(_texto_de(p0))
        if len(sonda) < 4:
            pulados.append((tipo, "sonda curta"))
            continue
        try:
            controle = bool(re.search(p0, sonda, re.IGNORECASE | re.DOTALL))
            real = bool(re.search(p, sonda, re.IGNORECASE | re.DOTALL))
        except re.error as exc:
            quebradas.append((tipo, f"REGEX INVALIDO: {exc}", p))
            continue
        if not controle:
            pulados.append((tipo, "a sonda nao representa nem o padrao SEM blindagem"))
            continue
        if real:
            provadas += 1
        else:
            quebradas.append((tipo, p, sonda))
    checar(provadas >= 40,
           f"{provadas} ancoras blindadas foram provadas contra texto plano "
           f"({len(pulados)} puladas por sonda ruim)",
           "amostra pequena demais nao autoriza a conclusao")
    checar(not quebradas,
           "e o `\\*?` casa ZERO vezes: a blindagem nao muda o resultado em texto plano",
           f"quebraram: {quebradas[:3]}")


def as_frases_reais_da_ura_casam_nas_duas_formas() -> None:
    """A prova que não depende de gerador nenhum: frase de URA escrita à mão.

    Cada uma tem uma âncora BLINDADA (`\\*?`) do outro lado — o lugar onde um
    conserto mal feito trocaria 272 quebras por 43 novas. As duas formas, limpa
    e negritada, precisam cair no MESMO passo.
    """
    casos = [
        ("allianz-residencial-whatsapp@v1", "pedir_cpf",
         "Digite o CPF ou CNPJ do titular da apólice",
         "Digite o *CPF* ou *CNPJ* do titular da apólice"),
        ("allianz-residencial-whatsapp@v1", "pedir_cpf",
         "Digite o CPF ou CNPJ do titular da apólice",
         "*Digite o CPF ou CNPJ* do titular da apólice"),
        ("bradesco-auto-whatsapp@v1", "informar_placa",
         "Me informa a placa do veículo, por favor",
         "Me informa a *placa do veículo*, por favor"),
        ("bradesco-auto-whatsapp@v1", "cpf_fallback",
         "Digite somente os números do CPF ou CNPJ",
         "Digite somente os números do *CPF* ou *CNPJ*"),
    ]
    for ref, esperado, limpo, negrito in casos:
        pb = PB.get_playbook(ref) or {}
        a = PB.match_ura_step(pb, limpo)
        b = PB.match_ura_step(pb, negrito)
        checar(a is not None and a.get("step") == esperado,
               f"[{ref.split('-')[0]}] texto LIMPO cai em `{esperado}`",
               f"caiu em: {a and a.get('step')}")
        checar(b is not None and b.get("step") == esperado,
               f"[{ref.split('-')[0]}] e o MESMO texto negritado tambem",
               f"caiu em: {b and b.get('step')}")


def a_classe_inteira_fecha() -> None:
    """Varre TODA âncora: negritar uma palavra não pode mais mudar o resultado."""
    ancoras = _ancoras_de_texto()
    checar(len(ancoras) >= 300,
           f"a varredura enxerga o acervo inteiro ({len(ancoras)} ocorrencias)")

    # Para cada ancora, um texto que ela casa; depois o MESMO texto negritado.
    testadas = 0
    quebram = []
    for ref, tipo, p in ancoras:
        base = _texto_de(p)
        if len(base) < 4:
            continue
        try:
            if not re.search(p, PB._norm(base), re.IGNORECASE | re.DOTALL):
                continue  # a sonda nao representa o padrao; nao conta
        except re.error:
            continue
        negrito = _negritar(base)
        if negrito == base:
            continue
        testadas += 1
        if not re.search(p, PB._norm(negrito), re.IGNORECASE | re.DOTALL):
            quebram.append((ref, tipo, p, negrito))

    checar(testadas >= 200,
           f"{testadas} ocorrencias de ancora foram testadas com negrito de verdade",
           "amostra pequena demais nao autoriza a conclusao")
    checar(not quebram,
           "NENHUMA ancora quebra com negrito",
           f"quebraram {len(quebram)}: {[(q[1], q[3][:40]) for q in quebram[:3]]}")


def o_falso_freio_da_bradesco_continua_falso() -> None:
    """O controle negativo: tirar o `*` não pode fazer casar o que não devia.

    *"envie a assistência agora ou prefere agendar"* é COLETA no meio do fluxo da
    Bradesco (urgência), não confirmação de abertura. Se ela virasse freio, todo
    acionamento da Bradesco pararia pedindo aprovação humana no meio da coleta.
    """
    br = PB.get_playbook("bradesco-auto-whatsapp@v1") or {}
    checar(bool(br), "o playbook da bradesco carregou")

    coleta = "E como prefere fazer, quer que *envie a assist\u00eancia agora ou prefere agendar*?"
    checar(PB.detect_finalize_anchor(br, coleta) is None,
           "'envie a assistencia agora ou prefere agendar' NEGRITADA nao e freio",
           f"freou em: {PB.detect_finalize_anchor(br, coleta)}")
    passo = PB.match_ura_step(br, coleta)
    checar(passo is not None and passo.get("step") == "quando",
           "ela e o passo de COLETA `quando` — e agora casa mesmo negritada",
           f"casou: {passo and passo.get('step')}")

    freio = "Origem e Destino conferidos. *Posso confirmar a abertura* da assist\u00eancia?"
    checar(PB.detect_finalize_anchor(br, freio) is not None,
           "e o freio DE VERDADE continua freando, tambem em negrito")


def nao_casa_texto_neutro() -> None:
    """Um `_norm` que devolvesse vazio, ou um match que casasse tudo, passaria
    em todos os checks de cima. Aqui o guarda precisa RECUSAR."""
    pb = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    neutros = [
        "*Bom dia!* Como vai?",
        "*Obrigado* pelo contato.",
        "Seu atendimento foi *finalizado*. At\u00e9 logo!",
    ]
    for t in neutros:
        step = PB.match_ura_step(pb, t)
        checar(step is None, f"texto neutro negritado NAO casa passo: {t[:34]}\u2026",
               f"casou indevidamente: {step and step.get('step')}")
    checar(PB._norm("***") == "", "e a normalizacao de so-asteriscos e vazia, nao um coringa")


def o_motor_de_dispatch_usa_a_mesma_norma() -> None:
    """`insurer_dispatch_service._norm_text` era uma CÓPIA de `_norm`.

    Cópia de normalizador é onde o conserto de um lado deixa o outro quebrado:
    ali moram o padrão de `insurer_closed`, o de pesquisa de satisfação, o de
    "me chamo X" e a leitura dos `finalize_anchors` em `pergunta_de_decisao`.
    """
    fonte = (RAIZ / "app/services/insurer_dispatch_service.py").read_text(encoding="utf-8")
    checar("unicodedata.normalize(\"NFKD\"" not in fonte,
           "a copia literal de `_norm` SAIU do motor de dispatch",
           "duas normalizacoes = o proximo conserto so pega metade do produto")
    checar("_norm as _norm_corredor" in fonte and "return _norm_corredor(text)" in fonte,
           "e `_norm_text` delega para a definicao unica do corredor")


def main() -> int:
    print(__doc__)
    print("== o asterisco sai do texto ==")
    o_asterisco_sai_do_texto()
    print("== e o `_` e o `-` ficam (a regra tem limite) ==")
    o_underline_e_o_traco_ficam()
    print("== ancora sem blindagem passa a casar negrito ==")
    o_ancoras_sem_blindagem_passam_a_casar()
    print("== o remendo pontual nao fechava a classe ==")
    o_remendo_pontual_nao_fechava_a_classe()
    print("== e o blindado continua casando texto limpo ==")
    o_blindado_continua_casando_texto_limpo()
    print("== frases reais da URA, nas duas formas ==")
    as_frases_reais_da_ura_casam_nas_duas_formas()
    print("== a classe inteira fecha ==")
    a_classe_inteira_fecha()
    print("== controle negativo: o falso freio da bradesco continua falso ==")
    o_falso_freio_da_bradesco_continua_falso()
    print("== e texto neutro continua sem casar ==")
    nao_casa_texto_neutro()
    print("== o motor de dispatch usa a MESMA norma ==")
    o_motor_de_dispatch_usa_a_mesma_norma()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O NEGRITO DA SEGURADORA NAO EMUDECE MAIS O CORREDOR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
