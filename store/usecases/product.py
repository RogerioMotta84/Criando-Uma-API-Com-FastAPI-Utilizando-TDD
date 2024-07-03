from typing import List, Optional
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
from store.db.mongo import db_client
from store.models.product import ProductModel
from store.schemas.product import ProductIn, ProductOut, ProductUpdate, ProductUpdateOut
from store.core.exceptions import InsertionException, NotFoundException
from pymongo.errors import PyMongoError
from datetime import datetime, timezone

class ProductUsecase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient = db_client.get()
        self.database: AsyncIOMotorDatabase = self.client.get_database()
        self.collection = self.database.get_collection("products")

    async def query(self, price_min: Optional[float] = None, price_max: Optional[float] = None) -> List[ProductOut]:
        filters = {}
        if price_min:
            filters["price"] = {"$gt": price_min}  # Greater than
        if price_max:
            filters["price"]["$lt"] = price_max  # Less than

        products = await self.collection.find(filters).to_list(length=None)
        return [ProductOut(**product) for product in products]
    
    async def create(self, body: ProductIn) -> ProductOut:
        try:
            new_product = ProductModel(**body.model_dump())
            result = await self.collection.insert_one(new_product.model_dump())
            if not result.acknowledged:
                raise InsertionException(message="Falha ao inserir o produto.")
            return ProductOut(**new_product.model_dump())
        except PyMongoError as exc:
            raise InsertionException(message=str(exc))

    async def get(self, id: UUID) -> ProductOut:
        result = await self.collection.find_one({"id": id})

        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        return ProductOut(**result)

    async def update(self, id: UUID, body: ProductUpdate) -> ProductUpdateOut:
        body_dict = body.model_dump(exclude_none=True)
        body_dict["updated_at"] = datetime.now(timezone.utc)  # Atualizar o campo updated_at com a data atual
        result = await self.collection.find_one_and_update(
            filter={"id": id},
            update={"$set": body_dict},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if not result:
            raise NotFoundException(message=f"Produto não encontrado com o filtro: {id}")

        return ProductUpdateOut(**result)

    async def delete(self, id: UUID) -> bool:
        product = await self.collection.find_one({"id": id})
        if not product:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        result = await self.collection.delete_one({"id": id})

        return True if result.deleted_count > 0 else False

product_usecase = ProductUsecase()
