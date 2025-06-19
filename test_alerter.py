import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import sys

# Add the directory containing alerter.py to sys.path
# This ensures that 'import alerter' works correctly from the test file
# Assuming test_alerter.py is in the same directory as alerter.py
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    import alerter # The script to be tested
except ImportError:
    # This fallback might be needed if the subtask environment structure is different
    # For local testing, the sys.path.append should be sufficient
    print("Failed to import alerter.py directly. Ensure it's in the same directory or PYTHONPATH.")
    # As a last resort for the subtask, try to load it specifically if the simple import fails
    # import importlib.util
    # spec = importlib.util.spec_from_file_location("alerter", "alerter.py")
    # alerter = importlib.util.module_from_spec(spec)
    # spec.loader.exec_module(alerter)


ALERTS_TEST_FILE = "test_alerts.json"

class TestAlerter(unittest.TestCase):

    def setUp(self):
        """Set up for each test method."""
        # Use a different alerts file for testing to avoid interfering with the main one
        alerter.ALERTS_FILE = ALERTS_TEST_FILE
        # Ensure a clean slate for alerts before each test
        if os.path.exists(ALERTS_TEST_FILE):
            os.remove(ALERTS_TEST_FILE)
        self.alerts = [] # Keep an in-memory version for some tests

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(ALERTS_TEST_FILE):
            os.remove(ALERTS_TEST_FILE)
        # Reset ALERTS_FILE to its original value if necessary, though setUp handles it per test
        # import alerter as app_alerter # Re-import to get original constants if modified
        # alerter.ALERTS_FILE = app_alerter.ALERTS_FILE

    # --- Test Alert Management ---

    def test_load_alerts_file_not_found(self):
        """Test loading alerts when the JSON file does not exist."""
        self.assertEqual(alerter.load_alerts(), [])

    def test_load_alerts_empty_file(self):
        """Test loading alerts from an empty (but valid) JSON file."""
        with open(ALERTS_TEST_FILE, 'w') as f:
            json.dump([], f)
        self.assertEqual(alerter.load_alerts(), [])

    def test_load_alerts_corrupted_file(self):
        """Test loading alerts from a corrupted JSON file."""
        with open(ALERTS_TEST_FILE, 'w') as f:
            f.write("this is not json")
        self.assertEqual(alerter.load_alerts(), [])


    def test_save_and_load_alerts(self):
        """Test saving alerts to a file and then loading them back."""
        test_alerts_data = [
            {'symbol': 'BTC', 'target_price': 50000, 'condition': 'above', 'id': '1'},
            {'symbol': 'ETH', 'target_price': 4000, 'condition': 'below', 'id': '2'}
        ]
        alerter.save_alerts(test_alerts_data)
        loaded_alerts = alerter.load_alerts()
        self.assertEqual(loaded_alerts, test_alerts_data)

    @patch('builtins.input')
    @patch('alerter.fetch_price', return_value=52000.0) # Mock fetch_price during add_alert
    def test_add_alert(self, mock_fetch_price, mock_input):
        """Test adding a new alert. Mocks user input and price fetching."""
        mock_input.side_effect = ['BTC', '50000', 'above'] # Symbol, target, condition

        alerts_list = [] # Start with an empty list
        alerter.add_alert(alerts_list) # Pass the list to be modified

        self.assertEqual(len(alerts_list), 1)
        self.assertEqual(alerts_list[0]['symbol'], 'BTC')
        self.assertEqual(alerts_list[0]['target_price'], 50000.0)
        self.assertEqual(alerts_list[0]['condition'], 'above')
        # Check if save_alerts was called (implicitly by checking file content after add_alert)
        saved_alerts_from_file = alerter.load_alerts() # Assumes add_alert calls save_alerts
        self.assertEqual(len(saved_alerts_from_file), 1)
        self.assertEqual(saved_alerts_from_file[0]['symbol'], 'BTC')


    @patch('builtins.input', return_value='1') # Mock input for selecting alert to remove
    def test_remove_alert(self, mock_input):
        """Test removing an alert."""
        initial_alerts = [
            {'symbol': 'BTC', 'target_price': 50000, 'condition': 'above', 'id': '1', 'active': True},
            {'symbol': 'ETH', 'target_price': 4000, 'condition': 'below', 'id': '2', 'active': True}
        ]
        # Save initial alerts to the test file so remove_alert can load them
        alerter.save_alerts(initial_alerts)

        # Create a copy to pass to remove_alert if it modifies the list in-memory
        # However, alerter.remove_alert reloads from file, modifies, then saves.
        # So we check the file content after the operation.

        alerter.remove_alert(initial_alerts) # This list is not actually used by the current remove_alert logic
                                            # remove_alert loads from file, pops, then saves back to file.
                                            # This is a bit of a design smell in alerter.py if it takes a list it doesn't use.
                                            # For now, we'll test the file-based behavior.

        remaining_alerts = alerter.load_alerts()
        self.assertEqual(len(remaining_alerts), 1)
        self.assertEqual(remaining_alerts[0]['symbol'], 'ETH')

    # --- Test Price Checking and Notifications ---

    @patch('alerter.fetch_price')
    @patch('plyer.notification.notify') # Mock the actual notification call
    def test_check_alerts_trigger_above(self, mock_notify, mock_fetch_price):
        """Test alert triggering when price is above target."""
        mock_fetch_price.return_value = 55000.0 # Price is above target
        alerts = [{'symbol': 'BTC', 'target_price': 50000, 'condition': 'above', 'active': True, 'id': '1'}]

        triggered_messages = alerter.check_alerts(alerts)

        mock_fetch_price.assert_called_once_with('BTC')
        mock_notify.assert_called_once()
        self.assertIn("BTC is now $55000.0, which is above your target of $50000", mock_notify.call_args[1]['message'])
        self.assertEqual(len(triggered_messages), 1)


    @patch('alerter.fetch_price')
    @patch('plyer.notification.notify')
    def test_check_alerts_trigger_below(self, mock_notify, mock_fetch_price):
        """Test alert triggering when price is below target."""
        mock_fetch_price.return_value = 3500.0 # Price is below target
        alerts = [{'symbol': 'ETH', 'target_price': 4000, 'condition': 'below', 'active': True, 'id': '2'}]

        triggered_messages = alerter.check_alerts(alerts)

        mock_fetch_price.assert_called_once_with('ETH')
        mock_notify.assert_called_once()
        self.assertIn("ETH is now $3500.0, which is below your target of $4000", mock_notify.call_args[1]['message'])
        self.assertEqual(len(triggered_messages), 1)

    @patch('alerter.fetch_price')
    @patch('plyer.notification.notify')
    def test_check_alerts_no_trigger(self, mock_notify, mock_fetch_price):
        """Test no alert when price does not meet condition."""
        mock_fetch_price.return_value = 50000.0 # Price is at target (not above)
        alerts = [{'symbol': 'BTC', 'target_price': 50000, 'condition': 'above', 'active': True, 'id': '1'}]

        triggered_messages = alerter.check_alerts(alerts)

        mock_fetch_price.assert_called_once_with('BTC')
        mock_notify.assert_not_called()
        self.assertEqual(len(triggered_messages), 0)

    @patch('alerter.fetch_price', return_value=None) # Simulate API error
    @patch('plyer.notification.notify')
    def test_check_alerts_api_error(self, mock_notify, mock_fetch_price):
        """Test that no notification is sent if price fetching fails."""
        alerts = [{'symbol': 'XYZ', 'target_price': 100, 'condition': 'above', 'active': True, 'id': '3'}]

        triggered_messages = alerter.check_alerts(alerts)

        mock_fetch_price.assert_called_once_with('XYZ')
        mock_notify.assert_not_called()
        self.assertEqual(len(triggered_messages), 0)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False) # exit=False to prevent script halt in some envs
