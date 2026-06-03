# Claude Code GitHub Actions

Claude Code GitHub Actions + Amazon Bedrock 연동 저장소입니다.
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

---

## 설정 방법 (Step-by-Step)

### 사전 조건

- AWS 계정 (Amazon Bedrock 접근 권한)
- GitHub 계정 및 저장소
- AWS CLI (선택 사항, 설정 확인용)

---

### Step 1: Amazon Bedrock 모델 접근 활성화

1. [AWS Console](https://console.aws.amazon.com) → **Amazon Bedrock** → **Model access**
2. **us-west-2 (Oregon)** 리전 선택
3. **Manage model access** 클릭
4. `Claude Sonnet 4` (또는 `claude-sonnet-4-6`) 체크 후 **Request access** 저장
5. 상태가 **Access granted** 로 바뀔 때까지 대기 (수 분 소요)

---

### Step 2: AWS GitHub OIDC Provider 등록

GitHub Actions가 AWS에 비밀 키 없이 인증할 수 있도록 OIDC Provider를 등록합니다.

1. AWS Console → **IAM** → **Identity providers** → **Add provider**
2. 다음 값 입력:

   | 항목 | 값 |
   |------|-----|
   | Provider type | OpenID Connect |
   | Provider URL | `https://token.actions.githubusercontent.com` |
   | Audience | `sts.amazonaws.com` |

3. **Add provider** 클릭

---

### Step 3: IAM Role 생성

GitHub Actions가 Bedrock을 호출하기 위한 IAM Role을 생성합니다.

1. AWS Console → **IAM** → **Roles** → **Create role**
2. **Trusted entity type**: Web identity
3. **Identity provider**: `token.actions.githubusercontent.com`
4. **Audience**: `sts.amazonaws.com`
5. **Add condition** 클릭 후 다음 조건 추가 (본인 저장소로 변경):

   | Condition | Key | Value |
   |-----------|-----|-------|
   | StringLike | `token.actions.githubusercontent.com:sub` | `repo:YOUR_GITHUB_USERNAME/YOUR_REPO_NAME:*` |

6. **Next** → 권한 정책 추가:
   - `AmazonBedrockFullAccess` 또는 아래 최소 권한 인라인 정책:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude*"
       }
     ]
   }
   ```

7. Role 이름 입력 (예: `GitHubActions-ClaudeCode-Bedrock`) → **Create role**
8. 생성된 Role의 **ARN** 복사 (예: `arn:aws:iam::123456789012:role/GitHubActions-ClaudeCode-Bedrock`)

---

### Step 4: GitHub App 생성

Claude가 Issue/PR에 코멘트를 작성하려면 GitHub App이 필요합니다.

1. [GitHub App 생성 페이지](https://github.com/settings/apps/new) 이동
2. 다음 값 입력:

   | 항목 | 값 |
   |------|-----|
   | GitHub App name | 원하는 이름 (예: `My Claude Bot`) |
   | Homepage URL | 저장소 URL |
   | Webhook | **비활성화** (Active 체크 해제) |

3. **Permissions** 설정:

   | 권한 | 수준 |
   |------|------|
   | Contents | Read & Write |
   | Issues | Read & Write |
   | Pull requests | Read & Write |

4. **Where can this GitHub App be installed?**: Only on this account
5. **Create GitHub App** 클릭
6. 앱 설정 페이지에서 **App ID** 메모
7. **Generate a private key** 클릭 → `.pem` 파일 다운로드

---

### Step 5: GitHub App을 저장소에 설치

1. GitHub App 설정 페이지 → **Install App** → 저장소 선택 → **Install**

---

### Step 6: Repository Secrets 등록

저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret 이름 | 값 | 설명 |
|-------------|-----|------|
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::...` | Step 3에서 복사한 IAM Role ARN |
| `APP_ID` | 숫자 | Step 4에서 메모한 GitHub App ID |
| `APP_PRIVATE_KEY` | `.pem` 파일 내용 전체 | Step 4에서 다운로드한 private key |

> **APP_PRIVATE_KEY 입력 방법**: `.pem` 파일을 텍스트 편집기로 열어 `-----BEGIN RSA PRIVATE KEY-----` 부터 `-----END RSA PRIVATE KEY-----` 까지 전체를 복사해서 붙여넣기

---

### Step 7: 워크플로우 파일의 저장소 이름 수정

`.github/workflows/` 파일들의 Trust Policy 조건을 본인 저장소에 맞게 수정합니다.

`aws-actions/configure-aws-credentials@v4` 스텝에서 `role-to-assume`은 Secrets에서 가져오므로 별도 수정 불필요합니다. 단, IAM Role의 Trust Policy에서 `sub` 조건의 저장소 이름이 본인 것과 일치하는지 확인합니다.

---

## 테스트 방법

### 테스트 1: @claude 멘션 (대화형)

1. 저장소에 Issue 생성 또는 PR 코멘트 작성
2. 본문에 `@claude`를 포함:
   ```
   @claude 안녕, 이 코드가 하는 일을 설명해줘
   ```
3. **Actions 탭** → `Claude Code` 워크플로우 실행 확인
4. 수십 초 후 봇이 코멘트로 응답

**예상 결과:** GitHub App 봇 계정이 Issue/PR에 Claude의 답변을 코멘트로 게시

---

### 테스트 2: Agent Teams 자동 코드 리뷰

1. 새 브랜치 생성 후 결함이 있는 코드 파일 추가:

   ```python
   # test_sample.py
   import sqlite3

   def get_user(db_path, user_id):
       conn = sqlite3.connect(db_path)
       cur = conn.cursor()
       cur.execute("SELECT * FROM users WHERE id = '%s'" % user_id)  # SQL 인젝션
       return cur.fetchall()

   def login(password):
       admin_password = "admin1234"  # 하드코딩 비밀번호
       return password == admin_password
   ```

2. 커밋 후 push:
   ```bash
   git checkout -b test/review-sample
   git add test_sample.py
   git commit -m "Add sample code for review test"
   git push origin test/review-sample
   ```

3. GitHub에서 `test/review-sample` → `main` PR 생성

4. **Actions 탭** → `Claude Code Review (Agent Teams)` 워크플로우 실행 확인

5. 3~10분 후 PR 코멘트로 리뷰 결과 게시:
   ```
   ## Claude Agent Teams 코드 리뷰

   ## 보안 리뷰
   - [HIGH] test_sample.py:6 — SQL 인젝션: 문자열 포매팅으로 쿼리 조합
   - [HIGH] test_sample.py:11 — 하드코딩 비밀번호
   ...
   ```

6. **Actions 탭** → 해당 실행 → **Summary** 탭에서도 결과 확인 가능

7. **Artifacts** 에서 `stream-json-pr-N` 다운로드 → Agent Teams 실행 로그 확인 (디버깅용)

---

## 실제 테스트 결과 예시

이 저장소의 PR #3에서 실제 테스트를 수행했습니다. 결과는 [HOW_AGENT_TEAMS_WORKS.md](./HOW_AGENT_TEAMS_WORKS.md#실제-테스트-결과-pr-3)를 참고하세요.

- **분석 대상**: `app.py` (의도적 결함 4종)
- **총 발견사항**: 18개 (HIGH: 9, MED: 7, LOW: 2)
- **소요 시간**: 약 3~10분 (Bedrock API 응답 시간 포함)

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 워크플로우가 트리거되지 않음 | GitHub App이 저장소에 설치 안 됨 | Step 5 재확인 |
| `Error: Credentials could not be loaded` | IAM Role Trust Policy의 저장소 이름 불일치 | Trust Policy의 `sub` 조건 확인 |
| `Agent Teams 리뷰를 완료하지 못했습니다` | Bedrock 모델 접근 권한 없음 또는 리전 불일치 | Step 1 재확인, `AWS_REGION: us-west-2` 확인 |
| 봇이 응답하지 않음 | `APP_ID` 또는 `APP_PRIVATE_KEY` 오류 | Secrets 값 재입력 |
| `exit code 2` | `claude` CLI 인수 오류 | 워크플로우 파일의 `--settings` JSON 형식 확인 |

---

## 참고 문서

- [HOW_IT_WORKS.md](./HOW_IT_WORKS.md) — @claude 멘션 방식 상세 흐름도
- [HOW_AGENT_TEAMS_WORKS.md](./HOW_AGENT_TEAMS_WORKS.md) — Agent Teams CI/CD 상세 흐름도 및 실제 테스트 결과
