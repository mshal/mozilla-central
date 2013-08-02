#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    perl = sandbox.get_string('PERL')
    nss_certdata = sandbox.get_string('NSS_CERTDATA_TXT')
    print ": |> %s certdata.perl < %s > %%o |> certdata.c" % (perl, nss_certdata)
