# Five-face solver engine

Vendored from hkociemba/RubiksCube-TwophaseSolverFiveFaces. See
`UPSTREAM_README.md` for the original documentation and `LICENSE` for GPLv3.

The robot application calls this engine through `../robot_solver.py`.
Upstream module names and core algorithm files are preserved. The standalone
GUI, socket server and examples are omitted because this application does not
use them. The example/server commands in the upstream README therefore do not
apply to this distribution.

Extensionless files are generated lookup tables, kept locally and ignored by
Git. Missing tables are generated when the solver is first imported. The
upstream README estimates 2–24 hours for generation, depending on hardware.
Existing tables from this project can be copied into this directory instead.
