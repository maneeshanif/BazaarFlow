# Library Docs

Project-specific usage patterns for every third-party library in this project. This file covers how *we* use each library in {{PROJECT_NAME}} — rules, patterns and constraints specific to this project. It is not a substitute for the official docs.

---

## Before Using Any Library

1. **Check `AGENTS.md`** at the project root for installed skills.
2. **Fetch current API documentation** (Context7 MCP or the official docs) — library APIs change and training data goes stale. This is required, not optional, for any library question.
3. **Read this file** for project-specific patterns that override general library knowledge.

Order of authority:

```
Current official docs -> Skills via AGENTS.md -> This file (project rules) -> General knowledge
```

---

## Adding a library

When a task adopts a new library, add a section here **in the same PR** using this shape:

```
## <Library> (<package name>, <pinned version>)

Where it is configured: <file>
Project rules:
- <the pattern we always use>
- <the thing we never do, and why>
Gotchas found in this project:
- <symptom> -> <cause> -> <fix>
```

{{LIBRARY_SECTIONS}}
