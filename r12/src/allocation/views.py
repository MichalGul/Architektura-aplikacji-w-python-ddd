from allocation.service_layer import unit_of_work
from  allocation.adapters import redis_eventpublisher
from  allocation.domain import model

# def allocations(orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
#     with uow:
#         results = list(uow.session.execute(
#             'SELECT sku, batchref FROM allocations_view WHERE orderid = :orderid',
#             dict(orderid=orderid)
#         ))
#     return [dict(r) for r in results]


def single_allocation(orderid: str, sku: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        result = uow.session.execute(
            'SELECT batchref FROM allocations_view WHERE orderid = :orderid AND sku = :sku',
            dict(orderid=orderid, sku=sku)
        ).fetchone()
        if result:
            return {'batchref': result[0]}
        else:
            return None

def single_allocation_orm(orderid: str, sku: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        single_line = uow.session.query(
            model.Batch).join(model.OrderLine, model.Batch._allocations).filter(model.OrderLine.orderid == orderid,
                                                                                model.Batch.sku == sku).one()
        if single_line:
            return {'batchref': single_line.reference}
        else:
            return None


# redis allocations view
# def allocations(orderid):
#     batches = redis_eventpublisher.get_readmodel(orderid)
#     return [
#         {'batchref': b.decode(), 'sku': s.decode()} for s, b in batches.items()
#     ]


def single_allocation_redis(orderid, sku):
    batchref = redis_eventpublisher.get_single_readmodel(orderid, sku)
    if batchref:
        return {'batchref': batchref.decode()}
    else:
        return None