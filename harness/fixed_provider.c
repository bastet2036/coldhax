#include <stddef.h>
#include <stdint.h>

#include "provider.h"
#include "py/obj.h"
#include "py/runtime.h"
#include "py/mperrno.h"

#define MICROPY_HW_ENABLE_RNG (0)
#define RNG_CR_RNGEN (1u << 2)
#define RNG_SR_DRDY (1u << 0)

typedef struct { uint32_t CR, SR, DR; } shim_rng_t;
static shim_rng_t shim_rng;
#define RNG (&shim_rng)
#define __HAL_RCC_RNG_CLK_ENABLE() ((void)0)

static const uint32_t *shim_words;
static size_t shim_word_count;
static size_t shim_word_index;
static uint32_t shim_tick;

uint32_t HAL_GetTick(void) {
    if (shim_word_index >= shim_word_count) {
        mp_raise_OSError(MP_EFAULT);
    }
    shim_rng.DR = shim_words[shim_word_index++];
    shim_rng.SR = RNG_SR_DRDY;
    return shim_tick++;
}

#include UPSTREAM_PROVIDER_SOURCE

void provider_configure(const uint32_t *values, size_t count) {
    if (count < 8) {
        mp_raise_ValueError("fixed provider requires at least eight hardware words");
    }
    shim_words = values;
    shim_word_count = count;
    shim_word_index = 0;
    shim_tick = 0;
    shim_rng.CR = 0;
    shim_rng.SR = 0;
    shim_rng.DR = 0;
}
