"""
Stock price tool using yfinance.
"""

from langchain.tools import tool


@tool
def get_stock_price(ticker: str) -> str:
    """
    Get the current stock price and key financial data for a given ticker symbol.
    Input should be a stock ticker symbol like 'AAPL', 'GOOGL', 'MSFT', etc.
    Returns current price, previous close, market cap, and 52-week range.
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker.upper().strip())
        info = stock.info

        if not info or "regularMarketPrice" not in info:
            # Fallback: try fast_info
            try:
                fast = stock.fast_info
                return (
                    f"Stock: {ticker.upper()}\n"
                    f"Current Price: ${fast.last_price:.2f}\n"
                    f"Previous Close: ${fast.previous_close:.2f}\n"
                    f"Market Cap: ${fast.market_cap:,.0f}"
                )
            except Exception:
                return f"Could not find stock data for ticker '{ticker}'. Please check the symbol."

        name = info.get("shortName", ticker.upper())
        price = info.get("regularMarketPrice", info.get("currentPrice", "N/A"))
        prev_close = info.get("previousClose", "N/A")
        market_cap = info.get("marketCap", "N/A")
        fifty_two_low = info.get("fiftyTwoWeekLow", "N/A")
        fifty_two_high = info.get("fiftyTwoWeekHigh", "N/A")
        volume = info.get("volume", "N/A")

        result = f"📈 {name} ({ticker.upper()})\n"
        result += f"  Current Price : ${price}\n"
        result += f"  Previous Close: ${prev_close}\n"
        if market_cap != "N/A":
            result += f"  Market Cap    : ${market_cap:,.0f}\n"
        result += f"  52-Week Range : ${fifty_two_low} – ${fifty_two_high}\n"
        if volume != "N/A":
            result += f"  Volume        : {volume:,}\n"
        return result

    except Exception as e:
        return f"Error fetching stock data for '{ticker}': {str(e)}"
