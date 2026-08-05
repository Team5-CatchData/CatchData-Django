import csv
import os
import random

from django.conf import settings
from django.core.management.base import BaseCommand

# eval_topk의 기본 질의 세트(카테고리)와 맞춰야 recall@K 실험이 의미가 있다.
CATEGORIES = [
    "국밥", "파스타", "삼겹살", "카페", "초밥",
    "냉면", "고기", "브런치", "치킨", "떡볶이",
]

AREAS = [
    ("강남역", 127.0276, 37.4979),
    ("이태원", 126.9944, 37.5344),
    ("홍대", 126.9235, 37.5563),
    ("성수동", 127.0557, 37.5445),
    ("잠실", 127.1000, 37.5133),
    ("여의도", 126.9243, 37.5219),
    ("합정", 126.9139, 37.5497),
    ("신촌", 126.9368, 37.5551),
]

NAME_SUFFIXES = ["맛집", "전문점", "하우스", "식당", "포차", "키친", "본점", "화로구이"]


def _generate_rows(count_per_category, seed):
    rng = random.Random(seed)
    kakao_rows = []
    waiting_rows = []
    idx = 0

    for category in CATEGORIES:
        for _ in range(count_per_category):
            idx += 1
            r_id = f"synthetic_{idx:04d}"
            area_name, base_x, base_y = rng.choice(AREAS)
            suffix = rng.choice(NAME_SUFFIXES)
            place_name = f"{area_name}{category}{suffix}{idx}"

            rating = round(rng.uniform(3.0, 4.9), 1)
            # 대기 없는 곳이 더 흔하되, 인기 맛집(긴 웨이팅)도 일부 섞는다.
            waiting_count = rng.choices(
                [0, 1, 2, 3, 5, 8], weights=[35, 20, 15, 15, 10, 5]
            )[0]

            kakao_rows.append({
                "id": r_id,
                "place_name": place_name,
                "category_name": f"음식점 > {category}",
                "road_address_name": (
                    f"서울 {area_name}인근 {rng.randint(1, 99)}길 "
                    f"{rng.randint(1, 50)}"
                ),
                "phone": "02-000-0000",
                "rating": rating,
                "img_url": "",
                "x": round(base_x + rng.uniform(-0.003, 0.003), 6),
                "y": round(base_y + rng.uniform(-0.003, 0.003), 6),
            })
            waiting_rows.append({"id": r_id, "waiting": waiting_count})

    return kakao_rows, waiting_rows


class Command(BaseCommand):
    help = (
        "실 크롤링 데이터(kakao_crawl.csv, realtime_waiting.csv)가 없을 때, "
        "eval_topk 실험용으로 쓸 합성 맛집 데이터를 생성해 같은 형식의 CSV로 저장한다. "
        "생성 후 'python manage.py test_embedding'으로 그대로 적재하면 된다. "
        "주의: 실제 크롤링 데이터가 아니므로 결과 수치는 방법론 검증용일 뿐, "
        "실제 서비스 품질을 대변하지 않는다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count-per-category", type=int, default=15,
            help="카테고리당 생성할 식당 수 (기본 15, 카테고리 10개 -> 총 150개)",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="재현 가능하도록 고정하는 랜덤 시드 (기본 42)",
        )

    def handle(self, *args, **options):
        kakao_rows, waiting_rows = _generate_rows(
            options["count_per_category"], options["seed"]
        )

        kakao_path = os.path.join(settings.BASE_DIR, "kakao_crawl.csv")
        waiting_path = os.path.join(settings.BASE_DIR, "realtime_waiting.csv")

        with open(kakao_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(kakao_rows[0].keys()))
            writer.writeheader()
            writer.writerows(kakao_rows)

        with open(waiting_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "waiting"])
            writer.writeheader()
            writer.writerows(waiting_rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {len(kakao_rows)} synthetic restaurants "
                f"({len(CATEGORIES)} categories x "
                f"{options['count_per_category']}) -> {kakao_path}, {waiting_path}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "합성 데이터입니다. 다음 단계: "
                "python manage.py test_embedding  (Gemini embed_content 호출 발생) "
                "-> python manage.py eval_topk"
            )
        )
