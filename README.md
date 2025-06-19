# Price Alert System

This is a simple price alert system that notifies you when a specified stock or cryptocurrency reaches a certain price.

## Setup

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the `alerter.py` script from your terminal:

```bash
python alerter.py
```

Follow the on-screen prompts to:
- Add new price alerts (specify symbol, target price, and whether to alert above or below).
- View existing alerts.
- Remove alerts.

The system will periodically check the prices and send a desktop notification when an alert condition is met.

## Disclaimer
This is a basic alert system. Price data accuracy and notification delivery depend on external APIs and system configurations. Use at your own risk.
