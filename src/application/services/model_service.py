"""
模型服务
封装AI模型的选择、切换、状态管理等逻辑
集成基础设施层的配置和日志服务
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime

from src.shared.state.application_state import app_state
from src.infrastructure import (
    IConfigurationService,
    ILoggingService,
    get_config,
    get_logger,
    performance_monitor
)


class ModelService:
    """模型管理服务"""

    def __init__(self, config_service: IConfigurationService = None, logging_service: ILoggingService = None):
        # 基础设施服务
        self._config_service = config_service or get_config()
        self._logger = logging_service or get_logger()

        # 从配置获取模型元数据
        self._model_metadata = self._config_service.get_value("model_metadata", {
            "gemini-2.5-flash-preview-05-20": {
                "display_name": "Gemini 2.5 Flash Preview",
                "description": "最新预览版本，速度快，适合日常问答",
                "max_tokens": 8192,
                "recommended": True
            },
            "gemini-2.0-flash": {
                "display_name": "Gemini 2.0 Flash",
                "description": "稳定版本，平衡速度和质量",
                "max_tokens": 8192,
                "recommended": True
            },
            "gemini-2.0-flash-lite": {
                "display_name": "Gemini 2.0 Flash Lite",
                "description": "轻量版本，响应更快",
                "max_tokens": 4096,
                "recommended": False
            },
            "gemini-1.5-flash": {
                "display_name": "Gemini 1.5 Flash",
                "description": "经典快速版本",
                "max_tokens": 8192,
                "recommended": False
            },
            "gemini-1.5-pro": {
                "display_name": "Gemini 1.5 Pro",
                "description": "高质量版本，适合复杂问答",
                "max_tokens": 32768,
                "recommended": True
            }
        })

        self._logger.info("ModelService 初始化完成", extra={
            "available_models_count": len(self._model_metadata)
        })

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return app_state.available_models

    def get_current_model(self) -> str:
        """获取当前模型"""
        return app_state.current_model

    @performance_monitor(get_logger())
    def switch_model(self, model_name: str) -> Tuple[bool, str]:
        """
        切换模型

        Args:
            model_name: 模型名称

        Returns:
            (是否成功, 状态消息)
        """
        try:
            if model_name not in self.get_available_models():
                self._logger.warning("尝试切换到不支持的模型", extra={
                    "requested_model": model_name,
                    "available_models": self.get_available_models()
                })
                return False, f"❌ 不支持的模型: {model_name}"

            old_model = app_state.current_model
            app_state.current_model = model_name

            # 重置QA链，强制使用新模型重新初始化
            app_state.qa_chain = None

            success_msg = f"✅ 模型已切换: {old_model} → {model_name}"
            self._logger.info("模型切换成功", extra={
                "old_model": old_model,
                "new_model": model_name
            })

            return True, success_msg

        except Exception as e:
            error_msg = f"❌ 模型切换失败: {str(e)}"
            self._logger.error("模型切换失败", exception=e, extra={
                "requested_model": model_name
            })
            return False, error_msg

    def get_model_status(self) -> str:
        """获取当前模型状态"""
        try:
            current_model = app_state.current_model
            model_info = self._model_metadata.get(current_model, {})

            status_parts = [
                f"🤖 当前模型: {model_info.get('display_name', current_model)}",
                f"📝 描述: {model_info.get('description', '标准AI模型')}",
                f"📊 最大token: {model_info.get('max_tokens', '未知')}",
                f"⭐ 推荐: {'是' if model_info.get('recommended', False) else '否'}",
                f"🔧 状态: {'就绪' if app_state.qa_chain else '需要初始化'}"
            ]

            return "\\n".join(status_parts)

        except Exception as e:
            return f"❌ 获取模型状态失败: {str(e)}"

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """获取指定模型的详细信息"""
        return self._model_metadata.get(model_name)

    def get_recommended_models(self) -> List[str]:
        """获取推荐模型列表"""
        return [
            model for model, info in self._model_metadata.items()
            if info.get('recommended', False) and model in self.get_available_models()
        ]

    def validate_model_compatibility(self, model_name: str) -> Tuple[bool, str]:
        """
        验证模型兼容性

        Args:
            model_name: 模型名称

        Returns:
            (是否兼容, 验证消息)
        """
        try:
            if model_name not in self.get_available_models():
                return False, f"模型 {model_name} 不在支持列表中"

            model_info = self._model_metadata.get(model_name)
            if not model_info:
                return False, f"模型 {model_name} 缺少元数据信息"

            # 检查token限制
            max_tokens = model_info.get('max_tokens', 0)
            if max_tokens < 1000:
                return False, f"模型 {model_name} token限制过低 ({max_tokens})"

            return True, f"模型 {model_name} 兼容性验证通过"

        except Exception as e:
            return False, f"验证模型兼容性时发生错误: {str(e)}"

    def get_model_selection_info(self) -> str:
        """获取模型选择信息"""
        try:
            available_models = self.get_available_models()
            current_model = self.get_current_model()

            info_parts = ["## 🤖 可用模型信息\\n"]

            for model in available_models:
                model_info = self._model_metadata.get(model, {})
                is_current = " **(当前)**" if model == current_model else ""
                is_recommended = " 🌟" if model_info.get('recommended', False) else ""

                info_parts.append(
                    f"**{model_info.get('display_name', model)}{is_current}{is_recommended}**\\n"
                    f"- 描述: {model_info.get('description', '标准AI模型')}\\n"
                    f"- 最大token: {model_info.get('max_tokens', '未知')}\\n"
                )

            info_parts.append("\\n🌟 = 推荐模型")

            return "\\n".join(info_parts)

        except Exception as e:
            return f"❌ 获取模型信息失败: {str(e)}"

    def force_model_reinit(self) -> str:
        """强制模型重新初始化"""
        try:
            app_state.qa_chain = None
            app_state.system_ready = False

            return f"✅ 模型 {app_state.current_model} 已重新初始化"

        except Exception as e:
            return f"❌ 模型重新初始化失败: {str(e)}"