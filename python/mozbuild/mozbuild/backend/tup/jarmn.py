#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import JarMaker

class TupJar(object):
    def __init__(self, final_target, flags, moz_root):
        self.final_target = final_target
        self.moz_root = moz_root

        cwd_parts = os.getcwd().split(os.path.sep)
        path_count = self.moz_root.count(os.path.sep) + 1
        self.relativesrcdir = os.path.join(*cwd_parts[-path_count:])

        # Hack to join flags with spaces in them into single elements in the
        # list. Normally this is handled by the shell.
        nextflag = ""
        self.flags = []
        for f in flags:
            flag_part = f.replace('@relativesrcdir@', self.relativesrcdir)
            flag_part = f.replace('-DAPP_LICENSE_BLOCK=/.',
                                  '-DAPP_LICENSE_BLOCK=' + os.getcwd())
            if nextflag:
                nextflag += ' ' + flag_part
            else:
                nextflag = flag_part
            if nextflag.count('"') % 2 == 0:
                self.flags.append(nextflag)
                nextflag = ""

    def generate_chrome_rules(self, extra_manifest_files):
        jm = JarMaker.JarMaker()
        p = jm.getCommandLineParser()
        (options, args) = p.parse_args(args=self.flags)
        jm.useChromeManifest = False
        jm.useJarfileManifest = False
        jm.outputFormat = 'list'
        jm.topsourcedir = self.moz_root
        jm.tupSupport = True

        jm.relativesrcdir = self.relativesrcdir
        jm.localedirs = options.l10n_src

        jm.makeJar('jar.mn', self.final_target)
        for extra_file in extra_manifest_files:
            jm.makeJar(extra_file, self.final_target)

        jarmaker = '$(PYTHON) $(MOZ_ROOT)/config/JarMaker.py'

        outputs = jm.getOutputs()
        for jarfile in outputs:
            jartarget = jarfile.replace(self.final_target + '/', '')
            (dirname, filename) = os.path.split(jarfile)
            print ": | $(MOZ_ROOT)/config/buildid |> ^ JarMaker.py jar.mn^ %s --tup-support --jarfile %s -j %s %s |> %s | %s/<%s>" % (jarmaker, jartarget, self.final_target, ' '.join(self.flags), ' '.join(outputs[jarfile]), dirname, filename)

def generate_rules(sandbox):
    # TODO
    extra_manifest_files = []

    xpi_name = sandbox.get_string('XPI_NAME')
    dist = sandbox.get_string('DIST')
    dist_subdir = sandbox.get_string('DIST_SUBDIR')
    if xpi_name:
        final_target = os.path.join(dist, 'xpi-stage', xpi_name)
    else:
        if dist_subdir:
            final_target = os.path.join(dist, 'bin', dist_subdir)
        else:
            final_target = os.path.join(dist, 'bin')
    jarmaker_flags = []
    # MAKE_JARS_FLAGS normally comes from config/config.mk
    jarmaker_flags.append('-t')
    jarmaker_flags.append(sandbox.get_string('topsrcdir'))
    jarmaker_flags.append('-f')
    jarmaker_flags.append(sandbox.get_string('MOZ_CHROME_FILE_FORMAT'))
    jarmaker_flags.append('--relativesrcdir=%s' % (sandbox.get_string('relativesrcdir')))

    jarmaker_flags.extend(sandbox['XULPPFLAGS'])
    jarmaker_flags.extend(sandbox['DEFINES'])
    jarmaker_flags.extend(sandbox['ACDEFINES'])
    jarmaker_flags.append('jar.mn')
    jarmaker_flags.extend(extra_manifest_files)
    tup_jar = TupJar(final_target, jarmaker_flags, sandbox.moz_root)
    tup_jar.generate_chrome_rules(extra_manifest_files)
