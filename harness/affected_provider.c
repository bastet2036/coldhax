#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "provider.h"
#include "py/obj.h"
#include "py/runtime.h"

#define MICROPY_INCLUDED_STM32_RTC_H
#define MICROPY_INCLUDED_STM32_RNG_H
#define MICROPY_HW_ENABLE_RNG (0)

typedef struct { uint32_t CTRL, LOAD, VAL; } shim_systick_t;
typedef struct { uint32_t TR; uint32_t reserved[9]; uint32_t SSR; } shim_rtc_t;

static shim_systick_t shim_systick;
static shim_rtc_t shim_rtc;
static uint32_t shim_uid;

#define SysTick (&shim_systick)
#define RTC (&shim_rtc)
#define MP_HAL_UNIQUE_ID_ADDRESS ((uintptr_t)&shim_uid)

void rtc_init_finalise(void) { }

#include UPSTREAM_PROVIDER_SOURCE

void provider_configure(const uint32_t *values, size_t count) {
    if (count != 4) {
        mp_raise_ValueError("affected provider requires four register values");
    }
    shim_systick.VAL = values[0];
    shim_uid = values[1];
    shim_rtc.TR = values[2];
    shim_rtc.SSR = values[3];
}
