"""Filter functions to determine which strings should be translated"""

import re
from .config import MIN_TEXT_LENGTH


def should_translate(text: str) -> bool:
    """
    Determine if a string should be translated based on various rules.
    
    Args:
        text: The text to check
        
    Returns:
        bool: True if the text should be translated
    """
    s = text.strip()
    
    # Too short
    if len(s) < MIN_TEXT_LENGTH:
        return False
    
    # No alphabetic characters
    if not re.search(r"[A-Za-z]", s):
        return False
    
    # skip strings without whitespace to avoid keys/paths
    if " " not in s:
        return False
    
    # Contains technical placeholders
    if "{" in s or "%s" in s or "%d" in s:
        return False
    
    return True
