CONVERT_CMD=pdflatex

CONVERT_OPTIONS=-file-line-error -halt-on-error

%.pdf: %.tex
	$(CONVERT_CMD) $(CONVERT_OPTIONS) $<

.PHONY: all clean

document = first_report


all = $(document).pdf
intermediate = $(document).aux *.log

all: $(all)

clean:
	$(RM) $(all) $(intermediate)

