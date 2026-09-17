# aq-003 optimization

The accepted change replaces two repeated regular-expression searches over
successive suffixes with one substitution pass. All work remains inside the
original region. A differential check found no differences across 65,989
escape-focused inputs, including `None` and unquoted controls.

DrPerf target instructions fell from 274,390 to 168,438 across the same seven
states, a 38.6% reduction. Both measurements passed the strict 5% gate with no
unexplained instructions. Seven interleaved native runs were dominated by
fresh-interpreter startup (median 38.9 ms before and 39.9 ms after), so they do
not establish a wall-time speedup.
