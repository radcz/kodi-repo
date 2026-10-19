# -*- coding: utf-8 -*-
"""Ruční spuštění instalátoru (Doplňky -> Programy)."""
from resources.lib import installer

import sys

# RunScript(plugin.program.radcz.instalator,noask) = bez úvodního dotazu
installer.run(ask='noask' not in sys.argv[1:])
