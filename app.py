import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import os
from datetime import datetime, timedelta
from utils import (
    load_data, 
    identify_vanity_metrics, 
    identify_valuable_metrics,
    get_top_metrics_by_department,
    calculate_metric_impact_score,
    get_metrics_to_remove
)

# Set page configuration
st.set_page_config(
    page_title="AI-Powered KPI Audit Tool",
    page_icon="📊",
    layout="wide"
)

# Add page styling and header
st.title("🔍 AI-Powered KPI Audit Tool")
st.markdown("""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>
    <h3>Identify vanity metrics and focus on what drives business outcomes</h3>
    <p>This tool analyzes your organization's KPIs to identify metrics that may be redundant, misleading, or have zero impact on business outcomes.</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar for filters and controls
with st.sidebar:
    st.header("About")
    st.info("""
    This KPI Audit Tool helps organizations:
    - Identify metrics that don't drive decisions
    - Find the most valuable metrics
    - Reduce dashboard clutter
    - Focus on metrics that matter
    """)
    
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Upload your KPI metrics CSV file", type=["csv"])
    
    # Sample data option
    use_sample_data = st.checkbox("Use sample data", value=True)
    
    # Add Audit Metrics button when a file is uploaded or sample data is selected
    if uploaded_file is not None or use_sample_data:
        if st.button("Audit Metrics", type="primary"):
            # Remove homepage flag if it exists
            if "show_homepage" in st.session_state:
                del st.session_state["show_homepage"]
            # Set flag to run analysis
            st.session_state["run_audit"] = True
            st.rerun()
    
    # Reset app button (returns to homepage)
    if st.button("Reset Analysis", key="reset_btn"):
        # Set a flag in session state to show the homepage
        st.session_state["show_homepage"] = True
        # Clear any other session state data
        for key in list(st.session_state.keys()):
            if key != "show_homepage":
                del st.session_state[key]
        st.rerun()  # Using st.rerun() to restart the app

# Main content
# Check if we should show the homepage
if "show_homepage" in st.session_state and st.session_state["show_homepage"]:
    # Display homepage content
    st.header("Welcome to the KPI Audit Tool")
    
    st.markdown("""
    ### What This Tool Does
    
    This AI-powered KPI Audit Tool helps you identify which metrics in your organization are actually driving business outcomes and which ones might be "vanity metrics" - numbers that look good but don't impact decisions.
    
    ### Getting Started
    
    1. Use the sidebar on the left to upload your KPI data in CSV format
    2. Or simply use our sample data to see how the tool works
    3. Explore the different tabs to see the analysis:
        - **Metrics Overview**: See high-level distribution of metrics
        - **Vanity Metrics Analysis**: Identify metrics that may not be driving value
        - **Valuable Metrics**: Find your most impactful KPIs
        - **Recommendations**: Get specific advice for each department
    
    ### About Vanity Metrics
    
    Vanity metrics are measurements that look impressive but don't actually help you make better decisions. Examples include:
    - Social media follower counts that don't convert to sales
    - Page views without engagement
    - Downloads without active usage
    - Metrics that are visible in dashboards but never used for decisions
    
    ### Why This Matters
    
    Organizations often track dozens of metrics, but research shows only 5-7 KPIs typically drive 80% of business outcomes. This tool helps you focus on what matters.
    """)
    
    # Add a button to start analysis
    if st.button("Start Analysis", type="primary"):
        # Remove the homepage flag to show analysis
        if "show_homepage" in st.session_state:
            del st.session_state["show_homepage"]
        st.rerun()
    
    # Exit early - don't show the analysis
    st.stop()
    
# Load and process data
df = None

# Check if we need to run the audit (button was pressed)
run_analysis = False
if "run_audit" in st.session_state and st.session_state["run_audit"]:
    run_analysis = True
    # Clear the flag so it doesn't auto-run next time
    del st.session_state["run_audit"]

# Load data from file or sample if running analysis
if run_analysis:
    try:
        if uploaded_file is not None:
            try:
                df = load_data(uploaded_file)
            except Exception as e:
                st.error(f"Error loading uploaded file: {e}")
                st.error("Please check that your CSV file has the required format and columns.")
        elif use_sample_data:
            # Use included sample data
            try:
                sample_file_path = "attached_assets/week 2 - Problem_4_-_Vanity_Metrics_Dashboard__Revised_.csv"
                if os.path.exists(sample_file_path):
                    df = load_data(sample_file_path)
                else:
                    alternative_path = "week 2 - Problem_4_-_Vanity_Metrics_Dashboard__Revised_.csv"
                    df = load_data(alternative_path)
            except Exception as e:
                st.error(f"Could not load sample data file: {e}")
                st.error("Please upload your own CSV file.")
    except Exception as e:
        st.error(f"An unexpected error occurred while loading data: {e}")
        st.info("Try uploading a different file or using the sample data.")
else:
    # If not running analysis, show a message to prompt user to run audit
    if not ("show_homepage" in st.session_state and st.session_state["show_homepage"]):
        st.info("👈 Use the sidebar to upload a CSV file or use sample data, then click 'Audit Metrics' to analyze your data")
        # Preview of data capabilities with some sample screenshots
        st.markdown("""
        ## What You'll Get
        
        After clicking the 'Audit Metrics' button, you'll get a complete analysis of your metrics, including:
        
        * Identification of potential vanity metrics
        * Analysis of your most valuable KPIs
        * Department-specific recommendations
        * Dashboard cleanup recommendations
        
        This tool helps focus your organization on metrics that actually drive business outcomes.
        """)

if df is not None:
    # Display dataset overview
    st.header("Dataset Overview")
    
    # Key metrics for overview
    metrics_count = len(df)
    departments = df['Department'].nunique()
    visible_count = len(df[df['Visible_in_Dashboard'] == 'Yes'])
    decision_count = len(df[df['Used_in_Decision_Making'] == 'Yes'])
    
    # Create metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Metrics", metrics_count)
    with col2:
        st.metric("Departments", departments)
    with col3:
        st.metric("Metrics in Dashboard", visible_count)
    with col4:
        st.metric("Decision-Driving Metrics", decision_count)
    
    # Data preview
    with st.expander("Preview Raw Data"):
        st.dataframe(df)
    
    # Initialize variables to avoid "possibly unbound" errors
    analyzed_df = None
    vanity_df = None
    top_metrics = {}
    metrics_to_remove = pd.DataFrame()
    impact_scores = pd.DataFrame()
    
    # Process metrics
    with st.spinner("Analyzing metrics..."):
        try:
            # Apply the analysis algorithms
            vanity_df = identify_vanity_metrics(df)
            analyzed_df = identify_valuable_metrics(vanity_df)
            
            # Get additional derived data
            top_metrics = get_top_metrics_by_department(analyzed_df, n=3)
            metrics_to_remove = get_metrics_to_remove(analyzed_df)
            impact_scores = calculate_metric_impact_score(analyzed_df)
        except Exception as e:
            st.error(f"Error during metrics analysis: {e}")
            st.error("There may be an issue with the format of your data. Please ensure it contains all required columns with the correct data types.")
            st.stop()  # Stop execution if analysis fails
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Metrics Overview", 
        "Vanity Metrics Analysis", 
        "Valuable Metrics", 
        "Recommendations"
    ])
    
    with tab1:
        st.header("Metrics Distribution Overview")
        
        # Department-wise metrics distribution
        st.subheader("Metrics by Department")
        dept_counts = df.groupby('Department').size().reset_index(name='count')
        dept_counts = dept_counts.sort_values('count', ascending=False)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(data=dept_counts, x='Department', y='count', ax=ax)
        plt.title("Number of Metrics by Department")
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig)
        
        # Visible vs Decision-making metrics
        st.subheader("Dashboard Visibility vs Decision Usage")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Metrics visibility
            visibility_counts = df['Visible_in_Dashboard'].value_counts()
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.pie(
                visibility_counts, 
                labels=visibility_counts.index, 
                autopct='%1.1f%%',
                colors=['#1f77b4', '#ff7f0e']
            )
            ax.set_title('Metrics in Dashboard')
            st.pyplot(fig)
        
        with col2:
            # Decision making
            decision_counts = df['Used_in_Decision_Making'].value_counts()
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.pie(
                decision_counts, 
                labels=decision_counts.index, 
                autopct='%1.1f%%',
                colors=['#1f77b4', '#ff7f0e']
            )
            ax.set_title('Metrics Used for Decisions')
            st.pyplot(fig)
        
        # Cross-tabulation of visibility vs decision making
        st.subheader("Dashboard Visibility vs Decision Making Cross-tabulation")
        cross_tab = pd.crosstab(
            df['Visible_in_Dashboard'], 
            df['Used_in_Decision_Making'],
            margins=True, 
            margins_name="Total"
        )
        st.dataframe(cross_tab)
        
        # Executive requests vs actual use
        st.subheader("Executive Requested vs Actual Use")
        exec_vs_use = pd.crosstab(
            df['Executive_Requested'], 
            df['Used_in_Decision_Making'],
            margins=True, 
            margins_name="Total"
        )
        st.dataframe(exec_vs_use)
    
    with tab2:
        st.header("Vanity Metrics Analysis")
        
        # Check if we have analysis data before proceeding
        if analyzed_df is None or 'is_vanity' not in analyzed_df.columns:
            st.error("Analysis data is missing or incomplete. Please try refreshing the page or uploading your data again.")
            st.stop()
            
        # Vanity metrics summary
        vanity_count = sum(analyzed_df['is_vanity'])
        st.subheader(f"Found {vanity_count} potential vanity metrics ({vanity_count/len(df):.1%} of total)")
        
        # Filter controls
        st.subheader("Filters")
        selected_departments = st.multiselect(
            "Select Departments", 
            options=sorted(df['Department'].unique()),
            default=sorted(df['Department'].unique())
        )
        
        # Filter data based on selection
        filtered_df = analyzed_df[analyzed_df['Department'].isin(selected_departments)]
        
        # Vanity metrics by department
        st.subheader("Vanity Metrics by Department")
        vanity_by_dept = filtered_df[filtered_df['is_vanity']].groupby('Department').size().reset_index(name='count')
        vanity_by_dept = vanity_by_dept.sort_values('count', ascending=False)
        
        if not vanity_by_dept.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=vanity_by_dept, x='Department', y='count', ax=ax)
            plt.title("Vanity Metrics by Department")
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)
        else:
            st.info("No vanity metrics found for the selected departments.")
        
        # List of vanity metrics with filtering
        st.subheader("All Vanity Metrics")
        vanity_metrics = filtered_df[filtered_df['is_vanity']].sort_values('vanity_score', ascending=False)
        
        if not vanity_metrics.empty:
            display_cols = [
                'Department', 'Metric_Name', 'vanity_score', 
                'vanity_reasons', 'Visible_in_Dashboard', 
                'Used_in_Decision_Making'
            ]
            st.dataframe(vanity_metrics[display_cols], use_container_width=True)
        else:
            st.info("No vanity metrics found for the selected filters.")
        
        # Vanity metrics interpretations
        if not vanity_metrics.empty:
            st.subheader("Vanity Metrics Interpretation")
            
            for idx, row in vanity_metrics.head(5).iterrows():
                with st.expander(f"{row['Department']} - {row['Metric_Name']} (Score: {row['vanity_score']})"):
                    st.markdown(f"**Why it's a vanity metric:** {row['vanity_reasons']}")
                    st.markdown(f"**Interpretation Notes:** {row['Interpretation_Notes']}")
                    st.markdown(f"**Last Reviewed:** {row['Last_Reviewed']}")
                    st.markdown(f"**Last Used for Decision:** {row['Metric_Last_Used_For_Decision']}")
    
    with tab3:
        st.header("Valuable Metrics Analysis")
        
        # Valuable metrics summary
        valuable_count = sum(analyzed_df['is_high_value'])
        st.subheader(f"Found {valuable_count} high-value metrics ({valuable_count/len(df):.1%} of total)")
        
        # Filter controls
        st.subheader("Filters")
        selected_departments_valuable = st.multiselect(
            "Select Departments", 
            options=sorted(df['Department'].unique()),
            default=sorted(df['Department'].unique()),
            key="valuable_dept_filter"
        )
        
        # Filter data based on selection
        filtered_df_valuable = analyzed_df[analyzed_df['Department'].isin(selected_departments_valuable)]
        
        # Valuable metrics by department
        st.subheader("High-Value Metrics by Department")
        value_by_dept = filtered_df_valuable[filtered_df_valuable['is_high_value']].groupby('Department').size().reset_index(name='count')
        value_by_dept = value_by_dept.sort_values('count', ascending=False)
        
        if not value_by_dept.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=value_by_dept, x='Department', y='count', ax=ax)
            plt.title("High-Value Metrics by Department")
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)
        else:
            st.info("No high-value metrics found for the selected departments.")
        
        # List of valuable metrics
        st.subheader("All High-Value Metrics")
        high_value_metrics = filtered_df_valuable[filtered_df_valuable['is_high_value']].sort_values('value_score', ascending=False)
        
        if not high_value_metrics.empty:
            display_cols = [
                'Department', 'Metric_Name', 'value_score', 
                'value_reasons', 'Used_in_Decision_Making',
                'Visible_in_Dashboard'
            ]
            st.dataframe(high_value_metrics[display_cols], use_container_width=True)
        else:
            st.info("No high-value metrics found for the selected filters.")
        
        # Top valuable metrics details
        if not high_value_metrics.empty:
            st.subheader("High-Value Metrics Details")
            
            for idx, row in high_value_metrics.head(5).iterrows():
                with st.expander(f"{row['Department']} - {row['Metric_Name']} (Score: {row['value_score']})"):
                    st.markdown(f"**Why it's valuable:** {row['value_reasons']}")
                    st.markdown(f"**Interpretation Notes:** {row['Interpretation_Notes']}")
                    st.markdown(f"**Last Reviewed:** {row['Last_Reviewed']}")
                    st.markdown(f"**Last Used for Decision:** {row['Metric_Last_Used_For_Decision']}")
        
        # Metric Potential Assessment
        st.subheader("Metrics Value Distribution")
        
        # Create a figure showing distribution of value scores
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(analyzed_df['value_score'], bins=10, kde=True, ax=ax)
        plt.title("Distribution of Metric Value Scores")
        plt.xlabel("Value Score")
        plt.ylabel("Count")
        st.pyplot(fig)
    
    with tab4:
        st.header("Recommendations")
        
        # Get top metrics by department
        st.subheader("Top 3 Metrics by Department")
        
        # Department selector for focused view
        selected_dept = st.selectbox(
            "Select Department for Detailed View", 
            options=['All Departments'] + sorted(df['Department'].unique())
        )
        
        if selected_dept == 'All Departments':
            display_depts = sorted(df['Department'].unique())
        else:
            display_depts = [selected_dept]
        
        # Display recommendations for selected departments
        for dept in display_depts:
            if dept in top_metrics:
                with st.expander(f"{dept} Department - Top Metrics", expanded=(selected_dept != 'All Departments')):
                    metrics_df = top_metrics[dept]
                    if len(metrics_df) > 0:
                        st.write(f"**Recommended metrics for {dept}:**")
                        for idx, row in metrics_df.iterrows():
                            st.markdown(f"- **{row['Metric_Name']}** (Value Score: {row['value_score']})")
                            st.markdown(f"  - *Why it matters*: {row['value_reasons']}")
                            st.markdown(f"  - *Last used*: {row['Metric_Last_Used_For_Decision']}")
                            
                            # Is this metric already in dashboard?
                            if row['Visible_in_Dashboard'] == 'Yes':
                                st.markdown("  - ✅ *Already in dashboard*")
                            else:
                                st.markdown("  - ⚠️ *Not in dashboard - consider adding*")
                    else:
                        st.write(f"No high-value metrics found for {dept}.")
        
        # Metrics to remove
        st.subheader("Recommended Metrics to Remove from Dashboard")
        
        if selected_dept == 'All Departments':
            metrics_to_remove_filtered = metrics_to_remove
        else:
            metrics_to_remove_filtered = metrics_to_remove[metrics_to_remove['Department'] == selected_dept]
        
        if len(metrics_to_remove_filtered) > 0:
            # Display count of metrics to remove
            st.write(f"Found {len(metrics_to_remove_filtered)} metrics recommended for removal from dashboards.")
            
            # Create a table view
            display_cols = [
                'Department', 'Metric_Name', 'vanity_score', 
                'vanity_reasons', 'Metric_Last_Used_For_Decision'
            ]
            st.dataframe(metrics_to_remove_filtered[display_cols], use_container_width=True)
            
            # Detailed view
            for idx, row in metrics_to_remove_filtered.iterrows():
                with st.expander(f"{row['Department']} - {row['Metric_Name']}"):
                    st.markdown(f"**Why it's a vanity metric**: {row['vanity_reasons']}")
                    st.markdown(f"**Interpretation Notes**: {row['Interpretation_Notes']}")
                    st.markdown(f"**Last Reviewed**: {row['Last_Reviewed']}")
                    st.markdown(f"**Last Used for Decision**: {row['Metric_Last_Used_For_Decision']}")
        else:
            st.info("No metrics recommended for removal with the current filters.")
        
        # Dashboard cleanup summary
        st.subheader("Dashboard Cleanup Impact")
        
        if selected_dept == 'All Departments':
            total_dashboard = len(analyzed_df[analyzed_df['Visible_in_Dashboard'] == 'Yes'])
            removable = len(metrics_to_remove)
        else:
            dept_df = analyzed_df[analyzed_df['Department'] == selected_dept]
            total_dashboard = len(dept_df[dept_df['Visible_in_Dashboard'] == 'Yes'])
            removable = len(metrics_to_remove_filtered)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Dashboard Metrics", total_dashboard)
        with col2:
            st.metric("Recommended for Removal", removable)
        with col3:
            reduction_pct = 0 if total_dashboard == 0 else (removable/total_dashboard*100)
            st.metric("Dashboard Size Reduction", f"{reduction_pct:.1f}%")
        
        # Final recommendations
        st.subheader("Executive Summary")
        st.markdown("""
        ### Key Findings and Recommendations:
        
        Based on our analysis, we recommend:
        
        1. **Remove identified vanity metrics** from dashboards to reduce noise and focus attention on metrics that matter
        
        2. **Elevate high-value metrics** to ensure they're prominently displayed and regularly reviewed
        
        3. **Establish a quarterly metrics review process** to prevent dashboard bloat over time
        
        4. **Implement clear criteria for new metrics** before adding them to dashboards:
           - Is it tied to business outcomes?
           - Will it drive decisions?
           - Is it actionable?
           - Does it replace an existing metric?
        
        5. **Consider department-specific dashboard redesigns** focusing on the top recommended metrics
        """)
        
        # Action plan template
        st.subheader("Action Plan Template")
        st.markdown("""
        ### Suggested 30-60-90 Day Plan:
        
        **First 30 Days:**
        - Remove the top 5 vanity metrics from dashboards
        - Elevate the top 3 valuable metrics for each department
        - Schedule metrics review sessions with each department
        
        **60 Days:**
        - Implement all dashboard cleanup recommendations
        - Create new dashboard layouts focusing on valuable metrics
        - Establish metrics governance process
        
        **90 Days:**
        - Measure impact of dashboard changes on decision-making
        - Train teams on metrics evaluation criteria
        - Re-run KPI audit to measure improvement
        """)
else:
    # Show introduction if no data is loaded
    st.info("👈 Please upload a CSV file with KPI metrics data or use the sample data to get started.")
    
    st.header("How This Tool Works")
    st.markdown("""
    ### Identify and eliminate vanity metrics with AI-powered analysis
    
    This tool helps you:
    
    1. **Analyze your organization's KPIs** to identify which ones are actually driving value
    
    2. **Identify vanity metrics** that are visible but not used in decision-making
    
    3. **Get department-specific recommendations** for which metrics to keep and which to remove
    
    4. **Visualize metric usage patterns** across your organization
    
    5. **Generate an actionable improvement plan** to focus on metrics that matter
    
    ### Getting Started
    
    1. Upload your KPI metrics CSV file using the sidebar
    2. Review the analysis across the different tabs
    3. Use the recommendations to streamline your dashboards
    
    ### Sample Data Format
    
    Your CSV file should include columns for:
    - Department
    - Metric_Name
    - Visible_in_Dashboard (Yes/No)
    - Used_in_Decision_Making (Yes/No)
    - Executive_Requested (Yes/No)
    - Last_Reviewed (timeframe)
    - Metric_Last_Used_For_Decision (timeframe)
    - Interpretation_Notes (additional context)
    """)
