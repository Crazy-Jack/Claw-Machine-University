"""Pydantic schema for configuration."""

from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    """System-level configuration."""

    workspace_path: str = Field("./autolab_workspace", description="Path to workspace directory")
    loop_interval_seconds: float = Field(60.0, ge=1.0, description="Main loop interval")
    log_level: str = Field("INFO", description="Logging level")
    enable_heartbeat: bool = Field(True, description="Enable heartbeat logging")
    heartbeat_path: str = Field("workspace/state/heartbeat.txt", description="Heartbeat file path")
    max_state_history: int = Field(1000, ge=0, description="Max state history entries")


class PlannerConfig(BaseModel):
    """Planner configuration."""

    integration_mode: str = Field("tool", description="Integration mode: 'tool' or 'json'")
    max_actions_per_cycle: int = Field(5, ge=1, description="Max planner actions per cycle")
    max_new_experiments_per_cycle: int = Field(3, ge=1, description="Max new experiments per cycle")
    max_hypotheses_per_cycle: int = Field(2, ge=0, description="Max new hypotheses per cycle")
    context_history_limit: int = Field(20, ge=1, description="Max experiments in context")
    include_failures: bool = Field(True, description="Include failures in context")
    include_metrics: bool = Field(True, description="Include metrics in context")


class GPUConfig(BaseModel):
    """GPU worker configuration."""

    workers: list[dict] = Field(default_factory=list, description="List of worker configurations")
    default_ssh_key: str = Field("~/.ssh/id_ed25519", description="Default SSH key path")
    connection_timeout_seconds: int = Field(30, ge=1, description="SSH connection timeout")
    command_timeout_seconds: int = Field(300, ge=1, description="Default command timeout")
    heartbeat_interval_seconds: float = Field(300.0, ge=1.0, description="Worker heartbeat interval")


class ExecutorConfig(BaseModel):
    """Executor configuration."""

    max_concurrent_jobs: int = Field(2, ge=1, description="Max concurrent jobs across all workers")
    retry_transient_failures: bool = Field(True, description="Retry transient failures")
    stall_timeout_minutes: int = Field(30, ge=5, description="Timeout for stalled jobs")
    log_poll_interval_seconds: float = Field(10.0, ge=1.0, description="Log polling interval")
    enable_local_fallback: bool = Field(True, description="Enable local execution fallback")
    max_retries_per_job: int = Field(3, ge=0, description="Max retries per experiment")
    kill_on_stall: bool = Field(True, description="Kill stalled jobs automatically")


class PatchingConfig(BaseModel):
    """Patching configuration."""

    allow_code_patching: bool = Field(False, description="Allow code patching")
    allowed_config_paths: list[str] = Field(
        default_factory=list, description="Allowed config paths for patching"
    )
    allowed_code_files: list[str] = Field(
        default_factory=list, description="Allowed code files for patching"
    )
    require_git_snapshot: bool = Field(True, description="Require git snapshot before patching")
    validate_syntax: bool = Field(True, description="Validate Python syntax before patching")
    auto_rollback: bool = Field(True, description="Auto-rollback on patch failure")
    patch_backup_dir: str = Field("workspace/patches/backups", description="Patch backup directory")


class PoliciesConfig(BaseModel):
    """Policy constraints configuration."""

    protected_paths: list[str] = Field(
        default_factory=lambda: [".git", "secrets/", "ssh_keys/"],
        description="Protected paths that cannot be modified",
    )
    duplicate_experiment_check: bool = Field(True, description="Check for duplicate experiments")
    max_experiments_per_family: int = Field(100, ge=1, description="Max experiments per family")
    max_queue_size: int = Field(1000, ge=1, description="Max queue size")
    require_hypothesis: bool = Field(False, description="Require hypothesis for experiments")
    human_approval_required: bool = Field(False, description="Require human approval for actions")


class OpenClawConfig(BaseModel):
    """OpenClaw integration configuration."""

    anthropic_api_key: str | None = Field(None, description="Anthropic API key")
    model: str = Field("claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(4096, ge=1, description="Max tokens in response")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature parameter")
    skills_path: str = Field("autolab/openclaw/skills", description="Skills directory path")
    workspace_path: str = Field("autolab/openclaw_workspace", description="OpenClaw workspace path")
    enable_multi_agent: bool = Field(True, description="Enable multi-agent mode")


class ReportingConfig(BaseModel):
    """Reporting configuration."""

    reports_dir: str = Field("workspace/reports", description="Reports directory")
    cycle_report_interval: int = Field(10, ge=1, description="Cycles between periodic reports")
    include_plots: bool = Field(False, description="Include plots in reports (requires matplotlib)")
    markdown_template: str = Field("default", description="Markdown report template")
    json_export: bool = Field(True, description="Export JSON reports")
    retention_days: int = Field(30, ge=1, description="Report retention in days")
