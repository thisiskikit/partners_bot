# Neutral Color Migration - Visual Regression Checklist

## 대상 화면
- 로그인 화면
- 목록 화면
- 상세 화면
- 생성 화면

## 점검 기준
1. 각 화면에서 배경/카드/버튼/배지에 분홍 계열 포인트가 보이지 않아야 한다.
2. 아래 패턴이 HTML/CSS/JS 렌더링 경로에 남아있지 않아야 한다.
   - `#f6dce3`, `#efc2d1`, `#d885a2`, `#f4d1dc`, `#fce9ee`
   - `rgba(242, 198, 214`, `rgba(244, 224, 229`, `rgba(243, 193, 208`
3. `:root`의 `--bg`, `--bg-soft`, `--accent`, `--accent-strong`, `--accent-deep`, `--accent-ink`, `--line`, `--shadow-*` 값이 중립 팔레트로 정의되어 있어야 한다.
4. `meta[name="theme-color"]` 값이 새 배경 톤(`#f2f5f9`)과 일치해야 한다.

## 빠른 정적 점검 명령
```bash
rg -n "#f6dce3|#efc2d1|#d885a2|#f4d1dc|#fce9ee|rgba\(242, 198, 214|rgba\(244, 224, 229|rgba\(243, 193, 208" ui_shell
```

## 수동 시각 점검 절차
1. 로그인 → 목록 → 상세 → 생성 순서로 이동한다.
2. 각 화면에서 다음 컴포넌트를 확인한다.
   - 배경 그라디언트
   - 히어로 카드/배지/eyebrow
   - 주요 버튼(primary)
3. 색상 톤이 블루-그레이 기반의 중립 팔레트로 보이는지 확인한다.
