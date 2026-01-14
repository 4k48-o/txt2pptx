"""
检查任务状态的调试脚本
"""

import json
import sys
from src.manus_client import ManusClient

def check_task(task_id: str, show_full_json: bool = False):
    """查看任务详细信息"""
    client = ManusClient()
    
    print(f"\n🔍 获取任务信息: {task_id}\n")
    
    # 获取任务详情
    result = client.get(f"/v1/tasks/{task_id}")
    
    # 状态图标
    status = result.get('status', 'unknown')
    status_icons = {
        'pending': '⏳',
        'running': '🔄',
        'completed': '✅',
        'failed': '❌'
    }
    status_icon = status_icons.get(status, '❓')
    
    # 基本信息
    print("=" * 60)
    print(f"📋 任务状态: {status_icon} {status.upper()}")
    print("=" * 60)
    
    metadata = result.get('metadata', {})
    print(f"  🆔 任务 ID: {result.get('id', 'N/A')}")
    print(f"  📝 标题: {metadata.get('task_title', 'N/A')}")
    print(f"  🔗 链接: {metadata.get('task_url', 'N/A')}")
    print(f"  💰 积分使用: {result.get('credit_usage', 0)}")
    print(f"  🤖 模型: {result.get('model', 'N/A')}")
    
    # 解析 output 消息来显示进度
    outputs = result.get('output', [])
    print(f"\n📊 执行进度: {len(outputs)} 条消息")
    print("-" * 60)
    
    if outputs:
        for i, output in enumerate(outputs):
            role = output.get('role', '')
            msg_status = output.get('status', '')
            msg_type = output.get('type', '')
            
            role_icon = '👤' if role == 'user' else '🤖'
            status_mark = '✓' if msg_status == 'completed' else '○'
            
            # 获取消息内容
            content = output.get('content', [])
            text = ""
            file_info = ""
            
            for item in content:
                item_type = item.get('type', '')
                if item_type == 'output_text':
                    text = item.get('text', '')[:100]
                    if len(item.get('text', '')) > 100:
                        text += "..."
                elif item_type in ['file', 'output_file', 'artifact']:
                    file_url = item.get('url', item.get('file_url', ''))
                    if file_url:
                        file_info = f"📁 文件: {file_url[:60]}..."
            
            print(f"  [{status_mark}] {role_icon} {msg_type}")
            if text:
                print(f"      💬 {text}")
            if file_info:
                print(f"      {file_info}")
    
    # 查找文件输出
    print("\n" + "-" * 60)
    print("📁 查找文件输出:")
    
    found_files = []
    for output in outputs:
        content = output.get('content', [])
        for item in content:
            item_type = item.get('type', '')
            if item_type in ['file', 'output_file', 'artifact']:
                url = item.get('url', item.get('file_url', ''))
                if url:
                    found_files.append(url)
    
    if found_files:
        for f in found_files:
            print(f"  ✅ {f}")
    else:
        print("  ⏳ 暂无文件输出（任务可能仍在进行中）")
    
    print("=" * 60)
    
    # 完整 JSON（可选）
    if show_full_json:
        print("\n完整 JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_task.py <task_id> [--full]")
        print("Example: python check_task.py g6HeS33BTYWHkXRpC835hY")
        print("         python check_task.py g6HeS33BTYWHkXRpC835hY --full")
        sys.exit(1)
    
    task_id = sys.argv[1]
    show_full = "--full" in sys.argv
    check_task(task_id, show_full)

