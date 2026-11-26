#!/bin/bash
set -eu
if [[ $# -lt 5 || $# -gt 6 ]]; then
    echo "Usage: $0 netlist corner temp_c vdd_v vdd|vss [outfile]" >&2
    exit 2
fi
source "$(dirname "$0")/probe-common.sh"
vdd_ac=""
vss_ac=""
case $5 in
    vdd) vdd_ac="ac 1" ;;
    vss) vss_ac="ac 1" ;;
    *) echo "Expected vdd or vss, got $5" >&2; exit 2 ;;
esac

measurements=$(run_probe o0 d2 ib tl d1 cz <<D
* Unity-buffer supply coupling probe
.lib "$library" $corner
.option scale=1u
.temp $temp_c
.include "$netlist"
Vdd vdd 0 dc $vdd_v $vdd_ac
Vss vss 0 dc 0 $vss_ac
Iref vdd ibias dc 5u
Rdiv1 vdd inp 500k
Rdiv2 inp 0 500k
Cinp inp 0 1
Rshort inn out 1m
Cload out 0 2p
.control
ac dec 10 0.1 1k
meas ac o0 find vdb(out) at=0.1
meas ac d2 find vdb(d2) at=0.1
meas ac ib find vdb(ibias) at=0.1
meas ac tl find vdb(tail) at=0.1
meas ac d1 find vdb(d1) at=0.1
meas ac cz find vdb(cz) at=0.1
quit
.endc
.end
D
)
printf '%s\n' "$measurements"
if [[ $# -eq 6 ]]; then
    printf '%s\n' "$measurements" > "$6"
fi
