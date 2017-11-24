
PREFIX = ieapspect-wrapper
CC = gcc

CFLAGS_FTD2XX = -L/opt/lib64 -l ftd2xx

ifeq ($(ASAN), 1)
	CFLAGS_ASAN = -lasan -O -g -fsanitize=address -fno-omit-frame-pointer
else
	CFLAGS_ASAN =
endif

CFLAGS = $(CFLAGS_ASAN) \
		 -Wall -Wno-unused-result -pthread -O2 -g3 \
		 $(shell pkg-config --libs --cflags libftdi1)

all: $(PREFIX)-dm100 $(PREFIX)-spectrig

$(PREFIX)-dm100-ftd2xx: dm100-ftd2xx.c
	$(CC) $(CFLAGS) $(CFLAGS_FTD2XX) -o $@ $^

$(PREFIX)-dm100: dm100.c
	$(CC) $(CFLAGS) -o $@ $^

$(PREFIX)-spectrig: spectrig.c
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f $(PREFIX)-*
