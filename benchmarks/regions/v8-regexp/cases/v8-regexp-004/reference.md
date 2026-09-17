# Reference

The target is `v8::internal::regexp::CheckSpecialClassRanges` in V8's RegExp implementation. The patch adds one empty marker and the helper include without changing existing statements.

No parameter context values are collected. Runtime reachability and a concrete build command have not been verified.
