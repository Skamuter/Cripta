# mexc_exch.py
import ccxt
import time
from typing import Dict, List
from datetime import datetime, timedelta
from exch.base_exch import BaseExchange

class MEXCExchange(BaseExchange):
    """Класс для работы с MEXC"""
    
    def __init__(self, credentials: Dict):
        super().__init__('mexc', credentials)
        
    def _initialize_exchange(self):
        """Инициализация MEXC"""
        try:
            # Проверяем ключи
            api_key = self.credentials.get('apiKey', '')
            secret = self.credentials.get('secret', '')
            
            if not api_key or not secret:
                raise ValueError("API ключи MEXC не предоставлены")
            
            # Конфигурация
            config = {
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'},
                'timeout': 30000,
            }
            
            self.exchange = ccxt.mexc(config)
            self.exchange.load_markets()
            
        except Exception as e:
            error_msg = str(e)
            # Безопасное логирование ошибки
            if "10072" in error_msg:
                raise Exception("Неверные API ключи MEXC. Проверьте ключи в конфиге.")
            elif "10071" in error_msg:
                raise Exception("IP адрес не в белом списке MEXC")
            else:
                raise Exception(f"Ошибка подключения к MEXC: {error_msg.split(':')[-1].strip()}")
    
    def fetch_balance(self) -> List[Dict]:
        """Получение баланса"""
        try:
            balance = self.exchange.fetch_balance()
            balance_list = []
            
            if isinstance(balance, dict):
                # Проверяем все возможные разделы
                sections = ['total', 'free', 'used']
                for section in sections:
                    if section in balance and isinstance(balance[section], dict):
                        for currency, amount in balance[section].items():
                            if amount and float(amount) > 0.00000001:
                                balance_list.append({
                                    'exchange': 'MEXC',
                                    'account': 'spot',
                                    'type': 'balance',
                                    'currency': currency.upper(),
                                    'amount': float(amount),
                                    'timestamp': self.exchange.milliseconds(),
                                    'details': f'{section}_balance'
                                })
            
            # Убираем дубликаты
            unique = []
            seen = set()
            for item in balance_list:
                key = item['currency']
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            
            return unique
            
        except Exception as e:
            if "10072" in str(e):
                raise Exception("Неверные API ключи MEXC")
            return []
    
    def fetch_transactions(self, days: int = 30) -> List[Dict]:
        """Получение истории транзакций"""
        transactions = []
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        try:
            # Депозиты
            deposits = self.exchange.fetch_deposits(since=since, limit=100)
            if isinstance(deposits, list):
                for deposit in deposits:
                    transactions.append({
                        'exchange': 'MEXC',
                        'account': 'spot',
                        'type': 'deposit',
                        'currency': deposit.get('currency', ''),
                        'amount': float(deposit.get('amount', 0)),
                        'timestamp': deposit.get('timestamp', 0),
                        'details': deposit.get('txid', ''),
                        'status': deposit.get('status', '')
                    })
            
            time.sleep(1)
            
            # Выводы
            withdrawals = self.exchange.fetch_withdrawals(since=since, limit=100)
            if isinstance(withdrawals, list):
                for withdrawal in withdrawals:
                    transactions.append({
                        'exchange': 'MEXC',
                        'account': 'spot',
                        'type': 'withdrawal',
                        'currency': withdrawal.get('currency', ''),
                        'amount': float(withdrawal.get('amount', 0)),
                        'timestamp': withdrawal.get('timestamp', 0),
                        'details': withdrawal.get('txid', ''),
                        'status': withdrawal.get('status', ''),
                        'fee': float(withdrawal.get('fee', 0))
                    })
            
            # Сортируем
            transactions.sort(key=lambda x: x['timestamp'], reverse=True)
            return transactions
            
        except Exception as e:
            if "10072" in str(e):
                raise Exception("Неверные API ключи MEXC")
            return []
