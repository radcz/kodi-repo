# -*- coding: utf-8 -*-
"""Po instalaci ze ZIPu se instalátor spustí sám (jen poprvé)."""
from resources.lib import installer

if not installer.already_done():
    installer.run(ask=True, first_run=True)
