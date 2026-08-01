"""Stable public API for Agent Loop Reflection V2."""

from agentloop.adaptive_strategy_v2 import AdaptiveStrategyV2
from agentloop.contracts_v2 import (
    ContractRegistryV2,
    TaskContractV2,
)
from agentloop.evaluation_boundary import (
    ArtifactVerifier,
    CandidateArtifact,
    EvaluationSpec,
    FunctionCaseSpec,
    RepositoryPatchArtifact,
    SourceCodeArtifact,
    TestCommandSpec,
    UnsupportedEvaluationBoundaryError,
    verify_artifact,
)
from agentloop.evaluation_v2_models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationSuite,
    EvaluationTask,
)
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.repair_replay_strategy_v2 import RepairReplayStrategyV2
from agentloop.repair_v2 import RepairContext
from agentloop.repair_workflow_v2 import EvidenceDrivenRepairWorkflow
from agentloop.repository_benchmark import (
    RepositoryBenchmarkDataset,
    RepositoryMutationReport,
    run_repository_mutation_matrix,
)
from agentloop.repository_verifier import (
    RepositoryFixture,
    RepositoryFixtureRegistry,
    RepositoryWorkspaceVerifier,
    repository_fingerprint,
)
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.suite_normalization import (
    NormalizedSuite,
    normalize_suite,
)

__all__ = [
    "AdaptiveStrategyV2",
    "ArtifactVerifier",
    "CandidateArtifact",
    "ContractRegistryV2",
    "EvaluationCase",
    "EvaluationDataset",
    "EvaluationSpec",
    "EvaluationSuite",
    "EvaluationTask",
    "EvidenceDrivenRepairWorkflow",
    "FunctionCaseSpec",
    "ManagedDockerSandboxV2",
    "NormalizedSuite",
    "RepairContext",
    "RepairReplayStrategyV2",
    "RepositoryBenchmarkDataset",
    "RepositoryFixture",
    "RepositoryFixtureRegistry",
    "RepositoryMutationReport",
    "RepositoryPatchArtifact",
    "RepositoryWorkspaceVerifier",
    "RoutingSuiteRegistry",
    "SourceCodeArtifact",
    "TaskContractV2",
    "TestCommandSpec",
    "UnsupportedEvaluationBoundaryError",
    "normalize_suite",
    "repository_fingerprint",
    "run_repository_mutation_matrix",
    "verify_artifact",
]
