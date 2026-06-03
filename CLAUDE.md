# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code GitHub Actions 테스트 저장소입니다. GitHub Issue/PR에서 `@claude`를 멘션하면 Claude가 자동으로 응답합니다. Claude는 Amazon Bedrock(us-west-2)을 통해 실행되며, GitHub OIDC 인증으로 AWS 임시 자격증명을 획득합니다.

## Architecture

### 실행 흐름

```
사용자 @claude 멘션 → GitHub Actions 트리거 → GitHub App Token 생성
  → AWS OIDC 인증 (임시 Credentials 획득) → claude-code-action@v1 실행
  → Amazon Bedrock (Claude Sonnet 4.6) 호출 → GitHub에 코멘트 작성
```

### 핵심 구성 요소

| 파일 | 역할 |
|------|------|
| `.github/workflows/claude.yml` | @claude 멘션 기반 대화형 응답 |
| `.github/workflows/claude-code-review.yml` | PR 자동 Agent Teams 리뷰 |
| `.claude/agents/*.md` | 전문 리뷰어 에이전트 시스템 프롬프트 |
| `CLAUDE.md` | Claude 실행 시 자동 로드되는 동작 가이드라인 |

### 트리거 조건

- `issue_comment` (created) — Issue 코멘트에 `@claude` 포함
- `pull_request_review_comment` (created) — PR 리뷰 코멘트에 `@claude` 포함
- `issues` (opened, assigned) — Issue 본문에 `@claude` 포함

### 인증 구조

GitHub Actions는 OIDC JWT Token을 자동 발급 → AWS STS가 Trust Policy 검증 → 임시 AWS Credentials 발급(15분 유효). AWS Access Key를 Secrets에 저장하지 않는 패턴입니다.

### 필수 Secrets

| Secret | 내용 |
|--------|------|
| `AWS_ROLE_TO_ASSUME` | IAM Role ARN (Bedrock 호출 권한) |
| `APP_ID` | GitHub App ID |
| `APP_PRIVATE_KEY` | GitHub App Private Key (.pem) |

## PR 리뷰 (Agent Teams)

PR 자동 리뷰는 `.claude/agents/`의 4개 전문 에이전트 팀이 병렬로 수행합니다.

- 각 에이전트 출력 형식: `[HIGH/MED/LOW] 파일명:줄번호 — 설명`
- 발견사항 없을 시 반드시 "이상 없음" 명시 (침묵 금지)
- diff 범위만 분석, 추측 금지

| 에이전트 | 담당 |
|----------|------|
| `security-reviewer` | SQL 인젝션, 하드코딩 비밀, 인증 결함 |
| `performance-reviewer` | N+1, 비효율 알고리즘, 중복 코드 |
| `test-reviewer` | 누락 테스트, 엣지 케이스 |
| `architecture-reviewer` | 결합도, SOLID, API 설계 |

## Language

- 코드 리뷰 및 응답은 한국어로 작성해주세요.
- 커밋 메시지는 영어로 작성합니다.

## Code Style

- 간결하고 읽기 쉬운 코드를 작성합니다.
- 불필요한 주석은 피하고, 코드 자체가 설명이 되도록 합니다.
