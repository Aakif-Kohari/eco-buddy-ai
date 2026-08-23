# tests/test_transaction_rollback.py
"""
Database transaction rollback tests.
Ensures that transactions are properly rolled back on errors and that
database state remains consistent.
"""

import pytest
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime

# Define models
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    accounts = relationship("Account", back_populates="user")

class Account(Base):
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_balance_positive'),
    )
    
    user = relationship("User", back_populates="accounts")
    transactions_from = relationship("Transaction", foreign_keys="Transaction.from_account", back_populates="from_account_rel")
    transactions_to = relationship("Transaction", foreign_keys="Transaction.to_account", back_populates="to_account_rel")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    from_account = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    to_account = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    from_account_rel = relationship("Account", foreign_keys=[from_account], back_populates="transactions_from")
    to_account_rel = relationship("Account", foreign_keys=[to_account], back_populates="transactions_to")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Use an in-memory SQLite database for testing
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(test_engine)
    
    TestingSession = sessionmaker(bind=test_engine)
    session = TestingSession()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(test_engine)


@pytest.fixture
def sample_data(db_session):
    """Create sample data for testing."""
    user1 = User(id=1, name="Alice", email="alice@example.com")
    user2 = User(id=2, name="Bob", email="bob@example.com")
    
    account1 = Account(id=1, user_id=1, balance=1000.00)
    account2 = Account(id=2, user_id=2, balance=500.00)
    
    db_session.add_all([user1, user2, account1, account2])
    db_session.commit()
    
    return {"user1": user1, "user2": user2, "account1": account1, "account2": account2}


class TestTransactionRollback:
    """Test suite for transaction rollback behavior."""

    def test_successful_transaction_commit(self, db_session, sample_data):
        """Test that a successful transaction commits correctly."""
        account1 = sample_data["account1"]
        account2 = sample_data["account2"]
        
        # Perform a valid transaction
        amount = 100.00
        account1.balance -= amount
        account2.balance += amount
        
        # Add transaction record
        transaction = Transaction(
            from_account=account1.id,
            to_account=account2.id,
            amount=amount,
            status="completed"
        )
        db_session.add(transaction)
        
        # Commit should succeed
        db_session.commit()
        
        # Verify balances were updated
        updated_account1 = db_session.query(Account).filter_by(id=account1.id).first()
        updated_account2 = db_session.query(Account).filter_by(id=account2.id).first()
        
        assert updated_account1.balance == 900.00
        assert updated_account2.balance == 600.00
        
        # Verify transaction record exists
        tx = db_session.query(Transaction).filter_by(from_account=account1.id).first()
        assert tx is not None
        assert tx.amount == amount
        assert tx.status == "completed"

    def test_rollback_on_integrity_error(self, db_session, sample_data):
        """Test that transaction is rolled back on integrity error."""
        account1 = sample_data["account1"]
        account2 = sample_data["account2"]
        
        # Get initial balances
        initial_balance1 = account1.balance
        initial_balance2 = account2.balance
        
        # Attempt to create a transaction that violates integrity
        try:
            # Invalid transaction (negative balance not allowed)
            account1.balance = -100.00  # This would violate a CHECK constraint
            account2.balance += 200.00
            
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify balances remained unchanged (rollback worked)
        refreshed_account1 = db_session.query(Account).filter_by(id=account1.id).first()
        refreshed_account2 = db_session.query(Account).filter_by(id=account2.id).first()
        
        assert refreshed_account1.balance == initial_balance1
        assert refreshed_account2.balance == initial_balance2

    def test_rollback_on_duplicate_key(self, db_session, sample_data):
        """Test rollback when inserting duplicate primary key."""
        account1 = sample_data["account1"]
        initial_balance = account1.balance
        
        # Try to insert an account with duplicate ID
        try:
            duplicate_account = Account(id=account1.id, user_id=999, balance=1000.00)
            db_session.add(duplicate_account)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify original account wasn't affected
        refreshed_account = db_session.query(Account).filter_by(id=account1.id).first()
        assert refreshed_account is not None
        assert refreshed_account.balance == initial_balance

    def test_rollback_on_constraint_violation(self, db_session, sample_data):
        """Test rollback when a foreign key constraint is violated."""
        initial_count = db_session.query(User).count()
        
        # Try to create an account with non-existent user_id
        try:
            invalid_account = Account(id=99, user_id=9999, balance=1000.00)
            db_session.add(invalid_account)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify no new account was created
        assert db_session.query(Account).filter_by(id=99).first() is None
        assert db_session.query(User).count() == initial_count

    def test_nested_transaction_rollback(self, db_session, sample_data):
        """Test rollback in nested transaction scenarios."""
        account1 = sample_data["account1"]
        account2 = sample_data["account2"]
        
        initial_balance1 = account1.balance
        initial_balance2 = account2.balance
        
        try:
            # Outer transaction
            account1.balance -= 50.00
            
            try:
                # Inner transaction that will fail
                account2.balance -= 200.00  # Insufficient balance
                
                # This commit will fail, causing inner rollback
                db_session.commit()
            except SQLAlchemyError:
                # Rollback inner transaction
                db_session.rollback()
                # Re-raise to trigger outer rollback
                raise
            
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
        
        # Both accounts should be unchanged
        refreshed_account1 = db_session.query(Account).filter_by(id=account1.id).first()
        refreshed_account2 = db_session.query(Account).filter_by(id=account2.id).first()
        
        assert refreshed_account1.balance == initial_balance1
        assert refreshed_account2.balance == initial_balance2

    def test_rollback_maintains_database_consistency(self, db_session, sample_data):
        """Test that rollback maintains ACID consistency."""
        account1 = sample_data["account1"]
        account2 = sample_data["account2"]
        
        initial_balance1 = account1.balance
        initial_balance2 = account2.balance
        
        # Start a transaction with multiple operations
        account1.balance -= 50.00
        account2.balance += 50.00
        
        # Add some audit records
        db_session.add(Transaction(
            from_account=account1.id,
            to_account=account2.id,
            amount=50.00,
            status="pending"
        ))
        
        # Intentionally trigger an error
        try:
            # This will fail if user_id must exist
            invalid_user = User(id=1, email="invalid@example.com")  # Duplicate ID
            db_session.add(invalid_user)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify ALL changes were rolled back
        refreshed_account1 = db_session.query(Account).filter_by(id=account1.id).first()
        refreshed_account2 = db_session.query(Account).filter_by(id=account2.id).first()
        
        assert refreshed_account1.balance == initial_balance1
        assert refreshed_account2.balance == initial_balance2
        
        # Verify no transaction records were added
        tx_count = db_session.query(Transaction).count()
        assert tx_count == 0

    def test_multiple_transactions_independence(self, db_session, sample_data):
        """Test that independent transactions don't interfere."""
        account1 = sample_data["account1"]
        account2 = sample_data["account2"]
        
        # Transaction 1: Successful
        account1.balance -= 100.00
        account2.balance += 100.00
        db_session.commit()
        
        # Verify first transaction succeeded
        assert db_session.query(Account).filter_by(id=account1.id).first().balance == 900.00
        assert db_session.query(Account).filter_by(id=account2.id).first().balance == 600.00
        
        # Transaction 2: Will fail
        try:
            account1.balance -= 1000.00  # Insufficient funds
            account2.balance += 1000.00
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
        
        # Verify first transaction's changes are preserved
        assert db_session.query(Account).filter_by(id=account1.id).first().balance == 900.00
        assert db_session.query(Account).filter_by(id=account2.id).first().balance == 600.00

    def test_rollback_with_explicit_savepoint(self, db_session, sample_data):
        """Test rollback to a specific savepoint."""
        account1 = sample_data["account1"]
        initial_balance = account1.balance
        
        # Create a savepoint
        savepoint = db_session.begin_nested()
        
        # Make changes
        account1.balance -= 50.00
        db_session.commit()  # This commits within the nested transaction
        
        # Rollback to savepoint
        savepoint.rollback()
        
        # Verify changes were rolled back
        refreshed_account = db_session.query(Account).filter_by(id=account1.id).first()
        assert refreshed_account.balance == initial_balance

    def test_rollback_multiple_models(self, db_session, sample_data):
        """Test rollback with multiple model relationships."""
        user = sample_data["user1"]
        account = sample_data["account1"]
        
        initial_user_count = db_session.query(User).count()
        initial_account_count = db_session.query(Account).count()
        
        try:
            # Create new user with invalid data
            new_user = User(id=999, name="Charlie", email="charlie@example.com")
            db_session.add(new_user)
            
            # Create associated accounts - one will fail
            db_session.add(Account(id=999, user_id=999, balance=1000.00))
            db_session.add(Account(id=1000, user_id=999, balance=2000.00))
            
            # This will fail if there's a constraint on balance
            invalid_account = Account(id=1001, user_id=999, balance=-100.00)
            db_session.add(invalid_account)
            
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify no records were added
        assert db_session.query(User).count() == initial_user_count
        assert db_session.query(Account).count() == initial_account_count

    def test_rollback_with_session_flush(self, db_session, sample_data):
        """Test that flush can be rolled back properly."""
        account1 = sample_data["account1"]
        initial_balance = account1.balance
        
        try:
            # Make changes
            account1.balance -= 30.00
            
            # Flush to database but don't commit
            db_session.flush()
            
            # Verify changes are visible in session but not persisted
            assert account1.balance == initial_balance - 30.00
            
            # Trigger error
            account1.balance -= 10000.00  # Violates constraint
            
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
        
        # Verify complete rollback
        refreshed_account = db_session.query(Account).filter_by(id=account1.id).first()
        assert refreshed_account.balance == initial_balance


class TestTransactionIsolation:
    """Test transaction isolation and rollback scenarios."""
    
    def test_rollback_on_duplicate_email(self, db_session, sample_data):
        """Test rollback when inserting duplicate email."""
        initial_user_count = db_session.query(User).count()
        
        try:
            # Try to create user with duplicate email
            duplicate_user = User(id=999, name="Charlie", email="alice@example.com")
            db_session.add(duplicate_user)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify no new user was created
        assert db_session.query(User).count() == initial_user_count
        assert db_session.query(User).filter_by(email="alice@example.com").first() is not None

    def test_rollback_during_bulk_operations(self, db_session, sample_data):
        """Test rollback during bulk insert operations."""
        initial_account_count = db_session.query(Account).count()
        
        try:
            # Bulk insert multiple accounts
            accounts = [
                Account(id=10, user_id=1, balance=100.00),
                Account(id=11, user_id=1, balance=200.00),
                Account(id=12, user_id=999, balance=300.00),  # Invalid user_id
                Account(id=13, user_id=1, balance=400.00),
            ]
            db_session.add_all(accounts)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify no accounts were added
        assert db_session.query(Account).count() == initial_account_count

    def test_rollback_with_relationships(self, db_session, sample_data):
        """Test rollback when creating objects with relationships."""
        user = sample_data["user1"]
        initial_account_count = db_session.query(Account).count()
        
        try:
            # Create user with accounts
            new_user = User(id=100, name="David", email="david@example.com")
            new_user.accounts = [
                Account(id=100, balance=500.00),
                Account(id=101, balance=600.00),
                Account(id=102, balance=-100.00),  # Invalid balance
            ]
            db_session.add(new_user)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify no records were added
        assert db_session.query(User).filter_by(id=100).first() is None
        assert db_session.query(Account).filter_by(id=100).first() is None

    def test_rollback_after_partial_operations(self, db_session, sample_data):
        """Test rollback after some operations have been performed."""
        account1 = sample_data["account1"]
        account2 = sample_data["account2"]
        
        initial_balance1 = account1.balance
        initial_balance2 = account2.balance
        
        # Perform some successful operations
        account1.balance -= 50.00
        db_session.flush()
        
        # Add a transaction record
        tx = Transaction(from_account=account1.id, to_account=account2.id, amount=50.00)
        db_session.add(tx)
        db_session.flush()
        
        # Then trigger an error
        try:
            account1.balance -= 1000.00  # Will violate constraint
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # All changes should be rolled back
        refreshed_account1 = db_session.query(Account).filter_by(id=account1.id).first()
        refreshed_account2 = db_session.query(Account).filter_by(id=account2.id).first()
        
        assert refreshed_account1.balance == initial_balance1
        assert refreshed_account2.balance == initial_balance2
        assert db_session.query(Transaction).count() == 0

    def test_rollback_handles_multiple_errors(self, db_session, sample_data):
        """Test rollback handling multiple errors in sequence."""
        account1 = sample_data["account1"]
        initial_balance = account1.balance
        
        # Try multiple invalid operations
        errors_handled = 0
        
        for _ in range(3):
            try:
                account1.balance = -100.00  # Invalid
                db_session.commit()
            except IntegrityError:
                db_session.rollback()
                errors_handled += 1
        
        # Verify account state remained consistent
        refreshed_account = db_session.query(Account).filter_by(id=account1.id).first()
        assert refreshed_account.balance == initial_balance
        assert errors_handled == 3

    def test_rollback_preserves_original_state(self, db_session, sample_data):
        """Test that rollback completely preserves original state."""
        # Get initial state
        initial_users = db_session.query(User).all()
        initial_accounts = db_session.query(Account).all()
        initial_transactions = db_session.query(Transaction).all()
        
        try:
            # Perform multiple operations
            new_user = User(id=100, name="Eve", email="eve@example.com")
            db_session.add(new_user)
            
            account = Account(id=100, user_id=100, balance=500.00)
            db_session.add(account)
            
            tx = Transaction(from_account=1, to_account=100, amount=200.00)
            db_session.add(tx)
            
            # Modify existing
            account1 = sample_data["account1"]
            account1.balance -= 200.00
            
            # Trigger error
            account1.balance = -50.00  # Invalid
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify no changes were persisted
        assert db_session.query(User).all() == initial_users
        assert db_session.query(Account).all() == initial_accounts
        assert db_session.query(Transaction).all() == initial_transactions


def test_rollback_after_connection_error(monkeypatch, db_session, sample_data):
    """Test rollback when a connection error occurs."""
    account1 = sample_data["account1"]
    initial_balance = account1.balance
    
    # Mock a connection error
    def mock_commit(*args, **kwargs):
        raise SQLAlchemyError("Connection lost")
    
    monkeypatch.setattr(db_session, 'commit', mock_commit)
    
    try:
        account1.balance -= 50.00
        db_session.commit()
    except SQLAlchemyError:
        db_session.rollback()
    
    # Verify rollback occurred
    refreshed_account = db_session.query(Account).filter_by(id=account1.id).first()
    assert refreshed_account.balance == initial_balance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
