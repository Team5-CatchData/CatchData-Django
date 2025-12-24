import os

import google.genai as genai
from google.genai import types
import psycopg
from django.core.management.base import BaseCommand

from RAG.models import EmbeddedData


class Command(BaseCommand):
    help = "Load restaurant data from Redshift and save to EmbeddedData"

    def handle(self, *args, **kwargs):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        redshift_host = os.getenv("REDSHIFT_HOST")
        redshift_port = os.getenv("REDSHIFT_PORT")
        redshift_user = os.getenv("REDSHIFT_USER")
        redshift_password = os.getenv("REDSHIFT_PASSWORD")
        redshift_db = os.getenv("REDSHIFT_DB")

        if not gemini_api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY is missing in .env!"))
            return

        if not all(
            [
                redshift_host,
                redshift_port,
                redshift_user,
                redshift_password,
                redshift_db,
            ]
        ):
            self.stdout.write(
                self.style.ERROR("Redshift connection info is missing in .env!")
            )
            return

        client = genai.Client(api_key=gemini_api_key)
        conn = None
        cursor = None
        count = 0

        try:
            conn = psycopg.connect(
                host=redshift_host,
                port=redshift_port,
                user=redshift_user,
                password=redshift_password,
                dbname=redshift_db,
                sslmode="require",
                client_encoding="UTF8",
            )
            cursor = conn.cursor()
            self.stdout.write(self.style.SUCCESS("Connected to Redshift"))

            query = """
                SELECT k.id, k.place_name, k.category_name, k.road_address_name,
                       k.phone, k.rating, k.img_url, k.x, k.y,
                       COALESCE(w.waiting, 0) as waiting_count
                FROM raw_data.kakao_crawl k
                LEFT JOIN analytics.realtime_waiting w 
                    ON CAST(k.id AS VARCHAR) = w.id
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                (
                    r_id,
                    name,
                    category,
                    address,
                    phone,
                    rating,
                    img_url,
                    x,
                    y,
                    waiting,
                ) = row

                if EmbeddedData.objects.filter(name=name).exists():
                    self.stdout.write(
                        self.style.WARNING(f"Skipping {name} (Already exists)")
                    )
                    continue

                waiting_count = int(waiting) if waiting else 0
                estimated_time = waiting_count * 10

                desc_text = (
                    f"맛집 이름: {name}, 카테고리: {category}. "
                    f"현재 대기 팀: {waiting_count}팀, 예상 대기시간: {estimated_time}분. "
                    f"주소: {address}, 전화번호: {phone or '없음'}. "
                    f"평점: {rating}점."
                )

                embedding_vector = None
                try:
                    response = client.models.embed_content(
                        model="text-embedding-004",
                        contents=desc_text,
                        config=types.EmbedContentConfig(output_dimensionality=768),
                    )
                    # google.genai SDK 응답 객체에서 실제 벡터 값 추출
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
                    place_url=f"https://place.map.kakao.com/{r_id}" if r_id else "",
                    img_url=img_url,
                    x=float(x) if x else None,
                    y=float(y) if y else None,
                    # location 필드는 blank/default가 없어서 필수이므로 기본값 설정
                    location="Unknown",
                    description=desc_text,
                    embedding=embedding_vector,
                    current_waiting_team=waiting_count,
                    estimated_waiting_time=estimated_time,
                )
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Saved: {name} (Wait: {estimated_time}min)")
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing data: {e}"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            self.stdout.write(
                self.style.SUCCESS(f"Successfully loaded {count} restaurants!")
            )
