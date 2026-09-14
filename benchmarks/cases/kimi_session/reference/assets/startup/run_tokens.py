"""Drive the per-step request token estimate over a realistic conversation.

Usage: run_tokens.py [n_msgs=N] [chars_per_msg=N] [steps=N]
Builds a history of n_msgs messages, then calls estimate_request_tokens the way
KimiSoul does before every LLM step.
"""
import os, sys, random, pathlib

def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1); args[k] = int(v)
    n_msgs = args.get("n_msgs", 40)
    cpm = args.get("chars_per_msg", 800)
    steps = args.get("steps", 8)
    n_tools = args.get("n_tools", 17)

    from kosong.message import Message, TextPart
    from kosong.tooling import Tool
    from kimi_cli.llm import estimate_request_tokens

    rng = random.Random(7)
    words = ("the quick brown fox reads a file and greps the repository for a symbol "
             "then writes the patch and runs the test suite again").split()
    def text(n):
        out = []
        total = 0
        while total < n:
            w = rng.choice(words); out.append(w); total += len(w) + 1
        return " ".join(out)[:n]

    history = []
    for i in range(n_msgs):
        role = "user" if i % 2 == 0 else "assistant"
        history.append(Message(role=role, content=[TextPart(type="text", text=text(cpm))]))

    system_prompt = text(4000)
    tools = [
        Tool(name=f"tool_{i}", description=text(300),
             parameters={"type": "object",
                         "properties": {"path": {"type": "string", "description": text(80)},
                                        "n": {"type": "integer"}},
                         "required": ["path"]})
        for i in range(n_tools)
    ]

    total = 0
    for _ in range(steps):
        total += estimate_request_tokens(system_prompt, tools, history)
    print(f"n_msgs={n_msgs} chars_per_msg={cpm} n_tools={n_tools} steps={steps} estimate={total // steps}")

if __name__ == "__main__":
    main()
