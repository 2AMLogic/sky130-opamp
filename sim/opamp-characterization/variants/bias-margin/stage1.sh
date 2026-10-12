#!/usr/bin/env bash
# Stage 1 screen of PLAN.md: sequential fleet submissions (--fleet --backend batch), no local grid.
# usage: stage1.sh TAG   (ic090 | ic075 | ic060)
set -u
TAG=$1
cd "$(git rev-parse --show-toplevel)"
V=sim/opamp-characterization/variants/bias-margin/sink-$TAG.spice
PS="python3 sim/opamp-characterization/bin/pvt_sweep.py --fleet --backend batch --netlist $V --timeout-s 600"
$PS --corners tt --temps 27   --analyses ac,tran_sr,icmr,tran_sr_icmr
$PS --corners ss --temps -40  --analyses ac,tran_sr,icmr,tran_sr_icmr
$PS --corners fs --temps 125  --analyses ac
$PS --corners sf --temps 27   --analyses ac
$PS --corners ff --temps 125  --analyses ac
python3 sim/opamp-characterization/variants/sink_bias_margin.py static --tag "$TAG"
