
import re
import json
from typing import Dict, List, Any, Optional

class TextCleaner:
    """
    Janitor class for cleaning and normalizing text output from LLMs.
    """
    
    @staticmethod
    def strip_italics(text: str) -> str:
        """Comprehensive formatting cleanup with regex to fix common LLM formatting issues."""
        if not isinstance(text, str):
            return text
        
        # PASS 1: Remove ALL formatting characters (bold, italics)
        text = re.sub(r'\*+', '', text)
        text = re.sub(r'_+', '', text)
        
        # PASS 2: Fix em-dash and en-dash spacing
        text = text.replace('—', ' - ')
        text = text.replace('–', ' - ')
        
        # PASS 3: Fix number-letter spacing (e.g., "39.05CPA")
        for _ in range(3):
            text = re.sub(r'(\d+\.\d+)([A-Za-z])', r'\1 \2', text)
            text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
            text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
        
        # PASS 4: Dictionary-based fixes
        common_fixes = {
            'campaignson': 'campaigns on',
            'platformsgenerating': 'platforms generating',
            'conversionsat': 'conversions at',
            'CPAfrom': 'CPA from',
            'CPAwith': 'CPA with',
            'Kconversions': 'K conversions',
            'Mspend': 'M spend',
            'Mimpressions': 'M impressions',
            'Mclicks': 'M clicks',
            'comparedto': 'compared to',
        }
        for wrong, correct in common_fixes.items():
            text = text.replace(wrong, correct)
        
        # PASS 5: Fix punctuation spacing
        text = re.sub(r'([.,!?:;])([A-Za-z0-9])', r'\1 \2', text)
        
        # PASS 6: Remove brackets from headers
        text = re.sub(r'\[OVERALL SUMMARY\]', 'OVERALL SUMMARY:', text)
        text = re.sub(r'\[CHANNEL SUMMARY\]', 'CHANNEL SUMMARY:', text)
        
        # PASS 7: Clean up multiple spaces and excessive newlines
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    @staticmethod
    def extract_json_array(text: str) -> List[Dict[str, Any]]:
        """Extract the first JSON array from an LLM response."""
        if not text:
            raise ValueError("Empty response")

        cleaned = text.strip()
        
        # Strip code blocks
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("[") and part.endswith("]"):
                    cleaned = part
                    break

        # Find array brackets
        if not cleaned.startswith("["):
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1 and end > start:
                cleaned = cleaned[start:end + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return []
