/* drperf.c -- DynamoRIO client: exact instruction counts per perfmark region.
 *
 * Counting: every basic block gets two inline adds, into the thread's total
 * instruction counter (raw TLS slot 0) and into the current region's
 * per-basic-block counter array (pointer in raw TLS slot 1), indexed by a
 * slot id assigned once per basic block.
 *
 * Markers: perfmark_begin/perfmark_end/perfmark_state are wrapped with
 * drwrap.  Each thread keeps its own region stack, key cache and statistics,
 * so the marker path takes no lock in the common case.  Threads with no
 * open region of their own follow the innermost region of the leader (the
 * first thread that opened a region; replaced only when it exits); followers
 * get a private counter array per region so counts stay exact under
 * concurrency, and follower pointers are only rewritten when the leader's
 * innermost region changes, so other threads' markers stay lock-free.
 *
 * Regions are keyed by (region, state_name, state_value, root region) and
 * aggregated over instances; every instance is also appended to a per-thread
 * trace (sequence numbers, timestamps, extra states) written as JSON lines.
 * At exit per-slot counts are folded into per-module and per-symbol counts
 * (drsyms) and everything is written as JSON.
 *
 * Options (client args):  -o FILE  -top N  -max_slots N  -trace N (records,
 *   0 = off)  -blocks (dump per-region per-basic-block counts to FILE.blocks
 *   and the block table to FILE.slots)  -no_rep_expand  -no_symbols  -verbose
 *   -exclude_cuda_module BASENAME  -no_follow_threads
 */
#include "dr_api.h"
#include "drmgr.h"
#include "drreg.h"
#include "drwrap.h"
#include "drutil.h"
#include "drx.h"
#include "drsyms.h"
#include "hashtable.h"
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>

#define DRPERF_VERSION "0.3"
#define MAX_DEPTH 64
#define RNAME_MAX 160
#define SYM_MAX 512
#define MAX_MODULES 4096
#define MAX_THREADS 4096
#define MAX_STATES 40
#define STATE_NAME_MAX 64
#define STATE_VAL_MAX 64
#define TRACE_CHUNK 256
#define MAX_KEYS 65536
#define KEYS_PER_REGION 128        /* distinct state combinations kept per region */
/* Counter arrays are mapped, not committed: a key only faults in the pages of
 * the blocks it actually runs, so this bounds address space, not memory. */
#define COUNTER_BUDGET (96ULL << 30)
#define STACK_KEY_STATES 8  /* allocation-free marker fast path, not a limit */

/* ------------------------------------------------------------------ types */

typedef struct {
    uint64 count, incl_sum, incl_min, incl_max, self_sum, self_min, self_max;
    uint64 sys_sum, implicit_ends;
} kstats_t;

typedef struct _rkey_t {
    char region[RNAME_MAX];
    char state_name[RNAME_MAX]; /* first declared state (kept for readers of the JSON) */
    int64 state_value;
    bool overflow;              /* the "<other>" bucket: state combinations beyond the budget */
    int nkstates;               /* all declared states in the aggregation key */
    char (*kname)[STATE_NAME_MAX];
    int64 *kval;
    char parent[RNAME_MAX]; /* enclosing region at first instance */
    char root[RNAME_MAX];   /* outermost open region when begun; part of the key */
    int index;
    uint64 **tslots;        /* per-thread per-bb self counts */
    struct _rkey_t *next;
} rkey_t;

typedef struct {
    char name[STATE_NAME_MAX];
    char value[STATE_VAL_MAX];
} state_t;

typedef struct {
    rkey_t *key;
    uint64 *cur;            /* counter array this frame counts into */
    uint64 total_at_begin;
    uint64 sys_at_begin;
    uint64 children_incl;
    int64 seq_begin;
    uint64 t_begin_us;
    int nstates;
    state_t states[MAX_STATES];
} frame_t;

typedef struct {
    rkey_t *key;
    int64 seq_begin, seq_end;
    uint64 t_begin_us, t_end_us;
    uint64 clock_begin; /* thread instruction clock at begin */
    uint64 incl, self, sys;
    int nstates;
    bool implicit;
    state_t states[MAX_STATES];
} trace_rec_t;

typedef struct _trace_chunk_t {
    trace_rec_t recs[TRACE_CHUNK];
    int n;
    struct _trace_chunk_t *next;
} trace_chunk_t;

typedef struct _thread_t {
    volatile uint64 *total_ptr; /* raw TLS slot 0 of this thread */
    uint64 *followed;           /* what the leader last installed for this thread */
    uint64 final_total;
    uint64 excluded_total;
    uint64 sys;
    thread_id_t tid;
    int index;
    bool alive;
    bool bb_expanded;
    int depth;
    frame_t stack[MAX_DEPTH];
    kstats_t *stats;            /* per-key statistics, indexed by key index; thread-private */
    hashtable_t key_cache;      /* key string -> rkey_t*, thread-private */
    struct {
        uint64 hash;            /* of the key's contents, not its addresses */
        rkey_t *key;
    } fast[512];                /* content-keyed cache in front of key_cache */
    trace_chunk_t *trace_head, *trace_tail;
    struct _thread_t *next;
} thread_t;

typedef struct {
    char name[RNAME_MAX];
    char path[512];
    app_pc start, end;
} module_t;

typedef struct {
    int mod;
    size_t start_offs;
    char name[SYM_MAX];
} sym_t;

/* ---------------------------------------------------------------- globals */

static char opt_out[512] = "drperf.json";
static int opt_top = 25;
static uint64 opt_max_slots = 1024 * 1024;   /* counter slots per key per thread (8 MB) */
static int64 opt_trace = 500000;
static bool opt_rep_expand = true;
static bool opt_symbols = true;
static bool opt_verbose = false;
static bool opt_block_counters = true;   /* -no_block_counters: keep only the thread total */
static bool opt_blocks = false;
static bool opt_follow_threads = true;
static char opt_exclude_cuda_module[128];
static int excluded_wrappers;
static int64 excluded_calls;
static file_t blocks_file = INVALID_FILE;
static byte *slot_used;          /* slots referenced by any region (for the .slots table) */

static int tls_idx;
static reg_id_t tls_seg;
static uint tls_offs;
#define TLS_TOTAL (tls_offs)
#define TLS_CUR (tls_offs + sizeof(void *))
#define TLS_EXCLUDE_DEPTH (tls_offs + 2 * sizeof(void *))
#define TLS_EXCLUDE_COUNT (tls_offs + 3 * sizeof(void *))

static void *threads_rw;     /* thread list: readers = marker path, writers = thread init/exit */
static void *keys_lock;      /* key creation, lazy per-thread arrays */
static void *leader_lock;    /* leader / shared_key changes */
static void *slots_lock;     /* bb slot assignment, module table */
static thread_t *threads;
static int nthreads_seen;

static hashtable_t slot_table;
static uint64 next_slot;
static app_pc *slot_pc;
static int *slot_mod;
static int *slot_sym;
static uint64 *dummy_slots;
static uint64 slots_overflow;
static uint64 counter_bytes;
static volatile int64 counter_denied;

static hashtable_t key_table;
static struct { char region[RNAME_MAX]; int n; } region_keys[64];
static int nregion_keys;

/* A region whose declared state takes very many values would otherwise get a
 * counter array per value.  A formula needs a handful of points, so keep the
 * first KEYS_PER_REGION combinations and fold the rest into one bucket that
 * the analysis ignores. */
static void safe_strcpy(char *dst, const char *src, size_t n);

static const char *empty_name = "";
static const int64 zero_val = 0;

static bool
region_key_budget(const char *region)
{
    int i;
    for (i = 0; i < nregion_keys; i++) {
        if (strcmp(region_keys[i].region, region) == 0) {
            if (region_keys[i].n >= KEYS_PER_REGION)
                return false;
            region_keys[i].n++;
            return true;
        }
    }
    if (nregion_keys < (int)(sizeof(region_keys) / sizeof(region_keys[0]))) {
        safe_strcpy(region_keys[nregion_keys].region, region, RNAME_MAX);
        region_keys[nregion_keys].n = 1;
        nregion_keys++;
    }
    return true;
}
static rkey_t *keys, *keys_tail;
static int nkeys;

static hashtable_t mod_table;
static module_t modules[MAX_MODULES];
static int nmodules;
static app_pc main_module_start;

static hashtable_t sym_table;
static sym_t *syms;
static int nsyms, syms_cap;

/* Hot shared counters get their own cache lines; the rarely written
 * leader/shared_key pair shares one that every begin reads. */
static volatile int64 seq_counter __attribute__((aligned(64)));
static volatile int64 trace_records __attribute__((aligned(64)));
static volatile int64 trace_dropped __attribute__((aligned(64)));
static volatile int64 unmatched_ends, depth_overflows, state_overflows;
static bool marker_seen;

static struct {
    rkey_t *volatile shared_key; /* region followed by threads with no open region */
    thread_t *volatile leader;
} __attribute__((aligned(64))) L;
#define shared_key L.shared_key
#define leader L.leader
static uint64 tsc0, us0;             /* anchors to convert rdtsc ticks to microseconds */

static inline uint64
rdtsc(void)
{
    unsigned lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64)hi << 32) | lo;
}

/* -------------------------------------------------------------- helpers */

static thread_t *
cur_thread(void *drcontext)
{
    return (thread_t *)drmgr_get_tls_field(drcontext, tls_idx);
}

static void
safe_strcpy(char *dst, const char *src, size_t cap)
{
    size_t i = 0;
    if (src == NULL)
        src = "";
    for (; i + 1 < cap && src[i] != '\0'; i++)
        dst[i] = src[i];
    dst[i] = '\0';
}

static uint64 *
slots_for(rkey_t *k, thread_t *t)
{
    uint64 *s;
    if (k == NULL)
        return dummy_slots;
    s = k->tslots[t->index];
    if (s != NULL)
        return s;
    dr_mutex_lock(keys_lock);
    if (k->tslots[t->index] == NULL) {
        uint64 bytes = opt_max_slots * sizeof(uint64);
        if (counter_bytes + bytes > COUNTER_BUDGET) {
            /* out of counter memory: this key counts nowhere rather than into
               another key's array, and the run says so */
            dr_atomic_add64_return_sum(&counter_denied, 1);
            dr_mutex_unlock(keys_lock);
            return dummy_slots;
        }
        s = dr_raw_mem_alloc(bytes, DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
        if (s == NULL) {
            /* the counting code writes through this pointer, so it must never
               be null: count nowhere and say so rather than fault in the app */
            dr_atomic_add64_return_sum(&counter_denied, 1);
            dr_mutex_unlock(keys_lock);
            return dummy_slots;
        }
        counter_bytes += bytes;
        k->tslots[t->index] = s;
    }
    s = k->tslots[t->index];
    dr_mutex_unlock(keys_lock);
    return s;
}

static kstats_t *
stats_for(rkey_t *k, thread_t *t)
{
    kstats_t *s;
    if (t->stats == NULL) {
        t->stats = dr_raw_mem_alloc(MAX_KEYS * sizeof(kstats_t), DR_MEMPROT_READ | DR_MEMPROT_WRITE,
                                    NULL);
        if (t->stats == NULL) {
            dr_fprintf(STDERR, "drperf: out of memory for per-thread statistics\n");
            dr_abort();
        }
    }
    s = &t->stats[k->index];
    if (s->count == 0 && s->incl_min == 0)
        s->incl_min = s->self_min = ~(uint64)0;
    return s;
}

/* Only the thread itself stores here while it is running its own regions. */
static void
set_thread_cur(thread_t *t, uint64 *slots)
{
    *(uint64 *volatile *)((byte *)t->total_ptr + sizeof(void *)) = slots;
    t->followed = slots;
}

/* Point a thread that has no region of its own at the leader's counters.  Runs
 * on the leader, so it may only replace the value it installed itself: a thread
 * that opened its own region between the depth check and here has stored its
 * own pointer, the exchange fails, and its work stays in its own region. */
static void
steer_follower(thread_t *t, uint64 *slots)
{
    uint64 **cur = (uint64 **)((byte *)t->total_ptr + sizeof(void *));
    if (__sync_bool_compare_and_swap(cur, t->followed, slots))
        t->followed = slots;
}

/* Does this key describe exactly (region, states, root)?  Compares the copies
 * the key owns, so it is safe against the caller's strings being freed. */
static bool
key_matches(rkey_t *k, const char *region, int nk, const char *const *names, const int64 *vals,
            const char *root)
{
    int i, want = (nk == 1 && names[0][0] == '\0') ? 0 : nk;
    if (k->overflow || k->nkstates != want || strcmp(k->region, region) != 0 ||
        strcmp(k->root, root) != 0)
        return false;
    for (i = 0; i < want; i++) {
        if (k->kval[i] != vals[i] || strcmp(k->kname[i], names[i]) != 0)
            return false;
    }
    return true;
}

static void
remember_key(thread_t *t, uint h, uint64 hv, rkey_t *k)
{
    t->fast[h].hash = hv;
    t->fast[h].key = k;
}

static rkey_t *
get_key(thread_t *t, const char *region, int nk, const char *const *names, const int64 *vals,
        const char *parent, rkey_t *rootkey)
{
    char stack_kbuf[2 * RNAME_MAX + STACK_KEY_STATES * (STATE_NAME_MAX + 24) + 32];
    char *kbuf = stack_kbuf;
    size_t kbuf_size = sizeof(stack_kbuf), pos;
    char nbuf[STATE_NAME_MAX];
    const char *root = rootkey != NULL ? rootkey->region : "";
    bool overflow = false;
    const char *state_name = names[0];
    int64 state_value = vals[0];
    rkey_t *k;
    uint h;
    uint64 hv;
    const char *cp;
    int i, w;
    bool hit;
    /* Fast path.  The marker fires once per region and building the string key
     * below costs microseconds, so hash the contents and verify against the
     * key's own copies: the caller's strings may be freed and their addresses
     * reused (Python bytes are), so comparing addresses can return another
     * region's key. */
    hv = 1469598103934665603ULL;
    for (cp = region; *cp != '\0'; cp++)
        hv = (hv ^ (unsigned char)*cp) * 1099511628211ULL;
    for (cp = root; *cp != '\0'; cp++)
        hv = (hv ^ (unsigned char)*cp) * 1099511628211ULL;
    for (i = 0; i < nk; i++) {
        for (cp = names[i]; *cp != '\0'; cp++)
            hv = (hv ^ (unsigned char)*cp) * 1099511628211ULL;
        hv = (hv ^ (uint64)vals[i]) * 1099511628211ULL;
    }
    h = (uint)(hv & 511);
    hit = t->fast[h].hash == hv && t->fast[h].key != NULL &&
          key_matches(t->fast[h].key, region, nk, names, vals, root);
    if (hit)
        return t->fast[h].key;

    if (nk > STACK_KEY_STATES) {
        if ((size_t)nk > (SIZE_MAX - 2 * RNAME_MAX - 32) / (STATE_NAME_MAX + 24)) {
            dr_fprintf(STDERR, "drperf: declared state key is too large\n");
            dr_abort();
        }
        kbuf_size = 2 * RNAME_MAX + (size_t)nk * (STATE_NAME_MAX + 24) + 32;
        kbuf = dr_thread_alloc(dr_get_current_drcontext(), kbuf_size);
        if (kbuf == NULL) {
            dr_fprintf(STDERR, "drperf: out of memory for declared state key\n");
            dr_abort();
        }
    }
    pos = 0;
    w = dr_snprintf(kbuf, kbuf_size, "%s", region);
    pos = w < 0 ? kbuf_size - 1 : (size_t)w;
    for (i = 0; i < nk && pos < kbuf_size - 1; i++) {
        safe_strcpy(nbuf, names[i], STATE_NAME_MAX);
        w = dr_snprintf(kbuf + pos, kbuf_size - pos, "\1%s=%lld", nbuf, (long long)vals[i]);
        pos = w < 0 ? kbuf_size - 1 : pos + (size_t)w;
    }
    if (pos < kbuf_size - 1)
        dr_snprintf(kbuf + pos, kbuf_size - pos, "\1%s", root);
    kbuf[kbuf_size - 1] = '\0';
    k = hashtable_lookup(&t->key_cache, kbuf);
    if (k != NULL) {
        remember_key(t, h, hv, k);
        if (kbuf != stack_kbuf)
            dr_thread_free(dr_get_current_drcontext(), kbuf, kbuf_size);
        return k;
    }
    dr_mutex_lock(keys_lock);
    k = hashtable_lookup(&key_table, kbuf);
    if (k == NULL &&
        (counter_bytes + opt_max_slots * sizeof(uint64) > COUNTER_BUDGET || !region_key_budget(region))) {
        overflow = true;
        /* out of budget: one shared bucket per region, not counted per state */
        dr_snprintf(kbuf, kbuf_size, "%s\1<other>", region);
        kbuf[kbuf_size - 1] = '\0';
        k = hashtable_lookup(&key_table, kbuf);
        nk = 0;
        names = &empty_name;
        vals = &zero_val;
        overflow = true;
    }
    if (k == NULL) {
        k = dr_global_alloc(sizeof(*k));
        memset(k, 0, sizeof(*k));
        safe_strcpy(k->region, region, RNAME_MAX);
        safe_strcpy(k->state_name, nk > 0 ? names[0] : "", RNAME_MAX);
        safe_strcpy(k->parent, parent, RNAME_MAX);
        safe_strcpy(k->root, root, RNAME_MAX);
        k->state_value = nk > 0 ? vals[0] : 0;
        k->nkstates = (nk == 1 && names[0][0] == '\0') ? 0 : nk;
        k->overflow = overflow;
        if (k->nkstates > 0) {
            k->kname = dr_global_alloc((size_t)k->nkstates * sizeof(*k->kname));
            k->kval = dr_global_alloc((size_t)k->nkstates * sizeof(*k->kval));
            if (k->kname == NULL || k->kval == NULL) {
                dr_fprintf(STDERR, "drperf: out of memory for declared states\n");
                dr_abort();
            }
        }
        for (i = 0; i < k->nkstates; i++) {
            safe_strcpy(k->kname[i], names[i], STATE_NAME_MAX);
            k->kval[i] = vals[i];
        }
        k->index = nkeys++;
        DR_ASSERT_MSG(k->index < MAX_KEYS, "drperf: too many region keys");
        k->tslots = dr_global_alloc(MAX_THREADS * sizeof(uint64 *));
        if (k->tslots == NULL) {
            dr_fprintf(STDERR, "drperf: out of memory for region keys\n");
            dr_abort();
        }
        memset(k->tslots, 0, MAX_THREADS * sizeof(uint64 *));
        hashtable_add(&key_table, kbuf, k);
        if (keys_tail == NULL)
            keys = k;
        else
            keys_tail->next = k;
        keys_tail = k;
    }
    dr_mutex_unlock(keys_lock);
    hashtable_add(&t->key_cache, kbuf, k);
    remember_key(t, h, hv, k);
    if (kbuf != stack_kbuf)
        dr_thread_free(dr_get_current_drcontext(), kbuf, kbuf_size);
    return k;
}

/* Leader bookkeeping.  Called by the leader when its innermost region
 * changed, by a thread opening a region while there is no leader, and when
 * the leader exits. */
static void
update_shared(thread_t *self)
{
    thread_t *t;
    rkey_t *nk;
    /* One thread: there are no followers to steer, so this is two stores and
     * no locks.  Markers fire once per region, so this path must stay cheap. */
    if (nthreads_seen <= 1) {
        leader = (self != NULL && self->depth > 0) ? self : NULL;
        shared_key = leader != NULL ? leader->stack[leader->depth - 1].key : NULL;
        /* a thread with no region of its own counts into the shared key, as in
         * the general path below: instructions between regions belong to no one */
        if (self != NULL && self->depth == 0)
            set_thread_cur(self, slots_for(opt_follow_threads ? shared_key : NULL, self));
        return;
    }
    dr_mutex_lock(leader_lock);
    if (leader != NULL && !leader->alive)
        leader = NULL;
    if (leader == NULL && self != NULL && self->depth > 0)
        leader = self;
    nk = (leader != NULL && leader->depth > 0) ? leader->stack[leader->depth - 1].key : NULL;
    if (nk != shared_key) {
        shared_key = nk;
        /* only when the region the followers count into actually changed */
        dr_rwlock_read_lock(threads_rw);
        for (t = threads; t != NULL; t = t->next) {
            if (opt_follow_threads && t->alive && t->depth == 0)
                steer_follower(t, slots_for(nk, t));
        }
        dr_rwlock_read_unlock(threads_rw);
    }
    dr_mutex_unlock(leader_lock);
}

/* --------------------------------------------------------------- trace */

static void
trace_append(thread_t *t, frame_t *f, int64 seq_end, uint64 t_end, uint64 incl, uint64 self,
             uint64 sys, bool implicit)
{
    trace_chunk_t *c;
    trace_rec_t *r;
    if (opt_trace <= 0)
        return;
    if (dr_atomic_add64_return_sum(&trace_records, 1) > opt_trace) {
        dr_atomic_add64_return_sum(&trace_dropped, 1);
        return;
    }
    c = t->trace_tail;
    if (c == NULL || c->n == TRACE_CHUNK) {
        c = dr_global_alloc(sizeof(trace_chunk_t));
        c->n = 0;
        c->next = NULL;
        if (t->trace_tail == NULL)
            t->trace_head = c;
        else
            t->trace_tail->next = c;
        t->trace_tail = c;
    }
    r = &c->recs[c->n++];
    r->key = f->key;
    r->seq_begin = f->seq_begin;
    r->seq_end = seq_end;
    r->t_begin_us = f->t_begin_us;
    r->t_end_us = t_end;
    r->clock_begin = f->total_at_begin;
    r->incl = incl;
    r->self = self;
    r->sys = sys;
    r->implicit = implicit;
    r->nstates = f->nstates;
    memcpy(r->states, f->states, f->nstates * sizeof(state_t));
}

/* ------------------------------------------------------------- markers */

static void
close_frame(thread_t *t, uint64 total, int64 seq_end, uint64 t_end, bool implicit)
{
    frame_t *f = &t->stack[t->depth - 1];
    rkey_t *k = f->key;
    kstats_t *s = stats_for(k, t);
    uint64 incl = total - f->total_at_begin;
    uint64 self = incl - f->children_incl;
    uint64 sys = t->sys - f->sys_at_begin;
    s->count++;
    s->incl_sum += incl;
    if (incl < s->incl_min)
        s->incl_min = incl;
    if (incl > s->incl_max)
        s->incl_max = incl;
    s->self_sum += self;
    if (self < s->self_min)
        s->self_min = self;
    if (self > s->self_max)
        s->self_max = self;
    s->sys_sum += sys;
    if (implicit)
        s->implicit_ends++;
    trace_append(t, f, seq_end, t_end, incl, self, sys, implicit);
    t->depth--;
    if (t->depth > 0)
        t->stack[t->depth - 1].children_incl += incl;
}

static void
begin_common(thread_t *t, uint64 total, const char *region, int nk, const char *const *names,
             const int64 *vals)
{
    const char *parent;
    frame_t *f;
    rkey_t *k;
    if (region == NULL || region[0] == '\0')
        region = "<unnamed>";
    if (!marker_seen)
        marker_seen = true;
    if (t->depth >= MAX_DEPTH) {
        dr_atomic_add64_return_sum(&depth_overflows, 1);
        return;
    }
    parent = t->depth > 0 ? t->stack[t->depth - 1].key->region : "";
    k = get_key(t, region, nk, names, vals, parent, t->depth > 0 ? t->stack[0].key : NULL);
    f = &t->stack[t->depth++];
    f->key = k;
    f->total_at_begin = total;
    f->sys_at_begin = t->sys;
    f->children_incl = 0;
    if (opt_trace > 0) {
        f->seq_begin = dr_atomic_add64_return_sum(&seq_counter, 1);
        f->t_begin_us = rdtsc();
    }
    f->nstates = 0;
    f->cur = slots_for(k, t);
    set_thread_cur(t, f->cur);
    if (leader == NULL || leader == t)
        update_shared(t);
}

/* perfmark_begin(region, state_name, state_value): one declared state */
static void
pre_begin(void *wrapcxt, void **user_data)
{
    void *drcontext = drwrap_get_drcontext(wrapcxt);
    thread_t *t = cur_thread(drcontext);
    uint64 total = *t->total_ptr;
    const char *region = (const char *)drwrap_get_arg(wrapcxt, 0);
    const char *sname = (const char *)drwrap_get_arg(wrapcxt, 1);
    int64 sval = (int64)(ptr_int_t)drwrap_get_arg(wrapcxt, 2);
    if (sname == NULL)
        sname = "";
    begin_common(t, total, region, 1, &sname, &sval);
}

/* perfmark_begin_v(region, n, names[], values[]): all n declared
 * states form the key, so block counts are kept per combination
 * of their values and a formula can be derived in all of them. */
static void
pre_begin_v(void *wrapcxt, void **user_data)
{
    void *drcontext = drwrap_get_drcontext(wrapcxt);
    thread_t *t = cur_thread(drcontext);
    uint64 total = *t->total_ptr;
    const char *region = (const char *)drwrap_get_arg(wrapcxt, 0);
    int n = (int)(ptr_int_t)drwrap_get_arg(wrapcxt, 1);
    const char *const *anames = (const char *const *)drwrap_get_arg(wrapcxt, 2);
    const int64 *avals = (const int64 *)drwrap_get_arg(wrapcxt, 3);
    const char *stack_names[STACK_KEY_STATES];
    int64 stack_vals[STACK_KEY_STATES];
    const char **names = stack_names;
    int64 *vals = stack_vals;
    int i, nk = 0;
    if (n > STACK_KEY_STATES) {
        if ((size_t)n > SIZE_MAX / sizeof(*names) || (size_t)n > SIZE_MAX / sizeof(*vals)) {
            dr_fprintf(STDERR, "drperf: too many declared states\n");
            dr_abort();
        }
        names = dr_thread_alloc(drcontext, (size_t)n * sizeof(*names));
        vals = dr_thread_alloc(drcontext, (size_t)n * sizeof(*vals));
        if (names == NULL || vals == NULL) {
            dr_fprintf(STDERR, "drperf: out of memory for marker states\n");
            dr_abort();
        }
    }
    for (i = 0; i < n; i++) {
        const char *nm = NULL;
        int64 v = 0;
        if (anames == NULL || avals == NULL || !dr_safe_read(&anames[i], sizeof(nm), &nm, NULL) ||
            !dr_safe_read(&avals[i], sizeof(v), &v, NULL) || nm == NULL)
            break;
        names[nk] = nm;
        vals[nk] = v;
        nk++;
    }
    if (nk == 0) {
        names[0] = "";
        vals[0] = 0;
        nk = 1;
    }
    begin_common(t, total, region, nk, names, vals);
    if (n > STACK_KEY_STATES) {
        dr_thread_free(drcontext, names, (size_t)n * sizeof(*names));
        dr_thread_free(drcontext, vals, (size_t)n * sizeof(*vals));
    }
}

static void
pre_end(void *wrapcxt, void **user_data)
{
    void *drcontext = drwrap_get_drcontext(wrapcxt);
    thread_t *t = cur_thread(drcontext);
    uint64 total = *t->total_ptr;
    const char *region = (const char *)drwrap_get_arg(wrapcxt, 0);
    int64 seq_end;
    uint64 t_end;
    int i;
    if (region == NULL || region[0] == '\0')
        region = "<unnamed>";
    for (i = t->depth - 1; i >= 0; i--) {
        if (strcmp(t->stack[i].key->region, region) == 0)
            break;
    }
    if (i < 0) {
        dr_atomic_add64_return_sum(&unmatched_ends, 1);
        return;
    }
    seq_end = t_end = 0;
    if (opt_trace > 0) {
        seq_end = dr_atomic_add64_return_sum(&seq_counter, 1);
        t_end = rdtsc();
    }
    while (t->depth - 1 > i)
        close_frame(t, total, seq_end, t_end, true);
    close_frame(t, total, seq_end, t_end, false);
    if (t->depth > 0)
        set_thread_cur(t, t->stack[t->depth - 1].cur);
    else
        set_thread_cur(t, slots_for(opt_follow_threads ? shared_key : NULL, t));
    if (leader == t)
        update_shared(t);
}

static void
pre_state(void *wrapcxt, void **user_data)
{
    void *drcontext = drwrap_get_drcontext(wrapcxt);
    thread_t *t = cur_thread(drcontext);
    const char *name = (const char *)drwrap_get_arg(wrapcxt, 0);
    const char *value = (const char *)drwrap_get_arg(wrapcxt, 1);
    frame_t *f;
    state_t *s;
    if (t->depth == 0)
        return;
    f = &t->stack[t->depth - 1];
    if (f->nstates >= MAX_STATES) {
        dr_atomic_add64_return_sum(&state_overflows, 1);
        return;
    }
    s = &f->states[f->nstates++];
    safe_strcpy(s->name, name, STATE_NAME_MAX);
    safe_strcpy(s->value, value, STATE_VAL_MAX);
}

/* ------------------------------------------------------------- modules */

/* Suppress synchronous work below explicitly selected emulator CUDA exports.
 * The depth is thread-local: independent work on other threads stays counted. */
static void
pre_excluded_cuda(void *wrapcxt, void **user_data)
{
    byte *base = dr_get_dr_segment_base(tls_seg);
    (*(ptr_uint_t *)(base + TLS_EXCLUDE_DEPTH))++;
    dr_atomic_add64_return_sum(&excluded_calls, 1);
    *user_data = (void *)1;
}

static void
post_excluded_cuda(void *wrapcxt, void *user_data)
{
    byte *base = dr_get_dr_segment_base(tls_seg);
    ptr_uint_t *depth = (ptr_uint_t *)(base + TLS_EXCLUDE_DEPTH);
    if (user_data != NULL && *depth > 0)
        --*depth;
}

static bool
exclude_cuda_symbol(const char *name, size_t offset, void *data)
{
    const module_data_t *mod = (const module_data_t *)data;
    const char *n = name;
    app_pc address;
    if (n && strncmp(n, "__cuda", 6) == 0)
        n += 2;
    if (!n || n[0] != 'c' || n[1] != 'u' ||
        !((n[2] >= 'A' && n[2] <= 'Z') || strncmp(n, "cuda", 4) == 0 ||
          strncmp(n, "cublas", 6) == 0 || strncmp(n, "cudnn", 5) == 0 ||
          strncmp(n, "cusolver", 8) == 0 || strncmp(n, "cusparse", 8) == 0 ||
          strncmp(n, "cufft", 5) == 0 || strncmp(n, "curand", 6) == 0 ||
          strncmp(n, "cutensor", 8) == 0))
        return true;
    address = (app_pc)dr_get_proc_address(mod->handle, name);
    if (address == NULL || drwrap_is_wrapped(address, pre_excluded_cuda, post_excluded_cuda))
        return true;
    if (!drwrap_wrap(address, pre_excluded_cuda, post_excluded_cuda)) {
        dr_fprintf(STDERR, "drperf: cannot exclude CUDA export %s\n", name);
        dr_abort();
    }
    excluded_wrappers++;
    return true;
}

static void
event_module_load(void *drcontext, const module_data_t *mod, bool loaded)
{
    const char *name = dr_module_preferred_name(mod);
    app_pc towrap;
    /* DR's preferred name comes from the SONAME and is garbage for some
     * torch libraries; the file name is reliable. */
    if (mod->full_path != NULL && mod->full_path[0] == '/') {
        const char *slash = strrchr(mod->full_path, '/');
        if (slash != NULL && slash[1] != '\0')
            name = slash + 1;
    }
    dr_mutex_lock(slots_lock);
    if (nmodules < MAX_MODULES && hashtable_lookup(&mod_table, mod->start) == NULL) {
        module_t *m = &modules[nmodules];
        safe_strcpy(m->name, name != NULL ? name : "?", RNAME_MAX);
        safe_strcpy(m->path, mod->full_path != NULL ? mod->full_path : "", sizeof(m->path));
        m->start = mod->start;
        m->end = mod->end;
        hashtable_add(&mod_table, mod->start, (void *)(ptr_int_t)(nmodules + 1));
        nmodules++;
    }
    dr_mutex_unlock(slots_lock);
    if (opt_exclude_cuda_module[0] && name && strcmp(name, opt_exclude_cuda_module) == 0) {
        /* DR 11.3's ELF export iterator misses symbols in some GNU-hash
         * libraries. Enumerate on-disk symbols, then resolve exported APIs. */
        if (drsym_enumerate_symbols(mod->full_path, exclude_cuda_symbol, (void *)mod,
                                    DRSYM_DEFAULT_FLAGS) != DRSYM_SUCCESS) {
            dr_fprintf(STDERR, "drperf: cannot enumerate CUDA module %s\n", name);
            dr_abort();
        }
    }
    /* Only walk the export table of modules that can carry the markers:
     * libperfmark.so itself or the main executable (static linking).
     * Walking every module's dynamic section crashes DR on some torch libs. */
    if (!(name != NULL && strstr(name, "perfmark") != NULL) && mod->start != main_module_start)
        return;
    towrap = (app_pc)dr_get_proc_address(mod->handle, "perfmark_begin");
    if (towrap != NULL) {
        bool ok = drwrap_wrap(towrap, pre_begin, NULL);
        if (opt_verbose)
            dr_fprintf(STDERR, "drperf: wrapping perfmark_begin in %s: %d\n", name, ok);
    }
    towrap = (app_pc)dr_get_proc_address(mod->handle, "perfmark_end");
    if (towrap != NULL)
        drwrap_wrap(towrap, pre_end, NULL);
    towrap = (app_pc)dr_get_proc_address(mod->handle, "perfmark_state");
    if (towrap != NULL)
        drwrap_wrap(towrap, pre_state, NULL);
    towrap = (app_pc)dr_get_proc_address(mod->handle, "perfmark_begin_v");
    if (towrap != NULL)
        drwrap_wrap(towrap, pre_begin_v, NULL);
}

static int
module_index_for_pc(app_pc pc)
{
    module_data_t *mod = dr_lookup_module(pc);
    void *v;
    if (mod == NULL)
        return -1;
    v = hashtable_lookup(&mod_table, mod->start);
    dr_free_module_data(mod);
    return v == NULL ? -1 : (int)(ptr_int_t)v - 1;
}

/* ------------------------------------------------------- threads/syscalls */

static void
event_thread_init(void *drcontext)
{
    thread_t *t = dr_raw_mem_alloc(sizeof(*t), DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    byte *base = dr_get_dr_segment_base(tls_seg);
    DR_ASSERT_MSG(t != NULL, "drperf: cannot allocate thread struct");
    memset(t, 0, sizeof(*t));
    t->total_ptr = (volatile uint64 *)(base + TLS_TOTAL);
    *t->total_ptr = 0;
    *(ptr_uint_t *)(base + TLS_EXCLUDE_DEPTH) = 0;
    *(uint64 *)(base + TLS_EXCLUDE_COUNT) = 0;
    t->tid = dr_get_thread_id(drcontext);
    t->alive = true;
    hashtable_init_ex(&t->key_cache, 6, HASH_STRING, true, false, NULL, NULL, NULL);
    drmgr_set_tls_field(drcontext, tls_idx, t);
    dr_rwlock_write_lock(threads_rw);
    t->index = nthreads_seen < MAX_THREADS ? nthreads_seen : MAX_THREADS - 1;
    nthreads_seen++;
    t->next = threads;
    threads = t;
    dr_rwlock_write_unlock(threads_rw);
    set_thread_cur(t, slots_for(opt_follow_threads ? shared_key : NULL, t));
}

static void
event_thread_exit(void *drcontext)
{
    thread_t *t = cur_thread(drcontext);
    uint64 total = *t->total_ptr;
    int64 seq_end = dr_atomic_add64_return_sum(&seq_counter, 1);
    uint64 t_end = rdtsc();
    while (t->depth > 0)
        close_frame(t, total, seq_end, t_end, true);
    dr_rwlock_write_lock(threads_rw);
    t->final_total = total;
    t->excluded_total = *(uint64 *)((byte *)t->total_ptr + 3 * sizeof(void *));
    t->alive = false;
    dr_rwlock_write_unlock(threads_rw);
    if (leader == t)
        update_shared(NULL);
}

static bool
event_filter_syscall(void *drcontext, int sysnum)
{
    return true;
}

static bool
event_pre_syscall(void *drcontext, int sysnum)
{
    thread_t *t = cur_thread(drcontext);
    byte *base = dr_get_dr_segment_base(tls_seg);
    if (opt_exclude_cuda_module[0] && *(ptr_uint_t *)(base + TLS_EXCLUDE_DEPTH))
        return true;
    t->sys++;
    return true;
}

/* ------------------------------------------------------- instrumentation */

static dr_emit_flags_t
event_app2app(void *drcontext, void *tag, instrlist_t *bb, bool for_trace, bool translating)
{
    thread_t *t = cur_thread(drcontext);
    bool expanded = false;
    if (opt_rep_expand) {
        instr_t *stringop;
        if (!drutil_expand_rep_string_ex(drcontext, bb, &expanded, &stringop))
            DR_ASSERT(false);
    }
    t->bb_expanded = expanded;
    return DR_EMIT_DEFAULT;
}

static dr_emit_flags_t
event_analysis(void *drcontext, void *tag, instrlist_t *bb, bool for_trace, bool translating,
               void **user_data)
{
    thread_t *t = cur_thread(drcontext);
    app_pc pc = dr_fragment_app_pc(tag);
    uint64 n = t->bb_expanded ? 1 : (uint64)drx_instrlist_app_size(bb);
    uint64 slot;
    void *v;
    dr_mutex_lock(slots_lock);
    v = hashtable_lookup(&slot_table, pc);
    if (v != NULL) {
        slot = (uint64)(ptr_uint_t)v - 1;
    } else {
        if (next_slot >= opt_max_slots) {
            slots_overflow++;
            slot = opt_max_slots - 1;
        } else {
            slot = next_slot++;
            slot_pc[slot] = pc;
            slot_mod[slot] = module_index_for_pc(pc);
            slot_sym[slot] = -1;
            hashtable_add(&slot_table, pc, (void *)(ptr_uint_t)(slot + 1));
        }
    }
    dr_mutex_unlock(slots_lock);
    *user_data = (void *)(ptr_uint_t)((slot << 32) | (n & 0xffffffffu));
    return DR_EMIT_DEFAULT;
}

static dr_emit_flags_t
event_insert(void *drcontext, void *tag, instrlist_t *bb, instr_t *inst, bool for_trace,
             bool translating, void *user_data)
{
    uint64 packed = (uint64)(ptr_uint_t)user_data;
    uint64 slot = packed >> 32;
    uint n = (uint)(packed & 0xffffffffu);
    reg_id_t reg;
    instr_t *excluded = NULL, *done = NULL;
    drmgr_disable_auto_predication(drcontext, bb);
    if (!drmgr_is_first_instr(drcontext, inst))
        return DR_EMIT_DEFAULT;
    if (n == 0)
        return DR_EMIT_DEFAULT;
    if (drreg_reserve_aflags(drcontext, bb, inst) != DRREG_SUCCESS ||
        drreg_reserve_register(drcontext, bb, inst, NULL, &reg) != DRREG_SUCCESS)
        DR_ASSERT(false);
    if (opt_exclude_cuda_module[0]) {
        int mod = slot_mod[slot];
        excluded = INSTR_CREATE_label(drcontext);
        done = INSTR_CREATE_label(drcontext);
        /* Also suppress module entry/exit blocks around drwrap callbacks and
         * module-private helpers. Export wrappers extend exclusion into callees. */
        if (mod >= 0 && strcmp(modules[mod].name, opt_exclude_cuda_module) == 0) {
            instrlist_meta_preinsert(bb, inst, INSTR_CREATE_jmp(drcontext, opnd_create_instr(excluded)));
        } else {
            instrlist_meta_preinsert(bb, inst, INSTR_CREATE_cmp(drcontext,
                dr_raw_tls_opnd(drcontext, tls_seg, TLS_EXCLUDE_DEPTH), OPND_CREATE_INT8(0)));
            instrlist_meta_preinsert(bb, inst, INSTR_CREATE_jcc(drcontext, OP_jnz, opnd_create_instr(excluded)));
        }
    }
    instrlist_meta_preinsert(
        bb, inst,
        INSTR_CREATE_add(drcontext, dr_raw_tls_opnd(drcontext, tls_seg, TLS_TOTAL),
                         OPND_CREATE_INT32(n)));
    if (opt_block_counters) {
        dr_insert_read_raw_tls(drcontext, bb, inst, tls_seg, TLS_CUR, reg);
        instrlist_meta_preinsert(
            bb, inst,
            INSTR_CREATE_add(drcontext, OPND_CREATE_MEM64(reg, (int)(slot * sizeof(uint64))),
                             OPND_CREATE_INT32(n)));
    }
    if (excluded != NULL) {
        instrlist_meta_preinsert(bb, inst, INSTR_CREATE_jmp(drcontext, opnd_create_instr(done)));
        instrlist_meta_preinsert(bb, inst, excluded);
        instrlist_meta_preinsert(bb, inst, INSTR_CREATE_add(drcontext,
            dr_raw_tls_opnd(drcontext, tls_seg, TLS_EXCLUDE_COUNT), OPND_CREATE_INT32(n)));
        instrlist_meta_preinsert(bb, inst, done);
    }
    if (drreg_unreserve_register(drcontext, bb, inst, reg) != DRREG_SUCCESS ||
        drreg_unreserve_aflags(drcontext, bb, inst) != DRREG_SUCCESS)
        DR_ASSERT(false);
    return DR_EMIT_DEFAULT;
}

/* --------------------------------------------------------- symbolization */

typedef struct {
    size_t offs;
    char *name;
} msym_t;

typedef struct {
    msym_t *syms;
    int n, cap;
    bool done;
} modsyms_t;

static modsyms_t modsyms[MAX_MODULES];

static bool
enum_cb(drsym_info_t *info, drsym_error_t status, void *data)
{
    modsyms_t *ms = (modsyms_t *)data;
    size_t len;
    if ((status != DRSYM_SUCCESS && status != DRSYM_ERROR_LINE_NOT_AVAILABLE) ||
        info->name == NULL || info->name[0] == '\0')
        return true;
    if (ms->n == ms->cap) {
        int ncap = ms->cap == 0 ? 4096 : ms->cap * 2;
        msym_t *ns = dr_global_alloc(ncap * sizeof(msym_t));
        if (ms->syms != NULL) {
            memcpy(ns, ms->syms, ms->n * sizeof(msym_t));
            dr_global_free(ms->syms, ms->cap * sizeof(msym_t));
        }
        ms->syms = ns;
        ms->cap = ncap;
    }
    len = strlen(info->name);
    if (len >= SYM_MAX)
        len = SYM_MAX - 1;
    ms->syms[ms->n].offs = info->start_offs;
    ms->syms[ms->n].name = dr_global_alloc(len + 1);
    memcpy(ms->syms[ms->n].name, info->name, len);
    ms->syms[ms->n].name[len] = '\0';
    ms->n++;
    return true;
}

static int
msym_cmp(const void *a, const void *b)
{
    size_t oa = ((const msym_t *)a)->offs, ob = ((const msym_t *)b)->offs;
    return oa < ob ? -1 : (oa > ob ? 1 : 0);
}

static const msym_t *
nearest_symbol(int mod, size_t offs)
{
    modsyms_t *ms = &modsyms[mod];
    int lo, hi;
    if (!ms->done) {
        ms->done = true;
        drsym_enumerate_symbols_ex(modules[mod].path, enum_cb, sizeof(drsym_info_t), ms,
                                   DRSYM_DEFAULT_FLAGS);
        if (ms->n > 1)
            qsort(ms->syms, ms->n, sizeof(msym_t), msym_cmp);
    }
    if (ms->n == 0 || ms->syms[0].offs > offs)
        return NULL;
    lo = 0;
    hi = ms->n - 1;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        if (ms->syms[mid].offs <= offs)
            lo = mid;
        else
            hi = mid - 1;
    }
    return &ms->syms[lo];
}

static void
free_modsyms(void)
{
    int i, j;
    for (i = 0; i < MAX_MODULES; i++) {
        modsyms_t *ms = &modsyms[i];
        for (j = 0; j < ms->n; j++)
            dr_global_free(ms->syms[j].name, strlen(ms->syms[j].name) + 1);
        if (ms->syms != NULL)
            dr_global_free(ms->syms, ms->cap * sizeof(msym_t));
    }
}

static int
sym_index_for_slot(uint64 slot)
{
    int mod = slot_mod[slot];
    char kbuf[64];
    sym_t s;
    void *v;
    size_t offs;
    if (slot_sym[slot] >= 0)
        return slot_sym[slot];
    memset(&s, 0, sizeof(s));
    s.mod = mod;
    if (mod < 0) {
        safe_strcpy(s.name, "<no module>", SYM_MAX);
    } else if (!opt_symbols) {
        safe_strcpy(s.name, "<symbols off>", SYM_MAX);
    } else {
        drsym_info_t info;
        drsym_error_t err;
        char name[SYM_MAX];
        offs = (size_t)(slot_pc[slot] - modules[mod].start);
        memset(&info, 0, sizeof(info));
        info.struct_size = sizeof(info);
        info.name = name;
        info.name_size = sizeof(name);
        err = drsym_lookup_address(modules[mod].path, offs, &info, DRSYM_DEFAULT_FLAGS);
        if ((err == DRSYM_SUCCESS || err == DRSYM_ERROR_LINE_NOT_AVAILABLE) && name[0] != '\0') {
            s.start_offs = info.start_offs;
            if (info.end_offs > info.start_offs && offs >= info.end_offs) {
                dr_snprintf(s.name, SYM_MAX, "%s+?", name);
                s.name[SYM_MAX - 1] = '\0';
            } else {
                safe_strcpy(s.name, name, SYM_MAX);
            }
        } else {
            const msym_t *near = nearest_symbol(mod, offs);
            if (near != NULL) {
                s.start_offs = near->offs;
                dr_snprintf(s.name, SYM_MAX, "%s+?", near->name);
                s.name[SYM_MAX - 1] = '\0';
            } else {
                safe_strcpy(s.name, "<no symbol>", SYM_MAX);
            }
        }
    }
    dr_snprintf(kbuf, sizeof(kbuf), "%d:%llx:%s", mod, (unsigned long long)s.start_offs,
                s.start_offs == 0 ? s.name : "");
    kbuf[sizeof(kbuf) - 1] = '\0';
    v = hashtable_lookup(&sym_table, kbuf);
    if (v != NULL) {
        slot_sym[slot] = (int)(ptr_int_t)v - 1;
        return slot_sym[slot];
    }
    if (nsyms == syms_cap) {
        int ncap = syms_cap == 0 ? 4096 : syms_cap * 2;
        sym_t *ns = dr_global_alloc(ncap * sizeof(sym_t));
        if (syms != NULL) {
            memcpy(ns, syms, nsyms * sizeof(sym_t));
            dr_global_free(syms, syms_cap * sizeof(sym_t));
        }
        syms = ns;
        syms_cap = ncap;
    }
    syms[nsyms] = s;
    hashtable_add(&sym_table, kbuf, (void *)(ptr_int_t)(nsyms + 1));
    slot_sym[slot] = nsyms;
    return nsyms++;
}

/* ------------------------------------------------------------- output */

static void
json_str(file_t f, const char *s)
{
    dr_fprintf(f, "\"");
    for (; *s != '\0'; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\')
            dr_fprintf(f, "\\%c", c);
        else if (c < 0x20)
            dr_fprintf(f, "\\u%04x", c);
        else
            dr_fprintf(f, "%c", c);
    }
    dr_fprintf(f, "\"");
}

typedef struct {
    int idx;
    uint64 count;
} pair_t;

static void
topn_insert(pair_t *top, int *ntop, int cap, int idx, uint64 count)
{
    int i, j;
    if (*ntop == cap && count <= top[cap - 1].count)
        return;
    i = *ntop < cap ? (*ntop)++ : cap - 1;
    for (j = i; j > 0 && top[j - 1].count < count; j--)
        top[j] = top[j - 1];
    top[j].idx = idx;
    top[j].count = count;
}

static void
merge_stats(rkey_t *k, kstats_t *out)
{
    thread_t *t;
    memset(out, 0, sizeof(*out));
    out->incl_min = out->self_min = ~(uint64)0;
    for (t = threads; t != NULL; t = t->next) {
        kstats_t *s = t->stats == NULL ? NULL : &t->stats[k->index];
        if (s == NULL || s->count == 0)
            continue;
        out->count += s->count;
        out->incl_sum += s->incl_sum;
        out->self_sum += s->self_sum;
        out->sys_sum += s->sys_sum;
        out->implicit_ends += s->implicit_ends;
        if (s->incl_min < out->incl_min)
            out->incl_min = s->incl_min;
        if (s->incl_max > out->incl_max)
            out->incl_max = s->incl_max;
        if (s->self_min < out->self_min)
            out->self_min = s->self_min;
        if (s->self_max > out->self_max)
            out->self_max = s->self_max;
    }
    if (out->count == 0)
        out->incl_min = out->self_min = 0;
}

static void
write_key(file_t f, rkey_t *k, bool first)
{
    uint64 *mod_sum = dr_global_alloc((nmodules + 1) * sizeof(uint64));
    uint64 *sym_sum = dr_raw_mem_alloc((next_slot + 1) * sizeof(uint64),
                                       DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    pair_t *top = dr_global_alloc(opt_top * sizeof(pair_t));
    kstats_t st;
    int ntop = 0, i, nmods_used = 0, ti, threads_active = 0;
    uint64 slot, slot_total = 0;
    uint64 *vec = NULL;
    merge_stats(k, &st);
    memset(mod_sum, 0, (nmodules + 1) * sizeof(uint64));
    if (opt_blocks)
        vec = dr_raw_mem_alloc((next_slot + 1) * sizeof(uint64), DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    for (ti = 0; ti < MAX_THREADS; ti++) {
        uint64 *arr = k->tslots[ti];
        bool active = false;
        if (arr == NULL)
            continue;
        for (slot = 0; slot < next_slot; slot++) {
            uint64 c = arr[slot];
            int mi, si;
            if (c == 0)
                continue;
            active = true;
            slot_total += c;
            mi = slot_mod[slot];
            mod_sum[mi < 0 ? nmodules : mi] += c;
            si = sym_index_for_slot(slot);
            sym_sum[si] += c;
            if (vec != NULL)
                vec[slot] += c;
        }
        if (active)
            threads_active++;
    }
    if (vec != NULL && blocks_file != INVALID_FILE) {
        /* one record per key: "K index region state_name state_value root count" then "slot instrs" pairs */
        /* "K index region nk name1 value1 ... root count" */
        dr_fprintf(blocks_file, "K %d ", k->index);
        json_str(blocks_file, k->region);
        dr_fprintf(blocks_file, " %d", k->overflow ? -1 : k->nkstates);
        for (i = 0; i < k->nkstates; i++) {
            dr_fprintf(blocks_file, " ");
            json_str(blocks_file, k->kname[i]);
            dr_fprintf(blocks_file, " %lld", (long long)k->kval[i]);
        }
        dr_fprintf(blocks_file, " ");
        json_str(blocks_file, k->root);
        dr_fprintf(blocks_file, " %llu\n", (unsigned long long)st.count);
        for (slot = 0; slot < next_slot; slot++) {
            if (vec[slot] != 0) {
                dr_fprintf(blocks_file, "%llu %llu\n", (unsigned long long)slot, (unsigned long long)vec[slot]);
                slot_used[slot] = 1;
            }
        }
        dr_raw_mem_free(vec, (next_slot + 1) * sizeof(uint64));
    }
    for (i = 0; i < nsyms; i++) {
        if (sym_sum[i] != 0)
            topn_insert(top, &ntop, opt_top, i, sym_sum[i]);
    }
    dr_fprintf(f, "%s    {\"region\": ", first ? "" : ",\n");
    json_str(f, k->region);
    dr_fprintf(f, ", \"state_name\": ");
    json_str(f, k->state_name);
    dr_fprintf(f, ", \"state_value\": %lld, \"states\": {", (long long)k->state_value);
    for (i = 0; i < k->nkstates; i++) {
        dr_fprintf(f, "%s", i ? ", " : "");
        json_str(f, k->kname[i]);
        dr_fprintf(f, ": %lld", (long long)k->kval[i]);
    }
    dr_fprintf(f, "}, \"parent\": ");
    json_str(f, k->parent);
    dr_fprintf(f, ", \"root\": ");
    json_str(f, k->root);
    dr_fprintf(f, ",\n     \"count\": %llu, \"incl\": {\"sum\": %llu, \"min\": %llu, \"max\": %llu},"
               " \"self\": %llu, \"self_min\": %llu, \"self_max\": %llu,",
               (unsigned long long)st.count, (unsigned long long)st.incl_sum,
               (unsigned long long)st.incl_min, (unsigned long long)st.incl_max,
               (unsigned long long)st.self_sum, (unsigned long long)st.self_min,
               (unsigned long long)st.self_max);
    dr_fprintf(f, "\n     \"self_slots\": %llu, \"other_threads\": %llu, \"threads_active\": %d, "
               "\"syscalls\": %llu, \"implicit_ends\": %llu,\n",
               (unsigned long long)slot_total,
               (unsigned long long)(slot_total > st.self_sum ? slot_total - st.self_sum : 0),
               threads_active, (unsigned long long)st.sys_sum, (unsigned long long)st.implicit_ends);
    dr_fprintf(f, "     \"modules\": {");
    for (i = 0; i <= nmodules; i++) {
        if (mod_sum[i] == 0)
            continue;
        dr_fprintf(f, "%s", nmods_used++ ? ", " : "");
        json_str(f, i == nmodules ? "<no module>" : modules[i].name);
        dr_fprintf(f, ": %llu", (unsigned long long)mod_sum[i]);
    }
    dr_fprintf(f, "},\n     \"symbols\": [");
    for (i = 0; i < ntop; i++) {
        sym_t *s = &syms[top[i].idx];
        dr_fprintf(f, "%s\n      {\"module\": ", i ? "," : "");
        json_str(f, s->mod < 0 ? "<no module>" : modules[s->mod].name);
        dr_fprintf(f, ", \"symbol\": ");
        json_str(f, s->name);
        dr_fprintf(f, ", \"instrs\": %llu}", (unsigned long long)top[i].count);
    }
    dr_fprintf(f, "%s]}", ntop ? "\n     " : "");
    dr_global_free(top, opt_top * sizeof(pair_t));
    dr_raw_mem_free(sym_sum, (next_slot + 1) * sizeof(uint64));
    dr_global_free(mod_sum, (nmodules + 1) * sizeof(uint64));
}

static void
write_trace(const char *path)
{
    file_t f = dr_open_file(path, DR_FILE_WRITE_OVERWRITE);
    thread_t *t;
    trace_chunk_t *c;
    int i, j;
    uint64 tsc1 = rdtsc(), us1 = dr_get_microseconds();
    double us_per_tick = tsc1 > tsc0 ? (double)(us1 - us0) / (double)(tsc1 - tsc0) : 0.0;
    if (f == INVALID_FILE) {
        dr_fprintf(STDERR, "drperf: cannot open trace file %s\n", path);
        return;
    }
    for (t = threads; t != NULL; t = t->next) {
        for (c = t->trace_head; c != NULL; c = c->next) {
            for (i = 0; i < c->n; i++) {
                trace_rec_t *r = &c->recs[i];
                dr_fprintf(f, "{\"seq\": %lld, \"seq_end\": %lld, \"tid\": %d, \"region\": ",
                           (long long)r->seq_begin, (long long)r->seq_end, (int)t->tid);
                json_str(f, r->key->region);
                dr_fprintf(f, ", \"root\": ");
                json_str(f, r->key->root);
                dr_fprintf(f, ", \"nk\": %d, \"state\": {", r->key->nkstates);
                for (j = 0; j < r->key->nkstates; j++) {
                    dr_fprintf(f, "%s", j ? ", " : "");
                    json_str(f, r->key->kname[j]);
                    dr_fprintf(f, ": %lld", (long long)r->key->kval[j]);
                }
                for (j = 0; j < r->nstates; j++) {
                    dr_fprintf(f, "%s", (j > 0 || r->key->nkstates > 0) ? ", " : "");
                    json_str(f, r->states[j].name);
                    dr_fprintf(f, ": ");
                    json_str(f, r->states[j].value);
                }
                dr_fprintf(f, "}, \"incl\": %llu, \"self\": %llu, \"syscalls\": %llu, "
                           "\"clock\": %llu, \"t_begin_us\": %.1f, \"t_end_us\": %.1f%s}\n",
                           (unsigned long long)r->incl, (unsigned long long)r->self,
                           (unsigned long long)r->sys, (unsigned long long)r->clock_begin,
                           (double)us0 + (r->t_begin_us - tsc0) * us_per_tick,
                           (double)us0 + (r->t_end_us - tsc0) * us_per_tick,
                           r->implicit ? ", \"implicit\": true" : "");
            }
        }
    }
    dr_close_file(f);
}

static void
event_exit(void)
{
    file_t f = dr_open_file(opt_out, DR_FILE_WRITE_OVERWRITE);
    char trace_path[560];
    rkey_t *k;
    thread_t *t, *tn;
    uint64 total = 0;
    uint64 excluded_total = 0;
    int i, n = 0, ti;
    if (f == INVALID_FILE) {
        dr_fprintf(STDERR, "drperf: cannot open output file %s\n", opt_out);
        return;
    }
    dr_snprintf(trace_path, sizeof(trace_path), "%s.trace", opt_out);
    trace_path[sizeof(trace_path) - 1] = '\0';
    if (opt_trace > 0)
        write_trace(trace_path);
    dr_fprintf(f, "{\n  \"drperf\": {\"version\": \"%s\", \"pid\": %d, \"app\": ", DRPERF_VERSION,
               dr_get_process_id());
    json_str(f, dr_get_application_name());
    for (t = threads; t != NULL; t = t->next)
        excluded_total += t->alive ? *(uint64 *)((byte *)t->total_ptr + 3 * sizeof(void *)) : t->excluded_total;
    dr_fprintf(f, ",\n    \"excluded_cuda_module\": ");
    json_str(f, opt_exclude_cuda_module);
    dr_fprintf(f, ", \"follow_unmarked_threads\": %s", opt_follow_threads ? "true" : "false");
    dr_fprintf(f, ", \"excluded_cuda_exports\": %d, \"excluded_cuda_calls\": %lld, \"excluded_instructions\": %llu",
               excluded_wrappers, (long long)excluded_calls, (unsigned long long)excluded_total);
    dr_fprintf(f, ",\n    \"rep_expand\": %s, \"symbols\": %s, \"max_slots\": %llu, "
               "\"slots_used\": %llu, \"slots_overflow\": %llu, \"counter_denied\": %lld,\n",
               opt_rep_expand ? "true" : "false", opt_symbols ? "true" : "false",
               (unsigned long long)opt_max_slots, (unsigned long long)next_slot,
               (unsigned long long)slots_overflow, (long long)counter_denied);
    dr_fprintf(f, "    \"marker_seen\": %s, \"unmatched_ends\": %lld, \"depth_overflows\": %lld, "
               "\"state_overflows\": %lld, \"threads\": %d,\n",
               marker_seen ? "true" : "false", (long long)unmatched_ends, (long long)depth_overflows,
               (long long)state_overflows, nthreads_seen);
    dr_fprintf(f, "    \"trace_file\": ");
    json_str(f, opt_trace > 0 ? trace_path : "");
    dr_fprintf(f, ", \"trace_records\": %lld, \"trace_dropped\": %lld},\n",
               (long long)(opt_trace > 0 ? (trace_records > opt_trace ? opt_trace : trace_records) : 0),
               (long long)trace_dropped);
    dr_fprintf(f, "  \"modules\": [");
    for (i = 0; i < nmodules; i++) {
        dr_fprintf(f, "%s\n    {\"name\": ", i ? "," : "");
        json_str(f, modules[i].name);
        dr_fprintf(f, ", \"path\": ");
        json_str(f, modules[i].path);
        dr_fprintf(f, "}");
    }
    dr_fprintf(f, "\n  ],\n  \"threads\": [");
    for (t = threads; t != NULL; t = t->next) {
        uint64 tt = t->alive ? *t->total_ptr : t->final_total;
        total += tt;
        dr_fprintf(f, "%s\n    {\"tid\": %d, \"instrs\": %llu, \"open_regions\": %d}", n++ ? "," : "",
                   (int)t->tid, (unsigned long long)tt, t->depth);
    }
    dr_fprintf(f, "\n  ],\n  \"total_instrs\": %llu,\n  \"regions\": [\n", (unsigned long long)total);
    if (opt_blocks) {
        char bpath[560];
        dr_snprintf(bpath, sizeof(bpath), "%s.blocks", opt_out);
        bpath[sizeof(bpath) - 1] = '\0';
        blocks_file = dr_open_file(bpath, DR_FILE_WRITE_OVERWRITE);
        slot_used = dr_raw_mem_alloc(next_slot + 1, DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    }
    for (k = keys, i = 0; k != NULL; k = k->next, i++)
        write_key(f, k, i == 0);
    dr_fprintf(f, "\n  ]\n}\n");
    dr_close_file(f);
    if (opt_blocks && blocks_file != INVALID_FILE) {
        /* the block table: "slot module symbol" for every referenced block */
        char spath[560];
        file_t sf;
        uint64 slot;
        dr_close_file(blocks_file);
        dr_snprintf(spath, sizeof(spath), "%s.slots", opt_out);
        spath[sizeof(spath) - 1] = '\0';
        sf = dr_open_file(spath, DR_FILE_WRITE_OVERWRITE);
        if (sf != INVALID_FILE) {
            for (slot = 0; slot < next_slot; slot++) {
                sym_t *sy;
                if (!slot_used[slot])
                    continue;
                sy = &syms[sym_index_for_slot(slot)];
                /* "slot module offset symbol": module+offset identifies the block across processes */
                dr_fprintf(sf, "%llu ", (unsigned long long)slot);
                json_str(sf, sy->mod < 0 ? "<no module>" : modules[sy->mod].name);
                dr_fprintf(sf, " %llu ", (unsigned long long)(slot_mod[slot] < 0 ? (ptr_uint_t)slot_pc[slot] : (ptr_uint_t)(slot_pc[slot] - modules[slot_mod[slot]].start)));
                json_str(sf, sy->name);
                dr_fprintf(sf, "\n");
            }
            dr_close_file(sf);
        }
        dr_raw_mem_free(slot_used, next_slot + 1);
    }
    if (opt_verbose)
        dr_fprintf(STDERR, "drperf: %d regions, %llu slots, %llu total instrs -> %s\n", nkeys,
                   (unsigned long long)next_slot, (unsigned long long)total, opt_out);
    for (k = keys; k != NULL;) {
        rkey_t *kn = k->next;
        for (ti = 0; ti < MAX_THREADS; ti++) {
            if (k->tslots[ti] != NULL)
                dr_raw_mem_free(k->tslots[ti], opt_max_slots * sizeof(uint64));
        }
        dr_global_free(k->tslots, MAX_THREADS * sizeof(uint64 *));
        if (k->nkstates > 0) {
            dr_global_free(k->kname, (size_t)k->nkstates * sizeof(*k->kname));
            dr_global_free(k->kval, (size_t)k->nkstates * sizeof(*k->kval));
        }
        dr_global_free(k, sizeof(*k));
        k = kn;
    }
    for (t = threads; t != NULL; t = tn) {
        trace_chunk_t *c, *cn;
        tn = t->next;
        for (c = t->trace_head; c != NULL; c = cn) {
            cn = c->next;
            dr_global_free(c, sizeof(*c));
        }
        hashtable_delete(&t->key_cache);
        if (t->stats != NULL)
            dr_raw_mem_free(t->stats, MAX_KEYS * sizeof(kstats_t));
        dr_raw_mem_free(t, sizeof(*t));
    }
    if (syms != NULL)
        dr_global_free(syms, syms_cap * sizeof(sym_t));
    free_modsyms();
    hashtable_delete(&slot_table);
    hashtable_delete(&key_table);
    hashtable_delete(&mod_table);
    hashtable_delete(&sym_table);
    dr_raw_mem_free(slot_pc, opt_max_slots * sizeof(app_pc));
    dr_raw_mem_free(slot_mod, opt_max_slots * sizeof(int));
    dr_raw_mem_free(slot_sym, opt_max_slots * sizeof(int));
    dr_raw_mem_free(dummy_slots, opt_max_slots * sizeof(uint64));
    dr_raw_tls_cfree(tls_offs, 4);
    drmgr_unregister_tls_field(tls_idx);
    dr_mutex_destroy(keys_lock);
    dr_mutex_destroy(leader_lock);
    dr_mutex_destroy(slots_lock);
    dr_rwlock_destroy(threads_rw);
    drsym_exit();
    drx_exit();
    drutil_exit();
    drwrap_exit();
    drreg_exit();
    drmgr_exit();
}

/* --------------------------------------------------------------- init */

static void
parse_options(int argc, const char *argv[])
{
    int i, v;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            char *pp;
            safe_strcpy(opt_out, argv[++i], sizeof(opt_out));
            pp = strstr(opt_out, "%p");
            if (pp != NULL) { /* per-process output: %p -> pid */
                char tail[512];
                safe_strcpy(tail, pp + 2, sizeof(tail));
                dr_snprintf(pp, sizeof(opt_out) - (pp - opt_out), "%d%s", dr_get_process_id(), tail);
                opt_out[sizeof(opt_out) - 1] = '\0';
            }
        } else if (strcmp(argv[i], "-top") == 0 && i + 1 < argc) {
            if (dr_sscanf(argv[++i], "%d", &opt_top) != 1 || opt_top < 1)
                opt_top = 1;
        } else if (strcmp(argv[i], "-max_slots") == 0 && i + 1 < argc) {
            if (dr_sscanf(argv[++i], "%d", &v) != 1 || v < 1024)
                v = 1024;
            opt_max_slots = (uint64)v;
        } else if (strcmp(argv[i], "-trace") == 0 && i + 1 < argc) {
            if (dr_sscanf(argv[++i], "%d", &v) != 1 || v < 0)
                v = 0;
            opt_trace = v;

        } else if (strcmp(argv[i], "-blocks") == 0) {
            opt_blocks = true;
        } else if (strcmp(argv[i], "-no_rep_expand") == 0) {
            opt_rep_expand = false;
        } else if (strcmp(argv[i], "-no_block_counters") == 0) {
            opt_block_counters = false;
        } else if (strcmp(argv[i], "-no_symbols") == 0) {
            opt_symbols = false;
        } else if (strcmp(argv[i], "-exclude_cuda_module") == 0 && i + 1 < argc) {
            safe_strcpy(opt_exclude_cuda_module, argv[++i], sizeof(opt_exclude_cuda_module));
        } else if (strcmp(argv[i], "-no_follow_threads") == 0) {
            opt_follow_threads = false;
        } else if (strcmp(argv[i], "-verbose") == 0) {
            opt_verbose = true;
        } else {
            dr_fprintf(STDERR, "drperf: unknown option %s\n", argv[i]);
            dr_abort();
        }
    }
}

DR_EXPORT void
dr_client_main(client_id_t id, int argc, const char *argv[])
{
    drreg_options_t ops = { sizeof(ops), 3, false };
    module_data_t *main_mod;
    dr_set_client_name("drperf", "https://github.com/DynamoRIO/dynamorio/issues");
    parse_options(argc, argv);
    if (!drmgr_init() || drreg_init(&ops) != DRREG_SUCCESS || !drwrap_init() || !drutil_init() ||
        !drx_init())
        DR_ASSERT(false);
    if ((opt_symbols || opt_exclude_cuda_module[0]) && drsym_init(0) != DRSYM_SUCCESS) {
        if (opt_exclude_cuda_module[0]) {
            dr_fprintf(STDERR, "drperf: drsym_init failed; requested CUDA exclusion unavailable\n");
            dr_abort();
        }
        dr_fprintf(STDERR, "drperf: drsym_init failed; symbols disabled\n");
        opt_symbols = false;
    }
    drwrap_set_global_flags(DRWRAP_NO_FRILLS | DRWRAP_FAST_CLEANCALLS);
    keys_lock = dr_mutex_create();
    leader_lock = dr_mutex_create();
    slots_lock = dr_mutex_create();
    threads_rw = dr_rwlock_create();
    hashtable_init_ex(&slot_table, 20, HASH_INTPTR, false, false, NULL, NULL, NULL);
    hashtable_init_ex(&key_table, 8, HASH_STRING, true, false, NULL, NULL, NULL);
    hashtable_init_ex(&mod_table, 10, HASH_INTPTR, false, false, NULL, NULL, NULL);
    hashtable_init_ex(&sym_table, 16, HASH_STRING, true, false, NULL, NULL, NULL);
    slot_pc = dr_raw_mem_alloc(opt_max_slots * sizeof(app_pc), DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    slot_mod = dr_raw_mem_alloc(opt_max_slots * sizeof(int), DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    slot_sym = dr_raw_mem_alloc(opt_max_slots * sizeof(int), DR_MEMPROT_READ | DR_MEMPROT_WRITE, NULL);
    dummy_slots = dr_raw_mem_alloc(opt_max_slots * sizeof(uint64), DR_MEMPROT_READ | DR_MEMPROT_WRITE,
                                   NULL);
    DR_ASSERT_MSG(slot_pc != NULL && slot_mod != NULL && slot_sym != NULL && dummy_slots != NULL,
                  "drperf: allocation failed");
    tls_idx = drmgr_register_tls_field();
    if (!dr_raw_tls_calloc(&tls_seg, &tls_offs, 4, 0))
        DR_ASSERT(false);
    tsc0 = rdtsc();
    us0 = dr_get_microseconds();
    main_mod = dr_get_main_module();
    if (main_mod != NULL) {
        main_module_start = main_mod->start;
        dr_free_module_data(main_mod);
    }
    dr_register_exit_event(event_exit);
    if (!drmgr_register_thread_init_event(event_thread_init) ||
        !drmgr_register_thread_exit_event(event_thread_exit) ||
        !drmgr_register_bb_app2app_event(event_app2app, NULL) ||
        !drmgr_register_bb_instrumentation_event(event_analysis, event_insert, NULL) ||
        !drmgr_register_module_load_event(event_module_load) ||
        !drmgr_register_pre_syscall_event(event_pre_syscall))
        DR_ASSERT(false);
    dr_register_filter_syscall_event(event_filter_syscall);
    if (opt_verbose)
        dr_fprintf(STDERR, "drperf: initialized, output -> %s\n", opt_out);
}
