import requests
import time
from decimal import Decimal

class CurrencyService:
    _usd_brl_rate = None
    _last_fetched = 0
    _CACHE_DURATION = 3600  # 1 hour cache

    @classmethod
    def get_usd_to_brl_rate(cls) -> Decimal:
        """
        Fetches the real-time USD to BRL conversion rate using AwesomeAPI.
        Caches the result for 1 hour to prevent rate-limiting and improve performance.
        Returns a fallback rate of 5.0 in case of API failure.
        """
        now = time.time()
        
        # Return cached rate if still valid
        if cls._usd_brl_rate is not None and (now - cls._last_fetched) < cls._CACHE_DURATION:
            return cls._usd_brl_rate

        try:
            response = requests.get('https://economia.awesomeapi.com.br/last/USD-BRL', timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Extract bid (compra) value
            rate_str = data.get('USDBRL', {}).get('bid')
            if rate_str:
                cls._usd_brl_rate = Decimal(rate_str)
                cls._last_fetched = now
                return cls._usd_brl_rate
                
        except Exception as e:
            print(f"Error fetching USD to BRL rate from AwesomeAPI: {e}")
        
        # Fallback to previously cached rate if available
        if cls._usd_brl_rate is not None:
            return cls._usd_brl_rate
            
        # Hard fallback
        return Decimal("5.0")
