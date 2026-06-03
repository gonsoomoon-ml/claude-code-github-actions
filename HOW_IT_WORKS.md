# Claude Code GitHub Actions 동작 원리

## 전체 동작 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                                │
│  gonsoomoon-ml/claude-code-github-actions                               │
└─────────────────────────────────────────────────────────────────────────┘

  ① 사용자가 Issue/PR에 "@claude ..." 코멘트 작성
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GitHub Actions Trigger                              │
│                                                                         │
│  Events:                                                                │
│    - issue_comment (created)                                            │
│    - pull_request_review_comment (created)                              │
│    - issues (opened, assigned)                                          │
│                                                                         │
│  Condition: body contains "@claude"                                     │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Runner (ubuntu-latest)                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 1: actions/checkout@v4                                       │  │
│  │   - 저장소 코드 체크아웃 (CLAUDE.md 포함)                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 2: actions/create-github-app-token@v2                        │  │
│  │                                                                   │  │
│  │   Secrets:                                                        │  │
│  │     APP_ID ──────────┐                                            │  │
│  │     APP_PRIVATE_KEY ─┼──► GitHub App Token 생성                   │  │
│  │                      │    (Issues/PRs/Contents 읽기/쓰기 권한)     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 3: aws-actions/configure-aws-credentials@v4                  │  │
│  │                                                                   │  │
│  │   GitHub OIDC Token                                               │  │
│  │        │                                                          │  │
│  │        ▼                                                          │  │
│  │   ┌──────────────────────────────────┐                            │  │
│  │   │ AWS STS (AssumeRoleWithWebIdentity)                           │  │
│  │   │                                  │                            │  │
│  │   │ Trust Policy 검증:               │                            │  │
│  │   │  - aud: sts.amazonaws.com        │                            │  │
│  │   │  - sub: repo:gonsoomoon-ml/      │                            │  │
│  │   │         claude-code-github-*     │                            │  │
│  │   └──────────────────────────────────┘                            │  │
│  │        │                                                          │  │
│  │        ▼                                                          │  │
│  │   임시 AWS Credentials 발급                                       │  │
│  │   (Role: GitHubActions-ClaudeCode-Bedrock)                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Step 4: anthropics/claude-code-action@v1                          │  │
│  │                                                                   │  │
│  │   Inputs:                                                         │  │
│  │     github_token: (from Step 2)                                   │  │
│  │     use_bedrock: "true"                                           │  │
│  │     model: us.anthropic.claude-sonnet-4-6                         │  │
│  │     max-turns: 10                                                 │  │
│  │                                                                   │  │
│  │   ┌─────────────────────────────────────────────────────────────┐ │  │
│  │   │ Claude Code CLI 실행                                        │ │  │
│  │   │                                                             │ │  │
│  │   │  1. Issue/PR context 읽기                                   │ │  │
│  │   │  2. CLAUDE.md 가이드라인 로드                                │ │  │
│  │   │  3. Amazon Bedrock API 호출 ─────────────────────┐          │ │  │
│  │   │  4. 응답 생성                                     │          │ │  │
│  │   │  5. GitHub API로 코멘트 작성 (github_token 사용)  │          │ │  │
│  │   └──────────────────────────────────────────────────┼──────────┘ │  │
│  └───────────────────────────────────────────────────────┼───────────┘  │
└──────────────────────────────────────────────────────────┼──────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Amazon Bedrock (us-west-2)                        │
│                                                                         │
│   Model: us.anthropic.claude-sonnet-4-6                                 │
│                                                                         │
│   ┌───────────────────────────────────────────────────────────────────┐ │
│   │ Claude Sonnet 4.6                                                 │ │
│   │   - 코드 분석, 리뷰, 구현                                         │ │
│   │   - CLAUDE.md 기반 한국어 응답                                     │ │
│   │   - 파일 수정/PR 생성 가능                                         │ │
│   └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 인증 흐름 (OIDC - 비밀 키 없이 안전하게)

```
GitHub Actions Runner          AWS STS                    AWS Bedrock
       │                          │                          │
       │ ① OIDC JWT Token         │                          │
       │  (GitHub이 자동 발급)     │                          │
       ├─────────────────────────►│                          │
       │                          │                          │
       │                          │ ② Trust Policy 검증      │
       │                          │  - 저장소 이름 확인       │
       │                          │  - audience 확인          │
       │                          │                          │
       │ ③ 임시 Credentials 반환  │                          │
       │◄─────────────────────────┤                          │
       │  (15분간 유효)            │                          │
       │                          │                          │
       │ ④ Bedrock InvokeModel                               │
       ├──────────────────────────────────────────────────────►
       │                          │                          │
       │ ⑤ Claude 응답 반환                                   │
       │◄──────────────────────────────────────────────────────┤
       │                          │                          │
```

## 구성 요소 요약

| 구성 요소 | 역할 |
|-----------|------|
| **GitHub App** (Moon Claude Code Bot) | Issue/PR에 코멘트 작성 권한 제공 |
| **GitHub OIDC Provider** | AWS에 안전하게 인증 (비밀 키 저장 불필요) |
| **IAM Role** (GitHubActions-ClaudeCode-Bedrock) | Bedrock 호출 권한, 이 저장소만 허용 |
| **Amazon Bedrock** | Claude 모델 호스팅 및 추론 |
| **CLAUDE.md** | Claude 동작 가이드라인 (한국어 응답 등) |
| **claude-code-action@v1** | 모든 것을 연결하는 GitHub Action |

## 보안 특징

1. **OIDC 기반 인증**: AWS Access Key를 저장하지 않음. GitHub이 발급한 JWT 토큰으로 임시 credentials 획득
2. **저장소 제한**: Trust Policy에서 `gonsoomoon-ml/claude-code-github-actions` 저장소만 허용
3. **임시 자격증명**: 발급된 AWS credentials는 15분 후 자동 만료
4. **GitHub App Token**: 최소 권한 원칙 (Contents, Issues, Pull requests만)
5. **Secrets 관리**: 모든 민감 정보는 GitHub Secrets에 암호화 저장

## 사용 방법

Issue나 PR에서 `@claude`를 멘션하면 됩니다:

```
@claude 이 코드를 리뷰해줘
@claude 이 이슈를 구현해줘
@claude TypeError 버그를 수정해줘
```

## 설정된 Secrets

| Secret | 설명 |
|--------|------|
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::738490718699:role/GitHubActions-ClaudeCode-Bedrock` |
| `APP_ID` | GitHub App ID (Moon Claude Code Bot) |
| `APP_PRIVATE_KEY` | GitHub App private key (.pem) |
