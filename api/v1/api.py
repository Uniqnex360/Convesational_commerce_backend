from fastapi import APIRouter
from .endpoints import chat, questions, config,productfinder,mock_orders
api_router=APIRouter()
api_router.include_router(chat.router,tags=['chat'])
api_router.include_router(questions.router,tags=['questions'])
api_router.include_router(mock_orders.router,tags=['mock'])
api_router.include_router(config.router,tags=['config'])
api_router.include_router(productfinder.router,tags=['productfinder'])