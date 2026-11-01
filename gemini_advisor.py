import os
from typing import Optional
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class GeminiAdvisor:
    """
    AI Strategist and Battle Advisor powered by Google Gemini (gemini-3.1-flash-lite).
    Provides instant base analysis, loot evaluation, and attack strategy insights.
    """
    def __init__(self, api_key: str = "", model_name: str = "gemini-3.1-flash-lite"):
        self.api_key = api_key.strip() or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or "gemini-3.1-flash-lite"
        self.client = None
        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Gemini client initialization warning: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client and GENAI_AVAILABLE)

    def update_key(self, api_key: str):
        self.api_key = api_key.strip()
        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.client = None

    def analyze_base_or_battle(self, image: Image.Image, prompt_text: str = "") -> str:
        """
        Sends current game screenshot to Gemini for tactical advice and loot assessment.
        """
        if not self.is_configured():
            if not GENAI_AVAILABLE:
                return "⚠️ `google-genai` SDK is not installed. Please run `pip install google-genai`."
            return "⚠️ Gemini API key is not configured. Please set your Gemini API key in Settings or config.json."

        if not prompt_text:
            prompt_text = (
                "You are an expert Clash of Clans strategist. Analyze this screenshot of the game. "
                "Briefly evaluate: 1) Available Loot, 2) Defensive weak spots, 3) Best deployment angle for Dragons / Dragon Duke. "
                "Keep response concise, bulleted, and actionable for a live attack."
            )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt_text, image]
            )
            return response.text if response and response.text else "No analysis generated."
        except Exception as e:
            return f"❌ Gemini API error: {e}"

    def ask_advice(self, user_question: str) -> str:
        """Text-only consultation with Gemini advisor."""
        if not self.is_configured():
            return "⚠️ Gemini API key is missing. Please set your key to chat with the AI Advisor."

        try:
            system_instruction = (
                "You are CoC Commander AI, a tactical advisor for Clash of Clans. "
                "Answer questions about troop compositions, farming strategies, Town Hall upgrades, and attack timing. "
                "Be energetic, practical, and concise."
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_question,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                ) if hasattr(types, "GenerateContentConfig") else None
            )
            return response.text if response and response.text else "No response generated."
        except Exception as e:
            return f"❌ Gemini consultation error: {e}"
