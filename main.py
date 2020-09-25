#!/usr/bin/env python3.8

import sys
import serial
import argparse
import functools
import collections


STORAGE = {}

Packet = collections.namedtuple("Packet", ["rssi", "timestamp", "port"])

error = functools.partial(print, file = sys.stderr)


def collect(path: str, args: argparse.Namespace) -> None:
    with serial.Serial(path, args.baud) as s:
        while True:
            content = s.readline()
            ts = time.monotonic()
            mac, rssi, crc = content.rstrip().decode("ASCII").split(" ")

            while len(crc) < 8:
                crc = "0" + crc

            try:
                rssi = int(rssi)
            except ValueError as exc:
                error(f"ValueError: {exc}")
            if len(mac) != 17:
                error(f"Dropping weird packet from MAC {mac}!")

            packet = Packet(rssi = rssi, timestamp = ts, port = path)
            if args.verbose:
                print(f"{mac}: {rssi} ({crc}) @ {ts:.6f}")

            if mac not in STORAGE:
                STORAGE[mac] = {}
            if crc not in STORAGE[mac]:
                STORAGE[mac][crc] = []
            STORAGE[mac][crc].append(packet)


def setup() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description = "WiFi Tracking PoC"
    )

    parser.add_argument(
        "-v", "--version",
        help = "print verbose information",
        dest = "verbose",
        action = "store_true"
    )

    parser.add_argument(
        "-b", "--baud",
        help = "Baud rate of the connected serial devices (default 115200)",
        dest = "baud",
        type = int,
        default = 115200
    )

    parser.add_argument(
        "-p", "--port",
        help = "specify the port(s) to listen too, may be used multiple times",
        dest = "ports",
        action = "append",
        default = []
    )

    return parser


if __name__ == "__main__":
    arguments = setup().parse_args()
    if arguments.verbose:
        print(arguments)
