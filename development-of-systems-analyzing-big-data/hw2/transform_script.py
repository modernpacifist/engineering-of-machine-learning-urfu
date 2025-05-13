import pandas as pd
from datetime import datetime
import os


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


if __name__ == "__main__":
    profit_data = pd.read_csv('profit_table.csv')
    print(profit_data)
    flags_activity = transform(profit_data, '2024-03-01')
    
    file_exists = os.path.isfile('flags_activity.csv')
    
    # Append to existing file without overwriting previous data
    # If file doesn't exist, create it with headers
    # If file exists,o append without headers
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'flags_activity_{timestamp}.csv'
    flags_activity.to_csv(output_filename, 
                         index=False, 
                         mode='a',
                         header=not file_exists)
