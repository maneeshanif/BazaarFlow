"""
Guardrails module for input and output validation.
"""

# Import guardrails if they exist
try:
    from guardrails.input_guardrail import product_name_input_guardrail
except ImportError:
    product_name_input_guardrail = None

try:
    from guardrails.output_guardrail import inventory_output_guardrail
except ImportError:
    inventory_output_guardrail = None

__all__ = [
    "product_name_input_guardrail",
    "inventory_output_guardrail",
]
