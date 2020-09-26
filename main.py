#!/usr/bin/env python3.8

import sys
import json
import time
import serial
import typing
import argparse
import functools
import threading
import traceback
import collections
import socketserver


STORAGE = {}

Packet = collections.namedtuple("Packet", ["rssi", "timestamp", "port"])

error = functools.partial(print, file = sys.stderr)


def add_packet(line: bytes, args: argparse.Namespace, name: str) -> typing.Optional[Packet]:
    ts = time.monotonic()
    mac, rssi, crc = line.rstrip().decode("ASCII").split(" ")

    while len(crc) < 8:
        crc = "0" + crc

    try:
        rssi = int(rssi)
    except ValueError as exc:
        error(f"ValueError: {exc}")
    if len(mac) != 17:
        error(f"Dropping weird packet from MAC {mac}!")

    if len(args.filters) > 0:
        if mac not in args.filters:
            return

    packet = Packet(rssi = rssi, timestamp = ts, port = name)
    if args.verbose:
        print(f"{mac}: {rssi} ({crc}) @ {ts:.6f}")

    if mac not in STORAGE:
        STORAGE[mac] = {}
    if crc not in STORAGE[mac]:
        STORAGE[mac][crc] = []
    STORAGE[mac][crc].append(packet)

    if len(STORAGE[mac][crc]) == len(args.ports):
        calculate(STORAGE[mac][crc])
        del STORAGE[mac][crc]


class TCPCollectionHandler(socketserver.StreamRequestHandler):
    """
    The request handler class to collect data via network streams
    """

    args = None

    def handle_one(self):
        print("{} wrote:".format(self.client_address[0]))
        line = self.rfile.readline()
        if line == b"":
            return

        try:
            add_packet(line, TCPCollectionHandler.args, str(self.server.server_address))
        except ValueError:
            traceback.print_exc(file = sys.stderr)

    def handle(self) -> None:
        while True:
            self.handle_one()


def collect(path: str, args: argparse.Namespace) -> None:
    with serial.Serial(path, args.baud) as s:
        c = 0
        while True:
            content = s.readline()
            add_packet(content, args, path)

            c += 1
            if c >= args.counter > 0:
                break

    print(f"Exiting func for {path}")


def calculate(packets: list) -> None:
    error(f"Handling {packets}")
    pass


def start(func, path: str, args: argparse.Namespace) -> None:
    t = threading.Thread(target= func, args = (path, args), daemon = True)
    t.start()
    if args.verbose:
        print(f"Thread {t} has been started on serial device {path}")


def setup() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description = "WiFi Tracking PoC"
    )

    parser.add_argument(
        "-v", "--verbose",
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
        "-f", "--filter",
        help = "specify MAC addresses to filter against (white-list)",
        dest = "filters",
        action = "append",
        default = []
    )

    parser.add_argument(
        "-p", "--port",
        help = "specify the serial port(s) to listen to, may be used multiple times",
        dest = "ports",
        action = "append",
        default = []
    )

    parser.add_argument(
        "-n", "--network",
        help = "specify the TCP port(s) to listen too, may be used multiple times",
        dest = "network",
        action = "append",
        type = int,
        default = []
    )

    parser.add_argument(
        "-c", "--counter",
        help = "max. number of collected packets, use 0 to disable (default 1024)",
        dest = "counter",
        type = int,
        default = 1024
    )

    parser.add_argument(
        "-j", "--json",
        help = "path to the JSON file to store the resulting data",
        dest = "json"
    )

    return parser


if __name__ == "__main__":
    arguments = setup().parse_args()
    TCPCollectionHandler.args = arguments
    if arguments.verbose:
        print(arguments)

    for device in arguments.ports:
        start(collect, device, arguments)
    for port in arguments.network:
        s = socketserver.ThreadingTCPServer(("0.0.0.0", port), TCPCollectionHandler)
        process = threading.Thread(target = s.serve_forever, daemon = True)
        process.start()
        if arguments.verbose:
            print(f"Server thread {process} has been started on {port}")

    if arguments.verbose:
        print(f"Thread list: {threading.enumerate()}")

    while len(threading.enumerate()) > 1 and arguments.counter > 0:
        time.sleep(0.1)

    if arguments.json is not None:
        with open(arguments.json, "w") as f:
            json.dump(STORAGE, f, indent = 4)

    print("Main thread has exited!")
