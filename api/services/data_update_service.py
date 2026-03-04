"""数据更新服务 - 提供参考数据重载、缓存清理、配置热重载等功能"""
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class DataUpdateService:
    """数据更新服务类"""

    @staticmethod
    def reload_reference_data() -> Dict[str, Any]:
        """
        重新加载参考数据（同义词表、科目字典、指标定义等）

        Returns:
            {
                'message': str,
                'affected_tables': list,
                'duration_seconds': float
            }
        """
        start_time = datetime.now()
        affected_tables = []

        try:
            from database.seed_data import (
                seed_vat_synonyms,
                seed_eit_synonyms,
                seed_account_synonyms,
                seed_balance_sheet_data,
                seed_income_statement_data,
                seed_cash_flow_data,
                seed_invoice_data,
                seed_financial_metrics_data
            )
            from config.settings import DB_PATH

            # 重载各类参考数据
            logger.info("开始重载参考数据...")

            seed_vat_synonyms()
            affected_tables.append('vat_synonyms')

            seed_eit_synonyms()
            affected_tables.append('eit_synonyms')

            seed_account_synonyms()
            affected_tables.append('account_synonyms')

            seed_balance_sheet_data()
            affected_tables.extend(['fs_balance_sheet_item_dict', 'fs_balance_sheet_synonyms'])

            seed_income_statement_data()
            affected_tables.extend(['fs_income_statement_item_dict', 'fs_income_statement_synonyms'])

            seed_cash_flow_data()
            affected_tables.extend(['fs_cash_flow_item_dict', 'fs_cash_flow_synonyms'])

            seed_invoice_data()
            affected_tables.extend(['inv_column_mapping', 'inv_synonyms'])

            seed_financial_metrics_data()
            affected_tables.extend(['financial_metrics_item_dict', 'financial_metrics_synonyms'])

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"参考数据重载成功，耗时 {duration:.2f}s，影响表: {affected_tables}")

            return {
                'message': f'成功重载 {len(affected_tables)} 个参考数据表',
                'affected_tables': affected_tables,
                'duration_seconds': duration
            }

        except Exception as e:
            logger.error(f"参考数据重载失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def clear_cache(cache_types: Union[str, List[str]] = 'all') -> Dict[str, Any]:
        """
        清空指定类型的缓存

        Args:
            cache_types: 缓存类型列表或 'all'
                        可选值: ['intent', 'sql', 'result', 'cross_domain'] 或 'all'

        Returns:
            {
                'cleared_entries': dict,
                'message': str
            }
        """
        try:
            from modules.cache_manager import clear_all_caches, clear_cache_by_type

            if cache_types == 'all':
                result = clear_all_caches()
                logger.info(f"清空所有缓存: {result['cleared_entries']['total']} 条记录")
                return result

            # 清空指定类型的缓存
            if isinstance(cache_types, str):
                cache_types = [cache_types]

            cleared_entries = {}
            total = 0

            for cache_type in cache_types:
                result = clear_cache_by_type(cache_type)
                cleared_entries[cache_type] = result['cleared_entries']
                total += result['cleared_entries']

            logger.info(f"清空指定缓存: {cache_types}, 共 {total} 条记录")

            return {
                'cleared_entries': {
                    **cleared_entries,
                    'total': total
                },
                'message': f'成功清空 {len(cache_types)} 类缓存，共 {total} 条记录'
            }

        except Exception as e:
            logger.error(f"缓存清理失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def reload_router_config() -> Dict[str, Any]:
        """
        重新加载意图路由配置

        Returns:
            {
                'success': bool,
                'config_version': str,
                'loaded_at': str,
                'message': str
            }
        """
        try:
            from modules.intent_router import IntentRouter

            # 创建路由器实例并重载配置
            router = IntentRouter()
            result = router.reload_config()

            logger.info(f"意图路由配置重载: {result['message']}")
            return result

        except Exception as e:
            logger.error(f"配置重载失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def batch_quality_check(taxpayer_ids: Union[str, List[str]] = 'all',
                           check_categories: List[str] = None) -> Dict[str, Any]:
        """
        批量数据质量检查

        Args:
            taxpayer_ids: 纳税人ID列表或 'all'
            check_categories: 检查类别列表，默认全部检查
                            ['internal_consistency', 'reasonableness', 'cross_table',
                             'period_continuity', 'completeness']

        Returns:
            {
                'success': bool,
                'total_taxpayers': int,
                'checked_taxpayers': int,
                'results': dict[taxpayer_id, CheckResult],
                'summary': {
                    'total_issues': int,
                    'critical_issues': int,
                    'warning_issues': int
                }
            }
        """
        start_time = datetime.now()

        try:
            from api.services.data_quality import DataQualityChecker
            from config.settings import DB_PATH

            # 默认检查所有类别
            if check_categories is None:
                check_categories = [
                    'internal_consistency',
                    'reasonableness',
                    'cross_table',
                    'period_continuity',
                    'completeness'
                ]

            # 获取纳税人列表
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

            if taxpayer_ids == 'all':
                cursor = conn.execute("SELECT taxpayer_id, taxpayer_name FROM taxpayer_info")
                taxpayers = [(row['taxpayer_id'], row['taxpayer_name']) for row in cursor.fetchall()]
            else:
                if isinstance(taxpayer_ids, str):
                    taxpayer_ids = [taxpayer_ids]

                placeholders = ','.join('?' * len(taxpayer_ids))
                cursor = conn.execute(
                    f"SELECT taxpayer_id, taxpayer_name FROM taxpayer_info WHERE taxpayer_id IN ({placeholders})",
                    taxpayer_ids
                )
                taxpayers = [(row['taxpayer_id'], row['taxpayer_name']) for row in cursor.fetchall()]

            # 批量检查
            checker = DataQualityChecker(DB_PATH)
            results = {}
            total_issues = 0
            critical_issues = 0
            warning_issues = 0

            for taxpayer_id, taxpayer_name in taxpayers:
                try:
                    check_result = checker.check_all(taxpayer_id, check_categories)
                    results[taxpayer_id] = {
                        'taxpayer_name': taxpayer_name,
                        'domains': {}
                    }

                    # 统计问题数量
                    for domain, domain_result in check_result.domains.items():
                        domain_issues = []
                        for issue in domain_result.issues:
                            domain_issues.append({
                                'rule_id': issue.rule_id,
                                'severity': issue.severity,
                                'message': issue.message,
                                'details': issue.details
                            })

                            total_issues += 1
                            if issue.severity == 'critical':
                                critical_issues += 1
                            elif issue.severity == 'warning':
                                warning_issues += 1

                        results[taxpayer_id]['domains'][domain] = {
                            'passed': domain_result.passed,
                            'issues_count': len(domain_issues),
                            'issues': domain_issues
                        }

                except Exception as e:
                    logger.error(f"检查企业 {taxpayer_id} 失败: {str(e)}")
                    results[taxpayer_id] = {
                        'taxpayer_name': taxpayer_name,
                        'error': str(e)
                    }

            conn.close()

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"批量质量检查完成，耗时 {duration:.2f}s，检查 {len(taxpayers)} 个企业")

            return {
                'success': True,
                'total_taxpayers': len(taxpayers),
                'checked_taxpayers': len(results),
                'results': results,
                'summary': {
                    'total_issues': total_issues,
                    'critical_issues': critical_issues,
                    'warning_issues': warning_issues
                },
                'duration_seconds': duration
            }

        except Exception as e:
            logger.error(f"批量质量检查失败: {str(e)}", exc_info=True)
            raise
