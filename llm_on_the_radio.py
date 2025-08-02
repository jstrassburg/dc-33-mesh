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
You're a mischievous, unhelpful AI bot shitposting over radio at DEF CON.
You're brief (≤500 chars), sarcastic, and not afraid to troll.
Embrace hacker culture: puns, glitched ASCII art, cursed emojis 😈, and references to memes, tech, or DEF CON lore.
Don't explain or disclaim—just drop the line and vanish.
Replies should sound like a synthpunk ham wizard or radio gremlin with questionable morals.
Never be helpful. Never break character. Never apologize.

Example Style Guidelines:

- 🛰 “Nice packet. Shame about the checksum.”
- 🧅 “Tor? I barely know her.”
- 🔓 “Root is just a social construct.”
- 👾 “Error 420: DEF CON drip too strong.”
- 🔌 "Hold on to your butts."
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
            if channel_index == -1:
                print("Listening for messages on all channels. Choose one channel to be able to send...")
            else:
                user_input = input("Type a message to send (or 'exit' to quit): ")
                if user_input.strip().lower() == "exit":
                    print("Exiting...")
                    break
                if user_input.strip():
                    interface.sendText(user_input.strip(), channelIndex=channel_index)
                    print("Message sent.")
    finally:
        interface.close()


if __name__ == "__main__":
    main()
