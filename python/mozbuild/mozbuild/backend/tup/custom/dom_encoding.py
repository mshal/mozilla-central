#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    print ": |> $(PYTHON) $(MOZ_ROOT)/intl/locale/src/props2arrays.py labelsencodings.properties %o |> labelsencodings.properties.h | $(MOZ_ROOT)/<generated-headers>"
