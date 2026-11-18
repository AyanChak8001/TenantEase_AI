"""Owner-scoped destructive workspace operations.

The models do not define ORM delete cascades, so these operations explicitly
delete dependent rows before their parent rows inside one transaction.
"""

from sqlalchemy import delete, select

from database.models import NotificationLog, Payment, PredictionLog, Property, RentRecord, Tenant


def _ids_for_owner(session, owner_id: int):
    property_ids = [row[0] for row in session.execute(
        select(Property.id).where(Property.owner_id == owner_id)
    )]
    tenant_ids = []
    rent_ids = []
    if property_ids:
        tenant_ids = [row[0] for row in session.execute(
            select(Tenant.id).where(Tenant.property_id.in_(property_ids))
        )]
    if tenant_ids:
        rent_ids = [row[0] for row in session.execute(
            select(RentRecord.id).where(RentRecord.tenant_id.in_(tenant_ids))
        )]
    return property_ids, tenant_ids, rent_ids


def _delete_dependent_rows(session, tenant_ids: list[int], rent_ids: list[int]) -> None:
    """Delete rows in foreign-key dependency order using scoped predicates."""
    if tenant_ids or rent_ids:
        if tenant_ids:
            session.execute(delete(NotificationLog).where(NotificationLog.tenant_id.in_(tenant_ids)))
            session.execute(delete(PredictionLog).where(PredictionLog.tenant_id.in_(tenant_ids)))
        if rent_ids:
            session.execute(delete(NotificationLog).where(NotificationLog.rent_record_id.in_(rent_ids)))
            session.execute(delete(PredictionLog).where(PredictionLog.rent_record_id.in_(rent_ids)))
            session.execute(delete(Payment).where(Payment.rent_record_id.in_(rent_ids)))
            session.execute(delete(RentRecord).where(RentRecord.id.in_(rent_ids)))
    if tenant_ids:
        session.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))


def reset_owner_workspace(session, owner_id: int) -> dict[str, int]:
    """Delete one owner's operational workspace while preserving the owner row."""
    try:
        property_ids, tenant_ids, rent_ids = _ids_for_owner(session, owner_id)
        _delete_dependent_rows(session, tenant_ids, rent_ids)
        if property_ids:
            session.execute(delete(Property).where(Property.id.in_(property_ids), Property.owner_id == owner_id))
        session.flush()
        session.commit()
        return {"properties": len(property_ids), "tenants": len(tenant_ids), "rent_records": len(rent_ids)}
    except Exception:
        session.rollback()
        raise


def delete_tenant(session, tenant_id: int, owner_id: int) -> dict[str, int]:
    """Delete one tenant and dependents only if its property belongs to owner."""
    try:
        tenant = session.execute(
            select(Tenant).join(Property, Tenant.property_id == Property.id).where(
                Tenant.id == tenant_id,
                Property.owner_id == owner_id,
            )
        ).scalar_one_or_none()
        if tenant is None:
            raise ValueError("Tenant is not accessible to this owner.")
        rent_ids = [row[0] for row in session.execute(
            select(RentRecord.id).where(RentRecord.tenant_id == tenant_id)
        )]
        _delete_dependent_rows(session, [tenant_id], rent_ids)
        session.flush()
        session.commit()
        return {"tenants": 1, "rent_records": len(rent_ids)}
    except Exception:
        session.rollback()
        raise
