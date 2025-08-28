"""
Test for scheduling execution creating work orders in database
"""
import pytest
from datetime import datetime
from unittest.mock import Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.scheduling import execute_scheduling_algorithm, SchedulingRequest


@pytest.mark.asyncio
async def test_scheduling_execution_creates_work_orders():
    """Test that scheduling execution actually creates work orders in database"""
    # Mock database session
    db_mock = Mock(spec=AsyncSession)
    db_mock.commit = Mock()
    db_mock.add = Mock()
    db_mock.execute = Mock()
    db_mock.refresh = Mock()
    
    # Create scheduling request
    request = SchedulingRequest(
        import_batch_id="TEST_BATCH_001",
        algorithm_config={"merge_enabled": True}
    )
    
    # Execute scheduling - this should create work orders in database
    result = await execute_scheduling_algorithm(request, db_mock, None)
    
    # Check if any PackingOrder or FeedingOrder instances were added to database
    work_order_adds = []
    for call in db_mock.add.call_args_list:
        if call and len(call[0]) > 0:
            obj = call[0][0]
            if hasattr(obj, '__class__') and ('Order' in obj.__class__.__name__):
                work_order_adds.append(obj)
    
    # This should fail because current implementation doesn't create work orders
    assert len(work_order_adds) > 0, "Expected work orders to be created in database, but none were found"


if __name__ == "__main__":
    pytest.main([__file__])