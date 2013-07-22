#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_exports(exports, namespace=""):
    strings = exports.get_strings()
    if namespace:
        namespace += '/'
    for export in strings:
        print ": foreach %s |> !cp |> $(DIST)/include/%s%%b | $(MOZ_ROOT)/<installed-headers>" % (export, namespace)

    children = exports.get_children()
    for subdir in sorted(children):
        generate_exports(children[subdir], namespace=namespace + subdir)

def generate_rules(sandbox):
    generate_exports(sandbox['EXPORTS'])
