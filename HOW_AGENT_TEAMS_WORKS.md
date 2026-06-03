# Claude Code Agent Teams CI/CD 동작 원리

## Agent Teams는 어디서 실행되는가?

```
로컬 머신 (개발자 PC)        GitHub 클라우드              AWS 클라우드
─────────────────────        ───────────────────          ────────────────
git push / PR 생성    ──►   GitHub Actions Runner   ──►  Amazon Bedrock
                             (1회용 Ubuntu VM,             (Claude Sonnet 4.6
코드 작성, push,             PR마다 자동 생성/삭제)          Agent Teams 실행)
PR 결과 확인만 함
                             claude CLI 설치/실행
                             결과 파싱 및 게시
```

**핵심:** 로컬 머신은 `git push`로 트리거만 할 뿐, Claude가 코드를 읽고 분석하는
모든 작업은 GitHub Actions Runner(클라우드 VM)와 Amazon Bedrock(AWS)에서 실행됩니다.
로컬 머신이 꺼져 있어도 PR이 열려 있으면 리뷰가 자동으로 실행됩니다.

| 위치 | 역할 |
|------|------|
| **로컬 머신** | `git push`, PR 생성, 결과 확인 |
| **GitHub Actions Runner** | `claude` CLI 설치·실행, PR 코멘트 게시 |
| **Amazon Bedrock (us-west-2)** | Claude Sonnet 4.6 추론, Agent Teams 4개 에이전트 병렬 실행 |

---

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

---

## 실제 테스트 결과 (PR #3)

**테스트 파일:** `app.py` — 의도적 결함 4종 포함  
**모델:** Claude Sonnet 4.6 on Amazon Bedrock (us-west-2)  
**결과:** 총 **18개 발견사항** (HIGH: 9, MED: 7, LOW: 2)

```
app.py 주요 결함:
  1. SQL 인젝션    — cur.execute("SELECT * FROM users WHERE id = '%s'" % user_id)
  2. 하드코딩 비밀  — admin_password = "admin1234" / SECRET_KEY = "super-secret-key-..."
  3. O(n²) 알고리즘 — sum(orders[:i+1]) 매 루프마다 재계산
  4. SRP 위반      — UserService가 DB·메일·결제·분석 6가지 책임
```

### 보안 리뷰 (5개 발견사항)

```
[HIGH] app.py:8   — SQL 인젝션: 문자열 포매팅(%)으로 쿼리 조합
                    개선: cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
[HIGH] app.py:13  — 하드코딩 비밀번호: admin_password = "admin1234"
                    개선: 환경변수 또는 secrets manager 사용
[HIGH] app.py:14  — 하드코딩 SECRET_KEY: "super-secret-key-do-not-share"
                    개선: os.environ["SECRET_KEY"] 로 이동
[HIGH] app.py:44  — SQL 인젝션 (f-string): f"INSERT INTO users VALUES ('{name}', '{email}')"
                    개선: 파라미터 바인딩 사용
[MED]  app.py:11  — 인증 결함: username 파라미터 무시, 비밀번호만 검사
                    개선: username과 password를 함께 검증
```

### 성능·품질 리뷰 (4개 발견사항)

```
[HIGH] app.py:24  — O(n²) 알고리즘: sum(orders[:i+1]) 매 반복 재계산
                    개선: total += orders[i] 단순 누적으로 O(n) 달성
[HIGH] app.py:29  — ZeroDivisionError 미처리: return a / b
                    개선: if b == 0: raise ValueError 또는 return None
[MED]  app.py:34  — DB 커넥션 미닫음: __init__에서 연결 후 close() 없음
                    개선: with 문 또는 __del__ 에서 conn.close()
[LOW]  —           — 코드 전반 타입 힌트 부재 (가독성 개선 기회)
```

### 테스트 커버리지 리뷰 (4개 발견사항)

```
[HIGH] app.py:5   — get_user(): 테스트 없음 (SQL 인젝션 핵심 로직)
[HIGH] app.py:11  — login(): 테스트 없음 (인증 로직)
[HIGH] app.py:22  — process_orders(): 테스트 없음 (빈 리스트, 음수 케이스 미검증)
[HIGH] app.py:29  — divide(): 테스트 없음 (b=0 경계값 미검증)
[MED]  —           — 5개 함수/메서드 모두 테스트 파일 자체가 없음
```

### 아키텍처 리뷰 (5개 발견사항)

```
[HIGH] app.py:33  — 단일 책임 원칙(SRP) 위반: UserService가
                    DB·이메일·결제·분석·캐시·로거 6가지 책임 보유
                    개선: 각 책임을 별도 서비스로 분리
[HIGH] app.py:35  — 의존성 역전 원칙(DIP) 위반: sqlite3 직접 생성
                    개선: 생성자 주입(DI) 패턴 적용
[HIGH] app.py:44  — 레이어 경계 위반: 비즈니스 로직에서 DB SQL 직접 작성
                    개선: Repository 패턴 도입
[MED]  app.py:11  — API 설계 일관성 부재: login(username, password)에서
                    username 파라미터가 실제로 사용되지 않음
[LOW]  —           — 메서드 반환 타입 불일치 (True vs fetchall() vs None 혼재)
```

### 종합

| 에이전트 | HIGH | MED | LOW | 합계 |
|----------|------|-----|-----|------|
| security-reviewer | 4 | 1 | 0 | 5 |
| performance-reviewer | 2 | 1 | 1 | 4 |
| test-reviewer | 4 | 1 | 0 | 4 (주요 함수 전체 미테스트) |
| architecture-reviewer | 3 | 1 | 1 | 5 |
| **합계** | **9** | **7** | **2** | **18** |
