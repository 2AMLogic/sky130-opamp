#!/bin/bash
set -eu
if [[ $# -ne 4 ]]; then
    echo "Usage: $0 netlist corner temp_c vdd_v" >&2
    exit 2
fi
source "$(dirname "$0")/probe-common.sh"
vectors=('@m.xm6.msky130_fd_pr__pfet_01v8[id]' '@m.xm7.msky130_fd_pr__nfet_01v8[id]'
         '@m.xm5.msky130_fd_pr__nfet_01v8[id]' 'v(out)' 'v(d2)' 'v(d1)')
run_probe "${vectors[@]}" <<D
* Unity-buffer operating point
.lib "$library" $corner
.option scale=1u
.temp $temp_c
.include "$netlist"
Vdd vdd 0 dc $vdd_v
Vss vss 0 dc 0
Iref vdd ibias dc 5u
Rdiv1 vdd inp 500k
Rdiv2 inp 0 500k
Rshort inn out 1m
Cload out 0 2p
.control
op
print ${vectors[*]}
quit
.endc
.end
D
