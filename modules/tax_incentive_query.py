"""税收优惠查询模块：四级搜索（结构化→实体→关键词LIKE→FTS5）+ LLM摘要"""
import json
import logging
import re
import sqlite3
from pathlib import Path

from openai import OpenAI

from config.settings import (
    LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LLM_TIMEOUT,
    TAX_INCENTIVES_DB_PATH, PROMPTS_DIR,
)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tax_query_config.json"
_SEARCH_KW_PATH = Path(__file__).resolve().parent.parent / "config" / "tax_search_keywords.json"

# 模块级 OpenAI 客户端单例
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE, timeout=LLM_TIMEOUT)
    return _client


_tiq_logger = logging.getLogger(__name__)


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _tiq_logger.error("[TaxIncentiveQuery] JSON解析失败: %s — %s", _CONFIG_PATH, e)
        return {}
    except Exception as e:
        _tiq_logger.error("[TaxIncentiveQuery] 配置加载异常: %s", e)
        return {}


def _load_search_keywords() -> dict:
    try:
        with open(_SEARCH_KW_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _tiq_logger.error("[TaxIncentiveQuery] 搜索关键词JSON解析失败: %s — %s", _SEARCH_KW_PATH, e)
        return {}
    except Exception as e:
        _tiq_logger.error("[TaxIncentiveQuery] 搜索关键词加载异常: %s", e)
        return {}


class TaxIncentiveQuery:
    def __init__(self, db_path: str = None, config_path: str = None):
        self.db_path = db_path or str(TAX_INCENTIVES_DB_PATH)
        self.cfg = _load_config()
        self.search_kw_cfg = _load_search_keywords()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def search(self, question: str, limit: int = 30) -> dict:
        result = {
            "success": False,
            "route": "tax_incentive",
            "answer": "",
            "raw_results": [],
            "result_count": 0,
            "query_strategy": "empty",
            "tax_type": None,
            "error": None,
        }
        try:
            intent = self._parse_query_intent(question)
            result["tax_type"] = intent.get("tax_type")

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = []
            all_rows = []  # 全量结果，用于统计全貌

            # Tier 0.5: 类别搜索（匹配到优惠类别关键词）
            if intent.get("category_keywords"):
                all_rows, rows = self._category_search(
                    conn, intent.get("tax_type"), intent["category_keywords"], limit
                )
                if rows:
                    result["query_strategy"] = "category"

            # Tier 1: 结构化搜索（有明确税种）
            if not rows and intent.get("tax_type"):
                rows = self._structured_search(
                    conn, intent["tax_type"], intent.get("entity_keywords", []), limit
                )
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "structured"

            # Tier 2: 实体搜索（有实体关键词，无明确税种或 Tier 1 无结果）
            if not rows and intent.get("entity_keywords"):
                rows = self._entity_search(conn, intent["entity_keywords"], limit)
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "entity"

            # Tier 3: 关键词 LIKE 搜索
            if not rows and intent.get("search_keywords"):
                rows = self._keyword_search(conn, intent["search_keywords"], limit)
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "keyword"

            # Tier 4: FTS5 兜底
            if not rows:
                rows = self._fts5_search(conn, question, limit)
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "fts5"

            conn.close()

            result["raw_results"] = rows
            result["result_count"] = len(rows)

            if rows:
                overview_stats = self._build_overview_stats(all_rows)
                result["answer"] = self._summarize_with_llm(question, rows, intent, overview_stats)
                result["success"] = True
            else:
                result["answer"] = "未找到与您问题相关的税收优惠政策。请尝试更换关键词或描述更具体的问题。"
                result["success"] = True  # 空结果也算成功返回

        except Exception as e:
            result["error"] = f"税收优惠查询异常: {e}"
        return result

    # ------------------------------------------------------------------
    # 意图解析（纯正则，无 LLM）
    # ------------------------------------------------------------------

    def _parse_query_intent(self, question: str) -> dict:
        intent = {"tax_type": None, "entity_keywords": [], "search_keywords": []}

        # 提取税种
        tax_types = self.cfg.get("tax_types", [])
        fuzzy_map = self.cfg.get("tax_fuzzy_map", {})
        for tt in tax_types:
            if tt in question:
                intent["tax_type"] = tt
                break
        if not intent["tax_type"]:
            for prefix, full in fuzzy_map.items():
                if prefix in question:
                    intent["tax_type"] = full
                    break

        # 提取优惠类别关键词（incentive_category匹配）
        category_kws = self.cfg.get("category_keywords", [])
        found_categories = []
        for ck in sorted(category_kws, key=len, reverse=True):  # longest-first
            if ck in question:
                found_categories.append(ck)
                break  # only match the first (longest) category
        intent["category_keywords"] = found_categories

        # 提取实体关键词
        entity_kws = self.cfg.get("core_entity_keywords", [])
        synonyms = self.cfg.get("entity_synonyms", {})
        found_entities = set()
        for ek in entity_kws:
            if ek in question:
                found_entities.add(ek)
                # 加入同义词扩展
                for syn_list in synonyms.values():
                    if ek in syn_list:
                        found_entities.update(syn_list)
        intent["entity_keywords"] = list(found_entities)

        # 提取搜索关键词（基于已知词表 + 去停用词切分）
        stopwords = {"的", "了", "吗", "呢", "吧", "有", "哪些", "什么", "是", "和", "与",
                     "请问", "查询", "请", "帮我", "我想", "知道", "告诉", "需要", "可以",
                     "政策", "条件", "规定", "要求", "怎么", "如何", "申请", "比例",
                     "包括", "包含", "具体", "相关", "全部", "所有", "一般"}
        # 先用已知词表做正向最长匹配
        known_words = set()
        for key in ("incentive_keywords", "core_entity_keywords", "condition_intent_keywords"):
            known_words.update(self.cfg.get(key, []))
        found_known = []
        for w in sorted(known_words, key=len, reverse=True):
            if w in question:
                found_known.append(w)
        # 从问题中去除已识别的税种/实体/已知词/停用词，剩余部分按标点和停用词边界切分
        remaining = question
        for w in (found_known + list(intent.get("entity_keywords", [])) + intent.get("category_keywords", [])):
            remaining = remaining.replace(w, " ")
        if intent["tax_type"]:
            remaining = remaining.replace(intent["tax_type"], " ")
        # 去除停用词
        for sw in stopwords:
            remaining = remaining.replace(sw, " ")
        # 提取剩余CJK片段（>=2字）
        extra_kws = [t for t in re.findall(r'[\u4e00-\u9fff]{2,}', remaining)]
        # 合并：已知词优先 + 剩余片段
        skip = set()
        if intent["tax_type"]:
            skip.add(intent["tax_type"])
        skip.update(intent["entity_keywords"])
        skip.update(intent.get("category_keywords", []))
        seen = set()
        search_kws = []
        for w in found_known + extra_kws:
            if w not in skip and w not in seen and len(w) >= 2:
                search_kws.append(w)
                seen.add(w)
        intent["search_keywords"] = search_kws

        return intent

    # ------------------------------------------------------------------
    # 多样性采样（Diversity Sampling）
    # ------------------------------------------------------------------

    def _build_overview_stats(self, all_rows: list) -> dict:
        """从全量结果行中统计税种、优惠方式、子类别分布，用于全貌性概括"""
        from collections import Counter
        tax_types = Counter()
        methods = Counter()
        subcategories = Counter()
        for r in all_rows:
            if r.get("tax_type"):
                tax_types[r["tax_type"]] += 1
            if r.get("incentive_method"):
                # 优惠方式可能较长，取前10字作为标签
                m = r["incentive_method"].strip()[:20]
                methods[m] += 1
            if r.get("incentive_subcategory"):
                subcategories[r["incentive_subcategory"]] += 1
        return {
            "total": len(all_rows),
            "tax_types": dict(tax_types.most_common()),
            "methods": dict(methods.most_common(10)),
            "subcategories": dict(subcategories.most_common(15)),
        }

    def _apply_diversity_sampling(self, rows: list, limit: int = 20, min_per_group: int = 1) -> list:
        """
        Apply diversity sampling to ensure broad coverage across policy categories.
        Groups by incentive_category and incentive_subcategory fields and samples evenly.

        Args:
            rows: List of policy dicts from database query
            limit: Maximum number of policies to return (default 20)
            min_per_group: Minimum policies per group (default 1)

        Returns:
            List of diverse policies sampled across categories
        """
        if not rows or len(rows) <= limit:
            return rows

        # Group by (incentive_category, incentive_subcategory) tuple for finer granularity
        from collections import defaultdict
        categories = defaultdict(list)
        for row in rows:
            category = row.get("incentive_category", "未分类")
            subcategory = row.get("incentive_subcategory", "未分类")
            # Use tuple as key for two-level grouping
            key = (category, subcategory)
            categories[key].append(row)

        # Calculate samples per category
        num_categories = len(categories)
        samples_per_category = max(min_per_group, limit // num_categories)

        # If samples_per_category is too small, increase it to ensure we use the full limit
        if samples_per_category * num_categories < limit:
            samples_per_category += 1

        # Sample evenly across categories (collect from ALL groups first)
        diverse_results = []
        for category_rows in categories.values():
            diverse_results.extend(category_rows[:samples_per_category])

        # If we still haven't reached the limit, add more from larger groups
        if len(diverse_results) < limit:
            # Sort groups by size (descending)
            sorted_groups = sorted(categories.values(), key=len, reverse=True)
            for category_rows in sorted_groups:
                # Add more policies from this group (beyond samples_per_category)
                already_added = min(len(category_rows), samples_per_category)
                remaining_in_group = category_rows[already_added:]
                for row in remaining_in_group:
                    if len(diverse_results) >= limit:
                        break
                    diverse_results.append(row)
                if len(diverse_results) >= limit:
                    break

        return diverse_results[:limit]

    # ------------------------------------------------------------------
    # 四级搜索实现
    # ------------------------------------------------------------------

    def _category_search(self, conn, tax_type, category_keywords, limit) -> tuple:
        """Tier 0.5: 按优惠类别(incentive_category)精确搜索
        Returns (all_rows, sampled_rows) — all_rows用于统计全貌，sampled_rows用于LLM摘要
        """
        if not category_keywords:
            return [], []

        clauses = []
        params = []

        # Category filter (OR across category keywords, though typically just one)
        cat_ors = " OR ".join("incentive_category LIKE ?" for _ in category_keywords)
        clauses.append(f"({cat_ors})")
        params.extend([f"%{ck}%" for ck in category_keywords])

        # Optional tax_type filter
        if tax_type:
            clauses.append("tax_type = ?")
            params.append(tax_type)

        # Fetch all matching rows for stats (no limit cap for stats accuracy)
        fetch_limit = limit * 20

        sql = f"""
            SELECT * FROM tax_incentives
            WHERE {" AND ".join(clauses)}
            LIMIT ?
        """
        params.append(fetch_limit)
        rows = conn.execute(sql, params).fetchall()
        all_rows = [dict(r) for r in rows]

        # Apply diversity sampling for display
        sampled_rows = self._apply_diversity_sampling(all_rows, limit) if len(all_rows) > limit else all_rows

        return all_rows, sampled_rows

    def _structured_search(self, conn, tax_type, entity_kws, limit) -> list:
        like_clauses = []
        params = [tax_type]

        # Determine if this is a broad query (no entity keywords)
        is_broad_query = not entity_kws

        if entity_kws:
            for ek in entity_kws:
                like_clauses.append(
                    "(incentive_items LIKE ? OR keywords LIKE ? OR qualification LIKE ? OR incentive_subcategory LIKE ?)"
                )
                params.extend([f"%{ek}%"] * 4)

        where_extra = " AND " + " AND ".join(like_clauses) if like_clauses else ""

        # For broad queries, fetch more rows for diversity sampling
        # For entity queries, also fetch more to enable diversity if needed
        fetch_limit = limit * 10 if (is_broad_query or entity_kws) else limit

        sql = f"""
            SELECT * FROM tax_incentives
            WHERE tax_type = ?{where_extra}
            LIMIT ?
        """
        params.append(fetch_limit)
        rows = conn.execute(sql, params).fetchall()
        result_rows = [dict(r) for r in rows]

        # Apply diversity sampling for broad queries OR entity queries with many results
        if is_broad_query and len(result_rows) > limit:
            result_rows = self._apply_diversity_sampling(result_rows, limit)
        elif entity_kws and len(result_rows) > limit:
            # Entity queries with >limit results also get diversity sampling
            result_rows = self._apply_diversity_sampling(result_rows, limit)

        return result_rows

    def _entity_search(self, conn, entity_kws, limit) -> list:
        if not entity_kws:
            return []

        # Use OR across entity keywords (synonyms should broaden, not narrow results)
        all_field_clauses = []
        params = []
        for ek in entity_kws:
            all_field_clauses.append(
                "(incentive_items LIKE ? OR keywords LIKE ? OR qualification LIKE ? OR enterprise_type LIKE ? OR incentive_subcategory LIKE ?)"
            )
            params.extend([f"%{ek}%"] * 5)

        # OR: any entity keyword matching any field
        combined = " OR ".join(all_field_clauses)

        # Fetch more rows to enable diversity sampling if needed
        # For entity queries, fetch up to 50 rows (more than broad queries)
        fetch_limit = min(limit * 15, 50)

        sql = f"""
            SELECT * FROM tax_incentives
            WHERE ({combined})
            LIMIT ?
        """
        params.append(fetch_limit)
        rows = conn.execute(sql, params).fetchall()
        result_rows = [dict(r) for r in rows]

        # Apply diversity sampling only if result count significantly exceeds limit
        # Use a higher threshold (1.5x) for entity queries to preserve more results
        if len(result_rows) > limit * 1.5:
            result_rows = self._apply_diversity_sampling(result_rows, limit)
        elif len(result_rows) > limit:
            # If only slightly over limit, just truncate (no diversity needed)
            result_rows = result_rows[:limit]

        return result_rows

    def _keyword_search(self, conn, keywords, limit) -> list:
        if not keywords:
            return []

        # Filter out generic noise keywords that are too broad for AND search
        generic_keywords = set(self.search_kw_cfg.get("generic_noise_keywords", []))
        filtered_keywords = [kw for kw in keywords if kw not in generic_keywords]

        # If all keywords were generic, fall through to FTS5
        if not filtered_keywords:
            return []

        search_fields = [
            "incentive_items", "qualification", "detailed_rules",
            "keywords", "explanation", "incentive_method",
            "incentive_category", "incentive_subcategory",
        ]
        clauses = []
        params = []
        for kw in filtered_keywords:
            field_ors = " OR ".join(f"{f} LIKE ?" for f in search_fields)
            clauses.append(f"({field_ors})")
            params.extend([f"%{kw}%"] * len(search_fields))

        fetch_limit = limit * 5
        sql = f"""
            SELECT * FROM tax_incentives
            WHERE {" AND ".join(clauses)}
            LIMIT ?
        """
        params.append(fetch_limit)
        rows = conn.execute(sql, params).fetchall()
        result_rows = [dict(r) for r in rows]

        # Apply diversity sampling when results exceed limit
        if len(result_rows) > limit:
            result_rows = self._apply_diversity_sampling(result_rows, limit)

        return result_rows

    def _fts5_search(self, conn, question, limit) -> list:
        # 提取中文词作为 FTS5 查询词
        tokens = re.findall(r'[\u4e00-\u9fff]{2,}', question)
        if not tokens:
            return []

        # Filter out stopwords/noise tokens from config
        fts_stopwords = set(self.search_kw_cfg.get("fts5_stopwords", []))
        tokens = [t for t in tokens if t not in fts_stopwords]
        if not tokens:
            return []

        # Split long CJK tokens (>4 chars) into 2-char bigrams for better FTS5 matching
        # e.g. "养老托育家政" → ["养老", "托育", "家政"]
        expanded = []
        for t in tokens:
            if len(t) <= 4:
                expanded.append(t)
            else:
                for i in range(0, len(t) - 1, 2):
                    chunk = t[i:i + 2]
                    if chunk not in fts_stopwords and chunk not in expanded:
                        expanded.append(chunk)
        tokens = expanded if expanded else tokens

        # Also filter generic noise keywords from config
        generic_kws = set(self.search_kw_cfg.get("generic_noise_keywords", []))
        tokens = [t for t in tokens if t not in generic_kws]
        if not tokens:
            return []

        # Use OR between tokens for broader matching (FTS5 default is AND)
        match_expr = " OR ".join(tokens)

        try:
            # Fetch more for diversity sampling
            fetch_limit = limit * 5
            rows = conn.execute(
                """SELECT t.* FROM tax_incentives_fts f
                   JOIN tax_incentives t ON t.rowid = f.rowid
                   WHERE tax_incentives_fts MATCH ?
                   LIMIT ?""",
                (match_expr, fetch_limit),
            ).fetchall()
            result_rows = [dict(r) for r in rows]

            # Apply diversity sampling
            if len(result_rows) > limit:
                result_rows = self._apply_diversity_sampling(result_rows, limit)

            return result_rows
        except Exception:
            return []

    # ------------------------------------------------------------------
    # LLM 摘要
    # ------------------------------------------------------------------

    def _summarize_with_llm(self, question, results, query_intent, overview_stats: dict = None) -> str:
        prompt = self._build_summary_prompt(question, results, query_intent, overview_stats)
        try:
            client = _get_client()
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return self._llm_fallback(results)

    def _build_summary_prompt(self, question, results, query_intent, overview_stats: dict = None) -> str:
        """构建 LLM 摘要的 prompt（供流式和非流式共用）"""
        prompt_template = (PROMPTS_DIR / "tax_incentive_summary.txt").read_text(encoding="utf-8")

        # 构建全貌统计文本
        stats_text = ""
        if overview_stats:
            total = overview_stats.get("total", len(results))
            tax_types = overview_stats.get("tax_types", {})
            methods = overview_stats.get("methods", {})
            subcategories = overview_stats.get("subcategories", {})
            tax_types_str = "、".join(tax_types.keys()) if tax_types else "未知"
            methods_str = "、".join(list(methods.keys())[:8]) if methods else "未知"
            subcats_str = "、".join(list(subcategories.keys())[:10]) if subcategories else "未知"
            stats_text = (
                f"【全量统计数据】\n"
                f"- 数据库中符合条件的政策总数：{total}条\n"
                f"- 涉及税种（{len(tax_types)}个）：{tax_types_str}\n"
                f"- 主要优惠方式：{methods_str}\n"
                f"- 涵盖领域/子类别：{subcats_str}\n"
                f"- 以下提供{len(results)}条代表性政策样本（按多样性抽样）"
            )

        # 构建政策数据文本（最多30条）
        policy_lines = []
        for i, r in enumerate(results[:30], 1):
            parts = [f"【政策{i}】"]
            if r.get("tax_type"):
                parts.append(f"税种: {r['tax_type']}")
            if r.get("incentive_category"):
                parts.append(f"优惠类别: {r['incentive_category']}")
            if r.get("incentive_subcategory"):
                parts.append(f"子类别: {r['incentive_subcategory']}")
            if r.get("incentive_items"):
                parts.append(f"优惠项目: {r['incentive_items']}")
            if r.get("incentive_method"):
                parts.append(f"优惠方式: {r['incentive_method']}")
            if r.get("qualification"):
                parts.append(f"适用条件: {r['qualification']}")
            if r.get("detailed_rules"):
                parts.append(f"详细规定: {r['detailed_rules'][:200]}")
            if r.get("legal_basis"):
                parts.append(f"法律依据: {r['legal_basis']}")
            policy_lines.append("\n".join(parts))
        policy_data = "\n\n".join(policy_lines)

        return prompt_template.format(
            question=question,
            result_count=len(results),
            stats_text=stats_text,
            policy_data=policy_data,
        )

    def _llm_fallback(self, results) -> str:
        """LLM 失败时的兜底摘要"""
        fallback = f"找到 {len(results)} 条相关政策：\n\n"
        for i, r in enumerate(results[:5], 1):
            fallback += f"{i}. {r.get('incentive_items', '未知')}"
            if r.get("tax_type"):
                fallback += f"（{r['tax_type']}）"
            fallback += "\n"
        return fallback

    def _summarize_with_llm_stream(self, question, results, query_intent, overview_stats: dict = None):
        """流式 LLM 摘要。Yields (chunk_text, is_done)"""
        prompt = self._build_summary_prompt(question, results, query_intent, overview_stats)
        try:
            client = _get_client()
            stream = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )
            accumulated = []
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    accumulated.append(delta.content)
                    yield delta.content, False
            yield "".join(accumulated), True
        except Exception:
            yield self._llm_fallback(results), True

    def search_stream(self, question: str, limit: int = 30):
        """流式版本的 search()。Yields (chunk_text, is_done, result_dict)"""
        result = {
            "success": False,
            "route": "tax_incentive",
            "answer": "",
            "raw_results": [],
            "result_count": 0,
            "query_strategy": "empty",
            "tax_type": None,
            "error": None,
        }
        try:
            intent = self._parse_query_intent(question)
            result["tax_type"] = intent.get("tax_type")

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = []
            all_rows = []  # 全量结果，用于统计全貌

            # Tier 0.5: 类别搜索
            if intent.get("category_keywords"):
                all_rows, rows = self._category_search(
                    conn, intent.get("tax_type"), intent["category_keywords"], limit
                )
                if rows:
                    result["query_strategy"] = "category"

            if not rows and intent.get("tax_type"):
                rows = self._structured_search(
                    conn, intent["tax_type"], intent.get("entity_keywords", []), limit
                )
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "structured"

            if not rows and intent.get("entity_keywords"):
                rows = self._entity_search(conn, intent["entity_keywords"], limit)
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "entity"

            if not rows and intent.get("search_keywords"):
                rows = self._keyword_search(conn, intent["search_keywords"], limit)
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "keyword"

            if not rows:
                rows = self._fts5_search(conn, question, limit)
                if rows:
                    all_rows = rows
                    result["query_strategy"] = "fts5"

            conn.close()

            result["raw_results"] = rows
            result["result_count"] = len(rows)

            if rows:
                overview_stats = self._build_overview_stats(all_rows)
                for chunk_text, is_done in self._summarize_with_llm_stream(question, rows, intent, overview_stats):
                    if not is_done:
                        yield chunk_text, False, None
                    else:
                        result["answer"] = chunk_text
                        result["success"] = True
                yield "", True, result
            else:
                result["answer"] = "未找到与您问题相关的税收优惠政策。请尝试更换关键词或描述更具体的问题。"
                result["success"] = True
                yield "", True, result

        except Exception as e:
            result["error"] = f"税收优惠查询异常: {e}"
            yield "", True, result
