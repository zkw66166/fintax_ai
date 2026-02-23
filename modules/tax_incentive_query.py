"""税收优惠查询模块：四级搜索（结构化→实体→关键词LIKE→FTS5）+ LLM摘要"""
import json
import re
import sqlite3
from pathlib import Path

from openai import OpenAI

from config.settings import (
    LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LLM_TIMEOUT,
    TAX_INCENTIVES_DB_PATH, PROMPTS_DIR,
)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tax_query_config.json"

# 模块级 OpenAI 客户端单例
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE, timeout=LLM_TIMEOUT)
    return _client


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class TaxIncentiveQuery:
    def __init__(self, db_path: str = None, config_path: str = None):
        self.db_path = db_path or str(TAX_INCENTIVES_DB_PATH)
        self.cfg = _load_config()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def search(self, question: str, limit: int = 20) -> dict:
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

            # Tier 1: 结构化搜索（有明确税种）
            if intent.get("tax_type"):
                rows = self._structured_search(
                    conn, intent["tax_type"], intent.get("entity_keywords", []), limit
                )
                if rows:
                    result["query_strategy"] = "structured"

            # Tier 2: 实体搜索（有实体关键词，无明确税种或 Tier 1 无结果）
            if not rows and intent.get("entity_keywords"):
                rows = self._entity_search(conn, intent["entity_keywords"], limit)
                if rows:
                    result["query_strategy"] = "entity"

            # Tier 3: 关键词 LIKE 搜索
            if not rows and intent.get("search_keywords"):
                rows = self._keyword_search(conn, intent["search_keywords"], limit)
                if rows:
                    result["query_strategy"] = "keyword"

            # Tier 4: FTS5 兜底
            if not rows:
                rows = self._fts5_search(conn, question, limit)
                if rows:
                    result["query_strategy"] = "fts5"

            conn.close()

            result["raw_results"] = rows
            result["result_count"] = len(rows)

            if rows:
                result["answer"] = self._summarize_with_llm(question, rows, intent)
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
        for w in (found_known + list(intent.get("entity_keywords", []))):
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
        seen = set()
        search_kws = []
        for w in found_known + extra_kws:
            if w not in skip and w not in seen and len(w) >= 2:
                search_kws.append(w)
                seen.add(w)
        intent["search_keywords"] = search_kws

        return intent

    # ------------------------------------------------------------------
    # 四级搜索实现
    # ------------------------------------------------------------------

    def _structured_search(self, conn, tax_type, entity_kws, limit) -> list:
        like_clauses = []
        params = [tax_type]
        if entity_kws:
            for ek in entity_kws:
                like_clauses.append(
                    "(incentive_items LIKE ? OR keywords LIKE ? OR qualification LIKE ?)"
                )
                params.extend([f"%{ek}%"] * 3)
        where_extra = " AND " + " AND ".join(like_clauses) if like_clauses else ""
        sql = f"""
            SELECT * FROM tax_incentives
            WHERE tax_type = ?{where_extra}
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _entity_search(self, conn, entity_kws, limit) -> list:
        if not entity_kws:
            return []
        clauses = []
        params = []
        for ek in entity_kws:
            clauses.append(
                "(incentive_items LIKE ? OR keywords LIKE ? OR qualification LIKE ? OR enterprise_type LIKE ?)"
            )
            params.extend([f"%{ek}%"] * 4)
        sql = f"""
            SELECT * FROM tax_incentives
            WHERE {" AND ".join(clauses)}
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _keyword_search(self, conn, keywords, limit) -> list:
        if not keywords:
            return []
        search_fields = [
            "incentive_items", "qualification", "detailed_rules",
            "keywords", "explanation", "incentive_method",
        ]
        clauses = []
        params = []
        for kw in keywords:
            field_ors = " OR ".join(f"{f} LIKE ?" for f in search_fields)
            clauses.append(f"({field_ors})")
            params.extend([f"%{kw}%"] * len(search_fields))
        sql = f"""
            SELECT * FROM tax_incentives
            WHERE {" AND ".join(clauses)}
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _fts5_search(self, conn, question, limit) -> list:
        # 提取中文词作为 FTS5 查询词，用空格拼接
        tokens = re.findall(r'[\u4e00-\u9fff]{2,}', question)
        if not tokens:
            return []
        match_expr = " ".join(tokens)
        try:
            rows = conn.execute(
                """SELECT t.* FROM tax_incentives_fts f
                   JOIN tax_incentives t ON t.rowid = f.rowid
                   WHERE tax_incentives_fts MATCH ?
                   LIMIT ?""",
                (match_expr, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # LLM 摘要
    # ------------------------------------------------------------------

    def _summarize_with_llm(self, question, results, query_intent) -> str:
        prompt_template = (PROMPTS_DIR / "tax_incentive_summary.txt").read_text(encoding="utf-8")

        # 构建政策数据文本（每条取关键字段）
        policy_lines = []
        for i, r in enumerate(results[:10], 1):  # 最多送10条给LLM
            parts = [f"【政策{i}】"]
            if r.get("incentive_items"):
                parts.append(f"优惠项目: {r['incentive_items']}")
            if r.get("tax_type"):
                parts.append(f"税种: {r['tax_type']}")
            if r.get("qualification"):
                parts.append(f"适用条件: {r['qualification']}")
            if r.get("incentive_method"):
                parts.append(f"优惠方式: {r['incentive_method']}")
            if r.get("detailed_rules"):
                parts.append(f"详细规定: {r['detailed_rules'][:200]}")
            if r.get("legal_basis"):
                parts.append(f"法律依据: {r['legal_basis']}")
            policy_lines.append("\n".join(parts))

        policy_data = "\n\n".join(policy_lines)
        prompt = prompt_template.format(
            question=question,
            result_count=len(results),
            policy_data=policy_data,
        )

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
            # LLM 失败时返回原始数据摘要
            fallback = f"找到 {len(results)} 条相关政策：\n\n"
            for i, r in enumerate(results[:5], 1):
                fallback += f"{i}. {r.get('incentive_items', '未知')}"
                if r.get("tax_type"):
                    fallback += f"（{r['tax_type']}）"
                fallback += "\n"
            return fallback

    def _build_summary_prompt(self, question, results, query_intent) -> str:
        """构建 LLM 摘要的 prompt（供流式和非流式共用）"""
        prompt_template = (PROMPTS_DIR / "tax_incentive_summary.txt").read_text(encoding="utf-8")
        policy_lines = []
        for i, r in enumerate(results[:10], 1):
            parts = [f"【政策{i}】"]
            if r.get("incentive_items"):
                parts.append(f"优惠项目: {r['incentive_items']}")
            if r.get("tax_type"):
                parts.append(f"税种: {r['tax_type']}")
            if r.get("qualification"):
                parts.append(f"适用条件: {r['qualification']}")
            if r.get("incentive_method"):
                parts.append(f"优惠方式: {r['incentive_method']}")
            if r.get("detailed_rules"):
                parts.append(f"详细规定: {r['detailed_rules'][:200]}")
            if r.get("legal_basis"):
                parts.append(f"法律依据: {r['legal_basis']}")
            policy_lines.append("\n".join(parts))
        policy_data = "\n\n".join(policy_lines)
        return prompt_template.format(
            question=question,
            result_count=len(results),
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

    def _summarize_with_llm_stream(self, question, results, query_intent):
        """流式 LLM 摘要。Yields (chunk_text, is_done)"""
        prompt = self._build_summary_prompt(question, results, query_intent)
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

    def search_stream(self, question: str, limit: int = 20):
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

            if intent.get("tax_type"):
                rows = self._structured_search(
                    conn, intent["tax_type"], intent.get("entity_keywords", []), limit
                )
                if rows:
                    result["query_strategy"] = "structured"

            if not rows and intent.get("entity_keywords"):
                rows = self._entity_search(conn, intent["entity_keywords"], limit)
                if rows:
                    result["query_strategy"] = "entity"

            if not rows and intent.get("search_keywords"):
                rows = self._keyword_search(conn, intent["search_keywords"], limit)
                if rows:
                    result["query_strategy"] = "keyword"

            if not rows:
                rows = self._fts5_search(conn, question, limit)
                if rows:
                    result["query_strategy"] = "fts5"

            conn.close()

            result["raw_results"] = rows
            result["result_count"] = len(rows)

            if rows:
                for chunk_text, is_done in self._summarize_with_llm_stream(question, rows, intent):
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
