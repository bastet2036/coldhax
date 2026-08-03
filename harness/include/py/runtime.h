#ifndef COLDHAX_MICROPY_STUB_RUNTIME_H
#define COLDHAX_MICROPY_STUB_RUNTIME_H

#include "obj.h"

#ifndef MIN
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#endif

void mp_raise_OSError(int error);
void mp_raise_ValueError(const char *message);
int mp_obj_get_int_truncated(mp_obj_t value);
mp_obj_t mp_obj_new_int_from_uint(uint32_t value);
mp_obj_t mp_obj_new_int(uint32_t value);
void mp_get_buffer_raise(mp_obj_t value, mp_buffer_info_t *buffer, int flags);
void vstr_init_len(vstr_t *value, size_t length);
mp_obj_t mp_obj_new_str_from_vstr(const mp_obj_type_t *type, vstr_t *value);

#endif
