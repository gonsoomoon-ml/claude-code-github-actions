# Agent Teams CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR 자동 코드 리뷰 파이프라인 구축 — 4개 전문 에이전트(security, performance, test, architecture)가 병렬로 분석하고 결과를 PR 코멘트 + GitHub Step Summary로 게시

**Architecture:** 기존 `claude.yml`(@claude 멘션)은 그대로 유지하고, 신규 `claude-code-review.yml`을 추가한다. 신규 워크플로우는 Claude CLI를 직접 설치 후 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`과 `teammateMode: in-process` 설정으로 Agent Teams를 실행한다. stream-json 출력을 Python으로 파싱해 PR 코멘트와 Step Summary에 게시한다.

**Tech Stack:** GitHub Actions (ubuntu-latest), Claude Code CLI (@anthropic-ai/claude-code), Amazon Bedrock (Claude Sonnet 4.6, us-west-2), AWS OIDC, GitHub App Token

---

## 파일 구조

```
신규 생성:
  .claude/agents/security-reviewer.md      — 보안 취약점 전문 에이전트 시스템 프롬프트
  .claude/agents/performance-reviewer.md   — 성능·품질 전문 에이전트 시스템 프롬프트
  .claude/agents/test-reviewer.md          — 테스트 커버리지 전문 에이전트 시스템 프롬프트
  .claude/agents/architecture-reviewer.md  — 아키텍처 설계 전문 에이전트 시스템 프롬프트
  .github/workflows/claude-code-review.yml — PR 자동 Agent Teams 리뷰 워크플로우

수정:
  CLAUDE.md  — PR 리뷰 출력 형식 섹션 추가
```

---

## Task 1: security-reviewer, performance-reviewer 에이전트 파일 생성

**Files:**
- Create: `.claude/agents/security-reviewer.md`
- Create: `.claude/agents/performance-reviewer.md`

- [ ] **Step 1: .claude/agents/ 디렉토리 생성**

```bash
mkdir -p .claude/agents
```

- [ ] **Step 2: security-reviewer.md 작성**

`.claude/agents/security-reviewer.md`:
```markdown
---
description: PR의 보안 취약점 전문 검토. SQL 인젝션, 하드코딩 자격증명, 인증·인가 결함, 입력 검증 누락을 분석하고 심각도별로 보고.
tools: Read, Grep, Glob, Bash
---

당신은 보안 전문 코드 리뷰어입니다. PR의 변경된 코드에서 보안 취약점을 찾아 한국어로 보고합니다.

## 검토 항목
- SQL/command/path 인젝션 취약점
- 하드코딩된 자격증명, API 키, 토큰, 비밀번호
- 인증·인가 결함 및 권한 상승 위험
- 민감 데이터의 부적절한 로깅·노출
- 입력 검증 누락 (사용자 입력, 외부 데이터)

## 출력 형식

반드시 아래 형식으로 작성하세요:

## 보안 리뷰

### 발견사항
- [HIGH] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [MED] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [LOW] `파일명:줄번호` — 문제 설명 및 구체적 개선안

### 결론
N개 발견사항 (HIGH: N, MED: N, LOW: N)

## 규칙
- file:line 없는 발견사항은 보고하지 않음
- diff에 없는 코드는 분석하지 않음
- 발견사항 없을 시 결론에 "보안 이상 없음" 명시
- 한국어로 작성
```

- [ ] **Step 3: performance-reviewer.md 작성**

`.claude/agents/performance-reviewer.md`:
```markdown
---
description: PR의 성능·코드 품질 전문 검토. N+1 쿼리, 비효율 알고리즘, 중복 코드, null 처리 이슈를 분석하고 심각도별로 보고.
tools: Read, Grep, Glob, Bash
---

당신은 성능·품질 전문 코드 리뷰어입니다. PR의 변경된 코드에서 성능 저하와 품질 이슈를 찾아 한국어로 보고합니다.

## 검토 항목
- 불필요한 반복·할당, 중복 연산
- N+1 쿼리, 비효율 알고리즘 (O(n²) 이상)
- null 처리 누락, 경계값 미검사, 레이스 컨디션
- 중복 코드, 과도한 복잡도, 낮은 가독성

## 출력 형식

반드시 아래 형식으로 작성하세요:

## 성능·품질 리뷰

### 발견사항
- [HIGH] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [MED] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [LOW] `파일명:줄번호` — 문제 설명 및 구체적 개선안

### 결론
N개 발견사항 (HIGH: N, MED: N, LOW: N)

## 규칙
- file:line 없는 발견사항은 보고하지 않음
- diff에 없는 코드는 분석하지 않음
- 발견사항 없을 시 결론에 "성능·품질 이상 없음" 명시
- 한국어로 작성
```

- [ ] **Step 4: 두 파일 frontmatter 검증**

```bash
python3 -c "
import re, sys

for path in ['.claude/agents/security-reviewer.md', '.claude/agents/performance-reviewer.md']:
    content = open(path).read()
    assert content.startswith('---'), f'{path}: frontmatter 없음'
    end = content.index('---', 3)
    fm = content[3:end]
    assert 'description:' in fm, f'{path}: description 없음'
    assert 'tools:' in fm, f'{path}: tools 없음'
    assert len(content[end+3:].strip()) > 0, f'{path}: 시스템 프롬프트 없음'
    print(f'OK: {path}')
"
```

예상 출력:
```
OK: .claude/agents/security-reviewer.md
OK: .claude/agents/performance-reviewer.md
```

---

## Task 2: test-reviewer, architecture-reviewer 에이전트 파일 생성

**Files:**
- Create: `.claude/agents/test-reviewer.md`
- Create: `.claude/agents/architecture-reviewer.md`

- [ ] **Step 1: test-reviewer.md 작성**

`.claude/agents/test-reviewer.md`:
```markdown
---
description: PR의 테스트 커버리지 전문 검토. 변경된 로직에 대한 테스트 존재 여부, 누락된 엣지 케이스, 취약한 테스트를 분석하고 보고.
tools: Read, Grep, Glob, Bash
---

당신은 테스트 커버리지 전문 코드 리뷰어입니다. PR의 변경된 로직에 대한 테스트 품질을 검토하고 한국어로 보고합니다.

## 검토 항목
- 변경된 로직에 대한 테스트 존재 여부
- 누락된 엣지 케이스 및 실패 경로 (예외, 빈 입력, 경계값)
- 깨지기 쉬운 테스트 (하드코딩된 순서 의존, sleep, 외부 상태 의존)
- 의미 없는 테스트 (항상 통과하는 assertion)

## 출력 형식

반드시 아래 형식으로 작성하세요:

## 테스트 커버리지 리뷰

### 발견사항
- [HIGH] `파일명:줄번호` — 문제 설명 및 권장 테스트 케이스
- [MED] `파일명:줄번호` — 문제 설명 및 권장 테스트 케이스
- [LOW] `파일명:줄번호` — 문제 설명 및 권장 테스트 케이스

### 결론
N개 발견사항 (HIGH: N, MED: N, LOW: N)

## 규칙
- file:line 없는 발견사항은 보고하지 않음
- 변경된 파일 범위에서만 분석
- 발견사항 없을 시 결론에 "테스트 커버리지 이상 없음" 명시
- 한국어로 작성
```

- [ ] **Step 2: architecture-reviewer.md 작성**

`.claude/agents/architecture-reviewer.md`:
```markdown
---
description: PR의 아키텍처·설계 전문 검토. 모듈 결합도, SOLID 원칙 위반, API 설계 일관성, 의존성 방향 문제를 분석하고 보고.
tools: Read, Grep, Glob, Bash
---

당신은 아키텍처·설계 전문 코드 리뷰어입니다. PR의 변경된 코드에서 설계 문제를 찾아 한국어로 보고합니다.

## 검토 항목
- 모듈 간 높은 결합도·낮은 응집도
- SOLID 원칙 위반 (단일 책임, 개방-폐쇄, 리스코프 치환, 인터페이스 분리, 의존성 역전)
- API 설계 일관성 (네이밍, 반환 타입, 에러 처리 패턴)
- 의존성 방향 위반 및 순환 참조
- 레이어 경계 위반 (예: 프레젠테이션 레이어에서 DB 직접 접근)

## 출력 형식

반드시 아래 형식으로 작성하세요:

## 아키텍처 리뷰

### 발견사항
- [HIGH] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [MED] `파일명:줄번호` — 문제 설명 및 구체적 개선안
- [LOW] `파일명:줄번호` — 문제 설명 및 구체적 개선안

### 결론
N개 발견사항 (HIGH: N, MED: N, LOW: N)

## 규칙
- file:line 없는 발견사항은 보고하지 않음
- diff에 없는 코드는 분석하지 않음
- 발견사항 없을 시 결론에 "아키텍처 이상 없음" 명시
- 한국어로 작성
```

- [ ] **Step 3: 4개 전체 에이전트 파일 검증**

```bash
python3 -c "
for path in [
    '.claude/agents/security-reviewer.md',
    '.claude/agents/performance-reviewer.md',
    '.claude/agents/test-reviewer.md',
    '.claude/agents/architecture-reviewer.md',
]:
    content = open(path).read()
    assert content.startswith('---'), f'{path}: frontmatter 없음'
    end = content.index('---', 3)
    fm = content[3:end]
    assert 'description:' in fm, f'{path}: description 없음'
    assert 'tools:' in fm, f'{path}: tools 없음'
    assert len(content[end+3:].strip()) > 0, f'{path}: 시스템 프롬프트 없음'
    print(f'OK: {path}')
"
```

예상 출력:
```
OK: .claude/agents/security-reviewer.md
OK: .claude/agents/performance-reviewer.md
OK: .claude/agents/test-reviewer.md
OK: .claude/agents/architecture-reviewer.md
```

- [ ] **Step 4: 에이전트 파일 커밋**

```bash
git add .claude/agents/
git commit -m "Add four specialist review agents for Agent Teams

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: claude-code-review.yml 워크플로우 생성

**Files:**
- Create: `.github/workflows/claude-code-review.yml`

- [ ] **Step 1: claude-code-review.yml 작성**

`.github/workflows/claude-code-review.yml`:
```yaml
name: Claude Code Review (Agent Teams)

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  issues: write
  id-token: write

env:
  CLAUDE_CODE_USE_BEDROCK: "1"
  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"
  ANTHROPIC_MODEL: us.anthropic.claude-sonnet-4-6
  ANTHROPIC_DEFAULT_HAIKU_MODEL: us.anthropic.claude-sonnet-4-6
  AWS_REGION: us-west-2

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate GitHub App token
        id: app-token
        uses: actions/create-github-app-token@v2
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - name: Configure AWS Credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: us-west-2

      - name: Install Claude Code CLI
        run: npm install -g @anthropic-ai/claude-code

      - name: Get PR diff
        id: diff
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          PR_DIFF=$(gh pr diff ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }} 2>/dev/null \
            | head -300 \
            || echo "diff를 가져올 수 없습니다.")
          {
            echo "content<<EOF"
            echo "$PR_DIFF"
            echo "EOF"
          } >> $GITHUB_OUTPUT

      - name: Run Agent Teams Review
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
          GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          PROMPT="PR #${{ github.event.pull_request.number }} 코드를 리뷰해주세요.

          PR 제목: ${{ github.event.pull_request.title }}

          변경 내용:
          ${{ steps.diff.outputs.content }}

          'pr-review' 팀을 구성하여 다음 전문 리뷰어들이 병렬로 분석하도록 해주세요:
          - security-reviewer
          - performance-reviewer
          - test-reviewer
          - architecture-reviewer

          모든 리뷰어의 분석이 완료되면 결과를 종합하여 마크다운 형식으로 보고해주세요."

          claude -p "$PROMPT" \
            --settings '{"teammateMode":"in-process"}' \
            --permission-mode acceptEdits \
            --allowedTools "Read,Grep,Glob,Bash,TeamCreate,TeamDelete,SendMessage,TaskCreate,TaskUpdate,TaskList,Agent" \
            --disallowedTools "Task" \
            --max-budget-usd 3 \
            --output-format stream-json \
            --verbose \
            > /tmp/stream.jsonl 2>&1

      - name: Extract review and post comment
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          REVIEW=$(python3 -c "
          import json, sys

          result = ''
          try:
              with open('/tmp/stream.jsonl') as f:
                  for line in f:
                      line = line.strip()
                      if not line:
                          continue
                      try:
                          obj = json.loads(line)
                          if obj.get('type') == 'result':
                              result = obj.get('result', '')
                              break
                      except json.JSONDecodeError:
                          pass
          except FileNotFoundError:
              pass

          print(result if result else 'Agent Teams 리뷰를 완료하지 못했습니다.')
          ")

          COMMENT="## Claude Agent Teams 코드 리뷰

          ${REVIEW}

          ---
          *Claude Sonnet 4.6 on Amazon Bedrock | Agent Teams (security · performance · test · architecture)*"

          gh pr comment ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }} \
            --body "$COMMENT"

          echo "## Claude Agent Teams 코드 리뷰" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "${REVIEW}" >> $GITHUB_STEP_SUMMARY

      - name: Upload stream log
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: stream-json-pr-${{ github.event.pull_request.number }}
          path: /tmp/stream.jsonl
          retention-days: 7
```

- [ ] **Step 2: YAML 문법 검증**

```bash
python3 -c "
import yaml
with open('.github/workflows/claude-code-review.yml') as f:
    doc = yaml.safe_load(f)

assert doc['on']['pull_request']['types'] == ['opened', 'synchronize', 'reopened'], 'trigger 오류'
assert doc['jobs']['review']['runs-on'] == 'ubuntu-latest', 'runner 오류'
env = doc['env']
assert env['CLAUDE_CODE_USE_BEDROCK'] == '1', 'BEDROCK 환경변수 오류'
assert env['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] == '1', 'AGENT_TEAMS 환경변수 오류'
print('OK: .github/workflows/claude-code-review.yml')
print(f'  트리거: {doc[\"on\"][\"pull_request\"][\"types\"]}')
print(f'  모델: {env[\"ANTHROPIC_MODEL\"]}')
print(f'  에이전트팀: {env[\"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS\"]}')
"
```

예상 출력:
```
OK: .github/workflows/claude-code-review.yml
  트리거: ['opened', 'synchronize', 'reopened']
  모델: us.anthropic.claude-sonnet-4-6
  에이전트팀: 1
```

- [ ] **Step 3: 워크플로우 파일 커밋**

```bash
git add .github/workflows/claude-code-review.yml
git commit -m "Add claude-code-review workflow with Agent Teams

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: CLAUDE.md 업데이트 및 최종 커밋

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md에 PR 리뷰 섹션 추가**

`CLAUDE.md` 파일에서 `## Code Style` 섹션 바로 앞에 다음 섹션을 추가하세요:

```markdown
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
```

추가 후 `## Architecture` 섹션의 핵심 구성 요소 테이블도 업데이트:

```markdown
| `.github/workflows/claude.yml` | @claude 멘션 기반 대화형 응답 |
| `.github/workflows/claude-code-review.yml` | PR 자동 Agent Teams 리뷰 |
| `.claude/agents/*.md` | 전문 리뷰어 에이전트 시스템 프롬프트 |
| `CLAUDE.md` | Claude 실행 시 자동 로드되는 동작 가이드라인 |
```

- [ ] **Step 2: CLAUDE.md 내용 확인**

```bash
grep -n "Agent Teams\|PR 리뷰\|security-reviewer" CLAUDE.md
```

예상 출력 (줄번호는 다를 수 있음):
```
XX:## PR 리뷰 (Agent Teams)
XX:- 각 에이전트 출력 형식: `[HIGH/MED/LOW] 파일명:줄번호 — 설명`
XX:| `security-reviewer` | SQL 인젝션, 하드코딩 비밀, 인증 결함 |
```

- [ ] **Step 3: CLAUDE.md 커밋**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md with Agent Teams PR review guidelines

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 4: 최종 상태 확인**

```bash
git log --oneline -5
```

예상 출력 (최신 3개 커밋 확인):
```
xxxxxxx Update CLAUDE.md with Agent Teams PR review guidelines
xxxxxxx Add claude-code-review workflow with Agent Teams
xxxxxxx Add four specialist review agents for Agent Teams
```

```bash
find .claude/agents .github/workflows -name "*.yml" -o -name "*.md" | sort
```

예상 출력:
```
.claude/agents/architecture-reviewer.md
.claude/agents/performance-reviewer.md
.claude/agents/security-reviewer.md
.claude/agents/test-reviewer.md
.github/workflows/claude-code-review.yml
.github/workflows/claude.yml
```

---

## 통합 테스트 안내

이 워크플로우는 실제 GitHub PR을 통해서만 검증 가능합니다. 구현 완료 후:

1. `app.py` (의도적 결함 포함) 같은 테스트용 Python 파일을 작성
2. 새 브랜치에서 커밋 후 PR 생성
3. Actions 탭에서 `Claude Code Review (Agent Teams)` 워크플로우 실행 확인
4. PR 코멘트에 4개 에이전트 결과 종합 리뷰 게시 확인
5. Actions 탭 > 해당 워크플로우 실행 > Summary에 리뷰 내용 확인
6. Artifacts에서 `stream-json-pr-N` 다운로드 후 Agent Teams 도구 호출 로그 확인
