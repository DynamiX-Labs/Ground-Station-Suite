# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Utilities for resolving and bootstrapping logging configuration files."""

import shutil
from pathlib import Path

DEFAULT_RUNTIME_LOG_CONFIG = Path("data/configs/log_config.yaml")
FALLBACK_RUNTIME_LOG_CONFIG = Path("backend/data/configs/log_config.yaml")
DEFAULT_TEMPLATE_LOG_CONFIG = Path("logconfigtemplate.yaml")
FALLBACK_TEMPLATE_LOG_CONFIG = Path("backend/logconfigtemplate.yaml")
LEGACY_DEFAULT_TEMPLATE_LOG_CONFIG = Path("logconfig.yaml")
LEGACY_FALLBACK_TEMPLATE_LOG_CONFIG = Path("backend/logconfig.yaml")


def _default_runtime_path() -> Path:
    if Path("data").is_dir():
        return DEFAULT_RUNTIME_LOG_CONFIG
    if Path("backend/data").is_dir():
        return FALLBACK_RUNTIME_LOG_CONFIG
    return DEFAULT_RUNTIME_LOG_CONFIG


def _default_template_path() -> Path:
    if DEFAULT_TEMPLATE_LOG_CONFIG.exists():
        return DEFAULT_TEMPLATE_LOG_CONFIG
    if FALLBACK_TEMPLATE_LOG_CONFIG.exists():
        return FALLBACK_TEMPLATE_LOG_CONFIG
    if LEGACY_DEFAULT_TEMPLATE_LOG_CONFIG.exists():
        return LEGACY_DEFAULT_TEMPLATE_LOG_CONFIG
    return LEGACY_FALLBACK_TEMPLATE_LOG_CONFIG


def _bootstrap_runtime_log_config(target_path: Path, template_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        return
    if not template_path.exists():
        raise FileNotFoundError(f"Log config template not found: {template_path}")
    shutil.copy2(template_path, target_path)


def resolve_log_config_path(config_path: str | None) -> Path:
    """
    Resolve the runtime logging config path.

    Runtime configuration lives in ``data/configs/log_config.yaml``.
    If that file is missing, it is copied from the template ``logconfigtemplate.yaml``.
    """
    runtime_default = _default_runtime_path()
    template_default = _default_template_path()

    if not config_path:
        _bootstrap_runtime_log_config(runtime_default, template_default)
        return runtime_default

    requested = Path(config_path)
    if requested.exists():
        return requested

    if requested.name == "logconfig.yaml":
        _bootstrap_runtime_log_config(runtime_default, template_default)
        return runtime_default

    if requested.name == "log_config.yaml":
        _bootstrap_runtime_log_config(requested, template_default)
        return requested

    raise FileNotFoundError(f"Log config not found: {requested}")
