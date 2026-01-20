"""Command-line interface for JSON translator"""

import argparse
import sys
from .translator import JSONTranslator
from .config import DEFAULT_INPUT, DEFAULT_OUTPUT, DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Translate JSON files using Argos Translate"
    )
    parser.add_argument(
        "-i", "--input",
        default=DEFAULT_INPUT,
        help=f"Input JSON file (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON file (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--from-lang",
        default=DEFAULT_SOURCE_LANG,
        help=f"Source language code (default: {DEFAULT_SOURCE_LANG})"
    )
    parser.add_argument(
        "--to-lang",
        default=DEFAULT_TARGET_LANG,
        help=f"Target language code (default: {DEFAULT_TARGET_LANG})"
    )
    
    args = parser.parse_args()
    
    try:
        # Create translator instance
        translator = JSONTranslator(
            source_lang=args.from_lang,
            target_lang=args.to_lang
        )
        
        # Translate the file
        translator.translate_file(args.input, args.output)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
