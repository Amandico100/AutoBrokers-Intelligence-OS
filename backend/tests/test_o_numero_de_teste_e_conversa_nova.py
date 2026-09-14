"""Os números de teste do piloto ficam FORA da janela e da pausa (Founder, 10/09/2026)."""
import asyncio, os, sys
sys.path.insert(0, ".")
from app.services import o_fim_do_atendimento as M

def _porta(conversa, env):
    old = os.environ.get(M._ENV_EXCECOES_DA_JANELA)
    os.environ[M._ENV_EXCECOES_DA_JANELA] = env
    try:
        return asyncio.run(M.a_ia_deve_calar(None, company_id="c1", conversa=conversa, companhia={}))
    finally:
        if old is None: os.environ.pop(M._ENV_EXCECOES_DA_JANELA, None)
        else: os.environ[M._ENV_EXCECOES_DA_JANELA] = old

def test_excecao_nao_fura_o_takeover_mas_fura_a_janela():
    """§9.3 — migrado em 14/09/2026 pela SPEC-EXTRA-001.2 (BLOCO E, ordem do silêncio:
    corretora → pausa/takeover → exceção SÓ para a janela → janela). Até 14/09 este teste
    afirmava que o número de teste FALAVA mesmo com a conversa assumida — era o "robô falava
    por cima da atendente" (P-PILOTO-15). Hoje: assumida → CALA, com ou sem exceção; e a
    exceção continua servindo para o que ela existe: pular a janela de N dias."""
    conv = {"id": "x", "user_phone": "5548911112222", "status": "HUMAN_REQUESTED", "claimed_by": "u1"}
    calar, motivo = _porta(conv, "48911112222, 47933334444")
    assert calar is True, (calar, motivo)
    # CONTROLE: fora da lista, a MESMA conversa também cala (o takeover não depende da lista)
    calar2, _ = _porta(conv, "47933334444")
    assert calar2 is True
    # PAR: sem takeover, o número de teste continua pulando a janela (db=None não é lido)
    aberta = {"id": "y", "user_phone": "5548911112222", "status": "active"}
    calar3, motivo3 = _porta(aberta, "48911112222")
    assert calar3 is False, (calar3, motivo3)

def test_variantes_do_nono_digito_e_do_55():
    assert M.telefone_e_excecao_da_janela("5548911112222", "4811112222")
    assert M.telefone_e_excecao_da_janela("4811112222", "5548911112222")
    assert not M.telefone_e_excecao_da_janela("5548911112222", "")
    assert not M.telefone_e_excecao_da_janela("", "48911112222")

if __name__ == "__main__":
    test_excecao_fala_mesmo_assumida(); test_variantes_do_nono_digito_e_do_55(); print("VERDE")
