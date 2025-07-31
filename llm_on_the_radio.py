import argparse
import time

import ollama
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

parser = argparse.ArgumentParser(
    description="Listen for Meshtastic messages on a specific channel, funnel them to an AI assistant, and send responses."
)
parser.add_argument(
    "-c",
    "--channel",
    type=int,
    default=0,
    help="Channel index to listen on (default: 0, use -1 for all channels)",
)

args = parser.parse_args()
channel_index = args.channel

def invoke_ai_assistant(input: str):
    response = ollama.generate(
        model="deepseek-r1:8b",
        prompt=f"Very briefly, without yapping, and limiting response to 200 characters, respond to this input: {input}",
        think=False,
    )
    return response["response"][:200]


def on_receive(packet, interface):
    try:
        if "decoded" in packet and packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP":
            # Get the channel index from the packet
            message_bytes = packet["decoded"]["payload"]
            message_string = message_bytes.decode("utf-8")
            packet_channel = packet.get("channel", 0)
            print(f"Incomming message: [Channel {packet_channel}] {message_string}")

            # Filter by the specified channel (or show all if channel_index is -1)
            if channel_index == -1 or packet_channel == channel_index:
                response = invoke_ai_assistant(message_string)
                print(f"Sending AI Response: {response}")
                interface.sendText(response, channelIndex=packet_channel)
            else:
                print(f"Message on channel {packet_channel} ignored as it wasn't channel {channel_index}.")

    except KeyError as e:
        print(f"Error processing packet: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


pub.subscribe(on_receive, "meshtastic.receive")


def main():
    interface = SerialInterface()
    if channel_index == -1:
        print("Listening for messages on all channels...")
    else:
        print(f"Listening for messages on channel {channel_index}...")

    try:
        while True:
            time.sleep(0.5)
    finally:
        interface.close()


if __name__ == "__main__":
    main()
