#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    grepref_files = sandbox.get_string('grepref_files')
    flags = sandbox['PREF_PPFLAGS']
    flags.extend(sandbox['DEFINES'])
    flags.extend(sandbox['ACDEFINES'])
    flags.extend(sandbox['XULPPFLAGS'])
    flags_string = ' '.join(flags)
    print ": |> ^ Preprocessor -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %s > %%o |> $(DIST)/bin/greprefs.js" % (flags_string, grepref_files)
