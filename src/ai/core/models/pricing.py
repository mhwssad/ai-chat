"""模型价格计算适配层。"""

from __future__ import annotations

from src.ai.storage import Model
from src.ai.utils.pricing_utils import (
    PricingCalculator as BasePricingCalculator,
    PricingRule,
    PricingUsage,
    pricing_calculator,
)

from .types import ModelCost, ModelUsage


class PricingCalculator:
    """把模型请求模块的 usage/model 转换给通用计费工具。"""

    def __init__(self, calculator: BasePricingCalculator = pricing_calculator) -> None:
        self._calculator = calculator

    def calculate(self, usage: ModelUsage, model: Model) -> ModelCost:
        cost = self._calculator.calculate(
            usage=PricingUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
            ),
            rule=self._rule_from_model(model),
        )
        return ModelCost(
            input_cost=cost.input_cost,
            output_cost=cost.output_cost,
            total_cost=cost.total_cost,
            currency=cost.currency,
        )

    def _rule_from_model(self, model: Model) -> PricingRule:
        return PricingRule(
            strategy=model.pricing_strategy,
            unit=model.pricing_unit,
            unit_size=model.pricing_unit_size,
            input_price=model.input_price,
            output_price=model.output_price,
            total_price=model.total_price,
            flat_price=model.flat_price,
            currency=model.currency,
        )
