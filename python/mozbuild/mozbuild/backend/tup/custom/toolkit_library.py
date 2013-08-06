#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    library_name = sandbox.get_string('LIBRARY_NAME')
    mozilla_version = sandbox.get_string('MOZILLA_VERSION')
    print ': |> $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py -DVERSION="%s%s" symverscript.in > %%o |> symverscript | $(MOZ_ROOT)/<generated-headers>' % (library_name, mozilla_version)

    final_target = sandbox.get_string('FINAL_TARGET')
    shared_library_name = '%s/%s%s%s' % (
        final_target,
        sandbox.get_string('DLL_PREFIX'),
        sandbox.get_string('SHARED_LIBRARY_NAME'),
        sandbox.get_string('DLL_SUFFIX'),
    )
    # TODO: Why are mozsqlite3/mozalloc needed, but nss3/ssl3/etc not?
    print ': | $(MOZ_ROOT)/<-lxul> $(MOZ_ROOT)/<-lmozsqlite3> $(MOZ_ROOT)/<-lmozalloc> |> $(PYTHON_PATH) -I$(MOZ_ROOT)/python/mozbuild dependentlibs.py %s -L %s | sed "s/.*\///" > %%o |> %s/dependentlibs.list' % (shared_library_name, final_target, final_target)
