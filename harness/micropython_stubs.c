#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "py/runtime.h"

const mp_obj_type_t mp_type_bytes = {0};
const mp_obj_type_t mp_type_module = {0};
mp_obj_t mp_const_none = NULL;

static _Noreturn void die(const char *kind, const char *message) {
    fprintf(stderr, "TEST-ONLY harness %s: %s\n", kind, message ? message : "(none)");
    exit(2);
}

void mp_raise_OSError(int error) {
    char message[64];
    snprintf(message, sizeof(message), "MicroPython OSError %d", error);
    die("fault", message);
}

void mp_raise_ValueError(const char *message) { die("value error", message); }
int mp_obj_get_int_truncated(mp_obj_t value) { (void)value; die("unsupported", "Python API invoked"); }
mp_obj_t mp_obj_new_int_from_uint(uint32_t value) { (void)value; die("unsupported", "Python API invoked"); }
mp_obj_t mp_obj_new_int(uint32_t value) { (void)value; die("unsupported", "Python API invoked"); }
void mp_get_buffer_raise(mp_obj_t value, mp_buffer_info_t *buffer, int flags) {
    (void)value; (void)buffer; (void)flags; die("unsupported", "Python API invoked");
}
void vstr_init_len(vstr_t *value, size_t length) {
    (void)value; (void)length; die("unsupported", "Python API invoked");
}
mp_obj_t mp_obj_new_str_from_vstr(const mp_obj_type_t *type, vstr_t *value) {
    (void)type; (void)value; die("unsupported", "Python API invoked");
}
