"""The agent runtime for Phase 1 (build-plan 1B): the sales agent running on the shop's own data.

Layers: ``llm`` builds the model (provider chosen by settings), ``tools`` are the tenant-scoped functions the model may
call (each passes the permission gate), ``executors`` run an approved action, ``runtime`` ties a chat turn together with
the kill switch, spend cap, tool-call cap and a redacted trace, and ``redact`` keeps personal data out of that trace.
"""
