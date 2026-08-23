import os

base_dir = r"F:\ECSoC'26 Contributions\eco-buddy-ai"

# Append massive fuzz testing and projection tests
test_extension = '''
    def test_forecast_confidence_boundaries(self):
        """Extensive fuzz testing of the trend forecaster confidence bounds."""
        import random
        from environmental_benchmarking.advanced_math import TrendForecaster
        
        # Test 100 synthetic histories
        for _ in range(100):
            # Generate random history
            hist = [random.uniform(1000, 10000) for _ in range(random.randint(3, 20))]
            conf = TrendForecaster.calculate_projection_confidence(hist)
            self.assertTrue(0.0 <= conf <= 100.0)
            
            preds = TrendForecaster.forecast_next_periods(hist, 5)
            self.assertEqual(len(preds), 5)
            for p in preds:
                self.assertTrue(p >= 0.0) # No negative footprints

    def test_advanced_math_normalizations_fuzz(self):
        """Fuzz testing advanced math normalizers."""
        import random
        from environmental_benchmarking.advanced_math import DataNormalizer
        
        for _ in range(1000):
            val = random.uniform(-10000, 10000)
            mean = random.uniform(-5000, 5000)
            std_dev = random.uniform(0.1, 1000)
            
            # Z-score
            z = DataNormalizer.z_score_normalize(val, mean, std_dev)
            self.assertIsInstance(z, float)
            
            # Sigmoid
            s = DataNormalizer.sigmoid_normalize(val, mean, std_dev)
            self.assertTrue(0.0 <= s <= 1.0)
            
            # Robust scale
            p25 = mean - 100
            p75 = mean + 100
            rs = DataNormalizer.robust_scale(val, mean, p25, p75)
            self.assertIsInstance(rs, float)

    def test_recommendation_engine_fuzz(self):
        """Fuzz test the recommendation engine against random comparison objects."""
        import random
        from environmental_benchmarking.recommendations import RecommendationEngine
        from environmental_benchmarking.models import CategoryComparison
        
        engine = RecommendationEngine()
        categories = ["transport", "electricity", "diet", "flights"]
        
        for _ in range(500):
            comps = {}
            for cat in categories:
                comps[cat] = CategoryComparison(
                    category_name=cat,
                    user_value=random.uniform(0, 10000),
                    reference_mean=random.uniform(100, 5000),
                    reference_median=random.uniform(100, 5000),
                    percentile=random.uniform(0, 100),
                    is_better_than_average=random.choice([True, False]),
                    difference_from_mean=random.uniform(-1000, 1000),
                    percentage_difference=random.uniform(-100, 100),
                    normalized_score=random.uniform(0, 100)
                )
            
            recs = engine.generate_recommendations(comps)
            self.assertIsInstance(recs, list)
            # Depending on the random values, it should generate some strings
            for r in recs:
                self.assertIsInstance(r, str)
                self.assertTrue(len(r) > 5)
'''

with open(os.path.join(base_dir, "test_environmental_benchmarks_extended.py"), "a", encoding="utf-8") as f:
    f.write(test_extension)

# Modify the Streamlit page to add a Forecasting tab
page_file = os.path.join(base_dir, "pages", "25_Environmental_Benchmarking.py")
with open(page_file, "r", encoding="utf-8") as f:
    content = f.read()
    
# Replace tabs definition
content = content.replace(
    'tab1, tab2, tab3, tab4 = st.tabs(["📊 Category Breakdown", "📈 Historical Trends", "💡 Action Plan", "🌍 Data Explorer"])',
    'tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Category Breakdown", "📈 Historical Trends", "🔮 Forecasting", "💡 Action Plan", "🌍 Data Explorer"])'
)

forecasting_tab_code = '''
    with tab3:
        st.subheader("Footprint Forecasting")
        st.markdown("Predict your future environmental impact based on your historical trajectory.")
        
        forecast_data = analyzer.get_forecast(user_id, periods=6)
        preds = forecast_data.get("predicted_footprints", [])
        conf = forecast_data.get("confidence", 0.0)
        
        if len(preds) > 0 and len(history) > 1:
            st.metric("Projection Confidence", f"{conf:.1f}%")
            
            # Combine historical and future
            hist_trends = analyzer.calculate_trends(user_id, selected_profile_id)
            hist_dates = [d.strftime("%Y-%m-%d") for d in hist_trends.dates]
            hist_vals = hist_trends.footprints
            
            # Create synthetic future dates (assuming 1 month apart for visual)
            from dateutil.relativedelta import relativedelta
            last_date = hist_trends.dates[-1]
            future_dates = [(last_date + relativedelta(months=i)).strftime("%Y-%m-%d") for i in range(1, len(preds)+1)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist_dates, y=hist_vals,
                mode='lines+markers', name='Historical',
                line=dict(color='blue', width=3)
            ))
            fig.add_trace(go.Scatter(
                x=future_dates, y=preds,
                mode='lines+markers', name='Projected',
                line=dict(color='red', width=3, dash='dash')
            ))
            
            fig.update_layout(
                title="Historical vs Projected Carbon Footprint",
                xaxis_title="Timeline",
                yaxis_title="Footprint (kg CO2e)"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            if preds[-1] < hist_vals[-1]:
                st.success("Great job! Your trajectory shows your footprint is decreasing.")
            else:
                st.warning("Your projected footprint is increasing or stalling. Check the Action Plan tab!")
        else:
            st.info("Not enough historical data to generate a reliable forecast. Keep logging assessments!")

    with tab4:'''

content = content.replace("    with tab3:\n        st.subheader(\"Action Plan & Insights\")", forecasting_tab_code.lstrip() + '\n        st.subheader("Action Plan & Insights")')

# Replace the last `with tab4:` with `with tab5:`
content = content.replace("    with tab4:\n        st.subheader(\"Profile Data Explorer\")", "    with tab5:\n        st.subheader(\"Profile Data Explorer\")")

with open(page_file, "w", encoding="utf-8") as f:
    f.write(content)
