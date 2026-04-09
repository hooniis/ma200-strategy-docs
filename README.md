# 200일선 매매법 문서 (Mintlify)

Mintlify 기반 문서 사이트. [아기티큐 블로그](https://blog.naver.com/humblich/224019523362)의
200일선 매매법 전략을 정리·백테스트·재검증한 개인 학습 자료입니다.

## 📂 구조

```
docs/
├── docs.json              # Mintlify 설정
├── introduction.mdx       # 랜딩 페이지
├── strategy/
│   ├── overview.mdx       # 전략 상세 분석
│   └── playbook.mdx       # 실전 매매 가이드
├── backtest/
│   ├── results.mdx        # 2010-2026 백테스트
│   ├── trades.mdx         # 거래 이력 (32회)
│   └── whipsaw.mdx        # 파라미터 실험
└── images/
    └── backtest-chart.png
```

## 🚀 배포 방법 (GitHub + Mintlify)

### 1단계. 로컬 미리보기 (선택)

```bash
# Mintlify CLI 설치
npm i -g mint

# docs 디렉토리에서 실행
cd docs
mint dev
# → http://localhost:3000 열림
```

### 2단계. GitHub 저장소 생성

```bash
cd /Users/sunghoon.lee/workspace/ma200-strategy/docs

git init
git add .
git commit -m "docs: initial 200MA strategy documentation"

# GitHub에 새 repo 생성 후 (예: ma200-strategy-docs, Public)
git branch -M main
git remote add origin https://github.com/hooniis/ma200-strategy-docs.git
git push -u origin main
```

### 3단계. Mintlify 연결

1. https://dashboard.mintlify.com 접속 후 로그인 (GitHub OAuth)
2. **"Add a deployment"** 클릭
3. GitHub App 설치 → `hooniis/ma200-strategy-docs` 저장소 선택
4. **Root directory** 를 `/` 로 설정 (docs.json이 루트에 있으므로)
5. 배포 완료 → `hooniis.mintlify.app` 또는 커스텀 도메인 URL 생성됨

### 4단계. 자동 배포

- `main` 브랜치에 push할 때마다 Mintlify가 자동으로 재빌드
- 변경사항은 보통 1~2분 내 반영

## 📝 수정 가이드

### 새 페이지 추가
1. 적절한 폴더에 `.mdx` 파일 생성
2. 파일 상단에 frontmatter 추가:
   ```yaml
   ---
   title: "페이지 제목"
   description: "짧은 설명"
   ---
   ```
3. `docs.json`의 `navigation.tabs[].groups[].pages` 배열에 파일 경로 추가 (확장자 제외)

### 스타일/색상 변경
`docs.json`의 `colors` 키 수정:
```json
"colors": {
  "primary": "#1f77b4",
  "light": "#4a9fd8",
  "dark": "#0d4f7a"
}
```

## 🔗 참고

- Mintlify 공식 문서: https://mintlify.com/docs
- 원 전략 블로그: https://blog.naver.com/humblich/224019523362

## ⚠️ 고지

이 문서는 개인 학습 자료이며 투자 권유가 아닙니다.
모든 투자 결정과 결과의 책임은 투자자 본인에게 있습니다.
