
# Add to core/llm_service.py

async def extract_attributes(user_input: str) -> dict:
    """
    Extracts structured user attributes (facts) from the input using a fast model.
    e.g., "I live in Kyiv" -> {"location": "Kyiv"}
    """
    try:
        if len(user_input) < 10: return {} # Skip short inputs
        
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        prompt = f"""
        TASK: Extract PERMANENT FACTS about the user from the text.
        TEXT: "{user_input}"
        
        RULES:
        1. Extract only EXPLICIT facts (Name, Location, Job, Goals, Core Values).
        2. Ignore transient info (e.g., "I am hungry", "I am going to the store").
        3. If no facts, return empty JSON {{}}.
        
        OUTPUT JSON:
        {{
            "extracted": {{
                "<key>": "<value>",
                ...
            }}
        }}
        """
        
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_FAST,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        try:
            data = json.loads(response.text)
            return data.get("extracted", {})
        except json.JSONDecodeError:
            return {}
            
    except Exception as e:
        logger.warning(f"Attribute extraction failed: {e}")
        return {}
