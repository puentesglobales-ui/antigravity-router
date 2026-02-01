
import re
import json

class V0Classifier:
    """
    Antigravity Router - V0 Classifier (Determinístico · Cost-Aware · Product-Aware)
    Implementación estricta del 'Canonical Prompt'.
    """

    def __init__(self):
        # Taxonomía de Intenciones (Regex Keywords para simulación)
        self.STATIC_INTENTS = {
            "greeting": r"^(hola|buenas|buenos dias|tardes|noches|hi|hello)$",
            "closing": r"^(chau|adios|gracias|ok|listo)$",
            "faq_pricing": r"(precio|costo|cuanto sale|planes|tarifas)",
            "faq_schedule": r"(horario|dias|agenda|turno)",
            "faq_product_info": r"(que es|como funciona|info|informacion)",
            "confirmation_yes": r"^(si|claro|correcto|dale)$",
            "confirmation_no": r"^(no|nunca|jamas)$",
        }
        
        self.TRANSACTIONAL_INTENTS = {
            "lead_capture": r"(contacto|llamanos|mail|correo)",
            # slot_filling se detecta por missing_slots
        }

        self.CONVERSATIONAL_INTENTS = {
            "explanation_request": r"(explicame|por que|diferencia)",
            "product_comparison": r"(comparar|vs|mejor que)",
        }

        self.CRITICAL_INTENTS = {
            "ats_evaluation": r"(evaluacion|candidato|perfil|liderazgo|soft skills)",
            "legal_or_health_related": r"(legal|contrato|salud|medico|denuncia)",
        }

    def _detect_intent_and_complexity(self, text, missing_slots):
        text = text.lower().strip()
        complexity = 0
        intent = "unknown"

        # Heurística 1: greeting/closing simples
        if re.match(r"^(hola|gracias|ok)$", text):
            return "greeting" if "hola" in text else "closing", 0

        # Heurística 2: Missing Slots -> Transactional
        if missing_slots and len(missing_slots) > 0:
            return "slot_filling", 10 # Pedido simple

        # Regex Matching for other intents
        # Priority: Critical > Conversational > Transactional > Static
        
        # 1. Critical
        for int_name, pattern in self.CRITICAL_INTENTS.items():
            if re.search(pattern, text):
                return int_name, 80 # Juicio humano
        
        # 2. Conversational
        for int_name, pattern in self.CONVERSATIONAL_INTENTS.items():
            if re.search(pattern, text):
                # Calcular complejidad extra
                if re.search(r"(si|depende|cuando)", text):
                    return int_name, 40 # Condicionales
                return int_name, 25 # Múltiples preguntas
        
        # 3. Transactional
        for int_name, pattern in self.TRANSACTIONAL_INTENTS.items():
            if re.search(pattern, text):
                return int_name, 10
        
        # 4. Static
        for int_name, pattern in self.STATIC_INTENTS.items():
            if re.search(pattern, text):
                return int_name, 0

        # Default fallback logic if nothing matches but we need to classify
        if len(text.split()) > 10:
             return "explanation_request", 25
        
        return "system_command", 0

    def _calculate_risk(self, product, intent, metadata):
        risk = 0
        
        # Base risk keywords (simplified)
        text = metadata.get("text", "").lower()
        if re.search(r"(tiempo real|voice)", metadata.get("channel", "")):
            risk += 20
        if re.search(r"(incorrecto|daño|error)", text):
            risk += 40
        if re.search(r"(legal|laboral)", text):
            risk += 60
        if re.search(r"(salud|accesibilidad)", text):
            risk += 80

        # Context Heuristics
        if product == "ats" and intent != "greeting":
             # "Si product === ats Y intent ≠ greeting → mínimo conversational" -> affects category, but let's check risk prompts
             # "Si is_interview === true → mínimo critical" -> handled in category mostly, but prompt says risk:
             # "+80 -> accesibilidad / salud / entrevistas"
             if risk < 80: risk = 80 # Assuming ATS implies interview context often

        if metadata.get("is_interview"):
             if risk < 80: risk = 80
        
        if metadata.get("user_tier") == "enterprise":
            risk += 20
        
        return min(risk, 100)

    def _determine_category(self, intent, missing_slots, product, is_interview, score_complexity):
        # Default category based on intent groups
        if intent in self.STATIC_INTENTS: category = "static"
        elif intent in self.TRANSACTIONAL_INTENTS or intent == "slot_filling": category = "transactional"
        elif intent in self.CONVERSATIONAL_INTENTS: category = "conversational"
        elif intent in self.CRITICAL_INTENTS: category = "critical"
        else:
            # Fallback based on score
            if score_complexity >= 80: category = "critical"
            elif score_complexity >= 25: category = "conversational"
            else: category = "static"

        # Heurísticas Obligatorias overrides
        if missing_slots and len(missing_slots) > 0:
            category = "transactional"
        
        if product == "ats" and intent not in self.STATIC_INTENTS:
            if category in ["static", "transactional"]:
                category = "conversational"
        
        if is_interview:
            category = "critical"

        return category

    def _route(self, category):
        if category == "static": return "ANTIGRAVITY"
        if category == "transactional": return "ANTIGRAVITY"
        if category == "conversational": return "DEEPSEEK"
        if category == "critical": return "DEEPSEEK_THEN_GPT5"
        return "ANTIGRAVITY"

    def classify(self, input_data):
        text = input_data.get("text", "")
        metadata = input_data.get("metadata", {})
        channel = input_data.get("channel", "web")
        product = input_data.get("product", "")
        
        missing_slots = metadata.get("missing_slots", [])
        is_interview = metadata.get("is_interview", False)
        user_tier = metadata.get("user_tier", "free")

        # 1. Intent & Complexity
        # Need to pass text to risk calc too, effectively mocked here
        intent, complexity_score = self._detect_intent_and_complexity(text, missing_slots)

        # 2. Risk Score
        risk_score = self._calculate_risk(product, intent, {"text": text, "channel": channel, "is_interview": is_interview, "user_tier": user_tier})
        
        # 3. Category Determination (Overrides based on heuristics)
        category = self._determine_category(intent, missing_slots, product, is_interview, complexity_score)

        # 4. Route
        route_hint = self._route(category)

        # 5. Reason
        reason = f"Category: {category} matched. C={complexity_score}, R={risk_score}."
        if missing_slots: reason = "Transaccional: Faltan slots."
        if intent in self.STATIC_INTENTS: reason = "FAQ/Static directa."
        if is_interview: reason = "Crítico: Entrevista activa."


        return {
            "intent": intent,
            "category": category,
            "complexity_score": complexity_score,
            "risk_score": risk_score,
            "confidence": 0.95 if complexity_score < 40 else 0.85, # Simulated confidence
            "route_hint": route_hint,
            "reason": reason
        }

if __name__ == "__main__":
    # Test Exec in main
    classifier = V0Classifier()
    
    # Example 1: FAQ Pricing
    in1 = {
        "channel": "whatsapp",
        "product": "alex",
        "text": "hola, quiero saber el precio",
        "metadata": {"user_tier": "free", "missing_slots": []}
    }
    print(f"INPUT: {in1['text']}")
    print(json.dumps(classifier.classify(in1), indent=2))
    print("-" * 20)

    # Example 2: ATS Evaluation
    in2 = {
        "channel": "web",
        "product": "ats",
        "text": "creo que el candidato respondió bien pero dudó en liderazgo",
        "metadata": {"user_tier": "pro", "is_interview": False, "missing_slots": []} # Context suggests evaluation
    }
    print(f"INPUT: {in2['text']}")
    print(json.dumps(classifier.classify(in2), indent=2))
