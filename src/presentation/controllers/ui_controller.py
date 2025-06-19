"""
UI控制器基类
提供UI组件的统一管理和事件处理接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import gradio as gr


class UIController(ABC):
    """UI控制器抽象基类

    定义UI组件的标准接口，包括组件创建、事件绑定和状态管理
    """

    def __init__(self, name: str):
        """初始化UI控制器

        Args:
            name: 控制器名称，用于标识和调试
        """
        self.name = name
        self.components: Dict[str, Any] = {}
        self.event_handlers: List[Dict[str, Any]] = []

    @abstractmethod
    def create_components(self) -> Dict[str, Any]:
        """创建UI组件

        Returns:
            包含所有UI组件的字典，键为组件名称，值为Gradio组件对象
        """
        pass

    @abstractmethod
    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定

        Returns:
            事件绑定配置列表，每个配置包含组件、事件类型、处理函数等信息
        """
        pass

    def get_component(self, name: str) -> Optional[Any]:
        """获取指定名称的组件

        Args:
            name: 组件名称

        Returns:
            组件对象，如果不存在则返回None
        """
        return self.components.get(name)

    def initialize(self) -> None:
        """初始化控制器

        依次执行组件创建和事件设置
        """
        self.components = self.create_components()
        self.event_handlers = self.setup_events()

    def render(self) -> Any:
        """渲染UI组件

        子类可以重写此方法来自定义渲染逻辑

        Returns:
            渲染后的UI组件或容器
        """
        return self.components


class TabController(UIController):
    """Tab页面控制器基类

    专门用于管理Gradio Tab页面的控制器
    """

    def __init__(self, name: str, title: str):
        """初始化Tab控制器

        Args:
            name: 控制器名称
            title: Tab页面标题
        """
        super().__init__(name)
        self.title = title
        self.tab_container = None

    def render(self) -> gr.Tab:
        """渲染Tab页面

        Returns:
            包含所有组件的Gradio Tab对象
        """
        with gr.Tab(self.title) as self.tab_container:
            self._render_content()

        return self.tab_container

    @abstractmethod
    def _render_content(self) -> None:
        """渲染Tab页面内容

        子类需要实现此方法来定义具体的页面布局
        """
        pass