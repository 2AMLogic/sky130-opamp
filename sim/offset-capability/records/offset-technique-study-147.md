# Offset-correction technique study: trim, chopping, auto-zero, consumer-side correction, 2026-10-11 (append-only; issue #147)

**Desk study. Zero new simulations.** Every number below is one of four kinds,
tagged in the text and in the table cells: **[M]** measured (committed record
named), **[C]** calculated here from labelled inputs, **[A]** assumed (with
the range varied), **[U]** unknown (missing input and experiment named).
No residual sigma in this record is measured. Nothing here is a closure or
compliance claim.

Preserved unchanged: the canonical design (`design/opamp_core.sch`,
`design/netlist/opamp_core.spice`, DR-013 grid-legal widths),
`spec/target-spec.md`, all existing evidence, and the **proposed** status of
DR-009 and DR-011. DR-009's 0.275 mV is used only as a yardstick. Adopting any
technique needs its own decision record and ratification act.

Predeclared plan, committed before this record:
[`offset-technique-plan-147.json`](offset-technique-plan-147.json) (budget: 0
simulation runs, 0 `klt sim` requests, 0 ngspice runs). Base commit `9a58178`.

## 0. Verdict (ranked)

| Rank | Option | Calculated residual sigma (partial, RSS) | vs 0.275 mV | Main blockers (all open) |
|---|---|---|---|---|
| 1 | Foreground digital trim, 8 bit, +-35 mV, injected at d1/d2 | **0.20 mV [C], partial** (quantisation, calibration noise, DAC mismatch, beta-term drift only) | 72 % of allocation; leaves 0.036 mV^2 (0.19 mV rms) for every unknown term | gain row margin (1.6 dB), PM margin (3.9 deg = ~76 fF at d2), rise-slew margin, trim storage [U], measured drift [U] |
| 2 | Nulling-path auto-zero (continuous main path, sampled correction) | **0.06 to 0.21 mV [C/A]** (kT/C, sampled noise, charge injection) | 21 % to 76 % | white-noise folding (2x to 5.7x floor [C]), charge injection [A], extra gain path, topology unproven |
| 3 | Chopping, stage-1 input and pair-drain choppers | **>= 7.74 mV [C]** (mirror unmodulated) | **28x over** | input switch headroom at 1.8 V [C]; ripple up to 26 mV equivalent [C]; mirror needs a topology change |
| 4 | Consumer-side correction | not bounded [U] | not gradable | observability, transfer gain, consumer common mode [U] |

**No option is shown to close the gap, and none is shown impossible.** Trim and
auto-zero are the only ones whose partial sums fit inside 0.275 mV; both fit by
a margin that the still-unquantified terms could consume. Chopping, as the
topology stands, is excluded by calculation (Section 4). Sizing alone needs
~280 to 580x matched area ([#144 record](campaign-20261010-sizing-feasibility.md),
exploratory); a trim DAC of ~0.9e3 um^2 matched gate area [C/A] is a smaller
order of magnitude, but it adds calibration, storage and verification scope.

**Bounded next experiment (not run here):** E2 of the plan, 400 exploratory
sample-runs on the fleet (the same 100 seeds at -40/125 C and 1.62/1.98 V,
paired against 27 C/1.8 V), because the trim ranking depends on one number
this study can only calculate: the drift of a once-trimmed offset (0.15 mV
[C], 30 % of the variance budget by itself). Stop rule: paired sigma >
0.19 mV kills single-point trim.

## 1. Baseline and grading basis

| Quantity | Value | Label | Source |
|---|---|---|---|
| Open-loop Vos sigma, tt/27 C/1.8 V, N = 300 | 8.583 mV (+-4.1 % 1 SE) | M | `campaign-20261009-offset-mc300.md`; DR-007 widths, historical for DR-013 (the grid snap is electrically invisible, #144 grid0 row) |
| Worst corner sigma | 8.69 mV (ss) | M | DR-009 table |
| abs(mean) + 3 sigma, worst | 26.59 mV | M | DR-009 |
| Sample extremes (tt) | -27.38 / +27.64 mV | M | same |
| Groups: pair / mirror / stage 2 / bias / Rz,Cc | 3.103 / 7.740 / 0.052 / 0.037 / 0.000 mV | M | `campaign-20261009-offset-attribution.md` |
| Variance share: pair / mirror | 13.8 % / 86.2 % | M | same |
| Systematic Vos (mismatch off) | +0.151 mV | M | capability probe |
| Required reduction | 8.583 / 0.275 = **31.2x** in sigma (974x in variance); 31.6x at ss | C | equations below |
| Allocation as variance | 0.275^2 = **0.0756 mV^2** | C | |
| Best sizing candidate (m4p2) | 2.34 mV, N = 100, tt only; PM 27 deg, fails | M (exploratory) | #144 record |

Notation: sigma_x is a standard deviation in mV, variances add in RSS, and all
residual terms are treated as independent (assumed; correlation not measured).
Consumer allocation 0.275 to 0.369 mV sigma is quoted from the spec's
Consumers section (which cites the `sky130-bandgap` offset budget, §3). That
external repository document was not re-read here; it is the spec's citation.

## 2. Equations used throughout

- Uniform quantisation of step D: sigma_q = D / sqrt(12).
- Trim current for an input-referred range R: I_trim = R * gm1. LSB current
  = D * gm1. gm1 = 83.4 uS, ID1 = 4.7155 uA [M, OP probe, tt/27 C].
- Gaussian coverage of a +-R range with sigma s: erf(R / (s*sqrt(2))).
- kT/C sampled noise: v = sqrt(k*T/C), T = 300.15 K, k = 1.380649e-23 J/K
  (Johnson 1928 / Nyquist 1928 thermal noise; also derived in Enz & Temes
  1996, §II).
- Sampled amplifier noise at bandwidth f_bw (one-pole): v^2 = S_w * (pi/2) * f_bw,
  S_w = (35.75 nV/rtHz)^2 [M, floor, tt/27 C, DR-007-width DUT].
- Pelgrom area law for the DAC unit (Pelgrom, Duinmaijer, Welbers 1989):
  sigma_VT = s_vt / sqrt(W*L), s_vt(nfet) = 3.356 mV*um [M, pinned PDK].
  Current mismatch of a unit: sigma_I/I = (gm/ID) * sigma_VT.
- Rule of three (Hanley & Lippman-Hand 1983): zero events in N trials bounds
  the event rate by 3/N at 95 %.

## 3. Trim

### 3.1 Mechanism (block level)

Foreground, per-die, once at power-up or test: close a calibration loop that
drives the open-loop output to 0.9 V (the Vos definition in
`bench/offset_dc.cir`), found by successive approximation over an N-bit code.
A binary-weighted, current-steering DAC injects +-I_trim into the
first-stage output pair (d1/d2). Because the injection point is after the
pair and the mirror, it corrects **all** stage-1 terms (pair 13.8 %, mirror
86.2 %) and, with the loop closed at the output, stage 2 and bias too. Trim
codes are held in registers (volatile, re-run at each power-up) or in
non-volatile storage [U: not established for the open flow; needs a check of
the pinned PDK/MPW offerings].

### 3.2 Range, resolution, codes

| Item | Value | Label |
|---|---|---|
| Range choice R | +-35 mV (about +-4 sigma_ss plus the 0.5 mV mean) | A |
| Gaussian out-of-range fraction at R = 35 mV | 5.6e-5 (R = 26.6 mV: 2.2e-3) | C |
| Rule-of-three bound from N = 300 with zero out-of-range | <= 1.0 % at 95 % | C |
| Observed max abs, tt | 27.6 mV, inside +-35 mV (+-26.6 would not have covered the ss extreme 27.9 mV) | M |
| Trim current for R = 35 mV | **2.92 uA = 62 % of ID1** | C |
| 7 / 8 / 9 bit step D | 0.547 / 0.273 / 0.137 mV | C |
| sigma_q (7 / 8 / 9 bit) | 0.158 / 0.079 / 0.039 mV | C |
| LSB current (8 bit) | 22.8 nA | C |

A finite observed tail is not a bound: the +-35 mV range is a Gaussian-model
choice, the 3/N bound shows that N = 300 cannot demonstrate better than 1 %
coverage, and demonstrating 1e-3 needs N >= 3000 [C].

The 62 % current ratio is a design concern in itself: the correction is not a
small perturbation of the first stage, so gm1 and the mirror current shift for
a trimmed die [U, sim needed]. A segmented or mirror-ratio trim, or a hybrid
with auto-zero (coarse range elsewhere) reduces it; not evaluated.

### 3.3 Residual variance worksheet (8 bit)

| Term | sigma (mV) | variance (mV^2) | Label and basis |
|---|---|---|---|
| Quantisation | 0.079 | 0.00623 | C, D/sqrt(12) |
| Calibration decision noise (unfiltered 70 uV rms integrated noise, 100 Hz to 1 MHz) | 0.070 | 0.00490 | C, input-referred noise [M, old DUT]; averaging N_avg would divide by sqrt(N_avg) |
| DAC mismatch (see 3.4) | 0.080 | 0.00640 | A, this is the design requirement, not a prediction |
| Drift of the beta-term over -40 to 125 C | 0.148 | 0.02190 | C, 3.5; partial |
| Systematic-offset shift over P, V, T | unknown | unknown | U, needs E1 |
| VT-mismatch tempco and `voff` term drift | unknown | unknown | U, needs E2 |
| Supply dependence of the trimmed offset | unknown | unknown | U, E2 (VDD arms) |
| Trim-switch leakage, charge injection, DAC reference drift | unknown | unknown | U |
| **Sum of quantified terms** | **0.199** | **0.0394** | C |
| Headroom left in 0.0756 | 0.190 rms | 0.0362 | C |

Reading: with only these terms the residual is 0.20 mV, 72 % of the
allocation. Zero correction leaves 8.58 mV; coarse 7-bit codes alone give
0.158 mV of quantisation, which with the other terms makes 0.24 mV, near the
limit; a bad calibration (decision noise at the full 70 uV with no averaging)
is already included. This is not a pass: four unknown terms have to share
0.036 mV^2.

### 3.4 DAC mismatch requirement (correction-circuit mismatch)

To hold sigma_DAC <= 0.08 mV at full scale the absolute current error must be
<= 0.08 mV * 83.4 uS = 6.7 nA [C]. With 255 unit cells of 22.8 nA, the error
adds as sqrt(255) times a unit error, so each unit needs sigma_I/I <= 1.83 %.
At an assumed gm/ID of 10 /V [A] this is sigma_VT <= 1.83 mV, so a unit needs
sqrt(W*L) >= 3.356/1.83 = 1.83 um, i.e. **3.4 um^2 per unit, ~860 um^2 of
unit gate area for 255 units** [C/A]. Compare the canonical matched gate area
17.25 um^2 and the 4800 to 10000 um^2 estimated by #144 for sizing; the DAC
is smaller than sizing but about 50x the canonical matched area. The DAC
mismatch is **not self-correcting**: it is a fixed random error beyond the
calibration loop only if the loop does not recalibrate with the DAC in place.
In a closed calibration loop the DAC's static error is corrected at the one
code that is chosen; what remains is the code-to-code non-monotonicity, so
the 0.08 mV is conservative [A]. Gate area excludes routing, switches,
dummies, calibration logic and storage (digital control: unknown, to be
replaced by a synthesised count; order 1e2 to 1e3 um^2 [A]).

### 3.5 Power

DAC static current: between 2.9 uA (mid-code, one polarity) and 5.8 uA
(full-scale span) [C], i.e. 5.3 to 10.5 uW at 1.8 V against 117.0 uW nominal
quiescent power [M, spec row] = **+4.5 % to +9 %**. Digital calibration is
foreground and idle after power-up; dynamic power ~0 [A].

### 3.6 Drift calculation (3.5)

The beta term of the hand calculation (`bin/pelgrom_handcalc.py`): pair
sqrt(2) * (ID/gm1) * sigma_b = 0.102 mV, mirror 0.801 * sqrt(2) * (ID/gm3) *
sigma_b = 0.436 mV, RSS 0.448 mV [C]. ID/gm scales with T in the moderate/weak
region, so over 27 to 125 C it rises by 398.15/300.15 - 1 = 33 %, giving
**0.146 mV** (over 27 to -40 C: 0.100 mV) [C]. Omitted: VT-mismatch tempco,
the `voff` term (the hand calc under-predicted the pair by 43 %, #107),
temperature-dependent systematic offset. This is a partial estimate, not a
bound. Process corners are **not** drift: a trimmed die sits at one corner;
the corner-to-corner Pearson 0.9989 to 0.9996 [M] shows the same draws shift
by only ~0.26 to 0.40 mV between corners (sigma*sqrt(2(1-rho))) [C], which a
per-die trim absorbs.

### 3.7 Effects on ratified rows (baseline [M] vs predicted [C/A] vs unknown)

| Row | Baseline (DR-013 canonical, worst point) | Predicted effect | Added verification |
|---|---|---|---|
| Gain >= 60 dB | 61.64 dB @ fs/125 [M] | A1 = gm1/(gds2+gds4); gds sum 1.699 uS [M]. A leg of 2.9 uA with an assumed gds/ID of 0.05 to 0.1 /V adds 0.15 to 0.29 uS, **-0.73 to -1.37 dB** [C/A]; margin is only 1.64 dB. Cascoded/segmented injection may reduce it [U] | AC gain at 15 PVT points, all codes at extremes |
| GBW ~16 MHz | 17.92 MHz @ ss/125 [M] | gm1 untouched in first order; 62 % current imbalance at the code extremes [U] | AC at code extremes |
| PM >= 60 | 63.94 deg @ sf/27 [M] | Margin 3.94 deg. #144 loading gives <= 0.052 deg/fF at d2 (upper bound) [C], so **added d2 capacitance must be <= ~76 fF** [C]. Eight binary leg switches (~1 to 2 fF each [A]) are inside it; a 255-unit non-switched array is not | AC PM per code, E4 |
| Slew, rise ~20 V/us, fall unmet | 19.88 rise, 11.03 fall @ ss/-40 [M] | trim current adds to or subtracts from the Cc charging current of the 9.44 uA tail [M]: **+-31 % at +-35 mV, +-5 % at the median die** (|Vos| = 0.674 sigma) [C]. Rise slew has ~0.6 % margin: this can fail it in one polarity [C] | transient slew at extremes of code, both edges |
| Swing (unmet today) | 0.948 Vpp @ ss/-40 [M] | output stage untouched; d2 DC shift at extreme codes [U] | DC swing per code |
| ICMR | upper edge 1.1686 V vs 1.024 V target [M] | trim current on the mirror devices raises Vsg3 by ~ I_trim/gm3 = 2.92 uA / 66.8 uS = **<= 44 mV** (small-signal bound) [C]; margin was 145 mV | ICMR bench with trimmed codes |
| Quiescent power ~128.7 uW | 131.92 uW @ ff/125 [M] | + 4.5 to 9 % [C] | power at all PVT |

Added verification beyond rows: calibration and startup (power-up sequence,
monotone search, failure/abort mode and a stuck code), clock/control
(foreground only; no clock in the signal path), temperature and supply drift
(E2), correction-circuit mismatch (3.4), code retention, and a count of
dies with codes at the range end (clip).

## 4. Chopping

### 4.1 Mechanism and correctable locations

Square-wave chopping at f_ch moves the amplifier's own offset to f_ch and
leaves the signal at DC. Only errors **between the input chopper and the
output chopper** are modulated. In this topology:

- The pair (XM1/XM2) sits between the input chopper (at the gates) and a
  chopper that swaps d1/d2. Pair offset (3.103 mV, 13.8 % of variance) is
  modulated.
- The mirror XM3/XM4 (7.740 mV, 86.2 %) sits **after** a drain-side chopper
  and drives a single-ended node (d2). A single-ended node cannot be chopped
  without a second differential signal, so the mirror offset stays as DC
  offset. Stage 2 (0.052 mV) and bias (0.037 mV) also remain.
- **Calculated residual, input chop + pair-drain chop: sqrt(7.740^2 +
  0.052^2 + 0.037^2) = 7.74 mV, 28.1x the 0.275 mV allocation** [C]. Even
  an ideal chopper cannot be better than this.

Modulating the mirror requires a topology change, for example swapping the
diode/mirror roles of XM3/XM4 each phase together with the output, or a
fully differential first stage. Neither is evaluated. [U]

### 4.2 Switch headroom at 1.8 V (key finding, calculated from committed OP data)

The input pair gate common mode is 0.9 V (ICMR window 0.888 to 1.024 V).

- NMOS switch, gate = 1.8 V, source = CM. Vth: 0.5716 V at Vsb = 0 (XMB1)
  and 0.6266 V at Vsb = 0.21 V (XM1) [M, OP probe]. Fitting a body factor
  gamma = 0.495 V^0.5 with 2phi = 0.8 V [A] gives Vth = 0.775 V at CM = 0.9 V
  (Vgs = 0.90, **Vov ~ 0.12 V**) and 0.798 V at CM = 1.024 V (Vgs = 0.776,
  **Vov ~ -0.02 V, off**) [C/A].
- PMOS switch, gate = 0 V, source = CM, bulk at VDD: |Vth| is 0.936 V even
  at Vsb = 0 [M, XM3] and larger with reverse bulk bias, while Vsg = 0.9 to
  1.02 V. It is **off to marginal** at every CM in the window [C/A].
- A transmission gate therefore has a dead zone around the CM. Boosting the
  clock above 1.8 V is not acceptable for standard 1.8 V devices, and the
  3.3 V flavour is allowed only by a decision record (project rule).
- Candidate fix: LVT NMOS switches (`nfet_01v8_lvt`, vth0 parameter 0.418 V
  [M, pinned PDK]); availability in this flow, layout and mask rules,
  mismatch (s_vt 5.456 mV*um [M]) and body-effect data [U] (E3).
- Drain-side switches at d1/d2 ~ 0.82 V: Vgs = 0.98 V, Vov ~ 0.2 V [C/A]
  usable with a standard NMOS.

### 4.3 Frequency, settling, ripple, noise

| Item | Value | Label |
|---|---|---|
| Flicker corner | 441.8 kHz | M (tt/27 C, DR-007-width DUT) |
| Chop frequency | 1 MHz (2.3x the corner); range 0.9 to 1.3 MHz | A |
| GBW (worst) / amplifier gain at f_ch | 17.92 MHz / 17.9 (25 dB) | M / C |
| Stage-1 time constant tau = 1/(2*pi*GBW) | 8.9 ns | C |
| Dead time to settle (5 tau) per transition | 44 ns, two per period | A |
| Signal-time loss | 2 * 44 ns * 1 MHz = 8.9 % -> effective GBW 16.3 MHz (target ~16, 102 %) | C |
| Input-referred noise, 100 Hz to 1 MHz | measured 70.1 uV rms; floor-only 35.75 nV/rtHz * sqrt(1 MHz) = **35.8 uV** after 1/f removal (-49 %) | M / C |
| White-noise aliasing | chopping multiplies by +-1, so white noise is not folded; amplifier is not sampled | C (Enz & Temes 1996) |
| Switch thermal noise (input gate series R = 1.5 kohm [A], two) | 5.0 nV/rtHz each; floor goes 35.75 -> 36.4 nV/rtHz (+1.9 %) | C |
| Output ripple | the modulated offset appears as a square wave at f_ch; with the pair only: 3 sigma = 9.3 mV input-referred, with all stage-1 terms modulated: 3 sigma = 26 mV (x gain at f_ch, 17.9 in open loop). Needs a notch/filter or ripple-reduction loop (Burt & Zhang 2006; Wu, Makinwa, Huijsing 2009) whose residual is [U] | C |
| Charge-injection DC residual | I_inj = dQ * f_ch; V = I_inj / gm1. dQ 0.03 to 3 fC [A] -> **0.4 to 36 uV** (1 MHz, gm1 83.4 uS) | C/A |
| Switch gate cap and clock | ~0.3 pF total, C*V^2*f -> ~1 uW + drivers 1 to 5 uW [A] = +1 to 5 % | C/A |
| Added cap at d1/d2 | ~25 to 50 fF per switch [A]; PM bound 76 fF at d2 | A / C |

A DC Vos crossing alone cannot establish switched-system residual offset,
ripple, noise folding or settling: a transient/PSS-like campaign with
ripple, noise and settling measurements is required, and `klt sim`
support for it is unverified [U].

Effect on rows: gain unchanged to first order (switch Ron in a 4.7 uA path,
~1.5 kohm * gds ~ negligible) [C]; GBW -9 % effective [C]; PM bounded by 76 fF
[C]; slew unchanged until the chopper fails to settle [U]; swing unchanged
[C]; **ICMR set by the switch headroom above, not by the amplifier** [C/A].

## 5. Auto-zero

### 5.1 Mechanism

The only variant that keeps a continuous output and covers the mirror is a
**nulling-path auto-zero**: an auxiliary differential pair whose current
output sums into d1/d2 and whose gate voltage is stored on a hold capacitor
C_h; in the zero phase the main amplifier's input offset is measured and the
nulling pair adjusts C_h so that the main path is nulled; during the signal
phase the main path stays connected. (Enz & Temes 1996 describe this class.)
Two other forms are rejected: a single amplifier with output-offset storage
has no valid output during the zero phase (a reference loop needs a continuous
output; [U] whether the bandgap tolerates it), and a ping-pong pair doubles
the amplifier (153 um^2 MOS gate area and 117 uW) [C].

### 5.2 Residual-error worksheet (C_h = 5 pF [A], range 1 to 10 pF)

| Term | Value | Label |
|---|---|---|
| kT/C on C_h: 1 / 2 / 5 / 10 pF | 64.4 / 45.5 / 28.8 / 20.4 uV | C |
| Sampled amplifier noise, bandwidth limited to 1 MHz (1/f cancelled) | 44.8 uV | C |
| Sampled amplifier noise, bandwidth = GBW (22.5 MHz tt) | 212 uV | C |
| Charge-injection step on C_h: dQ 0.1 to 1 fC [A] on 5 pF | 20 to 200 uV; scaled by gm_n/gm1 (nulling-pair transconductance ratio, assumed 1 as the worst case) | C/A |
| Hold droop: I_leak * t / C_h <= 20 uV with 5 pF and 1 pA at the hot corner needs t <= 100 us, so refresh >= 10 kHz | leakage of the pinned PDK switch and its T dependence: **unknown** | U |
| **Quantified residual, RSS** | **0.057 mV** (dQ = 0.1 fC) to **0.21 mV** (dQ = 1 fC) | C/A |

Variance 0.0033 to 0.043 mV^2 of 0.0756 mV^2 [C]. Zero correction leaves the
baseline; a hold capacitor smaller than 1 pF makes kT/C 64 uV alone; no nulling
authority (gm_n/gm1 << 1) leaves part of the offset uncorrected: the nulling
pair must be able to produce at least R * gm1 = 2.92 uA at +-35 mV [C]
(the same 62 % of ID1 as trim, 3.2). Because the nulling pair's range is tied
to its gm, a nulling pair with gm_n/gm1 = 0.1 makes the correction voltage
span 10x larger on C_h (up to +-350 mV equivalent), a storage-node headroom
issue [C/U].

### 5.3 Noise, folding, bandwidth

- Sampled white noise folds into the baseband: density rises to roughly
  S_w * (1 + pi * f_bw / f_s) (derived from sampled variance S_w * (pi/2)
  * f_bw spread over f_s/2; the Enz & Temes expression differs in detail
  and must be re-derived) [C/A]. With f_bw = 1 MHz: f_s = 1 MHz gives a
  baseband density of 72.8 nV/rtHz (2.0x the floor); f_s = 100 kHz gives
  204 nV/rtHz (5.7x). For comparison, the spec row proposes ~30 nV/rtHz and
  the measured floor is already 35.75 nV/rtHz [M].
- In a nulling-path topology the folded noise is that of the auxiliary
  path, attenuated by the path ratio; magnitude [U].
- 1/f noise is cancelled below ~f_s/2 (1/f corner 442 kHz): useful only if
  f_s >> 442 kHz [C]; at 100 kHz it is only partly cancelled [C].

### 5.4 Area, power, rows

Hold cap 5 pF in MIM (cap_mim_m3_1): at ~2 fF/um^2 [A, to verify in the
PDK] about 2500 um^2, much larger than any other item here [C/A]. Nulling
pair + switches + clock: a few hundred um^2 [A]. Power: a nulling pair at
10 % of the main pair current adds ~1 uA + clock, +1 to 3 % [A].

| Row | Predicted effect (all [A]/[U]) |
|---|---|
| Gain | nulling pair drains add gds at d1/d2; for a nulling pair at 10 % of ID1: ~0.05 uS of 1.7 uS, **-0.25 dB** [C/A] |
| GBW, PM | added d2/d1 capacitance bounded by 76 fF [C]; zero-phase transients disturb the signal [U] |
| Slew | nulling current must stay below the tail, otherwise it loads Cc like the trim current (3.7) [U] |
| Swing | none [C] |
| ICMR | none for a nulling path (the pair inputs are the main inputs) [C]; switch headroom for the zero phase at the nulling-pair inputs [U] |

Added verification: transient with periodic zeroing (clock feedthrough,
glitch energy into the loop), steady-state noise/ripple, startup (acquisition
time constant C_h / gm_n), hold-time vs temperature (leakage), clock/control
failure (stuck zero phase), mismatch of the nulling pair (second-order).

## 6. Consumer-side correction

- The spec's bandgap allocation is derived through a Kuijk offset gain of
  9.65 [as cited in `spec/target-spec.md`, Consumers section; external
  document not re-read here]. Output error sigma = 9.65 * input sigma:
  0.275 mV -> 2.65 mV; the measured 8.58 mV -> **82.8 mV** [C, if the 9.65
  transfer holds for this amplifier's offset]. A +-35 mV amplifier trim range
  would be +-338 mV at the consumer output [C].
- A consumer output trim corrects the **sum** of amplifier offset and the
  consumer's own error terms at one temperature, not the amplifier offset
  itself; the amplifier offset is not observable separately [C]. DR-009's
  unresolved open-loop vs closed-loop conversion therefore stays unresolved:
  our Vos is defined at CM 0.9 V and v(out) = 0.9 V open loop.
- Open questions that block any number [U], each with the data needed: (a)
  the consumer's amplifier input common mode vs this block's ICMR window
  0.888 to 1.024 V (a mismatch would be an integration question); (b) the
  consumer's calibration observability and available trim range; (c)
  whether the consumer tolerates a calibration or auto-zero phase; (d) the
  required transfer gain at the consumer's operating point. These are
  follow-up questions for the consumer team, not an assumption of
  integration readiness. No cross-repository edit is made.

## 7. Cross-technique comparison (cells marked)

| | Trim | Nulling auto-zero | Chopping | Consumer-side |
|---|---|---|---|---|
| Errors corrected | all, including mirror [C] | all stage-1 incl. mirror [C] | pair only; mirror/stage 2 stay [C] | sum with consumer terms [C] |
| Residual sigma (quantified terms) | 0.20 mV [C], partial | 0.06 to 0.21 mV [C/A] | >= 7.74 mV [C] | [U] |
| Area (gate/cap, excl. wiring) | ~860 um^2 DAC + ~1e2 to 1e3 digital [C/A] | ~2500 um^2 hold cap + few 100 [A] | tens of um^2 + clock [A] | none here [U] |
| Power | +4.5 to 9 % [C] | +1 to 3 % [A] | +1 to 5 % [A] | none here [U] |
| Noise | unchanged; cal. noise only [C] | white noise 2 to 5.7x [C/A] | 1/f removed, -49 % integrated [C] | unchanged [C] |
| Ripple | none | zeroing glitches [U] | up to 9 to 26 mV equivalent [C] | none |
| Gain row | -0.7 to -1.4 dB, margin 1.64 [C/A] | ~ -0.25 dB [C/A] | ~ 0 [C] | n/a |
| GBW / PM | ~0 / <= 76 fF [C] | ~0 / <= 76 fF [C] | -9 % / <= 76 fF [C] | n/a |
| Slew | +-31 % at range ends [C] | [U] | [U] | n/a |
| ICMR | -44 mV bound [C] | none [C] | switch-limited [C/A] | n/a |
| Needs | storage, DAC, calibration [U] | hold cap, clock, nulling pair [A] | topology change, filter [U] | consumer data [U] |

## 8. What would be needed next (not done here)

1. E1 and E2 of the plan (1 + 4 fleet requests, 415 units total): systematic
   Vos over PVT and the drift of the paired trimmed residual. These replace
   the 0.146 mV calculated drift. E3 (<= 6 single-corner checks, headroom)
   and E4 (3 AC units, PM per fF).
2. A schematic-level prototype of the trim path and a nulling pair, sized
   gm/ID first from the committed sweep
   (`sim/gm-id-characterization/records/20260909-062847-35a9d46`), with the
   injection nodes checked against the 76 fF PM budget.
3. Switched-system analyses (periodic steady state, noise and ripple
   measurements, settling): tool support in `klt sim` is unverified [U].
4. A non-volatile storage option check, switch leakage data, LVT availability.
5. Consumer data for 6.

## 9. Later validation protocol (any statistical closure claim)

- N >= 300 per process corner (tt, ss, ff, sf, fs), for each technique
  that reaches circuit level; paired seeds allowed but not independent.
- Temperature and supply coverage declared before the run (candidates:
  -40/27/125 C, 1.62/1.8/1.98 V), offset measured after calibration at the
  trim temperature and then across the grid.
- Report measured mean, sigma, 3 sigma and tails, failed samples (never
  counted as zero) and the number out of correction range.
- Switched-system measurements: input-referred noise spectrum, output
  ripple at f_ch / f_s, settling after each phase, startup/calibration time.
- The ratified rows (gain, GBW, PM, slew, swing, ICMR) re-run on the
  corrected netlist at the 15-point PVT grid.
- Any adoption: its own design decision record and ratification act. DR-009
  and DR-011 stay proposed until ratified by their own acts.

## 10. Limits

- The baseline sigma is from the DR-007-width DUT; no mismatch campaign
  exists on the DR-013 netlist (#144 grid0 shows the grid snap is
  electrically invisible, so reuse is reasonable but not proven).
- The noise record is a single corner on the DR-007-width DUT.
- Pelgrom coefficients are from the pinned PDK; the hand calculation
  under-predicted the pair by 43 %; the 0.146 mV drift uses only the beta
  term.
- All assumed numbers (f_ch, C_h, dQ, Ron, gds/ID, gm/ID of the DAC, 5-tau
  settling) are listed where used; none is a result.
- Only external sources: Enz & Temes 1996 (doi 10.1109/5.542410), Pelgrom
  et al. 1989 (10.1109/JSSC.1989.572629), Burt & Zhang 2006
  (10.1109/isscc.2006.1696188), Wu et al. 2009
  (10.1109/isscc.2009.4977438), Hanley & Lippman-Hand 1983
  (10.1001/jama.1983.03330370053031); bibliographic data checked against
  Crossref, article content not re-read for this desk study. Their circuits
  and measured residuals are not copied; relevance to this topology and 1.8 V
  was assessed through the headroom and location arguments above.
