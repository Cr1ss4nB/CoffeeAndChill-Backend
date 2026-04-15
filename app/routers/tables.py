from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.infrastructure import TableSpot, TableZone
from app.schemas.auth import UserResponse
from app.schemas.tables import TableCreate, TableResponse, TableUpdate

router = APIRouter(prefix="/tables", tags=["Tables"])


@router.get("", response_model=List[TableResponse])
def get_tables(
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    tables = session.exec(select(TableSpot).where(TableSpot.is_active == True)).all()
    return tables


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    table_data: TableCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    existing = session.exec(
        select(TableSpot).where(TableSpot.table_number == table_data.table_number)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número de mesa ya está en uso",
        )

    table_code = f"T{table_data.table_number:03d}"

    table = TableSpot(
        table_number=table_data.table_number,
        table_code=table_code,
        capacity=table_data.capacity,
        label=table_data.label,
        status="FREE",
        is_active=True,
    )
    session.add(table)
    session.commit()
    session.refresh(table)

    return table


@router.put("/{table_id}", response_model=TableResponse)
def update_table(
    table_id: int,
    table_data: TableUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    table = session.get(TableSpot, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    if table_data.table_number is not None:
        existing = session.exec(
            select(TableSpot).where(
                TableSpot.table_number == table_data.table_number,
                TableSpot.table_id != table_id,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El número de mesa ya está en uso",
            )
        table.table_number = table_data.table_number
        table.table_code = f"T{table_data.table_number:03d}"

    if table_data.capacity is not None:
        table.capacity = table_data.capacity
    if table_data.label is not None:
        table.label = table_data.label
    if table_data.status is not None:
        if table_data.status not in ["FREE", "OCCUPIED", "RESERVED", "MAINTENANCE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estado inválido",
            )
        table.status = table_data.status

    session.commit()
    session.refresh(table)

    return table


@router.delete("/{table_id}")
def delete_table(
    table_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    table = session.get(TableSpot, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    table.is_active = False
    session.commit()

    return {"message": "Mesa desactivada exitosamente"}
