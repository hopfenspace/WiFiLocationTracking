#!/usr/bin/env python3

import os
import sys
import json
import time
import typing
import argparse
import functools
import threading
import traceback
import subprocess
import collections
import socketserver

import serial

STORAGE = {}
deviceLocations = {}

Packet = collections.namedtuple("Packet", ["rssi", "timestamp", "port"])
Device = collections.namedtuple("Device", ["mac", "x", "y", "count"])

error = functools.partial(print, file=sys.stderr)


def add_packet(line: bytes, args: argparse.Namespace, name: str) -> typing.Optional[Packet]:
    ts = time.monotonic()
    try:
        mac, rssi, crc = line.rstrip().decode("ascii").split(" ")

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

        packet = Packet(rssi=rssi, timestamp=ts, port=name)
        if args.verbose:
            print(f"{mac}: {rssi} ({crc}) @ {ts:.6f}")

        if mac not in STORAGE:
            STORAGE[mac] = {}
        if crc not in STORAGE[mac]:
            STORAGE[mac][crc] = []
        STORAGE[mac][crc].append(packet)

        if len(STORAGE[mac][crc]) == len(args.ports):
            calculate(mac, STORAGE[mac][crc], args)
            del STORAGE[mac][crc]

    except:
        pass


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
            traceback.print_exc(file=sys.stderr)

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


def calculate(mac: str, packets: list, args: argparse.Namespace) -> None:
    if len(packets) != 3:
        print(f"calculating a position is currently only implemented with 3 receivers")

    p1, p2, p3 = packets
    rssi1 = p1.rssi
    rssi2 = p2.rssi
    rssi3 = p3.rssi

    f12 = rssi1 / (rssi1 + rssi2)
    f23 = rssi2 / (rssi2 + rssi3)

    # device 0 at 0, 0
    # device 1 at args.distance, 0
    # device 2 at args.distance, args.distance
    x = f12 * args.distance
    y = f23 * args.distance

    count = 1
    if mac in deviceLocations:
        count = deviceLocations[mac].count + 1
    deviceLocations[mac] = Device(mac, x, y, count)

    if args.verbose:
        print(f"device {mac} is at {x} {y}")


def insert_data(path: str) -> None:
    pass


def get_remote(ip: str, path: str):
    while True:
        try:
            target = f"./export_{ip}.json"
            if os.path.exists(target):
                os.remove(target)
            p = subprocess.Popen(["scp", f"root@{ip}:{path}", target])
            if os.path.exists(target):
                insert_data(target)
        except:
            traceback.print_exc()


def start(func, path: str, args: argparse.Namespace) -> None:
    t = threading.Thread(target=func, args=(path, args), daemon=True)
    t.start()
    if args.verbose:
        print(f"Thread {t} has been started on serial device {path}")


def setup() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="WiFi Tracking PoC"
    )

    parser.add_argument(
        "-v", "--verbose",
        help="print verbose information",
        dest="verbose",
        action="store_true"
    )

    parser.add_argument(
        "-b", "--baud",
        help="Baud rate of the connected serial devices (default 115200)",
        dest="baud",
        type=int,
        default=115200
    )

    parser.add_argument(
        "-f", "--filter",
        help="specify MAC addresses to filter against (white-list)",
        dest="filters",
        action="append",
        default=[]
    )

    parser.add_argument(
        "-p", "--port",
        help="specify the serial port(s) to listen to, may be used multiple times",
        dest="ports",
        action="append",
        default=[]
    )

    parser.add_argument(
        "-d", "--distance",
        help="specify the distance of the ",
        dest="distance",
        type=int,
        default=10
    )

    parser.add_argument(
        "-n", "--network",
        help="specify the TCP port(s) to listen too, may be used multiple times",
        dest="network",
        action="append",
        type=int,
        default=[]
    )

    parser.add_argument(
        "-c", "--counter",
        help="max. number of collected packets, use 0 to disable (default 1024)",
        dest="counter",
        type=int,
        default=1024
    )

    parser.add_argument(
        "-j", "--json",
        help="path to the JSON file to store the resulting data",
        dest="json"
    )

    parser.add_argument(
        "-r", "--remote",
        help="ip address(es) of the remote collector service(s) to be used by SSH",
        dest="remotes",
        action="append",
        default=[]
    )

    parser.add_argument(
        "-l", "--location",
        help="location of the remotely stored JSON data storage file",
        dest="location"
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
        process = threading.Thread(target=s.serve_forever, daemon=True)
        process.start()
        if arguments.verbose:
            print(f"Server thread {process} has been started on {port}")
    for remote in arguments.remotes:
        process = threading.Thread(target=get_remote, args=(remote, arguments.location), daemon=True)
        process.start()
        if arguments.verbose:
            print(f"Remote collector thread {process} has been started for {remote}")

    if arguments.verbose:
        print(f"Thread list: {threading.enumerate()}")

    while len(threading.enumerate()) > 1 and arguments.counter > 0:
        time.sleep(0.1)

    if arguments.json is not None:
        with open(arguments.json, "w") as f:
            json.dump(STORAGE, f, indent=4)

    print("Main thread has exited!")
