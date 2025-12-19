import os
import google.generativeai as genai
import psycopg
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant

class Command(BaseCommand):
    help = 'Load restaurant data from Redshift (Joined Tables)'

    def handle(self, *args, **kwargs):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        redshift_host = os.getenv("REDSHIFT_HOST")
        redshift_port = os.getenv("REDSHIFT_PORT")
        redshift_user = os.getenv("REDSHIFT_USER")
        redshift_password = os.getenv("REDSHIFT_PASSWORD")
        redshift_db = os.getenv("REDSHIFT_DB")

        if not gemini_api_key:
            self.stdout.write(self.style.ERROR('GEMINI_API_KEY is missing in .env!'))
            return
        
        if not all([redshift_host, redshift_port, redshift_user, redshift_password, redshift_db]):
            self.stdout.write(self.style.ERROR('Redshift connection info is missing in .env!'))
            return

        genai.configure(api_key=gemini_api_key)

        conn = None
        cursor = None

        try:
            conn = psycopg.connect(
                host=redshift_host,
                port=redshift_port,
                user=redshift_user,
                password=redshift_password,
                dbname=redshift_db
            )
            cursor = conn.cursor()
            self.stdout.write(self.style.SUCCESS("Connected to Redshift"))

            query = """
                SELECT 
                    k.id, 
                    k.place_name, 
                    k.category_name, 
                    k.road_address_name, 
                    k.phone, 
                    k.rating, 
                    k.img_url, 
                    k.x, 
                    k.y, 
                    COALESCE(w.waiting, 0) as waiting_count
                FROM raw_data.kakao_crawl k
                LEFT JOIN analytics.realtime_waiting w 
                    ON CAST(k.id AS VARCHAR) = w.id
                LIMIT 10 -- 테스트용: 10개만 가져오기 | 운영 시: 이 라인 전체 삭제 (전체 데이터 적재)
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            count = 0
            for row in rows:
                r_id, name, category, address, phone, rating, img_url, x, y, waiting = row

                if Restaurant.objects.filter(name=name).exists():
                    self.stdout.write(self.style.WARNING(f"Skipping {name} (Already exists)"))
                    continue

                desc_text = (
                    f"맛집 이름: {name}, 카테고리: {category}, "
                    f"주소: {address}, 전화번호: {phone or '없음'}. "
                    f"평점: {rating}점."
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
                    self.stdout.write(self.style.ERROR(f"Error embedding {name}: {e}"))
                    continue

                if embedding_vector is None:
                    continue

                Restaurant.objects.create(
                    name=name,
                    address=address,
                    category=category,
                    phone=phone,
                    rating=float(rating) if rating else 0.0,
                    place_url=f"https://place.map.kakao.com/{r_id}" if r_id else "",
                    img_url=img_url,
                    x=float(x) if x else None,
                    y=float(y) if y else None,
                    description=desc_text,
                    embedding=embedding_vector,
                    current_waiting_team=int(waiting) if waiting else 0
                )
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Saved: {name} (Waiting: {waiting})"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing data: {e}"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} restaurants from Redshift!'))