## Case 3. Two `bind_batch` implementations: at the scale of the drivers the old one wins, at production it loses 8x, and the cost functions say why

**The item.** Commit d94b71d rewrote `Directory::bind_batch`: the previous
version cloned the entire `DirectoryState` (every superblock with its block
map, plus the block index) to plan a batch on the copy and swap it in; the
current version mutates in place under an undo log, in two passes (discover,
roll back, allocate handles, commit). The fixes document records this as done:
"no more clone of the whole `DirectoryState` per store job".

**What was measured.** The pre-rewrite core was rebuilt from `d94b71d^` with
one marker added at the top of `bind_batch`, `ftl_directory_bind_batch(requests,
blocks, superblocks)`, and the same marker was added to the current core (branch
`cases`). `examples/cases/bind_grow.py` grows one directory a superblock per
bind: 24 binds of 4 blocks, then 24 of 16, so `blocks` and `superblocks` do not
move in step and can be separated. Both cores, same driver:

```
./run_case.sh bind_grow_old old-bind/.venv-old/bin/python   examples/cases/bind_grow.py --regions ftl_directory_bind_batch
./run_case.sh bind_grow_new vllm-ditto/.venv-perf/bin/python examples/cases/bind_grow.py --regions ftl_directory_bind_batch
```

```
old (clone the state):
  cost(requests, blocks, superblocks) = 1,898.6*requests + 329.7*blocks + 946.6*superblocks + 6,788.1   blocks: 424 affine, 1073 constant, 147 irregular (41.7% of cost)
    per-blocks coefficient by function:
                83.5  _int_free  [libc.so.6]
                  36  __free  [libc.so.6]
                  34  <hashbrown::raw::RawTable<(i64, (alloc::string::String, usize))> as co  [_ditto_ftl_core.abi3.so]
                  33  <alloc::string::String as core::clone::Clone>::clone  [_ditto_ftl_core.abi3.so]
                29.6  __GI___libc_malloc  [libc.so.6]
                22.2  <alloc::collections::btree::map::BTreeMap<_, _, _> as core::clone::Clo  [_ditto_ftl_core.abi3.so]
    per-superblocks coefficient by function:
               244.2  _int_free  [libc.so.6]
               109.1  __free  [libc.so.6]
                  99  <alloc::string::String as core::clone::Clone>::clone  [_ditto_ftl_core.abi3.so]
                87.5  __GI___libc_malloc  [libc.so.6]
                72.6  <alloc::collections::btree::map::BTreeMap<_, _, _> as core::clone::Clo  [_ditto_ftl_core.abi3.so]
    irregular by function:
            35,898.8  _int_malloc  [libc.so.6]

new (undo log):
  cost(requests, blocks, superblocks) = 4,089.8*requests + -5.4*blocks + 133.5*superblocks + 12,390.7   blocks: 413 affine, 1233 constant, 150 irregular (52.4% of cost)
    irregular blocks, per call: 13,815 .. 143,625.5
    irregular by function:
            15,606.8  __memcmp_avx2_movbe  [libc.so.6]
            14,455.3  <_ditto_ftl_core::directory::Directory>::apply_batch  [_ditto_ftl_core.abi3.so]
             7,953.9  _int_malloc  [libc.so.6]
```

The old formula is the clone: 330 per resident io-block and 947 per superblock,
attributed to `String::clone`, `BTreeMap::clone`, the hash-table clone and the
matching frees, on every bind, whatever its size. The new formula has no
per-block term, a small per-superblock term (the prune scan, case 1), and a
per-request cost more than twice the old one: the two passes plus the undo log.

**Alike at small scale.** Per-call cost from the traces of the same two runs,
requests = 4, superblocks 0..9 (`drperf-dev trace out/bind_grow_{old,new} --region ftl_directory_bind_batch`):

```
superblocks:   0       1       2       3       4       5       6       7       8       9
old         19,393  24,969  25,787  33,570  34,822  39,471  43,127  55,707  53,039  56,750
new         47,418  47,552  46,233  52,888  48,784  50,759  52,511  62,214  56,240  58,745
```

At the directory sizes of the repository's tests and annotation drivers (five
superblocks or fewer) the pre-rewrite code is cheaper. A profile of either at
that scale shows malloc, memcmp and `apply_batch`, and nothing that says one of
them grows with the directory.

**Diverging at production shape.** Same driver, 120 binds of 32 blocks
(`CASE_STEPS=60 CASE_FILL_A=32 CASE_FILL_B=32`, `out/bind_grow_{old,new}_prod`),
every eighth bind:

```
superblocks:  0        8        16       24       32       40       48       56         64         72         80         88         96         104        112
old        117,375  297,186  485,157  614,071  784,286  940,422  1,117,894  1,646,033  1,476,831  1,662,969  1,796,992  1,968,092  2,113,324  2,255,061  3,094,844
new        258,488  342,094  357,451  392,651  301,457  285,740    332,595    382,815    397,545    440,571    414,214    429,822    397,915    366,259    355,777
```

The old core's formula from the small run, evaluated at the production point
(32 requests, 3,584 blocks, 112 superblocks), gives 1,899x32 + 330x3,584 +
947x112 + 6.8k = 1.35M; the measured value is 3.09M, and `derive --predict`
says why the formula is a floor: "formula covers only 58% of this regime's
cost", the rest being the 42% of allocator work it refused to fit (running the
driver with `GLIBC_TUNABLES=glibc.malloc.tcache_count=0 MALLOC_ARENA_MAX=1`
brings that share to 28.8% and the block coefficient to 433). The direction
and the order of magnitude are what the decision needs: a bind that costs
about the same as the new one at five superblocks costs eight times more at a
hundred.

**What the rewrite left behind.** The new core's 52% irregular share is not
allocator noise (the deterministic allocator leaves it at 49.7%). It is
`memcmp` under `apply_batch`, and it follows a state the region does not
declare. From `out/step_admission` (32 requests per bind, one superblock per
bind), the commit pass alone, `drperf-dev trace out/step_admission --region ftl_directory_bind_commit`:

```
blocks:    0       32      64      96      128     160     192     224     256     288     320     352     384     416      448
commit  65,148  70,848  76,513  84,751  86,942  90,591  95,492  87,073  97,684  107,902  64,070  91,454  91,876  178,755  102,365
```

The cost climbs by 4-5k per superblock and then drops back (at 10 superblocks,
again at 25, 30, 40), with one spike when `block_locations` doubles (416+32 =
448 blocks; discover's declared `rehash` state prices that at 186.8 per
rehashed block). `superblocks` is a `BTreeMap<String, Superblock>`: every
request does three string-keyed lookups per pass, each a linear scan of one
leaf with `memcmp` per key, and a leaf holds up to eleven keys before it
splits. The cost follows the occupancy of the leaf the new key lands in, which
is why it is neither constant nor linear in anything declared: at 16
requests the same bind costs anywhere from 153k to 211k depending on where in
the leaf's fill cycle the directory happens to be.

**Could a better formula have explained it?** This was pushed until it
stopped paying, because it is the question drperf's loop is supposed to
answer: read the unexplained functions, find the state they follow, declare
it, watch the share fall. Here the share does not fall. All four
declarations below were measured on the same driver at the same production
shape (120 binds of 32 blocks, the `commit` pass), so the percentages compare
directly:

| declared states | formula | unexplained |
|---|---|---|
| `requests, blocks` (as annotated on the branch) | `1.4*blocks + 33,048` | 69.7% |
| `requests, superblocks, rank, rehash` (rank = keys sorting before the batch's target) | `50*superblocks - 9.9*rank + 0.0202*rehash + 34,603` | 71.0% |
| `requests, superblocks, headroom, tombstones` (index growth left, and entries the rollbacks removed since it last grew) | `44.1*superblocks + 0*headroom + 0*tombstones + 32,956` | 70.4% |
| `requests, superblocks, rehash` (rehash = entries moved when arrivals exceed headroom, 0 otherwise) | `44*superblocks + 0.0187*rehash + 33,162` | 69.7% |
| `requests, superblocks, searches, rehash` (searches = requests x tree depth, a product) | `45.5*superblocks + 0.434*searches + 0.082*rehash + 33,186` | 69.6% |
| `requests, resident` with `resident = superblocks/16` (coarse: no per-call-unique quantity) | `1,339.3*requests + 956.8*resident + 4,829` | **54.2%** |
| `requests, resident, rehash` (threshold added back on top of the coarse pair) | `999.6*requests + 638.5*resident + 0.552*rehash + 4,231` | 65.0% |

The three added states are each a legitimate reading of "the history that
sets the cost", and the third is carried by the program rather than projected:
`DirectoryState` gains a `perfmark`-gated counter of the entries each rollback
removes since the block index last changed capacity, because a removal leaves
a tombstone that spends the table's growth exactly as a live entry does, and
no projection from the length can see that. Every one of them is reported with
a coefficient at or near zero, and drperf is right to do so:

- `rank` is collinear with `superblocks` in this driver and its coefficient
  comes out negative, the signature of a state that is not the driver.
- `headroom` and `tombstones` describe a threshold, not a slope. The bind at
  55 superblocks runs with `headroom=14` against 32 arriving blocks and costs
  447,272 against a ~110,000 neighbour, but a plane in `headroom` cannot
  express "and then it grows".
- The indicator built for that threshold fires five times in 120 binds, at 6,
  13, 27, 55 and 111 superblocks, and the cost per entry it implies is 432,
  then 127, then 254, then 223. Not proportional, so not affine, so correctly
  left out of the coefficients.
- `searches` counts the work rather than describing it: every request makes a
  fixed number of lookups in the map and each compares keys down one
  root-to-leaf path, so the comparisons go as requests x depth. Declared as
  that product it earns 0.434 per search and moves the share by 0.1 points.

None of this is an artifact of averaging the two instrumented repeats,
which run with different hash seeds: derived from each repeat alone the
share is 70.4% and 69.4%.

Varying `requests` at production size (`CASE_STEPS=45 CASE_FILL_A=8
CASE_FILL_B=32`, `out/commit_vary_prod`) recovers the per-request coefficient
that a fixed batch size hides, `841.4*requests + 45.6*superblocks + 3,397`,
and leaves the share at 70.1%.

**What actually brought it down.** Not a better description of the work, but a
coarser one. `blocks` and `superblocks` take a new value on every single call,
so all 120 binds sat at 120 state points of one sample each, and drperf's
per-block test compares a block's cost at a point against a plane within a 5%
tolerance. With one sample per point there is nothing to average, so ordinary
allocator and hash jitter is classified irregular. Bucketing the directory
into `superblocks/16` gives about 30 binds per point, and the irregular block
count falls from 155 to 33.

What matters is where the search cost goes once the points have samples: into
the coefficients, where it belongs.

```
per-requests coefficient by function:
           370.1  <Directory>::apply_batch          <- the inlined B-tree search
           286.5  _int_malloc
           137.2  __GI___libc_malloc
per-resident coefficient by function:
           471.2  <btree::map::Iter<String, Superblock>>   <- the prune scan
           270.6  _int_malloc
             102  __memcmp_avx2_movbe               <- the key comparison
```

So the B-tree search is explainable after all, at 370 instructions per request
plus 102 per sixteen resident superblocks. It was never the search that
resisted the fit; it was asking the fit to distinguish 120 singleton points.

Adding the threshold state back on top of the coarse pair makes it worse, 65.0%,
because the indicator fires often enough to split the points into singletons
again and give back the averaging.

What is left at 54.2% is not the B-tree. It is the hash-table rehash: two binds
of 120 cost 447,272 and 793,329 against a ~110,000 neighbour, and the ratio of
those two excesses to the table size at each, 191 and 192 instructions per
entry, is the same to within a part in two hundred. The work is exactly
proportional; only its timing is not predictable, because which pass pays for
the growth depends on tombstones left by the rollback and on the per-process
hash seed. Across the two instrumented repeats of one run the spikes land on
different binds.

Correlating the measured cost against superblock count directly gives R^2 =
0.06: the commit pass is close to flat per bind, and the variance the fit was
being asked to explain was almost entirely those two events.

What is left is `memcmp` and `apply_batch`, in every attribution, in the same
proportion: the string-keyed B-tree search. Its cost per lookup is set by how
many keys sit in the node the search lands in, and that occupancy is a
function of the entire insertion and removal history of the map, which the
program can neither read nor summarise in an integer. The hash side is worse
than undeclarable, it is not deterministic: the same logical run grows the
index at different binds in the two instrumented repeats, because the
placement of tombstones depends on the per-process random hash seed.

The A/B against the hash-keyed build settles what the residue is. Same
driver, same shape, same declared states, only the key type differs:

```
BTreeMap<String, _>   cost(requests, blocks) = 1.4*blocks   + 33,048   irregular 69.7%
    irregular by function: apply_batch 25,494 | __memcmp_avx2_movbe 22,781 | hash_one 13,043
HashMap                cost(requests, blocks) = 0.491*blocks + 34,165   irregular 62.7%
    irregular by function: sip::Hasher 17,196 | _int_malloc 12,249 | hash_one 10,234
```

The `memcmp` disappears with the string keys, which is the confirmation that
it was the B-tree search, and the share barely moves because a hash table's
probe counts are just as internal as a B-tree's node fills. The residue is
container-internal work in both, which is why no declaration reaches it.

**Verdict on this region: 19.5%, under the campaign's 20% bar.** Getting there
took four fixes, and only the last one was about the marker's states.

```
$ CASE_REPEAT=1 CASE_SIZES=0 CASE_FILLS=4,8,12,16,20,24 CASE_REPS=1 CASE_INNER=150 \
    ./run_case.sh commit_pure2 .venv-perf/bin/python examples/cases/bind_at_size.py

  states: requests=4 x150, requests=8 x151, requests=12 x150, requests=16 x151,
          requests=20 x150, requests=24 x1058
  cost(requests) = 2,237.6*requests + 3,877.5        [all requests]
      blocks: 192 affine, 648 constant, 33 irregular (19.5% of cost)
```

1. **Every call sat on a state point seen once.** `blocks` and `superblocks`
   take a new value on every bind, so 120 calls made 120 singleton points. A
   point with one sample has no mean, and the 5% per-block tolerance then reads
   ordinary allocator jitter as cost that follows no state. This was the
   largest single factor and it is a property of the driver, not the code.
2. **Bucketing was the wrong repair.** `superblocks/16` bought samples, but a
   bucket spans 32 real directory sizes, so the spread inside a point became
   genuine variation. It reached 54.2% and stopped.
3. **The driver mixed two operations.** The binds that build the fixture create
   superblocks; the binds being measured replaced blocks in one. No plane spans
   two code paths. Holding the directory at an exact size and making the
   measured call create-and-prune as well reached 42.1%.
4. **Then the states mattered, and the answer was fewer.** `resident`
   oscillated with the batch size, because a partial rebind leaves the old
   superblock alive and a full one empties it. It was a confound, not a state.
   Dropping it left `requests` alone, and the region resolved.

The earlier conclusion in this section, that the cost was structurally
undeclarable, was wrong. It is 2,238 instructions per request plus 3,878, and
the B-tree search sits inside that coefficient.

**What this run does not measure.** It holds the directory at one size, so it
gives the per-request cost cleanly and says nothing about how cost varies with
directory size. Recovering both at once needs `requests` and directory size to
vary independently with every combination repeated, which is again a driver
change rather than a marker change.

 Its formula is not
a usable cost model and should not be quoted as one. What this region does
yield is the attribution, which names the same three container-internal
symbols every time, and the measured per-call totals in the trace, which are
exact. Every quantitative claim in this case rests on those totals, not on the
formula: the 1,371,318 / 377,313 / 304,471 instructions per bind are measured
means over 120 binds, and the per-call tables are raw trigger costs.

So the honest report on this region is that its cost is not an affine function
of any state the program can declare, and that this is a property of the data
structure rather than a gap in the annotation. That is the argument for the
change below, and it is one a percentage alone would not have made: the
residue is stable at 70% however it is described, and its attribution names
the same two symbols every time.

**The experiment.** Branch `case-hashmap` (8e5349c) changes the type of that
one field to `HashMap<String, Superblock>` and sorts the keys `prune_empty`
collects so the order of freed handles stays deterministic; nothing else.
Same driver, same command, on `fix-hashmap/.venv-hm`:

```
derive ftl_directory_bind_batch          (out/bind_grow_hm)
  cost(requests, blocks, superblocks) = 4,168.9*requests + -1.7*blocks + 42.9*superblocks + 11,923   blocks: 391 affine, 1179 constant, 140 irregular (46.4% of cost)
    irregular by function:
            14,088.4  <core::hash::sip::Hasher<core::hash::sip::Sip13Rounds> as core::hash::  [_ditto_ftl_core.abi3.so]
               8,090  <std::hash::random::RandomState as core::hash::BuildHasher>::hash_one:  [_ditto_ftl_core.abi3.so]
```

Per call, requests = 16, superblocks 24..33, B-tree then hash map:

```
superblocks:   24       25       26       27       28       29       30       31       32       33
BTreeMap    210,558  207,309  185,585  189,572  200,278  201,210  153,264  202,648  163,148  172,087
HashMap     183,273  158,892  163,515  169,298  163,702  155,104  155,205  155,287  190,581  158,693
```

and at production shape (`out/bind_grow_hm_prod`, every eighth bind):

```
superblocks:  0        8        16       24       32       40       48       56       64       72       80       88       96       104      112
BTreeMap   258,488  342,094  357,451  392,651  301,457  285,740  332,595  382,815  397,545  440,571  414,214  429,822  397,915  366,259  355,777
HashMap    299,841  283,599  291,148  296,532  297,995  298,143  295,231  305,432  300,170  295,840  290,025  296,024  289,175  290,663  308,353
```

The climb with the directory is gone; what remains irregular is SipHash at the
hash map's own growth points (3, 7, 14, 28, 56 keys) and the `block_locations`
doubling that every variant pays: in both production-shaped runs the binds at
55 and 111 superblocks (1,760 and 3,552 blocks, the next 32 crossing 1,792 and
3,584) cost 648k/996k with the hash map and 699k/1,066k with the B-tree, the
187 per rehashed block that the discover pass's declared `rehash` state priced.
Over the 120 production-shaped binds the means are: old core 1,371,318, current
core 377,313, hash-keyed current core 304,471 instructions per bind. The
equivalence digest of case 2 is unchanged (`c4529c2f9fbf6a75`).


**What it changed.** Three things a profiler at driver scale does not give:
the rewrite was the right call even though the small-scale numbers favour the
old code, because the old cost function has terms in `blocks` and
`superblocks` and the new one does not; the residual growth in the new one
comes from the key type of one map, not from the algorithm, and changing that
type is worth 19% of the bind at production shape (377k to 304k per 32-block
bind, more at the directory sizes where a leaf is nearly full) with a one-line
diff; and the discover pass plus rollback are more than half of the new
per-request cost, so a read-only discovery (compute the new keys without
mutating) is the next-largest saving on this path. A fourth, smaller: the
`block_locations` doubling is a single bind that costs 187 instructions per
resident block, 700k at 3,584 blocks, and could be pre-sized from the admission
limit.

---

