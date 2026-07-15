# VECTOR — install fallback for users who don't use the Claude Code plugin system.
# Preferred install: /plugin marketplace add fedeglan/vector && /plugin install vector
# This Makefile copies commands + agents into ~/.claude/ so the commands resolve
# globally, and installs the Tier-2 runner.

CLAUDE_DIR ?= $(HOME)/.claude

.PHONY: help install uninstall runner test verify

help:
	@echo "make install    - copy commands + agents into $(CLAUDE_DIR)"
	@echo "make runner     - install the Tier-2 relay-runner (vector-run / vector-revert)"
	@echo "make test       - run the hook red-team batteries + the runner FSM spec"
	@echo "make verify     - test + report the method version"
	@echo "make uninstall  - remove VECTOR files from $(CLAUDE_DIR)"

install:
	@mkdir -p $(CLAUDE_DIR)/commands $(CLAUDE_DIR)/agents
	@cp -v src/commands/*.md $(CLAUDE_DIR)/commands/
	@cp -v agents/*.md       $(CLAUDE_DIR)/agents/
	@echo ""
	@echo "Commands installed to $(CLAUDE_DIR)/commands/."
	@echo "Note: the plugin install namespaces them as /vector:* — with this fallback"
	@echo "they resolve bare (/new-project, /run-phase, ...)."
	@echo "Next: /setup in Claude Code."

runner:
	@if [ -f src/orchestration/runner/pyproject.toml ]; then \
		pipx install ./src/orchestration/runner || pip install --user ./src/orchestration/runner; \
		echo "Runner installed. CLI: vector-run start|resume|status|halt"; \
	else \
		echo "Runner package missing (src/orchestration/runner/pyproject.toml). Reinstall VECTOR."; \
		exit 1; \
	fi

test:
	@echo "== Hook red-team, round 1 =="
	@cd src/orchestration/hooks/tests && python3 redteam.py
	@echo ""
	@echo "== Hook red-team, round 2 (adversarial) =="
	@cd src/orchestration/hooks/tests && python3 redteam2.py
	@echo ""
	@echo "== Hook red-team, round 3 (hardening regressions: absolute paths, compound installs, bare-dir deletes) =="
	@cd src/orchestration/hooks/tests && python3 redteam3.py
	@echo ""
	@echo "== CI nets red-team (coverage-ratchet + diff-based test-protection) =="
	@python3 src/orchestration/ci/tests/redteam_ci.py
	@echo ""
	@echo "== Runner FSM specification (the executable control-flow spec) =="
	@python3 src/orchestration/runner/tests/fsm_sim.py
	@echo ""
	@echo "== Runner live battery (real runner vs deterministic shims + red-team regressions) =="
	@cd src/orchestration/runner/tests && python3 test_fsm_live.py | tail -1

verify: test
	@echo ""
	@echo "method_version: $$(grep -m1 '\"version\"' .claude-plugin/plugin.json | cut -d'\"' -f4)"
	@echo "Gates hold on this machine."

uninstall:
	@rm -fv $(CLAUDE_DIR)/commands/*.md
	@rm -fv $(CLAUDE_DIR)/agents/*.md
	@echo "VECTOR removed from $(CLAUDE_DIR)."
