import os
import time
import requests
from typing import Dict, Any

import google.generativeai as genai
from openai import OpenAI

class LLMGateway:
    """
    The Gateway deals with the "Help me connect X" problem.
    It takes a route decision and executes the actual API call to the provider.
    """
    
    def __init__(self):
        # Env vars for keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        
        # Initialize Clients
        self.deepseek_client = None
        if self.deepseek_key:
            self.deepseek_client = OpenAI(api_key=self.deepseek_key, base_url="https://api.deepseek.com")
            
        self.openai_client = None 
        if self.openai_key:
             self.openai_client = OpenAI(api_key=self.openai_key)
             
        if self.google_key:
             genai.configure(api_key=self.google_key)

    def get_status(self):
         return {
             "openai": "configured" if self.openai_key else "missing_key",
             "deepseek": "configured" if self.deepseek_key else "missing_key",
             "google": "configured" if self.google_key else "missing_key"
         }
        
    def execute(self, route_decision: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the routing decision.
        If Antigravity -> Returns static confirmation.
        If DeepSeek/GPT5 -> Calls APIs.
        """
        route = route_decision.get("route_selected")
        text = input_data.get("text")
        
        response = {
            "route_decision": route_decision,
            "execution_result": None,
            "provider_latency_ms": 0
        }
        
        start = time.time()
        
        if route == "ANTIGRAVITY":
            # Immediate return (0 cost)
            response["execution_result"] = {
                "content": "ANTIGRAVITY_STATIC_RESPONSE", 
                "source": "static_rules",
                "note": "Traffic handled locally. No LLM cost."
            }
            
        elif route == "DEEPSEEK":
            response["execution_result"] = self._call_deepseek(text)

        elif route == "GOOGLE":
             response["execution_result"] = self._call_google(text)
            
        elif route == "DEEPSEEK_THEN_GPT5":
            # Waterfall Logic
            ds_result = self._call_deepseek(text)
            # Simulated confidence check (mock)
            if self._is_confident(ds_result):
                response["execution_result"] = ds_result
                response["execution_result"]["note"] = "Waterfall: DeepSeek sufficient."
            else:
                # Fallback to GPT-5
                gpt_result = self._call_gpt5(text)
                response["execution_result"] = gpt_result
                response["execution_result"]["note"] = "Waterfall: Escalated to GPT-5."

        response["provider_latency_ms"] = (time.time() - start) * 1000
        return response

    def _call_deepseek(self, text: str):
        if not self.deepseek_client:
            return {"error": "DeepSeek API Key missing", "content": "Error: Configure DEEPSEEK_API_KEY in Render"}
            
        try:
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": text},
                ],
                stream=False
            )
            return {
                "content": response.choices[0].message.content,
                "model": "deepseek-chat",
                "cost_estimated": 0.002 # DeepSeek is cheap
            }
        except Exception as e:
            return {"error": str(e), "content": "DeepSeek API Error"}

    def _call_google(self, text: str):
        if not self.google_key:
             return {"error": "Google API Key missing", "content": "Error: Configure GOOGLE_API_KEY in Render"}
        
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(text)
            return {
                "content": response.text,
                "model": "gemini-pro",
                "cost_estimated": 0.001
            }
        except Exception as e:
             return {"error": str(e), "content": "Google API Error"}

    def _call_gpt5(self, text: str):
        if not self.openai_client:
             return {"error": "OpenAI API Key missing", "content": "Error: Configure OPENAI_API_KEY in Render"}
             
        try:
             # Using gpt-4-turbo as proxy for 'gpt-5' or gpt-4o
             response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview", 
                messages=[{"role": "user", "content": text}]
             )
             return {
                "content": response.choices[0].message.content,
                "model": "gpt-4-turbo",
                "cost_estimated": 0.03
             }
        except Exception as e:
             return {"error": str(e), "content": "OpenAI API Error"}
        
    def _is_confident(self, result):
        # Placeholder for 'Self-Consistent' logic
        if "error" in result: return False
        return True
