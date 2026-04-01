known_dxf_files = k-a-b-c-cf-ci-c-d-s-st-t.dxf \
									k-a-b-c-cf-ci-c-d-s-st-t-linear.dxf \
									simple.dxf

all: $(known_dxf_files)

%.dxf: %.yaml
	./rule.py $< -o $@

clean:
	rm -f *.dxf

.PHONY: all clean
