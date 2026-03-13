Frontend Debug Test
Testing backend connection...
Backend response: 401
Login successful!
History API: 200
Login Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MzM4NTgwNH0.uVl34cZCFfz6barlRhTJW-Ud1h6MZ7pcFxUCdKU26VE",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "display_name": "系统管理员",
    "company_ids": [
      "91110108MA01AAAAA1",
      "91310000MA1FL8XQ30",
      "91310115MA2KZZZZZZ",
      "91320200MA02BBBBB2",
      "91330100MA2KWWWWWW",
      "91330200MA2KXXXXXX",
      "91330200MA2KYYYYYY",
      "92440300MA5EQXL17P"
    ]
  }
}
History Response
{
  "items": [
    {
      "query": "2024和2025年末的总资产和总负债构成分析",
      "status": "success",
      "timestamp": "下午9:43:45",
      "cache_key": "ccfea4252859c65136a4403c8d13b917",
      "conversation_history": [],
      "conversation_enabled": false,
      "conversation_depth": 3,
      "response_mode": "detailed",
      "thinking_mode": "think",
      "result": {
        "success": true,
        "user_query": "TSE科技有限公司 2024和2025年末的总资产和总负债构成分析",
        "clarification": null,
        "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month, revision_no,\n         assets_end, liabilities_end,\n         ROW_NUMBER() OVER (\n           PARTITION BY taxpayer_id, period_year, period_month\n           ORDER BY revision_no DESC\n         ) AS rn\n  FROM vw_balance_sheet_eas\n  WHERE taxpayer_id = '91310115MA2KZZZZZZ'\n    AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))\n)\nSELECT taxpayer_name, period_year, period_month,\n       assets_end, liabilities_end\nFROM latest\nWHERE rn = 1\nORDER BY period_year, period_month\nLIMIT 1000;",
        "results": [
          {
            "taxpayer_name": "TSE科技有限公司",
            "period_year": 2024,
            "period_month": 12,
            "assets_end": 6259728,
            "liabilities_end": 614825
          },
          {
            "taxpayer_name": "TSE科技有限公司",
            "period_year": 2025,
            "period_month": 12,
            "assets_end": 6393992,
            "liabilities_end": 1227103
          }
        ],
        "error": null,
        "entities": {
          "taxpayer_id": "91310115MA2KZZZZZZ",
          "taxpayer_name": "TSE科技有限公司",
          "taxpayer_type": "一般纳税人",
          "period_year": 2024,
          "period_month": 12,
          "period_end_month": null,
          "period_quarter": null,
          "period_years": [
            2024,
            2025
          ],
          "period_months": [
            12
          ],
          "time_range_hint": null,
          "item_type_hint": null,
          "domain_hint": "balance_sheet",
          "time_granularity": null,
          "original_query": "TSE科技有限公司 2024和2025年末的总资产和总负债构成分析",
          "resolved_query": "TSE科技有限公司 2024和2025年末的总资产和总负债构成分析",
          "accounting_standard": "企业会计准则"
        },
        "intent": {
          "domain": "balance_sheet",
          "vat_scope": {
            "taxpayer_type_hint": "unknown",
            "views": [
              "vw_vat_return_general"
            ],
            "cross_type_union": false
          },
          "eit_scope": {
            "report_type": "annual",
            "views": [
              "vw_eit_annual_main"
            ]
          },
          "account_balance_scope": {
            "views": [
              "vw_account_balance"
            ],
            "account_filter": null
          },
          "balance_sheet_scope": {
            "gaap_type": "ASBE",
            "views": [
              "vw_balance_sheet_eas"
            ]
          },
          "profit_scope": {
            "accounting_standard": "ASBE",
            "views": [
              "vw_profit_eas"
            ]
          },
          "cash_flow_scope": {
            "accounting_standard": "企业会计准则",
            "views": [
              "vw_cash_flow_eas"
            ]
          },
          "financial_metrics_scope": {
            "views": [
              "vw_financial_metrics"
            ]
          },
          "invoice_scope": {
            "direction": "both",
            "views": [
              "vw_inv_spec_purchase",
              "vw_inv_spec_sales"
            ]
          },
          "select": {
            "metrics": [
              "assets_end",
              "liabilities_end"
            ],
            "dimensions": [
              "taxpayer_name"
            ]
          },
          "filters": {
            "taxpayer_id": "91310115MA2KZZZZZZ",
            "period_mode": "range_month",
            "period": {
              "year": 2024,
              "month": 12,
              "quarter": null,
              "end_month": 12,
              "end_year": 2025
            },
            "quarter_mode": "single",
            "vat_dims": {
              "item_type": "一般项目",
              "time_range": "本月"
            },
            "profit_time_range": "本年累计",
            "account_name": null,
            "category": null,
            "revision_strategy": "latest"
          },
          "aggregation": {
            "group_by": [],
            "order_by": [],
            "limit": 1000
          },
          "need_clarification": false,
          "clarifying_questions": []
        },
        "audit_violations": [],
        "taxpayer_id": "91310115MA2KZZZZZZ",
        "taxpayer_name": "TSE科技有限公司",
        "period": "2024年12月",
        "domain": "balance_sheet",
        "display_data": {
          "display_type": "table",
          "table": {
            "headers": [
              "纳税人名称",
              "年度",
              "月份",
              "资产总计(期末余额)",
              "负债合计(期末余额)"
            ],
            "rows": [
              {
                "纳税人名称": "TSE科技有限公司",
                "年度": "2024",
                "月份": "12",
                "资产总计(期末余额)": "625.97万",
                "负债合计(期末余额)": "61.48万"
              },
              {
                "纳税人名称": "TSE科技有限公司",
                "年度": "2025",
                "月份": "12",
                "资产总计(期末余额)": "639.40万",
                "负债合计(期末余额)": "122.71万"
              }
            ],
            "columns": [
              "taxpayer_name",
              "period_year",
              "period_month",
              "assets_end",
              "liabilities_end"
            ]
          },
          "chart_data": {
            "chartType": "bar",
            "title": "资产负债表 资产总计(期末余额)、负债合计(期末余额) 趋势分析",
            "labels": [
              "2024年12月",
              "2025年12月"
            ],
            "datasets": [
              {
                "label": "资产总计(期末余额)",
                "data": [
                  6259728,
                  6393992
                ],
                "type": "bar",
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "负债合计(期末余额)",
                "data": [
                  614825,
                  1227103
                ],
                "type": "bar",
                "backgroundColor": "rgba(255, 99, 132, 0.8)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              }
            ]
          },
          "growth": [
            {
              "period": "2025年12月",
              "资产总计(期末余额)": {
                "current": 6393992,
                "previous": 6259728,
                "change": 134264,
                "change_pct": 2.14,
                "trend": "up"
              },
              "负债合计(期末余额)": {
                "current": 1227103,
                "previous": 614825,
                "change": 612278,
                "change_pct": 99.59,
                "trend": "up"
              }
            }
          ]
        },
        "response_mode": "detailed",
        "cache_key": "ccfea4252859c65136a4403c8d13b917",
        "cache_hit": false,
        "need_reinterpret": false
      },
      "company_id": "91310115MA2KZZZZZZ",
      "user_id": 1,
      "domain": ""
    },
    {
      "query": "2024-2025每年末的总资产和总负债分析",
      "status": "success",
      "timestamp": "下午9:42:50",
      "cache_key": "a096e447b037a15d1cd6e7732eb5eda5",
      "conversation_history": [],
      "conversation_enabled": false,
      "conversation_depth": 3,
      "response_mode": "detailed",
      "thinking_mode": "think",
      "result": {
        "success": true,
        "user_query": "TSE科技有限公司 2024-2025每年末的总资产和总负债分析",
        "clarification": null,
        "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month, revision_no,\n         assets_end, liabilities_end,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_balance_sheet_eas\n  WHERE taxpayer_id = '91310115MA2KZZZZZZ'\n    AND period_year = 2024\n    AND period_month = 12\n)\nSELECT taxpayer_name, period_year, period_month,\n       assets_end, liabilities_end\nFROM latest WHERE rn = 1\nORDER BY period_year, period_month\nLIMIT 1000",
        "results": [
          {
            "taxpayer_name": "TSE科技有限公司",
            "period_year": 2024,
            "period_month": 12,
            "assets_end": 6259728,
            "liabilities_end": 614825
          }
        ],
        "error": null,
        "entities": {
          "taxpayer_id": "91310115MA2KZZZZZZ",
          "taxpayer_name": "TSE科技有限公司",
          "taxpayer_type": "一般纳税人",
          "period_year": 2024,
          "period_month": 12,
          "period_end_month": null,
          "period_quarter": null,
          "period_years": [
            2024,
            2025
          ],
          "period_months": [
            12
          ],
          "time_range_hint": null,
          "item_type_hint": null,
          "domain_hint": "balance_sheet",
          "time_granularity": "yearly",
          "original_query": "TSE科技有限公司 2024-2025每年末的总资产和总负债分析",
          "resolved_query": "TSE科技有限公司 2024-2025每年末的总资产和总负债分析",
          "accounting_standard": "企业会计准则"
        },
        "intent": {
          "domain": "balance_sheet",
          "vat_scope": {
            "taxpayer_type_hint": "unknown",
            "views": [
              "vw_vat_return_general"
            ],
            "cross_type_union": false
          },
          "eit_scope": {
            "report_type": "annual",
            "views": [
              "vw_eit_annual_main"
            ]
          },
          "account_balance_scope": {
            "views": [
              "vw_account_balance"
            ],
            "account_filter": null
          },
          "balance_sheet_scope": {
            "gaap_type": "ASBE",
            "views": [
              "vw_balance_sheet_eas"
            ]
          },
          "profit_scope": {
            "accounting_standard": "ASBE",
            "views": [
              "vw_profit_eas"
            ]
          },
          "cash_flow_scope": {
            "accounting_standard": "企业会计准则",
            "views": [
              "vw_cash_flow_eas"
            ]
          },
          "financial_metrics_scope": {
            "views": [
              "vw_financial_metrics"
            ]
          },
          "invoice_scope": {
            "direction": "both",
            "views": [
              "vw_inv_spec_purchase",
              "vw_inv_spec_sales"
            ]
          },
          "select": {
            "metrics": [
              "assets_end",
              "liabilities_end"
            ],
            "dimensions": [
              "taxpayer_name"
            ]
          },
          "filters": {
            "taxpayer_id": "91310115MA2KZZZZZZ",
            "period_mode": "range_month",
            "period": {
              "year": 2024,
              "month": 12,
              "quarter": null,
              "end_month": 12
            },
            "quarter_mode": "single",
            "vat_dims": {
              "item_type": "一般项目",
              "time_range": "本月"
            },
            "profit_time_range": "本年累计",
            "account_name": null,
            "category": null,
            "revision_strategy": "latest"
          },
          "aggregation": {
            "group_by": [
              "period_year"
            ],
            "order_by": [
              "period_year"
            ],
            "limit": 1000
          },
          "need_clarification": false,
          "clarifying_questions": []
        },
        "audit_violations": [],
        "taxpayer_id": "91310115MA2KZZZZZZ",
        "taxpayer_name": "TSE科技有限公司",
        "period": "2024年12月",
        "domain": "balance_sheet",
        "display_data": {
          "display_type": "kv",
          "table": {
            "headers": [
              "纳税人名称",
              "年度",
              "月份",
              "资产总计(期末余额)",
              "负债合计(期末余额)"
            ],
            "rows": [
              {
                "纳税人名称": "TSE科技有限公司",
                "年度": "2024",
                "月份": "12",
                "资产总计(期末余额)": "625.97万",
                "负债合计(期末余额)": "61.48万"
              }
            ],
            "columns": [
              "taxpayer_name",
              "period_year",
              "period_month",
              "assets_end",
              "liabilities_end"
            ]
          },
          "chart_data": null,
          "growth": null
        },
        "response_mode": "detailed",
        "cache_key": "a096e447b037a15d1cd6e7732eb5eda5",
        "cache_hit": false,
        "need_reinterpret": false
      },
      "company_id": "91310115MA2KZZZZZZ",
      "user_id": 1,
      "domain": ""
    },
    {
      "query": "2024年六月和2025年六月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
      "status": "success",
      "timestamp": "下午9:37:03",
      "cache_key": "78f78c2535ad2d206383229819dcb2a7",
      "conversation_history": [],
      "conversation_enabled": false,
      "conversation_depth": 3,
      "response_mode": "detailed",
      "thinking_mode": "think",
      "result": {
        "success": true,
        "user_query": "创智软件股份有限公司 2024年六月和2025年六月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
        "clarification": null,
        "sql": null,
        "results": [
          {
            "period": "2024-06",
            "eit_total_profit": 4824375,
            "eit_tax_payable": 1206093.75,
            "eit_current_tax_payable_or_refund": 1206093.75,
            "profit_total_profit": 591913,
            "vat_tax_payable": 339484
          },
          {
            "period": "2025-06",
            "eit_total_profit": 6264000,
            "eit_tax_payable": 1566000,
            "eit_current_tax_payable_or_refund": 1566000,
            "profit_total_profit": 768546,
            "vat_tax_payable": 440788
          }
        ],
        "error": null,
        "entities": {
          "taxpayer_id": "91330200MA2KXXXXXX",
          "taxpayer_name": "创智软件股份有限公司",
          "taxpayer_type": "一般纳税人",
          "period_year": 2024,
          "period_month": 6,
          "period_end_month": 6,
          "period_quarter": null,
          "period_years": null,
          "period_months": null,
          "time_range_hint": null,
          "item_type_hint": null,
          "domain_hint": "cross_domain",
          "time_granularity": null,
          "original_query": "创智软件股份有限公司 2024年六月和2025年六月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
          "resolved_query": "创智软件股份有限公司 2024年6月和2025年6月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
          "cross_domain_list": [
            "eit",
            "profit",
            "vat"
          ],
          "period_end_year": 2025,
          "accounting_standard": "企业会计准则"
        },
        "intent": {
          "domain": "cross_domain",
          "cross_domain_list": [
            "eit",
            "profit",
            "vat"
          ],
          "vat_scope": {
            "taxpayer_type_hint": "一般纳税人",
            "views": [
              "vw_vat_return_general"
            ],
            "cross_type_union": false
          },
          "eit_scope": {
            "report_type": "quarter",
            "views": [
              "vw_eit_quarter_main"
            ]
          },
          "account_balance_scope": {
            "views": [
              "vw_account_balance"
            ],
            "account_filter": null
          },
          "balance_sheet_scope": {
            "gaap_type": "ASBE",
            "views": [
              "vw_balance_sheet_eas"
            ]
          },
          "profit_scope": {
            "accounting_standard": "ASBE",
            "views": [
              "vw_profit_eas"
            ]
          },
          "cash_flow_scope": {
            "accounting_standard": "企业会计准则",
            "views": [
              "vw_cash_flow_eas"
            ]
          },
          "financial_metrics_scope": {
            "views": [
              "vw_financial_metrics"
            ]
          },
          "invoice_scope": {
            "direction": "both",
            "views": [
              "vw_inv_spec_purchase",
              "vw_inv_spec_sales"
            ]
          },
          "select": {
            "metrics": [
              "total_profit",
              "tax_payable",
              "actual_tax_payable"
            ],
            "dimensions": [
              "taxpayer_name"
            ]
          },
          "filters": {
            "taxpayer_id": "91330200MA2KXXXXXX",
            "period_mode": "range_month",
            "period": {
              "year": 2024,
              "month": 6,
              "end_year": 2025,
              "end_month": 6
            },
            "quarter_mode": "single",
            "vat_dims": {
              "item_type": "一般项目",
              "time_range": "本月"
            },
            "profit_time_range": "本期",
            "account_name": null,
            "category": null,
            "revision_strategy": "latest"
          },
          "aggregation": {
            "group_by": [
              "period_year",
              "period_month"
            ],
            "order_by": [
              "period_year",
              "period_month"
            ],
            "limit": 1000
          },
          "need_clarification": false,
          "clarifying_questions": []
        },
        "audit_violations": null,
        "taxpayer_id": "91330200MA2KXXXXXX",
        "taxpayer_name": "创智软件股份有限公司",
        "period": "2024年6月",
        "domain": "cross_domain",
        "cross_domain_summary": "eit vs profit vs vat，共2个期间",
        "cross_domain_operation": "compare",
        "sub_results": [
          {
            "domain": "eit",
            "data": [
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_quarter": 2,
                "total_profit": 4824375,
                "tax_payable": 1206093.75,
                "current_tax_payable_or_refund": 1206093.75
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_quarter": 2,
                "total_profit": 6264000,
                "tax_payable": 1566000,
                "current_tax_payable_or_refund": 1566000
              }
            ],
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_quarter, revision_no,\n         total_profit, tax_payable, current_tax_payable_or_refund,\n         ROW_NUMBER() OVER (\n           PARTITION BY taxpayer_id, period_year, period_quarter\n           ORDER BY revision_no DESC\n         ) AS rn\n  FROM vw_eit_quarter_main\n  WHERE taxpayer_id = '91330200MA2KXXXXXX'\n    AND period_year IN (2024, 2025)\n    AND period_quarter = 2\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_quarter,\n       total_profit, tax_payable, current_tax_payable_or_refund\nFROM latest WHERE rn = 1\nORDER BY period_year\nLIMIT 1000;"
          },
          {
            "domain": "profit",
            "data": [
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 6,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 591913
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 7,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 584479
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 8,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 576431
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 9,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 573471
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 10,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 580238
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 11,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 598979
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 12,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 628855
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 1,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 666000
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 2,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 704475
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 3,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 737796
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 4,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 760695
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 5,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 770619
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 6,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 768546
              }
            ],
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month,\n         time_range, accounting_standard_name, revision_no,\n         total_profit,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month, time_range\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_profit_eas\n  WHERE taxpayer_id = '91330200MA2KXXXXXX'\n    AND (period_year*100+period_month) BETWEEN 202406 AND 202506\n    AND time_range = '本期'\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_month, time_range, accounting_standard_name, revision_no, total_profit\nFROM latest WHERE rn = 1\nORDER BY period_year, period_month\nLIMIT 1000;"
          },
          {
            "domain": "vat",
            "data": [
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 6,
                "item_type": "一般项目",
                "time_range": "本月",
                "tax_payable": 59188
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 6,
                "item_type": "一般项目",
                "time_range": "累计",
                "tax_payable": 339484
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 6,
                "item_type": "一般项目",
                "time_range": "本月",
                "tax_payable": 76850
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 6,
                "item_type": "一般项目",
                "time_range": "累计",
                "tax_payable": 440788
              }
            ],
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month,\n         item_type, time_range, taxpayer_type, revision_no,\n         tax_payable,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month, item_type, time_range\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_vat_return_general\n  WHERE taxpayer_id = '91330200MA2KXXXXXX'\n    AND period_year IN (2024, 2025)\n    AND period_month = 6\n    AND item_type = '一般项目'\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_month,\n       item_type, time_range,\n       tax_payable\nFROM latest WHERE rn = 1\nORDER BY period_year, period_month\nLIMIT 1000;"
          }
        ],
        "display_data": {
          "display_type": "cross_domain",
          "table": {
            "headers": [
              "期间",
              "企业所得税-利润总额",
              "企业所得税-应纳所得税额",
              "企业所得税-本期应补（退）所得税额",
              "利润表-利润总额",
              "增值税-应纳税额"
            ],
            "rows": [
              {
                "期间": "2024-06",
                "企业所得税-利润总额": "482.44万",
                "企业所得税-应纳所得税额": "120.61万",
                "企业所得税-本期应补（退）所得税额": "120.61万",
                "利润表-利润总额": "59.19万",
                "增值税-应纳税额": "33.95万"
              },
              {
                "期间": "2025-06",
                "企业所得税-利润总额": "626.40万",
                "企业所得税-应纳所得税额": "156.60万",
                "企业所得税-本期应补（退）所得税额": "156.60万",
                "利润表-利润总额": "76.85万",
                "增值税-应纳税额": "44.08万"
              }
            ],
            "columns": [
              "period",
              "eit_total_profit",
              "eit_tax_payable",
              "eit_current_tax_payable_or_refund",
              "profit_total_profit",
              "vat_tax_payable"
            ]
          },
          "chart_data": {
            "chartType": "bar",
            "title": "跨域 企业所得税-利润总额、企业所得税-应纳所得税额、企业所得税-本期应补（退）所得税额 趋势分析",
            "labels": [
              "2024-06",
              "2025-06"
            ],
            "datasets": [
              {
                "label": "企业所得税-利润总额",
                "data": [
                  4824375,
                  6264000
                ],
                "type": "bar",
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "企业所得税-应纳所得税额",
                "data": [
                  1206093.75,
                  1566000
                ],
                "type": "bar",
                "backgroundColor": "rgba(255, 99, 132, 0.8)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "企业所得税-本期应补（退）所得税额",
                "data": [
                  1206093.75,
                  1566000
                ],
                "type": "bar",
                "backgroundColor": "rgba(75, 192, 192, 0.8)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "利润表-利润总额",
                "data": [
                  591913,
                  768546
                ],
                "type": "bar",
                "backgroundColor": "rgba(255, 206, 86, 0.8)",
                "borderColor": "rgba(255, 206, 86, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "增值税-应纳税额",
                "data": [
                  339484,
                  440788
                ],
                "type": "bar",
                "backgroundColor": "rgba(153, 102, 255, 0.8)",
                "borderColor": "rgba(153, 102, 255, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              }
            ]
          },
          "growth": [
            {
              "period": "2025-06",
              "企业所得税-利润总额": {
                "current": 6264000,
                "previous": 4824375,
                "change": 1439625,
                "change_pct": 29.84,
                "trend": "up"
              },
              "企业所得税-应纳所得税额": {
                "current": 1566000,
                "previous": 1206093.75,
                "change": 359906.25,
                "change_pct": 29.84,
                "trend": "up"
              },
              "企业所得税-本期应补（退）所得税额": {
                "current": 1566000,
                "previous": 1206093.75,
                "change": 359906.25,
                "change_pct": 29.84,
                "trend": "up"
              },
              "利润表-利润总额": {
                "current": 768546,
                "previous": 591913,
                "change": 176633,
                "change_pct": 29.84,
                "trend": "up"
              },
              "增值税-应纳税额": {
                "current": 440788,
                "previous": 339484,
                "change": 101304,
                "change_pct": 29.84,
                "trend": "up"
              }
            }
          ],
          "summary": "eit vs profit vs vat，共2个期间"
        },
        "response_mode": "detailed",
        "cache_hit": true,
        "cache_key": "78f78c2535ad2d206383229819dcb2a7",
        "cached_interpretation": "",
        "need_reinterpret": true,
        "thinking_mode": "think"
      },
      "company_id": "91330200MA2KXXXXXX",
      "user_id": 1,
      "domain": ""
    },
    {
      "query": "2024年3月和2025年3月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
      "status": "success",
      "route": "financial_data",
      "timestamp": "下午9:20:30",
      "cache_key": "",
      "conversation_history": [],
      "conversation_enabled": false,
      "conversation_depth": 3,
      "response_mode": "detailed",
      "thinking_mode": "quick",
      "result": {
        "success": true,
        "route": "financial_data",
        "domain": "cross_domain",
        "results": [
          {
            "period": "2024-03",
            "eit_total_profit": 2412188,
            "eit_tax_payable": 603047,
            "profit_total_profit": 568232,
            "vat_tax_payable": 162365
          },
          {
            "period": "2025-03",
            "eit_total_profit": 3132000,
            "eit_tax_payable": 783000,
            "profit_total_profit": 737796,
            "vat_tax_payable": 210816
          }
        ],
        "cross_domain_summary": "eit vs profit vs vat，共2个期间",
        "cross_domain_operation": "compare",
        "sub_results": [
          {
            "domain": "eit",
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_quarter, revision_no,\n         total_profit, tax_payable,\n         ROW_NUMBER() OVER (\n           PARTITION BY taxpayer_id, period_year, period_quarter\n           ORDER BY revision_no DESC\n         ) AS rn\n  FROM vw_eit_quarter_main\n  WHERE taxpayer_id = :taxpayer_id\n    AND period_year IN (2024, 2025)\n    AND period_quarter = 1\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_quarter,\n       total_profit, tax_payable\nFROM latest WHERE rn = 1\nORDER BY period_year\nLIMIT 1000;",
            "data": [
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_quarter": 1,
                "total_profit": 2412188,
                "tax_payable": 603047
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_quarter": 1,
                "total_profit": 3132000,
                "tax_payable": 783000
              }
            ]
          },
          {
            "domain": "profit",
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month,\n         time_range, accounting_standard_name, revision_no,\n         total_profit,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month, time_range\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_profit_eas\n  WHERE taxpayer_id = :taxpayer_id\n    AND period_year IN (2024, 2025)\n    AND period_month = 3\n    AND time_range = '本期'\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_month, time_range,\n       accounting_standard_name, revision_no, total_profit\nFROM latest WHERE rn = 1\nORDER BY period_year, period_month\nLIMIT 1000",
            "data": [
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 3,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 568232
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 3,
                "time_range": "本期",
                "accounting_standard_name": "企业会计准则",
                "revision_no": 0,
                "total_profit": 737796
              }
            ]
          },
          {
            "domain": "vat",
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month,\n         item_type, time_range, taxpayer_type, revision_no,\n         tax_payable,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month, item_type, time_range\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_vat_return_general\n  WHERE taxpayer_id = :taxpayer_id\n    AND period_year IN (2024, 2025)\n    AND period_month = 3\n    AND item_type = '一般项目'\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_month,\n       item_type, time_range,\n       tax_payable\nFROM latest WHERE rn = 1\nORDER BY period_year\nLIMIT 1000;",
            "data": [
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 3,
                "item_type": "一般项目",
                "time_range": "本月",
                "tax_payable": 56820
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2024,
                "period_month": 3,
                "item_type": "一般项目",
                "time_range": "累计",
                "tax_payable": 162365
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 3,
                "item_type": "一般项目",
                "time_range": "本月",
                "tax_payable": 73776
              },
              {
                "taxpayer_id": "91330200MA2KXXXXXX",
                "taxpayer_name": "创智软件股份有限公司",
                "period_year": 2025,
                "period_month": 3,
                "item_type": "一般项目",
                "time_range": "累计",
                "tax_payable": 210816
              }
            ]
          }
        ],
        "entities": {
          "taxpayer_id": "91330200MA2KXXXXXX",
          "taxpayer_name": "TSE科技有限公司",
          "taxpayer_type": "一般纳税人",
          "period_year": 2024,
          "period_month": 3,
          "period_end_month": 3,
          "period_quarter": null,
          "period_years": null,
          "period_months": null,
          "time_range_hint": null,
          "item_type_hint": null,
          "domain_hint": "cross_domain",
          "time_granularity": null,
          "original_query": "TSE科技有限公司 2024年3月和2025年3月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
          "resolved_query": "TSE科技有限公司 2024年3月和2025年3月利润总额、增值税应纳税额、企业所得税应纳税额比较分析",
          "cross_domain_list": [
            "eit",
            "profit",
            "vat"
          ],
          "period_end_year": 2025,
          "accounting_standard": "企业会计准则"
        },
        "cache_hit": true,
        "cache_source": "l2",
        "need_reinterpret": true,
        "response_mode": "detailed",
        "thinking_mode": "quick",
        "display_data": {
          "display_type": "cross_domain",
          "table": {
            "headers": [
              "期间",
              "企业所得税-利润总额",
              "企业所得税-应纳所得税额",
              "利润表-利润总额",
              "增值税-应纳税额"
            ],
            "rows": [
              {
                "期间": "2024-03",
                "企业所得税-利润总额": "241.22万",
                "企业所得税-应纳所得税额": "60.30万",
                "利润表-利润总额": "56.82万",
                "增值税-应纳税额": "16.24万"
              },
              {
                "期间": "2025-03",
                "企业所得税-利润总额": "313.20万",
                "企业所得税-应纳所得税额": "78.30万",
                "利润表-利润总额": "73.78万",
                "增值税-应纳税额": "21.08万"
              }
            ],
            "columns": [
              "period",
              "eit_total_profit",
              "eit_tax_payable",
              "profit_total_profit",
              "vat_tax_payable"
            ]
          },
          "chart_data": {
            "chartType": "bar",
            "title": "跨域 企业所得税-利润总额、企业所得税-应纳所得税额、利润表-利润总额 趋势分析",
            "labels": [
              "2024-03",
              "2025-03"
            ],
            "datasets": [
              {
                "label": "企业所得税-利润总额",
                "data": [
                  2412188,
                  3132000
                ],
                "type": "bar",
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "企业所得税-应纳所得税额",
                "data": [
                  603047,
                  783000
                ],
                "type": "bar",
                "backgroundColor": "rgba(255, 99, 132, 0.8)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "利润表-利润总额",
                "data": [
                  568232,
                  737796
                ],
                "type": "bar",
                "backgroundColor": "rgba(75, 192, 192, 0.8)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "增值税-应纳税额",
                "data": [
                  162365,
                  210816
                ],
                "type": "bar",
                "backgroundColor": "rgba(255, 206, 86, 0.8)",
                "borderColor": "rgba(255, 206, 86, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              }
            ]
          },
          "growth": [
            {
              "period": "2025-03",
              "企业所得税-利润总额": {
                "current": 3132000,
                "previous": 2412188,
                "change": 719812,
                "change_pct": 29.84,
                "trend": "up"
              },
              "企业所得税-应纳所得税额": {
                "current": 783000,
                "previous": 603047,
                "change": 179953,
                "change_pct": 29.84,
                "trend": "up"
              },
              "利润表-利润总额": {
                "current": 737796,
                "previous": 568232,
                "change": 169564,
                "change_pct": 29.84,
                "trend": "up"
              },
              "增值税-应纳税额": {
                "current": 210816,
                "previous": 162365,
                "change": 48451,
                "change_pct": 29.84,
                "trend": "up"
              }
            }
          ],
          "summary": "eit vs profit vs vat，共2个期间"
        }
      },
      "company_id": "91330200MA2KXXXXXX",
      "user_id": 1,
      "domain": "cross_domain"
    },
    {
      "query": "“2024年一月和2025年一月利润总额、增值税应纳税额、企业所得税应纳税额比较分析”",
      "status": "success",
      "timestamp": "下午9:09:15",
      "cache_key": "c740c2638e2ec8fb8e105778fbdfe3f0",
      "conversation_history": [],
      "conversation_enabled": false,
      "conversation_depth": 3,
      "response_mode": "detailed",
      "thinking_mode": "deep",
      "result": {
        "success": true,
        "user_query": "TSE科技有限公司 “2024年一月和2025年一月利润总额、增值税应纳税额、企业所得税应纳税额比较分析”",
        "clarification": null,
        "sql": null,
        "results": [
          {
            "period": "2024-01",
            "eit_value": null,
            "profit_total_profit": 366144,
            "vat_tax_payable": 39843
          },
          {
            "period": "2025-01",
            "eit_value": null,
            "profit_total_profit": 510000,
            "vat_tax_payable": 55497
          }
        ],
        "error": null,
        "entities": {
          "taxpayer_id": "91310115MA2KZZZZZZ",
          "taxpayer_name": "TSE科技有限公司",
          "taxpayer_type": "一般纳税人",
          "period_year": 2024,
          "period_month": 1,
          "period_end_month": 1,
          "period_quarter": null,
          "period_years": null,
          "period_months": null,
          "time_range_hint": null,
          "item_type_hint": null,
          "domain_hint": "cross_domain",
          "time_granularity": null,
          "original_query": "TSE科技有限公司 “2024年一月和2025年一月利润总额、增值税应纳税额、企业所得税应纳税额比较分析”",
          "resolved_query": "TSE科技有限公司 “2024年1月和2025年1月利润总额、增值税应纳税额、企业所得税应纳税额比较分析”",
          "cross_domain_list": [
            "eit",
            "profit",
            "vat"
          ],
          "period_end_year": 2025,
          "accounting_standard": "企业会计准则"
        },
        "intent": {
          "domain": "cross_domain",
          "cross_domain_list": [
            "eit",
            "profit",
            "vat"
          ],
          "vat_scope": {
            "taxpayer_type_hint": "一般纳税人",
            "views": [
              "vw_vat_return_general"
            ],
            "cross_type_union": false
          },
          "eit_scope": {
            "report_type": "annual",
            "views": [
              "vw_eit_annual_main"
            ]
          },
          "account_balance_scope": {
            "views": [
              "vw_account_balance"
            ],
            "account_filter": null
          },
          "balance_sheet_scope": {
            "gaap_type": "ASBE",
            "views": [
              "vw_balance_sheet_eas"
            ]
          },
          "profit_scope": {
            "accounting_standard": "ASBE",
            "views": [
              "vw_profit_eas"
            ]
          },
          "cash_flow_scope": {
            "accounting_standard": "企业会计准则",
            "views": [
              "vw_cash_flow_eas"
            ]
          },
          "financial_metrics_scope": {
            "views": [
              "vw_financial_metrics"
            ]
          },
          "invoice_scope": {
            "direction": "both",
            "views": [
              "vw_inv_spec_purchase",
              "vw_inv_spec_sales"
            ]
          },
          "select": {
            "metrics": [
              "total_profit",
              "tax_payable",
              "tax_payable"
            ],
            "dimensions": [
              "taxpayer_name"
            ]
          },
          "filters": {
            "taxpayer_id": "91310115MA2KZZZZZZ",
            "period_mode": "range_month",
            "period": {
              "year": 2024,
              "month": 1,
              "quarter": null,
              "end_month": 1,
              "end_year": 2025
            },
            "quarter_mode": "single",
            "vat_dims": {
              "item_type": "一般项目",
              "time_range": "累计"
            },
            "profit_time_range": "本年累计",
            "account_name": null,
            "category": null,
            "revision_strategy": "latest"
          },
          "aggregation": {
            "group_by": [],
            "order_by": [],
            "limit": 1000
          },
          "need_clarification": false,
          "clarifying_questions": []
        },
        "audit_violations": null,
        "taxpayer_id": "91310115MA2KZZZZZZ",
        "taxpayer_name": "TSE科技有限公司",
        "period": "2024年1月",
        "domain": "cross_domain",
        "cross_domain_summary": "eit vs profit vs vat，共2个期间",
        "cross_domain_operation": "compare",
        "sub_results": [
          {
            "domain": "eit",
            "data": [
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2024,
                "total_profit": 5121624,
                "tax_payable": 1280405
              },
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2025,
                "total_profit": 7133865,
                "tax_payable": 1783466
              }
            ],
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, revision_no,\n         total_profit, tax_payable,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_eit_annual_main\n  WHERE taxpayer_id = '91310115MA2KZZZZZZ'\n    AND period_year IN (2024, 2025)\n)\nSELECT taxpayer_id, taxpayer_name, period_year,\n       total_profit, tax_payable\nFROM latest WHERE rn = 1\nORDER BY period_year\nLIMIT 1000;"
          },
          {
            "domain": "profit",
            "data": [
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2024,
                "period_month": 1,
                "time_range": "本年累计",
                "total_profit": 366144
              },
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2025,
                "period_month": 1,
                "time_range": "本年累计",
                "total_profit": 510000
              }
            ],
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month,\n         time_range, accounting_standard_name, revision_no,\n         total_profit,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month, time_range\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_profit_eas\n  WHERE taxpayer_id = '91310115MA2KZZZZZZ'\n    AND period_year IN (2024, 2025)\n    AND period_month = 1\n    AND time_range = '本年累计'\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_month, time_range,\n       total_profit\nFROM latest WHERE rn = 1\nORDER BY period_year, period_month\nLIMIT 1000"
          },
          {
            "domain": "vat",
            "data": [
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2024,
                "period_month": 1,
                "item_type": "一般项目",
                "time_range": "本月",
                "tax_payable": 39843
              },
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2024,
                "period_month": 1,
                "item_type": "一般项目",
                "time_range": "累计",
                "tax_payable": 39843
              },
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2025,
                "period_month": 1,
                "item_type": "一般项目",
                "time_range": "本月",
                "tax_payable": 55497
              },
              {
                "taxpayer_id": "91310115MA2KZZZZZZ",
                "taxpayer_name": "TSE科技有限公司",
                "period_year": 2025,
                "period_month": 1,
                "item_type": "一般项目",
                "time_range": "累计",
                "tax_payable": 55497
              }
            ],
            "sql": "WITH latest AS (\n  SELECT taxpayer_id, taxpayer_name, period_year, period_month,\n         item_type, time_range, taxpayer_type, revision_no,\n         tax_payable,\n    ROW_NUMBER() OVER (\n      PARTITION BY taxpayer_id, period_year, period_month, item_type, time_range\n      ORDER BY revision_no DESC\n    ) AS rn\n  FROM vw_vat_return_general\n  WHERE taxpayer_id = '91310115MA2KZZZZZZ'\n    AND period_year IN (2024, 2025)\n    AND period_month = 1\n    AND item_type = '一般项目'\n)\nSELECT taxpayer_id, taxpayer_name, period_year, period_month,\n       item_type, time_range,\n       tax_payable\nFROM latest WHERE rn = 1\nORDER BY period_year\nLIMIT 1000;"
          }
        ],
        "display_data": {
          "display_type": "cross_domain",
          "table": {
            "headers": [
              "期间",
              "eit_value",
              "利润表-利润总额",
              "增值税-应纳税额"
            ],
            "rows": [
              {
                "期间": "2024-01",
                "eit_value": "-",
                "利润表-利润总额": "36.61万",
                "增值税-应纳税额": "3.98万"
              },
              {
                "期间": "2025-01",
                "eit_value": "-",
                "利润表-利润总额": "51.00万",
                "增值税-应纳税额": "5.55万"
              }
            ],
            "columns": [
              "period",
              "eit_value",
              "profit_total_profit",
              "vat_tax_payable"
            ]
          },
          "chart_data": {
            "chartType": "bar",
            "title": "跨域 利润表-利润总额、增值税-应纳税额 趋势分析",
            "labels": [
              "2024-01",
              "2025-01"
            ],
            "datasets": [
              {
                "label": "利润表-利润总额",
                "data": [
                  366144,
                  510000
                ],
                "type": "bar",
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              },
              {
                "label": "增值税-应纳税额",
                "data": [
                  39843,
                  55497
                ],
                "type": "bar",
                "backgroundColor": "rgba(255, 99, 132, 0.8)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
                "borderRadius": 4,
                "yAxisID": "y"
              }
            ]
          },
          "growth": [
            {
              "period": "2025-01",
              "利润表-利润总额": {
                "current": 510000,
                "previous": 366144,
                "change": 143856,
                "change_pct": 39.29,
                "trend": "up"
              },
              "增值税-应纳税额": {
                "current": 55497,
                "previous": 39843,
                "change": 15654,
                "change_pct": 39.29,
                "trend": "up"
              }
            }
          ],
          "summary": "eit vs profit vs vat，共2个期间"
        },
        "response_mode": "detailed",
        "cache_key": "c740c2638e2ec8fb8e105778fbdfe3f0",
        "cache_hit": false,
        "need_reinterpret": false
      },
      "company_id": "91310115MA2KZZZZZZ",
      "user_id": 1,
      "domain": ""
    }
  ],
  "total": 35,
  "page": 1,
  "page_size": 5,
  "total_pages": 7
}