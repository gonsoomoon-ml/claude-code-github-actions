# Claude Code GitHub Actions

Claude Code GitHub Actions + Amazon Bedrock 연동 테스트 저장소입니다.
PR 자동 코드 리뷰(Agent Teams)와 `@claude` 멘션 기반 대화형 응답 두 가지 방식을 구현합니다.

## 폴더 구조

```
.
├── .claude/
│   └── agents/                  ← Claude Code 서브에이전트 정의
│       ├── security-reviewer.md     SQL 인젝션·하드코딩 비밀·인증 결함 검토
│       ├── performance-reviewer.md  N+1·비효율 알고리즘·중복 코드 검토
│       ├── test-reviewer.md         누락 테스트·엣지 케이스 검토
│       └── architecture-reviewer.md 결합도·SOLID·API 설계 검토
│
├── .github/
│   └── workflows/               ← GitHub Actions 워크플로우
│       ├── claude.yml               @claude 멘션 → 대화형 응답 (claude-code-action)
│       └── claude-code-review.yml   PR open/push → Agent Teams 자동 코드 리뷰
│
├── design/
│   └── prd.md                   ← 프로젝트 요구사항 문서
│
├── docs/
│   └── superpowers/
│       ├── specs/               ← 설계 문서 (brainstorming 산출물)
│       └── plans/               ← 구현 계획 (writing-plans 산출물)
│
├── CLAUDE.md                    ← Claude 동작 가이드라인 (모든 실행 시 자동 로드)
├── HOW_IT_WORKS.md              ← @claude 멘션 방식 동작 원리
└── HOW_AGENT_TEAMS_WORKS.md     ← Agent Teams CI/CD 동작 원리 + 실제 테스트 결과
```

## 두 가지 실행 방식

| 방식 | 트리거 | 워크플로우 | 에이전트 |
|------|--------|-----------|---------|
| **대화형** | Issue/PR에 `@claude` 멘션 | `claude.yml` | 단일 Claude |
| **자동 리뷰** | PR open / push | `claude-code-review.yml` | 4개 전문 에이전트 팀 |

## 설정 방법

### 1. GitHub App 설치
[Claude GitHub App](https://github.com/apps/claude)을 저장소에 설치합니다.

### 2. AWS 설정 (Bedrock)
- AWS에서 GitHub OIDC Identity Provider 설정
- Bedrock 권한이 있는 IAM Role 생성

### 3. GitHub App 생성
- [GitHub App 생성](https://github.com/settings/apps/new) (Contents, Issues, Pull requests 권한)
- Private key 생성

### 4. Repository Secrets 설정
Repository Settings > Secrets and variables > Actions에서:
- `AWS_ROLE_TO_ASSUME`: IAM Role ARN
- `APP_ID`: GitHub App ID
- `APP_PRIVATE_KEY`: GitHub App private key (.pem)

## 사용법

**대화형 응답** — Issue나 PR 코멘트에서 `@claude` 멘션:
```
@claude 이 코드를 리뷰해줘
@claude 이 이슈를 구현해줘
@claude TypeError 버그를 수정해줘
```

**자동 코드 리뷰** — PR을 열거나 커밋을 push하면 자동 실행됩니다.  
4개 에이전트(security · performance · test · architecture)가 병렬로 분석해 PR 코멘트로 결과를 게시합니다.

## 참고 문서

- [HOW_IT_WORKS.md](./HOW_IT_WORKS.md) — @claude 멘션 방식 상세 흐름
- [HOW_AGENT_TEAMS_WORKS.md](./HOW_AGENT_TEAMS_WORKS.md) — Agent Teams CI/CD 상세 흐름 및 실제 테스트 결과
