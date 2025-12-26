import csv
import os

import google.genai as genai
from django.conf import settings
from django.core.management.base import BaseCommand
from google.genai import types
from RAG.models import EmbeddedData


class Command(BaseCommand):
    help = "Load restaurant data from CSV files and save to EmbeddedData for testing"

    def handle(self, *args, **kwargs):
        # 1. API 키 확인
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY is missing in .env!"))
            return

        client = genai.Client(api_key=gemini_api_key)

        # 2. CSV 파일 경로 설정
        base_dir = settings.BASE_DIR
        kakao_path = os.path.join(base_dir, 'kakao_crawl.csv')
        waiting_path = os.path.join(base_dir, 'realtime_waiting.csv')

        # 3. 파일 존재 여부 확인
        if not os.path.exists(kakao_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {kakao_path}"))
            return

        if not os.path.exists(waiting_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {waiting_path}"))
            return

        # 4. 웨이팅 데이터 로드 (ID -> Waiting Count 매핑)
        waiting_map = {}
        try:
            with open(waiting_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = row.get('id')
                    cnt = row.get('waiting', 0)
                    if rid:
                        try:
                            # float로 변환 후 int로 변환
                            waiting_map[str(rid)] = int(float(cnt))
                        except ValueError:
                            waiting_map[str(rid)] = 0

            self.stdout.write(
                self.style.SUCCESS(
                    f"Loaded waiting data: {len(waiting_map)} items"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read waiting file: {e}"))
            return

        # 5. 맛집 데이터 로드 및 임베딩
        count = 0
        skipped_no_waiting = 0

        try:
            with open(kakao_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    r_id = row.get('id')
                    name = row.get('place_name')
                    category = row.get('category_name')
                    address = row.get('road_address_name')
                    phone = row.get('phone', '')
                    rating = row.get('rating', '0.0')
                    img_url = row.get('img_url', '')
                    x = row.get('x')
                    y = row.get('y')

                    if not r_id or not name:
                        continue

                    # 웨이팅 데이터에 없는 식당은 건너뛰기
                    if str(r_id) not in waiting_map:
                        skipped_no_waiting += 1
                        continue

                    # 이미 존재하는 데이터 스킵
                    if EmbeddedData.objects.filter(place_id=r_id).exists():
                        continue

                    waiting_count = waiting_map[str(r_id)]
                    estimated_time = waiting_count * 10

                    desc_text = (
                        f"맛집 이름: {name}, 카테고리: {category}. "
                        f"현재 대기 팀: {waiting_count}팀, "
                        f"예상 대기시간: {estimated_time}분. "
                        f"주소: {address}, 전화번호: {phone or '없음'}. "
                        f"평점: {rating}점."
                    )

                    # Google Gemini 임베딩 생성
                    embedding_vector = None
                    try:
                        response = client.models.embed_content(
                            model="text-embedding-004",
                            contents=desc_text,
                            config=types.EmbedContentConfig(output_dimensionality=768),
                        )
                        embedding_vector = response.embeddings[0].values
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error embedding {name}: {e}")
                        )
                        continue

                    if embedding_vector is None:
                        continue

                    EmbeddedData.objects.create(
                        place_id=r_id,
                        name=name,
                        address=address,
                        category=category,
                        phone=phone,
                        rating=float(rating) if rating else 0.0,
                        place_url=f"https://place.map.kakao.com/{r_id}",
                        img_url=img_url,
                        x=float(x) if x and x != '' else 0.0,
                        y=float(y) if y and y != '' else 0.0,
                        location="Unknown",
                        description=desc_text,
                        embedding=embedding_vector,
                        current_waiting_team=waiting_count,
                        estimated_waiting_time=estimated_time,
                    )
                    count += 1
                    if count % 10 == 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Processed {count} restaurants..."
                            )
                        )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing CSV: {e}"))

        self.stdout.write(
            self.style.WARNING(
                f"Skipped {skipped_no_waiting} restaurants (No waiting data)"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully loaded {count} restaurants for testing!"
            )
        )
