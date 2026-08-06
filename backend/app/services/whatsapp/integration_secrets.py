"""Criptografia de segredos de integração (token/client_token) — reuso do EncryptionService.

- Armazenamento: cifrar antes de gravar (Fernet/AES, mesma chave ENCRYPTION_KEY do runtime).
- Runtime: descriptografar em memória apenas, na hora de usar.
- Compatibilidade: um valor que NUNCA foi cifrado (plaintext legado) passa adiante.

🔴 06/08/2026 — ESTE ARQUIVO CUSTOU DIAS DE PAREAMENTO A UMA CORRETORA.

O `except` daqui tratava QUALQUER falha de decifragem como "deve ser plaintext
legado" e devolvia **o próprio ciphertext**. Fail-OPEN. O efeito não aparecia
aqui: aparecia três camadas adiante, como `apikey` de 188 caracteres no
provedor, HTTP 401, e uma tela dizendo *"A configuração do canal está
incompleta"* — que não nomeia nada e manda o corretor procurar suporte.

    o erro real .......  ENCRYPTION_KEY não abre este valor
    o que se via ......  configuration_error, três camadas adiante

Um valor que TEM FORMA de ciphertext e não decifra não é legado: é um segredo
perdido, e devolver o blob no lugar dele é entregar lixo a quem confia. A
diferença é MEDÍVEL — `EncryptionService.encrypt` produz uma forma exata — e é
essa medida que separa os dois casos:

    plaintext legado    36 chars, sem forma de Fernet    -> passa, com informe
    ciphertext quebrado 188 chars, `gAAAAA…` por dentro   -> GRITA

📊 Medido em 06/08/2026 no banco de produção: as duas linhas legadas de verdade
têm 36 e 49 caracteres e não são base64 válido; as quatro cifradas têm 188 e
decodificam para um token Fernet íntegro (versão 0x80). As duas populações não
se encostam — por isso o teste consegue distingui-las, e por isso o guarda pode
ser estrito sem quebrar o legado.
"""
import base64
import logging
from typing import Any, Dict, Optional

from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)

# Campos sensíveis em public.integrations.
SECRET_FIELDS = ("token", "client_token")

# Um token Fernet tem, no mínimo: 1 byte de versão + 8 de timestamp + 16 de IV
# + 16 de corpo + 32 de HMAC. Menos que isso não é token, é coincidência.
_FERNET_MIN_BYTES = 57
_FERNET_VERSAO = 0x80


class SegredoIndecifravel(RuntimeError):
    """O valor tem forma de ciphertext e a chave atual não o abre.

    Levantada de propósito, e alto. As causas possíveis são poucas e todas
    exigem uma pessoa:

      1. `ENCRYPTION_KEY` mudou (ou o contêiner subiu com outra) → restaurar a
         chave que cifrou, ou recadastrar o segredo pela camada segura.
      2. O valor foi gravado por um caminho que cifra com outra chave.
      3. O valor foi corrompido em trânsito ou por edição manual no banco.

    NUNCA carrega o valor na mensagem — só a sua forma.
    """


def tem_forma_de_ciphertext(value: Optional[str]) -> bool:
    """Este valor foi PRODUZIDO por `EncryptionService.encrypt`?

    PURA e barata: só olha a forma, nunca tenta a chave. É o que dá ao guarda o
    direito de distinguir "nunca foi cifrado" de "foi cifrado e eu não abro".

    `encrypt` faz exatamente isto:

        base64.b64encode(  Fernet.encrypt(plaintext)  )
                           └── já é base64 URL-safe de bytes que começam em 0x80

    Então a forma é conferível em três passos, e um plaintext de token (hex,
    UUID, chave de provedor) não passa por eles nem por acidente.
    """
    texto = str(value or "")
    if not texto:
        return False
    try:
        externo = base64.b64decode(texto, validate=True)
    except Exception:  # noqa: BLE001 — não é base64 padrão: não saiu de encrypt()
        return False
    try:
        interno = base64.urlsafe_b64decode(externo.decode("ascii"))
    except Exception:  # noqa: BLE001 — o miolo não é um token Fernet
        return False
    return len(interno) >= _FERNET_MIN_BYTES and interno[0] == _FERNET_VERSAO


def encrypt_integration_secret(value: Optional[str]) -> Optional[str]:
    """Cifra um segredo. Retorna o próprio valor se vazio/None.

    Não re-cifra o que já está cifrado. Uma cópia de `prepare_integration_for_runtime`
    que voltasse por `prepare_integration_for_storage` sem passar pelo decrypt
    dobraria a cifra — 📊 de 188 para 444 caracteres — e o segredo de dentro
    ficaria inalcançável pelo caminho normal. Nunca aconteceu em produção
    (medido em 06/08/2026: nenhum valor com 444), e agora não pode acontecer.
    """
    if not value:
        return value
    if tem_forma_de_ciphertext(value):
        logger.debug("[INTEGRATION SECRETS] valor ja cifrado; nao cifro de novo")
        return value
    return get_encryption_service().encrypt(value)


def decrypt_integration_secret(
    value: Optional[str], *, contexto: str = "", tolerar_perda: bool = False
) -> Optional[str]:
    """Descriptografa um segredo. NUNCA loga o valor.

    Três desfechos, e a diferença entre os dois últimos é o motivo deste arquivo
    ter sido reescrito:

      decifrou ........................  devolve o plaintext
      nunca foi cifrado (legado) ......  devolve como está, com informe
      é ciphertext e não abre .........  levanta `SegredoIndecifravel`

    `tolerar_perda=True` troca o levantamento por `None` — para o caminho que
    varre VÁRIAS corretoras e não pode deixar o segredo perdido de uma derrubar
    a varredura das outras. `None` continua sendo fail-CLOSED: ninguém recebe um
    blob achando que é chave. Quem tolera, loga em `error`.
    """
    if not value:
        return value
    try:
        return get_encryption_service().decrypt(value)
    except Exception as exc:  # noqa: BLE001
        onde = f" [{contexto}]" if contexto else ""
        if not tem_forma_de_ciphertext(value):
            # Nunca foi cifrado. Caminho legítimo e esperado: 📊 duas linhas de
            # 2026-07 no banco de produção. `info`, não `warning`: não há nada a
            # consertar às pressas, e alarme que sempre toca ninguém escuta.
            logger.info(
                "[INTEGRATION SECRETS]%s valor em PLAINTEXT legado (%d chars, sem forma "
                "de Fernet) — usado como está. Recadastre pela camada segura.",
                onde, len(str(value)),
            )
            return value

        # TEM forma de ciphertext e não abriu. Isto é perda de segredo, e o
        # sistema não tem o direito de seguir como se tivesse a chave.
        motivo = (
            f"segredo de integracao NAO DECIFRAVEL{onde}: tem forma de ciphertext "
            f"({len(str(value))} chars, Fernet v0x80 integro) mas a ENCRYPTION_KEY atual "
            f"nao o abre ({type(exc).__name__}). Causas: a chave mudou, o valor foi "
            f"cifrado por outra chave, ou foi corrompido. O valor NAO e logado."
        )
        if tolerar_perda:
            logger.error("[INTEGRATION SECRETS] %s — seguindo SEM chave para esta linha", motivo)
            return None
        logger.error("[INTEGRATION SECRETS] %s", motivo)
        raise SegredoIndecifravel(motivo) from exc


def prepare_integration_for_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    """Cópia com token/client_token CIFRADOS, pronta para gravar no banco."""
    out = dict(data)
    for field in SECRET_FIELDS:
        if out.get(field):
            out[field] = encrypt_integration_secret(out[field])
    return out


def prepare_integration_for_runtime(
    data: Optional[Dict[str, Any]], *, tolerar_perda: bool = False
) -> Optional[Dict[str, Any]]:
    """Cópia com token/client_token DESCRIPTOGRAFADOS em memória, pronta para uso.

    O `contexto` que vai para o log é a IDENTIDADE DA LINHA, nunca o segredo:
    com ele, quem lê o log às duas da manhã sabe qual corretora e qual instância
    precisam de recadastro — que é a única coisa que o log precisava dizer e não
    dizia.
    """
    if not data:
        return data
    out = dict(data)
    contexto = " ".join(
        str(out.get(campo)) for campo in ("company_id", "purpose", "instance_id")
        if out.get(campo)
    )
    for field in SECRET_FIELDS:
        if out.get(field):
            out[field] = decrypt_integration_secret(
                out[field], contexto=f"{field} {contexto}".strip(),
                tolerar_perda=tolerar_perda,
            )
    return out
