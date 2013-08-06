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
