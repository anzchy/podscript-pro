# Tasks: 002-Add-Transcribe-History

**Input**: Design documents from `/specs/002-add-transcribe-history/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Tests**: Included as per constitution requirement (80% coverage)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in descriptions

## User Stories (from spec.md)

| Story | Priority | Description |
|-------|----------|-------------|
| US1 | P1 | 历史记录列表 - 首页显示最近记录，文件名可点击跳转 |
| US2 | P2 | 操作菜单 - 下载、复制链接、编辑标签、软删除 |
| US3 | P3 | 完整历史页 - 查看全部页面，分页功能 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and create base structure

- [x] T001 Install new dependencies: `pip install filelock jieba` and update requirements.txt
- [x] T002 [P] Add HistoryRecord, HistoryIndex Pydantic models in src/podscript_shared/models.py
- [x] T003 [P] Create keyword extraction module in src/podscript_shared/keywords.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core HistoryManager that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create HistoryManager class with file lock support in src/podscript_shared/history.py
- [x] T005 Implement HistoryManager.load() and HistoryManager.save() methods in src/podscript_shared/history.py
- [x] T006 Implement HistoryManager.add_record() method in src/podscript_shared/history.py
- [x] T007 Implement HistoryManager.get_record() method in src/podscript_shared/history.py
- [x] T008 Implement HistoryManager.update_record() method in src/podscript_shared/history.py
- [x] T009 Implement HistoryManager.delete_record() (soft delete) method in src/podscript_shared/history.py
- [x] T010 Implement HistoryManager.list_records() with pagination in src/podscript_shared/history.py
- [x] T011 Write unit tests for HistoryManager in tests/test_history.py
- [x] T012 Hook pipeline.py to save history on transcription completion in src/podscript_pipeline/pipeline.py

**Checkpoint**: Foundation ready - HistoryManager fully tested, pipeline integration complete

---

## Phase 3: User Story 1 - 历史记录列表 (Priority: P1) 🎯 MVP

**Goal**: 首页显示最近转写记录，文件名可点击跳转到结果页

**Independent Test**:
1. 完成一次转写任务
2. 刷新首页，应看到历史记录表格
3. 点击文件名，跳转到 result.html?task_id=xxx

### Tests for User Story 1

- [x] T013 [P] [US1] Write API test for GET /history endpoint in tests/test_api.py
- [x] T014 [P] [US1] Write API test for GET /history/{task_id} endpoint in tests/test_api.py

### Implementation for User Story 1

- [x] T015 [US1] Implement GET /history API endpoint in src/podscript_api/main.py
- [x] T016 [US1] Implement GET /history/{task_id} API endpoint in src/podscript_api/main.py
- [x] T017 [P] [US1] Add history section HTML structure in src/podscript_api/static/index.html
- [x] T018 [P] [US1] Create history.js module with loadHistory() function in src/podscript_api/static/history.js
- [x] T019 [US1] Implement renderHistoryTable() in src/podscript_api/static/history.js
- [x] T020 [US1] Implement onRecordClick() with auto mark-as-viewed in src/podscript_api/static/history.js
- [x] T021 [US1] Add new record red dot indicator styling in src/podscript_api/static/index.html
- [x] T022 [US1] Implement empty state display in src/podscript_api/static/history.js
- [x] T023 [US1] Integrate history.js into app.js page load in src/podscript_api/static/app.js

**Checkpoint**: 首页显示历史记录，点击可跳转到结果页

---

## Phase 4: User Story 2 - 操作菜单 (Priority: P2)

**Goal**: 表格行操作菜单：下载 SRT/MD、复制链接、编辑标签、软删除

**Independent Test**:
1. 点击操作列的 ⋯ 按钮
2. 测试下载 SRT、下载 MD、复制链接
3. 测试编辑标签并保存
4. 测试删除记录（二次确认后记录消失）

### Tests for User Story 2

- [x] T024 [P] [US2] Write API test for PATCH /history/{task_id} endpoint in tests/test_api.py
- [x] T025 [P] [US2] Write API test for DELETE /history/{task_id} endpoint in tests/test_api.py

### Implementation for User Story 2

- [x] T026 [US2] Implement PATCH /history/{task_id} API endpoint in src/podscript_api/main.py
- [x] T027 [US2] Implement DELETE /history/{task_id} API endpoint (soft delete) in src/podscript_api/main.py
- [x] T028 [US2] Implement showOperationMenu() dropdown in src/podscript_api/static/history.js
- [x] T029 [US2] Implement downloadSRT() and downloadMarkdown() functions in src/podscript_api/static/history.js
- [x] T030 [US2] Implement copyResultLink() function in src/podscript_api/static/history.js
- [x] T031 [US2] Implement editTags() modal dialog in src/podscript_api/static/history.js
- [x] T032 [US2] Implement deleteRecord() with confirmation dialog in src/podscript_api/static/history.js
- [x] T033 [US2] Add operation menu CSS styling in src/podscript_api/static/index.html

**Checkpoint**: 操作菜单所有功能可用，软删除生效

---

## Phase 5: User Story 3 - 完整历史页 (Priority: P3)

**Goal**: 独立的历史列表页面，支持分页浏览所有记录

**Independent Test**:
1. 点击首页"查看全部"链接
2. 跳转到 history.html 页面
3. 显示完整列表，可翻页

### Implementation for User Story 3

- [x] T034 [P] [US3] Create history.html page structure in src/podscript_api/static/history.html
- [x] T035 [US3] Implement full history table with pagination UI in src/podscript_api/static/history.html
- [x] T036 [US3] Add pagination controls (prev/next/page numbers) in src/podscript_api/static/history.js
- [x] T037 [US3] Implement loadFullHistory(page, limit) function in src/podscript_api/static/history.js
- [x] T038 [US3] Connect "查看全部" link to history.html in src/podscript_api/static/index.html
- [x] T039 [US3] Apply responsive styles for mobile in src/podscript_api/static/history.html

**Checkpoint**: 完整历史页面可用，分页正常工作

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Refinements affecting multiple user stories

- [x] T040 [P] Add keyword extraction on transcription completion in src/podscript_api/main.py
- [x] T041 [P] Download YouTube thumbnail on video tasks in src/podscript_pipeline/download.py
- [x] T042 Run full test suite (45 tests pass, history.py 100% coverage)
- [x] T043 [P] Update API documentation in docs/接口定义.md
- [ ] T044 Manual end-to-end test following quickstart.md validation steps
- [ ] T045 Deploy to cloud server and verify persistence

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────────────────────►
                                                                   │
Phase 2 (Foundational) ◄───────────────────────────────────────────┘
         │
         ▼ BLOCKS all user stories until complete
         │
         ├──► Phase 3 (US1: 历史列表) ──► MVP Release
         │
         ├──► Phase 4 (US2: 操作菜单)  ──► after US1 or parallel
         │
         └──► Phase 5 (US3: 完整页面)  ──► after US1 or parallel
                                          │
Phase 6 (Polish) ◄────────────────────────┘
```

### User Story Dependencies

- **US1 (历史列表)**: Depends on Phase 2 - No other story dependencies - **MVP CANDIDATE**
- **US2 (操作菜单)**: Depends on Phase 2 + US1 history.js module
- **US3 (完整页面)**: Depends on Phase 2 + US1 history.js module

### Within Each User Story

1. Tests written FIRST (if included)
2. API endpoints before frontend
3. Core display before interactions
4. Commit after each logical group

### Parallel Opportunities

**Phase 1**:
```
T002 (models.py) ║ T003 (keywords.py)
```

**Phase 3 (US1)**:
```
T013 (test GET /history) ║ T014 (test GET /history/{id})
T017 (index.html) ║ T018 (history.js)
```

**Phase 4 (US2)**:
```
T024 (test PATCH) ║ T025 (test DELETE)
```

---

## Parallel Example: User Story 1

```bash
# Launch tests in parallel:
Task: "Write API test for GET /history endpoint in tests/test_api.py"
Task: "Write API test for GET /history/{task_id} endpoint in tests/test_api.py"

# Launch HTML and JS creation in parallel:
Task: "Add history section HTML structure in src/podscript_api/static/index.html"
Task: "Create history.js module with loadHistory() function in src/podscript_api/static/history.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~15 min)
2. Complete Phase 2: Foundational (~1-2 hrs)
3. Complete Phase 3: US1 历史列表 (~1 hr)
4. **STOP and VALIDATE**: Test history display and click-to-navigate
5. Deploy MVP if ready

### Incremental Delivery

1. Setup + Foundational → Core ready
2. Add US1 → Test → Deploy (MVP!)
3. Add US2 → Test → Deploy (Operations)
4. Add US3 → Test → Deploy (Full History)
5. Polish → Final Release

---

## Task Summary

| Phase | Tasks | Parallel | Description |
|-------|-------|----------|-------------|
| Phase 1 | 3 | 2 | Setup & Dependencies |
| Phase 2 | 9 | 0 | HistoryManager Core |
| Phase 3 (US1) | 11 | 4 | 历史列表显示 |
| Phase 4 (US2) | 10 | 2 | 操作菜单 |
| Phase 5 (US3) | 6 | 1 | 完整历史页 |
| Phase 6 | 6 | 3 | Polish |
| **Total** | **45** | **12** | |

---

## Notes

- [P] tasks can run in parallel (different files)
- [US*] label maps task to user story for traceability
- MVP = Complete Phase 1-3 only
- Verify tests pass before moving to next phase
- Commit after each task or logical group
