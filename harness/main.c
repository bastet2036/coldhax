#include <errno.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "provider.h"

void my_random_bytes(uint8_t *dest, uint32_t count);

static uint32_t parse_word(const char *text) {
    char *end = NULL;
    errno = 0;
    unsigned long value = strtoul(text, &end, 0);
    if (errno || !end || *end || value > UINT32_MAX) {
        fprintf(stderr, "invalid uint32: %s\n", text);
        exit(2);
    }
    return (uint32_t)value;
}

static void print_hex(const uint8_t *bytes, size_t count) {
    for (size_t index = 0; index < count; index++) {
        printf("%02x", bytes[index]);
    }
}

int main(int argc, char **argv) {
    if (argc < 2 || argc > 33) {
        fprintf(stderr, "usage: %s uint32 [uint32 ...]\n", argv[0]);
        return 2;
    }

    uint32_t values[32];
    for (int index = 1; index < argc; index++) {
        values[index - 1] = parse_word(argv[index]);
    }
    provider_configure(values, (size_t)(argc - 1));

    uint8_t raw[32];
    uint8_t digest[SHA256_DIGEST_LENGTH];
    my_random_bytes(raw, sizeof(raw));
    SHA256(raw, sizeof(raw), digest);

    printf("TEST-ONLY raw_entropy=");
    print_hex(raw, sizeof(raw));
    printf(" sha256_seed_entropy=");
    print_hex(digest, sizeof(digest));
    putchar('\n');
    return 0;
}
