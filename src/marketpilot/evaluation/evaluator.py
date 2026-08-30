"""Deterministic structural evaluator for Step 1."""

from marketpilot.domain.enums import RunStatus, TaskStatus
from marketpilot.domain.state import ResearchState
from marketpilot.evaluation.schemas import (
    EvaluationCheck,
    EvaluationMetrics,
    EvaluationResult,
)


class SystemEvaluator:
    """Evaluate system-level structural properties, not market truth."""

    def evaluate(self, state: ResearchState) -> EvaluationResult:
        checks: list[EvaluationCheck] = []

        run_completed = state.status is RunStatus.COMPLETED
        checks.append(
            EvaluationCheck(
                name="run_completed",
                passed=run_completed,
                details=f"run status={state.status.value}",
            )
        )

        unfinished = [
            task.task_id for task in state.tasks.values() if task.status is not TaskStatus.SUCCEEDED
        ]
        checks.append(
            EvaluationCheck(
                name="all_required_tasks_completed",
                passed=not unfinished,
                details=f"unfinished_task_count={len(unfinished)}",
            )
        )

        checks.append(
            EvaluationCheck(
                name="recommendation_exists",
                passed=bool(state.recommendations),
                details=f"recommendation_count={len(state.recommendations)}",
            )
        )

        recommendations_reference_findings = all(
            recommendation.findings for recommendation in state.recommendations.values()
        )
        checks.append(
            EvaluationCheck(
                name="recommendations_reference_findings",
                passed=recommendations_reference_findings,
                details=(
                    "all recommendations reference findings"
                    if recommendations_reference_findings
                    else "at least one recommendation has no findings"
                ),
            )
        )

        findings_reference_evidence = all(
            finding.evidence_ids for finding in state.findings.values()
        )
        checks.append(
            EvaluationCheck(
                name="findings_reference_evidence",
                passed=findings_reference_evidence,
                details=(
                    "all findings reference evidence"
                    if findings_reference_evidence
                    else "at least one finding has no evidence"
                ),
            )
        )

        missing_evidence: list[str] = []
        for finding in state.findings.values():
            missing_evidence.extend(
                str(evidence_id)
                for evidence_id in finding.evidence_ids
                if evidence_id not in state.evidence
            )
        for recommendation in state.recommendations.values():
            missing_evidence.extend(
                str(evidence_id)
                for evidence_id in recommendation.supporting_evidence
                if evidence_id not in state.evidence
            )
        checks.append(
            EvaluationCheck(
                name="no_missing_evidence_ids",
                passed=not missing_evidence,
                details=f"missing_evidence_count={len(missing_evidence)}",
            )
        )

        invalid_dag_state = any(
            task.status
            in {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.BLOCKED}
            for task in state.tasks.values()
        )
        checks.append(
            EvaluationCheck(
                name="no_invalid_dag_state",
                passed=not invalid_dag_state,
                details=f"invalid_dag_state={invalid_dag_state}",
            )
        )

        unsupported_recommendation = any(
            not recommendation.findings
            or not recommendation.supporting_evidence
            or not recommendation.risk_flags
            for recommendation in state.recommendations.values()
        )
        checks.append(
            EvaluationCheck(
                name="no_unsupported_recommendation",
                passed=not unsupported_recommendation,
                details=(
                    "all recommendations have findings, evidence, and risk flags"
                    if not unsupported_recommendation
                    else "at least one recommendation lacks required support"
                ),
            )
        )

        total_tasks = len(state.tasks)
        successful_tasks = sum(task.status is TaskStatus.SUCCEEDED for task in state.tasks.values())
        failed_tasks = sum(task.status is TaskStatus.FAILED for task in state.tasks.values())
        total_findings = len(state.findings)
        supported_findings = sum(
            bool(set(finding.evidence_ids) & set(state.evidence))
            for finding in state.findings.values()
        )
        total_tool_calls = state.metrics.tool_calls
        failed_tool_calls = state.metrics.tool_failures
        recommendation_confidence = (
            sum(item.confidence for item in state.recommendations.values())
            / len(state.recommendations)
            if state.recommendations
            else 0.0
        )
        risk_violations = sum(
            flag.severity > state.goal.constraints.maximum_risk
            for flag in state.risk_flags.values()
        )

        metrics = EvaluationMetrics(
            task_success_rate=successful_tasks / total_tasks if total_tasks else 0.0,
            evidence_coverage=supported_findings / total_findings if total_findings else 1.0,
            unsupported_claim_rate=(
                1.0 - supported_findings / total_findings if total_findings else 0.0
            ),
            tool_success_rate=(
                (total_tool_calls - failed_tool_calls) / total_tool_calls
                if total_tool_calls
                else 1.0
            ),
            tool_calls_per_run=float(total_tool_calls),
            execution_latency_seconds=state.metrics.elapsed_seconds,
            cost_per_run=state.metrics.token_cost,
            retry_rate=failed_tasks / total_tasks if total_tasks else 0.0,
            recommendation_confidence=recommendation_confidence,
            risk_violation_rate=(
                risk_violations / len(state.risk_flags) if state.risk_flags else 0.0
            ),
            llm_call_count=state.metrics.llm_calls,
            llm_input_tokens=state.metrics.llm_input_tokens,
            llm_output_tokens=state.metrics.llm_output_tokens,
            llm_total_tokens=state.metrics.llm_total_tokens,
            llm_latency_ms=state.metrics.llm_latency_ms,
            llm_estimated_cost=state.metrics.llm_estimated_cost,
            llm_failed_calls=state.metrics.llm_failed_calls,
            llm_retry_count=state.metrics.llm_retry_count,
        )

        return EvaluationResult(
            run_id=state.run_id,
            passed=all(check.passed for check in checks),
            checks=checks,
            metrics=metrics,
        )
