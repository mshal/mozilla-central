#!/bin/sh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#
# A Bourne shell script for running the NIST HMAC Algorithm Validation Suite
#
# Before you run the script, set your PATH, LD_LIBRARY_PATH, ... environment
# variables appropriately so that the fipstest command and the NSPR and NSS
# shared libraries/DLLs are on the search path.  Then run this script in the
# directory where the REQUEST (.req) files reside.  The script generates the
# RESPONSE (.rsp) files in the same directory.
                               
hmac_requests="
HMAC.req
"

for request in $hmac_requests; do
    response=`echo $request | sed -e "s/req/rsp/"`
    echo $request $response
    fipstest hmac $request > $response
done

