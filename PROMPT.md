# Podscript: Supabase Auth + Z-Pay Payment Integration

## Context

You are implementing the 003-add-supabase-and-payment feature for Podscript, an audio/video transcription tool.

**Reference Documents** (read these first):
- `specs/003-add-supabase-and-payment/spec.md` - Feature specification
- `specs/003-add-supabase-and-payment/plan.md` - Implementation plan
- `specs/003-add-supabase-and-payment/data-model.md` - Database schema
- `specs/003-add-supabase-and-payment/tasks.md` - Complete task list
- `CLAUDE.md` - Project conventions

## Your Mission

Complete all unchecked tasks `- [ ]` in `specs/003-add-supabase-and-payment/tasks.md`.

**After completing each task:**
1. Mark it as done: `- [x]` in tasks.md
2. Run relevant tests to verify
3. Commit your changes with a descriptive message

## Current Phase

Check tasks.md for the current phase and complete tasks in order:
1. Phase 1: Setup (T001-T006)
2. Phase 2: Foundational (T007-T017) - BLOCKS all user stories
3. Phase 3: US1 & US2 Auth (T018-T033) - MVP
4. Phase 4: US3 & US4 Payment (T034-T052)
5. Phase 5: US5 Transcription Gating (T053-T070)
6. Phase 6: US6 History (T071-T079)
7. Phase 7: Polish (T080-T090)

## Rules

1. **Test-First**: Write tests before implementation when specified
2. **One task at a time**: Complete, test, commit, then move to next
3. **Parallel tasks [P]**: Can be done in any order within the same phase
4. **Dependencies**: Respect phase dependencies (see tasks.md)
5. **Coverage**: Maintain 80% test coverage

## Completion Criteria

The feature is COMPLETE when:
- All 90 tasks are marked `- [x]` in tasks.md
- All tests pass: `PYTHONPATH=./src pytest`
- Coverage >= 80%
- Manual end-to-end test passes (T090)

## Commands

```bash
# Run tests
PYTHONPATH=./src pytest --disable-warnings

# Run with coverage
PYTHONPATH=./src pytest --cov=src --cov-report=term-missing

# Start server for manual testing
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001 --reload
```

## START

Read tasks.md, find the first unchecked task `- [ ]`, and begin implementation.
