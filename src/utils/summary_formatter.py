"""
Post-processing formatter for executive summaries.
Fixes formatting issues WITHOUT modifying the LLM prompt.
"""
import re
from typing import Tuple


def format_summary(brief: str, detailed: str) -> Tuple[str, str]:
    """
    Apply post-processing formatting to both brief and detailed summaries.
    
    Fixes:
    1. Numbers to M/K notation with $ symbols
    2. Remove Source mentions
    3. Fix spacing issues
    4. Ensure section headers are visible
    
    Args:
        brief: Brief summary text
        detailed: Detailed summary text
        
    Returns:
        Tuple of (formatted_brief, formatted_detailed)
    """
    brief = _format_text(brief)
    detailed = _format_text(detailed)
    
    return brief, detailed


def _format_text(text: str) -> str:
    """Apply all formatting rules to text - CONSERVATIVE VERSION."""
    if not text:
        return text
    
    # 1. Remove Source mentions (e.g., "Source 1", "(Source: ...)")
    text = re.sub(r'\(Source:?[^)]+\)', '', text)
    text = re.sub(r'Source \d+[:\-\s]+[^\n]+', '', text)
    text = re.sub(r'\bSource \d+\b', '', text)
    
    # 2. Fix section headers with bold formatting (do this FIRST)
    text = _fix_section_headers(text)
    
    # 3. Clean up multiple spaces and newlines
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def _format_currency_and_numbers(text: str) -> str:
    """Convert large numbers to M/K notation and add $ for currency."""
    
    # First, fix malformed numbers with spaces (e.g., "4, 452, 903. 68" -> "4452903.68")
    text = re.sub(r'(\d+)(?:\s*,\s*(\d+))+(?:\s*\.\s*(\d+))?', lambda m: m.group(0).replace(' ', '').replace(',', ''), text)
    
    def format_number(match):
        """Format a single number match."""
        num_str = match.group(0).replace(',', '').replace(' ', '')
        try:
            num = float(num_str)
            
            # Check if it's likely currency (preceded by $ or "dollars" or spend/cost keywords)
            start_pos = max(0, match.start() - 20)
            context_before = text[start_pos:match.start()].lower()
            is_currency = ('$' in context_before or 'dollar' in context_before or 
                          'spend' in context_before or 'cost' in context_before or 
                          'cpa' in context_before or 'cpc' in context_before)
            
            # Format based on magnitude
            if num >= 1_000_000:
                formatted = f"${num/1_000_000:.2f}M" if is_currency else f"{num/1_000_000:.2f}M"
            elif num >= 1_000:
                formatted = f"${num/1_000:.0f}K" if is_currency else f"{num/1_000:.0f}K"
            else:
                formatted = f"${num:.2f}" if is_currency else f"{num:.2f}"
            
            return formatted
        except ValueError:
            return match.group(0)
    
    # Match numbers with optional commas and decimals
    # Catches: 4452903.68, 4,452,903.68, 813455, 813,455
    pattern = r'(?<![KMB$%])\b\d{1,3}(?:,\d{3})+(?:\.\d+)?|\b\d{4,}(?:\.\d+)?\b'
    text = re.sub(pattern, format_number, text)
    
    # Remove "dollars" word after we've added $ symbols
    text = re.sub(r'\$([0-9.KM]+)\s*dollars?', r'$\1', text, flags=re.IGNORECASE)
    
    # Fix percent formatting: "0. 42 percent" -> "0.42%"
    text = re.sub(r'(\d+)\s*\.\s*(\d+)\s*percent', r'\1.\2%', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s+percent', r'\1%', text, flags=re.IGNORECASE)
    
    # Fix B2B spacing: "B 2 B" -> "B2B"
    text = re.sub(r'\bB\s*2\s*B\b', 'B2B', text, flags=re.IGNORECASE)
    text = re.sub(r'\bB\s*2\s*C\b', 'B2C', text, flags=re.IGNORECASE)
    
    return text


def _fix_spacing(text: str) -> str:
    """Fix spacing issues between numbers and words."""
    
    # Space after numbers before letters
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    
    # Space before numbers after letters (but not in words like "2x" or "4.5x")
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    
    # Space after periods before letters
    text = re.sub(r'(\.)([A-Z])', r'\1 \2', text)
    
    # Fix common concatenations
    replacements = {
        'campaignson': 'campaigns on',
        'platformson': 'platforms on',
        'conversionsat': 'conversions at',
        'CPAof': 'CPA of',
        'CTRof': 'CTR of',
        'CPCof': 'CPC of',
        'ROASof': 'ROAS of',
        'yielding': ', yielding ',  # Fix "1.67M , yielding316.40M"
        'impressionsat': 'impressions at',
        'clicksat': 'clicks at',
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    return text


def _fix_section_headers(text: str) -> str:
    """Ensure section headers are properly formatted with bold and colons."""
    
    # List of expected section headers
    headers = [
        'Performance Overview',
        'Performance vs Industry Benchmarks',
        'Multi-KPI Analysis',
        'Platform-Specific Insights',
        'What Is Working',
        'What Is Not Working',
        'Budget Optimization',
        'Optimization Roadmap',
        'Priority Actions',
        'Overall',
        'Overall Summary',
        'Channel Summary',
        'Key Strengths',
        'Key Strength',
        'Priority Actions',
        'Priority Action'
    ]
    
    for header in headers:
        # Ensure header is on its own line with bold formatting and colon
        # Match header with optional punctuation/formatting
        pattern = rf'(?:^|\n)\s*{re.escape(header)}\s*[:\-]?\s*'
        # Use markdown bold (**header:**) for Streamlit rendering
        replacement = f'\n\n**{header}:**\n\n'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text
