"""Shared fixture for the drperf case drivers (CPU only, Rust core only)."""

import gc
import os
import sys

from perfmark import region  # the drivers run only under drperf


class Storage:
    """Handle allocator with no capacity: admission_limit() == live blocks."""

    def __init__(self) -> None:
        self.next_handle = 0

    def allocate(self, _name: str) -> int:
        self.next_handle += 1
        return self.next_handle

    def free(self, _handle: int) -> None:
        pass

    def additional_capacity(self) -> int:
        return 0


def superblock_entries(sb: int, nblocks: int, fill: int, owner: str = "s"):
    """`fill` store entries that all land in superblock `owner/g0/<sb>`."""
    return [
        (sb * nblocks + off, owner, 0, sb * nblocks + off, (sb * nblocks + off) * 256, True)
        for off in range(fill)
    ]


def superblock_key(sb: int, owner: str = "s") -> str:
    return f"{owner}/g0/{sb}"


def prologue() -> None:
    """Deterministic single-threaded run; first region declares no state.

    drperf attaches at the first marked region and records that trigger
    without its declared states, so the first region of every driver is a
    stateless one (see /home/ubuntu/drperf/bug_report.md).
    """
    gc.disable()
    with region("case_prologue"):
        pass


def arg(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def say(*parts) -> None:
    print(*parts, file=sys.stderr)
