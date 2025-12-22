import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from RAG.models import EmbeddedData

class RagApiTest(TestCase):
    databases = {'default', 'vectordb'}  # 멀티 DB 사용 시 명시 필요

    def setUp(self):
        """테스트 시작 전 데이터 적재"""
        self.client = Client()
        self.url = reverse('main:rag_api')
        
        # 기존 데이터가 없다면 test_embedding 커맨드 실행하여 CSV 데이터 로드
        if EmbeddedData.objects.count() == 0:
            print("\n[Test Setup] Loading test data from CSV...")
            call_command('test_embedding')
        else:
            print("\n[Test Setup] Data already exists.")

    def test_rag_chat_api(self):
        """RAG 채팅 API 동작 및 응답 확인"""
        # 1. 질문 설정
        test_message = "강남역 근처 맛집 추천해줘"
        print(f"\n[Test] User Message: {test_message}")
        print("-" * 50)

        # 2. API 호출
        response = self.client.post(
            self.url,
            data=json.dumps({'message': test_message}),
            content_type='application/json'
        )

        # 3. 상태 코드 확인
        self.assertEqual(response.status_code, 200, f"API failed with status {response.status_code}")
        
        # 4. 응답 데이터 확인 및 출력
        data = response.json()
        
        if 'error' in data:
            print(f"Error Response: {data['error']}")
        else:
            print(f"Answer: {data.get('answer')}")
            print(f"Recommended Restaurants IDs: {data.get('restaurant_ID')}")
            
            # 추천된 ID가 실제로 DB에 있는지 확인
            ids = data.get('restaurant_ID', [])
            if ids:
                exists = EmbeddedData.objects.filter(place_id__in=ids).exists()
                print(f"Recommended items exist in DB: {exists}")

        print("-" * 50)