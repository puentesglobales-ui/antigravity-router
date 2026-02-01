
import json
import re
import time
import logging

# Configurar logging básico para auditoría
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AntigravityRouter")

class RouterEngineV1:
    """
    Antigravity Router V1 - Deterministic Decision Engine
    "Hardened, Boring, Profitable"
    """
    
    def __init__(self, ruleset_path="ruleset.json"):
        with open(ruleset_path, 'r', encoding='utf-8') as f:
            self.rules = json.load(f)
        
        # Pre-compile regexes for performance
        self._compile_regexes()
        
    def _compile_regexes(self):
        self.compiled_intents = {}
        for category, intent_list in self.rules["intents"].items():
            for item in intent_list:
                if item["patterns"]:
                    # Join patterns with OR
                    full_pattern = "|".join(item["patterns"])
                    self.compiled_intents[item["name"]] = {
                        "regex": re.compile(full_pattern, re.IGNORECASE),
                        "category": category
                    }

    def _match_intent(self, text, missing_slots):
        text = text.strip()
        
        # 1. Check Missing Slots (Hard Rule)
        if missing_slots and len(missing_slots) > 0:
            return "slot_filling", "transactional", 10

        # 2. Check Static/Transactional/Conversational/Critical Regexes
        # Order of check matters? Usually Specific > General.
        # But V1 Rules say "Static intents -> Antigravity". If it matches Greeting, it IS Greeting.
        
        # We iterate through intents based on Priority Groups defined implicitly or explicitly.
        # Let's verify Critical first to catch keywords, then Conversational, then Static?
        # Actually, if it says "Hola", it IS Static, even if it's in a critical context usually.
        # "Hola" should not trigger "Critical".
        # However, "Hola, quiero denunciar" -> Contains "denunciar" (Critical) and "Hola" (Static).
        # Context extraction is complex. For V1 Deterministic:
        # Match "Critical" keywords first? No, simple "Hola" is definitely static.
        # Let's match by category priority defined in implementation plan? No, user says:
        # "Static intents -> ANTIGRAVITY" (First check)
        
        # Check Static First
        for intent_name, data in self.compiled_intents.items():
            if data["category"] == "static":
                if data["regex"].search(text):
                    return intent_name, "static", 0
        
        # Check Transactional (regex based)
        for intent_name, data in self.compiled_intents.items():
            if data["category"] == "transactional":
                if data["regex"].search(text):
                    return intent_name, "transactional", 10

        # Check Critical
        for intent_name, data in self.compiled_intents.items():
            if data["category"] == "critical":
                if data["regex"].search(text):
                    return intent_name, "critical", 80

        # Check Conversational
        for intent_name, data in self.compiled_intents.items():
            if data["category"] == "conversational":
                # Special logic for conditionals mentioned in prompt can be refined here
                score = 40 if re.search(r"(si|depende|cuando)", text) else 25
                if data["regex"].search(text):
                    return intent_name, "conversational", score

        # Fallback
        if len(text.split()) > 7:
             return "explanation_request", "conversational", 40
             
        return "unknown", "static", 0 # Default low cost

    def _calculate_risk(self, text, intent, category, metadata):
        risk = 0
        channel = metadata.get("channel", "web")
        product = metadata.get("product", "generic")
        
        # Channel Rules
        if channel in self.rules["channel_rules"]:
            risk += self.rules["channel_rules"][channel]["risk_modifier"]
            
        # Product Rules
        if product in self.rules["product_rules"]:
            risk += self.rules["product_rules"][product].get("risk_modifier", 0)
            
        # Intent/Category Base Risk
        if category == "critical":
            risk += 60
        elif category == "conversational":
            risk += 20
            
        # Hard Keywords Risk (from prompt)
        text_lower = text.lower()
        if re.search(r"(legal|laboral|medico|denuncia)", text_lower):
            risk = max(risk, 60)
            
        # Enterprise Tier
        if metadata.get("user_tier") == "enterprise":
            risk += 20
            
        return min(risk, 100)

    def getRoute(self, input_data):
        start_time = time.time()
        
        text = input_data.get("text", "")
        metadata = input_data.get("metadata", {})
        channel = input_data.get("channel", "web")
        product = input_data.get("product", "generic")
        missing_slots = metadata.get("missing_slots", [])
        
        # --- PRIORITY OPTIMIZATIONS (Hard Checks) ---
        
        # RULE C: Aggressive Voice Force (Optimization)
        # If channel is voice and text is short (< 10 chars implies < 2s duration/noise), FORCE ANTIGRAVITY.
        if channel == "voice":
             if not text or len(text.strip()) < 10:
                  return {
                    "timestamp": time.time(),
                    "input_preview": "voice_noise",
                    "channel": channel,
                    "engine_used": "rules_engine",
                    "intent": "silence_or_noise",
                    "category": "static",
                    "complexity_score": 0,
                    "risk_score": 0,
                    "route_selected": "ANTIGRAVITY",
                    "estimated_cost": 0.0001,
                    "fallback_used": False,
                    "processing_time_ms": 0.0,
                    "note": "Rule C: Voice Aggressive Filter"
                }

        # RULE B: Strict Slot Filling
        # If any slots are missing, it IS transactional. No debate.
        if missing_slots and len(missing_slots) > 0:
             return {
                "timestamp": time.time(),
                "input_preview": text[:50],
                "channel": channel,
                "engine_used": "rules_engine",
                "intent": "slot_filling",
                "category": "transactional",
                "complexity_score": 10,
                "risk_score": 0,
                "route_selected": "ANTIGRAVITY",
                "estimated_cost": 0.0001,
                "fallback_used": False,
                "processing_time_ms": 0.0,
                "note": "Rule B: Strict Slot Filling"
            }

        # RULE A: Global Free Patterns (Strict)
        # Global dictionary of free patterns. If text MATCHES any of these (heuristic: short & confident), FORCE ANTIGRAVITY.
        # Patterns: Greetings, Closings, Short Confirmations.
        # Implemented as checking if the ENTIRE text is a match or contained in a short phrase.
        
        free_patterns = [
            "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", 
            "chau", "adios", "hasta luego", "gracias", "muchas gracias",
            "ok", "dale", "listo", "bueno", "perfecto", "genial",
            "si", "no", "claro", "exacto", "correcto", "asi es",
            "precio", "precios", "info", "ayuda", "menu", "salir"
        ]
        
        text_lower = text.lower().strip()
        # Clean punctuation for better matching
        text_clean = re.sub(r'[^\w\s]', '', text_lower)
        
        # Check 1: Exact Match (High Confidence)
        if text_clean in free_patterns:
             is_free = True
        # Check 2: Starts with pattern and is short (< 20 chars)
        elif len(text_clean) < 20 and any(text_clean.startswith(p) for p in free_patterns):
             is_free = True
        else:
             is_free = False
             
        if is_free:
             return {
                "timestamp": time.time(),
                "input_preview": text[:50],
                "channel": channel,
                "engine_used": "rules_engine",
                "intent": "quick_confirmation",
                "category": "static",
                "complexity_score": 0,
                "risk_score": 0,
                "route_selected": "ANTIGRAVITY",
                "estimated_cost": 0.0001,
                "fallback_used": False,
                "processing_time_ms": 0.0,
                "note": "Rule A: Global Free Patterns"
            }

        # 1. Intent Detection
        intent, category, complexity_score = self._match_intent(text, missing_slots)
        
        # 2. Financial/Product Overrides
        # Product Specific Rules
        if product in self.rules["product_rules"]:
            rule = self.rules["product_rules"][product]
            if "min_category_if_not_static" in rule:
                 if category not in ["static", "transactional"]:
                      # Check upgrades only if NOT caught by Rule A/B previously
                      pass 

        # 3. Risk Calculation
        risk_score = self._calculate_risk(text, intent, category, input_data)
        
        # 4. Final Routing Decision (The "NO Negotiable" Order)
        # - Static intents → ANTIGRAVITY
        # - Missing slots → ANTIGRAVITY (Handled via intent=slot_filling -> category=transactional)
        # - Low complexity → ANTIGRAVITY
        # - Medium reasoning → DEEPSEEK
        # - High risk / decisión crítica → GPT-5
        
        final_route = "ANTIGRAVITY"
        engine_used = "rules_engine"
        
        if category == "static":
            final_route = "ANTIGRAVITY"
        elif category == "transactional":
            final_route = "ANTIGRAVITY"
        elif category == "conversational":
            final_route = "DEEPSEEK"
        elif category == "critical":
            final_route = "DEEPSEEK_THEN_GPT5"
        
        # Complexity/Risk Threshold Overrides
        # "High risk / decisión crítica → GPT-5"
        if risk_score >= self.rules["thresholds"]["risk"]["high"]:
            final_route = "DEEPSEEK_THEN_GPT5"
            category = "critical" # Force category update for consistency
            
        target = final_route

        # 5. Financial Safeguards
        # Timeout Check
        max_timeout = self.rules["financial_guardrails"]["timeouts_ms"].get(channel, 5000)
        estimated_latency = 0 # Placeholder for simulation
        
        # Cost Limit Check
        # Estimate cost based on route
        estimated_cost = 0.0
        if target == "ANTIGRAVITY": estimated_cost = 0.0000
        elif target == "DEEPSEEK": estimated_cost = 0.002
        elif target == "DEEPSEEK_THEN_GPT5": estimated_cost = 0.025
        
        hard_limit = self.rules["financial_guardrails"]["max_cost_per_request_usd"]
        fallback_used = False
        
        if estimated_cost > hard_limit:
            logger.warning(f"Cost limit exceeded ({estimated_cost} > {hard_limit}). Fallback to ANTIGRAVITY.")
            target = "ANTIGRAVITY"
            fallback_used = True
            estimated_cost = 0.0001

        # Log Metrics
        # - engine_used
        # - intent
        # - complexity_score
        # - estimated_cost
        # - fallback_used (true/false)
        
        log_entry = {
            "timestamp": time.time(),
            "input_preview": text[:50],
            "channel": channel,
            "engine_used": engine_used,
            "intent": intent,
            "category": category,
            "complexity_score": complexity_score,
            "risk_score": risk_score,
            "route_selected": target,
            "estimated_cost": estimated_cost,
            "fallback_used": fallback_used,
            "processing_time_ms": (time.time() - start_time) * 1000
        }
        
        # In production this goes to ELK/Datadog. Here we verify.
        return log_entry

if __name__ == "__main__":
    engine = RouterEngineV1()
    
    # Test cases
    inputs = [
        {"text": "hola", "channel": "whatsapp", "product": "alex"},
        {"text": "necesito agendar", "metadata": {"missing_slots": ["date"]}, "channel": "web"},
        {"text": "el candidato titubeó en la respuesta sobre sql", "product": "ats", "channel": "web"},
        {"text": "quiero denunciar un caso de mala praxis legal", "channel": "voice", "product": "talkme"}
    ]
    
    print("ROUTER V1 EXECUTION LOG")
    for inp in inputs:
        result = engine.getRoute(inp)
        print(json.dumps(result, indent=2))

