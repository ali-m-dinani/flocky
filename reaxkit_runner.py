"""File-only serial Flocky smoke runner; requires a separately supplied engine."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess


def number(value):
    result = float(str(value).replace("D", "E").replace("d", "e"))
    if not math.isfinite(result):
        raise ValueError("Nonfinite parameter")
    return result


def render_control(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith(("#", "!")):
            continue
        if len(fields) < 2:
            raise ValueError("Control row requires value and keyword")
        value, keyword = fields[:2]
        number(value)
        if len(value) > 7 or len(keyword) > 6:
            raise ValueError("Control value/keyword exceeds native fixed-width format")
        if value == "5" or keyword == "5":
            raise ValueError("Native Flocky treats token '5' as fixed-charge mode; unsupported")
        rows.append(f"{value:>7} {keyword:<6}\n")
    return "".join(rows)


def prepare_request(path):
    request = json.loads(Path(path).read_text())
    if request.get("contract") != "reaxkit-external-runner-v1" or request.get("optimizer") != "flocky":
        raise ValueError("Expected Flocky external-runner request")
    if request.get("seed") is not None:
        raise ValueError("Use seed: null; native RNG forwarding is not supported")
    settings = request["settings"]
    allowed = {"executable", "engine_executable", "params_mod", "iterations", "swarm_size", "cycles"}
    if set(settings) - allowed:
        raise ValueError("Unknown Flocky setting")
    for key, default, minimum in (("iterations", 2, 1), ("swarm_size", 2, 2), ("cycles", 1, 1)):
        settings.setdefault(key, default)
        if type(settings[key]) is not int or settings[key] < minimum:
            raise ValueError("Invalid " + key)
    inputs = request["inputs"]
    for key in ("ffield", "params", "geo", "trainset", "control"):
        if not inputs.get(key) or not Path(inputs[key]).is_file():
            raise ValueError("Required input missing: " + key)
    for key in ("executable", "engine_executable", "params_mod"):
        if not settings.get(key) or not Path(settings[key]).is_file():
            raise ValueError("Supply " + key + "; obtain permission for Tapered ReaxFF from its authors; engine not bundled by ReaxKit")
    for line in Path(inputs["trainset"]).read_text().splitlines():
        if line.strip().upper().startswith(("FORCE", "FREQUENC")):
            raise ValueError("This smoke profile does not stage force/frequency auxiliary files")
    render_control(inputs["control"])
    order = request.get("params_bounds_order")
    if order not in ("min_max", "max_min"):
        raise ValueError("Explicit params_bounds_order required")
    common = {}
    for line in Path(inputs["params"]).read_text().splitlines():
        fields = line.split("#")[0].split("!")[0].split()
        if not fields:
            continue
        if len(fields) != 6:
            raise ValueError("Common params requires six columns")
        address = tuple(map(int, fields[:3]))
        lower, upper = map(number, fields[4:])
        if order == "max_min":
            lower, upper = upper, lower
        if address in common or lower >= upper:
            raise ValueError("Duplicate/invalid common parameter bounds")
        common[address] = (lower, upper)
    field = Path(inputs["ffield"]).read_text().splitlines()
    rows, seen, locations = [], set(), set()
    for line in Path(settings["params_mod"]).read_text().splitlines():
        fields = line.split("#")[0].split("!")[0].split()
        if not fields:
            continue
        if len(fields) != 7:
            raise ValueError("params_mod requires line column section row parameter lower upper")
        line_no, column = map(int, fields[:2])
        address = tuple(map(int, fields[2:5]))
        bounds = tuple(map(number, fields[5:]))
        if address in seen or (line_no, column) in locations or common.get(address) != bounds:
            raise ValueError("params_mod identities/bounds differ from common params")
        if line_no < 1 or line_no > len(field) or column < 1 or column > len(field[line_no - 1].split()):
            raise ValueError("params_mod location outside force field")
        initial = number(field[line_no - 1].split()[column - 1])
        if not bounds[0] <= initial <= bounds[1]:
            raise ValueError("Initial parameter outside bounds")
        seen.add(address)
        locations.add((line_no, column))
        rows.append(" ".join(fields) + "\n")
    if not common or seen != set(common):
        raise ValueError("params_mod must cover all common parameters")
    return request, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_config", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    request, rows = prepare_request(args.run_config)
    settings = request["settings"]
    if args.check_only:
        print(f"Input checks passed: {len(rows)} parameters; manually verify params_mod line/column mappings. No engine evaluations performed.")
        return 0
    if os.name != "posix":
        raise ValueError("Native Flocky requires a POSIX environment; use Linux on Roar")
    for key in ("SLURM_NTASKS", "SLURM_JOB_NUM_NODES", "SLURM_CPUS_PER_TASK"):
        if int(os.environ.get(key, "1")) != 1:
            raise ValueError("Initial serial profile requires one node/task/CPU")
    for key in ("executable", "engine_executable"):
        if not os.access(settings[key], os.X_OK):
            raise ValueError("Not executable: " + settings[key])
    root = Path(request["native_directory"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    marker = root / "flocky-profile.json"
    if marker.exists() or (root / "ffield").exists() or list(root.glob("opti_log.out.*")):
        raise ValueError("Use a fresh campaign; this native directory has already been prepared")
    for key, name in {"ffield": "ffield", "geo": "geo", "trainset": "trainset.in", "control": "control"}.items():
        shutil.copy2(request["inputs"][key], root / name)
    (root / "control").write_text(render_control(request["inputs"]["control"]))
    shutil.copy2(settings["engine_executable"], root / "tapreaxff")
    (root / "params.mod").write_text("".join(rows))
    values = [0, 0, 1, 1, 0, 0.9, 0, 2, 0.001, 0, 0.5, 1, 0, 0,
              settings["swarm_size"], 2, 2, 0.9, 0.4, 1, 0.1, 1,
              settings["iterations"], settings["cycles"], 0, 0, 627.50947406, 2721.2220202]
    (root / "inp_flocky.in").write_text("# ReaxKit serial smoke profile\n\n" + "\n".join(map(str, values)) + "\n")
    marker.write_text(json.dumps(dict(schema_version=1, profile="serial_tapered_reaxff",
                                     regularization="none", local_minimization="none",
                                     mapping_verified="user_supplied", settings=settings), indent=2))
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    subprocess.run([str(Path(settings["executable"]).resolve())], cwd=root, env=environment, check=True)
    scores = []
    for path in root.glob("opti_log.out.*"):
        for line in path.read_text().splitlines():
            fields = line.split()
            if len(fields) == 2:
                try:
                    scores.append(number(fields[1]))
                except ValueError as error:
                    raise RuntimeError("Nonfinite Flocky fitness; inspect native run.log and engine diagnostics") from error
    if not scores or not list(root.glob("ffield.gbest.*")):
        raise RuntimeError("No finite optimization history/best-field evidence; inspect native logs")
    print(f"Flocky completed; {len(scores)} best-so-far checkpoints (not evaluation count)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
