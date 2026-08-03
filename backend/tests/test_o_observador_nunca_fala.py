"""O Observador escuta. Ele nunca fala — nem quando é o único que sobrou.

O defeito, medido em 02/08/2026
-------------------------------
O Observador é o número que a corretora pareia para o sistema ESCUTAR as
conversas reais dela. Ele é mudo por construção: o módulo de captura não importa
nenhum cliente de envio — é ausência de código, não uma flag.

Mas os seletores de canal de **saída** nunca olharam `purpose`::

    rank = {"auxiliary": 0, "attendance": 1}
    rows.sort(key=lambda r: rank.get(str(r.get("purpose") or ""), 2))
    return rows[0] if rows else None

`observer` caía no rank 2 — "por último". E **"por último" vira "o escolhido"
quando é o único ativo.**

📊 Em 02/08/2026, Amandus e AutoFleet tinham exatamente isso: uma única
integração ativa, e ela era o observador.

Cobrança, follow-up e alerta sairiam pelo número que existe para ficar calado.
O segurado receberia mensagem de um número que nunca falou com ele, e a
corretora perderia justamente o silêncio que pediu ao parear.

**Última prioridade não protege. Só a proibição protege.**

E o corolário que este teste também guarda: quando não há canal elegível, o
certo é **não enviar**. Uma corretora que fica sem cobrança automática por um
dia tem um problema operacional. Uma corretora cujo número mudo começou a
falar com segurados perdeu a confiança que a fez parear.
"""

from __future__ import annotations

import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


def teste_a_proibicao_existe_e_e_uma_so():
    print("\n[D1] Existe UMA proibição, num lugar só")
    fonte = _ler("backend", "app", "services", "integration_service.py")
    checar("PROPOSITOS_QUE_NUNCA_ENVIAM" in fonte, "a proibição está nomeada")
    checar('frozenset({"observer"})' in fonte,
           "e o observador está nela",
           "imutável de propósito: não é lista que alguém acrescenta em runtime")
    checar("def pode_enviar" in fonte, "há um único jeito de perguntar")


def teste_a_busca_de_plataforma_respeita():
    print("\n[D2] O canal de plataforma nunca é o observador")
    codigo = _sem_comentario(_ler("backend", "app", "services", "integration_service.py"))
    checar("if integ and self.pode_enviar(integ):" in codigo,
           "a integração encontrada é conferida antes de virar canal")
    checar("and self.pode_enviar(i)]" in codigo,
           "e o fallback da corretora também filtra")
    checar("NAO tem canal de saida" in codigo,
           "sem canal elegível, avisa alto em vez de improvisar",
           "não enviar é a resposta certa — improvisar com o mudo, não")


def teste_a_cobranca_respeita():
    print("\n[D3] A cobrança nunca sai pelo observador")
    codigo = _sem_comentario(_ler("backend", "app", "services", "billing_collection.py"))
    checar("IntegrationService.pode_enviar(r)" in codigo,
           "o observador sai da lista ANTES da ordenação",
           "ordenar não basta: o último da fila é o escolhido quando é o único")

    # A ordem importa: filtrar depois de ordenar não resolveria nada.
    pos_filtro = codigo.find("pode_enviar(r)")
    pos_sort = codigo.find("rows.sort(")
    checar(pos_filtro != -1 and pos_sort != -1 and pos_filtro < pos_sort,
           "o filtro vem antes do sort")


def teste_a_prova_funcional():
    print("\n[D4] A regra funciona quando exercitada")
    fonte = _ler("backend", "app", "services", "integration_service.py")
    ini = fonte.index("    PROPOSITOS_QUE_NUNCA_ENVIAM")
    fim = fonte.index("    def get_platform_whatsapp_integration", ini)
    ns: dict = {"Optional": object, "Dict": dict}
    exec(compile("class S:\n" + fonte[ini:fim], "<proibicao>", "exec"), ns)  # noqa: S102
    S = ns["S"]

    checar(S.pode_enviar({"purpose": "attendance"}) is True, "atendimento pode enviar")
    checar(S.pode_enviar({"purpose": "auxiliary"}) is True, "auxiliar pode enviar")
    checar(S.pode_enviar({"purpose": "observer"}) is False,
           "OBSERVADOR não pode — nunca")
    checar(S.pode_enviar({"purpose": "OBSERVER "}) is False,
           "e não escapa por maiúscula ou espaço")
    checar(S.pode_enviar(None) is False, "integração ausente também não envia")
    checar(S.pode_enviar({}) is False,
           "dicionário vazio é ausência de integração, não permissão",
           "fail-closed: 'não sei o que é isto' nunca vira canal de saída")
    # Linha legada REAL: tem dados, só não tem o rótulo `purpose` (a coluna é
    # posterior a várias integrações). Recusá-la deixaria corretoras antigas sem
    # canal por um detalhe de schema — o defeito trocaria de lugar.
    checar(S.pode_enviar({"id": "x", "provider": "evolution-go"}) is True,
           "integração legada sem rótulo continua podendo enviar")


def main() -> int:
    print("=" * 68)
    print("O OBSERVADOR ESCUTA — E NUNCA FALA")
    print("=" * 68)
    for t in (teste_a_proibicao_existe_e_e_uma_so,
              teste_a_busca_de_plataforma_respeita,
              teste_a_cobranca_respeita,
              teste_a_prova_funcional):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O NUMERO QUE FOI PAREADO PARA CALAR CONTINUA CALADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
