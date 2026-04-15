import json
import os
import re

# 처리할 노트북 파일 목록
notebook_files = [
    'architecture/rag_modeling.ipynb',
    'architecture/check_absa.ipynb',
    'architecture/check_recommend.ipynb'
]

# 찾아서 지울 API 키 패턴 (일부만 매칭되어도 지우도록 정규식 사용)
api_key_pattern = r'sk-proj-[a-zA-Z0-9_-]+'

def cleanup_notebook(file_path):
    if not os.path.exists(file_path):
        print(f"[SKIP] 파일을 찾을 수 없음: {file_path}")
        return

    print(f"[PROCESS] 세척 중: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        nb_data = json.load(f)

    modified = False
    for cell in nb_data.get('cells', []):
        if cell.get('cell_type') == 'code':
            new_source = []
            for line in cell.get('source', []):
                # API 키가 포함된 라인을 발견하면 환경 변수 로드 방식으로 변경
                if re.search(api_key_pattern, line):
                    # 키 할당 부분만 os.getenv()로 교체
                    line = re.sub(f'"{api_key_pattern}"', 'os.getenv("OPENAI_API_KEY")', line)
                    line = re.sub(f"'{api_key_pattern}'", 'os.getenv("OPENAI_API_KEY")', line)
                    modified = True
                new_source.append(line)
            cell['source'] = new_source

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(nb_data, f, ensure_ascii=False, indent=1)
        print(f"[SUCCESS] 세척 완료 및 저장: {file_path}")
    else:
        print(f"[OK] 지울 키가 발견되지 않음: {file_path}")

if __name__ == "__main__":
    # 프로젝트 루트 폴더에서 실행한다고 가정
    for nb in notebook_files:
        cleanup_notebook(nb)
    print("\n[DONE] 모든 노트북 세척 작업이 끝났습니다!")
