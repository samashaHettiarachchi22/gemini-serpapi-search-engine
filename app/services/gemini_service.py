from google import genai
from flask import current_app

class GeminiService:
    """Service for interacting with Google Gemini AI"""
    
    def __init__(self):
        self.client = None
    
    def initialize(self, api_key):
        """Initialize the Gemini client with API key"""
        self.client = genai.Client(api_key=api_key)
    
    def list_models(self):
        """
        List all available Gemini models
        
        Returns:
            list: List of model names
        """
        if not self.client:
            raise ValueError("Gemini client not initialized")
        
        models = self.client.models.list()
        return [model.name for model in models]
    
    def generate_content(self, prompt, model=None):
        """
        Generate content using Gemini AI
        
        Args:
            prompt (str): The prompt to generate content from
            model (str, optional): The model to use. Defaults to config value.
        
        Returns:
            str: Generated text response
        """
        if not self.client:
            raise ValueError("Gemini client not initialized")
        
        if model is None:
            model = current_app.config.get('GEMINI_MODEL', 'models/gemini-2.5-flash')
        
        response = self.client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        return response.text

# Singleton instance
gemini_service = GeminiService()
