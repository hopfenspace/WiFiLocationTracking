#!/usr/bin/env python3

import subprocess
import xml.sax
import os
import time
import json
import traceback


client_list = []


class ClientInfo:
    def __init__(self):
        self.mac = ""
        self.rssi = ""
        self.mon = "0"

    def __str__(self):
        return self.mac


class ClientInfoHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.CurrentData = ""
        self.current_client = None
        self.in_client = False

    def startElement(self, tag, argument):
        self.CurrentData = tag
        if tag == "wireless-client":
            self.in_client = True
            self.current_client = ClientInfo()

    def endElement(self, tag):
        global client_list
        if tag == "wireless-client":
            self.in_client = False
            client_list.append(self.current_client.__dict__)
        self.CurrentData = ""

    def characters(self, content):
        if self.CurrentData == "client-mac":
            self.current_client.mac = content
        elif self.CurrentData == "last_signal_rssi":
            self.current_client.rssi = content


def main():
    storage = "export-01.kismet.netxml"
    if os.path.exists(storage):
        os.remove(storage)

    s = subprocess.Popen(
        ["airodump-ng", "--output-format", "netxml", "--bssid", "50:C7:BF:BA:F4:12", "-w" "export", "mon0"]
    )
    time.sleep(3)
    os.system("kill -2 " + str(s.pid))

    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = ClientInfoHandler()
    parser.setContentHandler(handler)

    try:
        parser.parse(storage)
    except xml.sax.SAXParseException:
        traceback.print_exc()

    with open("export.json", "w") as f:
        json.dump(client_list, f)


if __name__ == "__main__":
    c = 1
    while True:
        print(f"Starting round {c}...")
        main()
        c += 1
