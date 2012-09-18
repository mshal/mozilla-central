# -*- makefile -*-
# vim:set ts=8 sw=8 sts=8 noet:
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#

XPIDL_GEN_DIR ?= _xpidlgen
GARBAGE_DIRS  += $(XPIDL_GEN_DIR)

###########################################################################
## Defines
###########################################################################
ifndef INCLUDED_XPIDL_MK #{

ifdef SDK_XPIDLSRCS
_EXTRA_XPIDLSRCS := $(filter-out $(XPIDLSRCS),$(SDK_XPIDLSRCS))
XPIDLSRCS += $(_EXTRA_XPIDLSRCS)
endif


ifneq ($(XPIDLSRCS),) #{

export:: $(patsubst %.idl,$(XPIDL_GEN_DIR)/%.h, $(XPIDLSRCS))

ifndef XPIDL_MODULE
XPIDL_MODULE		= $(MODULE)
endif

ifeq ($(XPIDL_MODULE),) # we need $(XPIDL_MODULE) to make $(XPIDL_MODULE).xpt
export:: FORCE
	@echo
	@echo "*** Error processing XPIDLSRCS:"
	@echo "Please define MODULE or XPIDL_MODULE when defining XPIDLSRCS,"
	@echo "so we have a module name to use when creating MODULE.xpt."
	@echo; sleep 2; false
endif

# generate .h files from into $(XPIDL_GEN_DIR), then export to $(DIST)/include;
# warn against overriding existing .h file.

XPIDL_DEPS = \
  $(LIBXUL_DIST)/sdk/bin/header.py \
  $(LIBXUL_DIST)/sdk/bin/typelib.py \
  $(LIBXUL_DIST)/sdk/bin/xpidl.py \
  $(NULL)

xpidl-preqs = \
  $(call mkdir_deps,$(XPIDL_GEN_DIR)) \
  $(call mkdir_deps,$(MDDEPDIR)) \
  $(NULL)

$(XPIDL_GEN_DIR)/%.h: %.idl $(XPIDL_DEPS) $(xpidl-preqs)
	$(REPORT_BUILD)
	$(PYTHON_PATH) \
	  $(PLY_INCLUDE) \
	  $(LIBXUL_DIST)/sdk/bin/header.py $(XPIDL_FLAGS) $(_VPATH_SRCS) -d $(MDDEPDIR)/$(@F).pp -o $@
	@if test -n "$(findstring $*.h, $(EXPORTS))"; \
	  then echo "*** WARNING: file $*.h generated from $*.idl overrides $(srcdir)/$*.h"; else true; fi

# generate intermediate .xpt files into $(XPIDL_GEN_DIR), then link
# into $(XPIDL_MODULE).xpt and export it to $(FINAL_TARGET)/components.
$(XPIDL_GEN_DIR)/%.xpt: %.idl $(XPIDL_DEPS) $(xpidl-preqs)
	$(REPORT_BUILD)
	$(PYTHON_PATH) \
	  $(PLY_INCLUDE) \
	  -I$(topsrcdir)/xpcom/typelib/xpt/tools \
	  $(LIBXUL_DIST)/sdk/bin/typelib.py $(XPIDL_FLAGS) $(_VPATH_SRCS) -d $(MDDEPDIR)/$(@F).pp -o $@

# no need to link together if XPIDLSRCS contains only XPIDL_MODULE
ifneq ($(XPIDL_MODULE).idl,$(strip $(XPIDLSRCS)))
$(XPIDL_GEN_DIR)/$(XPIDL_MODULE).xpt: $(patsubst %.idl,$(XPIDL_GEN_DIR)/%.xpt,$(XPIDLSRCS)) $(GLOBAL_DEPS)
	$(XPIDL_LINK) $(XPIDL_GEN_DIR)/$(XPIDL_MODULE).xpt $(patsubst %.idl,$(XPIDL_GEN_DIR)/%.xpt,$(XPIDLSRCS))
endif # XPIDL_MODULE.xpt != XPIDLSRCS

ifndef NO_DIST_INSTALL
XPIDL_MODULE_FILES := $(XPIDL_GEN_DIR)/$(XPIDL_MODULE).xpt
XPIDL_MODULE_DEST := $(FINAL_TARGET)/components
INSTALL_TARGETS += XPIDL_MODULE

ifndef NO_INTERFACES_MANIFEST
libs:: $(call mkdir_deps,$(FINAL_TARGET)/components)
	@$(PYTHON) $(MOZILLA_DIR)/config/buildlist.py $(FINAL_TARGET)/components/interfaces.manifest "interfaces $(XPIDL_MODULE).xpt"
	@$(PYTHON) $(MOZILLA_DIR)/config/buildlist.py $(FINAL_TARGET)/chrome.manifest "manifest components/interfaces.manifest"
endif
endif

ifndef NO_DIST_INSTALL
XPIDL_HEADERS_FILES := $(patsubst %.idl,$(XPIDL_GEN_DIR)/%.h, $(XPIDLSRCS))
XPIDL_HEADERS_DEST := $(DIST)/include
XPIDL_HEADERS_TARGET := export
INSTALL_TARGETS += XPIDL_HEADERS

XPIDLSRCS_FILES := $(XPIDLSRCS)
XPIDLSRCS_DEST := $(IDL_DIR)
XPIDLSRCS_TARGET := export
INSTALL_TARGETS += XPIDLSRCS
endif
endif #} XPIDLSRCS

endif #} INCLUDED_XPIDL_MK


ifndef INCLUDED_XPIDL_MK #{
  INCLUDED_XPIDL_MK = 1
endif #}
