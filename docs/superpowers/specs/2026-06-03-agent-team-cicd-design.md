# Agent Teams CI/CD 설계 문서

**날짜:** 2026-06-03  
**저장소:** gonsoomoon-ml/claude-code-github-actions  
**목표:** PR 자동 코드 리뷰 파이프라인 — 4개 전문 에이전트 팀 + 기존 @claude 멘션 기능 병행

---

## 결정 사항 요약

| 항목 | 결정 |
|------|------|
| 트리거 | 하이브리드: PR open/push 자동 + @claude 멘션 수동 |
| 모델 | Claude Sonnet 4.6 (us.anthropic.claude-sonnet-4-6) |
| 리뷰 결과 | Advisory (비차단) + PR 코멘트 + GitHub Step Summary |
| 에이전트 구성 | security, performance, test, architecture (4개) |
| 워크플로우 전략 | 분리된 두 워크플로우 (Approach B) |

---

## 파일 변경 목록

```
신규 생성:
  .claude/agents/security-reviewer.md
  .claude/agents/performance-reviewer.md
  .claude/agents/test-reviewer.md
  .claude/agents/architecture-reviewer.md
  .github/workflows/claude-code-review.yml

수정:
  CLAUDE.md  (PR 리뷰 출력 형식 섹션 추가)

변경 없음:
  .github/workflows/claude.yml  (@claude 멘션 기능 그대로 유지)
```

---

## 아키텍처

### 실행 흐름

```
PR open / push (opened, synchronize, reopened)
  └─► claude-code-review.yml 트리거
        ├─ Step 1: actions/checkout@v4
        ├─ Step 2: GitHub App Token 생성
        ├─ Step 3: AWS OIDC → 임시 Bedrock 자격증명
        ├─ Step 4: Claude CLI 설치 (npm install -g @anthropic-ai/claude-code)
        ├─ Step 5: PR diff 추출 (최대 300줄)
        └─ Step 6: claude -p "$PROMPT" 실행
              │  env: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
              │  env: CLAUDE_CODE_USE_BEDROCK=1
              │  --settings '{"teammateMode":"in-process"}'
              │
              ├─[병렬] security-reviewer     → 보안 취약점
              ├─[병렬] performance-reviewer  → 성능·품질
              ├─[병렬] test-reviewer         → 테스트 커버리지
              └─[병렬] architecture-reviewer → 아키텍처 설계
                    │
              Orchestrator가 4개 결과 종합
                    ├─ Step 7: stream-json 파싱 → 마크다운 추출
                    ├─ Step 8: gh pr comment → PR 코멘트 게시
                    ├─ Step 9: $GITHUB_STEP_SUMMARY → Actions 탭 기록
                    └─ Step 10: stream.jsonl 아티팩트 보관 (7일)
```

### 두 워크플로우의 독립성

```
.github/workflows/claude.yml          .github/workflows/claude-code-review.yml
─────────────────────────────         ────────────────────────────────────────
트리거: issue_comment (@claude)        트리거: pull_request (open/push)
방식: claude-code-action@v1           방식: claude CLI 직접 설치 후 실행
에이전트: 없음 (단일 Claude)           에이전트: 4개 전문 에이전트 팀
모델: Sonnet 4.6                       모델: Sonnet 4.6
```

두 워크플로우는 완전히 독립적으로 동작합니다. 신규 워크플로우 장애 시 기존 @claude 멘션 기능에 영향 없습니다.

---

## Agent 파일 설계 (.claude/agents/)

### 공통 구조

```markdown
---
description: [Orchestrator가 이 에이전트를 선택할 때 참조하는 설명]
tools: Read, Grep, Glob, Bash
---

[에이전트 시스템 프롬프트]
```

### 공통 출력 형식 (4개 에이전트 모두 동일)

```
## [에이전트명] 리뷰

### 발견사항
- [HIGH] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [MED]  `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [LOW]  `파일명:줄번호` — 문제 설명 및 구체적 개선안

### 결론
이상 없음 OR N개 발견사항 (HIGH: N, MED: N, LOW: N)
```

**규칙:** `file:line` 없는 발견사항은 보고하지 않음. 발견사항 없을 시 반드시 "이상 없음" 명시 (침묵 금지).

### 각 에이전트 검토 항목

**security-reviewer**
- SQL/command/path 인젝션
- 하드코딩된 자격증명, API 키, 토큰
- 인증·인가 결함, 권한 상승 위험
- 민감 데이터의 부적절한 로깅·노출
- 입력 검증 누락

**performance-reviewer**
- 불필요한 반복·할당
- N+1 쿼리, 비효율 알고리즘
- null 처리, 경계값, 레이스 컨디션
- 중복 코드, 복잡도, 가독성

**test-reviewer**
- 변경된 로직에 대한 테스트 존재 여부
- 누락된 엣지 케이스 및 실패 경로
- 깨지기 쉽거나 의미 없는 테스트

**architecture-reviewer**
- 모듈 결합도·응집도 (SOLID 원칙)
- API 설계 일관성
- 의존성 방향 및 순환 참조
- 레이어 경계 위반

---

## 신규 워크플로우 설계 (claude-code-review.yml)

### 핵심 환경변수

```yaml
env:
  CLAUDE_CODE_USE_BEDROCK: "1"
  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"
  ANTHROPIC_MODEL: us.anthropic.claude-sonnet-4-6
  ANTHROPIC_DEFAULT_HAIKU_MODEL: us.anthropic.claude-sonnet-4-6
  AWS_REGION: us-west-2
```

### Claude CLI 실행 파라미터

```bash
claude -p "$PROMPT" \
  --settings '{"teammateMode":"in-process"}' \
  --permission-mode acceptEdits \
  --allowedTools "Read,Grep,Glob,Bash,TeamCreate,TeamDelete,SendMessage,TaskCreate,TaskUpdate,TaskList,Agent" \
  --disallowedTools "Task" \
  --max-budget-usd 3 \
  --output-format stream-json \
  --verbose \
  > /tmp/stream.jsonl
```

**파라미터 결정 이유:**
- `teammateMode: in-process` — 별도 프로세스 없이 동일 프로세스 내 병렬 실행 (빠름)
- `acceptEdits` — CI 환경에서 권한 확인 프롬프트 없이 자동 진행
- `Task` disallowed — 백그라운드 CLI 태스크 생성 방지 (TaskCreate/List와 다른 도구)
- `max-budget-usd 3` — Sonnet 4.6 기준 약 PR 60개 분량 상한
- `stream-json` — 아티팩트 저장 및 디버깅용

### Orchestrator 프롬프트 구조

```
PR #[번호] 코드를 리뷰해주세요.

PR 제목: [제목]

변경 내용:
[diff 내용 — 최대 300줄]

'pr-review' 팀을 구성하여 다음 전문 리뷰어들이 분석하도록 해주세요:
- security-reviewer
- performance-reviewer
- test-reviewer
- architecture-reviewer

모든 리뷰어의 분석이 완료되면 결과를 종합하여 마크다운으로 보고해주세요.
```

---

## CLAUDE.md 추가 내용

```markdown
## PR 리뷰 (Agent Teams)
- PR 자동 리뷰 시 security/performance/test/architecture 4개 에이전트 팀 사용
- 각 에이전트: [HIGH/MED/LOW] `파일명:줄번호` 형식으로 발견사항 보고
- 발견사항 없을 시 "이상 없음" 명시 (침묵 금지)
- 리뷰는 diff 범위만 분석, 추측 금지
```

---

## 범위 외 (이번 구현에 포함하지 않음)

- Branch Protection Rules 연동 (HIGH 심각도 → merge 차단)
- 파일 타입별 조건부 트리거
- 다중 모델 티어 라우팅
- Adversarial Verify 패턴 (발견사항 반박 검증)
