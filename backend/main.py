from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.engine import run_simulation

app = FastAPI(title="RetireRight AI")

# Serve UI static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    result = run_simulation(
        current_age=payload.current_age,
        retire_age=payload.retire_age,
        current_savings=payload.current_savings,
        annual_contribution=payload.annual_contribution,
        annual_spend=payload.annual_spend,
        baseline_inflation=payload.baseline_inflation,
        inflation_shock=payload.inflation_shock,
        medical_shock=payload.medical_shock,
        career_shock=payload.career_shock,
        extra_work_years=payload.extra_work_years,
        extra_annual_savings=payload.extra_annual_savings
    )
    return result

@app.post("/api/chat")
def handle_chat(query: ChatQuery):
    msg = query.message.lower()
    state = query.current_state.model_dump()
    override = {}
    reply = ""

    if "fix" in msg or "shortfall" in msg or "help" in msg:
        override = {"extra_work_years": 3, "extra_annual_savings": 3000.0}
        reply = "I calculated two primary adjustments: Delaying retirement by 3 years and increasing savings by $3,000/year to recover your baseline goal. Would you like to apply this adjustment?"
    elif "inflation" in msg:
        override = {"inflation_shock": not state["inflation_shock"]}
        mode = "applied" if override["inflation_shock"] else "removed"
        reply = f"Inflation shock scenario (8% persistent inflation) has been {mode}. Watch the shortfall metric update on the dashboard."
    elif "medical" in msg:
        override = {"medical_shock": not state["medical_shock"]}
        mode = "triggered" if override["medical_shock"] else "cleared"
        reply = f"A $45,000 unforeseen medical emergency at age 48 has been {mode}."
    elif "career" in msg or "job" in msg:
        override = {"career_shock": not state["career_shock"]}
        mode = "triggered" if override["career_shock"] else "cleared"
        reply = f"A 2-year income freeze scenario at age 40 has been {mode}."
    elif "reset" in msg:
        override = {
            "inflation_shock": False,
            "medical_shock": False,
            "career_shock": False,
            "extra_work_years": 0,
            "extra_annual_savings": 0.0
        }
        reply = "Resetting simulation to your clean baseline financial assumptions."
    else:
        reply = "I can test life shocks or balance your retirement gap. Try asking: 'Simulate inflation shock', 'Add medical emergency', or 'How do I fix the shortfall?'"

    return {"reply": reply, "state_override": override}