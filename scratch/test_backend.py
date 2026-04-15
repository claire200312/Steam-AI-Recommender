import requests

def test_recommend():
    url = "http://localhost:8000/recommend"
    payload = {"query": "재밌는 공포 게임 추천해줘"}
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_recommend()
