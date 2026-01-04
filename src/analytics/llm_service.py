
import os
import requests
from typing import Optional, Dict, Any, List
from loguru import logger
from openai import OpenAI
import google.generativeai as genai
from ..utils.resilience import retry, circuit_breaker
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    """
    Unified client for LLM interactions.
    Handles provider selection (Anthropic, OpenAI, Gemini) and resilience.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_anthropic: bool = False):
        self.use_anthropic = use_anthropic
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY') or api_key
        self.openai_api_key = os.getenv('OPENAI_API_KEY') or api_key
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        
        self.openai_client = None
        self.gemini_client = None
        
        # Initialize Primary Provider
        if self.use_anthropic:
            if not self.anthropic_api_key:
                logger.warning("Anthropic requested but no key found. Falling back to OpenAI.")
                self.use_anthropic = False
            else:
                self.model = os.getenv('DEFAULT_ANTHROPIC_MODEL', 'claude-3-5-sonnet-20240620')
                logger.info(f"Initialized LLMService with Anthropic: {self.model}")
        
        if not self.use_anthropic:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required")
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.model = os.getenv('DEFAULT_OPENAI_MODEL', 'gpt-4o')
            logger.info(f"Initialized LLMService with OpenAI: {self.model}")
            
        # Initialize Fallback (Gemini)
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_client = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("Gemini fallback initialized")
            except Exception as e:
                logger.warning(f"Failed to init Gemini: {e}")

    @retry(max_retries=3)
    def generate_completion(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate text completion with automatic fallback.
        """
        try:
            if self.use_anthropic:
                return self._call_anthropic(prompt, system_prompt)
            else:
                return self._call_openai(prompt, system_prompt)
        except Exception as e:
            logger.error(f"Primary LLM failed: {e}. Trying fallback...")
            if self.gemini_client:
                return self._call_gemini(prompt, system_prompt)
            raise e

    def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        """Direct HTTP call to Anthropic API."""
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
        response.raise_for_status()
        return response.json()['content'][0]['text']

    def _call_openai(self, prompt: str, system_prompt: str) -> str:
        """Call OpenAI SDK."""
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    def _call_gemini(self, prompt: str, system_prompt: str) -> str:
        """Call Gemini SDK."""
        # Gemini doesn't have system prompts in the same way, usually prepended
        full_prompt = f"{system_prompt}\n\n{prompt}"
        response = self.gemini_client.generate_content(full_prompt)
        return response.text
