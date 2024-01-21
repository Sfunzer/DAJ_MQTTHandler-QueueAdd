import unittest
from unittest.mock import MagicMock, patch
from main import MqttClient, MqttPublisher  # Replace with the actual module name

class TestMqttClient(unittest.TestCase):
    def setUp(self):
        # Set up MQTT client with mock parameters
        self.mqtt_client = MqttClient(
            broker_address="test_broker",
            port=1234,
            light_device_topic="test/light/device",
            light_signal_topic="test/light/signal",
            pause_topic="test/pause"
        )
        self.mqtt_client.client.connect = MagicMock()  # Mocking the connect method
        self.mqtt_client.client.loop_forever = MagicMock()  # Mocking the loop_forever method

    def tearDown(self):
        # Disconnect the client
        self.mqtt_client.client.disconnect()

    @patch('threading.Thread.start')
    def test_start_method(self, mock_thread_start):
        # Test the start method
        self.mqtt_client.start()

        # Assert that the connect method is called
        self.mqtt_client.client.connect.assert_called_once_with("test_broker", 1234, 60)

        # Assert that the message processing loop is started in a separate thread
        mock_thread_start.assert_called_once_with()

        # Assert that the MQTT loop is started in a separate thread
        self.mqtt_client.client.loop_forever.assert_called_once()

    @patch('threading.Event.set')
    @patch('time.sleep')
    def test_process_received_message_method_true(self, mock_sleep, mock_event_set):
        # Test process_received_message method with 'true' payload
        self.mqtt_client.last_message = {'topic': 'test/topic', 'payload': 'true'}

        with patch.object(MqttPublisher, 'publish_true_and_false') as mock_publish_method:
            self.mqtt_client.process_received_message()

        # Assert that the publish_true_and_false method is called
        mock_publish_method.assert_called_once()

        # Assert that the event is set
        mock_event_set.assert_called_once()

        # Assert that sleep is not called since payload is 'true'
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    def test_process_received_message_method_false(self, mock_sleep):
        # Test process_received_message method with 'false' payload
        self.mqtt_client.last_message = {'topic': 'test/topic', 'payload': 'false'}

        with patch.object(MqttPublisher, 'publish_true_and_false') as mock_publish_method:
            self.mqtt_client.process_received_message()

        # Assert that the publish_true_and_false method is not called
        mock_publish_method.assert_not_called()

        # Assert that sleep is not called since payload is 'false'
        mock_sleep.assert_not_called()


    def test_process_received_message_method_other_payload(self, mock_sleep):
        # Test process_received_message method with payload other than 'true' or 'false'
        self.mqtt_client.last_message = {'topic': 'test/topic', 'payload': 'other'}

        with patch.object(MqttPublisher, 'publish_true_and_false') as mock_publish_method:
            self.mqtt_client.process_received_message()

        # Assert that the publish_true_and_false method is not called
        mock_publish_method.assert_not_called()

        # Assert that sleep is not called since payload is neither 'true' nor 'false'
        mock_sleep.assert_not_called()

    def test_stop_method(self):
        # Test the stop method
        self.mqtt_client.client.loop_stop = MagicMock()  # Mocking the loop_stop method

        self.mqtt_client.stop()

        # Assert that the loop_stop method is called
        self.mqtt_client.client.loop_stop.assert_called_once()

        # Assert that the terminate_event is set
        self.assertTrue(self.mqtt_client.terminate_event.is_set())


if __name__ == '__main__':
    unittest.main()
