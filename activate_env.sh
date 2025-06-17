#!/bin/bash
# Web RAG项目虚拟环境激活脚本

echo "🚀 激活Web RAG项目虚拟环境..."

# 检查虚拟环境是否存在
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，正在创建..."
    python3 -m venv .venv
    echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查是否成功激活
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 虚拟环境已激活: $VIRTUAL_ENV"
    echo "📦 Python版本: $(python --version)"
    echo "📍 pip位置: $(which pip)"
    echo ""
    echo "💡 使用方法:"
    echo "   • 安装依赖: pip install -r requirements.txt"
    echo "   • 运行应用: python app.py"
    echo "   • 退出环境: deactivate"
    echo ""
else
    echo "❌ 虚拟环境激活失败"
    exit 1
fi