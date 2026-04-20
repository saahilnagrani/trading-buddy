import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.account import Account
from app.models.basket import Basket, BasketItem
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.basket import (
    BasketCreate,
    BasketUpdate,
    BasketResponse,
    BasketItemCreate,
    BasketItemResponse,
    BasketExecuteRequest,
)
from app.services.basket_executor import execute_basket

router = APIRouter()


@router.get("", response_model=list[BasketResponse])
async def list_baskets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Basket)
        .options(selectinload(Basket.items))
        .where(Basket.is_active.is_(True))
        .order_by(Basket.name)
    )
    return result.scalars().all()


@router.get("/{basket_id}", response_model=BasketResponse)
async def get_basket(basket_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Basket).options(selectinload(Basket.items)).where(Basket.id == basket_id)
    )
    basket = result.scalar_one_or_none()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    return basket


@router.post("", response_model=BasketResponse, status_code=201)
async def create_basket(data: BasketCreate, db: AsyncSession = Depends(get_db)):
    basket = Basket(name=data.name, description=data.description)
    for item_data in data.items:
        basket.items.append(BasketItem(**item_data.model_dump()))
    db.add(basket)
    await db.commit()
    await db.refresh(basket, attribute_names=["items"])
    return basket


@router.put("/{basket_id}", response_model=BasketResponse)
async def update_basket(basket_id: uuid.UUID, data: BasketUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Basket).options(selectinload(Basket.items)).where(Basket.id == basket_id)
    )
    basket = result.scalar_one_or_none()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(basket, key, value)
    await db.commit()
    await db.refresh(basket, attribute_names=["items"])
    return basket


@router.delete("/{basket_id}", status_code=204)
async def delete_basket(basket_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Basket).where(Basket.id == basket_id))
    basket = result.scalar_one_or_none()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    basket.is_active = False
    await db.commit()


@router.post("/{basket_id}/items", response_model=BasketItemResponse, status_code=201)
async def add_basket_item(basket_id: uuid.UUID, data: BasketItemCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Basket).where(Basket.id == basket_id))
    basket = result.scalar_one_or_none()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")

    item = BasketItem(basket_id=basket_id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{basket_id}/items/{item_id}", status_code=204)
async def remove_basket_item(basket_id: uuid.UUID, item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BasketItem).where(BasketItem.id == item_id, BasketItem.basket_id == basket_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()


@router.post("/{basket_id}/execute")
async def execute_basket_endpoint(
    basket_id: uuid.UUID,
    req: BasketExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.account_ids == ["all"]:
        result = await db.execute(
            select(Account.id).where(Account.is_active.is_(True), Account.user_id == current_user.id)
        )
        account_ids = [row[0] for row in result.all()]
    else:
        requested_ids = [uuid.UUID(aid) for aid in req.account_ids]
        result = await db.execute(
            select(Account.id).where(
                Account.id.in_(requested_ids),
                Account.user_id == current_user.id,
                Account.is_active.is_(True),
            )
        )
        account_ids = [row[0] for row in result.all()]
        if len(account_ids) != len(requested_ids):
            raise HTTPException(status_code=403, detail="One or more accounts not found or not accessible")

    try:
        result = await execute_basket(
            basket_id=basket_id,
            account_ids=account_ids,
            mode=req.mode,
            uniform_lots=req.uniform_lots,
            custom_allocations=req.custom_allocations,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
