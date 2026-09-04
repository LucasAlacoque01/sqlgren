"""Compat: src.script.analyzer → src.core.analyzer."""

from src.core.analyzer import *  # noqa: F403
from src.core.analyzer import analyze_sql, heuristic_analyze, parse_sql, DIALECTS
