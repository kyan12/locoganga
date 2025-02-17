from typing import Dict, List, Optional
from ..models import Product, ProductSKU, db
from .winit_api import WinitAPI

class ProductService:
    def __init__(self, winit_api: WinitAPI):
        self.winit_api = winit_api

    def sync_products(self, warehouse_code: Optional[str] = None) -> int:
        """Sync products from Winit API to local database"""
        page = 1
        total_synced = 0
        
        while True:
            # Get products from Winit API
            result = self.winit_api.get_product_list(warehouse_code, page)
            if not result or 'SPUList' not in result:
                break

            products = result['SPUList']
            if not products:
                break

            # Process each product
            for product_data in products:
                self._sync_single_product(product_data)
                total_synced += 1

            # Check if there are more pages
            page_params = result.get('pageParams', {})
            if page >= page_params.get('totalCount', 0) / page_params.get('pageSize', 200):
                break
            page += 1

        return total_synced

    def _sync_single_product(self, product_data: Dict) -> Product:
        """Sync a single product from Winit API data"""
        # Find existing product or create new one
        product = Product.query.filter_by(spu=product_data['SPU']).first()
        if not product:
            product = Product(spu=product_data['SPU'])

        # Update product fields
        product.title = product_data['title']
        product.category_id = product_data.get('categoryID')
        product.sale_type_id = product_data.get('saleTypeIds')
        product.warehouse_code = product_data.get('warehouseCode')
        product.thumbnail = product_data.get('thumbnail')
        product.total_inventory = product_data.get('totalInventory', 0)

        # Get detailed product info for description
        try:
            detail = self.winit_api.get_product_detail(product.spu)
            if detail and 'SPUList' in detail and detail['SPUList']:
                product.description = detail['SPUList'][0].get('description', '')
        except Exception:
            # Log error but continue processing
            pass

        # Process SKUs
        if 'SKUList' in product_data:
            existing_skus = {sku.sku: sku for sku in product.skus}
            
            for sku_data in product_data['SKUList']:
                sku = existing_skus.get(sku_data['SKU'])
                if not sku:
                    sku = ProductSKU(product=product, sku=sku_data['SKU'])

                # Update SKU fields
                sku.random_sku = sku_data['randomSKU']
                sku.supply_inventory = sku_data.get('supplyInventory', 0)
                sku.supply_price = sku_data.get('supplyPrice', 0)
                sku.settle_price = sku_data.get('settlePrice', 0)
                sku.min_retail_price = sku_data.get('minRetailPrice', 0)
                sku.retail_price_code = sku_data.get('retailPriceCode')
                sku.weight = sku_data.get('weight', 0)
                sku.length = sku_data.get('length', 0)
                sku.width = sku_data.get('width', 0)
                sku.height = sku_data.get('height', 0)
                sku.specification = sku_data.get('sepcification')

                if sku not in product.skus:
                    product.skus.append(sku)

        db.session.add(product)
        db.session.commit()
        return product

    def get_product(self, spu: str) -> Optional[Product]:
        """Get a product by SPU"""
        return Product.query.filter_by(spu=spu).first()

    def get_products(self, page: int = 1, per_page: int = 20, category_id: Optional[int] = None) -> List[Product]:
        """Get paginated list of products"""
        query = Product.query
        if category_id:
            query = query.filter_by(category_id=category_id)
        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_product_by_sku(self, sku: str) -> Optional[ProductSKU]:
        """Get a product SKU"""
        return ProductSKU.query.filter_by(sku=sku).first() 