"""Named TrustGate robustness CLI.

This is a documented alias of the Dataset A failure simulator. It never reads
Dataset B and never estimates prevented harm.
"""

from __future__ import annotations

from predict_rx.robustness.failures import main


if __name__ == "__main__":
    main()
