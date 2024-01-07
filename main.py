import paho.mqtt.client as mqtt
import threading
import time

class MessageQueue:
    def __init__(self, mqtt_publisher, pause_topic):
        # Reference to the MqttPublisher instance
        self.publisher = mqtt_publisher

        # Topic for receiving 'true' messages
        self.switch_topic = "In/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Switch"

        # Topic for receiving 'pause' and 'unpause' messages
        self.pause_topic = pause_topic

        # List to store 'true' messages
        self.message_queue = []

        # Event for synchronization
        self.process_event = threading.Event()

        # Subscribe to the switch topic
        self.publisher.client.subscribe(self.switch_topic)
        print(f"Queue Subscribed to topic: {self.switch_topic}")

        # Subscribe to the pause topic
        self.publisher.client.subscribe(self.pause_topic)
        print(f"Queue Subscribed to topic: {self.pause_topic}")

        # Set the callback functions
        self.publisher.client.message_callback_add(self.switch_topic, self.on_switch_message)
        self.publisher.client.message_callback_add(self.pause_topic, self.on_pause_message)

    def on_switch_message(self, client, userdata, msg):
        # Callback function called when a 'true' message is received
        if msg.payload.decode() == 'true':
            # Add the message to the queue
            self.message_queue.append(msg.payload.decode())
            print("Added 'true' message to the queue:", msg.payload.decode())

    def on_pause_message(self, client, userdata, msg):
        # Callback function called when a 'pause' or 'unpause' message is received
        command = msg.payload.decode()

        if command == 'pause':
            # Pause message received, stop processing messages
            self.process_event.clear()
            print("Received 'pause' command. Pausing message processing.")

        elif command == 'unpause':
            # Unpause message received, start processing messages
            self.process_event.set()
            print("Received 'unpause' command. Resuming message processing.")

            # Process the stored messages with a delay of 10 seconds between each
            for message in self.message_queue:
                # Wait for the process_event to be set before processing the next message
                self.process_event.wait()

                # Publish the 'true' message
                self.publisher.client.publish(self.switch_topic, message)
                print(f"Published 'true' message to topic: {self.switch_topic}")

                # Add a delay of 10 seconds
                time.sleep(10)

            # Clear the message queue after sending all stored messages
            self.message_queue.clear()
            print("Message processing completed. Cleared the message queue.")

class MqttPublisher:
    def __init__(self, client, topic):
        # Reference to the shared MQTT client
        self.client = client

        # Set the topic to publish to
        self.topic = topic

    def publish_true_and_false(self):
        try:
            # Publish 'true' to the specified topic with QoS level 1
            self.client.publish(self.topic, 'true', qos=1)
            print(f"Published 'true' to topic: {self.topic}")

            # Start a new thread to handle the delay and publish 'false'
            threading.Thread(target=self._delayed_publish_false).start()

        except Exception as e:
            print(f"Error publishing messages: {e}")

    def _delayed_publish_false(self):
        try:
            # Add a delay of 6.5 seconds
            time.sleep(6.5)

            # After the delay, publish 'false'
            self.client.publish(self.topic, 'false', qos=1)
            print(f"Published 'false' to topic: {self.topic}")

        except Exception as e:
            print(f"Error publishing 'false' message: {e}")

class MqttClient:
    def __init__(self, broker_address, port, publisher_topic, subscriber_topics, message_queue):
        # Initialize MQTT client
        self.client = mqtt.Client()

        # Set MQTT broker address and port
        self.broker_address = broker_address
        self.port = port

        # Set the topics for subscribing
        self.subscriber_topics = subscriber_topics

        # Set the topic for publishing
        self.publisher_topic = publisher_topic

        # Set the callback functions
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Store the last received message
        self.last_message = None

        # Reference to the MqttPublisher instance
        self.publisher = MqttPublisher(self.client, self.publisher_topic)

        # Reference to the MessageQueue instance
        self.message_queue = message_queue

        # Event for synchronization
        self.publish_event = threading.Event()

        # Create a threading event for handling program termination
        self.terminate_event = threading.Event()

    def on_connect(self, client, userdata, flags, rc):
        # Callback function called when the client successfully connects to the broker
        print(f"Connected with result code {rc}")

        # Subscribe to the specified topics
        for topic in self.subscriber_topics:

            self.publisher.client.subscribe(self.message_queue.pause_topic)
            print(f"on_connect Subscribed to topic: {self.message_queue.pause_topic}")

            self.client.subscribe(topic)
            print(f"on_connect Subscribed to topic: {topic}")

    def on_message(self, client, userdata, msg):
        # Callback function called when a new message is received on a subscribed topic
        print(f"Received message on topic '{msg.topic}': {msg.payload.decode()}")

        # Check for 'pause' message and forward it to the message queue
        if msg.topic == self.message_queue.pause_topic and msg.payload.decode() == 'pause':
            self.message_queue.on_pause_message(client, userdata, msg)
            return

        # Store the last received message
        self.last_message = {'topic': msg.topic, 'payload': msg.payload.decode()}

        # Process the received message
        self.process_received_message()

        # Reset last_message to None to continue looking for new messages
        self.last_message = None

    def start(self):
        # Connect to the MQTT broker
        self.client.connect(self.broker_address, self.port, 60)

        # Start the MQTT loop in a separate thread
        threading.Thread(target=self._mqtt_loop).start()

    def _mqtt_loop(self):
        try:
            # Start the MQTT loop (blocking)
            self.client.loop_forever()

        except KeyboardInterrupt:
            print("Received KeyboardInterrupt. Exiting...")

        finally:
            # Disconnect the client when the loop is exited
            self.client.disconnect()
            print("Disconnected from the MQTT broker")

            # Set the terminate_event to signal the main program to exit
            self.terminate_event.set()

    def process_received_message(self):
        # Process the received message
        print("Processing received message:", self.last_message)

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

if __name__ == "__main__":
    # Set MQTT broker address, port, and topics for both publisher and subscriber
    broker_address = "broker.hivemq.com"  # Use HiveMQ public broker
    port = 1883  # Replace with your MQTT broker port
    subscriber_topics = ["In/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Switch"]
    publisher_topic = "Out/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Switch"

    # Create an instance of the MqttPublisher class
    mqtt_publisher = MqttPublisher(client=mqtt.Client(), topic=publisher_topic)

    # Create an instance of the MessageQueue class
    message_queue = MessageQueue(mqtt_publisher, "In/Lights/Location/qggrVblFaQbcpslyTPRdU2cSBHy1/Pause")

    # Create an instance of the MqttClient class
    mqtt_client = MqttClient(broker_address, port, publisher_topic, subscriber_topics, message_queue)

    # Start the MQTT client
    mqtt_client.start()

    try:
        # Keep the main program running until a termination event occurs
        while not mqtt_client.terminate_event.is_set():
            time.sleep(1)

    except KeyboardInterrupt:
        print("Received KeyboardInterrupt. Exiting...")

    finally:
        # Stop the MQTT client and wait for it to finish
        mqtt_client.stop()
        print("Main program exited.")
