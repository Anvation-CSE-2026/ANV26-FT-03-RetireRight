import os
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from backend.engine import run_simulation

app = FastAPI(title="RetireRight AI")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- REAL LLM INTEGRATION (Modern SDK) ---
GEMINI_API_KEY = "AQ.Ab8RN6LDimElRaS7KW4Waeicm7z_skxgI7d8nnZu_Zej9329IQ"

client = None
try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("\n✅ SUCCESS: Connected to Gemini using the new google-genai SDK!\n")
except Exception as e:
    print(f"\n❌ FAILED to initialize Gemini Client: {e}\n")


class PlanRequest(BaseModel):
    current_age: int = 30
    retire_age: int = 60
    current_savings: float = 50000.0
    annual_contribution: float = 15000.0
    annual_spend: float = 30000.0
    baseline_inflation: float = 0.025
    inflation_shock: bool = False
    medical_shock: bool = False
    career_shock: bool = False
    extra_work_years: int = 0
    extra_annual_savings: float = 0.0

class ChatQuery(BaseModel):
    message: str
    current_state: PlanRequest

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

@app.post("/api/simulate")
def simulate_plan(payload: PlanRequest):
    return run_simulation(**payload.model_dump())

@app.post("/api/chat")
def handle_chat(query: ChatQuery):
    msg = query.message.lower()
    state = query.current_state.model_dump()
    
    reply = ""
    override = {}
    
    # 1. ATTEMPT REAL AI NLP PARSING
    if client:
        prompt = f"""
        You are an autonomous FinTech retirement planning copilot with direct access to the user's simulation controls.
        Current Financial State:
        {json.dumps(state)}
        
        User input: "{msg}"
        
        TASK:
        If the user asks to fix the shortfall, recover, improve their score, or adjust to life shocks:
        1. Formulate a realistic adjustment strategy to eliminate the shortfall and return the plan to Surplus (A+ Grade).
        2. Set DIRECT absolute values in "state_override" for:
           - "retire_age": delayed retirement age (typically +2 to +6 years beyond current retire_age, between 60 and 68).
           - "annual_contribution": increased annual savings amount (e.g., raise by $3,000 to $8,000 to overcome inflation or shocks).
        3. If the user asks to toggle life shocks, set "inflation_shock", "medical_shock", or "career_shock" to true or false.

        Respond STRICTLY with a raw JSON object (NO MARKDOWN backticks):
        {{
            "reply": "Clear, concise 2-sentence explanation telling the user the exact slider adjustments applied.",
            "state_override": {{
                "retire_age": <integer or omit if unchanged>,
                "annual_contribution": <number or omit if unchanged>,
                "inflation_shock": <bool or omit if unchanged>,
                "medical_shock": <bool or omit if unchanged>,
                "career_shock": <bool or omit if unchanged>
            }}
        }}
        """
        
        models_to_test = [
            'gemini-1.5-pro',
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-pro',
            'gemini-3.5-flash'
        ]
        
        for model_name in models_to_test:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                
                ai_result = json.loads(raw_text)
                reply = ai_result.get("reply", "")
                override = ai_result.get("state_override", {})
                break
            except Exception:
                continue

    # 2. GUARANTEED SHORTFALL SOLVER (Fail-Safe if LLM is offline or omitted keys)
    is_fix_intent = any(keyword in msg for keyword in ["fix", "shortfall", "solve", "recover", "help", "repair", "balance"])
    
    if is_fix_intent:
        target_retire = max(state["retire_age"] + 4, 62)
        target_contrib = state["annual_contribution"] + 5000.0
        
        if "retire_age" not in override:
            override["retire_age"] = int(target_retire)
        if "annual_contribution" not in override:
            override["annual_contribution"] = float(target_contrib)
            
        if not reply:
            reply = f"I have adjusted your plan to absorb the shortfall: shifted retirement to age {override['retire_age']} and increased annual savings to ${int(override['annual_contribution']):,}. Watch your sliders update to the target trajectory."

    elif "inflation" in msg and "inflation_shock" not in override:
        override["inflation_shock"] = not state["inflation_shock"]
        mode = "applied" if override["inflation_shock"] else "cleared"
        reply = f"Inflation shock (+4% persistent cost inflation) has been {mode}."

    elif "medical" in msg and "medical_shock" not in override:
        override["medical_shock"] = not state["medical_shock"]
        mode = "triggered" if override["medical_shock"] else "cleared"
        reply = f"Unforeseen medical event ($45,000 expense at age 48) has been {mode}."

    elif "career" in msg and "career_shock" not in override:
        override["career_shock"] = not state["career_shock"]
        mode = "triggered" if override["career_shock"] else "cleared"
        reply = f"Income freeze scenario (2 years at age 40) has been {mode}."

    if not reply:
        reply = "I'm tracking your portfolio risks. You can ask to 'Fix the shortfall', 'Simulate inflation shock', or test life events."

    return {"reply": reply, "state_override": override}