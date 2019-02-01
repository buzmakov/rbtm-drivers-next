XIGEN = ${top_builddir}/xigen/src/xigen
XIGEN_DEP = ${top_builddir}/xigen/src/xigen.stamp

$(top_builddir)/wrappers/python/pyximc.py: ${top_srcdir}/libximc/src/protocol.xi $(top_srcdir)/wrappers/python/pyximc-template.py $(XIGEN_DEP) 
	$(XIGEN) --gen-python -w -x $(top_srcdir)/version -i $< -o $@ -t $(top_srcdir)/wrappers/python/pyximc-template.py

BUILT_SOURCES = $(top_builddir)/wrappers/python/pyximc.py

all-local: ${BUILT_SOURCES}

EXTRA_DIST = pyximc-template.py

CLEANFILES = $(top_builddir)/wrappers/python/pyximc.py
