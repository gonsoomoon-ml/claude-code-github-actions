# Claude Code Agent Teams CI/CD 동작 원리

## 전체 동작 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                             │
│           gonsoomoon-ml/claude-code-github-actions                  │
└─────────────────────────────────────────────────────────────────────┘

  ① PR open / push (synchronize)
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   GitHub Actions Trigger                             │
│                                                                      │
│  Workflow: claude-code-review.yml                                    │
│  Events: pull_request (opened, synchronize, reopened)               │
└─────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                GitHub Actions Runner (ubuntu-latest)                 │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 1: actions/checkout@v4 (fetch-depth: 0)               │    │
│  │   → 전체 git 히스토리 포함 저장소 체크아웃                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 2: actions/create-github-app-token@v2                 │    │
│  │   APP_ID + APP_PRIVATE_KEY → GitHub App Token              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 3: aws-actions/configure-aws-credentials@v4           │    │
│  │   GitHub OIDC JWT → AWS STS → 임시 Credentials (15분)      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 4: npm install -g @anthropic-ai/claude-code           │    │
│  │   Claude Code CLI 설치                                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 5: Run Agent Teams Review                             │    │
│  │                                                             │    │
│  │   ENV:                                                      │    │
│  │     CLAUDE_CODE_USE_BEDROCK=1                               │    │
│  │     CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1                  │    │
│  │     ANTHROPIC_MODEL=us.anthropic.claude-sonnet-4-6          │    │
│  │                                                             │    │
│  │   claude -p "$PROMPT"                                       │    │
│  │     --settings '{"teammateMode":"in-process"}'              │    │
│  │     --allowedTools "Read,Grep,Glob,Bash,                    │    │
│  │                      TeamCreate,TeamDelete,SendMessage,..."  │    │
│  │     --max-budget-usd 3                                      │    │
│  │     --output-format stream-json                             │    │
│  │     > /tmp/stream.jsonl                                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Claude Code CLI (Orchestrator)                      │
│                                                                      │
│   "pr-review" 팀 구성 → 4개 에이전트 병렬 실행                       │
│                                                                      │
│        ┌──────────────────────────────────────────┐                 │
│        │             teammateMode: in-process      │                 │
│        │    (동일 프로세스 내 병렬 실행, 빠름)       │                 │
│        └──────────────────────────────────────────┘                 │
│                 │         │          │          │                    │
│                 ▼         ▼          ▼          ▼                   │
│         ┌───────────┐ ┌─────────┐ ┌──────┐ ┌──────────────┐        │
│         │ security- │ │perform- │ │test- │ │architecture- │        │
│         │ reviewer  │ │ance-    │ │review│ │ reviewer     │        │
│         │           │ │reviewer │ │ -er  │ │              │        │
│         │ SQL 인젝션 │ │ N+1     │ │테스트│ │ SOLID        │        │
│         │ 하드코딩  │ │ O(n²)   │ │커버리│ │ 결합도       │        │
│         │ 인증결함  │ │ 중복코드 │ │지    │ │ API 설계     │        │
│         └───────────┘ └─────────┘ └──────┘ └──────────────┘        │
│                 │         │          │          │                    │
│                 └────┬────┘          └────┬─────┘                   │
│                      │                   │                          │
│                      └────────┬──────────┘                          │
│                               │                                     │
│                               ▼                                     │
│                 ┌─────────────────────────────┐                     │
│                 │  Orchestrator 결과 종합       │                     │
│                 │  → stream-json 출력          │                     │
│                 │  → /tmp/stream.jsonl 저장    │                     │
│                 └─────────────────────────────┘                     │
│                               │                                     │
│                               ▼                                     │
│            Amazon Bedrock (us-west-2) 호출 완료                      │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 GitHub Actions Runner (계속)                         │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 6: Extract review and post comment (if: always())     │    │
│  │                                                             │    │
│  │   Python 파서: stream.jsonl → type=="result" → 마크다운 추출│    │
│  │                                                             │    │
│  │   ┌─────────────────────┐   ┌──────────────────────────┐   │    │
│  │   │  gh pr comment      │   │  $GITHUB_STEP_SUMMARY    │   │    │
│  │   │  PR 코멘트 게시      │   │  Actions 탭 요약 기록    │   │    │
│  │   └─────────────────────┘   └──────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Step 7: Upload stream log (if: always())                   │    │
│  │   /tmp/stream.jsonl → GitHub Artifact (7일 보관)           │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PR 코멘트 게시 (moon-claude-code-bot)              │
│                                                                      │
│  ## Claude Agent Teams 코드 리뷰                                     │
│                                                                      │
│  ## 보안 리뷰                 ## 성능·품질 리뷰                       │
│  - [HIGH] app.py:8 SQL 인젝션  - [HIGH] app.py:25 O(n²) 알고리즘    │
│  - [HIGH] app.py:13 하드코딩  - [HIGH] app.py:29 ZeroDivisionError  │
│  ...                          ...                                   │
│                                                                      │
│  ## 테스트 커버리지 리뷰       ## 아키텍처 리뷰                        │
│  - [HIGH] 5개 함수 테스트 없음 - [HIGH] DIP 위반                      │
│  ...                          ...                                   │
│                                                                      │
│  *Claude Sonnet 4.6 on Amazon Bedrock | Agent Teams*                │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent 파일 구조 (.claude/agents/)

```
.claude/agents/
├── security-reviewer.md      ← SQL 인젝션, 하드코딩 비밀, 인증 결함
├── performance-reviewer.md   ← N+1 쿼리, 비효율 알고리즘, 중복 코드
├── test-reviewer.md          ← 누락 테스트, 엣지 케이스, 취약 테스트
└── architecture-reviewer.md  ← 결합도, SOLID 원칙, API 설계 일관성

각 파일 형식:
┌─────────────────────────────────────────┐
│ ---                                     │
│ description: "에이전트 설명 (Orchestrator│
│               가 선택 시 참조)"           │
│ tools: Read, Grep, Glob, Bash           │
│ ---                                     │
│                                         │
│ [한국어 시스템 프롬프트]                  │
│ - 검토 항목                              │
│ - 출력 형식 (HIGH/MED/LOW + 파일:줄번호) │
│ - 심각도 기준                            │
│ - 규칙 (diff 범위만, 침묵 금지)          │
└─────────────────────────────────────────┘
```

## 인증 흐름 (OIDC — 비밀 키 없이 안전하게)

```
GitHub Actions Runner          AWS STS                  Amazon Bedrock
       │                          │                          │
       │ ① OIDC JWT Token         │                          │
       │  (GitHub 자동 발급)       │                          │
       ├─────────────────────────►│                          │
       │                          │ ② Trust Policy 검증      │
       │                          │  repo: gonsoomoon-ml/    │
       │                          │  claude-code-github-*    │
       │ ③ 임시 Credentials 반환  │                          │
       │◄─────────────────────────┤                          │
       │  (15분 유효)              │                          │
       │                          │                          │
       │ ④ Bedrock InvokeModel (Claude Sonnet 4.6)          │
       ├──────────────────────────────────────────────────► │
       │                          │                          │
       │ ⑤ Agent Teams 실행 결과 반환                        │
       │◄──────────────────────────────────────────────────┤ │
```

## 두 워크플로우 비교

```
┌──────────────────────────────┬──────────────────────────────────────┐
│ claude.yml                   │ claude-code-review.yml               │
├──────────────────────────────┼──────────────────────────────────────┤
│ 트리거: @claude 멘션 (수동)   │ 트리거: PR open/push (자동)          │
│ 방식: claude-code-action@v1  │ 방식: Claude CLI 직접 설치           │
│ 에이전트: 없음 (단일 Claude)  │ 에이전트: 4개 전문 리뷰어 팀         │
│ 모델: Sonnet 4.6             │ 모델: Sonnet 4.6                     │
│ 용도: Q&A, 구현 보조          │ 용도: 자동 코드 리뷰                 │
│ 차단: 없음                    │ 차단: 없음 (Advisory)               │
└──────────────────────────────┴──────────────────────────────────────┘
```

## 구성 요소 요약

| 구성 요소 | 역할 |
|-----------|------|
| **GitHub App** (moon-claude-code-bot) | PR 코멘트 작성 권한 |
| **GitHub OIDC Provider** | AWS 인증 (비밀 키 저장 불필요) |
| **IAM Role** (GitHubActions-ClaudeCode-Bedrock) | Bedrock 호출 권한 |
| **Amazon Bedrock** (us-west-2) | Claude Sonnet 4.6 모델 호스팅 |
| **CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1** | Agent Teams 기능 활성화 |
| **teammateMode: in-process** | 동일 프로세스 내 병렬 에이전트 실행 |
| **.claude/agents/*.md** | 전문 리뷰어 에이전트 시스템 프롬프트 |
| **stream-json + Python 파서** | 결과 추출 및 PR 코멘트 게시 |
