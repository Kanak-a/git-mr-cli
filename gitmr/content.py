"""OpenAI-generated MR title and description."""

from openai import OpenAI


class ContentGenerationError(Exception):
    pass


SYSTEM_PROMPT = """\
You are an expert software engineer writing GitLab merge request content.
You follow Conventional Commits formatting strictly.
You write for a technical audience: no marketing language, no emojis, no filler phrases.
You use plain Markdown only — no HTML, no emoji, no decorative symbols.
You always use imperative mood in titles ("add feature", not "added feature").
"""

TITLE_FORMAT = """\
Title format: type(scope): short description

Allowed types: feat, fix, refactor, docs, test, ci, chore, perf, style
Scope: the module, component, or layer being changed (optional but preferred)
Description: imperative mood, lowercase, no period, max 72 chars total
"""

DESCRIPTION_TEMPLATE = """\
## Summary

## Changes made
-

## How to test
1.

## Checklist
- [ ] Code follows project style guide
- [ ] CI/CD pipeline passes
- [ ] Relevant tests added or updated
- [ ] Documentation updated if needed
"""


def _build_prompt(ctx):
    commit_lines = "\n".join(
        f"  - {c['message']} ({c['author']})" for c in ctx["commits"]
    ) or "  (no commits found)"
    file_lines = "\n".join(
        f"  - [{f['status']}] {f['path']}" for f in ctx["files"]
    ) or "  (no file changes found)"

    return f"""\
You are writing a merge request for the following change.

Branch: {ctx['source']} → {ctx['target']}

Commits:
{commit_lines}

Files changed:
{file_lines}

---

{TITLE_FORMAT}

Write the MR title following the format above.

Then write the MR description by filling in the template below.
Replace every comment with real content. Remove comments from the final output.
Do not add sections that are not in the template.
Do not use emojis or decorative symbols anywhere.
Use plain Markdown only.

Template:
{DESCRIPTION_TEMPLATE}

---

Respond in exactly this format — no preamble, no explanation:

TITLE: <title here>
DESCRIPTION:
<description here>
"""


def generate_content(ctx, api_key):
    if not api_key:
        raise ContentGenerationError("OPENAI_API_KEY is not set in .env")

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(ctx)},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise ContentGenerationError(f"OpenAI request failed: {e}") from e

    return _parse_response(response.choices[0].message.content.strip())


def _parse_response(raw):
    if "TITLE:" not in raw or "DESCRIPTION:" not in raw:
        raise ContentGenerationError(
            f"Model response missing TITLE:/DESCRIPTION: markers.\nRaw output:\n{raw}"
        )

    parts = raw.split("DESCRIPTION:", 1)
    title_line = parts[0].strip()
    description = parts[1].strip()
    title = title_line[len("TITLE:") :].strip() if title_line.startswith("TITLE:") else ""

    if not title:
        raise ContentGenerationError(
            f"Could not extract title from response.\nRaw output:\n{raw}"
        )
    return {"title": title, "description": description}
