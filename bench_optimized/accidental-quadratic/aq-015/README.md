# aq-015 optimization

The accepted change scans the major and minor version fields by index, then
slices each completed field once. This replaces repeated string concatenation
and suffix slicing while keeping all work inside the original region. A
differential check found no differences across 39,531 grammar-focused inputs.

DrPerf target instructions fell from 273,667 to 235,906 across the same six
calls, a 13.8% reduction. Both measurements passed the strict gate. Seven
interleaved native runs had medians of 48.9 ms before and 48.0 ms after, but
fresh-interpreter startup and concurrent activity make that timing indicative
only.
