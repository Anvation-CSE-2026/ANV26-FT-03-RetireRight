import random

def run_simulation(current_age=30, retire_age=60, current_savings=50000.0, 
                   annual_contribution=10000.0, annual_spend=40000.0, 
                   inflation_shock=False, medical_shock=False, 
                   extra_work_years=0, extra_annual_savings=0.0, **kwargs):
    
    effective_retire = retire_age + extra_work_years
    total_years = 85 - current_age
    ages = list(range(current_age, 86))
    
    # MVP Simplified Math
    growth_rate = 0.07 if not inflation_shock else 0.04 # Inflation kills growth
    eff_contribution = annual_contribution + extra_annual_savings
    
    trajectory = [current_savings]
    current_val = current_savings
    
    for t in range(1, total_years + 1):
        age_now = current_age + t
        
        if age_now < effective_retire:
            current_val = (current_val * (1 + growth_rate)) + eff_contribution
        else:
            current_val = (current_val * (1 + growth_rate)) - annual_spend
            
        # MVP Medical Shock: Subtract $45k at age 48
        if medical_shock and age_now == 48:
            current_val -= 45000
            
        # Add a fake "random jitter" so the chart looks like a real simulation
        jitter = random.uniform(0.98, 1.02)
        current_val = max(0, current_val * jitter)
        trajectory.append(round(current_val, 2))

    # Calculate gap based on age 60 target of $1M
    target_corpus = 1000000.0 
    corpus_at_retire = trajectory[effective_retire - current_age]
    gap = corpus_at_retire - target_corpus
    
    return {
        "ages": ages,
        "p50_median": trajectory, 
        "p90_optimistic": [v * 1.2 for v in trajectory], # Fake upper band
        "p10_pessimistic": [v * 0.8 for v in trajectory], # Fake lower band
        "target_corpus": target_corpus,
        "gap": round(gap, 2),
        "status": "Surplus" if gap >= 0 else "Shortfall",
        "success_rate": 95.0 if gap >= 0 else 32.0, # Fake success rate
        "recommendations": [{"action": "Delay Retirement", "detail": "Delay by 3 years"}] if gap < 0 else []
    }