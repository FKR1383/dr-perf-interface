"""Python event checkpoints; original control flow supplies the condition."""
import sys
import threading
import time
import perfmark

# Attach before either thread can publish. Event markers themselves do not attach.
with perfmark.region('capture', n=1):
    pass
ready = threading.Event()


def produce():
    with perfmark.region('B', n=1):
        time.sleep(.01)
        perfmark.event_publish(1, 1)  # Delay here holds back the following set().
        ready.set()


thread = threading.Thread(target=produce)
thread.start()
with perfmark.region('A', need=1):
    if len(sys.argv) > 1 and sys.argv[1] == 'missing-wait':
        time.sleep(.2)  # Deliberate bug: timing coincidence instead of readiness.
    else:
        ready.wait()
    perfmark.event_waited(1, 1)
thread.join()
