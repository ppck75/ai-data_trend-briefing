# AI·데이터 기반 콘텐츠 전략가를 위한 RSS 트렌드 브리핑 아카이브

마케팅, 플랫폼, AI, 데이터 트렌드를 RSS로 자동 수집하고 GitHub Pages에서 확인하는 서버리스 브리핑 아카이브입니다. 별도 서버 없이 GitHub Actions가 정기 실행되고, 결과는 `docs/data.json`과 `docs/archive/YYYY-MM-DD.md`에 저장됩니다.

## 주요 기능

- `config.json` 기반 RSS 피드 관리
- `news`, `tech_blog`, `ai_data` group별 수집 분리
- `feedparser` 기반 RSS/Atom 파싱
- 새 글 감지, 중복 제거, 최신 200개 유지
- GitHub Pages용 정적 대시보드 제공
- 일자별 Markdown 아카이브 생성
- 피드 하나가 실패해도 전체 실행은 계속되는 예외 처리
- v1.5 AI 중요도 평가와 이메일 브리핑을 위한 파일 구조 준비

## 기술 스택

- Python 3.11
- feedparser
- GitHub Actions
- GitHub Pages
- HTML, CSS, JavaScript
- JSON, Markdown

## 파일 구조

```text
ai-data-trend-briefing-archive/
├── .github/workflows/
│   ├── news-rss-monitor.yml
│   └── tech-rss-monitor.yml
├── scripts/
│   ├── scraper.py
│   ├── rss_collector.py
│   ├── scorer.py
│   ├── archive_writer.py
│   └── email_sender.py
├── docs/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── data.json
│   └── archive/
├── config.json
├── requirements.txt
├── README.md
└── .gitignore
```

## 1차 MVP RSS 피드

뉴스성 RSS는 30분마다 수집합니다.

- 한국경제
- 매일경제 기업
- 머니투데이
- ZDNet Korea
- BBC Technology
- NYT Technology

기술블로그와 AI·데이터 RSS는 6시간마다 수집합니다.

- 토스 기술블로그
- 당근 기술블로그
- 쿠팡 엔지니어링
- 네이버 D2
- 카카오 기술블로그
- 무신사 테크
- 마켓컬리 기술블로그
- 우아한형제들 기술블로그
- 뱅크샐러드 기술블로그
- arXiv cs.CL
- Anthropic
- Hugging Face Blog
- AWS 한국 블로그

## 로컬 실행

```bash
pip install -r requirements.txt
python scripts/scraper.py --group news
python scripts/scraper.py --group tech_blog,ai_data
```

실행 후 `docs/data.json`과 `docs/archive/YYYY-MM-DD.md`가 생성 또는 갱신됩니다. 새 항목이 없으면 `docs/data.json`은 수정하지 않습니다.

정적 페이지는 로컬에서 `docs/index.html`을 열거나 간단한 서버로 확인할 수 있습니다.

```bash
python -m http.server 8000 -d docs
```

## GitHub Pages 설정

1. GitHub 저장소의 Settings로 이동합니다.
2. Pages 메뉴에서 Source를 `Deploy from a branch`로 선택합니다.
3. Branch는 `main`, folder는 `/docs`로 선택합니다.
4. 저장 후 제공되는 Pages URL에서 대시보드를 확인합니다.

## GitHub Actions

- `news-rss-monitor.yml`: 30분마다 `python scripts/scraper.py --group news` 실행
- `tech-rss-monitor.yml`: 매 6시간 10분에 `python scripts/scraper.py --group tech_blog,ai_data` 실행
- 두 workflow 모두 `workflow_dispatch`를 지원합니다.
- 변경사항이 있을 때만 `docs/data.json`과 `docs/archive`를 commit합니다.

## 보안 및 운영 원칙

- API 키 없이 RSS 수집만 수행합니다.
- `.env`는 Git에 올리지 않습니다.
- 이메일 환경변수는 `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_TO`가 모두 있을 때만 사용합니다.
- 이메일 비밀번호나 API 키는 로그에 출력하지 않습니다.
- Playwright, BeautifulSoup, OpenAI/Gemini 호출은 1차 MVP에 포함하지 않습니다.

## 향후 고도화

- v1.5: Gemini/OpenAI 기반 중요도 평가, 키워드 추출, 기획 인사이트 생성
- v1.5: 일정 기준 이상 항목만 이메일 브리핑 발송
- v2: 공식 changelog와 업데이트 페이지의 정적 스크래핑
- v3: 동적 페이지 모니터링과 고급 대시보드 필터
