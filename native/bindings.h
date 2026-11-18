#ifndef SSZ_Z_BINDINGS_H
#define SSZ_Z_BINDINGS_H
#include <stddef.h>
#include <stdint.h>

/* The caller supplies valid input pointers (including for zero-length slices).
 * Operations: 0 JSON->SSZ (arbitrary field order), 1 SSZ->JSON, 2 SSZ->root, 3 default JSON,
 * 4 type schema JSON, 5 type names JSON, 6 validate SSZ (empty output),
 * 7 REST {data:...}->SSZ,
 * 8 block header SSZ (112 bytes) followed by unsigned block root (32 bytes),
 * 9 REST metadata JSON plus data_start/data_end byte offsets into the input.
 * ABI version 2. Calls share no mutable binding state.
 * Status: 0 success, 1 invalid input (output is an error name), 2 allocation failure.
 * Free every non-NULL output with ssz_z_free, including error messages.
 * Inputs and serialized outputs are limited to 512 MiB. */
uint8_t ssz_z_call(const uint8_t *fork, size_t fork_len,
                   const uint8_t *name, size_t name_len, uint8_t operation,
                   const uint8_t *input, size_t input_len,
                   uint8_t **output, size_t *output_len);
void ssz_z_free(uint8_t *output, size_t output_len);
uint32_t ssz_z_abi_version(void);
#endif
