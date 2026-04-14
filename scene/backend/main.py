from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

app = FastAPI()

# 1. CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실 운영 시에는 프론트엔드 주소로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 전역 설정 및 모델 초기화
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# .env 파일 경로를 루트 폴더로 명시적 지정, override=True를 추가하여 시스템 환경변수보다 .env 우선
load_dotenv(os.path.join(BASE_DIR, "../../.env"), override=True)

CHROMA_PATH = os.path.join(BASE_DIR, "../../architecture/chroma_db")

# API 키 누락 여부 확인
if not os.getenv("OPENAI_API_KEY"):
    print("[ERROR] OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

embeddings = OpenAIEmbeddings()

# Vector DB 초기화 (노트북에서 생성된 폴더를 읽어옴)
try:
    if os.path.exists(CHROMA_PATH):
        vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        retriever = vector_db.as_retriever(search_kwargs={"k": 5}) # 검색 개수를 노트북 수준(5개)으로 상향
        print(f"[SUCCESS] Vector DB 로드 완료: {CHROMA_PATH}")
    else:
        print(f"[WARNING] Vector DB 경로를 찾을 수 없습니다: {CHROMA_PATH}")
        vector_db = None
        retriever = None
except Exception as e:
    print(f"[ERROR] Vector DB 초기화 실패: {e}")
    vector_db = None
    retriever = None

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 3. CSV 데이터 로드 (관리자 대시보드 연동용)
CSV_PATH = os.path.join(BASE_DIR, "../../reviewdata/popgame.csv")

def load_reviews_from_csv():
    encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']
    for enc in encodings:
        try:
            if os.path.exists(CSV_PATH):
                # on_bad_lines='skip'을 추가하여 데이터 형식이 깨진 행을 무시하고 로드
                df = pd.read_csv(CSV_PATH, encoding=enc, on_bad_lines='skip', engine='python')
                return df
        except Exception as e:
            continue
    print(f"CSV Load Error: 파일이 없거나 모든 인코딩 시도 실패 ({CSV_PATH})")
    return None

# 4. 인메모리 로그 (데모용)
query_logs = []

# 4. 데이터 모델
class RecommendRequest(BaseModel):
    query: str

class SentimentModel(BaseModel):
    스토리: int
    그래픽: int
    최적화: int
    밸런스: int
    액션: int

class RecommendResponse(BaseModel):
    game_name: str
    summary: str
    reason: str
    tags: List[str]
    sentiment: SentimentModel

# 4. Steam 가용성 체크 함수
async def check_steam_availability(game_name: str) -> bool:
    """Steam Store Search API를 통해 게임이 현재 다운로드/구매 가능한지 확인합니다."""
    try:
        # Steam 스토어 검색 API (한국 지역 기준)
        url = f"https://store.steampowered.org/api/storesearch/?term={game_name}&l=korean&cc=KR"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # 검색 결과가 있고, ID가 존재하면 판매 중으로 간주
                if data.get("total", 0) > 0:
                    return True
    except Exception as e:
        print(f"Availability check error for {game_name}: {e}")
        return True # 에러 발생 시에는 보수적으로 추천에 포함
    return False

# 5. RAG 추천 로직
@app.post("/recommend", response_model=List[RecommendResponse])
async def recommend_games(request: RecommendRequest):
    try:
        # 1. 자연어 전처리
        query = request.query.strip()
        print(f"\n[DEBUG] 사용자 질문: {query}")
        
        # 2. 관련 리뷰 검색 (Vector DB)
        if retriever:
            docs = await asyncio.to_thread(retriever.invoke, query)
            print(f"[DEBUG] Vector DB 검색 결과 수: {len(docs)}")
        else:
            docs = []
            print("[DEBUG] Retriever가 초기화되지 않음")
        
        # 3. CSV 직접 검색 (백업 로직 강화)
        if len(docs) < 1:
            print("[DEBUG] Vector DB 결과 없음, CSV 백업 검색 시작...")
            df = load_reviews_from_csv()
            if df is not None:
                # 검색 방해 단어 필터링 강화
                import re
                clean_query = re.sub(r'[^\w\s]', '', query)
                stop_words = ["추천", "게임", "해줘", "알려줘", "같은", "비슷한", "어떤", "이게", "거", "뭐냐", "말고", "해서", "에서", "있냐", "없냐", "관련", "재밌는", "재미있는"]
                keywords = [k for k in clean_query.split() if len(k) > 1 and k not in stop_words]
                
                if not keywords: 
                    keywords = [query]
                
                print(f"[DEBUG] 추출된 키워드: {keywords}")
                
                content_col = df.columns[4] if len(df.columns) > 4 else df.columns[-1]
                # 주요 키워드로 검색 후 무작위 추출하여 답변 다양성 확보
                mask = df[content_col].str.contains(keywords[0], na=False, case=False)
                filtered_df = df[mask]
                
                if not filtered_df.empty:
                    sample_size = min(15, len(filtered_df))
                    temp_df = filtered_df.sample(n=sample_size)
                    
                    print(f"[DEBUG] CSV 검색된 리뷰 수: {len(temp_df)}")
                    
                    from langchain_core.documents import Document
                    for _, row in temp_df.iterrows():
                        docs.append(Document(
                            page_content=str(row[content_col]),
                            metadata={"game_name": str(row.iloc[0])}
                        ))
                else:
                    print(f"[DEBUG] '{keywords[0]}' 키워드로 결과를 찾지 못함")
        
        if not docs:
            print("[DEBUG] 최종 검색된 문서가 없음")
            return []
        
        # 중복 게임 제거 및 이름 추출
        unique_game_docs = {}
        for d in docs:
            name = d.metadata.get('game_name')
            if name and name not in unique_game_docs:
                unique_game_docs[name] = d
        
        # 실시간 가용성 체크 (병렬 처리)
        game_names = list(unique_game_docs.keys())
        availability_results = await asyncio.gather(*[check_steam_availability(name) for name in game_names])
        
        available_docs = []
        for name, is_available in zip(game_names, availability_results):
            if is_available:
                available_docs.append(unique_game_docs[name])
            else:
                print(f"Game delisted or unavailable: {name}")
        
        # 필터링된 결과가 있으면 사용, 없으면 검색된 전체 결과 중 상위 사용 (안전 장치)
        final_docs = available_docs[:5] if available_docs else list(unique_game_docs.values())[:3]
        
        # LLM에게 전달할 컨텍스트 구성
        context_list = []
        for d in final_docs:
            game_name = d.metadata.get('game_name', '알 수 없음')
            context_list.append(f"[게임명: {game_name}] {d.page_content}")
        
        context = "\n".join(context_list)
        print(f"[DEBUG] LLM에게 전달될 컨텍스트 구성 완료 (리뷰 {len(context_list)}건)")
        
        # 프론트엔드에서 요구하는 JSON 형식으로 반환하도록 프롬프트 구성
        template = """
        당신은 게임 추천 AI 전문가입니다.
        아래 검색된 리뷰 데이터를 기반으로 사용자의 질문에 답하세요.
        
        **중요 규칙:**
        1. 질문에 '재미', '게임', '추천' 등 게임 관련 키워드가 있다면 Context를 최대한 활용하여 긍정적으로 답변하세요.
        2. 검색된 Context가 부족하더라도 아는 범위 내에서 유용한 추천을 제공하세요.
        
        Context: {context}
        Question: {question}
        
        반드시 다음 JSON 배열 형식으로만 답변하세요. 
        **주의1: "game_name"은 반드시 Context에 명시된 원문 그대로(보통 영문) 작성하세요.**
        **주의2: sentiment의 키값은 반드시 '스토리', '그래픽', '최적화', '밸런스', '액션'이라는 한글 단어만 사용하세요.**
        
        [
          {{
            "game_name": "Context에 나온 원문 이름",
            "summary": "리뷰 요약 (한 문장)",
            "reason": "추천 이유",
            "tags": ["태그1", "태그2"],
            "sentiment": {{"스토리": 5, "그래픽": 4, "최적화": 3, "밸런스": 4, "액션": 5}}
          }}
        ]
        """
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm
        
        # LLM 실행 (노트북과 동일한 query 변수 사용)
        response = await asyncio.to_thread(chain.invoke, {"context": context, "question": query})
        
        # JSON 결과 파싱 (정규표현식을 사용하여 JSON 블록만 추출)
        import re
        content = response.content.strip()
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        else:
            # 대괄호가 없는 경우 (단일 객체일 가능성 등 대비)
            content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            results = json.loads(content)
        except json.JSONDecodeError as json_err:
            print(f"[ERROR] JSON Parsing Failed: {json_err}\nRaw Content: {content}")
            raise HTTPException(status_code=500, detail="LLM의 응답 형식이 올바르지 않습니다.")
        
        # 쿼리 로그 저장
        query_logs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": request.query,
            "results": [r.get("game_name", "Unknown") for r in results]
        })
        
        return results
        
    except Exception as e:
        print(f"[CRITICAL ERROR] {str(e)}")
        # OpenAI API 에러인 경우 더 명확한 메시지 제공
        if "invalid_api_key" in str(e) or "401" in str(e):
            raise HTTPException(status_code=401, detail="OpenAI API 키가 유효하지 않습니다. .env 파일을 확인해주세요.")
        raise HTTPException(status_code=500, detail=str(e))

# 6. 관리자 API
@app.get("/admin/queries")
async def get_queries():
    return query_logs

@app.get("/admin/games")
async def get_games():
    """CSV와 ChromaDB에서 고유 게임 목록을 가져옵니다."""
    try:
        unique_games = {}
        
        # 1. CSV에서 먼저 가져오기 (연동 보장)
        df = load_reviews_from_csv()
        if df is not None:
            # 첫 번째 컬럼이 게임명으로 추정됨
            game_col = df.columns[0]
            counts = df[game_col].value_counts().to_dict()
            for name, count in counts.items():
                unique_games[name] = {"name": name, "count": count}
        
        # 2. ChromaDB 데이터 추가 (있을 경우)
        all_data = vector_db.get()
        metadatas = all_data.get('metadatas', [])
        for meta in metadatas:
            name = meta.get('game_name')
            if name:
                if name not in unique_games:
                    unique_games[name] = {"name": name, "count": 1}
                else:
                    # 중복 합산 (실제로는 CSV와 겹치겠지만 카운트 업데이트)
                    unique_games[name]["count"] += 1
        
        return list(unique_games.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/reviews")
async def get_all_reviews(limit: int = 50):
    """전체 리뷰를 가져옵니다 (CSV 우선)."""
    try:
        df = load_reviews_from_csv()
        results = []
        if df is not None:
            game_col = df.columns[0]
            content_col = df.columns[4] if len(df.columns) > 4 else df.columns[-1]
            for _, row in df.head(limit).iterrows():
                results.append({
                    "content": str(row[content_col]),
                    "metadata": {"game_name": str(row[game_col])}
                })
            return results
        
        # CSV 실패 시 ChromaDB
        all_data = vector_db.get(limit=limit)
        for i in range(len(all_data['documents'])):
            results.append({
                "content": all_data['documents'][i],
                "metadata": all_data['metadatas'][i]
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/game-reviews/{game_name}")
async def get_game_reviews(game_name: str):
    """특정 게임의 리뷰를 가져옵니다 (CSV 우선)."""
    try:
        df = load_reviews_from_csv()
        if df is not None:
            game_col = df.columns[0]
            content_col = df.columns[4] if len(df.columns) > 4 else df.columns[-1]
            filtered = df[df[game_col] == game_name]
            reviews = []
            for _, row in filtered.iterrows():
                reviews.append({
                    "content": str(row[content_col]),
                    "metadata": {"game_name": game_name}
                })
            if reviews:
                return reviews

        # CSV에 없거나 실패 시 ChromaDB 필터
        results = vector_db.get(where={"game_name": game_name})
        reviews = []
        for i in range(len(results['documents'])):
            reviews.append({
                "content": results['documents'][i],
                "metadata": results['metadatas'][i]
            })
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
