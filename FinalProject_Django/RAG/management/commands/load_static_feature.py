import csv
import json
import os
import time

import google.genai as genai
from django.conf import settings
from django.core.management.base import BaseCommand
from google.genai import types

from RAG.models import EmbeddedData

# RAG 앱 폴더 기준 상대 경로 (개인 로컬 경로에 의존하지 않도록)
DEFAULT_CSV_PATH = os.path.join(settings.BASE_DIR, "RAG", "static_feature.csv")

# static_feature.csv에는 실시간 대기열 데이터가 없다. 대신 time0~time23(시간대별
# 방문/혼잡 지수)가 있는데, 데이터가 있는 행의 분포를 보면 비혼잡 시간대 baseline이
# 약 16~17이고 점심/저녁 피크에 30~76까지 오른다. baseline을 초과하는 만큼을
# 10분 단위 '대기 팀 수'로 환산한 근사치이며, 실측 웨이팅 데이터가 아니다.
CONGESTION_BASELINE = 17
MINUTES_PER_TEAM = 10
MAX_TEAM = 8


def congestion_to_wait(congestion_value: int) -> tuple[int, int]:
    excess = max(0, congestion_value - CONGESTION_BASELINE)
    team = min(MAX_TEAM, round(excess / 10))
    return team, team * MINUTES_PER_TEAM


class Command(BaseCommand):
    help = (
        "static_feature.csv(실제 카카오 크롤링 데이터 + 시간대별 혼잡도 피처)를 읽어 "
        "EmbeddedData에 적재하고 Gemini 임베딩을 생성한다. "
        "대기시간은 time{hour} 혼잡도 지수를 baseline 초과분 기준으로 환산한 근사치이므로 "
        "설명(description)에도 '추정치'임을 명시해 둔다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path", type=str, default=DEFAULT_CSV_PATH,
            help=f"static_feature.csv 경로 (기본: {DEFAULT_CSV_PATH})",
        )
        parser.add_argument(
            "--hour", type=int, default=18,
            help="적재 시점 스냅샷 기준 시각(0-23). 기본 18시(저녁 피크) "
                 "— 대기시간 변주가 잘 드러나는 시간대를 골랐다.",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="테스트용으로 앞에서부터 N개만 적재 (기본: 전체)",
        )
        parser.add_argument(
            "--sleep-ms", type=int, default=0,
            help="임베딩 API 레이트리밋에 걸릴 경우 호출 사이 지연(ms)",
        )

    def handle(self, *args, **options):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY is missing in .env!"))
            return

        csv_path = options["csv_path"]
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        hour = options["hour"]
        if not (0 <= hour <= 23):
            self.stdout.write(self.style.ERROR("--hour must be between 0 and 23"))
            return

        client = genai.Client(api_key=gemini_api_key)

        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        if options["limit"]:
            rows = rows[: options["limit"]]

        count = 0
        skipped_existing = 0
        skipped_error = 0

        for i, row in enumerate(rows, start=1):
            r_id = row.get("id")
            name = row.get("place_name")
            if not r_id or not name:
                continue

            if EmbeddedData.objects.filter(place_id=r_id).exists():
                skipped_existing += 1
                continue

            sub_category = row.get("sub_category", "")
            category_name = row.get("category_name", "")
            district = row.get("main_district", "")
            address = row.get("road_address_name") or row.get("address_name", "")
            phone = row.get("phone", "")
            rating = row.get("rating") or "0.0"
            review_count = row.get("review_count") or 0
            blog_count = row.get("blog_count") or 0
            img_url = row.get("img_url", "")
            x = row.get("x")
            y = row.get("y")

            hourly_visit = [int(row.get(f"time{h}", 0) or 0) for h in range(24)]
            has_congestion_data = any(v != 0 for v in hourly_visit)
            team, wait_min = congestion_to_wait(hourly_visit[hour])

            congestion_note = (
                f"{hour}시 기준 혼잡도 지수로 추정한 예상 대기시간(실측 아님): "
                if has_congestion_data
                else "혼잡도 데이터 없음, 대기시간 추정 불가(0분 처리): "
            )

            desc_text = (
                f"맛집 이름: {name}, 카테고리: {sub_category} ({category_name}). "
                f"지역: {district}. "
                f"{congestion_note}"
                f"현재 대기 팀: {team}팀, 예상 대기시간: {wait_min}분. "
                f"주소: {address}, 전화번호: {phone or '없음'}. "
                f"평점: {rating}점 (리뷰 {review_count}개, 블로그 {blog_count}개)."
            )

            try:
                response = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=desc_text,
                    config=types.EmbedContentConfig(output_dimensionality=768),
                )
                embedding_vector = response.embeddings[0].values
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error embedding {name}: {e}"))
                skipped_error += 1
                continue

            EmbeddedData.objects.create(
                place_id=r_id,
                name=name,
                address=address,
                category=sub_category,
                phone=phone,
                rating=float(rating) if rating else 0.0,
                review_count=int(review_count) if review_count else 0,
                blog_count=int(blog_count) if blog_count else 0,
                place_url=f"https://place.map.kakao.com/{r_id}",
                img_url=img_url,
                x=float(x) if x else None,
                y=float(y) if y else None,
                location=district or "Unknown",
                hourly_visit=json.dumps(hourly_visit),
                description=desc_text,
                embedding=embedding_vector,
                current_waiting_team=team,
                estimated_waiting_time=wait_min,
            )
            count += 1

            if count % 50 == 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Processed {count}/{len(rows)}...")
                )

            if options["sleep_ms"]:
                time.sleep(options["sleep_ms"] / 1000)

        self.stdout.write(
            self.style.WARNING(
                f"Skipped {skipped_existing} existing, {skipped_error} errors"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"Successfully loaded {count} restaurants!")
        )
