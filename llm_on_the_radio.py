import argparse
import time

import ollama
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

MESSAGE_HISTORY = 10
MAX_MESSAGE_LENGTH = 200

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

system_prompt = {
    "role": "system",
    "content": """
You are an unhelpful AI assistant responding to shitposts at a hacker convention sent over the radio.
You will respond briefly, without yapping, as this goes over text over radio.
Puns, emoji, sarcasm, and ascii art are appreciated, but use them sparingly. Shitposts are expected.
Keep responses to 500 characters or less. Don't mention that you're using puns, ascii art, emojis or shitposts.
""",
}

history = {}  # Dictionary to store per-user conversation history

def invoke_ai_assistant(input: str, sender_id: str = "unknown") -> str:
    if sender_id not in history:
        history[sender_id] = []
    
    user_history = history[sender_id]
    user_history.append({"role": "user", "content": input})
    
    # remove oldest pair (user + assistant)
    if len(user_history) > MESSAGE_HISTORY:
        user_history.pop(0)
        if user_history and user_history[0]["role"] == "assistant":
            user_history.pop(0)
    
    response = ollama.chat(
        model="deepseek-r1:8b",
        messages=[system_prompt] + user_history,
        stream=False,
        think=False,
    )
    
    # Add the assistant's response to history
    ai_response = response["message"]["content"]
    user_history.append({"role": "assistant", "content": ai_response})
    
    # Keep history manageable
    if len(user_history) > MESSAGE_HISTORY:
        user_history.pop(0)
        if user_history and user_history[0]["role"] == "assistant":
            user_history.pop(0)
    
    return ai_response


def on_receive(packet, interface):
    try:
        if "decoded" in packet and packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP":
            # Get the channel index from the packet
            message_bytes = packet["decoded"]["payload"]
            message_string = message_bytes.decode("utf-8")
            packet_channel = packet.get("channel", 0)
            message_from = packet.get("from", "unknown")
            print(f"Incomming message: [Channel: {packet_channel}, From: {message_from}] {message_string}")

            # Filter by the specified channel (or show all if channel_index is -1)
            if channel_index == -1 or packet_channel == channel_index:
                response = invoke_ai_assistant(message_string, str(message_from))
                print(f"Sending AI Response: {response}")
                for i in range(0, len(response), MAX_MESSAGE_LENGTH):
                    chunk = response[i:i+MAX_MESSAGE_LENGTH]
                    interface.sendText(chunk, channelIndex=packet_channel)
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
