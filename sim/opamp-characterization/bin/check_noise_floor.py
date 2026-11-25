"""Reproduce DR-018's source breakdown from the November noise campaign.

Pass the campaign's SKY130A sky130.lib.spice. The CSV is written to stdout.
Requires ngspice 47. Run from any directory.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile


EXP = Path(__file__).resolve().parents[1]
RUN = "20261119-030444-02cc663-b6d61e"
SNAPSHOT = EXP / "netlist-snapshots" / f"{RUN}-psrr-noise"
# ngspice BSIM4 channel and internal resistance thermal terms, and resistor
# thermal noise. Exclude device totals to avoid counting their terms twice.
THERMAL = (".id", ".rd", ".rs", ".rg", ".rbps", ".rbpd", ".rbpb", ".rbsb", ".rbdb", "_thermal")
FLICKER = (".1overf", "_1overf")


def replay(row, lib, directory):
    # One additional quarter-decade above 10 MHz brackets endpoint minima.
    deck = directory / "check.cir"
    deck.write_text(f"""DR-018 source breakdown
.lib "{lib}" {row["corner"]}
.include "{SNAPSHOT / 'noise.spice'}"
.temp {row["temp_c"]}
.control
alter vdd={row["vdd_v"]}
set sqrnoise
noise v(out) Vinp dec 4 100k 17.78279410038923Meg 1
setplot noise1
set wr_vecnames
set wr_singlescale
set numdgt=15
wrdata spectrum.txt all
quit
.endc
.end
""")
    output = directory / "spectrum.txt"
    output.unlink(missing_ok=True)
    result = subprocess.run(["ngspice", "-n", "-b", deck], cwd=directory, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    if result.returncode or not output.exists():
        raise RuntimeError(f"{row['corner']} at {row['temp_c']} C: {result.stdout}")
    with output.open() as f:
        names = f.readline().split()
        return [dict(zip(names, map(float, line.split()), strict=True)) for line in f]


def compare(row, points):
    if len(points) != 10:
        raise ValueError(f"expected 9 search spots and 1 upper neighbor, got {len(points)}")
    for point in points:
        hz = point["frequency"]
        fleet_nv = float(row[f"en_nv_rthz@{hz:.4g}Hz"])
        nv = 1e9 * math.sqrt(point["inoise_spectrum"])
        if not math.isclose(nv, fleet_nv, rel_tol=5e-6):  # CSV prints six digits
            raise ValueError(f"{row['corner']} at {row['temp_c']} C, {hz:g} Hz: {nv} vs {fleet_nv}")
    index = min(range(9), key=lambda i: points[i]["inoise_spectrum"])
    if index == 0:
        raise ValueError("lower-edge minimum needs a lower neighbor")
    point = points[index]
    total = point["onoise_spectrum"]
    thermal = sum(v for name, v in point.items() if name.endswith(THERMAL))
    flicker = sum(v for name, v in point.items() if name.endswith(FLICKER))
    if not math.isclose(thermal + flicker, total, rel_tol=1e-6):
        raise ValueError("unaccounted source power in output noise spectrum")
    density = 1e9 * math.sqrt(point["inoise_spectrum"])
    thermal_nv = density * math.sqrt(thermal / total)
    neighbor_db = max(abs(10 * math.log10(p["inoise_spectrum"] / point["inoise_spectrum"]))
                      for p in (points[index - 1], points[index + 1]))
    return (row["corner"], row["temp_c"], row["vdd_v"], f'{point["frequency"]:.8g}',
            f"{density:.6f}", f"{thermal_nv:.6f}", f"{100 * flicker / total:.4f}",
            f"{20 * math.log10(density / thermal_nv):.5f}", f"{neighbor_db:.5f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_library", type=Path)
    lib = parser.parse_args().model_library.resolve()
    record = json.loads((EXP / "records" / f"{RUN}-psrr-noise.json").read_text())
    model_sha = record["benches"]["noise"]["backend_remote"]["runner_models_lib_sha256"]
    if hashlib.sha256(lib.read_bytes()).hexdigest() != model_sha:
        parser.error("model library hash differs from the November fleet run")
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("corner", "temp_c", "vdd_v", "selected_hz", "total_nv_rthz", "thermal_nv_rthz",
                     "flicker_pct_power", "total_over_thermal_db", "max_neighbor_delta_db"))
    with (EXP / "records" / f"{RUN}-noise.csv").open() as f, tempfile.TemporaryDirectory() as tmp:
        for row in csv.DictReader(f):
            writer.writerow(compare(row, replay(row, lib, Path(tmp))))


if __name__ == "__main__":
    main()
