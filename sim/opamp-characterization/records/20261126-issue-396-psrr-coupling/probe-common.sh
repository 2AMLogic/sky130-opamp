# shellcheck shell=bash
# Shared by run.sh and op.sh. The netlist is relative to the caller's directory.
netlist=$1
corner=$2
temp_c=$3
vdd_v=$4
library=${SKY130_LIB:-${PDK_ROOT:-$HOME/.ciel}/${PDK:-sky130A}/libs.tech/ngspice/sky130.lib.spice}
for path in "$netlist" "$library"; do
    if [[ ! -f "$path" || ! -r "$path" ]]; then
        echo "Cannot read probe input: $path" >&2
        exit 1
    fi
done

# Read a batch deck on stdin. ngspice can exit successfully on a failed measure.
run_probe() {
    local log
    if ! log=$(ngspice -b 2>&1); then
        printf '%s\n' "$log" >&2
        return 1
    fi
    awk -v names="$*" '
        BEGIN {
            n = split(names, keys)
            for (i = 1; i <= n; ++i) want[keys[i]] = 1
        }
        ($1 in want) && $2 == "=" && $3 ~ /^[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?$/ {
            result[$1] = $0
        }
        END {
            for (i = 1; i <= n; ++i) {
                if (!(keys[i] in result)) {
                    print "Missing numeric measurement: " keys[i] > "/dev/stderr"
                    exit 1
                }
            }
            for (i = 1; i <= n; ++i) print result[keys[i]]
        }
    ' <<< "$log"
}
