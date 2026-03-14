from urllib.parse import urlencode

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request


async def generate_page_link(
        request: Request,
        page_number: int,
        per_page: int
) -> str:
    params = dict(request.query_params)
    params["page"] = page_number
    params["per_page"] = per_page

    return f"{request.url.path}?{urlencode(params)}"


async def pagination_helper(
        request: Request,
        page: int,
        per_page: int,
        db: AsyncSession,
        stmt: Select,
) -> dict:
    offset = (page - 1) * per_page
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_items = (await db.execute(count_stmt)).scalar() or 0
    total_pages = (total_items + per_page - 1) // per_page

    prev_page = await generate_page_link(
        request, page - 1, per_page
    ) if page > 1 else None
    next_page = await generate_page_link(
        request, page + 1, per_page
    ) if page < total_pages else None

    items = await db.execute(stmt.offset(offset).limit(per_page))

    return {
        "items": items.scalars().all(),
        "total_pages": total_pages,
        "total_items": total_items,
        "prev_page": prev_page,
        "next_page": next_page,
    }
