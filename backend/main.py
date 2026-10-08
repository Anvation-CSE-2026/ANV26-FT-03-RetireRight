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
    
    if not client:
        return {
            "reply": "DIAGNOSTIC ERROR: Client not initialized. Check your API key.",
            "state_override": {}
        }
    
    prompt = f"""
    You are a financial AI. User profile:
    {json.dumps(state)}
    
    User message: "{msg}"
    
    Respond ONLY with a raw JSON object (NO MARKDOWN). Do not wrap in ```json.
    {{
        "reply": "Your conversational advice.",
        "state_override": {{}}
    }}
    """
    
    try:
        # BULLETPROOF LOOP: Try every standard model name until one succeeds
        response = None
        last_error = ""
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
                break  # Success! Break out of the loop
            except Exception as inner_e:
                last_error = str(inner_e)
                continue  # 404 Error? Immediately try the next model
                
        if not response:
            raise Exception(f"All models failed. Last API error: {last_error}")

        raw_text = response.text.strip()
        
        # Bruteforce markdown cleaner
        if raw_text.startswith("```json"): raw_text = raw_text[7:]
        if raw_text.startswith("```"): raw_text = raw_text[3:]
        if raw_text.endswith("```"): raw_text = raw_text[:-3]
        raw_text = raw_text.strip()
        
        ai_result = json.loads(raw_text)
        
        return {
            "reply": ai_result.get("reply", "Plan updated successfully."),
            "state_override": ai_result.get("state_override", {})
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "reply": f"DIAGNOSTIC ERROR: {error_msg}",
            "state_override": {}
        }