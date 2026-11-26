#!/bin/bash
# usage: run.sh netlist corner temp vdd railac(vdd|vss) outfile
NET=$1; C=$2; T=$3; V=$4; R=$5
ACV=""; ACS=""; [ $R = vdd ] && ACV="ac 1" || ACS="ac 1"
cat > deck_$$.cir <<D
.lib "/home/ubuntu/.ciel/sky130A/libs.tech/ngspice/sky130.lib.spice" $C
.option scale=1u
.temp $T
.include "$NET"
Vdd vdd 0 dc $V $ACV
Vss vss 0 dc 0 $ACS
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
.endc
.end
D
ngspice -b deck_$$.cir 2>&1 | grep -E "^(o0|d2|ib|tl|d1|cz) "
