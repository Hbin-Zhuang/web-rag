"""
事件处理器管理类
统一管理和绑定UI组件的事件处理逻辑
"""

from typing import Any, Dict, List, Callable
import gradio as gr


class EventManager:
    """事件管理器

    负责统一管理和绑定UI组件的事件处理逻辑
    """

    def __init__(self):
        """初始化事件管理器"""
        self.registered_events: List[Dict[str, Any]] = []
        self.event_handlers: Dict[str, Callable] = {}

    def register_controller_events(self, controller) -> None:
        """注册控制器的事件

        Args:
            controller: Tab控制器实例
        """
        # 获取控制器的事件配置
        events = controller.setup_events()
        handlers = controller.get_event_handlers()

        # 注册事件处理函数
        for handler_name, handler_func in handlers.items():
            self.event_handlers[f"{controller.name}_{handler_name}"] = handler_func

        # 保存事件配置
        for event_config in events:
            event_config['controller'] = controller
            event_config['handler_key'] = f"{controller.name}_{event_config['handler']}"
            self.registered_events.append(event_config)

    def bind_all_events(self) -> None:
        """绑定所有已注册的事件"""
        for event_config in self.registered_events:
            self._bind_single_event(event_config)

    def _bind_single_event(self, event_config: Dict[str, Any]) -> None:
        """绑定单个事件

        Args:
            event_config: 事件配置字典
        """
        try:
            controller = event_config['controller']
            component_name = event_config['component']
            event_type = event_config['event']
            handler_key = event_config['handler_key']
            inputs = event_config.get('inputs', [])
            outputs = event_config.get('outputs', [])

            # 获取组件对象
            component = controller.get_component(component_name)
            if component is None:
                print(f"⚠️ 警告: 找不到组件 {component_name} 在控制器 {controller.name}")
                return

            # 获取事件处理函数
            handler_func = self.event_handlers.get(handler_key)
            if handler_func is None:
                print(f"⚠️ 警告: 找不到处理函数 {handler_key}")
                return

            # 解析输入输出组件
            input_components = self._resolve_components(controller, inputs)
            output_components = self._resolve_components(controller, outputs)

            # 绑定事件
            if event_type == "upload":
                component.upload(
                    fn=handler_func,
                    inputs=input_components,
                    outputs=output_components
                )
            elif event_type == "clear":
                component.clear(
                    fn=handler_func,
                    inputs=input_components,
                    outputs=output_components
                )
            elif event_type == "change":
                component.change(
                    fn=handler_func,
                    inputs=input_components,
                    outputs=output_components
                )
            elif event_type == "click":
                component.click(
                    fn=handler_func,
                    inputs=input_components,
                    outputs=output_components
                )
            elif event_type == "submit":
                component.submit(
                    fn=handler_func,
                    inputs=input_components,
                    outputs=output_components
                )
            else:
                print(f"⚠️ 警告: 不支持的事件类型 {event_type}")

        except Exception as e:
            print(f"❌ 绑定事件失败: {e}")

    def _resolve_components(self, controller, component_names: List[str]) -> List[Any]:
        """解析组件名称列表为组件对象列表

        Args:
            controller: 控制器实例
            component_names: 组件名称列表

        Returns:
            组件对象列表
        """
        components = []
        for name in component_names:
            component = controller.get_component(name)
            if component is not None:
                components.append(component)
            else:
                # 尝试从全局组件注册表查找（用于跨Tab的组件引用）
                global_component = self._find_global_component(name)
                if global_component is not None:
                    components.append(global_component)
                else:
                    print(f"⚠️ 警告: 找不到组件 {name}")

        return components

    def _find_global_component(self, component_name: str) -> Any:
        """从全局组件注册表查找组件

        Args:
            component_name: 组件名称

        Returns:
            组件对象，如果找不到则返回None
        """
        # 遍历所有注册的控制器查找组件
        for event_config in self.registered_events:
            controller = event_config['controller']
            component = controller.get_component(component_name)
            if component is not None:
                return component

        return None

    def get_handler_count(self) -> int:
        """获取已注册的事件处理器数量

        Returns:
            事件处理器数量
        """
        return len(self.event_handlers)

    def get_event_count(self) -> int:
        """获取已注册的事件数量

        Returns:
            事件数量
        """
        return len(self.registered_events)

    def print_summary(self) -> None:
        """打印事件管理器摘要信息"""
        print(f"📋 事件管理器摘要:")
        print(f"   - 已注册事件处理器: {self.get_handler_count()} 个")
        print(f"   - 已注册事件绑定: {self.get_event_count()} 个")

        for event_config in self.registered_events:
            controller_name = event_config['controller'].name
            component_name = event_config['component']
            event_type = event_config['event']
            handler_name = event_config['handler']
            print(f"   - {controller_name}.{component_name}.{event_type} -> {handler_name}")


class CrossTabEventManager:
    """跨Tab事件管理器

    专门处理需要跨Tab组件交互的事件绑定
    """

    def __init__(self, event_manager: EventManager):
        """初始化跨Tab事件管理器

        Args:
            event_manager: 主事件管理器实例
        """
        self.event_manager = event_manager
        self.cross_tab_bindings: List[Dict[str, Any]] = []

    def register_cross_tab_binding(self,
                                 source_controller,
                                 source_component: str,
                                 target_controller,
                                 target_component: str,
                                 event_type: str = "change") -> None:
        """注册跨Tab组件绑定

        Args:
            source_controller: 源控制器
            source_component: 源组件名称
            target_controller: 目标控制器
            target_component: 目标组件名称
            event_type: 事件类型
        """
        binding = {
            'source_controller': source_controller,
            'source_component': source_component,
            'target_controller': target_controller,
            'target_component': target_component,
            'event_type': event_type
        }
        self.cross_tab_bindings.append(binding)

    def setup_cross_tab_events(self) -> None:
        """设置所有跨Tab事件绑定"""
        for binding in self.cross_tab_bindings:
            self._setup_single_cross_tab_event(binding)

    def _setup_single_cross_tab_event(self, binding: Dict[str, Any]) -> None:
        """设置单个跨Tab事件绑定

        Args:
            binding: 绑定配置字典
        """
        try:
            source_comp = binding['source_controller'].get_component(binding['source_component'])
            target_comp = binding['target_controller'].get_component(binding['target_component'])

            if source_comp is None or target_comp is None:
                print(f"⚠️ 警告: 跨Tab绑定失败，组件不存在")
                return

            # 设置简单的更新绑定（这里可以根据需要扩展）
            def update_target(*args):
                return args[0] if args else ""

            if binding['event_type'] == "change":
                source_comp.change(
                    fn=update_target,
                    inputs=[source_comp],
                    outputs=[target_comp]
                )

        except Exception as e:
            print(f"❌ 跨Tab事件绑定失败: {e}")