from fastapi import APIRouter, Header, HTTPException, Request, Query
from typing import List
from models.schemas import product_category, QuestionResponse, ShopifyProduct, filter
from services.auth import verify_api_key
from bson import ObjectId
import pandas as pd
from typing import Optional, Dict
from spellchecker import SpellChecker
router = APIRouter()


@router.get('/fourth_level_categories')
async def fourth_level_categories_view(x_api_key: str = Header(..., alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        categories_cursor = product_category.objects(end_level=True)
        categories_list = []
        for ins in categories_cursor:
            cat = {
                "id": str(ins.id),
                "name": ins.name,
            }
            categories_list.append(cat)
        return {"data": {"categories": categories_list}}
    except Exception as e:
        print(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
ATTRIBUTE_MAP: Dict[str, str] = {
    "color":            "Color",
    "capacity":         "Capacity",
    "energy_rating":    "Energy Rating",
    "connectivity":     "Connectivity",
    "tv_type":          "TV Type",
    "screen_size":      "Screen Size",
    "resolution":       "Resolution",
    "refresh_rate":     "Refresh Rate",
    "display_type":     "Display Type",
    "operating_system": "Operating System",
    "laundry_features": "Laundry Features",
    "load_type":        "Load Type",
    "smart_features":   "Smart Features",
}
BASE_QUERY_PARAMS = {"category", "search", "brand"}

@router.get('/products')
async def get_products_filtered(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-KEY"),
    category: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None, alias="search"),
    brand: Optional[str] = Query(None),
):
    print("\n" + "=" * 60)
    print("🔍 GET /products REQUEST")
    print("=" * 60)
    print("URL:   ", request.url)
    print("Query: ", dict(request.query_params))
    print("=" * 60 + "\n")
    try:
        verify_api_key(x_api_key)
        match: Dict[str, object] = {}
        
        if category:
            try:
                match["category_id"] = ObjectId(category)
            except Exception:
                return {"products": []}
        
        if brand:
            match["brand"] = {"$in": [b.strip() for b in brand.split(",")]}
        
        for raw_key, raw_val in request.query_params.items():
            q_key = raw_key.strip().replace(" ", "_").lower()
            if q_key in BASE_QUERY_PARAMS or q_key not in ATTRIBUTE_MAP:
                continue
            values: List[str] = [v.strip() for v in raw_val.split(",") if v.strip()]
            if values:
                attr_name = ATTRIBUTE_MAP[q_key]
                match[f"attributes.{attr_name}"] = {"$in": values}
        
        pipeline = [
            {"$match": match},
            {"$lookup": {
                "from":         "product_category",
                "localField":   "category_id",
                "foreignField": "_id",
                "as":           "product_category_ins"}},
            {"$unwind": "$product_category_ins"},
        ]
        
        if search_query and search_query.strip():
            s = search_query.strip()
            pipeline.append({"$match": {
                "$or": [
                    {"brand_name":   {"$regex": s, "$options": "i"}},
                    {"product_name": {"$regex": s, "$options": "i"}},
                    {"sku_number_product_code_item_number": {
                        "$regex": s, "$options": "i"}},
                ]}})
        
        pipeline.append({
            "$project": {
                "_id": 0,
                "id":          {"$toString": "$_id"},
                "shopify_id":  "$_id",
                "handle":      {"$ifNull": ["$handle", ""]},
                "variant_id":  {"$ifNull": [{"$first": "$variants.id"}, None]},
                "image":       {"$ifNull": ["$image_url", "https://via.placeholder.com/300"]},
                "title":       {"$ifNull": ["$title", "Untitled"]},
                "sku":         {"$ifNull": [{"$first": "$variants.sku"}, "N/A"]},
                "category":    {"$ifNull": ["$product_category_ins.name", "Uncategorized"]},
                "breadcrumb":  {"$ifNull": ["$product_category_ins.breadcrumb", ""]},
                "price":       {"$ifNull": [{"$first": "$variants.price"}, 0]},
                "description": {"$ifNull": ["$body_html", ""]},
                "tags":        {"$ifNull": ["$tags", []]},
                "brand":       {"$ifNull": ["$brand", ""]},
                "vendor":      {"$ifNull": ["$vendor", ""]},
            }})
        
        product_list = list(ShopifyProduct.objects.aggregate(*pipeline))
        
        for p in product_list:
            p["price"] = f"${p.get('price', 0)} USD"
            
            
            if p.get("handle"):
                handle = p["handle"]
                
                handle = handle.replace('"', '').replace("'", '')
                handle = handle.lower().replace(' ', '-').replace('/', '-')
                
                import re
                handle = re.sub(r'[^a-z0-9-]', '', handle)
                
                handle = re.sub(r'-+', '-', handle)
                
                handle = handle.strip('-')
                p["handle"] = handle
            
            if not p.get('image'):
                p['image'] = 'https://via.placeholder.com/300'
        
        print(f' Found {len(product_list)} products')
        if product_list:
            print(f' Sample product: {product_list[0]}')
        
        return {"products": product_list}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category_id}", response_model=dict)
async def get_single_category(
    category_id: str,
    x_api_key: str = Header(..., alias="X-API-KEY")
):
  
    verify_api_key(x_api_key)
    try:
        cat = product_category.objects.get(id=ObjectId(category_id))
        return {
            "id": str(cat.id),
            "name": cat.name,
            "breadcrumb": getattr(cat, "breadcrumb", ""),
        }
    except product_category.DoesNotExist:
        raise HTTPException(status_code=404,
                            detail=f"Category {category_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/category_filters')
async def category_filters_view(category_id: str = Query(...),  x_api_key: str = Header(..., alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        category_obj = product_category.objects.get(id=ObjectId(category_id))
        category_name = category_obj.name
        filters_cursor = filter.objects(category_id=ObjectId(category_id))
        filters_list = []
        for ins in filters_cursor:
            f = ins.to_mongo().to_dict()
            f.pop('_id', None)
            f.pop('category_id', None)
            if f.get('config', {}).get('options', []):
                for key, value in f.items():
                    if pd.isna(value) or value == float('nan'):
                        f[key] = None
                filters_list.append(f)
        filters_list = sorted(
            filters_list, key=lambda x: x.get('name', '').lower())
        return {
            "data": {
                "category_id": category_id,
                "category_name": category_name,
                "filters": filters_list
            }
        }
    except product_category.DoesNotExist:
        raise HTTPException(
            status_code=404, detail=f"Category {category_id} not found")
    except Exception as e:
        print(f"Error fetching filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
