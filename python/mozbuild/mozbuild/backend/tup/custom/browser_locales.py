#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    no_ja_jp_mac_ab_cd = sandbox.get_string('NO_JA_JP_MAC_AB_CD')
    final_target = sandbox.get_string('FINAL_TARGET')
    print ": |> $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py -I en-US/profile/bookmarks.inc -DAB_CD=%s generic/profile/bookmarks.html.in > %%o |> %s/defaults/profile/bookmarks.html" % (no_ja_jp_mac_ab_cd, final_target)

    profile_files = ' '.join(['generic/profile/%s' % f for f in sandbox['PROFILE_FILES']])
    print ": foreach %s |> !cp |> %s/defaults/profile/%%b" % (profile_files, final_target)

    profile_chrome = ' '.join(['en-US/profile/chrome/%s' % f for f in sandbox['PROFILE_CHROME']])
    print ": foreach %s |> !cp |> %s/defaults/profile/chrome/%%b" % (profile_chrome, final_target)
