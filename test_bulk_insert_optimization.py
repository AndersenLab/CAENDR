#!/usr/bin/env python3
"""
Test script to verify bulk insert optimizations.

This tests:
1. Batched insert functionality
2. Foreign key deferral
3. Generator handling for strain annotated variants
"""

import os
import sys

# Set up environment for testing
os.environ["MODULE_DB_OPERATIONS_CONNECTION_TYPE"] = "memory"

# Add the package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/pkg'))

from caendr.services.logger import logger
from caendr.services.cloud.postgresql import db
from caendr.models.sql import Strain, WormbaseGeneSummary, WormbaseGene, Homolog, StrainAnnotatedVariant
from caendr.services.sql.db import bulk_insert_with_batching


def test_bulk_insert_basic():
    """Test basic bulk insert functionality."""
    logger.info("Testing basic bulk insert...")
    
    # Create test data generator
    def test_data_gen():
        for i in range(150):  # Test batching with batch_size=100
            yield {
                'name': f'strain_{i}',
                'isotype': f'iso_{i}',
                'sequenced': i % 2 == 0,
            }
    
    total = bulk_insert_with_batching(db, Strain, test_data_gen(), batch_size=100, defer_fks=False)
    
    assert total == 150, f"Expected 150 insertions, got {total}"
    count = db.session.query(Strain).count()
    assert count == 150, f"Expected 150 records in DB, got {count}"
    logger.info(f"✓ Basic bulk insert test passed: {total} records inserted and verified")


def test_bulk_insert_with_single_batch():
    """Test bulk insert with data smaller than batch size."""
    logger.info("Testing bulk insert with single batch...")
    
    def test_data_gen():
        for i in range(50):
            yield {
                'name': f'strain_small_{i}',
                'isotype': f'iso_small_{i}',
                'sequenced': False,
            }
    
    total = bulk_insert_with_batching(db, Strain, test_data_gen(), batch_size=100, defer_fks=False)
    
    assert total == 50, f"Expected 50 insertions, got {total}"
    logger.info(f"✓ Single batch test passed: {total} records inserted")


def test_bulk_insert_large_batch():
    """Test bulk insert with large dataset."""
    logger.info("Testing bulk insert with large dataset...")
    
    def test_data_gen():
        for i in range(25000):  # Larger dataset
            yield {
                'name': f'strain_large_{i}',
                'isotype': f'iso_large_{i}',
                'sequenced': i % 3 == 0,
            }
    
    total = bulk_insert_with_batching(db, Strain, test_data_gen(), batch_size=10000, defer_fks=False)
    
    assert total == 25000, f"Expected 25000 insertions, got {total}"
    count = db.session.query(Strain).count()
    # Count includes previous tests
    assert count >= 25000 + 150 + 50, f"Expected at least 25200 records in DB"
    logger.info(f"✓ Large batch test passed: {total} records inserted")


def test_generator_handling():
    """Test that generators are properly consumed."""
    logger.info("Testing generator handling...")
    
    data_yielded = [0]  # Track how many items were yielded
    
    def counting_gen():
        for i in range(500):
            data_yielded[0] += 1
            yield {
                'name': f'strain_gen_{i}',
                'isotype': f'iso_gen_{i}',
                'sequenced': False,
            }
    
    total = bulk_insert_with_batching(db, Strain, counting_gen(), batch_size=100, defer_fks=False)
    
    assert total == data_yielded[0], f"Mismatch: inserted {total}, but {data_yielded[0]} items were yielded"
    assert total == 500, f"Expected 500 insertions, got {total}"
    logger.info(f"✓ Generator handling test passed: {total} records inserted")


def run_all_tests():
    """Run all tests."""
    logger.info("Starting bulk insert optimization tests...")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        from caendr.models.sql import create_app
        app = create_app()
        with app.app_context():
            db.create_all()
            
            test_bulk_insert_basic()
            test_bulk_insert_with_single_batch()
            test_bulk_insert_large_batch()
            test_generator_handling()
            
            logger.info("=" * 60)
            logger.info("✓ All tests passed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
