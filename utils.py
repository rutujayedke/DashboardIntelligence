import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import re

def load_data(file_path):
    """Load and preprocess the KPI data from CSV"""
    df = pd.read_csv(file_path)
    
    # Clean column names (remove spaces, etc.)
    df.columns = [col.strip() for col in df.columns]
    
    # Perform basic data cleaning
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('Unknown').astype(str).str.strip()
    
    return df

def identify_vanity_metrics(df):
    """Identify metrics that show signs of being vanity metrics"""
    # Create a copy to avoid SettingWithCopyWarning
    result_df = df.copy()
    
    # Initialize vanity score
    result_df['vanity_score'] = 0
    result_df['vanity_reasons'] = ''
    
    # Rule 1: Visible but not used in decision making
    mask = (result_df['Visible_in_Dashboard'] == 'Yes') & (result_df['Used_in_Decision_Making'] == 'No')
    result_df.loc[mask, 'vanity_score'] += 3
    result_df.loc[mask, 'vanity_reasons'] += 'Visible but not used in decisions; '
    
    # Rule 2: Executive requested but not used in decisions
    mask = (result_df['Executive_Requested'] == 'Yes') & (result_df['Used_in_Decision_Making'] == 'No')
    result_df.loc[mask, 'vanity_score'] += 2
    result_df.loc[mask, 'vanity_reasons'] += 'Executive requested but not used; '
    
    # Rule 3: Not recently reviewed
    mask = (result_df['Last_Reviewed'] == 'Unknown') | (result_df['Last_Reviewed'] == 'Last quarter') | (result_df['Last_Reviewed'] == 'Last year')
    result_df.loc[mask, 'vanity_score'] += 1
    result_df.loc[mask, 'vanity_reasons'] += 'Not recently reviewed; '
    
    # Rule 4: Never or rarely used for decisions
    never_used = ['Never', 'Unknown', "Don't know"]
    mask = result_df['Metric_Last_Used_For_Decision'].isin(never_used)
    result_df.loc[mask, 'vanity_score'] += 2
    result_df.loc[mask, 'vanity_reasons'] += 'Never or rarely used for decisions; '
    
    # Rule 5: Check interpretation notes for vanity indicators
    vanity_keywords = ['vanity', 'optics', 'unclear ownership', 'misinterpreted']
    for idx, row in result_df.iterrows():
        if isinstance(row['Interpretation_Notes'], str):
            for keyword in vanity_keywords:
                if keyword.lower() in row['Interpretation_Notes'].lower():
                    result_df.loc[idx, 'vanity_score'] += 2
                    result_df.loc[idx, 'vanity_reasons'] += f'Notes indicate vanity ({keyword}); '
    
    # Clean up vanity_reasons
    result_df['vanity_reasons'] = result_df['vanity_reasons'].str.rstrip('; ')
    
    # Classify metrics based on vanity score
    result_df['is_vanity'] = result_df['vanity_score'] >= 3
    
    return result_df

def identify_valuable_metrics(df):
    """Identify metrics that are actually valuable for decision making"""
    # Create a copy to avoid SettingWithCopyWarning
    result_df = df.copy()
    
    # Initialize value score
    result_df['value_score'] = 0
    result_df['value_reasons'] = ''
    
    # Rule 1: Used in decision making
    mask = result_df['Used_in_Decision_Making'] == 'Yes'
    result_df.loc[mask, 'value_score'] += 3
    result_df.loc[mask, 'value_reasons'] += 'Used in decisions; '
    
    # Rule 2: Recently used for decision
    recent_decision_terms = ['recently', 'this week', '2 weeks ago', 'last month']
    for idx, row in result_df.iterrows():
        if isinstance(row['Metric_Last_Used_For_Decision'], str):
            for term in recent_decision_terms:
                if term.lower() in row['Metric_Last_Used_For_Decision'].lower():
                    result_df.loc[idx, 'value_score'] += 2
                    result_df.loc[idx, 'value_reasons'] += 'Recently used for decisions; '
                    break
    
    # Rule 3: Recently reviewed
    recent_review_terms = ['this week', 'last month']
    for idx, row in result_df.iterrows():
        if isinstance(row['Last_Reviewed'], str):
            for term in recent_review_terms:
                if term.lower() in row['Last_Reviewed'].lower():
                    result_df.loc[idx, 'value_score'] += 1
                    result_df.loc[idx, 'value_reasons'] += 'Recently reviewed; '
                    break
    
    # Rule 4: Check interpretation notes for value indicators
    value_keywords = ['tied to real goals', 'drives', 'customer impact', 'strategic', 'revenue']
    for idx, row in result_df.iterrows():
        if isinstance(row['Interpretation_Notes'], str):
            for keyword in value_keywords:
                if keyword.lower() in row['Interpretation_Notes'].lower():
                    result_df.loc[idx, 'value_score'] += 2
                    result_df.loc[idx, 'value_reasons'] += f'Notes indicate value ({keyword}); '
    
    # Clean up value_reasons
    result_df['value_reasons'] = result_df['value_reasons'].str.rstrip('; ')
    
    # Classify metrics as high-value
    result_df['is_high_value'] = result_df['value_score'] >= 4
    
    return result_df

def get_top_metrics_by_department(df, n=3):
    """Get top n valuable metrics for each department"""
    top_metrics = {}
    
    for dept in df['Department'].unique():
        dept_df = df[df['Department'] == dept].sort_values('value_score', ascending=False)
        top_metrics[dept] = dept_df.head(n)
    
    return top_metrics

def calculate_metric_impact_score(df):
    """Calculate an impact score for each metric to measure business value"""
    impact_scores = {}
    
    # Criteria weights
    weights = {
        'decision_making': 0.4,
        'recency': 0.3,
        'visibility': 0.1,
        'executive_interest': 0.2
    }
    
    # Calculate composite score
    for idx, row in df.iterrows():
        metric_id = f"{row['Department']}_{row['Metric_Name']}"
        
        # Decision making component
        decision_score = 1.0 if row['Used_in_Decision_Making'] == 'Yes' else 0.0
        
        # Recency component (simplified)
        recency_map = {
            'This week': 1.0,
            'Recently': 0.9,
            '2 weeks ago': 0.8,
            'Last month': 0.6,
            'Last quarter': 0.3,
            'Never': 0.0,
            'Unknown': 0.0,
            "Don't know": 0.0
        }
        
        recency_score = 0.0
        if isinstance(row['Metric_Last_Used_For_Decision'], str):
            for key, value in recency_map.items():
                if key in row['Metric_Last_Used_For_Decision']:
                    recency_score = value
                    break
        
        # Visibility component
        visibility_score = 0.5 if row['Visible_in_Dashboard'] == 'Yes' else 0.0
        
        # Executive interest
        executive_score = 0.8 if row['Executive_Requested'] == 'Yes' else 0.0
        
        # Calculate combined score
        impact_score = (
            weights['decision_making'] * decision_score +
            weights['recency'] * recency_score +
            weights['visibility'] * visibility_score +
            weights['executive_interest'] * executive_score
        )
        
        impact_scores[metric_id] = impact_score
    
    return impact_scores

def get_metrics_to_remove(df):
    """Identify metrics that should be removed from dashboards"""
    to_remove = df[
        (df['is_vanity'] == True) & 
        (df['Visible_in_Dashboard'] == 'Yes') &
        (df['is_high_value'] == False)
    ].sort_values('vanity_score', ascending=False)
    
    return to_remove
