# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

from . import (content_analysis, framework, grounded_theory,
               literature_synthesis, thematic)

METHODS = {
    m.id: m for m in (
        grounded_theory.METHOD,
        thematic.METHOD,
        content_analysis.METHOD,
        framework.METHOD,
        literature_synthesis.METHOD,
    )
}
