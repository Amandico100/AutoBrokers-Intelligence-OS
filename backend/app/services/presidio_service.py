
import logging
import os
import threading
from typing import Tuple

from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM BRAZILIAN RECOGNIZERS
# =============================================================================

class BrazilianCPFRecognizer(PatternRecognizer):
    """Recognizer for Brazilian CPF (Cadastro de Pessoa Física)."""

    PATTERNS = [
        Pattern(
            "CPF (XXX.XXX.XXX-XX)",
            r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
            0.85
        ),
        Pattern(
            "CPF (XXXXXXXXXXX)",
            r"\b\d{11}\b",
            0.4  # Lower score, needs validation
        ),
    ]

    CONTEXT = ["cpf", "cadastro", "pessoa física", "documento"]

    def __init__(self):
        super().__init__(
            supported_entity="BR_CPF",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="pt",
        )


class BrazilianCNPJRecognizer(PatternRecognizer):
    """Recognizer for Brazilian CNPJ (Cadastro Nacional de Pessoa Jurídica)."""

    PATTERNS = [
        Pattern(
            "CNPJ (XX.XXX.XXX/XXXX-XX)",
            r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
            0.85
        ),
    ]

    CONTEXT = ["cnpj", "empresa", "pessoa jurídica", "razão social"]

    def __init__(self):
        super().__init__(
            supported_entity="BR_CNPJ",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="pt",
        )


class BrazilianPhoneRecognizer(PatternRecognizer):
    """Recognizer for Brazilian phone numbers."""

    PATTERNS = [
        Pattern(
            "BR Phone (+55 XX XXXXX-XXXX)",
            r"\+55\s?\d{2}\s?\d{4,5}[-\s]?\d{4}\b",
            0.85
        ),
        Pattern(
            "BR Phone (XX XXXXX-XXXX)",
            r"\b\d{2}\s?\d{4,5}[-\s]?\d{4}\b",
            0.6
        ),
        Pattern(
            "BR Phone ((XX) XXXXX-XXXX)",
            r"\(\d{2}\)\s?\d{4,5}[-\s]?\d{4}\b",
            0.85
        ),
    ]

    CONTEXT = ["telefone", "celular", "whatsapp", "ligar", "contato", "fone"]

    def __init__(self):
        super().__init__(
            supported_entity="BR_PHONE",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="pt",
        )


class BrazilianEmailRecognizer(PatternRecognizer):
    """Email recognizer with Portuguese context."""

    PATTERNS = [
        Pattern(
            "Email",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            0.9
        ),
    ]

    CONTEXT = ["email", "e-mail", "correio", "enviar"]

    def __init__(self):
        super().__init__(
            supported_entity="EMAIL_ADDRESS",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="pt",
        )


# =============================================================================
# PRESIDIO SERVICE
# =============================================================================

def _modelo_instalado(nome: str) -> bool:
    try:
        import spacy.util

        return bool(spacy.util.is_package(nome))
    except Exception:  # noqa: BLE001
        return False


def _pode_baixar_modelo() -> bool:
    """`PRESIDIO_BAIXAR_MODELO=0` proíbe o download do spaCy no arranque (padrão: permitido, o comportamento de hoje).

    ⚠️ PENDÊNCIA de infra (SPEC-132-A, red team P1): o `backend/Dockerfile` só instala o `en_core_web_lg`; o
    `pt_core_news_md` é baixado por pip a CADA arranque. Com `python -m spacy download pt_core_news_md` no Dockerfile,
    o download nunca acontece em produção — e esta chave pode ir a `0`."""
    return str(os.getenv("PRESIDIO_BAIXAR_MODELO", "1")).strip().lower() not in ("0", "false", "no", "off", "nao")


class PresidioService:
    _instance = None
    #: 🔴 SPEC-132-A B7 — o aquecimento do arranque cria o singleton numa THREAD
    #: enquanto o 1º turno pode pedi-lo no event loop. Sem a trava, os dois viam
    #: `_instance is None` e o spaCy (pt + en) carregava DUAS vezes.
    _trava = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._trava:
                if cls._instance is None:
                    instancia = super(PresidioService, cls).__new__(cls)
                    instancia._initialize()
                    # Publicada só PRONTA: quem passa pelo `if` de fora sem a trava
                    # nunca recebe uma instância pela metade.
                    cls._instance = instancia
        return cls._instance

    def _initialize(self):
        try:
            # Try to load Portuguese model, fallback to multilingual approach
            try:
                configuration = {
                    "nlp_engine_name": "spacy",
                    "models": [
                        {"lang_code": "pt", "model_name": "pt_core_news_md"},
                        {"lang_code": "en", "model_name": "en_core_web_lg"},
                    ],
                }
                faltam = [m["model_name"] for m in configuration["models"]
                          if not _modelo_instalado(m["model_name"])]
                if faltam and not _pode_baixar_modelo():
                    raise RuntimeError("modelos do spaCy ausentes e download proibido: %s" % ", ".join(faltam))
                provider = NlpEngineProvider(nlp_configuration=configuration)
                nlp_engine = provider.create_engine()

                self.analyzer = AnalyzerEngine(
                    nlp_engine=nlp_engine,
                    supported_languages=["pt", "en"]
                )
                logger.info("Presidio Service initialized with Portuguese (pt_core_news_md) + English")

            except (Exception, SystemExit) as model_error:
                # 🔴 SPEC-132-A (red team P1): o download do spaCy que falha faz `sys.exit(1)` — `SystemExit` não é
                # `Exception`, e derrubava o processo (no arranque ou no 1º turno). Agora vira o motor padrão.
                logger.warning("Could not load pt_core_news_md (%s). Using default engine.", type(model_error).__name__)
                self.analyzer = AnalyzerEngine()

            # Register Brazilian recognizers
            self.analyzer.registry.add_recognizer(BrazilianCPFRecognizer())
            self.analyzer.registry.add_recognizer(BrazilianCNPJRecognizer())
            self.analyzer.registry.add_recognizer(BrazilianPhoneRecognizer())
            self.analyzer.registry.add_recognizer(BrazilianEmailRecognizer())

            self.anonymizer = AnonymizerEngine()
            logger.info("Presidio Service initialized with Brazilian recognizers (CPF, CNPJ, Phone, Email)")
            self.initialized = True

        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize Presidio (%s)", type(e).__name__)
            self.initialized = False

    def analyze_and_anonymize(self, text: str, action: str = 'mask') -> Tuple[bool, str]:
        """
        Analisa texto buscando PII e aplica ação (mask ou block).
        Retorna (found_pii: bool, processed_text: str)
        """
        if not self.initialized or not text:
            return False, text

        try:
            # 1. Analyze with Portuguese language
            results = self.analyzer.analyze(text=text, language='pt')

            if not results:
                return False, text

            # Log what was found for debugging
            entities_found = [f"{r.entity_type}:{r.score:.2f}" for r in results]
            logger.info(f"[Presidio] PII detected: {entities_found}")

            # 2. Se ação for BLOCK, retorna flag true e texto original
            if action == 'block':
                return True, text

            # 3. Se ação for MASK, anonimiza
            if action == 'mask':
                anonymized_result = self.anonymizer.anonymize(
                    text=text,
                    analyzer_results=results,
                    operators={
                        "DEFAULT": OperatorConfig("replace", {"new_value": "****"}),
                        "BR_CPF": OperatorConfig("replace", {"new_value": "[CPF OCULTO]"}),
                        "BR_CNPJ": OperatorConfig("replace", {"new_value": "[CNPJ OCULTO]"}),
                        "BR_PHONE": OperatorConfig("replace", {"new_value": "[TELEFONE OCULTO]"}),
                        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL OCULTO]"}),
                    }
                )
                return True, anonymized_result.text

            return False, text

        except Exception as e:
            logger.error(f"Error in PII analysis: {e}")
            return False, text


def get_presidio_service():
    return PresidioService()
