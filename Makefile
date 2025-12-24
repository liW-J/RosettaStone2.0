export FLOW_HOME = $(shell pwd)/../../flow
export PLATFORM ?= asap7
export DESIGN_NAME ?= null
export CONTEST ?= ispd2005

include $(FLOW_HOME)/scripts/variables.mk

export BENCH_GEN_DIR = $(shell pwd)/benchGen
export BENCH_CONFIG_FILES = $(shell find $(BENCH_GEN_DIR)/config -name "*$(PLATFORM).json")

export ODB_COMM_DIR = $(shell pwd)/odbComm
export LEFDEF2ODB_CONFIG_FILES = $(shell find $(ODB_COMM_DIR)/config -name "$(CONTEST)*.json")

.PHONY: bench_gen_all
bench_gen_all:
	for cfg in $(BENCH_CONFIG_FILES); do \
		$(TIME_CMD) $(OPENROAD_CMD) -python $(BENCH_GEN_DIR)/convert_pdk.py $$cfg; \
	done

.PHONY: bench_gen_one
bench_gen_one:
	@test -n "$(JSON)" || (echo "Usage: make bench_gen_one JSON=./benchGen/config/xxx.json" && exit 1)
	$(TIME_CMD) $(OPENROAD_CMD) -python $(BENCH_GEN_DIR)/convert_pdk.py $(JSON)

.PHONY: lefdef2odb_all
lefdef2odb_all:
	for cfg in $(LEFDEF2ODB_CONFIG_FILES); do \
		$(TIME_CMD) $(OPENROAD_CMD) -python $(ODB_COMM_DIR)/convert_lefdef2odb.py $$cfg; \
	done

.PHONY: lefdef2odb_one
lefdef2odb_one:
	@test -n "$(JSON)" || (echo "Usage: make lefdef2odb_one JSON=./odbComm/config/xxx.json" && exit 1)
	$(TIME_CMD) $(OPENROAD_CMD) -python $(ODB_COMM_DIR)/convert_lefdef2odb.py $(JSON)
