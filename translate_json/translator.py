"""Core JSON translation functionality"""

import json
import sys
import os
import math
import logging
from pathlib import Path
import ijson
import argostranslate.package
import argostranslate.translate
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed

from .config import DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG, PROGRESS_INTERVAL, DEFAULT_BACKEND, DEFAULT_MARIAN_MODEL
from .filters import should_translate


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class JSONTranslator:
    """A class to handle JSON file translation using Argos Translate"""
    
    def __init__(self, source_lang: str = DEFAULT_SOURCE_LANG, 
                 target_lang: str = DEFAULT_TARGET_LANG, 
                 backend: str = DEFAULT_BACKEND,
                 marian_model: str = DEFAULT_MARIAN_MODEL):
        """
        Initialize the translator.
        
        Args:
            source_lang: Source language code (default: 'en')
            target_lang: Target language code (default: 'vi')
            max_workers: Maximum number of worker threads (default: 4)
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.backend = backend
        self.marian_model = marian_model
        self._packages_installed = False
        self._lock = threading.Lock()  # For thread-safe translation
        self.translation_cache: dict[str, str] = {}
        self._translation_samples: list[tuple[str, str]] = []
        self._sample_limit = 15
        try:
            from transformers import pipeline as hf_pipeline
        except ImportError:
            hf_pipeline = None
        self._hf_pipeline = None
        self._hf_pipeline_factory = hf_pipeline
    
    def _ensure_packages(self):
        """Download and install translation packages if needed"""
        if self._packages_installed:
            return
            
        print("  - Checking translation packages...")
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        
        # Find the appropriate package
        package = next(
            (p for p in available_packages 
             if p.from_code == self.source_lang and p.to_code == self.target_lang),
            None
        )
        
        if not package:
            raise ValueError(
                f"No translation package available for {self.source_lang} -> {self.target_lang}"
            )
        
        # Install if not already installed
        installed_packages = argostranslate.package.get_installed_packages()
        if not any(p.from_code == self.source_lang and p.to_code == self.target_lang 
                  for p in installed_packages):
            print(f"  - Downloading {self.source_lang} to {self.target_lang} package...")
            argostranslate.package.install_from_path(package.download())
        
        self._packages_installed = True
    
    def translate_text(self, text: str) -> str:
        """
        Translate a single text string.
        
        Args:
            text: Text to translate
            
        Returns:
            Translated text
        """
        if text in self.translation_cache:
            return self.translation_cache[text]
        logger.debug("Translating text via backend %s: %s", self.backend, text)
        with self._lock:
            translated = self._translate_via_backend(text)
        self.translation_cache[text] = translated
        return translated
    
    def _translate_batch(self, texts: list) -> list:
        """
        Translate multiple texts using cache deduplication.
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts in the same order
        """
        if not texts:
            return []

        results = [None] * len(texts)
        pending: dict[str, list[int]] = {}

        for index, text in enumerate(texts):
            if text in self.translation_cache:
                results[index] = self.translation_cache[text]
            else:
                pending.setdefault(text, []).append(index)

        for raw_text, indices in pending.items():
            translated = self.translate_text(raw_text)
            for idx in indices:
                results[idx] = translated

        return results

    def _translate_via_backend(self, text: str) -> str:
        if self.backend == "marian":
            if not self._hf_pipeline_factory:
                raise RuntimeError("HuggingFace transformers not installed.\nInstall transformers>=4.0 to enable Marian backend.")
            if not self._hf_pipeline:
                self._hf_pipeline = self._hf_pipeline_factory(
                    "translation", model=self.marian_model, device=0 if sys.platform != "darwin" else -1
                )
            translated = self._hf_pipeline(text, max_length=512)[0]["translation_text"]
            return translated
        return argostranslate.translate.translate(text, self.source_lang, self.target_lang)

    def _log_translation(self, source: str, translated: str) -> None:
        if len(self._translation_samples) >= self._sample_limit:
            self._translation_samples.pop(0)
        self._translation_samples.append((source, translated))

    def pop_translation_samples(self) -> list[tuple[str, str]]:
        samples = self._translation_samples.copy()
        self._translation_samples.clear()
        return samples
    
    def process_parameters(self, params):
        """
        Process a list of parameters, translating eligible strings.
        
        Args:
            params: List of parameters from JSON
            
        Returns:
            Processed list with translations
        """
        # Collect strings that need translation
        strings_to_translate = []
        indices_to_translate = []
        
        for i, p in enumerate(params):
            if isinstance(p, str) and should_translate(p):
                strings_to_translate.append(p)
                indices_to_translate.append(i)
        
        # Translate in batches using thread pool
        if strings_to_translate:
            translated_strings = self._translate_batch(strings_to_translate)
            
            # Update the original params list with translations
            for idx, translated in zip(indices_to_translate, translated_strings):
                original = params[idx]
                wrap = original.startswith("`") and original.endswith("`")
                params[idx] = f"`{translated}`" if wrap else translated
                self._log_translation(original, params[idx])
        
        return params
    
    def translate_file(self, input_path: str, output_path: str):
        """
        Translate a JSON file, preserving structure.
        
        Args:
            input_path: Path to input JSON file
            output_path: Path to save translated JSON
        """
        # Check input file exists
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file '{input_path}' not found!")
        
        # Ensure translation packages are ready
        self._ensure_packages()
        
        print(f"▶ Translating JSON from {self.source_lang} to {self.target_lang}...")
        
        # Read the entire JSON file
        with open(input_path, "r", encoding="utf-8") as f_in:
            json_data = json.load(f_in)
        
        # Process the data with batch processing
        if isinstance(json_data, list):
            # Handle the specific format: [null, {id: 1, list: [...]}, {id: 2, list: [...]}]
            items_to_process = []
            
            for item in json_data:
                if item is None:
                    continue
                if isinstance(item, dict) and 'list' in item and isinstance(item['list'], list):
                    # Add all items from the list
                    items_to_process.extend(item['list'])
                elif isinstance(item, dict):
                    # Add the item itself if it has parameters
                    items_to_process.append(item)
            
            # Process items in batches
            total_items = len(items_to_process)
            processed_items = 0
            translated_count = 0
            batch_size = 50  # Process 50 items at a time
            
            print(f"  - Processing {total_items} items in batches of {batch_size}")
            
            for batch_start in range(0, total_items, batch_size):
                batch_end = min(batch_start + batch_size, total_items)
                batch = items_to_process[batch_start:batch_end]
                
                # Process batch
                for item in batch:
                    if isinstance(item, dict) and 'parameters' in item and isinstance(item['parameters'], list):
                        original_params = item['parameters']
                        item['parameters'] = self.process_parameters(item['parameters'])
                        # Count translated items
                        for p in original_params:
                            if isinstance(p, str) and should_translate(p):
                                translated_count += 1
                    
                    processed_items += 1
                
                # Update progress
                if processed_items % PROGRESS_INTERVAL == 0 or processed_items == total_items:
                    print(f"  - processed {processed_items}/{total_items} entries")
        
        # Save the result
        with open(output_path, "w", encoding="utf-8") as f_out:
            json.dump(json_data, f_out, ensure_ascii=False, indent=2)
        
        print(f"✅ Done: {output_path}")
        print(f"📊 Total entries: {processed_items}")
        print(f"🌐 Translated strings: {translated_count}")
