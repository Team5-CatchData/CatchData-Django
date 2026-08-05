import csv
import json
import os
import statistics
import time
from datetime import datetime

import google.genai as genai
from django.conf import settings
from django.core.management.base import BaseCommand

from RAG.models import EmbeddedData
from RAG.services import RagPipelineError, run_rag_pipeline

# static_feature.csv 실데이터 기준(홍대/대치동, 11개 sub_category)에 맞춘 질의 세트.
# category_keyword는 정답(gold) 후보를 임베딩 검색과 무관하게 SQL로 뽑아내기 위한
# 필터 키워드로, EmbeddedData.category(=sub_category)와 정확히 일치해야 한다.
DEFAULT_QUERIES = [
    {"message": "홍대에서 한식 먹고 싶은데 지금 바로 갈만한 곳 추천해줘", "category_keyword": "한식"},
    {"message": "대치동 일식집 중에 웨이팅 적은 곳 알려줘", "category_keyword": "일식"},
    {"message": "홍대 중식당 저녁에 갈만한 곳 추천해줘", "category_keyword": "중식"},
    {"message": "대치동 양식 레스토랑 분위기 좋은 곳", "category_keyword": "양식"},
    {"message": "홍대 치킨집 술 한잔 하기 좋은 곳으로 추천해줘", "category_keyword": "치킨"},
    {"message": "대치동 분식집 간단하게 먹을 곳", "category_keyword": "분식"},
    {"message": "홍대 간식거리 먹을만한 곳 추천해줘", "category_keyword": "간식"},
    {"message": "대치동 술집 안주 맛있는 곳", "category_keyword": "술집"},
    {"message": "홍대 고기집 회식하기 좋은 곳 추천", "category_keyword": "고기집"},
    {"message": "대치동 뷔페 가족모임하기 좋은 곳", "category_keyword": "뷔페"},
    {"message": "홍대 샤브샤브 맛집 지금 갈만한 곳", "category_keyword": "샤브샤브"},
]


def compute_gold_ids(category_keyword, limit=3):
    """
    임베딩 검색과 무관하게, 전체 DB에서 SQL로 직접 뽑은 '정답에 가까운 후보'.
    (대기 15분 이내 중 평점 최고 -> 없으면 대기시간 짧은 순) 이 gold set이
    top-K 임베딩 검색 결과 안에 들어오는지로 recall@K를 측정한다.
    """
    qs = EmbeddedData.objects.filter(category__icontains=category_keyword)
    quick = list(qs.filter(estimated_waiting_time__lte=15).order_by("-rating")[:limit])
    if quick:
        return [r.place_id for r in quick]
    fallback = list(qs.order_by("estimated_waiting_time", "-rating")[:limit])
    return [r.place_id for r in fallback]


class Command(BaseCommand):
    help = (
        "Top-K 값(예: 5 vs 10 vs 30)에 따른 RAG 파이프라인의 "
        "토큰 비용 / 지연시간 / 구조화 출력 실패율 / recall@K 를 비교하는 실험 스크립트. "
        "결과는 CSV로 저장되고 콘솔에 K별 요약이 출력된다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--k-values", type=str, default="5,10,20,30",
            help="쉼표로 구분된 top_k 후보 목록 (기본: 5,10,20,30)",
        )
        parser.add_argument(
            "--repeats", type=int, default=3,
            help="질의당 K별 반복 횟수 (재현성/변동성 측정용, 기본 3)",
        )
        parser.add_argument(
            "--queries-file", type=str, default=None,
            help="[{'message':..., 'category_keyword':...}, ...] 형식 JSON 파일 경로. "
                 "생략 시 내장된 기본 질의 8개 사용",
        )
        parser.add_argument(
            "--output", type=str, default=None,
            help="결과 CSV 저장 경로. 생략 시 BASE_DIR에 타임스탬프 파일명으로 저장",
        )
        parser.add_argument(
            "--sleep-ms", type=int, default=4000,
            help="호출 사이 지연(ms). 무료 티어 RPM 한도 방지용 (기본 4000ms)",
        )

    def handle(self, *args, **options):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY is missing in .env!"))
            return
        client = genai.Client(api_key=gemini_api_key)

        k_values = [int(k) for k in options["k_values"].split(",")]
        repeats = options["repeats"]

        if options["queries_file"]:
            with open(options["queries_file"], "r", encoding="utf-8") as f:
                queries = json.load(f)
        else:
            queries = DEFAULT_QUERIES

        output_path = options["output"] or os.path.join(
            settings.BASE_DIR,
            f"rag_topk_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

        gold_cache = {
            q["category_keyword"]: compute_gold_ids(q["category_keyword"])
            for q in queries
        }

        rows = []
        total_calls = len(queries) * len(k_values) * repeats
        done = 0

        for q in queries:
            gold_ids = gold_cache[q["category_keyword"]]
            for k in k_values:
                for rep in range(repeats):
                    done += 1
                    self.stdout.write(
                        f"[{done}/{total_calls}] k={k} rep={rep} "
                        f"q={q['message'][:24]}..."
                    )
                    try:
                        result = self._call_with_retry(client, q["message"], k)
                    except RagPipelineError as e:
                        rows.append({
                            "query": q["message"],
                            "category_keyword": q["category_keyword"],
                            "top_k": k,
                            "repeat": rep,
                            "error": str(e),
                        })
                        if options["sleep_ms"]:
                            time.sleep(options["sleep_ms"] / 1000)
                        continue

                    recall_hit = any(
                        gid in result["retrieved_ids"] for gid in gold_ids
                    )
                    category_match = self._check_category_match(
                        result["restaurant_ID"], q["category_keyword"]
                    )
                    usage = result["usage"] or {}

                    rows.append({
                        "query": q["message"],
                        "category_keyword": q["category_keyword"],
                        "top_k": k,
                        "repeat": rep,
                        "error": "",
                        "restaurant_ID": json.dumps(
                            result["restaurant_ID"], ensure_ascii=False
                        ),
                        "recall_hit": recall_hit,
                        "category_match": category_match,
                        "json_parse_failed": result["json_parse_failed"],
                        "embed_latency_ms": round(result["embed_latency_ms"], 1),
                        "generate_latency_ms": round(
                            result["generate_latency_ms"], 1
                        ),
                        "prompt_token_count": usage.get("prompt_token_count"),
                        "candidates_token_count": usage.get(
                            "candidates_token_count"
                        ),
                        "total_token_count": usage.get("total_token_count"),
                    })

                    if options["sleep_ms"]:
                        time.sleep(options["sleep_ms"] / 1000)

        self._write_csv(output_path, rows)
        self._print_summary(rows, k_values)
        self.stdout.write(self.style.SUCCESS(f"Saved raw results to {output_path}"))

    def _call_with_retry(self, client, message, top_k, max_retries=2):
        """레이트리밋(429)일 때만 한 번 더 대기 후 재시도. 그 외 오류는 즉시 올린다."""
        for attempt in range(max_retries + 1):
            try:
                return run_rag_pipeline(client, message, top_k=top_k)
            except RagPipelineError as e:
                is_quota_error = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if not is_quota_error or attempt == max_retries:
                    raise
                self.stdout.write(
                    self.style.WARNING(
                        f"  Rate limited, retrying in 60s (attempt {attempt + 1})..."
                    )
                )
                time.sleep(60)

    def _check_category_match(self, restaurant_ids, category_keyword):
        if not restaurant_ids:
            return False
        matched = EmbeddedData.objects.filter(
            place_id__in=restaurant_ids, category__icontains=category_keyword
        ).count()
        return matched == len(restaurant_ids)

    def _write_csv(self, path, rows):
        if not rows:
            self.stdout.write(self.style.WARNING("No rows to write."))
            return
        fieldnames = sorted({key for row in rows for key in row.keys()})
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _print_summary(self, rows, k_values):
        self.stdout.write("\n=== Summary by top_k ===")
        for k in k_values:
            k_rows = [
                r for r in rows if r.get("top_k") == k and not r.get("error")
            ]
            if not k_rows:
                self.stdout.write(f"K={k:>3} | no successful calls")
                continue

            tokens = [
                r["prompt_token_count"] for r in k_rows
                if r.get("prompt_token_count") is not None
            ]
            latencies = [r["generate_latency_ms"] for r in k_rows]
            recall = [r["recall_hit"] for r in k_rows]
            parse_fail = [r["json_parse_failed"] for r in k_rows]
            cat_match = [r["category_match"] for r in k_rows]

            avg_tokens = statistics.mean(tokens) if tokens else float("nan")

            self.stdout.write(
                f"K={k:>3} | n={len(k_rows):>3} | "
                f"avg_prompt_tokens={avg_tokens:.0f} | "
                f"avg_gen_latency_ms={statistics.mean(latencies):.0f} | "
                f"recall_rate={sum(recall) / len(recall):.2%} | "
                f"json_parse_fail_rate={sum(parse_fail) / len(parse_fail):.2%} | "
                f"category_match_rate={sum(cat_match) / len(cat_match):.2%}"
            )
