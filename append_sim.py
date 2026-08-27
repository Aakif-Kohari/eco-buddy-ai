def render_simulations(household_id: int):
    st.header("What-If Sustainability Scenarios")
    st.markdown("Explore how major lifestyle changes would project onto your household's baseline carbon footprint.")
    
    from household_scenario_modeling import simulate_scenarios, calculate_payback_period, recommend_top_scenario
    
    scenarios = simulate_scenarios(household_id)
    
    if not scenarios:
        st.info("We need more activity data logged to run meaningful simulations. Start by logging some activities!")
        return
        
    top_scenario = recommend_top_scenario(household_id)
    if top_scenario:
        st.success(f"🌟 **Top Recommendation:** {top_scenario['title']} (reduces footprint by {top_scenario['reduction_kg']:.1f} kg CO2e)")
        
    st.markdown("---")
    
    for sc in scenarios:
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"### {sc['title']}")
            c1.write(sc['description'])
            
            payback = calculate_payback_period(sc['id'], household_id)
            payback_str = f"{payback:.1f} yrs" if payback and payback != float('inf') else "N/A"
            
            c2.metric("Est. Upfront Cost", sc['cost_estimate'])
            c2.metric("Financial Carbon Payback", payback_str)
            
            c3.metric("CO2e Reduction", f"-{sc['reduction_kg']:.1f} kg")
            c3.metric("% of Baseline", f"-{sc['reduction_pct']:.1f}%")
            
        st.divider()
