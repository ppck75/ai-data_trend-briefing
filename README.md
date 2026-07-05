# RSS 트렌드 브리핑 아카이브 📡

AI·데이터 기반 콘텐츠 전략가를 위한 서버리스 트렌드 모니터링 프로젝트입니다.  
뉴스, 플랫폼 기술블로그, AI·데이터 RSS를 자동 수집하고, 중요한 항목만 선별해 GitHub Pages 대시보드와 날짜별 브리핑 아카이브로 제공합니다.

이 프로젝트의 핵심은 단순 RSS 목록 저장이 아니라, 매일 반복해서 쌓이는 정보 중 콘텐츠 전략 관점에서 확인할 가치가 높은 신호를 추려내는 것입니다.

## 핵심 기능 ✨

- 19개 RSS/Atom 피드를 자동 수집해 마케팅, 플랫폼, AI, 데이터 흐름을 한 화면에서 확인할 수 있습니다.
- `news`, `tech_blog`, `ai_data` 그룹으로 정보를 분리해 뉴스성 이슈, 서비스 기술 사례, AI·데이터 트렌드를 서로 다른 관점에서 비교할 수 있습니다.
- LLM(Gemini) 기반 평가로 각 그룹별 Top 5를 선별해 많은 RSS 항목 중 콘텐츠 전략가가 먼저 확인해야 할 후보를 좁혀줍니다.
- 그룹별 Top 5 총 15개를 다시 비교해 오늘의 통합 Top 5를 만들고, 시장 변화·서비스 기획·AI 활용 관점에서 중요한 신호를 요약합니다.
- 하루 3회 브리핑을 Markdown과 JSON으로 저장해 특정 시점의 트렌드 판단 근거를 날짜와 시간별로 다시 확인할 수 있습니다.
- GitHub Pages 대시보드에서 오늘의 핵심 브리핑, 카테고리별 Top 5, 지난 브리핑, 최신 RSS 원자료를 함께 탐색할 수 있습니다.
- GitHub Actions만으로 수집, 평가, 저장, 배포가 반복되는 서버리스 구조로 설계하여 자동 운영됩니다.
- 향후 주간 브리핑, 키워드 변화 추적, 콘텐츠 기획 리포트 자동화로 확장할 수 있는 데이터 파이프라인 기반을 제공합니다.

## 작동 방식 🔁

```text
RSS 피드 수집
  ↓
docs/data.json 최신 200개 유지
  ↓
그룹별 Top 5 선별
  ↓
총 15개 후보 통합 평가
  ↓
오늘의 통합 Top 5 생성
  ↓
docs/briefing.json + docs/archive 저장
  ↓
GitHub Pages 대시보드 표시
```

## 대시보드 구성 🖥️

- 오늘의 통합 Top 5
- 뉴스성 RSS Top 5
- 플랫폼·서비스 기술블로그 Top 5
- AI·데이터 트렌드 Top 5
- 지난 브리핑 보기
- 최신 200개 RSS 원자료 필터 보기

`docs/data.json`은 최신 RSS 원자료를 보여주기 위한 캐시입니다.  
장기 보관 대상은 전체 RSS 원자료가 아니라 하루 3회 생성되는 Top 5 브리핑입니다.

## 기술 스택 🛠️

- Python 3.11
- feedparser
- google-genai
- python-dotenv
- GitHub Actions
- GitHub Pages
- HTML, CSS, JavaScript
- JSON, Markdown


## 자동화 주기 ⏱️

- 뉴스 RSS 수집: 30분마다
- 기술블로그·AI RSS 수집: KST 03:10, 09:10, 15:10, 21:10
- 핵심 브리핑 생성: KST 07:35, 12:35, 17:35

브리핑은 알림 시간대 전에 GitHub Pages 반영 시간을 확보하기 위해 미리 생성합니다.
저녁 브리핑은 KST 20:50 알림 전에 안정적으로 노출되도록 KST 17:35에 생성합니다.

브리핑 생성 1회당 Gemini 호출은 최대 4회입니다.

- 뉴스 Top 5 선별
- 기술블로그 Top 5 선별
- AI·데이터 Top 5 선별
- 통합 Top 5 선별

## 로컬 실행 💻

```bash
pip install -r requirements.txt

python scripts/scraper.py --group news
python scripts/scraper.py --group tech_blog,ai_data
python scripts/briefing_generator.py
```

로컬에서 브리핑만 테스트하고 아카이브를 만들고 싶지 않다면:

```bash
python scripts/briefing_generator.py --skip-archive
```

Gemini 없이 fallback 평가만 확인하려면:

```bash
python scripts/briefing_generator.py --skip-archive --fallback-only
```

정적 페이지는 다음 명령으로 확인할 수 있습니다.

```bash
python -m http.server 8000 -d docs
```

## 운영 원칙 🔐

- 별도 서버를 사용하지 않습니다.
- RSS 원자료는 최신 200개만 유지합니다.
- 의미 있는 장기 기록은 Top 5 브리핑으로 보관합니다.
- `GEMINI_API_KEY`가 없으면 fallback 평가로 계속 동작합니다.

## 향후 개선 방향 🧭

- 주간 트렌드 브리핑 생성
- 반복 키워드의 주간 변화 추적
- 브리핑 품질 평가 로그 추가
- 관심 키워드 기반 개인화 필터
- 공식 changelog와 업데이트 페이지 수집 확장
