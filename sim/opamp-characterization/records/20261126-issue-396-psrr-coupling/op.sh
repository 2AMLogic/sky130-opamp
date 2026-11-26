#!/bin/bash
NET=$1; C=$2; T=$3; V=$4
cat > op_$$.cir <<D
.lib "/home/ubuntu/.ciel/sky130A/libs.tech/ngspice/sky130.lib.spice" $C
.option scale=1u
.temp $T
.include "$NET"
Vdd vdd 0 dc $V
Vss vss 0 dc 0
Iref vdd ibias dc 5u
Rdiv1 vdd inp 500k
Rdiv2 inp 0 500k
Rshort inn out 1m
Cload out 0 2p
.control
op
print @m.xm6.msky130_fd_pr__pfet_01v8[id] @m.xm7.msky130_fd_pr__nfet_01v8[id] @m.xm5.msky130_fd_pr__nfet_01v8[id] v(out) v(d2) v(d1)
.endc
.end
D
ngspice -b op_$$.cir 2>&1 | grep -E "^@|^v\(|=" | head
