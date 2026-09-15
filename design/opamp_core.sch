v {xschem version=3.4.7 file_version=1.2
* opamp_core -- sky130-opamp two-stage Miller-compensated op-amp core
* (issue #13), implementing the topology fixed by
* spec/decision-records/DR-001-topology-and-cl.md at the device sizing
* proposed by spec/decision-records/DR-002-device-sizing.md (status
* "proposed" -- unverified in simulation, see "caveats" below).
*
* 1.8 V core devices only (sky130_fd_pr__nfet_01v8 / __pfet_01v8), per
* CLAUDE.md's "1.8 V primary; 3.3 V I/O-device flavor only via decision
* record". No I/O-flavor device appears anywhere in this schematic.
*
* Full per-device sizing derivation -- W, L, Id, gm/ID, and the literal
* sim/gm-id-characterization/records/20260909-062847-35a9d46-full-sweep.csv
* rows each width is computed from -- is in DR-002. Read that first; this
* header names the topology and the conclusions, it does not re-derive them.
*
* --------------------------------------------------------------- topology
* Stage 1 (differential transconductance stage, differential-to-single-ended):
*   M1, M2   nfet_01v8 input pair, sources tied together at "tail".
*            M1 gate = inn (inverting), M2 gate = inp (non-inverting) -- see
*            "polarity" below. M1 drain = d1 (mirror-reference side),
*            M2 drain = d2 (mirror-output side, drives stage 2).
*   M3, M4   pfet_01v8 simple (non-cascoded) current-mirror load, sources at
*            vdd. M3 diode-connected (gate = drain = d1); M4 mirrors it
*            (gate = d1, drain = d2). 1:1 ratio [DR-002].
*   M5       nfet_01v8 tail current source: drain = tail, gate = ibias,
*            source = vss. mult=2 unit devices, i.e. 2:1 from MB1.
*
* Stage 2 (Class-A output stage) and compensation:
*   M6       pfet_01v8 common-source gain device: source = vdd, gate = d2,
*            drain = out. mult=10 of the SAME unit device as M3/M4, at the
*            same channel length -- so its Vsg equals the mirror's at
*            balance and the stage-2 bias current is 10 x the stage-1 branch
*            current by construction (zero systematic offset, DR-002).
*   M7       nfet_01v8 output current sink: drain = out, gate = ibias,
*            source = vss. mult=10 of the SAME unit device as MB1/M5.
*   Rz, Cc   nulling-resistor Miller compensation from d2 to out
*            (DR-001 decision (d)): d2 - Rz - cz - Cc - out.
*            Rz = res_high_po_1p41 (2.00 kohm), Cc = cap_mim_m3_1 (0.50 pF).
*
* Bias:
*   MB1      nfet_01v8 diode-connected bias reference: gate = drain = ibias,
*            source = vss, fed by the external ibias pin (5 uA sunk into the
*            block). One unit device; M5 = 2 units (I_SS = 10 uA) and
*            M7 = 10 units (ID2 = 50 uA) mirror it at the SAME channel
*            length, so both ratios are set by device count alone.
*
* -------------------------------------------------------------- polarity
* Raise inp (M2 gate): M2 takes more of the fixed tail current and M1 takes
* less, so the M3 diode current falls and the M4 mirror sources less current
* into d2 while M2 sinks more out of it -- d2 falls. M6 is a PMOS with its
* source at vdd, so d2 falling raises its Vsg, M6 sources more current into
* out, and out rises. inp is therefore the NON-inverting input and inn the
* inverting one, which is the assignment wired below.
*
* --------------------------------------------------------------- caveats
* Nothing in this schematic has been simulated. Every operating point named
* in DR-002 is interpolated from the committed bare-device gm/ID sweep at
* |Vds| = 0.9 V and Vsb = 0, not from an operating-point solve of this
* circuit. See DR-002 "Open items" and the follow-on PVT/AC-bench issue.
*
* Pins: vdd, vss, inn, inp, out, ibias.
}
G {}
K {}
V {}
S {}
E {}

* M3: first-stage mirror reference (diode-connected), 1 unit PMOS, 5 uA
C {sky130_fd_pr/pfet_01v8.sym} -800 0 0 0 {name=M3
L=0.6
W=2.745
nf=1
mult=1
model=pfet_01v8
spiceprefix=X}
N -780 30 -760 10 {}
C {devices/lab_pin.sym} -760 10 0 0 {name=l1 lab=d1}
N -820 0 -840 0 {}
C {devices/lab_pin.sym} -840 0 0 0 {name=l2 lab=d1}
N -780 -30 -760 -10 {}
C {devices/lab_pin.sym} -760 -10 0 0 {name=l3 lab=vdd}
N -780 0 -760 0 {}
C {devices/lab_pin.sym} -760 0 0 0 {name=l4 lab=vdd}

* M4: first-stage mirror output, 1 unit PMOS (1:1 with M3), 5 uA
C {sky130_fd_pr/pfet_01v8.sym} -400 0 0 0 {name=M4
L=0.6
W=2.745
nf=1
mult=1
model=pfet_01v8
spiceprefix=X}
N -380 30 -360 10 {}
C {devices/lab_pin.sym} -360 10 0 0 {name=l5 lab=d2}
N -420 0 -440 0 {}
C {devices/lab_pin.sym} -440 0 0 0 {name=l6 lab=d1}
N -380 -30 -360 -10 {}
C {devices/lab_pin.sym} -360 -10 0 0 {name=l7 lab=vdd}
N -380 0 -360 0 {}
C {devices/lab_pin.sym} -360 0 0 0 {name=l8 lab=vdd}

* M1: NMOS input pair, inverting input, 5 uA
C {sky130_fd_pr/nfet_01v8.sym} -800 400 0 0 {name=M1
L=1.2
W=1.325
nf=1
mult=1
model=nfet_01v8
spiceprefix=X}
N -780 370 -760 350 {}
C {devices/lab_pin.sym} -760 350 0 0 {name=l9 lab=d1}
N -820 400 -840 400 {}
C {devices/lab_pin.sym} -840 400 0 0 {name=l10 lab=inn}
N -780 430 -760 450 {}
C {devices/lab_pin.sym} -760 450 0 0 {name=l11 lab=tail}
N -780 400 -760 400 {}
C {devices/lab_pin.sym} -760 400 0 0 {name=l12 lab=vss}

* M2: NMOS input pair, non-inverting input, 5 uA
C {sky130_fd_pr/nfet_01v8.sym} -400 400 0 0 {name=M2
L=1.2
W=1.325
nf=1
mult=1
model=nfet_01v8
spiceprefix=X}
N -380 370 -360 350 {}
C {devices/lab_pin.sym} -360 350 0 0 {name=l13 lab=d2}
N -420 400 -440 400 {}
C {devices/lab_pin.sym} -440 400 0 0 {name=l14 lab=inp}
N -380 430 -360 450 {}
C {devices/lab_pin.sym} -360 450 0 0 {name=l15 lab=tail}
N -380 400 -360 400 {}
C {devices/lab_pin.sym} -360 400 0 0 {name=l16 lab=vss}

* M5: tail current source, 2 unit NMOS (2:1 from MB1), I_SS = 10 uA
C {sky130_fd_pr/nfet_01v8.sym} -800 800 0 0 {name=M5
L=1.2
W=3.835
nf=1
mult=2
model=nfet_01v8
spiceprefix=X}
N -780 770 -760 750 {}
C {devices/lab_pin.sym} -760 750 0 0 {name=l17 lab=tail}
N -820 800 -840 800 {}
C {devices/lab_pin.sym} -840 800 0 0 {name=l18 lab=ibias}
N -780 830 -760 850 {}
C {devices/lab_pin.sym} -760 850 0 0 {name=l19 lab=vss}
N -780 800 -760 800 {}
C {devices/lab_pin.sym} -760 800 0 0 {name=l20 lab=vss}

* MB1: diode-connected bias reference, 1 unit NMOS, Iref = 5 uA
C {sky130_fd_pr/nfet_01v8.sym} -400 800 0 0 {name=MB1
L=1.2
W=3.835
nf=1
mult=1
model=nfet_01v8
spiceprefix=X}
N -380 770 -360 750 {}
C {devices/lab_pin.sym} -360 750 0 0 {name=l21 lab=ibias}
N -420 800 -440 800 {}
C {devices/lab_pin.sym} -440 800 0 0 {name=l22 lab=ibias}
N -380 830 -360 850 {}
C {devices/lab_pin.sym} -360 850 0 0 {name=l23 lab=vss}
N -380 800 -360 800 {}
C {devices/lab_pin.sym} -360 800 0 0 {name=l24 lab=vss}

* M6: Class-A common-source gain device, 10 unit PMOS (10:1 on M3/M4), ID2 = 50 uA
C {sky130_fd_pr/pfet_01v8.sym} 400 0 0 0 {name=M6
L=0.6
W=2.745
nf=1
mult=10
model=pfet_01v8
spiceprefix=X}
N 420 30 440 10 {}
C {devices/lab_pin.sym} 440 10 0 0 {name=l25 lab=out}
N 380 0 360 0 {}
C {devices/lab_pin.sym} 360 0 0 0 {name=l26 lab=d2}
N 420 -30 440 -10 {}
C {devices/lab_pin.sym} 440 -10 0 0 {name=l27 lab=vdd}
N 420 0 440 0 {}
C {devices/lab_pin.sym} 440 0 0 0 {name=l28 lab=vdd}

* M7: output current sink, 10 unit NMOS (10:1 from MB1), ID2 = 50 uA
C {sky130_fd_pr/nfet_01v8.sym} 400 400 0 0 {name=M7
L=1.2
W=3.835
nf=1
mult=10
model=nfet_01v8
spiceprefix=X}
N 420 370 440 350 {}
C {devices/lab_pin.sym} 440 350 0 0 {name=l29 lab=out}
N 380 400 360 400 {}
C {devices/lab_pin.sym} 360 400 0 0 {name=l30 lab=ibias}
N 420 430 440 450 {}
C {devices/lab_pin.sym} 440 450 0 0 {name=l31 lab=vss}
N 420 400 440 400 {}
C {devices/lab_pin.sym} 440 400 0 0 {name=l32 lab=vss}

* Rz: nulling resistor, 2.00 kohm = 1/gm2 [DR-001 (d), DR-002]
C {sky130_fd_pr/res_high_po_1p41.sym} 900 150 0 0 {name=Rz
L=7.585
model=res_high_po_1p41
spiceprefix=X
mult=1}
N 900 120 900 100 {}
C {devices/lab_pin.sym} 900 100 0 0 {name=l33 lab=d2}
N 900 180 900 200 {}
C {devices/lab_pin.sym} 900 200 0 0 {name=l34 lab=cz}
N 880 150 860 150 {}
C {devices/lab_pin.sym} 860 150 0 0 {name=l35 lab=vss}

* Cc: Miller compensation capacitor, 0.50 pF = 0.25 x CL [DR-001 appendix]
C {sky130_fd_pr/cap_mim_m3_1.sym} 900 350 0 0 {name=Cc
model=cap_mim_m3_1
W=15.62
L=15.62
MF=1
spiceprefix=X}
N 900 320 900 300 {}
C {devices/lab_pin.sym} 900 300 0 0 {name=l36 lab=cz}
N 900 380 900 400 {}
C {devices/lab_pin.sym} 900 400 0 0 {name=l37 lab=out}

* Block pins. Order here sets the .subckt terminal order:
* vdd vss inn inp out ibias -- same order the three-foundry twin
* sg13g2-opamp/design/opamp_core.sch uses, for comparability.
* They are placed top-to-bottom in that same order because
* xschem's own make_sym.awk orders symbol pins by y coordinate --
* keeping the two orders identical keeps opamp_core.sym's pin
* order equal to this schematic's .subckt terminal order.
C {devices/iopin.sym} -1200 -200 0 0 {name=p_vdd lab=vdd}
C {devices/iopin.sym} -1200 -100 0 0 {name=p_vss lab=vss}
C {devices/iopin.sym} -1200 0 0 0 {name=p_inn lab=inn}
C {devices/iopin.sym} -1200 100 0 0 {name=p_inp lab=inp}
C {devices/iopin.sym} -1200 200 0 0 {name=p_out lab=out}
C {devices/iopin.sym} -1200 300 0 0 {name=p_ibias lab=ibias}
