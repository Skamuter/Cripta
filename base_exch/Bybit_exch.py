# exch/bybit_exchange.py
import ccxt
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from exch.base_exch import BaseExchange

class BybitExchange:
    """Специальный класс для работы с Bybit через CCXT"""
    
    def __init__(self, credentials: Dict):
        self.exchange_id = 'bybit'
        self.credentials = credentials
        self.exchange = None
        self._initialize_exchange()
        
    def _initialize_exchange(self):
        """Инициализация подключения к Bybit"""
        try:
            config = {
                'apiKey': self.credentials.get('apiKey', ''),
                'secret': self.credentials.get('secret', ''),
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'spot',
                }
            }
            
            self.exchange = ccxt.bybit(config)
            print(f"[BYBIT] Подключение инициализировано")
            
        except Exception as e:
            print(f"[BYBIT] Ошибка инициализации: {e}")
            self.exchange = None
    
    def get_bybit_time_params(self, start_time: Optional[int] = None, end_time: Optional[int] = None, days: Optional[int] = None):
        """Специальные параметры времени для Bybit"""
        if not end_time:
            end_time = self.exchange.milliseconds()
        
        if days:
            # Рассчитываем start_time на основе дней
            max_days = min(days, 29)  # 29 дней максимум!
            start_time = end_time - (max_days * 24 * 60 * 60 * 1000)
        
        # Ensure start_time is before end_time
        if start_time >= end_time:
            start_time = end_time - (24 * 60 * 60 * 1000)  # 1 день назад
            
        start_date = datetime.fromtimestamp(start_time/1000).strftime('%Y-%m-%d')
        end_date = datetime.fromtimestamp(end_time/1000).strftime('%Y-%m-%d')
        
        print(f"[BYBIT] Период: {start_date} - {end_date}")
        
        return {
            'startTime': int(start_time),
            'endTime': int(end_time),
            'limit': 50  # Bybit имеет лимит 50 за запрос
        }
    
    def fetch_balance(self) -> List[Dict]:
        """Получение баланса с Bybit"""
        if not self.exchange:
            return []
        
        try:
            print(f"[BYBIT] Запрашиваю баланс...")
            time.sleep(1)
            
            # Для Bybit нужен специальный параметр
            params = {'accountType': 'UNIFIED'}
            balance = self.exchange.fetch_balance(params=params)
            
            balance_list = []
            if balance and 'total' in balance:
                for currency, amount in balance['total'].items():
                    if amount and amount > 0.000001:
                        balance_list.append({
                            'exchange': 'bybit',
                            'type': 'balance',
                            'currency': currency,
                            'amount': amount,
                            'timestamp': self.exchange.milliseconds(),
                            'description': f'Баланс {currency}'
                        })
            
            print(f"[BYBIT] Найдено {len(balance_list)} валют с балансом")
            return balance_list
            
        except Exception as e:
            print(f"[BYBIT] Ошибка при получении баланса: {e}")
            return []
    
    def fetch_deposits(self, start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict]:
        """Получение депозитов с Bybit за указанный период"""
        if not self.exchange:
            return []
        
        try:
            params = self.get_bybit_time_params(start_time=start_time, end_time=end_time)
            
            print(f"[BYBIT] Запрашиваю историю депозитов...")
            time.sleep(1)
            
            deposits = self.exchange.fetch_deposits(params=params)
            
            deposit_list = []
            if deposits:
                for dep in deposits:
                    status = str(dep.get('status', '')).lower()
                    if status in ['ok', 'completed', 'success', 'done', 'successful', 'confirmed']:
                        deposit_list.append({
                            'exchange': 'bybit',
                            'type': 'deposit',
                            'currency': dep.get('currency', ''),
                            'amount': dep.get('amount', 0),
                            'timestamp': dep.get('timestamp', 0),
                            'description': f"Депозит {dep.get('currency', '')}",
                            'txid': dep.get('txid', ''),
                            'address': dep.get('address', ''),
                            'status': status
                        })
            
            print(f"[BYBIT] Найдено {len(deposit_list)} депозитов")
            return deposit_list
            
        except Exception as e:
            print(f"[BYBIT] Ошибка при получении депозитов: {e}")
            return []
    
    def fetch_withdrawals(self, start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict]:
        """Получение выводов с Bybit за указанный период"""
        if not self.exchange:
            return []
        
        try:
            params = self.get_bybit_time_params(start_time=start_time, end_time=end_time)
            
            print(f"[BYBIT] Запрашиваю историю выводов...")
            time.sleep(1)
            
            withdrawals = self.exchange.fetch_withdrawals(params=params)
            
            withdrawal_list = []
            if withdrawals:
                for wd in withdrawals:
                    status = str(wd.get('status', '')).lower()
                    if status in ['ok', 'completed', 'success', 'done', 'successful', 'confirmed']:
                        withdrawal_list.append({
                            'exchange': 'bybit',
                            'type': 'withdrawal',
                            'currency': wd.get('currency', ''),
                            'amount': wd.get('amount', 0),
                            'timestamp': wd.get('timestamp', 0),
                            'description': f"Вывод {wd.get('currency', '')}",
                            'txid': wd.get('txid', ''),
                            'address': wd.get('address', ''),
                            'status': status,
                            'fee': wd.get('fee', 0)
                        })
            
            print(f"[BYBIT] Найдено {len(withdrawal_list)} выводов")
            return withdrawal_list
            
        except Exception as e:
            print(f"[BYBIT] Ошибка при получении выводов: {e}")
            return []
    
    def get_all_data(self, days: int = 30) -> Dict[str, List]:
        """
        Получение всех данных с Bybit.
        Возвращает в старом формате для совместимости с main.py
        """
        print(f"\n{'='*50}")
        print(f"Сбор данных с BYBIT...")
        print(f"Запрошенный период: {days} дней")
        print(f"{'='*50}")
        
        if not self.exchange:
            print(f"[BYBIT] Биржа не инициализирована")
            return {'all_data': []}
        
        try:
            # Получаем баланс
            balance_data = self.fetch_balance()
            
            # ВАЖНО: Для депозитов и выводов используем пагинацию, 
            # чтобы получить данные за весь запрошенный период
            
            # Если запрошено больше 29 дней, разбиваем на чанки
            if days > 29:
                print(f"[BYBIT] Запрошено {days} дней. Использую пагинацию...")
                deposit_data = self._fetch_deposits_with_pagination(days)
                withdrawal_data = self._fetch_withdrawals_with_pagination(days)
            else:
                # Если <= 29 дней, используем обычный запрос
                end_time = self.exchange.milliseconds()
                start_time = end_time - (days * 24 * 60 * 60 * 1000)
                deposit_data = self.fetch_deposits(start_time=start_time, end_time=end_time)
                time.sleep(1)
                withdrawal_data = self.fetch_withdrawals(start_time=start_time, end_time=end_time)
            
            # Объединяем транзакции
            transaction_data = deposit_data + withdrawal_data
            
            # Объединяем все данные
            all_data = balance_data + transaction_data
            
            print(f"\n[BYBIT] ИТОГО:")
            print(f"  Балансы: {len(balance_data)} записей")
            print(f"  Депозиты: {len(deposit_data)}")
            print(f"  Выводы: {len(withdrawal_data)}")
            print(f"  Всего записей: {len(all_data)}")
            
            # Выводим диапазон дат транзакций
            if transaction_data:
                timestamps = [tx['timestamp'] for tx in transaction_data if tx['timestamp'] > 0]
                if timestamps:
                    min_date = datetime.fromtimestamp(min(timestamps) / 1000).strftime('%Y-%m-%d')
                    max_date = datetime.fromtimestamp(max(timestamps) / 1000).strftime('%Y-%m-%d')
                    print(f"  Диапазон транзакций: {min_date} - {max_date}")
            
            print(f"{'='*50}\n")
            
            # Возвращаем в старом формате для совместимости
            return {
                'balance': balance_data,
                'transactions': transaction_data,
                'all_data': all_data
            }
            
        except Exception as e:
            print(f"[BYBIT] Критическая ошибка: {e}")
            traceback.print_exc()
            return {'all_data': []}
    
    def _fetch_deposits_with_pagination(self, days: int) -> List[Dict]:
        """Получение депозитов с пагинацией для длинных периодов"""
        all_deposits = []
        end_time = self.exchange.milliseconds()
        
        print(f"[BYBIT] Получение депозитов за {days} дней с пагинацией...")
        
        # Вычисляем общий start_time для всего периода
        total_start_time = end_time - (days * 24 * 60 * 60 * 1000)
        current_end_time = end_time
        
        while current_end_time > total_start_time:
            # Рассчитываем start_time для текущего чанка (29 дней назад от current_end_time)
            chunk_start_time = current_end_time - (29 * 24 * 60 * 60 * 1000)
            
            # Убеждаемся, что не вышли за пределы общего периода
            if chunk_start_time < total_start_time:
                chunk_start_time = total_start_time
            
            start_date = datetime.fromtimestamp(chunk_start_time/1000).strftime('%Y-%m-%d')
            end_date = datetime.fromtimestamp(current_end_time/1000).strftime('%Y-%m-%d')
            
            print(f"[BYBIT] Чанк: {start_date} - {end_date}")
            
            # Получаем депозиты за этот чанк
            chunk_deposits = self.fetch_deposits(start_time=chunk_start_time, end_time=current_end_time)
            all_deposits.extend(chunk_deposits)
            
            # Проверяем, достигли ли мы начала периода
            if chunk_start_time <= total_start_time:
                break
            
            # Сдвигаем current_end_time для следующего чанка
            current_end_time = chunk_start_time - 1  # -1 чтобы избежать дублирования
            
            # Пауза между запросами
            time.sleep(2)
        
        print(f"[BYBIT] Всего депозитов: {len(all_deposits)}")
        return all_deposits
    
    def _fetch_withdrawals_with_pagination(self, days: int) -> List[Dict]:
        """Получение выводов с пагинацией для длинных периодов"""
        all_withdrawals = []
        end_time = self.exchange.milliseconds()
        
        print(f"[BYBIT] Получение выводов за {days} дней с пагинацией...")
        
        # Вычисляем общий start_time для всего периода
        total_start_time = end_time - (days * 24 * 60 * 60 * 1000)
        current_end_time = end_time
        
        while current_end_time > total_start_time:
            # Рассчитываем start_time для текущего чанка (29 дней назад от current_end_time)
            chunk_start_time = current_end_time - (29 * 24 * 60 * 60 * 1000)
            
            # Убеждаемся, что не вышли за пределы общего периода
            if chunk_start_time < total_start_time:
                chunk_start_time = total_start_time
            
            start_date = datetime.fromtimestamp(chunk_start_time/1000).strftime('%Y-%m-%d')
            end_date = datetime.fromtimestamp(current_end_time/1000).strftime('%Y-%m-%d')
            
            print(f"[BYBIT] Чанк: {start_date} - {end_date}")
            
            # Получаем выводы за этот чанк
            chunk_withdrawals = self.fetch_withdrawals(start_time=chunk_start_time, end_time=current_end_time)
            all_withdrawals.extend(chunk_withdrawals)
            
            # Проверяем, достигли ли мы начала периода
            if chunk_start_time <= total_start_time:
                break
            
            # Сдвигаем current_end_time для следующего чанка
            current_end_time = chunk_start_time - 1  # -1 чтобы избежать дублирования
            
            # Пауза между запросами
            time.sleep(2)
        
        print(f"[BYBIT] Всего выводов: {len(all_withdrawals)}")
        return all_withdrawals
