## Gradio: streaming one token re-processes the whole conversation

Gradio fronts a large share of AI demos, and its most common use is a streaming chat.
Streaming works by advancing a generator one yield at a time; `Blocks.process_api` calls
`postprocess_data` on each yield, and for a chatbot that runs `Chatbot.postprocess` over
the entire message list. The framework then diffs the result against the previous chunk
to discover that only the last message changed, and sends the delta.

The wire payload is small, which is good design. The CPU cost is not: everything before
the diff is proportional to the whole conversation.

### Measured per streamed chunk

drperf, per message already in the conversation:

| stage | instructions per message | what it does |
|---|---|---|
| `_postprocess` loop | 31,611.7 | re-processes every message |
| `model_dump` and glue | ~14,209 | re-serialises every message |
| `diff` | 1,258 | walks all messages to find the one that changed |
| `_check_format` | 939 | re-validates every message |
| `model_build` | 161.5 | rebuilds the Pydantic model |
| total | ~49,500 | |

Every one of those fits with 0.0% to 3.5% irregular, so the linear-in-conversation shape
is not in doubt. In wall time, one chunk costs:

| messages in conversation | 0 | 10 | 40 | 160 |
|---|---|---|---|---|
| per chunk | 0.015 ms | 0.072 ms | 0.243 ms | 1.268 ms |

An 85x rise from an empty chat to an 80-turn one. A 500-token reply at that point spends
0.63 s in postprocessing alone, and it keeps growing with the conversation. Against a
model streaming at 200 tokens per second, where a token is 5 ms, this is 25% overhead
that nobody attributes to the framework.

A second, milder effect: the reply being streamed is itself a growing string, and `diff`
tests `obj2.startswith(obj1)` on it. Per-chunk cost rises 1.70x over a 1,600-chunk reply.
Real, but an order of magnitude smaller than the conversation-length term.

### Not fixed

The honest fix is that the framework already knows what changed, since `diff` computes it,
but it computes it after doing the O(conversation) work rather than before. Making the
streaming path re-process only the changed message is a design change in Gradio's core
rather than a contained patch, and I have not attempted it. Recorded here as a
measurement, not as a fix.

