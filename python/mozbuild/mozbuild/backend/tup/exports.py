#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

def generate_exports(exports, outputdir, namespace=""):
    strings = exports.get_strings()
    if namespace:
        namespace += '/'
    for export in strings:
        # Install the file from the srcdir if it exists, otherwise try to
        # install it from the objdir. Some files (eg: headers generated from
        # configure) are in the objdir.
        print ": | $(MOZ_ROOT)/<generated-headers> |> ^ INSTALL %s^ if [ -f %s ]; then cp %s %%o; else cp %s/%s %%o; fi |> $(DIST)/include/%s%s | $(MOZ_ROOT)/<installed-headers>" % (export, export, export, outputdir, export, namespace, os.path.basename(export))

    children = exports.get_children()
    for subdir in sorted(children):
        generate_exports(children[subdir], outputdir, namespace=namespace + subdir)

def generate_rules(sandbox):
    exports = sandbox['EXPORTS']
    if type(exports) == list:
        # This is specific to security/nss
        for export in exports:
            print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/include/nss/%%b | $(MOZ_ROOT)/<installed-headers>" % (export)
        for export in sandbox['PRIVATE_EXPORTS']:
            print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/private/nss/%%b | $(MOZ_ROOT)/<installed-headers>" % (export)
    else:
        generate_exports(exports, sandbox.outputdir)
