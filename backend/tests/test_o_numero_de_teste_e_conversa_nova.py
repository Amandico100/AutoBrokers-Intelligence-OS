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

def test_excecao_fala_mesmo_assumida():
    conv = {"id": "x", "user_phone": "5548911112222", "status": "HUMAN_REQUESTED", "claimed_by": "u1"}
    calar, _ = _porta(conv, "48911112222, 47933334444")
    assert calar is False
    # CONTROLE: fora da lista, a MESMA conversa cala
    calar2, _ = _porta(conv, "47933334444")
    assert calar2 is True

def test_variantes_do_nono_digito_e_do_55():
    assert M.telefone_e_excecao_da_janela("5548911112222", "4811112222")
    assert M.telefone_e_excecao_da_janela("4811112222", "5548911112222")
    assert not M.telefone_e_excecao_da_janela("5548911112222", "")
    assert not M.telefone_e_excecao_da_janela("", "48911112222")

if __name__ == "__main__":
    test_excecao_fala_mesmo_assumida(); test_variantes_do_nono_digito_e_do_55(); print("VERDE")
