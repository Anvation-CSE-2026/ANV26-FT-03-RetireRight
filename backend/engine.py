import numpy as np

def run_simulation(
    current_age: int = 30,
    retire_age: int = 60,
    death_age: int = 85,
    current_savings: float = 50000.0,
    annual_contribution: float = 10000.0,
    annual_spend: float = 40000.0,
    baseline_inflation: float = 0.04,
    inflation_shock: bool = False,
    medical_shock: bool = False,
    career_shock: bool = False,
    extra_work_years: int = 0,
    extra_annual_savings: float = 0.0,
    num_simulations: int = 200
):
    effective_retire_age = retire_age + extra_work_years
    total_years = death_age - current_age
    ages = list(range(current_age, death_age + 1))
    
    # Financial parameters
    mean_market_return = 0.08
    market_volatility = 0.12
    
    # Effective inflation and contribution
    eff_inflation = baseline_inflation + (0.04 if inflation_shock else 0.0)
    eff_contribution = annual_contribution + extra_annual_savings
    
    # Trajectory matrix: [simulations, total_years + 1]
    trajectories = np.zeros((num_simulations, total_years + 1))
    trajectories[:, 0] = current_savings
    
    np.random.seed(42)  # Consistent demo reproducibility
    
    for t in range(total_years):
        age_now = current_age + t
        # Random annual market return for each simulation
        market_returns = np.random.normal(mean_market_return, market_volatility, num_simulations)
        cost_multiplier = (1.0 + eff_inflation) ** t
        
        # Apply Career Shock (e.g. 2 years of zero income/savings at age 40-41)
        is_career_interrupted = career_shock and (40 <= age_now <= 41)
        
        # Working Phase
        if age_now < effective_retire_age:
            yearly_inflow = 0.0 if is_career_interrupted else eff_contribution
            trajectories[:, t + 1] = trajectories[:, t] * (1.0 + market_returns) + yearly_inflow
        # Retirement Phase
        else:
            yearly_outflow = annual_spend * cost_multiplier
            trajectories[:, t + 1] = np.maximum(0.0, trajectories[:, t] * (1.0 + market_returns) - yearly_outflow)
            
        # Apply Medical Shock (One-time lump sum expense of $45,000 at age 48)
        if medical_shock and age_now == 48:
            trajectories[:, t + 1] = np.maximum(0.0, trajectories[:, t + 1] - 45000.0)

    # Statistical percentiles across runs
    p10 = np.percentile(trajectories, 10, axis=0).tolist()  # Bear market
    p50 = np.percentile(trajectories, 50, axis=0).tolist()  # Median expected path
    p90 = np.percentile(trajectories, 90, axis=0).tolist()  # Bull market

    # Metric evaluation at retirement age
    retire_index = min(effective_retire_age - current_age, total_years)
    median_corpus_at_retire = p50[retire_index]
    
    # Target corpus based on 25x adjusted retirement spending (4% safe withdrawal rule)
    target_corpus = (annual_spend * ((1.0 + eff_inflation) ** retire_index)) * 25.0
    gap = median_corpus_at_retire - target_corpus
    
    # Success probability (% of simulations solvent at age 85)
    success_rate = float(np.sum(trajectories[:, -1] > 0) / num_simulations * 100.0)

    # Actionable adjustment recommendation engine
    recommendations = []
    if gap < 0:
        recommendations.append({
            "action": "Delay Retirement",
            "detail": "Delay retirement by 3 years to continue compounding and defer portfolio drawdown.",
            "param": "delay_3"
        })
        recommendations.append({
            "action": "Boost Annual Savings",
            "detail": f"Increase savings by ${(abs(gap) / max(1, retire_index * 1.5)):,.0f}/year to close the shortfall.",
            "param": "boost_savings"
        })
    else:
        recommendations.append({
            "action": "Plan Optimized",
            "detail": "Surplus achieved. Consider allocating excess capital into tax-advantaged estate funds.",
            "param": "optimal"
        })

    return {
        "ages": ages,
        "p10_pessimistic": [round(val, 2) for val in p10],
        "p50_median": [round(val, 2) for val in p50],
        "p90_optimistic": [round(val, 2) for val in p90],
        "target_corpus": round(target_corpus, 2),
        "median_corpus_at_retire": round(median_corpus_at_retire, 2),
        "gap": round(gap, 2),
        "status": "Surplus" if gap >= 0 else "Shortfall",
        "success_rate": round(success_rate, 1),
        "recommendations": recommendations
    }