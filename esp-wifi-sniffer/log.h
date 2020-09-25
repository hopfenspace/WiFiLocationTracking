#pragma once

#include <Arduino.h>

extern Print *logger;

typedef enum
{
	LOG_OFF,
	LOG_ERROR,
	LOG_WARNING,
	LOG_INFO,
	LOG_DEBUG,
} LogLevel;

void logZeroPadded(uint32_t val, int digits)
{
	uint8_t count;

	if(val == 0)
	{
		count = digits - 1;
	}
	else
	{
		count = 0;
		for(uint32_t val2 = val; val2 > 0; val2 /= 10)
		{
			count++;
		}


		count = digits - count;
	}

	for(; count > 0; count--)
		logger->print('0');

	logger->print(val);
}

void logMessagePrefix(LogLevel level, const char *file, int line)
{
	static const char * const levels[] = {
		"OFF",
		"ERROR",
		"WARNING",
		"INFO",
		"DEBUG",
	};

	uint32_t now = millis();

	logger->print('[');
	logZeroPadded(now / (60 * 60 * 1000), 4);
	logger->print(':');
	logZeroPadded((now / (60 * 1000)) % 60, 2);
	logger->print(':');
	logZeroPadded((now / 1000) % 60, 2);
	logger->print('.');
	logZeroPadded(now % 1000, 4);

	logger->print("] [");

	if(level < LOG_OFF || level > LOG_DEBUG)
		logger->print("???");
	else
		logger->print(levels[level]);

	logger->print("] [");

	char *file2 = strchr(file, '/');
	if(file2 != NULL)
		file = file2 + 1;

	if(file != NULL)
		logger->print(file);
	else
		logger->print("<unknown file>");


	logger->print(':');
	logger->print(line);
	logger->print("] ");
}

inline void logMessagePart()
{
}

template<typename T, typename... Args>
inline void logMessagePart(T curr, Args... rest)
{
	logger->print(curr);
	logMessagePart(rest...);
}

template<typename... Args>
inline void logMessage(LogLevel level, const char *file, int line, Args... args)
{
	if(level > LOGGING_LEVEL)
		return;

	logMessagePrefix(level, file, line);
	logMessagePart(args...);
	logger->println();
}
#define LOG(level, ...) logMessage(LOG_##level, __FILE__, __LINE__, __VA_ARGS__)