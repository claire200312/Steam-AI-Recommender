# Steam Recommend: AI 기반 리뷰 분석 게임 추천 시스템 상세 설계 가이드

## 1. 프로젝트 개요 (Project Overview)
**Steam Recommend**는 실제 플레이어들의 리뷰 데이터 감성 분석(Sentiment Analysis)과 LLM(대형 언어 모델)을 결합하여, 유저의 취향에 딱 맞는 게임을 찾아주고 그 **'추천 이유'**를 명확하게 설명해주는 지능형 Steam 게임 추천 웹 서비스입니다. 

단순히 인기순, 평점순 정렬을 넘어 "스토리가 좋은 게임", "타격감이 뛰어난 액션 게임"과 같은 사용자의 구체적인 자연어 요청을 이해하고 답변하는 것이 핵심입니다.

## 2. 주요 기능 및 UI/UX 명세 (첨부 예시 기반)

### ✅ 메인 검색 화면
*   **장르 기반 탐색 필터**: 사용자가 직관적으로 선택할 수 있는 장르 태그 제공 (액션, RPG, 어드벤처, 전략, 시뮬레이션, 생존, FPS, 호러, 인디, 무료 플레이).
*   **자연어 검색 바 (Prompt Input)**: "스토리가 좋은 게임을 추천해줘" 등 사용자가 원하는 조건과 게임의 느낌을 자연어로 입력.

### ✅ 추천 결과 카드 (Result Card)
*   **기본 메타 데이터 제공**: 순위, 게임명(예: Stray, Ghost of Tsushima), 장르 태그, 가격, 긍정 리뷰 비율(예: 100% 긍정), 평균 플레이 시간.
*   **AI 추천 사유 (AI Generated Summary)**: 
    *   수많은 유저 리뷰를 종합하여 사용자의 검색 조건(예: 스토리)에 얼마나 잘 부합하는지 AI가 요약 생성.
    *   단순 장점뿐 아니라 "짧은 플레이 타임이 아쉽지만...", "단조로워서 아쉬운 점이 있습니다" 등 리뷰에서 공통으로 지적되는 단점/주의점까지 분석하여 입체적이고 객관적인 정보를 제공.
*   **핵심 유저 리뷰 인용 (Key Sentences)**:
    *   AI 요약의 근거가 되는 실제 유저의 "가장 공감되는/대표적인 리뷰" 원문과 작성자의 플레이타임(예: 8h 플레이)을 2~3개 발췌하여 신뢰성 부여.

## 3. 시스템 아키텍처 및 파이프라인 설계

### 3.1. 데이터 수집 파이프라인 (Data Pipeline)
이미 작성된 `popgame_reviewdata.ipynb` 스크립트를 확장/운용하여 다음 데이터를 구축.
*   **Game Meta:** Steam API를 통한 상위 인기 게임 기본 정보 수집.
*   **Reviews:** 게임당 1,000개의 한국어 리뷰 수집 및 전처리(가독성 10자 이상, 특수문자 제거 전략 적용).

### 3.2. NLP 및 AI 모델링 파이프라인 (RAG Architecture)
추천의 핵심은 사용자의 의도 파악과 **리뷰 대상 감성 분석(ABSA, Aspect-Based Sentiment Analysis)**입니다.
1.  **속성 분리 (Aspect Extraction)**: 리뷰 텍스트 내에서 게임의 특정 속성(스토리, 그래픽, 최적화, 밸런스, 타격감 등)을 추출.
2.  **감성 분석 (Sentiment Analysis)**: 각 속성별 긍정/부정 스코어링 진행.
3.  **Vector Embedding**: 리뷰 데이터와 분석 데이터를 임베딩(Embedding)하여 Vector DB 공간에 저장.
4.  **RAG (Retrieval-Augmented Generation) 쿼리**:
    *   유저 검색어 입력 시 Vector DB에서 가장 유사한 특징을 가진 게임의 메타데이터와 리뷰 데이터 검색.
    *   LLM(OpenAI 등)에게 검색된 실제 리뷰 데이터 컨텍스트를 주입(Prompting).
    *   LLM이 "사용자 맞춤형 추천 요약문(장/단점 포함)"을 최종 생성.

## 4. 데이터베이스 및 저장소 구조 (Database Schema)

*   **RDBMS (PostgreSQL 또는 MySQL)**:
    *   `Game Table`: App ID, 제목, 가격, 장르 태그 등 기본 메타 정보.
    *   `Review Table`: Review ID, 원문 텍스트, 사용자 플레이타임, 긍/부정 여부.
*   **Vector DB (ChromaDB, Pinecone, FAISS 등)**:
    *   리뷰와 속성 정보를 차원 공간에 맵핑해둔 임베딩 데이터베이스. (유저 자연어 검색과 가장 밀접하게 매칭하기 위해 필수적)

## 5. 단계별 개발 마일스톤 (Development Phases)

*   **[Phase 1] 데이터 수집 및 정제 시스템 완료 (Data Prep)**
    *   데이터 크롤러 보강 (Steam Data)
    *   리뷰 텍스트 클리닝 파이프라인 구축
*   **[Phase 2] 모델링 및 감성 분석 (NLP AI)**
    *   사전학습된 한국어 NLP 언어모델(KoBERT 등) 혹은 LLM을 통한 리뷰 속성(Aspect) 추출.
    *   추출된 속성별 감성 점수 테이블 구축 및 Vector DB 이관.
*   **[Phase 3] 검색/추천 백엔드 구축 (Backend & RAG 구축)**
    *   유저의 입력을 받아 VectorDB 쿼리 -> 관련 리뷰 탐색 로직 작성.
    *   LangChain 등을 활용한 LLM Prompt Engineering (게임 요약 추천문 생성 테스트).
*   **[Phase 4] 프론트엔드 통합 (Frontend UI)**
    *   첨부된 디자인(검은색 배경의 다크모드, 초록색 포인트 컬러, 깔끔한 정보 카드 구조)을 반영한 React 또는 Next.js 웹 뷰 구현.
    *   백엔드 API 연동 및 테스트.
