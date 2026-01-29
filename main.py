# main.py
import pandas as pd
from datetime import datetime
import time
from exch.base_exch import BaseExchange
from exch.Bybit_exch import BybitExchange # Исправлено: bybit_exch вместо Bybit_exch
from exch.htx_exch import HTXExchange
from exch.mexc_exch import MEXCExchange
import config

def collect_all_exchanges_data():
    """
    Сбор данных со всех кошельков всех бирж.
    Поддерживает:
    1. Старую структуру: 'htx': {'apiKey':..., 'secret':...}
    2. Новую структуру: 'htx': [{'apiKey':..., 'secret':...}, {...}]
    """
    all_data = []
    total_wallets = 0
    
    # Сначала подсчитаем общее количество кошельков
    for exchange_id, credentials in config.EXCHANGE_CREDENTIALS.items():
        if isinstance(credentials, list):
            total_wallets += len(credentials)
        else:
            total_wallets += 1
    
    print("="*60)
    print("НАЧАЛО СБОРА ДАННЫХ С КРИПТОБИРЖ")
    print(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Найдено бирж: {len(config.EXCHANGE_CREDENTIALS)}")
    print(f"Всего кошельков: {total_wallets}")
    print("="*60)
    
    processed_wallets = 0
    
    # Проходим по всем биржам
    for exchange_id, credentials in config.EXCHANGE_CREDENTIALS.items():
        print(f"\n📊 БИРЖА: {exchange_id.upper()}")
        
        # Определяем список кошельков для этой биржи
        wallets_list = []
        
        if isinstance(credentials, list):
            # Новая структура: список кошельков
            wallets_list = credentials
            print(f"   Найдено кошельков: {len(wallets_list)}")
        else:
            # Старая структура: один кошелек
            wallets_list = [credentials]
            print(f"   Найден 1 кошелек")
        
        # Обрабатываем каждый кошелек этой биржи
        for wallet_idx, wallet_creds in enumerate(wallets_list, 1):
            processed_wallets += 1
            
            try:
                wallet_name = wallet_creds.get('wallet_name', 
                    f"{exchange_id.upper()}_{wallet_idx}" if len(wallets_list) > 1 else exchange_id.upper()
                )
                
                print(f"\n   [{processed_wallets}/{total_wallets}] 🔹 Кошелек: {wallet_name}")
                
                # Выбираем нужный класс биржи
                exchange = None
                if exchange_id.lower() == 'bybit':
                    exchange = BybitExchange(wallet_creds)
                    
                elif exchange_id.lower() in ['htx', 'huobi']:
                    exchange = HTXExchange(wallet_creds)

                elif exchange_id.lower() == 'mexc':
                    exchange = MEXCExchange(wallet_creds)

                else:
                    exchange = BaseExchange(exchange_id, wallet_creds)
                # Получаем данные
                exchange_data = exchange.get_all_data(config.REPORT_SETTINGS['days_of_history'])
                
                # Добавляем название кошелька ко всем записям
                for item in exchange_data['all_data']:
                    item['wallet_name'] = wallet_name
                
                # Добавляем в общий список
                all_data.extend(exchange_data['all_data'])
                
                print(f"      ✅ Добавлено {len(exchange_data['all_data'])} записей")
                
                # Пауза между кошельками ОДНОЙ БИРЖИ (особенно важно!)
                if wallet_idx < len(wallets_list):
                    print(f"      ⏸️  Ожидание 3 секунды перед следующим кошельком {exchange_id.upper()}...")
                    time.sleep(3)
                
            except KeyboardInterrupt:
                print(f"\n⏹️  Прервано пользователем")
                return all_data
                
            except Exception as e:
                print(f"      ❌ Ошибка: {type(e).__name__}: {e}")
                print(f"      Пропускаю этот кошелек...")
                continue
        
        # Пауза между РАЗНЫМИ БИРЖАМИ
        if processed_wallets < total_wallets:
            print(f"\n⏸️  Ожидание 5 секунд перед следующей биржей...")
            time.sleep(5)
    
    print(f"\n📊 Сбор данных завершен.")
    print(f"   Обработано кошельков: {processed_wallets}/{total_wallets}")
    print(f"   Всего собрано записей: {len(all_data)}")
    
    # Сводка по биржам
    if all_data:
        df = pd.DataFrame(all_data)
        print(f"\n📈 СТАТИСТИКА:")
        for exchange in df['exchange'].unique():
            exchange_data = df[df['exchange'] == exchange]
            wallets = df[df['exchange'] == exchange]['wallet_name'].unique()
            print(f"   {exchange}: {len(exchange_data)} записей ({len(wallets)} кошельков)")
    
    return all_data

def create_excel_report(data, filename=None):
    """
    Создание Excel-файла с данными.
    
    :param data: Список словарей с данными
    :param filename: Имя файла (если None, генерируется автоматически)
    :return: Имя созданного файла
    """
    if not data:
        print("❌ Нет данных для создания отчета!")
        return None
    
    # Создаем DataFrame
    df = pd.DataFrame(data)
    
    # Если есть поле 'wallet_name', выносим его в начало
    if 'wallet_name' not in df.columns:
        df['wallet_name'] = 'Не указан'
    
    # Преобразуем timestamp в читаемый формат
    if 'timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
        df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
        df['time'] = df['datetime'].dt.strftime('%H:%M:%S')
    
    # Сортируем данные: сначала баланс, потом транзакции по дате
    df['sort_order'] = df['type'].apply(lambda x: 0 if x == 'balance' else 1)
    df = df.sort_values(['wallet_name', 'sort_order', 'datetime'], ascending=[True, True, False])
    df = df.drop('sort_order', axis=1)
    
    # Переупорядочиваем колонки для лучшей читаемости
    column_order = ['wallet_name', 'exchange', 'type', 'currency', 'amount', 'date', 'time']
    existing_columns = [col for col in column_order if col in df.columns]
    other_columns = [col for col in df.columns if col not in existing_columns]
    final_column_order = existing_columns + other_columns
    df = df[final_column_order]
    
    # Генерируем имя файла, если не задано
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crypto_report_{timestamp}.xlsx"
    
    # Создаем Excel-файл с несколькими листами
    print(f"\n💾 Сохраняю отчет в {filename}...")
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Лист 1: Все данные
        df.to_excel(writer, sheet_name='Все данные', index=False)
        
        # Лист 2: Только балансы
        balance_df = df[df['type'] == 'balance']
        if not balance_df.empty:
            balance_df.to_excel(writer, sheet_name='Балансы', index=False)
        
        # Лист 3: Только транзакции
        transactions_df = df[df['type'].isin(['deposit', 'withdrawal'])]
        if not transactions_df.empty:
            transactions_df.to_excel(writer, sheet_name='Транзакции', index=False)
        
        # Лист 4: Сводка по кошелькам
        _create_summary_sheet(writer, df)
        
        # Лист 5: Сводка по биржам (дополнительно)
        _create_exchange_summary_sheet(writer, df)
    
    print(f"✅ Отчет успешно сохранен: {filename}")
    return filename

def _create_summary_sheet(writer, df):
    """
    Создание листа со сводной информацией по кошелькам.
    """
    summary_data = []
    
    # Общая статистика
    summary_data.append(['ОТЧЕТ ПО КРИПТОКОШЕЛЬКАМ', ''])
    summary_data.append(['Дата создания', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    summary_data.append(['Период истории (дней)', config.REPORT_SETTINGS['days_of_history']])
    summary_data.append(['', ''])
    
    # Статистика по кошелькам
    summary_data.append(['СТАТИСТИКА ПО КОШЕЛЬКАМ', ''])
    
    for wallet_name in df['wallet_name'].unique():
        wallet_df = df[df['wallet_name'] == wallet_name]
        
        # Баланс
        balance_df = wallet_df[wallet_df['type'] == 'balance']
        total_balance = balance_df['amount'].sum() if not balance_df.empty else 0
        currencies_with_balance = len(balance_df)
        
        # Транзакции
        tx_df = wallet_df[wallet_df['type'].isin(['deposit', 'withdrawal'])]
        deposits = tx_df[tx_df['type'] == 'deposit']
        withdrawals = tx_df[tx_df['type'] == 'withdrawal']
        
        # Биржи в этом кошельке
        exchanges = ', '.join(wallet_df['exchange'].unique())
        
        summary_data.append([wallet_name, ''])
        summary_data.append(['  Биржи', exchanges])
        summary_data.append(['  Баланс', f"{currencies_with_balance} валют на сумму {total_balance:.8f}"])
        summary_data.append(['  Транзакции', f"{len(tx_df)} (Депозиты: {len(deposits)}, Выводы: {len(withdrawals)})"])
        summary_data.append(['', ''])
    
    # Конвертируем в DataFrame и сохраняем
    summary_df = pd.DataFrame(summary_data, columns=['Кошелек / Параметр', 'Значение'])
    summary_df.to_excel(writer, sheet_name='Сводка по кошелькам', index=False)

def _create_exchange_summary_sheet(writer, df):
    """
    Создание листа со сводной информацией по биржам.
    """
    summary_data = []
    
    summary_data.append(['СТАТИСТИКА ПО БИРЖАМ', ''])
    summary_data.append(['Дата', datetime.now().strftime('%Y-%m-%d')])
    summary_data.append(['', ''])
    
    for exchange in df['exchange'].unique():
        exchange_df = df[df['exchange'] == exchange]
        
        # Кошельки на этой бирже
        wallets = ', '.join(exchange_df['wallet_name'].unique())
        
        # Баланс
        balance_df = exchange_df[exchange_df['type'] == 'balance']
        total_balance = balance_df['amount'].sum() if not balance_df.empty else 0
        
        # Транзакции
        tx_df = exchange_df[exchange_df['type'].isin(['deposit', 'withdrawal'])]
        
        summary_data.append([exchange.upper(), ''])
        summary_data.append(['  Кошельки', wallets])
        summary_data.append(['  Баланс', f"{len(balance_df)} валют на сумму {total_balance:.8f}"])
        summary_data.append(['  Транзакции', f"{len(tx_df)}"])
        summary_data.append(['', ''])
    
    # Конвертируем в DataFrame и сохраняем
    summary_df = pd.DataFrame(summary_data, columns=['Биржа', 'Информация'])
    summary_df.to_excel(writer, sheet_name='Сводка по биржам', index=False)

def main():
    """
    Основная функция для ежедневного запуска.
    """
    try:
        # Проверяем конфигурацию
        if not config.EXCHANGE_CREDENTIALS:
            print("❌ В config.py не настроены API-ключи!")
            print("Добавьте хотя бы одну биржу в EXCHANGE_CREDENTIALS")
            return
        
        # 1. Собираем данные со всех бирж
        all_data = collect_all_exchanges_data()
        
        if not all_data:
            print("❌ Не удалось собрать данные ни с одной биржи.")
            print("Проверьте API-ключи в config.py и подключение к интернету.")
            return
        
        # 2. Создаем Excel-отчет
        report_file = create_excel_report(all_data)
        
        # 3. Выводим итоговую статистику
        print("\n" + "="*60)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("="*60)
        
        df = pd.DataFrame(all_data)
        wallet_count = df['wallet_name'].nunique()
        exchanges_count = df['exchange'].nunique()
        total_balance_entries = len(df[df['type'] == 'balance'])
        total_transactions = len(df[df['type'].isin(['deposit', 'withdrawal'])])
        
        print(f"Обработано кошельков: {wallet_count}")
        print(f"Обработано бирж: {exchanges_count}")
        print(f"Всего записей баланса: {total_balance_entries}")
        print(f"Всего транзакций: {total_transactions}")
        
        # Статистика по кошелькам
        print(f"\n📊 По кошелькам:")
        for wallet in df['wallet_name'].unique():
            wallet_df = df[df['wallet_name'] == wallet]
            exchanges = ', '.join(wallet_df['exchange'].unique())
            print(f"  {wallet}: {len(wallet_df)} записей ({exchanges})")
        
        print(f"\n📁 Отчет сохранен в файл: {report_file}")
        print("✅ Сбор данных завершен успешно!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
