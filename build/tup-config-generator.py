#! /usr/bin/python -B

import sys
import os
import re

if len(sys.argv) < 4:
    sys.exit('usage: %s path/to/config.status path/to/nsprpub/autoconf.mk path/to/tup.config' % sys.argv[0])

config_status_path = sys.argv[1]
nsprpub_path = sys.argv[2]
tup_config_path = sys.argv[3]

sys.path.append(os.path.dirname(config_status_path))
from configstatus import defines, substs, non_global_defines

output = open(tup_config_path, 'w')

for name, value in defines:
    print >> output, "CONFIG_%s=%s" % (name, value)

for name, value in substs:
    # TODO: Expand $(FOO) and ${FOO} here?
    print >> output, "CONFIG_%s=%s" % (name, value)

for line in open(nsprpub_path, 'r'):
    m = re.match("([A-Z_]*)[ \t]*= *(.*)", line)
    if m:
        if m.group(1) in ['MDCPUCFG_H',
                          'PR_MD_CSRCS',
                          'PR_MD_ASFILES',
                          'PR_MD_ARCH_DIR',
                          'CPU_ARCH',
                          ]:
            print >> output, "CONFIG_%s=%s" % (m.group(1), m.group(2))
