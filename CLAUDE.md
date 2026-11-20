# GuitarPractice

## Model roles

Pinned in `.claude/settings.json`; this section overrides the "Model Roles"
section of `~/CLAUDE.md` for this project.

- **Fable 5.2** (`claude-fable-5-2`) is the primary agent: the session the
  user talks to. It owns master planning, orchestration, top-level decisions,
  and the final review of worker output.
- **Opus 5.5** (`claude-opus-5-5`) is the worker: every subagent (Explore,
  Plan, general-purpose, custom agents, Workflow `agent()` calls) runs on it
  via `CLAUDE_CODE_SUBAGENT_MODEL`.

## How work is split

The primary agent plans and delegates; workers do the hands-on work.

- **Research** (reading across the codebase, docs, the web): delegate to
  workers and keep only the conclusions.
- **Sub-plans**: the primary agent writes the master plan and hands each
  piece to a worker (Plan agent) to detail.
- **Execution** (coding, running commands, testing): delegate to workers,
  with a brief that states the goal, the files involved, the constraints,
  and how to verify the result.
- The primary agent checks what workers report before telling the user it is
  done, and does trivial one-step work (a single lookup or one-line edit)
  itself rather than spawning a worker for it.
- Do not pass a `model` override when spawning agents, and do not use
  `subagent_type: "fork"` for worker tasks: a fork runs on the primary model.

## What this project is

A personal guitar program in two halves, generated from one set of data files:

- **Practice packets** (print, no screen at the music stand): six levels, each
  with four 45-minute sessions (A chord day, B fretboard day, C song day,
  D mix-and-measure), chord/scale reference pages, song charts, a practice
  log and a check-in sheet. `python3 build.py pdf` writes them to `out/pdf/`.
- **Reading site** (phone, away from the guitar): theory chapters, chord and
  scale libraries, song studies. Deployed to GitHub Pages by
  `.github/workflows/pages.yml` on every push to `main`.

`AUTHORING.md` is the contract for all content: schemas, shortcodes, id
conventions, validation, build commands. Read it before editing data or
chapters. `python3 build.py` must pass before committing; `site/` and `out/`
are build output and are never committed. Python standard library only.

## How the program evolves

The program is meant to change as the player improves. Levels 1 and 2 are
finished; levels 3 to 6 are first drafts to be re-tuned on arrival.

When the player reports back (a filled-in check-in sheet, a photo of the
practice log, or just notes), do this:

1. Record the check-in in `progress/journal.md` (date, level, benchmark
   numbers, what felt bad, songs liked or disliked, real session length).
2. Revise the next level's JSON in `data/levels/` from it: carry weak chord
   pairs into the Session A primer, swap songs the player disliked for ones
   from `data/song-bench.json` or their mixes, adjust tempo targets.
3. Add any new chords, scales, songs or chapters the revision needs, rebuild,
   check the PDF packet page by page, commit and push.

Song picks come from the player's own mixes (`/Volumes/Music Drive/Mixes`,
one `.m3u8` per mix; the drive is usually unplugged) and their album index in
`~/iPodOS/Research/rerip-priority.csv`, plus the Beatles and Radiohead.
Never include lyrics; charts are chords and structure only. Keep personal
details (names, email, teacher) out of the site: the repository is public.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
