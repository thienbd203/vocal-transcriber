"""
Translate JSON module - Dịch file JSON sử dụng Argos Translate
"""

from .translator import JSONTranslator
from .config import DEFAULT_INPUT, DEFAULT_OUTPUT

__version__ = "1.0.0"
__all__ = ["JSONTranslator", "DEFAULT_INPUT", "DEFAULT_OUTPUT"]
