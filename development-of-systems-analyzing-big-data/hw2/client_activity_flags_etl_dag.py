from datetime import datetime, timedelta
import pandas as pd
import os
from airflow.models import Variable

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


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
    schedule='0 0 5 * *',
    catchup=False
)


def transform(profit_table, date):
    """ Собирает таблицу флагов активности по продуктам
        на основании прибыли и количеству совершёных транзакций
        
        :param profit_table: таблица с суммой и кол-вом транзакций
        :param date: дата расчёта флагоа активности
        
        :return df_tmp: pandas-датафрейм флагов за указанную дату
    """
    start_date = pd.to_datetime(date) - pd.DateOffset(months=2)
    end_date = pd.to_datetime(date) + pd.DateOffset(months=1)
    date_list = pd.date_range(
        start=start_date, end=end_date, freq='M'
    ).strftime('%Y-%m-01')
    
    df_tmp = (
        profit_table[profit_table['date'].isin(date_list)]
        .drop('date', axis=1)
        .groupby('id')
        .sum()
    )
    
    product_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    for product in product_list:
        df_tmp[f'flag_{product}'] = (
            df_tmp.apply(
                lambda x: x[f'sum_{product}'] != 0 and x[f'count_{product}'] != 0,
                axis=1
            ).astype(int)
        )
        
    df_tmp = df_tmp.filter(regex='flag').reset_index()
    
    return df_tmp



def extract():
    """Extract data from profit_table.csv"""
    try:
        # Get data directory from Airflow variable or use environment variable
        data_dir = Variable.get("data_directory", default_var=os.environ.get("DATA_DIR", "/opt/airflow/data"))
        profit_data = pd.read_csv(f'{data_dir}/profit_table.csv')
        return profit_data
    except Exception as e:
        raise Exception(f"Error reading profit_table.csv: {e}")


def process_and_load(**context):
    """Transform data and load results to flags_activity.csv"""
    # Extract data
    profit_data = extract()
 
    # Get execution date
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Transform data
    flags_activity = transform(profit_data, date_str)
    
    # Create a new file with timestamp instead of appending
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Get output directory from Airflow variable or use environment variable
    output_dir = Variable.get("output_directory", default_var=os.environ.get("OUTPUT_DIR", "/opt/airflow/output"))
    os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist
    output_filename = f'{output_dir}/flags_activity_{timestamp}.csv'
    flags_activity.to_csv(output_filename, index=False)
    
    return f"Processed data for {date_str}, saved to {output_filename}"


etl_task = PythonOperator(
    task_id='etl_process',
    python_callable=process_and_load,
    dag=dag,
)
