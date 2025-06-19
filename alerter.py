import requests
import time
import json # For managing alerts persistence
from plyer import notification # For desktop notifications
import logging

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("alerter.log"), # Log to a file
        logging.StreamHandler() # Log to console
    ]
)

# --- Configuration ---
# (Consider moving to a separate config file later if it grows)
API_BASE_URL_CRYPTO = "https://api.coingecko.com/api/v3/simple/price" # Example for crypto
# For stocks, Yahoo Finance is often scraped or requires libraries like yfinance.
# For simplicity in this step, we'll focus on a conceptual structure.
# We'll need a more robust solution for actual stock price fetching.

ALERTS_FILE = "alerts.json" # File to store alerts

# --- Helper Functions ---

def fetch_price(symbol):
    """
    Fetches the current price for a given symbol (stock or crypto).
    """
    logging.info(f"Attempting to fetch price for {symbol}...")
    # Example for Crypto (CoinGecko)
    if symbol.lower() in ['bitcoin', 'ethereum', 'dogecoin']: # Adapt as needed
        try:
            params = {'ids': symbol.lower(), 'vs_currencies': 'usd'}
            response = requests.get(API_BASE_URL_CRYPTO, params=params, timeout=10) # Added timeout
            response.raise_for_status()
            data = response.json()
            price = data[symbol.lower()]['usd']
            logging.info(f"Successfully fetched price for {symbol}: ${price}")
            return price
        except requests.exceptions.Timeout:
            logging.error(f"Timeout while fetching price for {symbol} from CoinGecko.")
            return None
        except requests.exceptions.ConnectionError:
            logging.error(f"Connection error while fetching price for {symbol} from CoinGecko.")
            return None
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error fetching price for {symbol} from CoinGecko: {e.response.status_code} - {e}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Generic error fetching price for {symbol} from CoinGecko: {e}")
            return None
        except KeyError:
            logging.error(f"Could not parse price for {symbol} from CoinGecko response. Check symbol validity.")
            return None
    else:
        # Placeholder for stock symbols - yfinance or other APIs would have their own error patterns
        logging.warning(f"Stock symbol {symbol} uses placeholder pricing. No live API call.")
        if symbol == "AAPL": return 150.0
        if symbol == "TSLA": return 700.0
        logging.warning(f"Symbol {symbol} not supported by current configuration.")
        return None


def load_alerts():
    """Loads alerts from the ALERTS_FILE."""
    try:
        with open(ALERTS_FILE, 'r') as f:
            alerts = json.load(f)
        logging.info(f"Alerts loaded successfully from {ALERTS_FILE}.")
        return alerts
    except FileNotFoundError:
        logging.info(f"{ALERTS_FILE} not found. Starting with no alerts.")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {ALERTS_FILE}. File might be corrupted. Starting with no alerts.")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading alerts: {e}")
        return []

def save_alerts(alerts):
    """Saves alerts to the ALERTS_FILE."""
    try:
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=4)
        logging.info(f"Alerts saved successfully to {ALERTS_FILE}.")
    except IOError as e:
        logging.error(f"IOError saving alerts to {ALERTS_FILE}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving alerts: {e}")

def add_alert(alerts):
    """
    Prompts the user to add a new alert.
    An alert will be a dictionary like:
    {'symbol': 'BTC', 'target_price': 50000, 'condition': 'above'/'below', 'active': True}
    """
    print("\n--- Add New Alert ---")
    symbol = input("Enter stock/crypto symbol (e.g., AAPL, bitcoin): ").upper()

    # Try to fetch initial price to give user context, but handle if it fails
    current_price = fetch_price(symbol)
    if current_price is not None:
        print(f"Current price of {symbol}: ${current_price}")
    else:
        print(f"Could not fetch current price for {symbol}. Please ensure the symbol is correct.")

    target_price_str = input(f"Enter target price for {symbol}: ")
    try:
        target_price = float(target_price_str)
    except ValueError:
        print("Invalid target price. Please enter a number.")
        return

    condition = input("Alert when price is 'above' or 'below' target? ").lower()
    if condition not in ['above', 'below']:
        print("Invalid condition. Please enter 'above' or 'below'.")
        return

    alert = {
        'symbol': symbol,
        'target_price': target_price,
        'condition': condition,
        'active': True, # Alerts are active by default
        'id': time.time() # Simple unique ID for now
    }
    alerts.append(alert)
    save_alerts(alerts)
    print(f"Alert for {symbol} {condition} ${target_price} added.")
    logging.info(f"Alert for {symbol} {condition} ${target_price} added. ID: {alert['id']}")

def view_alerts(alerts):
    """Displays all current alerts."""
    print("\n--- Current Alerts ---")
    if not alerts:
        print("No alerts set.")
        return
    for i, alert in enumerate(alerts):
        status = "Active" if alert.get('active', True) else "Inactive/Triggered"
        print(f"{i+1}. {alert['symbol']} {alert['condition']} ${alert['target_price']} ({status}) (ID: {alert.get('id', 'N/A')})")

def remove_alert(alerts):
    """Removes an alert by its number displayed in view_alerts."""
    view_alerts(alerts)
    if not alerts:
        return
    try:
        alert_num_str = input("Enter the number of the alert to remove: ")
        alert_idx = int(alert_num_str) - 1
        if 0 <= alert_idx < len(alerts):
            removed_alert = alerts.pop(alert_idx)
            save_alerts(alerts)
            print(f"Alert for {removed_alert['symbol']} removed.")
            logging.info(f"Alert for {removed_alert['symbol']} (ID: {removed_alert.get('id')}) removed.")
        else:
            print("Invalid alert number.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def check_alerts(alerts):
    """
    Checks all active alerts against current prices.
    Triggers notifications if conditions are met.
    """
    print("\n--- Checking Alerts ---")
    if not alerts:
        print("No active alerts to check.")
        return

    triggered_alerts_details = [] # To store messages for console summary

    for alert in alerts:
        if not alert.get('active', True):
            continue

        current_price = fetch_price(alert['symbol'])
        if current_price is None:
            print(f"Could not fetch price for {alert['symbol']}. Skipping alert.")
            continue

           # Keep this print for console logging
        print(f"Checking {alert['symbol']}: Current Price ${current_price}, Target ${alert['target_price']}, Condition: {alert['condition']}")

        triggered = False
        if alert['condition'] == 'above' and current_price > alert['target_price']:
            triggered = True
        elif alert['condition'] == 'below' and current_price < alert['target_price']:
            triggered = True

        if triggered:
            title = f"Price Alert: {alert['symbol']}"
            message_body = f"{alert['symbol']} is now ${current_price}, which is {alert['condition']} your target of ${alert['target_price']}."

            # Console print (can keep for logging purposes)
            print(f"NOTIFICATION: {message_body}")

            # Desktop notification using plyer
            try:
                notification.notify(
                    title=title,
                    message=message_body,
                    app_name="Price Alerter", # Optional: Ticker for notification
                    timeout=10  # Optional: Notification timeout in seconds
                )
                logging.info(f"Notification sent for {alert['symbol']}: {message_body}")
                # Optionally mark alert as inactive to prevent immediate re-triggering
                # alert['active'] = False
            except Exception as e:
                print(f"Error sending notification for {alert['symbol']}: {e}")
                logging.error(f"Error sending desktop notification for {alert['symbol']}: {e}")
                # Fallback or simply log if plyer fails (e.g., on a headless server)

            triggered_alerts_details.append(message_body) # Keep for summary

    # if any(not alert.get('active') for alert in alerts): # Check if any alert was deactivated
        # save_alerts(alerts) # Save changes if alerts were marked inactive

    # Return details for console summary, not the notification object itself
    return triggered_alerts_details


# --- Main Application Logic ---
def main():
    """Main function to run the alerter application."""
    logging.info("Price Alerter application started.")
    alerts = load_alerts()

    while True:
        print("\n--- Price Alerter Menu ---")
        print("1. Add Alert")
        print("2. View Alerts")
        print("3. Remove Alert")
        print("4. Check Alerts Now")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            add_alert(alerts)
        elif choice == '2':
            view_alerts(alerts)
        elif choice == '3':
            remove_alert(alerts)
        elif choice == '4':
            triggered_notifications = check_alerts(alerts)
            if triggered_notifications:
                print("\n--- Notifications ---")
                for notif in triggered_notifications:
                    print(notif)
            else:
                print("No alerts were triggered.")
        elif choice == '5':
            logging.info("Price Alerter application shutting down.")
            print("Exiting Alerter. Alerts are saved.")
            break
        else:
            print("Invalid choice. Please try again.")

        # Optional: Add a small delay to prevent spamming menu or API in a real-time loop
        # time.sleep(1)

if __name__ == "__main__":
    main()
