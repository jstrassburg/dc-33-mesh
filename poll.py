import argparse
import time
from meshtastic.serial_interface import SerialInterface
from pubsub import pub

# Global variable to store the channel index
channel_index = 0


def on_receive(packet, interface):
    try:
        if "decoded" in packet and packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP":
            # Get the channel index from the packet
            packet_channel = packet.get("decoded", {}).get("channel_index", 0)

            # Filter by the specified channel (or show all if channel_index is -1)
            if channel_index == -1 or packet_channel == channel_index:
                message_bytes = packet["decoded"]["payload"]
                message_string = message_bytes.decode("utf-8")
                print(f"[Channel {packet_channel}] {message_string}")
    except KeyError as e:
        print(f"Error processing packet: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


pub.subscribe(on_receive, "meshtastic.receive")


def main():
    """
    Main function to run the Meshtastic message listener.

    Args:
        channel_index (int): The channel index to listen on (default: 0).
    """
    global channel_index

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Listen for Meshtastic messages on a specific channel"
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

    interface = SerialInterface()
    if channel_index == -1:
        print("Listening for messages on all channels...")
    else:
        print(f"Listening for messages on channel {channel_index}...")

    def send_message(message):
        interface.sendText(message)

    try:
        while True:
            time.sleep(0.5)
            # text = input("> ")
            # send_message(text)
    finally:
        interface.close()


if __name__ == "__main__":
    main()
