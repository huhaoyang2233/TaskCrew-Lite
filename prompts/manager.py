"""
提示词管理模块
"""
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    name: str
    content: str
    description: str = ""
    version: str = "1.0"


class PromptManager:
    def __init__(self):
        self._prompts: Dict[str, PromptTemplate] = {}
        self._init_default_prompts()
    
    def _init_default_prompts(self):
        self._prompts["orchestrator"] = PromptTemplate(
            name="orchestrator",
            description="协调器系统提示词",
            content="""你是一个智能任务协调器，负责协调规划器、执行器和反思器之间的工作。"""
        )
        self._prompts["planner"] = PromptTemplate(
            name="planner",
            description="规划器系统提示词",
            content="""你是一个任务规划专家，负责将复杂任务分解为可执行的步骤。"""
        )
        self._prompts["executor"] = PromptTemplate(
            name="executor",
            description="执行器系统提示词",
            content="""你是一个任务执行专家，负责调用工具完成具体任务。"""
        )
        self._prompts["reflector"] = PromptTemplate(
            name="reflector",
            description="反思器系统提示词",
            content="""你是一个任务反思专家，负责评估执行结果并决定下一步行动。"""
        )
    
    def get_prompt(self, name: str) -> Optional[str]:
        template = self._prompts.get(name)
        return template.content if template else None
    
    def update_prompt(self, name: str, content: str) -> bool:
        if name in self._prompts:
            self._prompts[name].content = content
            return True
        return False


prompt_manager = PromptManager()
