EXCHANGE_CREDENTIALS = {
  "bingx": {
          "apiKey": "",
          "secret": "",
          'wallet_name': ''
      },
      "bybit": {
          "apiKey": "",
          "secret": "",
          'wallet_name': ''
      },
      "mexc": {
          "apiKey": "",
          "secret": "",
          'wallet_name': '' 
      },
      "gate": {
          "apiKey": "",
          "secret": "",
          'wallet_name': ''
      },
      "htx": [
          {  
              'wallet_name': '',
              "apiKey": "",
              "secret": "",  
          },
          {  
              'wallet_name': '',
              "apiKey": "",
              "secret": "",
          
          },
      ],
      "kucoin": [
          {  
              'wallet_name': '',
              "apiKey": "",
              "secret": "",
              "password": "",  
          },
          {  
              'wallet_name': '',
              "apiKey": "",
              "secret": "",
              "password": "",
          },
      ],
}

REPORT_SETTINGS = {
    "days_of_history": 90,  # За сколько дней брать историю транзакций
    "timezone": "Europe/Moscow",  # Часовой пояс для отчета
    "min_balance_threshold": 0.000001,  # Минимальный баланс для отображения (избавит от "мусора")
}
