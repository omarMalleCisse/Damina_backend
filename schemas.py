from typing import List, Optional
from pydantic import BaseModel


class FeatureResponse(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class FilterResponse(BaseModel):
    id: str
    label: str

    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None

    class Config:
        from_attributes = True


class DesignBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: Optional[str] = None
    is_premium: Optional[bool] = False
    image_path: Optional[str] = None
    category_ids: Optional[List[int]] = []


class DesignCreate(DesignBase):
    pass


class DesignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    is_premium: Optional[bool] = None
    image_path: Optional[str] = None
    category_ids: Optional[List[int]] = None


class DesignResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: Optional[str]
    is_premium: bool
    download_count: int
    downloads: Optional[str]
    image_path: Optional[str]
    categories: List[CategoryResponse] = []

    class Config:
        from_attributes = True
