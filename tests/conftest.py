from agentloop.agents import TesterAgent

# Pytest treats imported classes beginning with "Test" as test containers.
TesterAgent.__test__ = False
