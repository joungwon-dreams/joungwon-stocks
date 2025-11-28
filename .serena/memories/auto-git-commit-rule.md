# Auto Git Commit Rule

## 규칙
**매 작업 완료 시 자동으로 git commit 수행**

## 적용 시점
1. Phase/기능 구현 완료 시
2. 버그 수정 완료 시
3. 최적화 작업 완료 시
4. 문서 업데이트 시
5. 사용자가 "완료" 또는 작업 종료 신호를 보낼 때

## Commit 형식
```bash
git add -A && git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

## Type 종류
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링
- `perf`: 성능 개선
- `docs`: 문서 수정
- `chore`: 기타 작업

## 주의사항
- 사용자가 명시적으로 "커밋 하지마" 라고 하지 않는 한 자동 커밋
- push는 사용자 요청 시에만 수행

*Created: 2025-11-29*
