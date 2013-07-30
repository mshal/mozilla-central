#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

def generate_exports(exports, namespace):
    for export in exports:
        print ": | $(MOZ_ROOT)/<generated-headers> |> ^ INSTALL %s^ cp %s %%o |> $(DIST)/include/%s/%s | $(MOZ_ROOT)/<installed-headers>" % (export, export, namespace, os.path.basename(export))

def generate_rules(sandbox):
    namespaces = sandbox['EXPORTS_NAMESPACES']
    for namespace in namespaces:
        generate_exports(sandbox['EXPORTS_%s' % (namespace)], namespace)
