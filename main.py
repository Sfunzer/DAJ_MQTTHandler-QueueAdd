import paho.mqtt.client as mqtt
import threading
import time
import logging
import queue

# DAJL Back-end Controller
# Version 1.03 - For changes see GitHub.


# Setup for fault-logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mqtt_client.log')
    ]
)


class MqttPublisher:
    def __init__(self, client, topic):
        # Reference to the shared MQTT client
        self.client = client

        # Set the topic to publish to
        self.topic = topic

        #module to handle the control of the light-device by publishing a switching boolean.
    def publish_true_and_false(self):
        try:
            # Publish 'true' to the specified topic with QoS level 1
            self.client.publish(self.topic, 'true', qos=1)
            logging.info(f"Published 'true' to topic: {self.topic}")

            # Start a new thread to handle the delay and publish 'false'
            threading.Thread(target=self._delayed_publish_false).start()

        except Exception as e:
            logging.error(f"Error publishing messages: {e}")

    def _delayed_publish_false(self):
        try:
            # Add a delay of 6.5 seconds
            time.sleep(6.5)

            # After the delay, publish 'false'
            self.client.publish(self.topic, 'false', qos=1)
            logging.info(f"Published 'false' to topic: {self.topic}")

        except Exception as e:
            logging.error(f"Error publishing 'false' message: {e}")


class MqttClient:
    def __init__(self, broker_address, port, light_device_topic, light_signal_topic, pause_topic):
        # Initialize MQTT client
        self.client = mqtt.Client()

        # Set MQTT broker address and port
        self.broker_address = broker_address
        self.port = port

        # Set the topics for receiving the light-switching signal
        self.light_signal_topic = light_signal_topic

        # Set the topic for switching the light-device
        self.light_device_topic = light_device_topic

        # Set the topic for the pause-function
        self.pause_topic = pause_topic

        # Set the callback functions
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Store the last received message
        self.last_message = None

        # Reference to the MqttPublisher instance
        self.publisher = MqttPublisher(self.client, self.light_device_topic)

        # Event for synchronization
        self.publish_event = threading.Event()

        # Create a threading event for handling program termination
        self.terminate_event = threading.Event()

        # Flag to indicate whether processing is paused
        self.paused = False

        # Queue for storing messages received on the switch-topic
        self.message_queue = queue.Queue()

        # Create a threading event for handling message processing
        self.process_message_event = threading.Event()

    def on_connect(self, client, userdata, flags, rc):
        # Callback function called when the client successfully connects to the broker
        try:
            logging.info(f"Connected with result code {rc}")

            # Subscribe to the specified topics

            # Subscribe to the light signal topic:
            self.client.subscribe(self.light_signal_topic)
            logging.info(f"on_connect Subscribed to topic: {self.light_signal_topic}")

            # Subscribe to the pause topic:
            self.client.subscribe(self.pause_topic)
            logging.info(f"on_connect Subscribed to topic: {self.pause_topic}")

        except Exception as e:
            logging.error(f"Error in on_connect: {e}")

    def on_message(self, client, userdata, msg):
        try:
            # Callback function called when a new message is received on a subscribed topic
            logging.info(f"Received message on topic '{msg.topic}': {msg.payload.decode()}")

            # Checking if message is received on the light-switch topic
            if msg.topic == self.light_signal_topic:
                # Add the received message to the queue
                self.message_queue.put({'topic': msg.topic, 'payload': msg.payload.decode()})
                logging.info('message submitted into queue')

                # activates the message processor if the pause-flag is not true. Needed for initial starting of the
                # program.
                if not self.paused:
                    self.process_message_event.set()

            # Check for 'pause' message and handle it
            elif msg.topic == self.pause_topic:
                pause_command = msg.payload.decode()

                if pause_command == 'true':
                    # Pause message received, stop processing messages
                    self.paused = True
                    logging.info("Received 'pause' command. Pausing message processing.")

                elif pause_command == 'false':
                    # Unpause message received, resume processing messages
                    self.paused = False
                    logging.info("Received 'unpause' command. Resuming message processing.")
                    self.process_message_event.set()

            # Process the received message if processing is not paused
            elif not self.paused:
                # Store the last received message
                self.last_message = {'topic': msg.topic, 'payload': msg.payload.decode()}

                # Process the received message
                self.process_received_message()

                # Reset last_message to None to continue looking for new messages
                self.last_message = None

        except Exception as e:
            logging.error(f"Error in on_message: {e}")

    def start(self):
        # Connect to the MQTT broker
        self.client.connect(self.broker_address, self.port, 60)

        threading.Thread(target=self.message_processing_loop).start()

        # Start the MQTT loop in a separate thread
        threading.Thread(target=self._mqtt_loop).start()

    def _mqtt_loop(self):
        try:
            # Start the MQTT loop (blocking)
            self.client.loop_forever()

        except KeyboardInterrupt:
            logging.info("Received KeyboardInterrupt. Exiting...")

        except Exception as e:
            logging.error(f"Error in MQTT loop: {e}")

        finally:
            # Disconnect the client when the loop is exited
            self.client.disconnect()
            logging.info("Disconnected from the MQTT broker")

            # Set the terminate_event to signal the main program to exit
            self.terminate_event.set()

    def process_received_message(self):
        # Process the received message
        logging.info("Processing received message:", self.last_message)

        # Check if the payload is 'true' and publish to the specified topic
        if self.last_message['payload'] == 'true':
            self.publisher.publish_true_and_false()
            # Set the event to signal that 'true' has been published
            self.publish_event.set()
        elif self.last_message['payload'] == 'false':
            # Do nothing here or add custom logic for handling 'false' messages
            pass

    def stop(self):
        # Stop the MQTT loop and wait for it to finish
        self.client.loop_stop()
        self.terminate_event.wait()

    def message_processing_loop(self):
        while not self.terminate_event.is_set():
            # Wait for the event to be set, indicating a new message has been received
            self.process_message_event.wait()

            # Process the messages in the queue with a 10-second interval
            while not self.message_queue.empty():
                message = self.message_queue.get()
                self.last_message = message

                # Process the received message
                self.process_received_message()

                # Reset last_message to None to continue looking for new messages
                self.last_message = None

                # Wait for 10 seconds before processing the next message
                time.sleep(10)

            # Clear the event to wait for the next message
            self.process_message_event.clear()


if __name__ == "__main__":

    # Application-settings: Broker-settings are for both publisher and subscriber.
    broker_address = "broker.hivemq.com"  # Use HiveMQ public broker
    port = 1883  # Replace with your MQTT broker port
    light_signal_topic = "In/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Switch"
    light_device_topic = "Out/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Switch"
    pause_topic = "In/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Pause"

    # Create an instance of the MqttClient class
    mqtt_client = MqttClient(broker_address, port, light_device_topic, light_signal_topic, pause_topic)

    # Start the MQTT client
    mqtt_client.start()

    try:
        # Keep the main program running until a termination event occurs
        while not mqtt_client.terminate_event.is_set():
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt. Exiting...")

    finally:
        # Stop the MQTT client and wait for it to finish
        mqtt_client.stop()
        logging.info("Main program exited.")
