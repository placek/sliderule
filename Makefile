all: k-a-b-c-cf-ci-c-d-s-st-t.dxf k-a-b-c-cf-ci-c-d-s-st-t-linear.dxf

%.dxf: %.yaml
	./rule.py $< -o $@

clean:
	rm -f *.dxf

.PHONY: all clean
