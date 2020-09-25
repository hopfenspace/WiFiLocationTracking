#include <Arduino.h>
#include <ESP8266WiFi.h>

extern "C" {
#include <user_interface.h>
}

#include "config.h"
#include "log.h"

#define DATA_LENGTH           112

#define TYPE_MANAGEMENT       0x00
#define TYPE_CONTROL          0x01
#define TYPE_DATA             0x02
#define SUBTYPE_PROBE_REQUEST 0x04
#define SUBTYPE_BEACON        0x08

struct RxControl
{
	signed rssi:8; // signal intensity of packet
	unsigned rate:4;
	unsigned is_group:1;
	unsigned:1;
	unsigned sig_mode:2; // 0:is 11n packet; 1:is not 11n packet;
	unsigned legacy_length:12; // if not 11n packet, shows length of packet.
	unsigned damatch0:1;
	unsigned damatch1:1;
	unsigned bssidmatch0:1;
	unsigned bssidmatch1:1;
	unsigned MCS:7; // if is 11n packet, shows the modulation and code used (range from 0 to 76)
	unsigned CWB:1; // if is 11n packet, shows if is HT40 packet or not
	unsigned HT_length:16;// if is 11n packet, shows length of packet.
	unsigned Smoothing:1;
	unsigned Not_Sounding:1;
	unsigned:1;
	unsigned Aggregation:1;
	unsigned STBC:2;
	unsigned FEC_CODING:1; // if is 11n packet, shows if is LDPC packet or not.
	unsigned SGI:1;
	unsigned rxend_state:8;
	unsigned ampdu_cnt:8;
	unsigned channel:4; //which channel this packet in.
	unsigned:12;
};

typedef struct
{
	struct RxControl rx_ctrl;
	uint8_t data[DATA_LENGTH];
	uint16_t cnt;
	uint16_t len;
} SnifferPacket;

typedef struct
{
	uint8_t mac[6];
	uint16_t isUsed : 1;
	uint32_t firstSeen;
	uint32_t lastSeen;
} WifiDevice;

Print *logger;

uint32_t calculate_crc32_step(uint32_t crc, uint8_t byte)
{
	int8_t i;
	crc = crc ^ byte;
	for(i = 7; i >= 0; i--)
		crc = (crc >> 1) ^ (0xedb88320ul & (-(crc&1)));
	return crc;
}
uint32_t calculate_crc32(uint8_t *data, uint32_t len)
{
	uint32_t reg = 0xffffffff;
	for(int i = 0; i < len; i++)
		reg = calculate_crc32_step(reg, data[i]);

	return reg;
}

static void getMAC(char *addr, uint8_t* data)
{
	sprintf(addr, "%02x:%02x:%02x:%02x:%02x:%02x",
		data[0], data[1], data[2],
		data[3], data[4], data[5]
	);
}

static void ICACHE_FLASH_ATTR sniffer_callback(uint8_t *buffer, uint16_t length)
{
	if(length != 128)
		return;

	SnifferPacket *snifferPacket = (SnifferPacket*) buffer;
	if(snifferPacket->len < DATA_LENGTH)
		memset(snifferPacket->data + snifferPacket->len, 0, DATA_LENGTH - snifferPacket->len);

	char mac[32];
	getMAC(mac, snifferPacket->data + 10);

	uint32_t checksum = calculate_crc32(snifferPacket->data, DATA_LENGTH);
	if(checksum & 0x7f != 0)
		return;

	Serial.print(mac);
	Serial.print(" ");
	Serial.print(snifferPacket->rx_ctrl.rssi);
	Serial.print(" ");
	Serial.println(checksum, 16);
}

void startSniffing()
{
	delay(10);
	wifi_set_opmode(STATION_MODE);
	wifi_set_channel(WIFI_CHANNEL);
	wifi_promiscuous_enable(0);
	delay(10);
	wifi_set_promiscuous_rx_cb(sniffer_callback);
	delay(10);
	wifi_promiscuous_enable(1);
}
void stopSniffing()
{
	wifi_promiscuous_enable(0);
	WiFi.mode(WIFI_OFF);
}

void setup()
{
	// set the WiFi chip to "promiscuous" mode
	Serial.begin(115200);
	logger = &Serial;

	startSniffing();
}

void loop()
{
	delay(100);
}
