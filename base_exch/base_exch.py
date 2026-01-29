#base_exch.py
import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Any

class BaseExchange:
    """Базовый класс для работы с биржами через CCXT"""
    
    def __init__(self, exchange_id: str, credentials: Dict):
        """
        Инициализация подключения к бирже.
        
        :param exchange_id: Идентификатор биржи в CCXT (например, 'binance', 'bybit')
        :param credentials: Словарь с учетными данными API
        """
        self.exchange_id = exchange_id
        self.credentials = credentials
        self.exchange = None
        self._initialize_exchange()
        
    def _initialize_exchange(self):
        """Инициализация объекта биржи CCXT с настройками"""
        exchange_class = getattr(ccxt, self.exchange_id)
        
        # Базовые настройки (очень важны для избежания банов!)
        config = {
            'apiKey': self.credentials.get('apiKey', ''),
            'secret': self.credentials.get('secret', ''),
            'enableRateLimit': True,  # ВКЛЮЧИТЬ лимитер запросов!
            'options': {
                'defaultType': 'spot',  # Работаем со спот-счетом
            }
        }
        
        # Особые параметры для некоторых бирж
        if self.exchange_id == 'kucoin':
            config['password'] = self.credentials.get('password', '')
        
        self.exchange = exchange_class(config)
        
    def fetch_balance(self) -> List[Dict]:
        """
        Получение баланса по всем валютам.
        Возвращает только валюты с ненулевым балансом.
        """
        try:
            print(f"[{self.exchange_id.upper()}] Запрашиваю баланс...")
            balance = self.exchange.fetch_balance()
            
            balance_list = []
            for currency, amount in balance['total'].items():
                if amount and amount > 0.000001:  # Игнорируем нулевые балансы
                    balance_list.append({
                        'exchange': self.exchange_id.upper(),
                        'account': 'spot',
                        'type': 'balance',
                        'currency': currency,
                        'amount': amount,
                        'timestamp': self.exchange.milliseconds(),
                        'details': 'current_balance'
                    })
            
            print(f"[{self.exchange_id.upper()}] Найдено {len(balance_list)} валют с балансом")
            return balance_list
            
        except Exception as e:
            print(f"[{self.exchange_id.upper()}] Ошибка при получении баланса: {e}")
            return []
    
    def fetch_transactions(self, days: int = 30) -> List[Dict]:
        """
        Получение истории депозитов и выводов.
        
        :param days: За сколько дней история
        """
        since = self.exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
        transactions = []
        
        # Получаем депозиты
        try:
            print(f"[{self.exchange_id.upper()}] Запрашиваю историю депозитов...")
            deposits = self.exchange.fetch_deposits(since=since, limit=500)
            
            for dep in deposits:
                transactions.append({
                    'exchange': self.exchange_id.upper(),
                    'account': 'spot',
                    'type': 'deposit',
                    'currency': dep['currency'],
                    'amount': dep['amount'],
                    'timestamp': dep['timestamp'],
                    'details': f"{dep.get('txid', 'N/A')} - {dep.get('address', 'N/A')}",
                    'status': dep.get('status', 'unknown')
                })
            
            print(f"[{self.exchange_id.upper()}] Найдено {len(deposits)} депозитов")
        except Exception as e:
            print(f"[{self.exchange_id.upper()}] Ошибка при получении депозитов: {e}")
        
        # Ждем между запросами, чтобы не получить бан
        time.sleep(1)
        
        # Получаем выводы
        try:
            print(f"[{self.exchange_id.upper()}] Запрашиваю историю выводов...")
            withdrawals = self.exchange.fetch_withdrawals(since=since, limit=500)
            
            for wd in withdrawals:
                transactions.append({
                    'exchange': self.exchange_id.upper(),
                    'account': 'spot',
                    'type': 'withdrawal',
                    'currency': wd['currency'],
                    'amount': wd['amount'],
                    'timestamp': wd['timestamp'],
                    'details': f"{wd.get('txid', 'N/A')} - {wd.get('address', 'N/A')}",
                    'status': wd.get('status', 'unknown'),
                    'fee': wd.get('fee', 0)
                })
            
            print(f"[{self.exchange_id.upper()}] Найдено {len(withdrawals)} выводов")
        except Exception as e:
            print(f"[{self.exchange_id.upper()}] Ошибка при получении выводов: {e}")
        
        return transactions
    
    def get_all_data(self, days: int = 30) -> Dict[str, List]:
        """
        Получение всех данных с биржи.
        
        :return: Словарь с балансами и транзакциями
        """
        print(f"\n{'='*50}")
        print(f"Сбор данных с {self.exchange_id.upper()}...")
        print(f"{'='*50}")
        
        # Запрашиваем данные
        balance_data = self.fetch_balance()
        transaction_data = self.fetch_transactions(days)
        
        # Объединяем все данные
        all_data = balance_data + transaction_data
        
        print(f"[{self.exchange_id.upper()}] Итого: {len(all_data)} записей")
        print(f"{'='*50}\n")
        
        return {
            'balance': balance_data,
            'transactions': transaction_data,
            'all_data': all_data
        }
