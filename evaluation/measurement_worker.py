"""Fresh process used exclusively by the evaluation harness measurement service."""
from pathlib import Path
import sys
import subprocess

import drperf_measure
from results import read_json, write_json
from workload import FrozenWorkload, WorkloadChanged


def main():
    request_path = Path(sys.argv[1])
    request = read_json(request_path)
    contract = request.get("workload")
    if contract is not None:
        workload = FrozenWorkload.from_metadata(contract, request["region"])
        out = Path(request["out"])
        if workload.build:
            built = subprocess.run(workload.build, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (out / "build.log").write_text(built.stdout)
            if built.returncode:
                write_json(request_path.parent / "result.json", drperf_measure.failed(
                    "measurement_error", f"frozen build failed ({built.returncode}); see build.log"))
                return
        try:
            workload.validate(Path.cwd())
        except WorkloadChanged as exc:
            write_json(out / "workload-check.json", {"status": "rejected", "message": str(exc)})
            write_json(request_path.parent / "result.json", drperf_measure.failed("invalid_measurement", str(exc)))
            return
    measured = drperf_measure.measure(request["command"], Path(request["out"]),
                                     request["region"], request["variables"])
    write_json(request_path.parent / "result.json", measured)


if __name__ == "__main__":
    main()
