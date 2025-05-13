from datetime import datetime, timedelta
import pandas as pd

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from transform_script import transform


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 5),  # Start from October 2023
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


dag = DAG(
    'client_activity_flags_etl',
    default_args=default_args,
    description='ETL process for client activity flags',
    schedule_interval='0 0 5 * *',
    catchup=False
)


def extract():
    """Extract data from profit_table.csv"""
    try:
        profit_data = pd.read_csv('profit_table.csv')
        return profit_data
    except Exception as e:
        raise Exception(f"Error reading profit_table.csv: {e}")


def process_and_load(**context):
    """Transform data and load results to flags_activity.csv"""
    # Extract data
    profit_data = extract()
    
    # Get execution date
    execution_date = context['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Transform data
    flags_activity = transform(profit_data, date_str)
    
    # Create a new file with timestamp instead of appending
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'flags_activity_{timestamp}.csv'
    flags_activity.to_csv(output_filename, index=False)
    
    return f"Processed data for {date_str}, saved to {output_filename}"


etl_task = PythonOperator(
    task_id='etl_process',
    python_callable=process_and_load,
    provide_context=True,
    dag=dag,
)
