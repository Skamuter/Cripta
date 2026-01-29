# htx_exch.py - ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ
import ccxt
import time
import hashlib
import hmac
import base64
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List
from exch.base_exch import BaseExchange

class HTXExchange(BaseExchange):
    """Класс для HTX с ручной подписью запросов"""
    
    def __init__(self, credentials: Dict):
        super().__init__('huobi', credentials)
        
    def _initialize_exchange(self):
        """Простая инициализация - только ключи"""
        try:
            print(f"[HTX] Инициализация...")
            
            self.api_key = self.credentials.get('apiKey', '').strip()
            self.secret_key = self.credentials.get('secret', '').strip()
            
            if not self.api_key or not self.secret_key:
                raise ValueError("API ключи HTX не настроены")
            
            print(f"[HTX] ✅ Ключи загружены")
            
            # Создаем объект биржи только для публичных запросов
            self.exchange = ccxt.huobi({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'timeout': 30000,
            })
            
        except Exception as e:
            print(f"[HTX] ❌ Ошибка инициализации: {e}")
            self.exchange = None
    
    def _sign_request(self, method, endpoint, params=None):
        """Ручное создание подписи по алгоритму HTX"""
        try:
            # 1. Параметры по умолчанию
            params = params or {}
            
            # 2. Добавляем обязательные параметры для подписи
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            
            # Используем БОЛЕЕ РАННЕЕ время для компенсации 8 секунд
            # Вычитаем 10 секунд от текущего времени
            from datetime import datetime, timedelta
            adjusted_time = datetime.utcnow() - timedelta(seconds=10)
            timestamp = adjusted_time.strftime("%Y-%m-%dT%H:%M:%S")
            
            query_params = {
                'AccessKeyId': self.api_key,
                'SignatureMethod': 'HmacSHA256',
                'SignatureVersion': '2',
                'Timestamp': timestamp,
            }
            
            # 3. Добавляем пользовательские параметры
            query_params.update(params)
            
            # 4. Сортируем параметры по ключу
            sorted_params = sorted(query_params.items())
            
            # 5. Создаем строку для подписи
            host = "api.huobi.pro"
            payload = f"{method.upper()}\n{host}\n{endpoint}\n"
            
            # Кодируем параметры
            encoded_params = []
            for key, value in sorted_params:
                encoded_key = urllib.parse.quote(str(key), safe='')
                encoded_value = urllib.parse.quote(str(value), safe='')
                encoded_params.append(f"{encoded_key}={encoded_value}")
            
            payload += "&".join(encoded_params)
            
            # 6. Создаем подпись
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            signature_encoded = urllib.parse.quote(signature_b64, safe='')
            
            # 7. Собираем итоговый URL
            url_params = encoded_params + [f"Signature={signature_encoded}"]
            url = f"https://{host}{endpoint}?{'&'.join(url_params)}"
            
            print(f"[HTX DEBUG] Использовано время: {timestamp}")
            print(f"[HTX DEBUG] URL запроса: {url[:200]}...")
            
            return url
            
        except Exception as e:
            print(f"[HTX] ❌ Ошибка создания подписи: {e}")
            return None
    
    def _make_request(self, url):
        """Выполнение HTTP-запроса"""
        import requests
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"[HTX] ❌ Ошибка HTTP запроса: {e}")
            return None
    
    def fetch_balance(self) -> List[Dict]:
        """Прямой запрос баланса с ручной подписью"""
        try:
            print(f"[HTX] Получаю баланс (ручная подпись)...")
            
            # ШАГ 1: Получаем список аккаунтов
            accounts_url = self._sign_request('GET', '/v1/account/accounts')
            if not accounts_url:
                return []
            
            accounts_data = self._make_request(accounts_url)
            if not accounts_data or 'data' not in accounts_data:
                print(f"[HTX] ❌ Не получен список аккаунтов")
                return []
            
            # ШАГ 2: Ищем spot аккаунт
            spot_account_id = None
            for acc in accounts_data['data']:
                if acc.get('type') == 'spot' and acc.get('state') == 'working':
                    spot_account_id = acc['id']
                    print(f"[HTX] Найден spot аккаунт ID: {spot_account_id}")
                    break
            
            if not spot_account_id:
                print(f"[HTX] ❌ Spot аккаунт не найден")
                return []
            
            # ШАГ 3: Получаем баланс аккаунта
            balance_url = self._sign_request(
                'GET', 
                f'/v1/account/accounts/{spot_account_id}/balance'
            )
            
            if not balance_url:
                return []
            
            balance_data = self._make_request(balance_url)
            
            balance_list = []
            if balance_data and 'data' in balance_data and 'list' in balance_data['data']:
                for item in balance_data['data']['list']:
                    if item.get('type') == 'trade':  # Доступные средства
                        currency = item.get('currency', '').upper()
                        amount = float(item.get('balance', 0))
                        
                        if amount > 0.000001:
                            balance_list.append({
                                'exchange': 'HTX',
                                'account': 'spot',
                                'type': 'balance',
                                'currency': currency,
                                'amount': amount,
                                'timestamp': int(time.time() * 1000),
                                'details': f'account_id: {spot_account_id}'
                            })
                
                print(f"[HTX] ✅ Получено {len(balance_list)} валют с балансом")
            else:
                print(f"[HTX] ❌ Не удалось получить баланс")
            
            return balance_list
            
        except Exception as e:
            print(f"[HTX] ❌ Ошибка получения баланса: {type(e).__name__}: {e}")
            return []
        
    def fetch_transactions(self, days: int = 30) -> List[Dict]:
  
        try:
            # ВАЖНО: HTX API использует время в СЕКУНДАХ
            current_time_seconds = int(time.time())  # Только секунды!
            since_seconds = current_time_seconds - (days * 24 * 60 * 60)
            
            print(f"[HTX] Запрашиваю транзакции за {days} дней...")
            print(f"[HTX DEBUG] Текущее время (сек): {current_time_seconds}")
            print(f"[HTX DEBUG] Since (сек): {since_seconds}")
            print(f"[HTX DEBUG] Дата since: {datetime.fromtimestamp(since_seconds)}")  # <-- ИСПРАВЛЕНО
            
            transactions = []
            
            # Депозиты
            try:
                print(f"[HTX] Получаю депозиты...")
                params = {
                    'type': 'deposit', 
                    'from': since_seconds,  # Уже в секундах!
                    'size': 100
                }
                
                deposits = self.exchange.private_get_query_deposit_withdraw(params)
                
                if deposits and deposits.get('data'):
                    deposit_count = 0
                    for dep in deposits['data']:
                        if dep.get('type') == 'deposit':
                            # HTX возвращает время в миллисекундах
                            tx_timestamp = int(dep.get('updated-at', dep.get('created-at', 0)))
                            
                            transactions.append({
                                'exchange': 'HTX',
                                'account': 'spot',
                                'type': 'deposit',
                                'currency': dep['currency'].upper(),
                                'amount': float(dep['amount']),
                                'timestamp': tx_timestamp,
                                'datetime': datetime.fromtimestamp(tx_timestamp/1000).strftime('%Y-%m-%d %H:%M:%S'),  # <-- ИСПРАВЛЕНО
                                'details': f"{dep.get('tx-hash', 'N/A')}",
                                'status': dep.get('state', 'unknown')
                            })
                            deposit_count += 1
                    
                    print(f"[HTX] Найдено {deposit_count} депозитов")
            
            except Exception as e:
                print(f"[HTX] Ошибка при получении депозитов: {type(e).__name__}: {e}")
            
            time.sleep(1)  # Пауза между запросами
            
            # Выводы
            try:
                print(f"[HTX] Получаю выводы...")
                params = {
                    'type': 'withdraw', 
                    'from': since_seconds,  # Уже в секундах!
                    'size': 100
                }
                
                withdrawals = self.exchange.private_get_query_deposit_withdraw(params)
                
                if withdrawals and withdrawals.get('data'):
                    withdraw_count = 0
                    for wd in withdrawals['data']:
                        if wd.get('type') == 'withdraw':
                            tx_timestamp = int(wd.get('updated-at', wd.get('created-at', 0)))
                            
                            transactions.append({
                                'exchange': 'HTX',
                                'account': 'spot',
                                'type': 'withdrawal',
                                'currency': wd['currency'].upper(),
                                'amount': float(wd['amount']),
                                'timestamp': tx_timestamp,
                                'datetime': datetime.fromtimestamp(tx_timestamp/1000).strftime('%Y-%m-%d %H:%M:%S'),  # <-- ИСПРАВЛЕНО
                                'details': f"{wd.get('tx-hash', 'N/A')}",
                                'status': wd.get('state', 'unknown'),
                                'fee': float(wd.get('fee', 0))
                            })
                            withdraw_count += 1
                    
                    print(f"[HTX] Найдено {withdraw_count} выводов")
            
            except Exception as e:
                print(f"[HTX] Ошибка при получении выводов: {type(e).__name__}: {e}")
            
            # Сортируем по дате (от новых к старым)
            if transactions:
                transactions.sort(key=lambda x: x['timestamp'], reverse=True)
                
                # Показываем диапазон дат
                oldest_ts = min(t['timestamp'] for t in transactions)
                newest_ts = max(t['timestamp'] for t in transactions)
                
                oldest_date = datetime.fromtimestamp(oldest_ts/1000).strftime('%Y-%m-%d')
                newest_date = datetime.fromtimestamp(newest_ts/1000).strftime('%Y-%m-%d')
                
                print(f"[HTX] Диапазон транзакций: {oldest_date} - {newest_date}")
                print(f"[HTX] Всего транзакций: {len(transactions)}")
            else:
                print(f"[HTX] Транзакций не найдено")
            
            return transactions
            
        except Exception as e:
            print(f"[HTX] Критическая ошибка в fetch_transactions: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
