#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    if sandbox['MOZ_WIDGET_GTK']:
        final_target = sandbox.get_string('FINAL_TARGET')
        for i in [
            'default16.png',
            'default32.png',
            'default48.png',
        ]:
            print ": $(MOZ_ROOT)/<installed-icons> |> ^ INSTALL %%o^ cp %s %%o |> %s/chrome/icons/default/%s" % ('$(DIST)/branding/' + i, final_target, i)

        print ": $(MOZ_ROOT)/<installed-icons> |> ^ INSTALL %%o^ cp $(DIST)/branding/mozicon128.png %%o |> %s/icons/mozicon128.png" % (final_target)

    # This is weird - there is a LIBXUL_SDK ifdef that puts channel-prefs.js
    # into PREF_JS_EXPORTS, and an ifndef that adds it to a libs target. This
    # is just the libs target here, since PREF_JS_EXPORTS is handled elsewhere.
    if not sandbox['LIBXUL_SDK']:
        flags = sandbox.get_string('PREF_PP_FLAGS')
        flags += ' ' + sandbox.get_string('ACDEFINES')
        print ": |> ^ Preprocessor.py -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s profile/channel-prefs.js > %%o |> $(DIST)/bin/defaults/pref/channel-prefs.js" % (flags)
