#ifndef COLDHAX_MICROPY_STUB_OBJ_H
#define COLDHAX_MICROPY_STUB_OBJ_H

#include <stddef.h>
#include <stdint.h>

typedef void *mp_obj_t;
typedef unsigned long mp_uint_t;
typedef long mp_int_t;
typedef struct { const void *type; } mp_obj_base_t;
typedef struct { int placeholder; } mp_obj_type_t;
typedef struct { int placeholder; } mp_obj_dict_t;
typedef struct { uintptr_t key, value; } mp_rom_map_elem_t;
typedef struct { mp_obj_base_t base; mp_obj_dict_t *globals; } mp_obj_module_t;
typedef struct { void *buf; size_t len; } mp_buffer_info_t;
typedef struct { char *buf; size_t len; } vstr_t;

extern const mp_obj_type_t mp_type_bytes;
extern const mp_obj_type_t mp_type_module;
extern mp_obj_t mp_const_none;

#define STATIC static
#define MP_ERROR_TEXT(x) (x)
#define MP_BUFFER_WRITE (1)
#define MP_ROM_QSTR(x) 0
#define MP_ROM_PTR(x) 0
#define MP_QSTR___name__ (0)
#define MP_QSTR_random (0)
#define MP_QSTR_bytes (0)
#define MP_QSTR_uint32 (0)
#define MP_QSTR_uniform (0)
#define MP_QSTR_reseed (0)
#define MP_DEFINE_CONST_FUN_OBJ_0(name, fun) const int name = 0
#define MP_DEFINE_CONST_FUN_OBJ_1(name, fun) const int name = 0
#define MP_DEFINE_CONST_DICT(name, table) const int name = 0
#define MP_DECLARE_CONST_FUN_OBJ_0(name) extern const int name
#define MP_DECLARE_CONST_FUN_OBJ_1(name) extern const int name

#endif
