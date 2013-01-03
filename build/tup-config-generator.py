#! /usr/bin/python -B

import sys
import os

if len(sys.argv) < 2:
    sys.exit('usage: %s path/to/config.status path/to/tup.config' % sys.argv[0])

config_status_path = sys.argv[1]
tup_config_path = sys.argv[2]

sys.path.append(os.path.dirname(config_status_path))
from configstatus import defines, substs, non_global_defines

output = open(tup_config_path, 'w')

for name, value in defines:
    print >> output, "CONFIG_%s=%s" % (name, value)

for name, value in substs:
    # TODO: Expand $(FOO) and ${FOO} here?
    print >> output, "CONFIG_%s=%s" % (name, value)
