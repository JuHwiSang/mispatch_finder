from __future__ import annotations

import json

from ..domain.models import AnalysisResult, Vulnerability
from ..domain.prompt import build_prompt
from ..ports import (
    LLMPort,
    LoggerPort,
    MCPServerPort,
    RepositoryPort,
    TokenGeneratorPort,
    VulnerabilityDataPort,
)
from .diff_service import DiffService
from .json_extractor import JsonExtractor


class AnalysisOrchestrator:
    """Orchestrates the complete analysis workflow.

    Coordinates between domain services and infrastructure adapters
    to perform vulnerability analysis.
    """

    def __init__(
        self,
        *,
        vuln_data: VulnerabilityDataPort,
        repo: RepositoryPort,
        mcp: MCPServerPort,
        llm: LLMPort,
        token_gen: TokenGeneratorPort,
        logger: LoggerPort,
        diff_service: DiffService,
        json_extractor: JsonExtractor,
    ) -> None:
        self._vuln_data = vuln_data
        self._repo = repo
        self._mcp = mcp
        self._llm = llm
        self._token_gen = token_gen
        self._logger = logger
        self._diff_service = diff_service
        self._json_extractor = json_extractor

    def analyze(self, *, ghsa: str, force_reclone: bool = False) -> AnalysisResult:
        """Execute complete analysis workflow for a GHSA.

        Args:
            ghsa: GHSA identifier
            force_reclone: Whether to force re-clone repository

        Returns:
            Analysis result
        """
        mcp_token = self._token_gen.generate()
        mcp_ctx = None

        try:
            # 1) Fetch GHSA metadata
            vuln = self._vuln_data.fetch_metadata(ghsa)
            self._logger.info(
                "ghsa_meta",
                type="ghsa_meta",
                ghsa=ghsa,
                vulnerability={
                    "repo_url": vuln.repository.url,
                    "commit": vuln.commit_hash,
                    "cve_id": vuln.cve_id,
                    "severity": vuln.severity,
                },
            )

            # 2) Prepare repositories
            current, previous = self._repo.prepare_workdirs(
                repo_url=vuln.repository.url,
                commit=vuln.commit_hash,
                force_reclone=force_reclone,
            )
            self._logger.info(
                "repos_prepared",
                type="repos_prepared",
                workdirs={
                    "current": str(current) if current else None,
                    "previous": str(previous) if previous else None,
                },
            )

            # 3) Generate diff
            base_worktree = current or previous
            diff_result = self._diff_service.generate_diff(
                workdir=base_worktree,
                commit=vuln.commit_hash,
            )
            self._logger.info(
                "diff_built",
                type="diff_built",
                full_len=diff_result.full_len,
                included_len=diff_result.included_len,
                truncated=diff_result.was_truncated,
            )

            # 4) Start MCP servers + tunnel
            mcp_ctx = self._mcp.start_servers(
                current_workdir=current,
                previous_workdir=previous,
                auth_token=mcp_token,
            )
            self._logger.info(
                "mcp_ready",
                type="mcp_ready",
                local_url=mcp_ctx.local_url,
                public_url=mcp_ctx.public_url,
                has_current=mcp_ctx.has_current,
                has_previous=mcp_ctx.has_previous,
            )

            # 5) Build prompt and call LLM
            prompt = build_prompt(
                ghsa=ghsa,
                repo_url=vuln.repository.url,
                commit=vuln.commit_hash,
                has_previous=mcp_ctx.has_previous,
                has_current=mcp_ctx.has_current,
                diff_text=diff_result.truncated_text,
            )

            raw_text = self._llm.call(
                prompt=prompt,
                mcp_url=mcp_ctx.public_url + '/mcp',
                mcp_token=mcp_token,
            )

            # 6) Extract JSON from LLM response
            extracted_json = self._json_extractor.extract(raw_text)

            # 7) Parse extracted JSON and populate result fields
            verdict = None
            severity = None
            rationale = None
            evidence = None
            poc_idea = None

            try:
                parsed = json.loads(extracted_json)
                if isinstance(parsed, dict):
                    # Map new field names (current_risk, patch_risk) to verdict/severity
                    current_risk = parsed.get("current_risk")
                    patch_risk = parsed.get("patch_risk")

                    # Verdict: use current_risk if available
                    if isinstance(current_risk, str):
                        verdict = current_risk

                    # Severity: use patch_risk if available
                    if isinstance(patch_risk, str):
                        severity = patch_risk

                    # Rationale: prefer 'reason', fallback to 'rationale'
                    reason = parsed.get("reason")
                    if isinstance(reason, str):
                        rationale = reason
                    elif isinstance(parsed.get("rationale"), str):
                        rationale = parsed.get("rationale")

                    # Evidence: handle both list and dict formats
                    ev = parsed.get("evidence")
                    if isinstance(ev, list):
                        evidence = ev
                    elif isinstance(ev, dict):
                        evidence = [ev]

                    # PoC: prefer 'poc', fallback to 'poc_idea'
                    poc = parsed.get("poc")
                    if isinstance(poc, str):
                        poc_idea = poc
                    elif isinstance(parsed.get("poc_idea"), str):
                        poc_idea = parsed.get("poc_idea")
            except json.JSONDecodeError:
                # If parsing fails, leave all fields as None
                pass

            # 8) Build result
            result = AnalysisResult(
                ghsa=ghsa,
                provider="",  # Will be filled from logs
                model="",  # Will be filled from logs
                verdict=verdict,
                severity=severity,
                rationale=rationale,
                evidence=evidence,
                poc_idea=poc_idea,
                raw_text=extracted_json,
            )

            # Log with dict representation for JSON serialization
            self._logger.info(
                "final_result",
                type="final_result",
                result={
                    "ghsa": result.ghsa,
                    "provider": result.provider,
                    "model": result.model,
                    "verdict": result.verdict,
                    "severity": result.severity,
                    "rationale": result.rationale,
                    "evidence": result.evidence,
                    "poc_idea": result.poc_idea,
                    "raw_text": result.raw_text,
                },
            )

            return result

        finally:
            if mcp_ctx is not None:
                try:
                    mcp_ctx.cleanup()
                except Exception:
                    self._logger.exception("mcp_cleanup_error")
