"""通用模型计费工具。

该模块只处理「用量 + 价格规则 => 费用」的计算，不依赖具体模型请求实现。
"""


from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol


@dataclass(frozen=True)
class PricingUsage:
    """统一计费用量。

    token 模型使用 input/output tokens；图片、音频、视频等模型可使用
    total_units 或 metadata 扩展具体业务维度。
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    input_units: float | None = None
    output_units: float | None = None
    total_units: float | None = None
    request_count: int = 1
    metadata: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class PricingRule:
    """统一计费规则。

    strategy:
        token: 按 input/output token 计费，默认 1000 token 一个计价单位。
        quantity: 按数量计费，例如图片张数、embedding 条数。
        duration: 按时长计费，例如音频秒数或视频秒数。
        flat: 按请求固定费用计费。
    """

    strategy: str = "token"
    unit: str = "token_1k"
    unit_size: float = 1000
    input_price: float | None = None
    output_price: float | None = None
    total_price: float | None = None
    flat_price: float | None = None
    currency: str = "USD"
    metadata: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class PricingCost:
    """统一费用结果。"""

    input_cost: float | None = None
    output_cost: float | None = None
    total_cost: float | None = None
    currency: str | None = None
    details: dict[str, float | int | str] = field(default_factory=dict)


class PricingStrategy(Protocol):
    """计费策略接口。"""

    def calculate(self, usage: PricingUsage, rule: PricingRule) -> PricingCost:
        """根据 usage 和 rule 计算费用。"""


class TokenPricingStrategy:
    """按 token 计费。"""

    def calculate(self, usage: PricingUsage, rule: PricingRule) -> PricingCost:
        unit_size = rule.unit_size or 1000
        input_cost = _unit_cost(usage.input_tokens, rule.input_price, unit_size)
        output_cost = _unit_cost(usage.output_tokens, rule.output_price, unit_size)
        total_cost = _unit_cost(usage.total_tokens, rule.total_price, unit_size)
        return _merge_cost(
            input_cost=input_cost,
            output_cost=output_cost,
            explicit_total_cost=total_cost,
            currency=rule.currency,
            details={"strategy": "token", "unit": rule.unit, "unit_size": unit_size},
        )


class QuantityPricingStrategy:
    """按数量计费，例如图片张数、embedding 条数。"""

    def calculate(self, usage: PricingUsage, rule: PricingRule) -> PricingCost:
        unit_size = rule.unit_size or 1
        input_cost = _unit_cost(usage.input_units, rule.input_price, unit_size)
        output_cost = _unit_cost(usage.output_units, rule.output_price, unit_size)
        total_cost = _unit_cost(usage.total_units, rule.total_price, unit_size)
        return _merge_cost(
            input_cost=input_cost,
            output_cost=output_cost,
            explicit_total_cost=total_cost,
            currency=rule.currency,
            details={"strategy": "quantity", "unit": rule.unit, "unit_size": unit_size},
        )


class DurationPricingStrategy:
    """按时长计费，例如音频秒、视频秒或分钟。"""

    def calculate(self, usage: PricingUsage, rule: PricingRule) -> PricingCost:
        unit_size = rule.unit_size or 1
        total_units = usage.total_units
        if total_units is None:
            raw_duration = usage.metadata.get("duration_seconds")
            total_units = float(raw_duration) if raw_duration is not None else None
        total_cost = _unit_cost(total_units, rule.total_price, unit_size)
        return _merge_cost(
            input_cost=None,
            output_cost=None,
            explicit_total_cost=total_cost,
            currency=rule.currency,
            details={"strategy": "duration", "unit": rule.unit, "unit_size": unit_size},
        )


class FlatPricingStrategy:
    """按请求固定费用计费。"""

    def calculate(self, usage: PricingUsage, rule: PricingRule) -> PricingCost:
        price = rule.flat_price if rule.flat_price is not None else rule.total_price
        total_cost = _unit_cost(usage.request_count, price, 1)
        return _merge_cost(
            input_cost=None,
            output_cost=None,
            explicit_total_cost=total_cost,
            currency=rule.currency,
            details={"strategy": "flat", "unit": rule.unit, "requests": usage.request_count},
        )


class PricingCalculator:
    """可注册策略的通用计费计算器。"""

    def __init__(self) -> None:
        self._strategies: dict[str, PricingStrategy] = {}
        self.register("token", TokenPricingStrategy())
        self.register("quantity", QuantityPricingStrategy())
        self.register("duration", DurationPricingStrategy())
        self.register("flat", FlatPricingStrategy())

    def register(self, strategy_name: str, strategy: PricingStrategy) -> None:
        self._strategies[strategy_name] = strategy

    def calculate(self, usage: PricingUsage, rule: PricingRule) -> PricingCost:
        strategy = self._strategies.get(rule.strategy)
        if strategy is None:
            raise ValueError(f"未知计费策略: {rule.strategy}")
        return strategy.calculate(usage, rule)


def _unit_cost(
    quantity: int | float | None,
    price: float | None,
    unit_size: int | float,
) -> float | None:
    if quantity is None or price is None:
        return None
    if unit_size <= 0:
        raise ValueError("计费单位大小必须大于 0")
    value = Decimal(str(quantity)) * Decimal(str(price)) / Decimal(str(unit_size))
    return float(value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP))


def _merge_cost(
    *,
    input_cost: float | None,
    output_cost: float | None,
    explicit_total_cost: float | None,
    currency: str,
    details: dict[str, float | int | str],
) -> PricingCost:
    total_cost = explicit_total_cost
    if total_cost is None and (input_cost is not None or output_cost is not None):
        total = Decimal(str(input_cost or 0)) + Decimal(str(output_cost or 0))
        total_cost = float(total.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP))

    return PricingCost(
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
        currency=currency if total_cost is not None else None,
        details=details,
    )


pricing_calculator = PricingCalculator()

