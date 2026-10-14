from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=PaginatedResponse[CategoryResponse])
def list_categories(
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List indicator categories with pagination."""
    items, total = CategoryService.list(
        db, skip=pagination.offset, limit=pagination.page_size
    )
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
):
    """Create a new indicator category."""
    existing = CategoryService.get_by_slug(db, category_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category_in.slug}' already exists",
        )
    return CategoryService.create(db, category_in)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    """Get category by ID."""
    category = CategoryService.get_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found",
        )
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing category."""
    category = CategoryService.get_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found",
        )
    return CategoryService.update(db, category, category_in)
