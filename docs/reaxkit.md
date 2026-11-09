# ReaxKit external-runner integration

Upstream base: a472e3c. Flocky is a C++ RiPSOGM optimizer, not a Python package.
Its native engine is Tapered ReaxFF (`tapreaxff`), not AMS or JAX-ReaxFF.

## Licensing boundary

Flocky's C++ sources are GPL-3.0-or-later. The upstream repository also contains
Fortran sources with headers requesting that copies not be distributed and that
interested users contact Adri van Duin; the modifications identify David Furman.
The repository-wide GPL label does not resolve that conflict. Obtain appropriate
engine permission from the authors. No engine sources or binaries are added by
this integration, and ReaxKit neither imports nor bundles either component.

## Build and run

The Roar GCC 13.4/Boost 1.81 build exposed missing explicit Boost filesystem
stream declarations and dormant serial-path defects. The fork now includes the
stream header, guards MPI-only calls, removes an unmatched brace and duplicate
variable, assigns invalid serial fitness to infinity, and requires a charges
file only when fixed-charge mode is active. Local Cygwin GNU C++11 syntax checks
of both translation units pass with NLopt 2.4.2 headers; this is not a linked
build or engine test. Rebuild on Roar against its installed NLopt 2.7.1.

On Linux, provide a C++11 compiler, Boost filesystem/system and headers, and NLopt
with its C++ header. `make -f Makefile.reaxkit` builds `flocky_serial` without MPI.
Use CPPFLAGS/LDFLAGS for nonstandard dependency prefixes. This makefile is a
serial alternative to the upstream Makefile.serial, which invokes mpicxx and
names its output flocky_mpi despite not defining WITH_MPI.

Provide a separately authorized compatible `tapreaxff`. Its source Makefile.my
uses gfortran; compiler compatibility must be checked on the target machine.
Do not substitute AMS reaxff or the untapered standalone reac executable.

`python reaxkit_runner.py run-config.json --check-only` checks input files and
parameter bounds without running an engine. Remove --check-only only in a fresh
campaign. The runner uses Python's standard library only; Python 3.8+ suffices.

The initial profile is deliberately serial: one node/task/CPU, two swarm members,
two iterations, one cycle. Local minimization, regularization, uncertainty
quantification, and overfitting detection are disabled. Force/frequency targets
requiring auxiliary files are rejected. Control values are preserved while
keywords are aligned to column 9 and comments removed. Geometry atom records
declaring 3f10.5 or 3f15.10 coordinates are rendered as 3f15.10 for the engine.
Original inputs remain unchanged; already converted geometries are not widened
again. Unsupported formats, nonfinite coordinates, and values that cannot fit
without precision loss are rejected during --check-only as well as execution.
Other geometry records and atom prefix/suffix fields are preserved. Run
`python examples/reaxkit_geometry_check.py` for synthetic regression checks
without an engine. Native RNG seeding and exact restart
are not exposed. Nonzero child status or absent finite history is an error.

## Parameter map

The common six-column params file is NOT Flocky's params.mod. Supply an explicit
seven-column map via settings.params_mod:

```
absolute_line column section row parameter lower upper
```

Line and column are one-based token coordinates in the exact input ffield.
Section/row/parameter identify the corresponding common params entry. Bounds
must match the common input after its explicit bounds-order normalization.
The runner checks coverage, uniqueness, numeric coordinates and initial bounds.
It does not independently prove that a line/column corresponds to the annotated
section/row/parameter: manually verify the map. Do not reuse a map after changing
force-field formatting. Blank/comment rows are removed before native execution.

## Output semantics

`opti_log.out.<cycle>` contains iteration and current global-best fitness, not
each evaluation. Native output precision is scientific notation with ten decimal
places. `ffield.gbest.<cycle>.<iteration>.<particle>` files are parameter-only
checkpoints; `results.out.<cycle>` is an overwritten native prediction report.
Its candidate association is not reconstructed by ReaxKit. `log.flocky` preserves
native diagnostics. Cross-engine objectives and parity data remain unverified.

Local build/sample status and Roar gates are tracked in ReaxKit docs/FLOCKY.md.

## Cooperative serial time budget

Rebuild flocky_serial after updating. REAXKIT_OPTIMIZATION_TIME_LIMIT_SECONDS
sets a positive wall-clock budget; existing cycle/iteration limits still apply.
The serial loop checks between populations/generations, not inside an engine
evaluation. REAXKIT_STOP_FILE is an optional cooperative stop marker.
REAXKIT_TIMING_FILE selects the JSON phase/termination report (otherwise
optimization-timing.json). Existing best-field saves remain at improvements.
Native MPI timing is not implemented by this serial integration.

The standalone timer regression can be compiled from
examples/reaxkit_budget_check.cpp. Run it with
REAXKIT_OPTIMIZATION_TIME_LIMIT_SECONDS=0.05 and REAXKIT_TIMING_FILE pointing
to a disposable output file. It waits 100 ms, verifies expiration and writes
a graceful timing record. This does not validate the ReaxFF engine.

The Python runner permits a leading iteration-zero positive-infinity history
entry only when the same cycle subsequently contains finite checkpoints.
It preserves that entry in the native log and excludes it from the finite count.
Later nonfinite entries, malformed records, cycles without finite history, and
missing or empty best-field evidence still fail validation. This validation is
not a scientific correctness or restartability certification.
