from pydantic import BaseModel
from mongoengine import fields, Document
from datetime import datetime
from typing import Optional, List
from mongoengine import connect
from typing import Dict, Any, Optional
from mongoengine import ReferenceField
import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_NAME = os.getenv("MONGODB_NAME")
try:
    connect(
        db=MONGODB_NAME,
        host=MONGODB_HOST,
        alias="default"
    )
    print(" MongoDB connected!")
except Exception as e:
    print(f" MongoDB connection failed: {e}")
    raise
class ProductRequest(BaseModel):
    product_id:int
class ProductResponse(BaseModel):
    id:int
    title:int
    body_html:str
class ChatRequest(BaseModel):
    message: str
    product_context: Dict[str, Any]
    product_id: Optional[str] = None
    session_id: Optional[str] = None
class ChatResponse(BaseModel):
    response: str
    session_id: str
    product_id: Optional[str] = None
class QuestionResponse(BaseModel):
    id:str
    question:str
class product_category(Document):
    name = fields.StringField(required=True)
    level = fields.IntField(default=0)
    parent_category_id = fields.ReferenceField('self', null=True)
    child_categories = fields.ListField(fields.ReferenceField('self'))
    breadcrumb = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    description = fields.StringField()
    code = fields.StringField()
    end_level = fields.BooleanField(default=False)
    industry_id_str = fields.StringField()
class ConfigResponse(BaseModel):
    theme:dict
    position:str
    greeting_message:str
    placeholder:str
class brand(Document):
    name = fields.StringField(required=True)
    code = fields.StringField()
    product_sub_category_id_str = fields.StringField()
    logo = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    industry_id_str = fields.StringField()
class fit_rule(Document):
    category = fields.StringField(required=True)
    requirement_attribute = fields.StringField(
        required=True
    )
    product_attribute = fields.StringField(
        required=True
    )
    relation = fields.StringField(
        required=True,
        choices=(
            "range_from_input",
            "equals",
            "contains",
        ),
    )
    min_offset = fields.FloatField()
    max_offset = fields.FloatField()
    required = fields.BooleanField(default=True)
    explanation_template = fields.StringField()
    meta = {
        "indexes": [
            {
                "fields": [
                    "category",
                    "requirement_attribute",
                ]
            }
        ]
    }
class vendor(Document):
    name = fields.StringField(required=True)
    manufacture_unit_id_str = fields.StringField()
class manufacture_unit(Document):
    name = fields.StringField()
    description = fields.StringField()
    location = fields.StringField()
    logo = fields.StringField()
    industry = fields.StringField()
    is_active = fields.BooleanField(default=True)
class product(Document):
    sku_number_product_code_item_number = fields.StringField(default="")
    model = fields.StringField()
    mpn = fields.StringField(default="")
    upc_ean = fields.StringField()
    breadcrumb = fields.StringField()
    brand_name = fields.StringField(default="")
    product_name = fields.StringField(default="")
    long_description = fields.StringField(default="")
    short_description = fields.StringField()
    features = fields.ListField(fields.StringField())
    images = fields.ListField(fields.StringField())
    attributes = fields.DictField(default={})
    tags = fields.ListField(fields.StringField())
    msrp = fields.FloatField(default=0.0)
    currency = fields.StringField(default="")
    was_price = fields.FloatField(default=0.0)
    list_price = fields.FloatField(default=0.0)
    discount = fields.FloatField(default=0.0)
    quantity_prices = fields.FloatField(default=0.0)
    quantity = fields.FloatField()
    availability = fields.BooleanField(default=True)
    return_applicable = fields.BooleanField(default=False)
    return_in_days = fields.StringField()
    visible = fields.BooleanField(default=True)
    brand_id = fields.ReferenceField(brand)
    vendor_id = fields.ReferenceField(vendor)
    category_id = fields.ReferenceField(product_category)
    quantity_price = fields.DictField(
        default={"1-100": 1, "100-1000": 2, "1000-10000": 3})
    rating_count = fields.IntField(default=0)
    rating_average = fields.FloatField(default=0.0)
    from_the_manufacture = fields.StringField()
    industry_id_str = fields.StringField()
    tax = fields.FloatField(default=0.0)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    old_names = fields.ListField(fields.StringField())
    old_description = fields.ListField(fields.StringField())
    old_features = fields.ListField(fields.ListField(fields.StringField()))
    ai_generated_title = fields.ListField(fields.DictField())
    ai_generated_description = fields.ListField(fields.DictField())
    ai_generated_features = fields.ListField(fields.DictField())
from mongoengine import Document, IntField, StringField, ListField, DictField, DateTimeField, FloatField
class ShopifyProduct(Document):
    _id = IntField(primary_key=True)
    title = StringField(required=True)
    vendor = StringField()
    product_type = StringField()
    handle = StringField()
    tags = ListField(StringField())
    status = StringField(default="active")
    body_html = StringField()
    image_url = StringField()
    variants = ListField(DictField())
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    shopify_updated_at = DateTimeField()
    last_synced = DateTimeField(default=datetime.utcnow)
    category_id = ReferenceField('product_category', null=True)
    # ===== NEW FIELDS FOR EXCEL DATA =====
    # Category Hierarchy (from Excel columns)
    category_1 = StringField()
    category_2 = StringField()
    category_3 = StringField()
    category_4 = StringField()
    category_5 = StringField()
    end_level = StringField()
    # Basic Product Info
    sku = StringField()  # Main SKU field for easy access
    brand = StringField()  # Duplicate of vendor for clarity
    # TV Specific Attributes
    tv_type = StringField()
    display_type = StringField()
    screen_size = StringField()
    os = StringField()
    resolution = StringField()
    refresh_rate = StringField()
    smart_features = StringField()
    # Washing Machine Specific Attributes
    load_type = StringField()
    capacity = StringField()
    laundry_features = StringField()
    energy_rating = StringField()
    # Connectivity (for both TVs and other smart appliances)
    connectivity = StringField()
    # Additional metadata
    attributes = DictField(default={})  # Store any extra attributes as key-value pairs
    meta = {
        "collection": "shopify_products",
        "indexes": [
            "sku",
            "vendor",
            "product_type",
            "category_1",
            "category_id"
        ]
    }
    def to_dict(self):
        return {
            "_id": self._id,
            "title": self.title,
            "vendor": self.vendor,
            "product_type": self.product_type,
            "handle": self.handle,
            "tags": self.tags,
            "status": self.status,
            "body_html": self.body_html,
            "image_url": self.image_url,
            "variants": self.variants,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shopify_updated_at": self.shopify_updated_at,
            "last_synced": self.last_synced,
            "category_id": str(self.category_id.id) if self.category_id else None,
            # New fields in to_dict
            "category_1": self.category_1,
            "category_2": self.category_2,
            "category_3": self.category_3,
            "category_4": self.category_4,
            "category_5": self.category_5,
            "end_level": self.end_level,
            "sku": self.sku,
            "brand": self.brand,
            "tv_type": self.tv_type,
            "display_type": self.display_type,
            "screen_size": self.screen_size,
            "os": self.os,
            "resolution": self.resolution,
            "refresh_rate": self.refresh_rate,
            "smart_features": self.smart_features,
            "load_type": self.load_type,
            "capacity": self.capacity,
            "laundry_features": self.laundry_features,
            "energy_rating": self.energy_rating,
            "connectivity": self.connectivity,
            "attributes": self.attributes
        }
class product_questions(Document):
    question = fields.StringField()
    answer = fields.StringField()
    question_type = fields.StringField()
    product_id = fields.ReferenceField(product)
    category_id = fields.ReferenceField(product_category)
class filter(Document):
    category_id = fields.ReferenceField(product_category, required=True)
    name = fields.StringField(required=True)
    filter_type = fields.StringField(
        required=True,
        choices=('select', 'range', 'multi-select', 'boolean')
    )
    display_order = fields.IntField(default=0)
    config = fields.DictField(default={})
def save_questions_from_excel(file_path):
    df=pd.read_excel(file_path)
    for _,row in df.iterrows():
        category_names=[
            str(row.get(f"C-{i}", "")).strip()
            for i in range(1,6)
            if pd.notna(row.get(f"C-{i}", "")) and str(row.get(f"C-{i}", "")).strip()
        ]
        category_name=str(row.get('Product Type',"")).strip()
        if not category_name:
            category_name='Unauthorized'
        category_obj=product_category.objects(name=category_name).first()
        if not category_obj:
            category_obj=product_category(
                name=category_name,
                breadcrumb=" -> ".join(category_names),
                end_level=True
            ).save()
        question_txt=str(row.get("Questions","")).strip()
        answer_txt=str(row.get("Answer","")).strip()
        question_type=str(row.get('Question Type',"")).strip()
        if not question_txt or not answer_txt:
            continue
        exisiting=product_questions.objects(
            question=question_txt,
            category_id=category_obj
        ).first()
        if exisiting:
            print(f"Skipping duplicate questions:{question_txt}")
            continue
        product_questions(
            question=question_txt,
            answer=answer_txt,
            question_type=question_type,
            category_id=category_obj
        ).save()
        print(f"Saved question :{question_txt}")
# save_questions_from_excel("/home/lexicon/Downloads/Shopify - 27 Category - FAQ's - updated-1.xlsx")
# def save_shopify_products_from_excel(file_path):
#     df = pd.read_excel(file_path)
#     saved_count = 0
#     updated_count = 0
#     skipped_count = 0
#     for _, row in df.iterrows():
#         try:
#             # Get basic product info
#             title = str(row.get("Title", "")).strip()
#             sku = str(row.get("SKU", "")).strip()
#             brand = str(row.get("Brand", "")).strip()
#             if not title or not sku:
#                 print(f"⚠ Skipping row with missing Title or SKU")
#                 skipped_count += 1
#                 continue
#             # Build category hierarchy
#             category_1 = str(row.get("Category-1", "")).strip()
#             category_2 = str(row.get("Category-2", "")).strip()
#             category_3 = str(row.get("Category-3", "")).strip()
#             category_4 = str(row.get("Category-4", "")).strip()
#             category_5 = str(row.get("Category-5", "")).strip()
#             end_level = str(row.get("End Level", "")).strip()
#             categories = [c for c in [category_1, category_2, category_3, category_4, category_5] if c]
#             # Get or create the product_type from the most specific category
#             product_type = categories[-1] if categories else "Uncategorized"
#             # Find or create category
#             category_obj = None
#             if product_type:
#                 category_obj = product_category.objects(name=product_type).first()
#                 if not category_obj:
#                     category_obj = product_category(
#                         name=product_type,
#                         breadcrumb=" > ".join(categories),
#                         level=len(categories),
#                         end_level=True
#                     ).save()
#             # Get all attribute fields
#             tv_type = str(row.get("TV Type", "")).strip() if pd.notna(row.get("TV Type")) else ""
#             display_type = str(row.get("Display Type", "")).strip() if pd.notna(row.get("Display Type")) else ""
#             screen_size = str(row.get("Screen Size", "")).strip() if pd.notna(row.get("Screen Size")) else ""
#             os = str(row.get("OS", "")).strip() if pd.notna(row.get("OS")) else ""
#             resolution = str(row.get("Resolution", "")).strip() if pd.notna(row.get("Resolution")) else ""
#             refresh_rate = str(row.get("Refresh rate", "")).strip() if pd.notna(row.get("Refresh rate")) else ""
#             connectivity = str(row.get("Connectivity", "")).strip() if pd.notna(row.get("Connectivity")) else ""
#             smart_features = str(row.get("Smart Features", "")).strip() if pd.notna(row.get("Smart Features")) else ""
#             load_type = str(row.get("Load Type", "")).strip() if pd.notna(row.get("Load Type")) else ""
#             capacity = str(row.get("Capacity", "")).strip() if pd.notna(row.get("Capacity")) else ""
#             laundry_features = str(row.get("Laundry Features", "")).strip() if pd.notna(row.get("Laundry Features")) else ""
#             energy_rating = str(row.get("Energy Rating", "")).strip() if pd.notna(row.get("Energy Rating")) else ""
#             # Build attributes dictionary for additional data
#             attributes = {}
#             if tv_type:
#                 attributes["TV Type"] = tv_type
#             if display_type:
#                 attributes["Display Type"] = display_type
#             if screen_size:
#                 attributes["Screen Size"] = screen_size
#             if os:
#                 attributes["Operating System"] = os
#             if resolution:
#                 attributes["Resolution"] = resolution
#             if refresh_rate:
#                 attributes["Refresh Rate"] = refresh_rate
#             if connectivity:
#                 attributes["Connectivity"] = connectivity
#             if smart_features:
#                 attributes["Smart Features"] = smart_features
#             if load_type:
#                 attributes["Load Type"] = load_type
#             if capacity:
#                 attributes["Capacity"] = capacity
#             if laundry_features:
#                 attributes["Laundry Features"] = laundry_features
#             if energy_rating:
#                 attributes["Energy Rating"] = energy_rating
#             # Build body_html from attributes
#             body_html = f"<h3>{title}</h3>"
#             if attributes:
#                 body_html += "<h4>Product Specifications</h4><ul>"
#                 for key, value in attributes.items():
#                     if value:
#                         body_html += f"<li><strong>{key}:</strong> {value}</li>"
#                 body_html += "</ul>"
#             # Build tags list
#             tags = categories.copy()
#             if brand:
#                 tags.append(brand)
#             tags.extend([k for k in attributes.keys()])
#             # Create handle (URL-friendly version of title)
#             handle = title.lower().replace(" ", "-").replace("|", "").replace("  ", "-").replace("/", "-")
#             # Build variant data
#             variant = {
#                 "sku": sku,
#                 "title": "Default",
#                 "price": "0.00",
#                 "inventory_quantity": 0,
#                 "inventory_management": "shopify",
#             }
#             # Check if product already exists by SKU
#             existing_product = ShopifyProduct.objects(sku=sku).first()
#             if existing_product:
#                 # Update existing product
#                 existing_product.title = title
#                 existing_product.vendor = brand
#                 existing_product.brand = brand
#                 existing_product.product_type = product_type
#                 existing_product.handle = handle
#                 existing_product.tags = tags
#                 existing_product.body_html = body_html
#                 existing_product.updated_at = datetime.utcnow()
#                 existing_product.last_synced = datetime.utcnow()
#                 existing_product.category_id = category_obj
#                 # Update category fields
#                 existing_product.category_1 = category_1
#                 existing_product.category_2 = category_2
#                 existing_product.category_3 = category_3
#                 existing_product.category_4 = category_4
#                 existing_product.category_5 = category_5
#                 existing_product.end_level = end_level
#                 # Update TV attributes
#                 existing_product.tv_type = tv_type
#                 existing_product.display_type = display_type
#                 existing_product.screen_size = screen_size
#                 existing_product.os = os
#                 existing_product.resolution = resolution
#                 existing_product.refresh_rate = refresh_rate
#                 existing_product.smart_features = smart_features
#                 # Update Washing Machine attributes
#                 existing_product.load_type = load_type
#                 existing_product.capacity = capacity
#                 existing_product.laundry_features = laundry_features
#                 existing_product.energy_rating = energy_rating
#                 # Update connectivity
#                 existing_product.connectivity = connectivity
#                 # Update attributes dict
#                 existing_product.attributes = attributes
#                 # Update variant
#                 existing_product.variants = [variant]
#                 existing_product.save()
#                 updated_count += 1
#                 print(f"✓ Updated: {title} (SKU: {sku})")
#             else:
#                 # Create new product - Generate new ID
#                 last_product = ShopifyProduct.objects.order_by('-_id').first()
#                 new_id = (last_product._id + 1) if last_product else 1
#                 new_product = ShopifyProduct(
#                     _id=new_id,
#                     title=title,
#                     vendor=brand,
#                     brand=brand,
#                     sku=sku,
#                     product_type=product_type,
#                     handle=handle,
#                     tags=tags,
#                     status="active",
#                     body_html=body_html,
#                     variants=[variant],
#                     created_at=datetime.utcnow(),
#                     updated_at=datetime.utcnow(),
#                     last_synced=datetime.utcnow(),
#                     category_id=category_obj,
#                     # Category fields
#                     category_1=category_1,
#                     category_2=category_2,
#                     category_3=category_3,
#                     category_4=category_4,
#                     category_5=category_5,
#                     end_level=end_level,
#                     # TV attributes
#                     tv_type=tv_type,
#                     display_type=display_type,
#                     screen_size=screen_size,
#                     os=os,
#                     resolution=resolution,
#                     refresh_rate=refresh_rate,
#                     smart_features=smart_features,
#                     # Washing Machine attributes
#                     load_type=load_type,
#                     capacity=capacity,
#                     laundry_features=laundry_features,
#                     energy_rating=energy_rating,
#                     # Connectivity
#                     connectivity=connectivity,
#                     # Attributes dict
#                     attributes=attributes
#                 )
#                 new_product.save()
#                 saved_count += 1
#                 print(f"✓ Saved: {title} (SKU: {sku})")
#         except Exception as e:
#             print(f" Error processing row: {e}")
#             skipped_count += 1
#             continue
#     print(f"\n{'='*50}")
#     print(f" Total Saved: {saved_count}")
#     print(f"🔄 Total Updated: {updated_count}")
#     print(f"⚠ Total Skipped: {skipped_count}")
#     print(f"📊 Total Processed: {saved_count + updated_count + skipped_count}")
#     print(f"{'='*50}")
#     return {
#         "saved": saved_count,
#         "updated": updated_count,
#         "skipped": skipped_count,
#         "total": saved_count + updated_count + skipped_count
#     }
# def get_shopify_product_by_sku(sku):
#     return ShopifyProduct.objects(sku=sku).first()
# def get_shopify_products_by_category(category_name):
#     category = product_category.objects(name=category_name).first()
#     if not category:
#         return []
#     products = ShopifyProduct.objects(category_id=category)
#     return list(products)
# def get_shopify_products_by_vendor(vendor_name):
#     products = ShopifyProduct.objects(vendor=vendor_name)
#     return list(products)
# def get_shopify_products_by_attribute(attribute_name, attribute_value):
#     query = {attribute_name: attribute_value}
#     products = ShopifyProduct.objects(**query)
#     return list(products)
# def delete_all_shopify_products():
#     count = ShopifyProduct.objects.count()
#     ShopifyProduct.objects.delete()
#     print(f"🗑 Deleted {count} products from shopify_products collection")
#     return count
# Example usage:
# result = save_shopify_products_from_excel("/home/lexicon/Downloads/Shopify - Appliances - Product Finder (1).xlsx")
# print(f"Import completed: {result}")
import pandas as pd
from collections import defaultdict
def save_filters_from_excel(file_path):
    """
    Reads Excel file and creates filter documents for each End Level category
    based on the attributes present in the data.
    """
    df = pd.read_excel(file_path)
    # Define attribute mappings for different categories
    # Format: {column_name: (display_name, filter_type)}
    attribute_mappings = {
        # TV Attributes
        "TV Type": ("TV Type", "multi-select"),
        "Display Type": ("Display Type", "multi-select"),
        "Screen Size": ("Screen Size", "multi-select"),
        "OS": ("Operating System", "multi-select"),
        "Resolution": ("Resolution", "multi-select"),
        "Refresh rate": ("Refresh Rate", "multi-select"),
        # Washing Machine Attributes
        "Load Type": ("Load Type", "multi-select"),
        "Capacity": ("Capacity", "multi-select"),
        "Laundry Features": ("Laundry Features", "multi-select"),
        "Energy Rating": ("Energy Rating", "multi-select"),
        # Common Attributes
        "Connectivity": ("Connectivity", "multi-select"),
        "Smart Features": ("Smart Features", "multi-select"),
        "Brand": ("Brand", "multi-select")
    }
    # Group data by End Level category
    category_data = defaultdict(lambda: defaultdict(set))
    for _, row in df.iterrows():
        end_level = str(row.get("End Level", "")).strip()
        if not end_level:
            continue
        # Collect unique values for each attribute
        for col_name, (display_name, filter_type) in attribute_mappings.items():
            value = str(row.get(col_name, "")).strip()
            if value and value.lower() not in ["", "nan", "none"]:
                category_data[end_level][col_name].add(value)
    # Statistics
    saved_count = 0
    updated_count = 0
    skipped_count = 0
    # Create filters for each category
    for category_name, attributes in category_data.items():
        # Find or create category
        category_obj = product_category.objects(name=category_name).first()
        if not category_obj:
            print(f"⚠ Category '{category_name}' not found. Creating...")
            category_obj = product_category(
                name=category_name,
                end_level=True
            ).save()
        print(f"\n📁 Processing category: {category_name}")
        # Create filters for each attribute
        display_order = 1
        for col_name, values in attributes.items():
            if col_name not in attribute_mappings:
                continue
            display_name, filter_type = attribute_mappings[col_name]
            # Convert set to sorted list
            options = sorted(list(values))
            # Build filter config
            config = {
                "options": options,
                "display_style": "checkbox" if filter_type == "multi-select" else "dropdown"
            }
            # Check if filter already exists
            existing_filter = filter.objects(
                category_id=category_obj,
                name=display_name
            ).first()
            if existing_filter:
                # Update existing filter
                existing_filter.filter_type = filter_type
                existing_filter.display_order = display_order
                existing_filter.config = config
                existing_filter.save()
                updated_count += 1
                print(f"  🔄 Updated filter: {display_name} ({len(options)} options)")
            else:
                # Create new filter
                new_filter = filter(
                    category_id=category_obj,
                    name=display_name,
                    filter_type=filter_type,
                    display_order=display_order,
                    config=config
                )
                new_filter.save()
                saved_count += 1
                print(f"  ✓ Created filter: {display_name} ({len(options)} options)")
            display_order += 1
    print(f"\n{'='*60}")
    print(f"✅ Total Filters Created: {saved_count}")
    print(f"🔄 Total Filters Updated: {updated_count}")
    print(f"⚠  Total Skipped: {skipped_count}")
    print(f"📊 Total Processed: {saved_count + updated_count}")
    print(f"{'='*60}")
    return {
        "saved": saved_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": saved_count + updated_count
    }
def get_filters_by_category(category_name):
    """
    Retrieve all filters for a specific category.
    Returns filters sorted by display_order.
    """
    category_obj = product_category.objects(name=category_name).first()
    if not category_obj:
        return []
    filters = filter.objects(category_id=category_obj).order_by('display_order')
    return list(filters)
def get_filters_by_category_id(category_id):
    """
    Retrieve all filters for a specific category by ID.
    Returns filters sorted by display_order.
    """
    category_obj = product_category.objects(id=category_id).first()
    if not category_obj:
        return []
    filters = filter.objects(category_id=category_obj).order_by('display_order')
    return list(filters)
def delete_filters_by_category(category_name):
    """
    Delete all filters for a specific category.
    """
    category_obj = product_category.objects(name=category_name).first()
    if not category_obj:
        print(f"⚠ Category '{category_name}' not found")
        return 0
    count = filter.objects(category_id=category_obj).count()
    filter.objects(category_id=category_obj).delete()
    print(f"🗑 Deleted {count} filters for category '{category_name}'")
    return count
def delete_all_filters():
    """
    Delete all filters from the database.
    """
    count = filter.objects.count()
    filter.objects.delete()
    print(f"🗑 Deleted {count} filters from database")
    return count
# result = save_filters_from_excel("/home/lexicon/Downloads/Shopify - Appliances - Product Finder (1).xlsx")
# print(f"Filter import completed: {result}")
# tv_filters = get_filters_by_category("TV")
# for f in tv_filters:
#     print(f"Filter: {f.name}, Type: {f.filter_type}, Options: {f.config.get('options', [])}")