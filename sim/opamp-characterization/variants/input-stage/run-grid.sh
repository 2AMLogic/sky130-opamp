#!/usr/bin/env bash
# Fleet stage of PLAN.md: sequential submissions (--fleet --backend batch), no local grid.
# The harness submits capacity_wait_s=600 with every request and applies its own
# capacity retry; a measured outcome is never retried (see PLAN.md caps).
set -u
cd "$(git rev-parse --show-toplevel)"
V=sim/opamp-characterization/variants/input-stage/icmr-rebias.spice
PS="python3 sim/opamp-characterization/bin/pvt_sweep.py --fleet --backend batch --netlist $V --timeout-s 600"
# 1) 15-point paired grid (5 corners x 3 temps, corner-paired supplies)
$PS --analyses ac,tran_sr,dc_swing,swing_fixcm,icmr,tran_sr_icmr
# 2) the two added points: SF/-40C/1.62V and FS/-40C/1.62V (45-point-grid worst cases)
$PS --supply-mode cartesian --corners sf,fs --temps -40 --supplies 1.62 \
    --analyses ac,tran_sr,dc_swing,swing_fixcm,icmr,tran_sr_icmr
