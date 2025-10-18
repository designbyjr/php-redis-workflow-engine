#!/usr/bin/env python3
"""Convenience wrapper to launch the workflow worker and dashboard together."""

from orchestrator.cli import main


if __name__ == "__main__":
    main(["stack"])
