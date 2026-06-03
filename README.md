# Claude Code GitHub Actions 테스트

Claude Code GitHub Actions를 테스트하기 위한 저장소입니다.

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

### 3. 사용법
Issue나 PR 코멘트에서 `@claude`를 멘션하면 Claude가 응답합니다.

**예시:**
```
@claude 이 코드를 리뷰해줘
@claude 이 이슈를 구현해줘
@claude TypeError 버그를 수정해줘
```

## 파일 구조
```
.github/workflows/claude.yml  # GitHub Actions 워크플로우
CLAUDE.md                      # Claude 동작 가이드라인
```
