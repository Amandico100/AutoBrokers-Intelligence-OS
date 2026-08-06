"""Um segredo que nao decifra nao e "plaintext legado" — e perda, e tem de gritar.

Rodar: python backend/tests/test_o_segredo_perdido_grita.py

A HISTORIA
----------
06/08/2026. Uma atendente da Resulta passou DIAS sem conseguir parear. A tela
dizia "A configuracao do canal esta incompleta" e mandava procurar o suporte.
Nao havia suporte a chamar: o erro nascia tres camadas antes, aqui.

`decrypt_integration_secret` tinha um `except Exception` que tratava QUALQUER
falha como "deve ser plaintext legado" e devolvia **o proprio ciphertext**.
Fail-OPEN. O blob de 188 caracteres virava `apikey`, o provedor respondia 401, e
o 401 virava `configuration_error` na tela — um erro que nao nomeia nada.

    o que aconteceu ....  a ENCRYPTION_KEY nao abriu o valor
    o que se via .......  "configuracao incompleta", tres camadas adiante

A LINHA DE CONTROLE (CLAUDE.md 9.2)
-----------------------------------
Um guarda que so soubesse gritar seria tao inutil quanto o que so sabia calar:
ele quebraria as duas linhas legadas que EXISTEM no banco e sao legitimas.

Por isso cada afirmacao vem em PAR, e o par usa as formas REAIS medidas em
producao em 06/08/2026:

    LEGADO   36 e 49 chars, nao e base64 valido    -> PASSA (e so informa)
    QUEBRADO 188 chars, Fernet v0x80 integro       -> GRITA

E o bloco 5 prova que as duas populacoes CONSEGUEM ser distinguidas — sem isso,
um guarda que devolvesse sempre o mesmo veredito passaria em metade dos casos
por acidente e ninguem saberia qual metade.
"""

import base64
import importlib.util
import logging
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FALHAS = []


def checar(nome, condicao, detalhe=None):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FALHAS.append((nome, detalhe))
        print(f"  [X] {nome}{': ' + str(detalhe) if detalhe else ''}")


# --------------------------------------------------------------------------
# Carga isolada: o modulo real, com a cripto real (Fernet de verdade), sem
# arrastar `app.core.config` nem banco nenhum. Cripto de mentira nao provaria
# nada — o defeito ERA na fronteira entre a cripto e o `except`.
# --------------------------------------------------------------------------
from cryptography.fernet import Fernet  # noqa: E402

CHAVE_A = Fernet.generate_key()          # a chave que cifrou
CHAVE_B = Fernet.generate_key()          # a chave que o container subiu com
assert CHAVE_A != CHAVE_B

for _n in ("app", "app.services", "app.services.whatsapp"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []


class _Cripto:
    """Copia fiel de EncryptionService.encrypt/decrypt — mesmo formato de saida."""

    def __init__(self, chave):
        self.cipher = Fernet(chave)

    def encrypt(self, plaintext: str) -> str:
        return base64.b64encode(self.cipher.encrypt(plaintext.encode())).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self.cipher.decrypt(base64.b64decode(ciphertext)).decode()
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Failed to decrypt: {e}") from e


_ATUAL = {"cripto": _Cripto(CHAVE_A)}
_enc = types.ModuleType("app.services.encryption_service")
_enc.get_encryption_service = lambda: _ATUAL["cripto"]
sys.modules["app.services.encryption_service"] = _enc

_spec = importlib.util.spec_from_file_location(
    "app.services.whatsapp.integration_secrets",
    RAIZ / "app" / "services" / "whatsapp" / "integration_secrets.py")
seg = importlib.util.module_from_spec(_spec)
sys.modules["app.services.whatsapp.integration_secrets"] = seg
_spec.loader.exec_module(seg)


class _Captura(logging.Handler):
    """Guarda a linha E o nivel: "informado" e "gritado" sao niveis diferentes,
    e a diferenca entre eles e metade do que este teste afirma."""

    def __init__(self):
        super().__init__()
        self.linhas = []
        self.niveis = []

    def emit(self, record):
        self.linhas.append(record.getMessage())
        self.niveis.append(record.levelno)


# As formas REAIS medidas em public.integrations em 06/08/2026 (nunca os valores).
LEGADO_36 = "1f4a9c2e-7b83-4d51-9e60-2ac8bd137f45"   # linha `autobrokers-go-teste`
LEGADO_49 = "3F45A55D9ECD21658FC6E6B1C946898" + "0ABCDEFGHIJKLMNOP"  # linha z-api
TOKEN_REAL = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"      # secrets.token_hex(16)


def rodar():
    global PASS
    print("== um segredo perdido grita; um legado passa ==\n")

    # ----------------------------------------------------------- bloco 1
    print("-- 1. o caso que travou a Resulta: cifrado com A, aberto com B --")
    ciphertext = _Cripto(CHAVE_A).encrypt(TOKEN_REAL)
    checar("o ciphertext tem os 188 chars medidos no banco",
           len(ciphertext) == 188, len(ciphertext))

    _ATUAL["cripto"] = _Cripto(CHAVE_B)          # o container subiu com outra chave
    levantou = None
    try:
        seg.decrypt_integration_secret(ciphertext, contexto="token resulta observer")
    except seg.SegredoIndecifravel as e:
        levantou = e
    checar("chave errada + ciphertext -> LEVANTA (nao devolve o blob)",
           levantou is not None,
           "devolveu em silencio — este era o defeito")
    checar("a mensagem NOMEIA a causa (ENCRYPTION_KEY), nao 'configuracao incompleta'",
           levantou is not None and "ENCRYPTION_KEY" in str(levantou))
    checar("a mensagem diz ONDE (corretora/instancia), para o log servir de manha",
           levantou is not None and "resulta observer" in str(levantou))
    checar("13.3 — a mensagem NAO contem o segredo nem o ciphertext",
           levantou is not None
           and TOKEN_REAL not in str(levantou)
           and ciphertext[:40] not in str(levantou))

    # ----------------------------------------------------------- bloco 2
    #
    # A LINHA DE CONTROLE. Sem ela um guarda que levantasse SEMPRE passaria no
    # bloco 1 inteiro — e quebraria as duas linhas legadas que existem de
    # verdade no banco, inclusive a que ainda serve de memoria de instancia.
    print("\n-- 2. CONTROLE: plaintext legado de verdade PASSA --")
    captura = _Captura()
    nivel_antes = seg.logger.level
    seg.logger.setLevel(logging.DEBUG)      # senao o INFO nem chega no handler
    seg.logger.addHandler(captura)
    for rotulo, legado in (("36 chars (uuid)", LEGADO_36), ("49 chars (z-api)", LEGADO_49)):
        devolvido = seg.decrypt_integration_secret(legado, contexto="token legado")
        checar(f"legado {rotulo}: devolvido como esta", devolvido == legado, devolvido[:6] + "…")
    seg.logger.removeHandler(captura)
    seg.logger.setLevel(nivel_antes)
    checar("o legado e registrado", any("PLAINTEXT legado" in l for l in captura.linhas),
           captura.linhas[:1])
    checar("e e INFORMADO, nao gritado — nada a consertar as pressas",
           captura.niveis and max(captura.niveis) <= logging.INFO,
           [logging.getLevelName(n) for n in captura.niveis])
    checar("13.3 — o valor legado tambem nao vai para o log",
           not any(LEGADO_36 in l or LEGADO_49 in l for l in captura.linhas))

    # ----------------------------------------------------------- bloco 3
    print("\n-- 3. o caminho feliz continua feliz --")
    _ATUAL["cripto"] = _Cripto(CHAVE_A)
    checar("chave certa: volta o token original",
           seg.decrypt_integration_secret(ciphertext) == TOKEN_REAL)
    ida_e_volta = seg.prepare_integration_for_runtime(
        seg.prepare_integration_for_storage({"token": TOKEN_REAL, "company_id": "c1"}))
    checar("guarda->runtime devolve o mesmo token", ida_e_volta["token"] == TOKEN_REAL)
    checar("vazio/None atravessam sem drama",
           seg.decrypt_integration_secret(None) is None
           and seg.decrypt_integration_secret("") == "")

    # ----------------------------------------------------------- bloco 4
    print("\n-- 4. cifra dupla: a hipotese que a aritmetica derruba --")
    # 📊 188 chars re-cifrados dariam 444. Nenhum valor de 444 existe no banco
    # (medido 06/08/2026) — mas a porta existia, e agora esta fechada.
    guardado = seg.prepare_integration_for_storage({"token": TOKEN_REAL})["token"]
    de_novo = seg.prepare_integration_for_storage({"token": guardado})["token"]
    checar("re-guardar um ciphertext NAO o cifra de novo",
           de_novo == guardado, f"{len(guardado)} -> {len(de_novo)}")
    checar("e o de dentro continua alcancavel",
           seg.decrypt_integration_secret(de_novo) == TOKEN_REAL)

    # ----------------------------------------------------------- bloco 5
    #
    # 9.2, corolario: "quando o teste comparar duas coisas, prove que elas
    # CONSEGUEM ser diferentes". Se `tem_forma_de_ciphertext` devolvesse sempre
    # o mesmo valor, os blocos 1 e 2 nao poderiam BOTH passar — mas so este
    # bloco mostra que o discriminador enxerga os dois lados.
    print("\n-- 5. o discriminador enxerga os DOIS lados --")
    checar("ciphertext real -> True", seg.tem_forma_de_ciphertext(ciphertext) is True)
    checar("legado 36 chars -> False", seg.tem_forma_de_ciphertext(LEGADO_36) is False)
    checar("legado 49 chars -> False", seg.tem_forma_de_ciphertext(LEGADO_49) is False)
    checar("token hex de 32 -> False", seg.tem_forma_de_ciphertext(TOKEN_REAL) is False)
    checar("vazio -> False", seg.tem_forma_de_ciphertext("") is False)
    # base64 valido que NAO e Fernet: o caso que separa "parece" de "e".
    checar("base64 valido sem miolo Fernet -> False",
           seg.tem_forma_de_ciphertext(base64.b64encode(b"nao sou fernet").decode()) is False)
    veredito_ciphertext = seg.tem_forma_de_ciphertext(ciphertext)
    veredito_legado = seg.tem_forma_de_ciphertext(LEGADO_36)
    checar("e os dois vereditos sao DIFERENTES (o guarda pode falhar, logo guarda)",
           veredito_ciphertext != veredito_legado)

    # ----------------------------------------------------------- bloco 6
    print("\n-- 6. a varredura de muitas corretoras nao morre por uma --")
    _ATUAL["cripto"] = _Cripto(CHAVE_B)
    # 13.3 vale aqui tambem: o DETALHE de uma falha nunca carrega o valor. Sem
    # esta precaucao o proprio teste imprimia o blob de 188 chars ao reprovar —
    # que e exatamente o que ele acusa o codigo de fazer.
    def forma(v):
        return "None" if v is None else f"<{len(str(v))} chars>"

    perdido = seg.decrypt_integration_secret(ciphertext, tolerar_perda=True)
    checar("tolerar_perda devolve None, NUNCA o blob",
           perdido is None, forma(perdido))
    linha = seg.prepare_integration_for_runtime(
        {"token": ciphertext, "company_id": "c1", "purpose": "observer"},
        tolerar_perda=True)
    checar("e a linha inteira sai sem token utilizavel (fail-CLOSED)",
           linha["token"] is None, forma(linha["token"]))
    _ATUAL["cripto"] = _Cripto(CHAVE_A)

    # ----------------------------------------------------------- bloco 7
    print("\n-- 7. o fail-open nao pode voltar --")
    fonte = (RAIZ / "app/services/whatsapp/integration_secrets.py").read_text(encoding="utf-8")
    corpo = fonte[fonte.index("def decrypt_integration_secret"):
                  fonte.index("def prepare_integration_for_storage")]
    depois_do_doc = corpo.split('"""')[-1]
    checar("o except NAO devolve mais o valor cru sem antes conferir a forma",
           "tem_forma_de_ciphertext" in depois_do_doc)
    checar("e existe um caminho que levanta",
           "raise SegredoIndecifravel" in depois_do_doc)

    print(f"\n{'=' * 60}")
    print(f"PASS={PASS} FAIL={FAIL}")
    if FALHAS:
        print("\nFALHAS:")
        for n, d in FALHAS:
            print(f"  - {n}: {d}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(rodar())
