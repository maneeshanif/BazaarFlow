from pydantic import BaseModel, Field
from typing import Optional


class SalesForm(BaseModel):
    customer_name: str = Field(..., description="Full name of the customer", examples=["Ali Khan"])
    customer_phone: str = Field(..., description="Customer WhatsApp or phone number", examples=["+923001234567"])
    product_id: str = Field(..., description="Product SKU or internal ID", examples=["sku-1234"])
    product_name: Optional[str] = Field(None, description="Readable product name", examples=["Mobile Charger"])
    quantity: int = Field(..., gt=0, description="Quantity ordered", examples=[1])
    budget: Optional[str] = Field(None, description="Expected spending range", examples=["3000-5000"])
    payment_status: Optional[str] = Field("pending", description="Payment status of the order", examples=["pending", "paid"])
    delivery_address: Optional[str] = Field(None, description="Delivery location", examples=["Karachi, Pakistan"])
    notes: Optional[str] = Field(None, description="Extra delivery instructions or preferences", examples=["Customer prefers evening delivery"])




# from pydantic import BaseModel, Field, EmailStr
# from typing import Optional


# class SalesForm(BaseModel):
#     customer_name: str = Field(..., example="Ali Khan")
#     customer_phone: str = Field(..., example="+923001234567")
#     product_id: str = Field(..., example="sku-1234")
#     product_name: Optional[str] = Field(None, example="Mobile Charger")
#     quantity: int = Field(..., gt=0, example=1)
#     budget: Optional[str] = Field(None, example="3000-5000")
#     payment_status: Optional[str] = Field("pending", example="pending")
#     delivery_address: Optional[str] = Field(None, example="Karachi, Pakistan")
#     notes: Optional[str] = Field(None, example="Customer prefers evening delivery")
