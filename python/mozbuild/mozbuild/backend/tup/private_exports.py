#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

def generate_rules(sandbox):
    exports = sandbox['PRIVATE_EXPORTS']
    module = sandbox.get_string('MODULE')
    # This is specific to security/nss
    for export in exports:
        print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/private/%s/%%b | $(MOZ_ROOT)/<installed-headers>" % (sandbox.vpath_resolve(export), module)
