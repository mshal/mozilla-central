#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    if sandbox.relativesrcdir == 'browser/devtools/sourceeditor':
        # This is the one sane directory
        return

    final_target = sandbox.get_string('FINAL_TARGET')

    print ": foreach *.jsm |> !cp |> %s/modules/devtools/%%b" % (final_target)

    subdir = sandbox.relativesrcdir.replace('browser/devtools', '')
    subdir = subdir.replace('toolkit/devtools', '')
    if subdir in (
        '', # Top-level browser/devtools/ or toolkit/devtools
        # browser/devtools
        '/framework',
        '/inspector',
        '/markupview',
        '/profiler',
        '/shared',
        '/styleinspector',
        '/tilt',
        '/webconsole',

        # toolkit/devtools
        '/server',
    ):
        print ": foreach *.js |> !cp |> %s/modules/devtools%s/%%b" % (final_target, subdir)
    if sandbox.relativesrcdir == 'browser/devtools/shared':
        print ": foreach widgets/*.jsm |> !cp |> %s/modules/devtools/%%b" % (final_target)
    elif sandbox.relativesrcdir == 'toolkit/devtools/server':
        print ": foreach actors/*.js |> !cp |> %s/modules/devtools/server/actors/%%b" % (final_target)
    elif sandbox.relativesrcdir == 'toolkit/devtools/webconsole':
        print ": foreach *.js |> !cp |> %s/modules/devtools/toolkit/webconsole/%%b" % (final_target)
