# -*- coding: utf-8 -*-
"""O TEXTO que o corretor lê no chat — SPEC-132-B §4 "A resposta pronta".

    onde_calcula(decisao)      "no seu Agger" / "no Agger da corretora (você ainda não conectou o seu)"
    frase_calculando(onde)     a resposta IMEDIATA do disparo ("… volto aqui em 1 a 2 minutos")
    texto_pronto(...)          "Pronto: N seguradoras responderam." + a tabela de 3 linhas + o link + a mensagem
    texto_sem_resposta(...)    nenhuma seguradora respondeu — frase honesta
    texto_nao_terminou()       o run desistiu — frase honesta
    sem_documento_inteiro(t)   o cinto: nenhum CPF/CNPJ inteiro sai daqui (mutação 7)

⛔ Número que aparece aqui vem do BANCO (as ofertas que a porta devolve) ou da publicação — nunca de constante.
⛔ "1 a 2 minutos": 📊 LAUDO-I1 (SPEC-132-B §2.1 C7) — 1ª oferta em 6 s, 80 % em 27 s, fecha em 64 s; p90 406 s. A
   promessa é a do meio; o corte do run (`workflow.TETO_S`) é 💭 6 min, com o que chegou.
⛔ O número de seguradoras ANTES do cálculo não é sabido (depende do que está habilitado em cada conta do Agger) — a
   frase do disparo não inventa N (D-132B-02); o N da resposta é o das que RESPONDERAM, contado nas ofertas.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

PROMESSA = "volto aqui com o resultado em 1 a 2 minutos"

#: a frase em 2ª pessoa para cada motivo que `qual_agger` escreve quando a cotação vai ao Agger da CORRETORA.
#: 🔴 O acoplamento é com os TEXTOS de `qual_agger._decidir` (ramo cotação): `test_spec132b_a_conversa` passa pelas
#: quatro situações com o `qual_agger` REAL — se o texto mudar lá, o teste fica vermelho aqui.
_POR_QUE_NAO_O_SEU = (
    ("ainda não tem o próprio agger", "você ainda não conectou o seu"),
    ("desconectado", "o seu está desconectado"),
    ("recusou a senha", "o seu recusou a senha — troque a senha dele em Conexões"),
    ("pausado", "o seu está pausado"),
    ("não está ativo", "o seu acesso não está ativo nesta corretora"),
    ("não sei quem pediu", "não consegui saber quem pediu"),
)


def por_que_nao_o_seu(motivo: Any) -> str:
    m = str(motivo or "").lower()
    for chave, frase in _POR_QUE_NAO_O_SEU:
        if chave in m:
            return frase
    return "o seu não está disponível agora"


def onde_calcula(decisao: Any) -> str:
    """A `DecisaoDeConta` (de `qual_agger.decidir`, ramo cotação) em português de gente."""
    if decisao is None:
        return "no Agger da corretora"
    if getattr(decisao, "regra", "") == "cotacao_da_pessoa":
        return "no seu Agger"
    return f"no Agger da corretora ({por_que_nao_o_seu(getattr(decisao, 'motivo', ''))})"


def onde_pelas_contas(contas: Sequence[Mapping[str, Any]]) -> str:
    """O mesmo, lido do que a PORTA gravou (`multicalculo_calculos.conta_regra`/`conta_motivo`) — o ELO da SPEC: a
    frase sai da conta USADA, nunca do que se esperava usar."""
    regras = [str(c.get("conta_regra") or "") for c in contas or ()]
    if regras and all(r == "cotacao_da_pessoa" for r in regras):
        return "no seu Agger"
    motivo = next((c.get("conta_motivo") for c in contas or () if c.get("conta_regra") != "cotacao_da_pessoa"), "")
    return f"no Agger da corretora ({por_que_nao_o_seu(motivo)})"


def frase_calculando(onde: str, *, ajuste: Optional[str] = None) -> str:
    if ajuste:
        return f"Recalculando com {ajuste} {onde} — {PROMESSA}."
    return f"Calculando nas seguradoras {onde} — {PROMESSA}. Pode seguir conversando."


# =====================================================================================================================
# a resposta pronta
# =====================================================================================================================
def _reais(v: Any) -> str:
    from app.providers.policy_data_provider import reais

    try:
        return reais(v) if v is not None else "—"
    except Exception:  # noqa: BLE001
        return "—"


def seguradoras_que_responderam(ofertas: Iterable[Mapping[str, Any]]) -> int:
    """Quantas SEGURADORAS deram preço (as ofertas com prêmio > 0, por seguradora) — contado no banco."""
    nomes = set()
    for o in ofertas or ():
        try:
            if float(o.get("premio_total") or 0) > 0:
                nomes.add(str(o.get("seguradora_codigo") or o.get("seguradora") or "").strip().lower())
        except (TypeError, ValueError):
            continue
    nomes.discard("")
    return len(nomes)


def _linha(rotulo: str, o: Mapping[str, Any]) -> str:
    parc = o.get("parcelas") if isinstance(o.get("parcelas"), Mapping) else {}
    parcela = f"{int(parc['vezes'])}x {_reais(parc.get('valor'))}" if parc.get("vezes") and parc.get("valor") else "—"
    fr = o.get("franquia") if isinstance(o.get("franquia"), Mapping) else {"valor": o.get("franquia")}
    a_vista = o.get("a_vista") if o.get("a_vista") is not None else o.get("premio_anual")
    return f"| {rotulo} | {o.get('seguradora') or '—'} | {parcela} | {_reais(a_vista)} | {_reais(fr.get('valor'))} |"


ROTULO_DA_LINHA = {"recomendada": "Recomendada", "mais_em_conta": "Mais em conta", "mais_completa": "Mais completa"}


def tabela(opcoes: Sequence[Mapping[str, Any]]) -> str:
    """As 3 linhas (Recomendada · Mais em conta · Mais completa), na ordem da página. Opção que não veio não aparece."""
    por_id = {str(o.get("id") or ""): o for o in opcoes or () if isinstance(o, Mapping)}
    linhas = [_linha(rot, por_id[i]) for i, rot in ROTULO_DA_LINHA.items() if i in por_id]
    if not linhas:
        return ""
    return "\n".join(["| | Seguradora | Parcela | À vista | Franquia |", "|---|---|---|---|---|", *linhas])


def texto_pronto(*, responderam: int, opcoes: Sequence[Mapping[str, Any]], link: Optional[str],
                 mensagem_para_o_cliente: Optional[str], aviso_da_conta: Optional[str] = None,
                 ajuste: Optional[str] = None) -> str:
    partes = [f"Pronto: {responderam} seguradora{'s' if responderam != 1 else ''} "
              f"respondera{'m' if responderam != 1 else ''}." + (f" (Recalculado com {ajuste}.)" if ajuste else "")]
    t = tabela(opcoes)
    if t:
        partes.append(t)
    if link:
        partes.append(f"Apresentação para o cliente: {link}")
    if mensagem_para_o_cliente:
        corpo = "\n".join(f"> {l}" if l.strip() else ">" for l in str(mensagem_para_o_cliente).strip().splitlines())
        partes.append("**Mensagem para o cliente** (é só copiar e mandar):\n" + corpo)
    if aviso_da_conta:
        partes.append(aviso_da_conta)
    return sem_documento_inteiro("\n\n".join(partes))


def aviso_da_conta(onde: str) -> Optional[str]:
    """Na resposta, só quando o cálculo NÃO saiu no Agger de quem pediu."""
    if onde == "no seu Agger":
        return None
    return f"Calculei {onde}. Para as próximas saírem no seu, conecte o seu Agger em Meu perfil."


def texto_sem_resposta(*, aviso: Optional[str] = None) -> str:
    base = ("Nenhuma seguradora respondeu com preço desta vez. Isso acontece quando elas estão fora do ar ou pedem uma "
            "análise a mais do perfil. Você pode abrir o cálculo no Agger para ver o motivo de cada uma, ou me pedir "
            "para tentar de novo daqui a pouco.")
    return sem_documento_inteiro(base + (f"\n\n{aviso}" if aviso else ""))


def texto_nao_terminou() -> str:
    return ("Não consegui terminar esta cotação — o problema foi do nosso lado, não dos dados. O que chegou fica em "
            "Cotação Rápida → Cotações; se quiser, me peça para calcular de novo.")


def texto_sem_publicar(*, responderam: int) -> str:
    return (f"{responderam} seguradora{'s' if responderam != 1 else ''} "
            f"respondera{'m' if responderam != 1 else ''}, mas não consegui montar a apresentação para o cliente agora. "
            "O resultado está em Cotação Rápida → Cotações e no Agger.")


# =====================================================================================================================
# o cinto — nenhum CPF/CNPJ inteiro sai desta fatia (mutação 7)
# =====================================================================================================================
_CPF = re.compile(r"(?<![\d*])(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?!\d)")
_CNPJ = re.compile(r"(?<![\d*])(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})(?!\d)")


def sem_documento_inteiro(texto: Any) -> str:
    """Todo CPF/CNPJ com dígito verificador VÁLIDO vira `***.***.***-NN` (a máscara da renovação). Os outros números
    (data, CEP, valor, telefone sem DV) ficam como vieram."""
    from app.services.cotacao.pedido_da_conversa import documento_valido
    from app.services.multicalculo.renovacao import mascarar_documento

    def _troca(m: "re.Match[str]") -> str:
        bruto = m.group(0)
        return mascarar_documento(bruto) if documento_valido(bruto) else bruto

    return _CPF.sub(_troca, _CNPJ.sub(_troca, str(texto or "")))
