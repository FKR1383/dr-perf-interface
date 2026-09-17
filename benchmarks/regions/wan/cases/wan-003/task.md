# VaeImageProcessor.postprocess

Inspect the marked block in `src/diffusers/image_processor.py` at the pinned revision.
The marker has no PCVs; identify useful state expressions for its cost.

Exercise the named diffusers Wan method with a tiny random model on CPU. Use a bounded video or prompt-encoding call appropriate to this method; full model downloads are unnecessary.

Apply this case patch independently in an upstream checkout. The snapshot is
source context, not a standalone program. Install the matching project
dependencies, make `perfmark/python` importable and build libperfmark before
measuring. See `case.json` for the test command and recorded validation status.
Keep the code behavior unchanged while adding observation state.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
