"""Compare paired native Inferix outputs; validation-copy timings are excluded.

Usage: python3 compare_inferix.py ORIGINAL_DIR ADAPTED_DIR --output comparison.json
Both directories need report.json and either video.pt or validation.pt. The
optional validation.pt files compare warmup and measured segment captures.
"""

import argparse
import json
import math
from pathlib import Path


SETTINGS = ("role", "latent_frames", "segments", "seed", "prompt",
            "warmup_frames", "streaming_mode", "low_memory", "clock")


def require(condition, message, failures):
    if not condition:
        failures.append(message)


def tensor_metrics(left, right, label, atol, rtol, failures):
    import torch

    item = {"name": label, "shape_a": list(left.shape), "shape_b": list(right.shape),
            "dtype_a": str(left.dtype), "dtype_b": str(right.dtype),
            "finite_a": None, "finite_b": None, "allclose": False,
            "max_abs_error": None, "mean_abs_error": None}
    same_layout = left.shape == right.shape and left.dtype == right.dtype
    require(same_layout, f"{label}: shape/dtype differs", failures)
    if left.is_floating_point() or left.is_complex():
        item["finite_a"] = bool(torch.isfinite(left).all().item())
        item["finite_b"] = bool(torch.isfinite(right).all().item())
        require(item["finite_a"] and item["finite_b"], f"{label}: nonfinite values", failures)
    else:
        item["finite_a"] = item["finite_b"] = True
    if not same_layout or not item["finite_a"] or not item["finite_b"]:
        return item
    if left.numel():
        target_dtype = torch.complex128 if left.is_complex() else torch.float64
        difference = (left.to(target_dtype) - right.to(target_dtype)).abs()
        item["max_abs_error"] = float(difference.max().item())
        item["mean_abs_error"] = float(difference.mean().item())
    else:
        item["max_abs_error"] = item["mean_abs_error"] = 0.0
    item["allclose"] = bool(torch.allclose(left, right, atol=atol, rtol=rtol))
    require(item["allclose"], f"{label}: values differ beyond atol={atol}, rtol={rtol}", failures)
    return item


def load_tensor(path):
    import torch
    return torch.load(path, map_location="cpu", weights_only=True)


def compare(left_dir, right_dir, atol=0.0, rtol=0.0, allowed_source_changes=(),
            allow_kv_residency_change=False):
    left_dir, right_dir = left_dir.resolve(), right_dir.resolve()
    paths = {"original": str(left_dir), "adapted": str(right_dir)}
    reports = [json.loads((folder / "report.json").read_text()) for folder in (left_dir, right_dir)]
    a, b = reports
    failures = []
    for field in SETTINGS:
        require(field in a and field in b and a[field] == b[field],
                f"report setting differs or is missing: {field}", failures)
    require(a.get("packages") == b.get("packages") and isinstance(a.get("packages"), dict)
            and bool(a.get("packages")),
            "package versions differ or are missing", failures)
    for field in ("shape", "finite_checked"):
        require(field in a and field in b and a[field] == b[field],
                f"report field differs or is missing: {field}", failures)
    for index, report in enumerate(reports):
        require(report.get("finite_checked") is True and report.get("finite") is True,
                f"{'original' if index == 0 else 'adapted'}: native video finiteness was not confirmed", failures)
        require(report.get("role") == "native", "semantic comparison requires native runs", failures)
    chunks_a = [row.get("shape") for row in a.get("chunks", [])]
    chunks_b = [row.get("shape") for row in b.get("chunks", [])]
    require(chunks_a == chunks_b and bool(chunks_a), "stream callback count/order/shapes differ or are empty", failures)
    require((left_dir / "config.yaml").is_file() and (right_dir / "config.yaml").is_file(),
            "config.yaml missing", failures)
    if (left_dir / "config.yaml").is_file() and (right_dir / "config.yaml").is_file():
        import yaml
        configs = [yaml.safe_load((folder / "config.yaml").read_text())
                   for folder in (left_dir, right_dir)]
        if allow_kv_residency_change:
            require(all(isinstance(c, dict) and isinstance(c.get("model_kwargs"), dict)
                        and isinstance(c["model_kwargs"].get("enable_kv_offload"), bool)
                        for c in configs),
                    "explicit KV allowance requires boolean model_kwargs.enable_kv_offload on both sides",
                    failures)
            for config in configs:
                if isinstance(config, dict) and isinstance(config.get("model_kwargs"), dict):
                    config["model_kwargs"] = dict(config["model_kwargs"])
                    config["model_kwargs"].pop("enable_kv_offload", None)
            require(configs[0] == configs[1],
                    "effective config.yaml differs outside model_kwargs.enable_kv_offload", failures)
        else:
            require((left_dir / "config.yaml").read_bytes() == (right_dir / "config.yaml").read_bytes(),
                    "effective config.yaml differs", failures)
    if "kv_residency" in a or "kv_residency" in b:
        require(a.get("kv_residency") == b.get("kv_residency") or allow_kv_residency_change,
                "recorded KV residency differs without explicit allowance", failures)

    source_a = a.get("source_sha256", {})
    source_b = b.get("source_sha256", {})
    require(isinstance(source_a, dict) and isinstance(source_b, dict) and
            set(source_a) == set(source_b) and bool(source_a),
            "source manifest keys differ or are missing", failures)
    source_changes = {key: {"original": source_a.get(key), "adapted": source_b.get(key)}
                      for key in sorted(set(source_a) | set(source_b))
                      if source_a.get(key) != source_b.get(key)}
    unexpected_sources = sorted(set(source_changes) - set(allowed_source_changes))
    require(not unexpected_sources,
            "source changes lack explicit allowance: " + ", ".join(unexpected_sources), failures)
    for field in ("checkpoint", "checkpoint_sha256", "base", "base_weights_sha256",
                  "cudnn_version", "cudnn_policy", "repetitions", "harness_sha256"):
        if field in a or field in b:
            require(a.get(field) == b.get(field), f"recorded input differs: {field}", failures)
    identities = [report.get("asset_identity") for report in reports]
    def valid_identity(identity):
        return (isinstance(identity, dict) and bool(identity) and all(
            isinstance(item, dict) and isinstance(item.get("bytes"), int)
            and item["bytes"] > 0 and isinstance(item.get("sha256"), str)
            and len(item["sha256"]) == 64 for item in identity.values()))
    identity_recorded = all(valid_identity(identity) for identity in identities)
    require(identity_recorded, "asset_identity hashes or byte counts are missing", failures)
    require(identities[0] == identities[1], "asset_identity differs", failures)

    video_paths = [folder / "video.pt" for folder in (left_dir, right_dir)]
    validation_paths = [folder / "validation.pt" for folder in (left_dir, right_dir)]
    require(video_paths[0].is_file() == video_paths[1].is_file(), "video.pt present on only one side", failures)
    require(validation_paths[0].is_file() == validation_paths[1].is_file(),
            "validation.pt present on only one side", failures)
    require(video_paths[0].is_file() or validation_paths[0].is_file(),
            "no paired video.pt or validation.pt tensors", failures)

    tensors = []
    if all(path.is_file() for path in video_paths):
        videos = [load_tensor(path) for path in video_paths]
        tensors.append(tensor_metrics(*videos, "video.pt", atol, rtol, failures))
        for side, report, video in zip(("original", "adapted"), reports, videos):
            require(list(video.shape) == report.get("shape"), f"{side}: video.pt disagrees with report shape", failures)

    validation = {"available": all(path.is_file() for path in validation_paths),
                  "segments": [], "cache_empty": None}
    if validation["available"]:
        manifests = []
        for folder in (left_dir, right_dir):
            path = folder / "validation.json"
            require(path.is_file(), f"{path}: missing validation manifest", failures)
            manifests.append(json.loads(path.read_text()) if path.is_file() else {})
        for side, manifest in zip(("original", "adapted"), manifests):
            require(manifest.get("timing_valid") is False,
                    f"{side}: validation artifact must declare timing_valid=false", failures)
        captured = [load_tensor(path) for path in validation_paths]
        require(len(captured[0]) == len(captured[1]) and bool(captured[0]),
                "validation segment count differs or is empty", failures)
        expected = int(a.get("segments", 0)) + int(bool(a.get("warmup_frames", 0)))
        require(a.get("warmup_frames") == b.get("warmup_frames"),
                "warmup_frames differs", failures)
        require(len(captured[0]) == expected and len(captured[1]) == expected,
                "validation segment count differs from warmup + measured segments", failures)
        cache_ok = True
        for segment_index, pair in enumerate(zip(*captured)):
            left, right = pair
            rows = {"index": segment_index, "callbacks": [], "outputs": [], "cache_empty": []}
            callbacks_a, callbacks_b = left.get("callbacks", []), right.get("callbacks", [])
            require(len(callbacks_a) == len(callbacks_b),
                    f"segment {segment_index}: callback counts differ", failures)
            for callback_index, (x, y) in enumerate(zip(callbacks_a, callbacks_b)):
                rows["callbacks"].append(tensor_metrics(x, y,
                    f"segment {segment_index} callback {callback_index}", atol, rtol, failures))
            outputs_a, outputs_b = left.get("outputs", []), right.get("outputs", [])
            require(len(outputs_a) == len(outputs_b) == 2,
                    f"segment {segment_index}: expected video and final latent outputs", failures)
            for output_index, (x, y) in enumerate(zip(outputs_a, outputs_b)):
                rows["outputs"].append(tensor_metrics(x, y,
                    f"segment {segment_index} {'video' if output_index == 0 else 'latent'}",
                    atol, rtol, failures))
            for side, item in zip(("original", "adapted"), pair):
                state = item.get("cache_empty", {})
                valid = state.get("_feat_map") is True and state.get("_enc_feat_map") is True
                cache_ok &= valid
                require(valid, f"segment {segment_index} {side}: VAE cache not empty after return", failures)
                rows["cache_empty"].append({"side": side, **state})
            validation["segments"].append(rows)
        validation["cache_empty"] = cache_ok
        require(manifests[0].get("segments") == manifests[1].get("segments"),
                "validation.json callback/output shapes or cache flags differ", failures)

    # The validation wrapper copies tensors during generation. Never derive
    # performance ratios or verdicts from either report's host timings.
    return {"schema": "inferix-native-semantic-comparison-v1", "artifacts": paths,
            "settings": {key: a.get(key) for key in SETTINGS},
            "packages": a.get("packages"), "source_changes": source_changes,
            "allowed_source_changes": sorted(set(allowed_source_changes)),
            "allowed_kv_residency_change": allow_kv_residency_change,
            "input_identity": {"asset_manifest_recorded": identity_recorded,
                               "strict_asset_identity_proved": identity_recorded and identities[0] == identities[1],
                               "files": len(identities[0]) if identity_recorded else 0},
            "stream_chunk_shapes": chunks_a, "atol": atol, "rtol": rtol,
            "tensor_comparisons": tensors, "validation": validation,
            "performance": {"eligible": False,
                            "reason": "validation copies alter execution; host times are excluded from semantic comparison"},
            "passed": not failures, "failures": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("adapted", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--atol", type=float, default=0.0)
    parser.add_argument("--rtol", type=float, default=0.0)
    parser.add_argument("--allow-source-change", action="append", default=[], metavar="RELATIVE_PY_PATH")
    parser.add_argument("--allow-kv-residency-change", action="store_true",
                        help="Permit only model_kwargs.enable_kv_offload to differ in effective config")
    args = parser.parse_args()
    if not all(math.isfinite(x) and x >= 0 for x in (args.atol, args.rtol)):
        parser.error("tolerances must be finite and nonnegative")
    result = compare(args.original, args.adapted, args.atol, args.rtol,
                     args.allow_source_change, args.allow_kv_residency_change)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"semantic comparison {'PASS' if result['passed'] else 'FAIL'}: {args.output}")
    if not result["passed"]:
        for failure in result["failures"]:
            print(" - " + failure)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
