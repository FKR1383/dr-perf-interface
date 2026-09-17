"""Price one streamed chat chunk in Gradio, broken down.

Chatbot.postprocess is copied from the installed gradio with only region markers added,
so each stage's cost function stands on its own against the conversation length.
"""
import sys, time

sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")
import perfmark

import gradio as gr
from gradio import utils
from gradio.components.chatbot import ChatbotDataMessages

WORDS = ("the quick brown fox jumps over the lazy dog while seven wizards vex a judge "
         "under pale moonlight").split()
BODY = " ".join(WORDS[i % len(WORDS)] for i in range(40))


def conversation(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"{BODY} ({i})"}
            for i in range(n)]


def marked_postprocess(chatbot, value, n):
    """gradio/components/chatbot.py: Chatbot.postprocess, with its stages marked."""
    if value is None:
        return ChatbotDataMessages(root=[])
    with perfmark.region("check_format", n=n):
        chatbot._check_format(value)
    with perfmark.region("per_message", n=n):
        processed_messages = []
        for message in value:
            processed_message = chatbot._postprocess(message)
            if processed_message is not None:
                processed_messages.extend(processed_message)
    with perfmark.region("model_build", n=n):
        return ChatbotDataMessages(root=processed_messages)


def main():
    st = perfmark.states(n=40)
    n = int(st["n"])
    chatbot = gr.Chatbot()
    msgs = conversation(n)
    prev = None
    for _ in range(3):
        with perfmark.region("chunk", n=n):
            cur = marked_postprocess(chatbot, msgs, n).model_dump()
            if prev is not None:
                with perfmark.region("diff", n=n):
                    utils.diff(prev, cur)
            prev = cur
    print(f"n={n} messages")


if __name__ == "__main__":
    main()
