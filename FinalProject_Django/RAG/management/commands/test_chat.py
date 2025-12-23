import json
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from RAG.views import rag_chat_api  # 뷰 함수 직접 import

class Command(BaseCommand):
    help = "Test rag_chat_api view directly by simulating a request"

    def handle(self, *args, **kwargs):
        # ---------------------------------------------------------
        # [설정] 테스트할 질문을 이곳에 적어주세요.
        TEST_QUESTION = "20분 후에 먹을 거 추천해줘"
        # ---------------------------------------------------------

        self.stdout.write(self.style.SUCCESS(f"\n[Test Start] Question: {TEST_QUESTION}"))
        self.stdout.write("-" * 50)

        # 1. 가짜(Mock) 요청 객체 생성
        # 마치 프론트엔드에서 POST 요청을 보낸 것처럼 Request 객체를 만듭니다.
        factory = RequestFactory()
        request = factory.post(
            '/rag/api/chat/',
            data=json.dumps({'message': TEST_QUESTION}), # JSON 데이터 전송
            content_type='application/json'
        )

        # 2. View 함수 실행
        # views.py를 수정하지 않고, import해온 함수에 request를 넣어 실행합니다.
        try:
            response = rag_chat_api(request)
            
            # 3. 결과 파싱 및 출력
            if response.status_code == 200:
                # JsonResponse 본문(body)을 읽어서 파이썬 딕셔너리로 변환
                response_data = json.loads(response.content.decode('utf-8'))
                
                answer = response_data.get('answer', 'No answer')
                restaurant_ids = response_data.get('restaurant_ID', [])

                self.stdout.write(self.style.SUCCESS("Status: 200 OK"))
                self.stdout.write(self.style.SUCCESS("\n[AI Answer]"))
                self.stdout.write(answer)
                
                self.stdout.write(f"\n[Recommended Restaurant IDs]: {restaurant_ids}")
            else:
                self.stdout.write(self.style.ERROR(f"Failed with status code: {response.status_code}"))
                self.stdout.write(f"Error Content: {response.content.decode('utf-8')}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error executing view: {e}"))
            # 에러 발생 시 상세 정보 출력을 위해 traceback 모듈 사용 가능
            import traceback
            self.stdout.write(traceback.format_exc())

        self.stdout.write("-" * 50)