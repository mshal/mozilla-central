#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    if sandbox['MOZ_APP_BASENAME']:
        flags = sandbox['DEFINES']
        flags.extend(sandbox['ACDEFINES'])
        flags_string = ' '.join(flags)
        print ": |> ^ Preprocessor.py -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s application.ini > %%o |> application.ini.gen" % (flags_string)
        if sandbox['MOZ_APP_STATIC_INI']:
            print ": application.ini.gen |> $(PYTHON) appini_header.py %f > %o |> application.ini.h | $(MOZ_ROOT)/<generated-headers>"
            print ": application.ini.h |> ^ INSTALL %%f^ cp %%f %%o |> %s/application.ini.h | $(MOZ_ROOT)/<installed-headers>" % (sandbox.outputdir)
