from time import sleep

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from awscrt import mqtt, http
from awsiot import mqtt_connection_builder
import sys
import threading
import time
import json
from gpiozero import DistanceSensor
from time import sleep
from Raspi_MotorHAT import Raspi_MotorHAT, Raspi_DCMotor

global mh
mh = Raspi_MotorHAT(addr=0x6f)
global myMotor
myMotor = mh.getMotor(2)
global Accel
Accel = 15
global Direction
Direction = 300
global Speed
Speed = 0

servo_control = mh._pwm
servo_control.setPWMFreq(50)

servo_control.setPWM(0, 0, Direction)



# This sample uses the Message Broker for AWS IoT to send and receive messages
# through an MQTT connection. On startup, the device connects to the server,
# subscribes to a topic, and begins publishing messages to that topic.
# The device should receive those same messages back from the message broker,
# since it is subscribed to that same topic.

# cmdData is the arguments/input from the command line placed into a single struct for
# use in this sample. This handles all of the command line parsing, validating, etc.
# See the Utils/CommandLineUtils for more information.

global received_count
global message
received_count = 0
received_all_event = threading.Event()
message = ""

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    # 0:F 1:B 2:L 3:R
    #print("Received message from topic '{}': {}".format(topic, payload))

    # convert bytes type to string(json)
    msg = payload.decode('utf-8')

    # convert json to dict
    msg = json.loads(msg)
    # print(f"decoded string : {msg}, {type(msg)}")

    # get message
    message = msg
    sign = message["message"]
    global received_count
    received_count += 1
   

    # control
    global Speed
    global Direction

    if sign == 0:
        Speed += Accel
    elif sign == 1:
        Speed -= Accel
    elif sign == 2:      
        Direction -= 50
    elif sign == 3:
        Direction += 50

    if Speed > 255:
        Speed = 255
    
    if Speed < -255:
        Speed = -255

    if Direction >= 400:
        Direction = 400
    if Direction <= 200:
        Direction = 200

    FB = 1
    if Speed < 0:
        FB = -1

    if FB == 1:
        myMotor.run(Raspi_MotorHAT.FORWARD)
    elif FB == -1:
        myMotor.run(Raspi_MotorHAT.BACKWARD)

    myMotor.setSpeed(Speed * FB)
    servo_control.setPWM(0, 0, Direction)
    

# Callback when the connection successfully connects
def on_connection_success(connection, callback_data):
    assert isinstance(callback_data, mqtt.OnConnectionSuccessData)
    print("Connection Successful with return code: {} session present: {}".format(callback_data.return_code, callback_data.session_present))

# Callback when a connection attempt fails
def on_connection_failure(connection, callback_data):
    assert isinstance(callback_data, mqtt.OnConnectionFailureData)
    print("Connection failed with error code: {}".format(callback_data.error))


# Callback when a connection has been disconnected or shutdown successfully
def on_connection_closed(connection, callback_data):
    print("Connection closed")


def publish(message, topic):
    print("Publishing message to topic '{}': {}".format(topic, message))
    message_json = json.dumps(message)
    mqtt_connection.publish(
        topic=topic,
        payload=message_json,
        qos=mqtt.QoS.AT_LEAST_ONCE)
    time.sleep(0.1)


def subscribe(topic):
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)
    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))


proxy_options = None
# Create a MQTT connection from the command line data
mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint="a1dtsyjhmtbbiu-ats.iot.ap-northeast-2.amazonaws.com",
    cert_filepath="cert/9068ab43bdbda54a8dbc83f7c6392ebb3a7f457773514ac7b10eac00330f7fb5-certificate.pem.crt",
    pri_key_filepath="cert/9068ab43bdbda54a8dbc83f7c6392ebb3a7f457773514ac7b10eac00330f7fb5-private.pem.key",
    ca_filepath="cert/AmazonRootCA1.pem",
    on_connection_interrupted=on_connection_interrupted,
    on_connection_resumed=on_connection_resumed,
    client_id="RCcar_1",
    clean_session=False,
    keep_alive_secs=30,
    http_proxy_options=proxy_options,
    on_connection_success=on_connection_success,
    on_connection_failure=on_connection_failure,
    on_connection_closed=on_connection_closed)

connect_future = mqtt_connection.connect()

# Future.result() waits until a result is available
connect_future.result()
print("Connected!")

# publish("geag", "test/testing")





topic = "car1/joystick"
subscribe(topic)
cnt = 0
        

received_all_event.wait()

# Disconnect
print("Disconnecting...")
disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()
print("Disconnected!")
