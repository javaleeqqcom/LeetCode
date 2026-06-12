# tools/solution_struct.py
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class Language(Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"


class ParamKind(Enum):
    POSITIONAL = "positional"


@dataclass
class ConstraintStruct:
    """参数/返回值约束（可被 AI 或分析器填充）"""
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    max_length: Optional[int] = None


@dataclass
class ParamStruct:
    """方法参数的结构化描述"""
    name: str
    type_str: str                       # 注释字符串，如 "List[int]"
    origin_type: Optional[str] = None   # 基础类型名，如 "list"
    nullable: bool = False
    default_value: Optional[Any] = None
    constraints: ConstraintStruct = field(default_factory=ConstraintStruct)


@dataclass
class ReturnStruct:
    """方法返回值描述"""
    type_str: str
    origin_type: Optional[str] = None


@dataclass
class MethodStruct:
    """单个方法的完整结构化描述"""
    name: str
    params: List[ParamStruct]
    return_info: ReturnStruct
    source_code: str                   # 方法源代码片段


@dataclass
class ComplexityHint:
    """算法复杂度提示（可由分析器填写，初始为空）"""
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    estimated_n_limit: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class SolutionStruct:
    """
    跨语言的代码结构统一表示。

    由 solution_runner 在解析学生代码后导出，供 AI‑Agent 使用，
    AI 层无需再接触原始 AST 或语言细节。
    """
    language: Language
    class_name: str
    source_code: str
    methods: List[MethodStruct]
    complexity_hint: ComplexityHint = field(default_factory=ComplexityHint)

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """递归转换为纯字典，language 转为字符串"""
        d = asdict(self)
        d["language"] = self.language.value
        return d

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SolutionStruct":
        """从字典构建实例（需保证结构完整）"""
        # 还原 Language 枚举
        data["language"] = Language(data["language"])
        # 还原 methods 中的 MethodStruct 列表
        methods_raw = data.get("methods", [])
        methods = []
        for m in methods_raw:
            params = [
                ParamStruct(
                    name=p["name"],
                    type_str=p["type_str"],
                    origin_type=p.get("origin_type"),
                    nullable=p.get("nullable", False),
                    default_value=p.get("default_value"),
                    constraints=ConstraintStruct(**p.get("constraints", {}))
                )
                for p in m["params"]
            ]
            ret = ReturnStruct(
                type_str=m["return_info"]["type_str"],
                origin_type=m["return_info"].get("origin_type")
            )
            methods.append(
                MethodStruct(
                    name=m["name"],
                    params=params,
                    return_info=ret,
                    source_code=m.get("source_code", "")
                )
            )
        complexity = ComplexityHint(**data.get("complexity_hint", {}))
        return cls(
            language=data["language"],
            class_name=data["class_name"],
            source_code=data.get("source_code", ""),
            methods=methods,
            complexity_hint=complexity
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SolutionStruct":
        """从 JSON 字符串反序列化"""
        return cls.from_dict(json.loads(json_str))