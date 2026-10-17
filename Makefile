.PHONY: run test fmt seed migrate pair-master install up down mock-shore worker

# Forward common targets to edge/ so `make run` works from the repo root.

run test fmt seed migrate pair-master install up down mock-shore worker:
	$(MAKE) -C edge $@
