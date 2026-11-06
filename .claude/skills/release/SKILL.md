---
name: release
description: Create release candidates or final releases for this project. Use when the user invokes `/release rc` (published pre-release RC), `/release` (published final release), `/release draft rc` (draft pre-release RC), or `/release draft` (draft final release). Handles version detection, version assessment from commits, git tagging, pyproject.toml bumping, and GitHub release creation with a point-form changelog.
disable-model-invocation: true
---

# Release Skill

## Invocation
- `/release rc`: published pre-release (RC)
- `/release`: published final release
- `/release draft rc`: draft pre-release (RC)
- `/release draft`: draft final release

## Conventions
- Versions follow PEP 440, Python's version specification: `X.Y.Z` for a final release, `X.Y.ZrcN`
  for a release candidate.
- A tag is `v` followed by the version in `pyproject.toml`: `vX.Y.Z` or `vX.Y.ZrcN`.
- Annotated tags only: `git tag -a <tag> -m "<tag>"`
- Before tagging, bump `pyproject.toml` to the version being released and sync `uv.lock`, in a
  commit of its own.
- The `latest` tag tracks the newest final release: its own annotated tag, overwritten each final
  release, so its tagger and date record when it moved.  Only final releases move it; RCs never do.
- Version bump commits are titled `Bump version to <version>`, as in the history.

Every build reports its own version: the server reads it from package metadata and gives it to MCP
clients when they connect.  An RC whose `pyproject.toml` still held the previous release would be
indistinguishable from it.

## Preconditions

Both workflows tag a commit and publish it, so the branch must be in sync with the remote before
anything is tagged.  Check first, and abort if it is not:

```bash
git fetch origin
git rev-list --left-right --count origin/development...HEAD   # expect: 0	0
```

Anything other than `0	0` aborts the release.  Commits ahead of the remote mean tagging history
nobody else has; commits behind mean releasing without work already on the remote.  Say which side
is out of sync and stop.  Pushing or pulling on the user's behalf is their call, not the skill's.

The tests must pass on the commit being released.  CI runs them on Linux, macOS and Windows for
every push to `development`; check the latest run for `HEAD` before going further:

```bash
gh run list --branch development --commit "$(git rev-parse HEAD)" --json conclusion,status
```

A run that failed aborts the release.  A run still in progress means waiting for it.  Say which, and
stop until it has passed.

## Tag Queries
```bash
# Last tag of any kind
git -c versionsort.suffix=rc tag -l 'v[0-9]*' --sort=-version:refname | head -1

# Last final tag (no rc); grep is needed, since git tag -l patterns only include
git tag -l 'v[0-9]*' --sort=-version:refname | grep -v rc | head -1
```

Git's version sort compares the numbers within a tag numerically, so `v4.0.0rc10` sorts above
`v4.0.0rc2`.  By default it also places a release candidate above its own final release, so
`v4.0.0rc1` sorts above `v4.0.0`; the `versionsort.suffix` setting makes `rc` tags sort below the
final release they lead up to.  The last-final query filters RCs out, so its order is unaffected.

## Assessing the Version

Commits in this project do not use conventional-commit prefixes, so assess the change from what the
commits do, reading their messages and, where unclear, their diffs:

- Major: an incompatible change for users or clients.  Examples: a tool, resource URI, parameter or
  command-line option renamed, removed or changed in meaning; a supported Python version dropped; a
  data file from an older downloader no longer accepted.
- Minor: a new capability without breaking an existing one.  Examples: a new tool, resource,
  parameter, command-line option or search feature.
- Patch: everything else.  Examples: fixes, performance, platform support, documentation, and
  dependency updates.

Internal changes alone (tests, CI, refactoring) are a patch release if released at all.

## RC Release Workflow

1. Find the last final tag and the last tag of any kind, which is the last RC while an RC series is
   in progress
2. Get commits since last final: `git log <last-final>..HEAD --oneline`
3. Assess the version from the commits (see Assessing the Version)
4. Present proposed next tag and confirm with user:
   - If RC series already in progress (e.g. `v3.2.0rc3`): default is `v3.2.0rc4`; also show the
     assessed version in case the user wants to revise the version base
   - If starting fresh from a final tag: show all three options (`vX.Y.Zrc1` for patch, minor and
     major)
5. Get commits for changelog: `git log <last-rc-or-final>..HEAD --oneline` (incremental: since the
   last RC, or since the last final release if this is rc1)
6. Write point-form draft changelog (see Changelog Format below)
7. Show proposed tag + changelog, wait for user confirmation before executing
8. Set `version` in `pyproject.toml` to `X.Y.ZrcN` (no `v` prefix), then run `uv lock` to sync
   `uv.lock`
9. Commit only the version bump: `git add pyproject.toml uv.lock`, then commit
   `Bump version to X.Y.ZrcN`
10. Execute:
    ```bash
    # Publish the version-bump commit before tagging it
    git push origin development
    git tag -a <new-rc-tag> -m "<new-rc-tag>"
    git push origin <new-rc-tag>
    # Add --draft if invoked as `/release draft rc`
    gh release create <new-rc-tag> --prerelease [--draft] --title "<new-rc-tag>" --notes "<changelog>"
    ```
    The `latest` tag is not moved here.  It names the newest final release, never a pre-release.

## Final Release Workflow

1. Find the last final tag and the last tag of any kind
2. Check for a `pyproject.toml` / tag version mismatch:

   - Strip `v` from the last tag of any kind, and compare it to `version` in `pyproject.toml`; they
     should be equal
   - The last tag is the last RC when an RC series is in progress, and `pyproject.toml` then holds
     that RC's version; the bump below drops its `rcN` suffix
   - If they differ: tell user and ask how to proceed (use tag version as base, use the
     `pyproject.toml` version, or specify manually)
3. Get commits since last final: `git log <last-final>..HEAD --oneline`
4. Assess the version (see Assessing the Version); suggest it, and confirm with the user
5. Set `version` in `pyproject.toml` (no `v` prefix), then run `uv lock` to sync `uv.lock`
6. Commit only the version bump: `git add pyproject.toml uv.lock`, then commit
   `Bump version to X.Y.Z`
7. Write point-form draft changelog covering full range since last final (spans all RCs)
8. Show proposed tag + changelog, wait for user confirmation before executing
9. Execute:
   ```bash
   # Publish the version-bump commit before tagging it
   git push origin development
   git tag -a <new-final-tag> -m "<new-final-tag>"
   git push origin <new-final-tag>
   # Add --draft if invoked as `/release draft`
   gh release create <new-final-tag> [--draft] --title "<new-final-tag>" --notes "<changelog>"
   ```
10. Move the `latest` tag onto this release.  Final releases only: an RC never moves `latest`, and
    never reaches this step.  Skip it for `/release draft` as well: `latest` should name a published
    release, so move it once the draft is published instead.

    ```bash
    git tag -f -a latest -m "<new-final-tag>" <new-final-tag>^{}
    git push --force origin latest
    ```

    Force is required on both: the tag exists already, locally and on the remote.  Overwriting is
    the point: no previous `latest` is kept, so nothing is lost.

    The `^{}` is required: it peels the release tag to its commit.  Without it the new tag points at
    the release's tag object instead, nesting one annotated tag inside another.

    Giving `latest` its own object is what makes the move visible.  Its tagger date is the date the
    tag moved, not the date the release was tagged, so a `latest` trailing the newest release shows
    up as stale.  A bare `git tag -f latest <tag>` cannot record that: it creates no object, only a
    second ref onto the release's own tag.

    The README tells users to run the server from `@latest`, so a release that does not move it
    leaves every reader of the README on the previous version.

## Changelog Format

Point-form, describing what changed for users and clients, not restating commit subjects.  Leave out
internal changes such as tests, CI and refactoring, unless they are all there is.

Group the points under these level-three headings, in this order, leaving out empty ones.  The
GitHub release page shows the release's title at level two, so level-three sections read as part of
it.

- `### Breaking changes`: anything that needs users or clients to change what they do, including a
  change of behavior they must adapt to
- `### New`: new capabilities
- `### Fixed`: bugs fixed
- `### Performance`: faster or more efficient behavior
- `### Other`: documentation, dependency updates, and similar

Always end with the full changelog compare link:
`Full Changelog: https://github.com/richardkmichael/mcp-tailwindplus/compare/<from>...<to>`

If there are no user-facing changes, open with `No user-facing changes.` then list the internal
items:

```markdown
No user-facing changes.

- Run the tests on Linux, macOS and Windows in CI
- Simplify the cache build's internal helpers

Full Changelog: https://github.com/richardkmichael/mcp-tailwindplus/compare/v3.1.0rc1...v3.1.0rc2
```

If there are user-facing changes, use the headings:

```markdown
### Breaking changes

- Component resource URIs name each level of the component

### New

- Search components by code, to find the component code was copied from

### Fixed

- Build the cache on Windows

### Performance

- Build the cache in worker processes

### Other

- Upgrade fastmcp to 4.1.6

Full Changelog: https://github.com/richardkmichael/mcp-tailwindplus/compare/v3.0.0...v3.1.0
```
