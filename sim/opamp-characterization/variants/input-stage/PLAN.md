# Plan: input-stage candidates for the common-mode range (issue #359)

Committed **before any fleet request**. The only simulations so far are local
single-unit probes, not evidence records: the sizing tables below come from the
committed gm/ID CSV only (`input_stage_rebias.py sizing`), and ONE local `.op`
probe at TT/27 C / 1.8 V provides the operating point of the Pelgrom offset
hand calculation (`op-probe.out.txt`). Approval scope (issue #359): a bounded
screen of **at most two** input-stage candidates; no adoption, no target or
spec edit, no netlist/schematic/layout change, no full-compliance claim. The
canonical design (`design/`) is not touched.

## The two unmet rows this screen addresses (binding corner SS / -40 C / 1.62 V)

- **Output swing**: 0.254-1.203 V (0.948 Vpp) unity-buffer vs ratified
  ≈ 0.072-1.464 V (≈ 1.39 Vpp). Attribution #181: input-CM-limited on the high
  side at 15/15 points (M1/M2 drain headroom = the PMOS mirror's `Vsg`), on the
  low side at 11/15 (tail M5 triode); only the four 125 C low-side points are
  output-stage limited.
- **Fall slew**: 11.03 V/us vs ≈ 20 V/us (9.13 V/us at FS / -40 C / 1.62 V on
  the 45-point grid). Attribution #185: output-current limited at 14/15 points;
  the input-range share is the SS / -40 C corner only (+26 % inside the window).

## Hand-calculated ceilings, stated up front (issue requirement)

All numbers from the committed sweep `sim/gm-id-characterization/records/
20260909-062847-35a9d46-full-sweep.csv` (W = 2 um, |Vds| = 0.9 V, Vsb = 0;
body effect at the real source height makes the high-edge numbers optimistic;
`input_stage_rebias.py sizing` regenerates every line):

- At SS / -40 C the present pair already runs at Vov ≈ 46 mV and the tail at
  ≈ 33 mV; the low-edge floor with an NMOS pair is **Vth_n(SS/-40 C) =
  0.6669 V**. The ratified low edge (0.072 V) is **≥ 0.595 V structurally
  short** — no re-bias of the existing pair and tail can reach it.
- The high edge is `VDD − |Vsg(XM3)| + Vth2_eff`; with |Vth_p(SS/-40 C,
  L=0.3)| = **1.0652 V**, driving the mirror's |Vov| to zero caps the edge at
  **≈ 1.230 V** (Vth2_eff = 0.676 V implied by the measured 1.1686 V edge).
  The ratified high edge (1.464 V) is **≥ 0.234 V structurally short**.
- Therefore **no candidate screened here can close the swing row**; the screen
  measures how much of the gap moves and what it costs, and records the
  structural result.

## Candidate (a) `icmr-rebias` — the ONE fleet-screened candidate

Low-headroom re-bias of the input stage at **unchanged currents** (every bias
current, the quiescent-power budget, and all group ratio laws are preserved by
construction):

| Card group | Devices | DR-013 W (um) | New W (um) | gm/ID at TT/27 C |
|---|---|---|---|---|
| NMOS input pair, L = 1.2 | `XM1`, `XM2` | 6.030 | **14.470** | 17 → **20** |
| PMOS mirror group, L = 0.3 | `XM3`, `XM4`, `XM6` | 4.635 | **13.710** | 14 → **16** |

- Why the pair move: lower `Vgs(XM1)` extends the **low** edge. gm/ID 20 (not
  higher): at SS/-40 C it already lands at Vov ≈ 4 mV — 42 of the maximal 46 mV
  reachable — while gm/ID 22 would need a 6x-wide pair for 4 mV more.
- Why the mirror move: lower `|Vsg(XM3)|` raises `d1`/`d2` and extends the
  **high** edge (the 15/15 side). gm/ID 16 (weak inversion at TT): at SS/-40 C
  it lands at |Vov| ≈ 0 mV — the |Vth_p|-limited ceiling itself. `XM3:XM4:XM6`
  move as ONE width so the 1:1:10 ratio law holds and `I(XM6) = 50 uA` is
  preserved; `XM6`'s width change is the price of that law, not an output-stage
  redesign (its `|Vov|` also drops, which helps the output top side).
- Why the tail is NOT widened: `Vov(XM5)` at SS/-40 C is already ≈ 33 mV
  (≤ 33 mV left); the `XMB1:XM5:XM7` group move would drag the output sink
  `XM7` out of input-stage scope. Documented, deliberately not taken.
- Expected first-order moves at SS/-40 C / 1.62 V: ICMR low edge
  0.7168 → ≈ 0.70 V, high edge 1.1686 → ≈ 1.23 V; at FS/-40 C the low edge
  0.7388 → ≈ 0.697 V, which would cover the sky130-bandgap consumer point
  0.73 V (currently missed by 8.8 mV — a consumer requirement, not this row's
  target). Expected costs: drawn MOS gate area 153.2 → 206.1 um² (+34.7 %),
  gm1 +21 % (GBW up ~1.2x, PM to be measured), offset σ by Pelgrom hand calc
  7.30 → 4.02 mV (bigger pair/mirror area; still ≫ the proposed 0.275 mV
  allocation — not a closure), sub-|Vth| mirror at TT and hotter corners
  (matching and noise at DC unmeasured here).

## Candidate (b) complementary PMOS pair — REJECTED BY HAND, no fleet request

A PMOS pair assists only while `Vin < VDD − |Vth_p| − |Vov_p| − Vov_tailp` ≈
**0.49 V** at SS/-40 C/1.62 V; the NMOS pair needs `Vin > Vth_n + Vov_n +
Vov_M5` ≈ **0.73 V**. `Vth_n + |Vth_p| = 1.732 V > VDD = 1.62 V` at that
corner, so there is a dead zone ≈ [0.49, 0.73] where **neither pair
conducts**. The `dc_swing` extraction takes the contiguous run containing
mid-supply (0.81 V), whose low edge stays NMOS-limited: (b) **does not improve
the binding-corner swing row at all**. Its costs are real everywhere: a second
tail (power), an extra pair + tail in the offset budget (Pelgrom; the row is
already 23-32x over its proposed allocation), gm doubling in the overlap
region at nominal corners (GBW/PM spread), and DR-001's input-pair polarity
rule requires a superseding record even to propose. Per the curation guidance
("(b) only if its hand-calculated ceiling is worth a fleet run") it is not:
rejected before any fleet spend. (Its low-segment gain [≈0.1, 0.49] V is not
contiguous with mid-supply, so it cannot appear in this row's metric.)

## Fleet stage (single pass, no survivor expansion)

One DUT snapshot per record; `pvt_sweep.py --fleet --backend batch` (DR-006
solver settings; `capacity_wait_s = 600` is submitted with every request by
the harness, plus its built-in capacity retry):

1. **15-point paired grid** (5 corners x 3 temperatures, corner-paired
   supplies), analyses `ac,tran_sr,dc_swing,swing_fixcm,icmr,tran_sr_icmr`
   (the ac bench carries quiescent power per point):
   requests = ac(2) + tran_sr(1) + dc_swing(1) + swing_fixcm(1) + icmr(5) +
   tran_sr_icmr(15) = **24 requests, 105 logical units**.
2. **Two added points** `SF/-40 C/1.62 V` and `FS/-40 C/1.62 V`
   (the 45-point worst cases for swing and fall slew):
   `--supply-mode cartesian --corners sf,fs --temps -40 --supplies 1.62`,
   same analyses = **9 requests, 14 units**.

Total first submissions ≤ **33 requests / 119 units**. Resubmission only of a
request that produced no measurements for an infrastructure reason (fleet
error, timeout, capacity refusal beyond the built-in wait): ≤ 1 per request,
≤ 8 in total (hard cap 41 requests). A measured outcome (unit fail,
non-convergence, railed output, low gain) is **never** retried. No local grid,
ever: if a submit still fails, the error is recorded in the report and the
affected claim stays unresolved.

## Baseline columns (committed records; the canonical is never re-run)

| Analysis | Baseline record | DUT |
|---|---|---|
| ac, tran_sr, dc_swing (paired 15) | `20261011-140526-04489d4-7e5893` | `e954d17d` (current canonical) |
| ac, tran_sr, dc_swing (the 2 added tuples) | `20261011-194651-046fe81-86146b` (45-pt cartesian) | `e954d17d` |
| icmr (paired 15) | `20261011-141126-04489d4-b4ac6f` | `e954d17d` |
| icmr (the 2 added tuples) | `20261011-200341-046fe81-f7ce78` (45-pt cartesian) | `e954d17d` |
| tran_sr, tran_sr_icmr (paired 15) | `20261011-201913-046fe81-7c5771` | `e954d17d` |
| swing_fixcm (paired 15) | `20261011-101231-39ac614-274895` (#181) | **`feb7cff4`** (pre-DR-013 widths; DR-013 measured the width move at ≤ 2.6e-5 Vpp swing, ≤ 0.003 V/us fall SR per point — disclosed, not hidden) |

`variants/compare.py` builds the per-row worst/binding-corner table (full-tuple
matching); a committed collation script extends it with the icmr/fixcm/sr-icmr
edge tables and the named-point callouts.

## Reporting rules (every row, every point, worse rows included)

- Per-row, per-candidate table at each ratified row's binding corner vs the
  DR-013 baseline: gain, GBW, PM, rise SR, fall SR (standard and ICMR-aware,
  never merged), ICMR window edges, unity-buffer swing, quiescent power.
- Unity-buffer swing and standard fall SR called out at SS/-40 C/1.62 V AND at
  the two added 1.62 V points.
- Verdict per candidate: closes / partially closes / does not close the swing
  row; how much of the fall-slew gap it recovers and at which corners; which
  ratified rows it breaks (any point outside a ratified bound is a break, and
  is reported however small).
- Drawn MOS gate area (per group and total) and the Pelgrom offset hand calc
  (stated as hand-calculated, not simulated).
- Every quoted number resolves to a committed fleet record (records.json maps
  them); simulator-free checks pass; `design/netlist/opamp_core.spice`,
  `spec/target-spec.md` and every ratified record unchanged.

## Expected outcome (from the ceilings above)

The honest expected result is a **negative structural finding**: the swing row
cannot be closed at SS/-40 C/1.62 V by any re-bias of this topology family —
the NMOS pair's `Vth_n` floors the low edge at ≈ 0.67 V and the PMOS mirror's
`|Vth_p|` caps the high edge at ≈ 1.23 V — plus a measured partial
improvement (`icmr-rebias` ≈ +0.06 V high / −0.04 V low at the binding
corner, ICMR window wider at every point, consumer 0.73 V point covered at
FS/-40 C) with gain/PM/GBW/power quantified. The decision record (next free
number, DR-015 as of `95d518f` — the curation comment's "after DR-018" does
not match the tree, re-derived per the re-verification rule) records this as
`proposed`; adoption is a separate ratification and is not sought here.
