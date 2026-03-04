"""测试管线是否接受conversation_history参数"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mvp_pipeline import run_pipeline, run_pipeline_stream


def test_pipeline_accepts_history():
    """测试管线函数接受conversation_history参数"""
    print("\n" + "="*60)
    print("测试管线接受对话历史参数")
    print("="*60)

    # 模拟对话历史
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年1月的增值税",
            "timestamp": "2026-03-02T10:00:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年1月的增值税为...",
            "timestamp": "2026-03-02T10:00:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": "vat",
                "entities": {
                    "taxpayer_id": "91310000MA1FL8XQ30",
                    "period_year": 2025,
                    "period_month": 1,
                },
            },
        },
    ]

    # 测试1: run_pipeline 不带历史
    print("\n【测试1】run_pipeline 不带对话历史")
    try:
        result = run_pipeline("华兴科技2025年1月的增值税")
        print(f"  ✓ 调用成功 (不带历史)")
    except TypeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试2: run_pipeline 带历史
    print("\n【测试2】run_pipeline 带对话历史")
    try:
        result = run_pipeline("2月呢?", conversation_history=conversation_history)
        print(f"  ✓ 调用成功 (带历史)")
    except TypeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试3: run_pipeline_stream 不带历史
    print("\n【测试3】run_pipeline_stream 不带对话历史")
    try:
        events = list(run_pipeline_stream("华兴科技2025年1月的增值税"))
        print(f"  ✓ 调用成功 (不带历史), {len(events)} 个事件")
    except TypeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试4: run_pipeline_stream 带历史
    print("\n【测试4】run_pipeline_stream 带对话历史")
    try:
        events = list(run_pipeline_stream("2月呢?", conversation_history=conversation_history))
        print(f"  ✓ 调用成功 (带历史), {len(events)} 个事件")
    except TypeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "="*60)
    print("🎉 所有管线测试通过!")
    print("="*60)
    print("\n管线函数正确接受conversation_history参数:")
    print("  ✓ run_pipeline() 不带历史")
    print("  ✓ run_pipeline() 带历史")
    print("  ✓ run_pipeline_stream() 不带历史")
    print("  ✓ run_pipeline_stream() 带历史")
    return True


if __name__ == "__main__":
    try:
        success = test_pipeline_accepts_history()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
