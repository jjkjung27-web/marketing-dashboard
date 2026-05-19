from dataclasses import dataclass, field


@dataclass
class SizePreset:
    channel: str
    name: str
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.name} ({self.width}×{self.height})"


@dataclass
class LayoutElement:
    name: str       # "logo", "main_copy", "sub_copy", "cta", "hero_image", "background"
    x: float        # 0.0 ~ 1.0 (원본 이미지 기준 상대 좌표)
    y: float
    width: float
    height: float
    priority: int   # 1=최고 우선순위 (잘리면 안 됨)


@dataclass
class AnalysisResult:
    elements: list[LayoutElement]
    background_color: str           # hex, e.g. "#FFFFFF"
    color_palette: list[str]        # hex 목록
    guide_constraints: dict = field(default_factory=dict)
    # guide_constraints 예시:
    # {"safe_zone": 0.05, "forbidden_zones": [...], "logo_min_width": 0.1}
