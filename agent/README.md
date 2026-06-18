# Agent Instructions

This folder contains instructions, prompts, and handoff documents for AI coding agents.

Agent files define how Claude Code, Codex, or other implementation agents should consume the constitution, domain package, policies, tests, and implementation plan.

Agents may generate code only after the required domain artifacts are complete.

Agents must not invent business rules, permissions, lifecycle transitions, events, or invariants.

When required information is missing or ambiguous, the agent must stop and ask.
