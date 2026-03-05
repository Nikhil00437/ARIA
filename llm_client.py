import json
from openai import OpenAI
from extract import offline_classify
from constants import INTENT_CLASSIFIER_PROMPT, SUMMARIZE_PROMPT, EXPLAIN_PROMPT

client_llm = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

CHAT_MODEL    = "qwen3-vl-8b-instruct"
INTENT_MODEL  = "oh-dcft-v3.1-claude-3-5-sonnet-20241022"
VALID_MODES = (
    "chat", "command", "wikipedia", "browser", "music", "search",
    "show_apps", "time", "quick_open", "powershell", "explain",
    "history", "rerun", "image_gen",
)

def classify_intent(user_input: str) -> dict:
    offline = offline_classify(user_input)
    if offline: return offline
    try:
        messages = [
            {"role": "system", "content": INTENT_CLASSIFIER_PROMPT},
            {"role": "user",   "content": user_input},
        ]
        completion = client_llm.chat.completions.create(
            model=INTENT_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=200,
        )
        raw = completion.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        intent = json.loads(raw)
        assert intent["mode"] in VALID_MODES
        assert 0.0 <= intent["confidence"] <= 1.0
        return intent
    except Exception as e:
        return {
            "mode": "chat",
            "confidence": 0.0,
            "reason": f"Classification error: {e}",
            "action": None,
        }

def summarize_output(raw_output: str) -> str:
    try:
        comp = client_llm.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SUMMARIZE_PROMPT},
                {"role": "user",   "content": raw_output[:3000]},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return comp.choices[0].message.content.strip()
    except Exception as e:
        return f"(Summary unavailable: {e})\n\n{raw_output}"

def explain_output(subject: str, context: str = "") -> str:
    try:
        prompt = f"Subject: {subject}"
        if context:
            prompt += f"\n\nOutput/context:\n{context[:2000]}"
        comp = client_llm.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": EXPLAIN_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.5,
            max_tokens=600,
        )
        return comp.choices[0].message.content.strip()
    except Exception as e:
        return f"(Explanation unavailable: {e})"

def chat_completion(messages: list, temperature: float = 0.7, max_tokens: int = 800) -> str:
    comp = client_llm.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return comp.choices[0].message.content.strip()
