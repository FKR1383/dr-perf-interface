/* perfmark: mark regions of an application for drperf.
 *
 * Outside DynamoRIO these are empty functions (cost: one PLT call).
 * Under drperf they are wrapped with drwrap and delimit counted regions.
 * Regions nest per thread. state_name/state_value describe the application
 * state the region ran under (e.g. "n_entries", 4096); pass "" and 0 if none.
 */
#ifndef PERFMARK_H
#define PERFMARK_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void perfmark_begin(const char *region, const char *state_name, int64_t state_value);
/* Several declared states (at most 4): all of them form the aggregation key,
 * so the cost formula can be derived in all of them (`drperf derive`). */
void perfmark_begin_v(const char *region, int n, const char *const *names, const int64_t *values);
void perfmark_end(const char *region);
/* Attach an extra named value to the innermost open region (recorded per
 * trigger in the trace; not part of the aggregation key). */
void perfmark_state(const char *name, const char *value);
#ifdef __cplusplus
}
#endif
#endif
