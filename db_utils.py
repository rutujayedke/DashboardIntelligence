import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create base class for declarative models
Base = declarative_base()

# Define the KPI metrics table model
class KPIMetric(Base):
    __tablename__ = 'kpi_metrics'
    
    id = Column(Integer, primary_key=True)
    department = Column(String(100))
    metric_name = Column(String(200))
    visible_in_dashboard = Column(String(10))
    used_in_decision_making = Column(String(10))
    executive_requested = Column(String(10))
    last_reviewed = Column(String(100))
    metric_last_used_for_decision = Column(String(100))
    interpretation_notes = Column(Text)
    vanity_score = Column(Float, default=0)
    vanity_reasons = Column(Text, default="")
    value_score = Column(Float, default=0)
    value_reasons = Column(Text, default="")
    is_vanity = Column(Boolean, default=False)
    is_high_value = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<KPIMetric(department='{self.department}', metric_name='{self.metric_name}')>"

# Create all tables in the database
def init_db():
    Base.metadata.create_all(engine)

# Create a session factory
Session = sessionmaker(bind=engine)

# Function to save DataFrame to database
def save_df_to_db(df):
    """Save a pandas DataFrame to the database"""
    # Create a session
    session = Session()
    
    try:
        # First, clear existing data
        session.query(KPIMetric).delete()
        session.commit()
        
        # Convert DataFrame to list of dictionaries for bulk insert
        records = []
        for _, row in df.iterrows():
            # Extract relevant columns
            record = {
                'department': row.get('Department', ''),
                'metric_name': row.get('Metric_Name', ''),
                'visible_in_dashboard': row.get('Visible_in_Dashboard', ''),
                'used_in_decision_making': row.get('Used_in_Decision_Making', ''),
                'executive_requested': row.get('Executive_Requested', ''),
                'last_reviewed': row.get('Last_Reviewed', ''),
                'metric_last_used_for_decision': row.get('Metric_Last_Used_For_Decision', ''),
                'interpretation_notes': row.get('Interpretation_Notes', ''),
                'vanity_score': float(row.get('vanity_score', 0)),
                'vanity_reasons': row.get('vanity_reasons', ''),
                'value_score': float(row.get('value_score', 0)),
                'value_reasons': row.get('value_reasons', ''),
                'is_vanity': bool(row.get('is_vanity', False)),
                'is_high_value': bool(row.get('is_high_value', False)),
            }
            
            kpi_metric = KPIMetric(**record)
            records.append(kpi_metric)
        
        # Add all records
        session.add_all(records)
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error saving data to database: {e}")
        return False
        
    finally:
        session.close()

# Function to load data from database
def load_from_db():
    """Load data from database into a pandas DataFrame"""
    # Create a session
    session = Session()
    
    try:
        # Query all records
        metrics = session.query(KPIMetric).all()
        
        # Convert to DataFrame
        if metrics:
            data = []
            for metric in metrics:
                record = {
                    'Department': metric.department,
                    'Metric_Name': metric.metric_name,
                    'Visible_in_Dashboard': metric.visible_in_dashboard,
                    'Used_in_Decision_Making': metric.used_in_decision_making,
                    'Executive_Requested': metric.executive_requested,
                    'Last_Reviewed': metric.last_reviewed,
                    'Metric_Last_Used_For_Decision': metric.metric_last_used_for_decision,
                    'Interpretation_Notes': metric.interpretation_notes,
                    'vanity_score': metric.vanity_score,
                    'vanity_reasons': metric.vanity_reasons,
                    'value_score': metric.value_score,
                    'value_reasons': metric.value_reasons,
                    'is_vanity': metric.is_vanity,
                    'is_high_value': metric.is_high_value,
                }
                data.append(record)
            
            return pd.DataFrame(data)
        else:
            return None
            
    except Exception as e:
        print(f"Error loading data from database: {e}")
        return None
        
    finally:
        session.close()

# Initialize the database tables
init_db()