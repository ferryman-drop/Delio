import streamlit as st
import plotly.express as px
import pandas as pd
from life_map import LifeCalculator

st.set_page_config(page_title="Delio Dashboard", layout="wide")

# Init
calc = LifeCalculator()

# Sidebar
st.sidebar.title("🧘 Delio Control")
user_id = st.sidebar.text_input("User ID", "593510565") # Default to user

if user_id:
    stats = calc.get_user_stats(user_id)
    
    st.sidebar.header(f"Level: {stats['level']}")
    st.sidebar.metric("XP", stats['xp'])
    st.sidebar.metric("Decisions", stats['decisions_count'])
    st.sidebar.metric("Insights", stats['insights_count'])

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["🗺️ Life Map", "🧠 System Health", "💰 Efficiency"])

    with tab1:
        st.header("Strategic Timeline")
        
        # Decisions Timeline
        df_dec = stats['decisions_df']
        if not df_dec.empty:
            df_dec['date'] = pd.to_datetime(df_dec['date'])
            fig = px.scatter(df_dec, x="date", y="topic", color="status", hover_data=["rationale"], 
                             title="Major Life Decisions")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_dec[['date', 'topic', 'status', 'expected_outcome']])
        else:
            st.info("No strategic decisions logged yet.")
            
        st.subheader("Extracted Insights")
        st.dataframe(stats['insights_df'])

    with tab2:
        st.header("DeepSeek Auditor Stats")
        
        audit_df = calc.get_system_health()
        if not audit_df.empty:
            audit_df['efficiency_score'] = pd.to_numeric(audit_df['efficiency_score'])
            
            # KPI
            avg_score = audit_df['efficiency_score'].mean()
            st.metric("Avg Efficiency Score", f"{avg_score:.1f}/10")
            
            # Chart
            fig_audit = px.line(audit_df, x="date", y="efficiency_score", title="Response Quality Over Time", markers=True)
            st.plotly_chart(fig_audit)
            
            # Log View
            st.subheader("Recent Critiques")
            st.dataframe(audit_df[['date', 'query', 'efficiency_score', 'critique', 'model_used']])
        else:
            st.info("No audit logs found yet.")

    with tab3:
        st.header("Self-Learning Router Efficiency")
        
        tele_df = calc.get_pricing_stats()
        if not tele_df.empty:
            total_cost = tele_df['cost_est'].sum()
            total_tokens = tele_df['input_tokens'].sum() + tele_df['output_tokens'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Est. Cost", f"${total_cost:.4f}")
            c2.metric("Total Tokens", f"{total_tokens:,}")
            c3.metric("Interactions", len(tele_df))
            
            # Graphs
            st.subheader("Model Usage Distribution")
            fig_model = px.pie(tele_df, names="model_selected", title="Routing Choices")
            st.plotly_chart(fig_model)
            
            st.subheader("Adaptive Weights (Live)")
            import routing_learner
            weights = routing_learner.load_weights()
            st.json(weights)
            
        else:
            st.info("No telemetry data yet.")
else:
    st.warning("Enter User ID to view stats.")
