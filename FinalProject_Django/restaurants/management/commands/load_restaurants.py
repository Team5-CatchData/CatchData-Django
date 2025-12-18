import csv
import os
import google.generativeai as genai
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class Command(BaseCommand):
    help = 'Load restaurant data from new CSV format'

    def handle(self, *args, **kwargs):
        if not GEMINI_API_KEY:
            self.stdout.write(self.style.ERROR('GEMINI_API_KEY is missing!'))
            return

        genai.configure(api_key=GEMINI_API_KEY)
        
        csv_path = 'eating_house_20251216.csv'
        
        if not os.path.exists(csv_path):
             self.stdout.write(self.style.ERROR(f'File not found: {csv_path}'))
             return

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            
            for row in reader:
                if Restaurant.objects.filter(name=row['place_name']).exists():
                    self.stdout.write(self.style.WARNING(f"Skipping {row['place_name']} (Already exists)"))
                    continue
                
                # place_url 생성 (Kakao Map URL 구조)
                generated_place_url = f"https://place.map.kakao.com/{row['id']}" if row.get('id') else ""

                # 검색을 위한 상세 텍스트 구성
                desc_text = (
                    f"맛집 이름: {row['place_name']}, "
                    f"카테고리: {row['category_name']}, "
                    f"주소: {row['road_address_name']}. "
                    f"전화번호: {row['phone'] or '없음'}. "
                    f"평점은 {row['rating']}점, 방문자 리뷰 {row['review_count']}개, 블로그 리뷰 {row['blog_count']}개입니다."
                )

                embedding_vector = None
                
                try:
                    response = genai.embed_content(
                        model="models/text-embedding-004",
                        content=desc_text,
                        task_type="retrieval_document",
                        title="Restaurant Description"
                    )
                    embedding_vector = response['embedding']
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error embedding {row['place_name']}: {e}"))
                    continue

                if embedding_vector is None:
                    continue
                
                try:
                    x_val = float(row['x']) if row['x'] else None
                    y_val = float(row['y']) if row['y'] else None
                    rating_val = float(row['rating']) if row['rating'] else 0.0
                    review_cnt = int(row['review_count']) if row['review_count'] else 0
                    blog_cnt = int(row['blog_count']) if row['blog_count'] else 0
                    waiting_cnt = int(row['waiting']) if row['waiting'] else 0
                except ValueError:
                    x_val, y_val = None, None
                    rating_val, review_cnt, blog_cnt, waiting_cnt = 0.0, 0, 0, 0

                # 주소에서 '구' 단위 또는 '동' 단위 추출 (예: 서울 마포구 상수동 -> 마포구 상수동)
                addr_split = row['address_name'].split()
                location_str = " ".join(addr_split[1:3]) if len(addr_split) > 2 else row['address_name']

                # DB 저장
                Restaurant.objects.create(
                    name=row['place_name'],
                    address=row['road_address_name'],
                    category=row['category_name'],
                    phone=row['phone'],
                    rating=rating_val,
                    review_count=review_cnt,
                    blog_count=blog_cnt,
                    place_url=generated_place_url,
                    img_url=row['img_url'],
                    x=x_val,
                    y=y_val,
                    location=location_str,
                    hourly_visit=row['hourly_visit'],
                    description=desc_text,
                    embedding=embedding_vector,
                    current_waiting_team=waiting_cnt
                )
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Saved: {row['place_name']}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} restaurants!'))