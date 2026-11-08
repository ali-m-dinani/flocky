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
requiring auxiliary files are rejected. Control settings are copied unchanged;
they must be compatible with Tapered ReaxFF. Native RNG seeding and exact restart
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
