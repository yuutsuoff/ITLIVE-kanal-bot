import json
import logging
import os
import re
import asyncio
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# API Keys
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY", "")).strip()
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")).strip()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# Standard Gemini Models - Optimized order: Fast models first
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro"
]

# Cache models to avoid overhead
_model_cache = {}

# Clients
openai_client = None
if OPENAI_API_KEY and len(OPENAI_API_KEY) > 10:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

claude_client = None
if ANTHROPIC_API_KEY and len(ANTHROPIC_API_KEY) > 10:
    try:
        from anthropic import AsyncAnthropic
        claude_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Claude: {e}")

# Track if Gemini is configured
_gemini_configured = False
if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_configured = True
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")

        _gemini_configured = True
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")

async def call_gemini(prompt: str, system: str = None):
    global _gemini_configured, _model_cache
    if not _gemini_configured:
        if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                _gemini_configured = True
            except Exception as e:
                logger.error(f"Lazy configuration of Gemini failed: {e}")
                return None
        else:
            return None
    
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    
    for model_name in GEMINI_MODELS:
        try:
            if model_name not in _model_cache:
                _model_cache[model_name] = genai.GenerativeModel(
                    model_name=model_name,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
            
            model = _model_cache[model_name]
            # Use a timeout if supported, otherwise just rely on the async call
            response = await asyncio.wait_for(model.generate_content_async(full_prompt), timeout=15.0)
            if response and response.text:
                return response.text
        except asyncio.TimeoutError:
            logger.warning(f"Gemini timeout with {model_name}")
            continue
        except Exception as e:
            logger.error(f"Gemini error with {model_name}: {e}")
            continue
    return None

async def call_openai(prompt: str, system: str = None):
    if not openai_client:
        return None
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API Error: {e}")
        return None

async def call_claude(prompt: str, system: str = None):
    if not claude_client:
        logger.warning("Claude client is not initialized.")
        return None
    try:
        params = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system:
            params["system"] = system
        response = await claude_client.messages.create(**params)
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API Error: {e}")
        return None

async def call_ai(prompt: str, system: str = None):
    # Try OpenAI first if configured
    if openai_client:
        resp = await call_openai(prompt, system)
        if resp:
            return resp

    # Try Gemini
    resp = await call_gemini(prompt, system)
    if resp:
        return resp
    
    # Try Claude
    logger.info("OpenAI and Gemini failed, trying Claude...")
    return await call_claude(prompt, system)


async def generate_next_question(candidate_info: str, qa_history: str, question_num: int) -> str:
    prompt = f"""
    Sen ITLIVE Academy uchun HR mutaxassisisan. Nomzod bilan interaktiv suhbat o'tkazyapsan.
    
    Nomzod ma'lumotlari:
    {candidate_info}
    
    Hozirgacha bo'lgan suhbat tarixi:
    {qa_history if qa_history else "Suhbat endi boshlandi."}
    
    Vazifang:
    Bu {question_num}-savol. Nomzod tanlagan SOHASIGA oid (masalan: HR, Mentor, Admin, Assistant va h.k.) professional va kreativ savol ber.
    Savol nomzodning tajribasi va qobiliyatini ochib berishga xizmat qilsin.
    
    Qoida:
    1. Faqat SAVOL matnini qaytar.
    2. Qo'shimcha gaplar (masalan: "Yaxshi", "Navbatdagi savol") qo'shma.
    3. Oldingi savollarni takrorlama.
    """
    
    response_text = await call_ai(prompt)
    if not response_text:
        # If both AI fail, we should try one more time or return a generic but "AI-like" error
        # Instead of hardcoded general questions, we tell the user there was a connection issue
        # but keep it in Uzbek.
        return "Kechirasiz, sun'iy intellekt bilan bog'lanishda muammo bo'ldi. Iltimos, birozdan so'ng qayta urinib ko'ring yoki /start bosing."
    
    return response_text.strip()


async def evaluate_candidate_answers(qa_pairs: str) -> dict:
    system_prompt = """
    Sen ITLIVE Academy uchun HR mutaxassisisan. Nomzodning javoblarini baholaysan.
    Faqat JSON qaytar:
    {"logic_score":0-100, "technical_score":0-100, "clarity_score":0-100, "overall_score":0-100, 
     "strengths":[], "weaknesses":[], "recommendation":"hire|maybe|reject", "summary":""}
    """
    response_text = await call_ai(qa_pairs, system=system_prompt)
    if not response_text:
        return None
    try:
        text = re.sub(r'```json\s*(.*?)\s*```', r'\1', response_text, flags=re.DOTALL)
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse AI JSON: {e}")
        return None
