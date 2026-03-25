from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_auth_service
from core.dependencies import RoleChecker, get_user_by_email
from database.models.user import UserGroupEnum, UserModel
from database.session_postgresql import get_db
from schemas.order import OrderListSchema, OrderDetailSchema
from schemas.payments import (
    PaymentReadSchema,
    RefundRequestSchema,
    PaymentAdminListSchema,
    PaymentAdminReadSchema,
    AdminPaymentFilterSchema
)
from schemas.user import ChangeUserGroupSchema, MessageSchema, UserBase
from services.auth_user import AuthServices
from services.order import OrderService
from services.payments import PaymentService

router = APIRouter(prefix="/admin", tags=["admin"])

allow_admin_only = RoleChecker([UserGroupEnum.ADMIN])

@router.patch(
    "/change-user-status",
    response_model=MessageSchema,
    summary="Update User Role",
    description="Modifies the permission level of a user (e.g., upgrading a "
                "User to Moderator or Admin)."
)
async def change_user_status(
        payload: ChangeUserGroupSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only),
        auth_service: AuthServices = Depends(get_auth_service)
):
    user_db = await get_user_by_email(payload.email, db=db)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    user = await auth_service.change_user_group(
        user=user_db, user_group=payload.user_group, db=db
    )
    await db.commit()
    await db.refresh(user)

    return MessageSchema(
        message=f"User with ID {user.id} (email: {user.email}) has been moved "
                f"into the {payload.user_group.name} group."
    )


@router.patch(
    "/activate-user",
    response_model=MessageSchema,
    summary="Manual Account Activation",
    description="Forcefully activates a user account, bypassing the standard "
                "email verification process."
)
async def admin_activate_user(
        payload: UserBase,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only),
        auth_service: AuthServices = Depends(get_auth_service)
):
    user_db = await get_user_by_email(email=payload.email, db=db)

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    if user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active."
        )

    await auth_service._perform_user_activation(user_db, db)
    await db.commit()

    return MessageSchema(message=f"User {user_db.email} activated by admin.")


@router.get(
    "/orders",
    response_model=OrderListSchema,
    summary="Global Order History",
    description="Retrieves a paginated list of all orders placed across the "
                "entire platform."
)
async def get_orders(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only),
        page: int = 1,
        per_page: int = 20
):
    return await OrderService.get_order_history(
        request=request,
        db=db,
        user=current_user,
        page=page,
        per_page=per_page
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderDetailSchema,
    summary="Fetch Detailed Order Info",
    description="Returns full item breakdowns and status history for a "
                "specific order ID."
)
async def get_order_detail(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only)
):
    return await OrderService.get_order_details(order_id=order_id, db=db)


@router.get(
    "/get_payments",
    response_model=PaymentAdminListSchema,
    summary="Filterable Payment Log",
    description="A comprehensive audit log of all Stripe transactions. "
                "Supports sorting and complex filtering."
)
async def get_payments_list(
        request: Request,
        filter_params: AdminPaymentFilterSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only),
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "newest"
):
    filters = filter_params.model_dump()
    return await PaymentService.get_payments(
            request=request,
            db=db,
            filter_params=filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by
    )


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentAdminReadSchema,
    summary="Detailed Payment Audit",
    description="Provides an in-depth view of a specific transaction, "
                "including external Stripe session IDs."
)
async def get_payment(
        payment_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only)
):
    return await PaymentService.admin_payment_detail(
        payment_id=payment_id, db=db
    )


@router.post(
    "/refund-payment",
    response_model=PaymentReadSchema,
    summary="Process Transaction Refund",
    description="Initiates a refund via the Stripe API for a successfully "
                "processed payment."
)
async def refund(
        payload: RefundRequestSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only)
):
    return await PaymentService.refund(payment_id=payload.payment_id, db=db)
