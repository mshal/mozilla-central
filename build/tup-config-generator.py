#! /usr/bin/python -B

import sys
import os
import re

def set_config(name, value, setvals):
    if name not in setvals:
        setvals[name] = value
        print >> output, "CONFIG_%s=%s" % (name, value)

if len(sys.argv) < 5:
    sys.exit('usage: %s path/to/config.status path/to/js-config.status path/to/nsprpub/autoconf.mk path/to/tup.config' % sys.argv[0])

setvals = {}

config_status_path = sys.argv[1]
js_config_status_path = sys.argv[2]
nsprpub_path = sys.argv[3]
tup_config_path = sys.argv[4]

sys.path.append(os.path.dirname(config_status_path))
sys.path.append(os.path.dirname(js_config_status_path))
import configstatus

output = open(tup_config_path, 'w')

for name, value in configstatus.defines:
    set_config(name, value, setvals)

for name, value in configstatus.substs:
    # TODO: Expand $(FOO) and ${FOO} here?
    set_config(name, value, setvals)

for line in open(nsprpub_path, 'r'):
    m = re.match("([A-Z_]*)[ \t]*= *(.*)", line)
    if m:
        if m.group(1) in ['MDCPUCFG_H',
                          'PR_MD_CSRCS',
                          'PR_MD_ASFILES',
                          'PR_MD_ARCH_DIR',
                          'CPU_ARCH',
                          ]:
            set_config(m.group(1), m.group(2), setvals)

# Now from js/src/config.status
import jsconfigstatus
for name, value in jsconfigstatus.defines:
    set_config(name, value, setvals)

for name, value in jsconfigstatus.substs:
    # TODO: Expand $(FOO) and ${FOO} here?
    set_config(name, value, setvals)
