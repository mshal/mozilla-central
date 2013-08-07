#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    final_target = sandbox.get_string('FINAL_TARGET')
    for dirpath, dirnames, filenames in os.walk('source/lib'):
        if not filenames:
            continue
        output_subdir = dirpath.replace('source/lib', '')
        input_filenames = ['%s/%s' % (dirpath, f) for f in filenames]
        inputs = ' '.join(input_filenames)
        print ": foreach %s |> !cp |> %s/modules/commonjs%s/%%b" % (inputs, final_target, output_subdir)
