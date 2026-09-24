import json
import random
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "factory/machines/M-001/sensors"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, PORT, 60)
print(f"Connected to MQTT: {BROKER}:{PORT}")
print(f"Publishing: {TOPIC}")

try:
    while True:
        air = round(random.uniform(298.0, 304.0), 2)
        process = round(air + random.uniform(8.0, 12.0), 2)
        rpm = random.randint(1400, 1700)
        torque = round(random.uniform(35.0, 55.0), 2)
        wear = random.randint(20, 220)
        payload = {"machine_id":"M-001","machine_type":"M","air_temperature":air,"process_temperature":process,"rotational_speed":rpm,"torque":torque,"tool_wear":wear,"timestamp":time.time()}
        client.publish(TOPIC, json.dumps(payload), qos=1)
        print(json.dumps(payload))
        time.sleep(2)
except KeyboardInterrupt:
    print("Simulator stopped")
finally:
    client.disconnect()
