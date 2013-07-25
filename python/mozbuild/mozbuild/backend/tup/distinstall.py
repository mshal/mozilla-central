#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_pp_rule(filename, defines, extra_flags, output_path):
    flags = ' '.join(defines)
    if(extra_flags):
        flags += ' ' + ' '.join(extra_flags)
    output_group = ""
    if filename.endswith('.manifest') and 'webapprt' not in output_path:
        output_group = "| $(MOZ_ROOT)/<installed-manifests>"
    print ": foreach %s | $(MOZ_ROOT)/<generated-headers> |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %%f > %%o |> %s/%%b %s" % (filename, flags, output_path, output_group)

def generate_install_rule(filename, output_path):
    output_group = ""
    if filename.endswith('.manifest') and 'webapprt' not in output_path:
        output_group = "| $(MOZ_ROOT)/<installed-manifests>"
    print ": foreach %s |> !cp |> %s/%%b %s" % (filename, output_path, output_group)

def generate_rules(sandbox):
    final_target = sandbox.get_string('FINAL_TARGET')
    defines = sandbox['DEFINES']
    defines.extend(sandbox['ACDEFINES'])

    component_dir = os.path.join(final_target, 'components')
    js_module_dir = sandbox.get_string('JS_MODULES_PATH')
    if not js_module_dir:
        js_module_dir = os.path.join(final_target, 'modules')

    extra_pp_components = sandbox['EXTRA_PP_COMPONENTS']
    extra_pp_components_flags = sandbox['EXTRA_PP_COMPONENTS_FLAGS']
    for component in extra_pp_components:
        generate_pp_rule(component, defines, extra_pp_components_flags, component_dir)

    pref_js_exports = sandbox['PREF_JS_EXPORTS']
    if sandbox['GRE_MODULE']:
        pref_dir = 'greprefs'
    elif sandbox['XPI_NAME'] or sandbox['LIBXUL_SDK'] or sandbox['MOZ_PHOENIX']:
        pref_dir = 'defaults/preferences'
    else:
        pref_dir = 'defaults/pref'
    pref_pp_flags = sandbox['PREF_PP_FLAGS']
    if sandbox['OS_ARCH'] == 'WINNT':
        # on win32, pref files need CRLF line endings... see bug 206029
        pref_pp_flags.append('--line-endings=crlf')
    for export in pref_js_exports:
        generate_pp_rule(export, defines, pref_pp_flags, os.path.join(final_target, pref_dir))

    extra_components = sandbox['EXTRA_COMPONENTS']
    for component in extra_components:
        generate_install_rule(component, component_dir)

    extra_js_modules = sandbox['EXTRA_JS_MODULES']
    for module in extra_js_modules:
        fullpath = sandbox.vpath_resolve(module)
        generate_install_rule(fullpath, js_module_dir)

    extra_pp_js_modules = sandbox['EXTRA_PP_JS_MODULES']
    for module in extra_pp_js_modules:
        generate_pp_rule(module, defines, [], js_module_dir)

    autocfg_js_exports = sandbox['AUTOCFG_JS_EXPORTS']
    autocfg_dest = os.path.join(final_target, 'defaults', 'autoconfig')
    for export in autocfg_js_exports:
        generate_install_rule(export, autocfg_dest)

    accessfu_files = sandbox['ACCESSFU_FILES']
    for export in accessfu_files:
        generate_install_rule(export, os.path.join(final_target,
                                                   'modules',
                                                   'accessibility'))
