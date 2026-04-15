#!/usr/bin/env python3
"""
Claude Code Stop Hook: PRD 자동 업데이트

Claude가 응답을 완료하면 자동 실행됩니다.
- git 변경사항을 감지하여 실제 코드 변경이 있을 때만 동작
- 최근 대화 내용 + 변경 파일 목록을 Upstage LLM에 전달
- 구현 완료된 수락 기준(Acceptance Criteria)을 [ ] → [x] 로 자동 업데이트
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error

# ── 상수 ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PRD_PATH = os.path.join(PROJECT_ROOT, "PRD_영수증_지출관리앱.md")
UPSTAGE_API_URL = "https://api.upstage.ai/v1/chat/completions"
UPSTAGE_MODEL = "solar-pro"


# ── 유틸 함수 ─────────────────────────────────────────────────────────────────

def get_env(key: str) -> str:
    """환경변수 로드 (.env fallback 포함)"""
    value = os.getenv(key, "")
    if not value:
        env_path = os.path.join(PROJECT_ROOT, ".env")
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        value = line[len(key) + 1:].strip().strip('"').strip("'")
                        break
    return value


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    return result.stdout.strip()


def has_code_changes() -> tuple[str, str]:
    """
    코드 변경 여부 확인.
    Returns (changed_tracked, git_status_short)
    """
    changed_tracked = run_git(["diff", "HEAD", "--name-only"])
    git_status = run_git(["status", "--porcelain"])
    return changed_tracked, git_status


def extract_assistant_text(transcript_path: str, max_chars: int = 4000) -> str:
    """트랜스크립트에서 마지막 assistant 응답 텍스트 추출"""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""

    messages = []
    try:
        # JSONL 형식 시도
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        # JSON 배열 형식 fallback
        if not messages:
            with open(transcript_path, encoding="utf-8") as f:
                messages = json.load(f)
    except Exception:
        return ""

    texts = []
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block["text"])
                    break
        elif isinstance(content, str):
            texts.append(content)
        if sum(len(t) for t in texts) >= max_chars:
            break

    combined = "\n\n---\n\n".join(reversed(texts))
    return combined[:max_chars]


def call_llm(prompt: str, api_key: str) -> str:
    """Upstage solar-pro API 호출 (표준 라이브러리만 사용)"""
    payload = json.dumps({
        "model": UPSTAGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 512,
    }).encode("utf-8")

    req = urllib.request.Request(
        UPSTAGE_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"].strip()


def get_unchecked_items(prd_content: str) -> list[str]:
    return re.findall(r"- \[ \] (.+)", prd_content)


def apply_checks(prd_content: str, items: list[str]) -> str:
    for item in items:
        prd_content = prd_content.replace(f"- [ ] {item}", f"- [x] {item}", 1)
    return prd_content


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    # 1. stdin에서 hook 데이터 읽기
    try:
        raw = sys.stdin.read()
        hook_data = json.loads(raw) if raw.strip() else {}
    except Exception:
        hook_data = {}

    # 무한 루프 방지
    if hook_data.get("stop_hook_active"):
        sys.exit(0)

    transcript_path = hook_data.get("transcript_path", "")

    # 2. 코드 변경 여부 확인 — 변경 없으면 종료
    changed_tracked, git_status = has_code_changes()
    has_changes = bool(changed_tracked) or any(
        line and not line.startswith("##")
        for line in git_status.splitlines()
    )
    if not has_changes:
        sys.exit(0)

    # 3. PRD 파일 읽기
    if not os.path.exists(PRD_PATH):
        print("[PRD 훅] PRD 파일을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(0)

    with open(PRD_PATH, encoding="utf-8") as f:
        prd_content = f.read()

    # 4. 미완료 수락 기준 추출
    unchecked = get_unchecked_items(prd_content)
    if not unchecked:
        sys.exit(0)  # 모두 완료됨

    # 5. API 키 확인
    api_key = get_env("UPSTAGE_API_KEY")
    if not api_key:
        print("[PRD 훅] UPSTAGE_API_KEY 없음 — PRD 자동 업데이트 건너뜀", file=sys.stderr)
        sys.exit(0)

    # 6. 대화 컨텍스트 추출
    assistant_context = extract_assistant_text(transcript_path)

    # 7. 변경된 파일 목록 정리
    changed_files_list = (
        changed_tracked
        or "\n".join(
            line[3:].strip()
            for line in git_status.splitlines()
            if line.strip()
        )
    )

    # 8. LLM 프롬프트 작성
    unchecked_numbered = "\n".join(
        f"{i + 1}. {item}" for i, item in enumerate(unchecked)
    )
    prompt = f"""당신은 소프트웨어 프로젝트 관리자입니다.
아래 정보를 바탕으로, 이번 구현 작업에서 완료된 수락 기준(Acceptance Criteria) 항목의 번호를 식별하세요.

## 변경된 파일 목록
{changed_files_list[:1000]}

## Claude가 이번에 구현한 내용 (요약)
{assistant_context[:3000] if assistant_context else "트랜스크립트 없음"}

## PRD 미완료 수락 기준 목록
{unchecked_numbered}

---
위 내용을 바탕으로, 이번 작업에서 구현 완료된 항목 번호만 쉼표로 나열하세요.
완료된 항목이 없으면 "없음" 이라고만 답하세요.
예시: 1, 3, 7
다른 설명은 하지 마세요."""

    # 9. LLM 호출
    try:
        response = call_llm(prompt, api_key)
    except urllib.error.URLError as e:
        print(f"[PRD 훅] API 호출 실패: {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"[PRD 훅] 오류: {e}", file=sys.stderr)
        sys.exit(0)

    if not response or response.strip() == "없음":
        sys.exit(0)

    # 10. 완료 항목 파싱
    try:
        indices = [
            int(x.strip()) - 1
            for x in re.split(r"[,\s]+", response)
            if x.strip().isdigit()
        ]
    except Exception:
        sys.exit(0)

    items_to_check = [
        unchecked[i] for i in indices if 0 <= i < len(unchecked)
    ]
    if not items_to_check:
        sys.exit(0)

    # 11. PRD 파일 업데이트
    updated = apply_checks(prd_content, items_to_check)
    with open(PRD_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(
        f"[PRD 자동 업데이트] {len(items_to_check)}개 수락 기준 완료 처리됨:",
        file=sys.stderr,
    )
    for item in items_to_check:
        print(f"  ✓ {item}", file=sys.stderr)


if __name__ == "__main__":
    main()
