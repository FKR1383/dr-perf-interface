"""Opt-in Self-Forcing host-metadata adaptation for an isolated Inferix checkout.

Apply the same adapted checkout in native and GX measurements. The original
Inferix checkout is left untouched unless explicitly passed to ``--apply``.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re


SOURCE_COMMIT = "77170deca738914c1999bc9e48eea84acb534db3"
SOURCE_HASHES = {
    "inferix/models/self_forcing/wrapper.py": "e151631f3962c7d7114ee793fa29be8b5796dae35abfd6d5dedf7a786d1f8baa",
    "inferix/pipeline/self_forcing/CausalInferencePipeline.py": "d71f233208fa2920e40e34ff8f6713c89e81ee4aa0b25610d136671ce35c34d2",
    "inferix/pipeline/self_forcing/CausalDiffusionInferencePipeline.py": "4cb422495f36cbe60e346442f51170be17b029764f5efe44aa3a14576db1bca7",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def adapt(relative, source):
    if relative.endswith("/wrapper.py"):
        old = """        ids = ids.to(self.device)
        mask = mask.to(self.device)
        seq_lens = mask.gt(0).sum(dim=1).long()
"""
        new = """        # Tokenizer mask is host data; retain its lengths before GPU transfer.
        seq_lens = mask.gt(0).sum(dim=1).long()
        ids = ids.to(self.device)
        mask = mask.to(self.device)
"""
        if source.count(old) != 1:
            raise ValueError(f"unexpected tokenizer layout in {relative}")
        return source.replace(old, new), 1

    # These counters are written only from host-derived positions and read for
    # Python cache slicing/branching. K/V tensors remain on their original device.
    pattern = re.compile(
        r'(?P<key>\["(?:global|local)_end_index"\]\s*=\s*torch\.tensor\(\s*'
        r'\[0\], dtype=torch\.long), device=(?:noise\.device|device)\)'
    )
    # Initial cache dictionaries use the same scalar constructors after ':' .
    pattern_dict = re.compile(
        r'(?P<key>"(?:global|local)_end_index":\s*torch\.tensor\(\s*'
        r'\[0\], dtype=torch\.long), device=(?:device|device_pos|device_neg)\)'
    )
    patched, assignments = pattern.subn(r'\g<key>)', source)
    patched, initializers = pattern_dict.subn(r'\g<key>)', patched)
    expected = (2, 2) if relative.endswith("/CausalInferencePipeline.py") else (4, 4)
    if (assignments, initializers) != expected:
        raise ValueError(f"unexpected cache metadata layout in {relative}: {(assignments, initializers)} != {expected}")
    return patched, assignments + initializers


def prepare(root):
    changes = {}
    for relative, expected_hash in SOURCE_HASHES.items():
        path = root / relative
        original = path.read_bytes()
        actual_hash = sha256(original)
        if actual_hash != expected_hash:
            raise ValueError(f"source mismatch for {path}: {actual_hash}; expected {expected_hash}")
        patched, count = adapt(relative, original.decode())
        changes[relative] = (path, original, patched.encode(), count)
    return changes


def apply(root):
    changes = prepare(root)  # Validate every input before any write.
    for path, _original, patched, _count in changes.values():
        path.write_bytes(patched)
    manifest = {
        "source_commit": SOURCE_COMMIT,
        "adaptation": "host tokenizer lengths and host KV cache position counters",
        "files": {relative: {"source_sha256": sha256(original),
                             "adapted_sha256": sha256(patched), "edits": count}
                  for relative, (_path, original, patched, count) in changes.items()},
    }
    manifest_path = root / "inferix-metadata-adaptation.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def validate():
    import torch

    masks = [torch.tensor([[1, 1, 0, 0], [1, 1, 1, 0]]),
             torch.tensor([[0, 1, 2, 0], [1, 1, 1, 1]])]
    for mask in masks:
        source_lengths = mask.gt(0).sum(dim=1).long()
        adapted_lengths = mask.gt(0).sum(dim=1).long()
        assert source_lengths.tolist() == adapted_lengths.tolist()
        context = torch.arange(mask.numel() * 3).reshape(*mask.shape, 3).float()
        source = context.clone()
        adapted = context.clone()
        for tensor, length in zip(source, source_lengths):
            tensor[length:] = 0
        for tensor, length in zip(adapted, adapted_lengths):
            tensor[length:] = 0
        assert torch.equal(source, adapted)

    # Exercise append and eviction branches, including a nonzero sink prefix.
    for capacity, sink, lengths in [(16, 0, [4, 4, 4]), (8, 1, [3, 3, 3]),
                                    (12, 2, [4, 4, 4, 4])]:
        for cpu_counter in (False, True):
            meta = ({key: torch.tensor([0], dtype=torch.long)
                     for key in ("global_end_index", "local_end_index")}
                    if cpu_counter else {"global_end_index": 0, "local_end_index": 0})
            state = []
            current_start = 0
            for length in lengths:
                current_end = current_start + length
                global_end = (meta["global_end_index"].item() if cpu_counter
                              else meta["global_end_index"])
                local_end = (meta["local_end_index"].item() if cpu_counter
                             else meta["local_end_index"])
                evicted = max(0, length + local_end - capacity) if current_end > global_end else 0
                if evicted:
                    rolled = local_end - evicted - sink
                    assert rolled >= 0
                    local_end = local_end + current_end - global_end - evicted
                else:
                    local_end = local_end + current_end - global_end
                state.append((bool(evicted), local_end - length, local_end))
                if cpu_counter:
                    meta["global_end_index"].fill_(current_end)
                    meta["local_end_index"].fill_(local_end)
                else:
                    meta["global_end_index"] = current_end
                    meta["local_end_index"] = local_end
                current_start = current_end
            if not cpu_counter:
                reference = state
            else:
                assert state == reference
    print("metadata CPU validation passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="isolated Inferix checkout")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="verify locked sources and patch counts")
    action.add_argument("--apply", action="store_true", help="adapt the specified isolated checkout")
    action.add_argument("--validate", action="store_true", help="run CPU semantic checks")
    args = parser.parse_args()
    if args.validate:
        validate()
    else:
        if args.root is None:
            parser.error("--root is required with --check or --apply")
        result = apply(args.root) if args.apply else prepare(args.root)
        print(result if args.apply else f"metadata patch ready: {len(result)} locked files")


if __name__ == "__main__":
    main()
