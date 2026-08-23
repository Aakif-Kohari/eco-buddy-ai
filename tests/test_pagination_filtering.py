# tests/test_pagination_filtering.py
"""
Comprehensive pagination and filtering tests for database queries.
Tests various pagination strategies, filtering options, and combination scenarios.
"""

import pytest
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, and_, or_, desc, asc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import math

# Define models
Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500))
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order_items = relationship("OrderItem", back_populates="product")

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(20))
    city = Column(String(100))
    state = Column(String(50))
    country = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default='pending')
    shipping_address = Column(String(200))
    payment_method = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
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
    """Create extensive sample data for pagination/filtering tests."""
    # Create customers
    customers = []
    for i in range(1, 101):
        customer = Customer(
            id=i,
            first_name=f"First{i}",
            last_name=f"Last{i}",
            email=f"customer{i}@example.com",
            phone=f"555-{i:04d}",
            city=f"City{i % 10}",
            state=f"State{i % 5}",
            country=f"Country{i % 3}",
            created_at=datetime.utcnow() - timedelta(days=i % 30),
            is_active=i % 2 == 0
        )
        customers.append(customer)
    db_session.add_all(customers)
    
    # Create products
    products = []
    categories = ['Electronics', 'Books', 'Clothing', 'Food', 'Toys', 'Sports', 'Home', 'Beauty']
    for i in range(1, 201):
        product = Product(
            id=i,
            name=f"Product{i}",
            description=f"Description for product {i}",
            price=round(10.0 + (i % 100) * 1.5, 2),
            category=categories[i % len(categories)],
            stock_quantity=(i * 7) % 100,
            is_active=i % 3 != 0,
            created_at=datetime.utcnow() - timedelta(days=i % 60)
        )
        products.append(product)
    db_session.add_all(products)
    
    # Create orders
    orders = []
    for i in range(1, 51):
        order = Order(
            id=i,
            customer_id=(i % 20) + 1,
            order_date=datetime.utcnow() - timedelta(days=i % 45),
            total_amount=round(50.0 + (i % 50) * 10.5, 2),
            status=['pending', 'processing', 'shipped', 'delivered', 'cancelled'][i % 5],
            shipping_address=f"{i} Main St, City{i % 10}",
            payment_method=['credit_card', 'paypal', 'bank_transfer'][i % 3]
        )
        orders.append(order)
    db_session.add_all(orders)
    
    # Create order items
    order_items = []
    for i in range(1, 151):
        order_id = (i % 25) + 1
        product_id = (i % 30) + 1
        quantity = (i % 5) + 1
        unit_price = round(20.0 + (i % 50) * 2.5, 2)
        order_item = OrderItem(
            id=i,
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=round(quantity * unit_price, 2)
        )
        order_items.append(order_item)
    db_session.add_all(order_items)
    
    db_session.commit()
    
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items
    }


class TestBasicPagination:
    """Test basic pagination functionality."""
    
    def test_offset_limit_pagination(self, db_session, sample_data):
        """Test pagination using offset and limit."""
        page_size = 10
        
        # Page 1
        page1 = db_session.query(Product).order_by(Product.id).offset(0).limit(page_size).all()
        assert len(page1) == page_size
        assert page1[0].id == 1
        assert page1[-1].id == 10
        
        # Page 2
        page2 = db_session.query(Product).order_by(Product.id).offset(page_size).limit(page_size).all()
        assert len(page2) == page_size
        assert page2[0].id == 11
        assert page2[-1].id == 20
        
        # All pages
        total_products = db_session.query(Product).count()
        total_pages = math.ceil(total_products / page_size)
        assert total_pages == 20
        
        # Last page
        last_page = db_session.query(Product).order_by(Product.id).offset((total_pages - 1) * page_size).limit(page_size).all()
        assert len(last_page) == total_products % page_size

    def test_cursor_based_pagination(self, db_session, sample_data):
        """Test cursor-based (keyset) pagination."""
        page_size = 10
        
        # First page
        first_page = db_session.query(Product).order_by(Product.id).limit(page_size).all()
        assert len(first_page) == page_size
        last_id = first_page[-1].id
        
        # Next page using cursor
        next_page = db_session.query(Product).filter(Product.id > last_id).order_by(Product.id).limit(page_size).all()
        assert len(next_page) == page_size
        assert next_page[0].id == last_id + 1
        
        # Verify no overlap
        first_page_ids = set(p.id for p in first_page)
        next_page_ids = set(p.id for p in next_page)
        assert first_page_ids.isdisjoint(next_page_ids)

    def test_offset_pagination_with_filtering(self, db_session, sample_data):
        """Test pagination combined with filtering."""
        # Filter active products and paginate
        page_size = 15
        active_products = db_session.query(Product).filter(Product.is_active == True).order_by(Product.id)
        
        total_active = active_products.count()
        page = active_products.offset(0).limit(page_size).all()
        
        assert len(page) == min(page_size, total_active)
        assert all(p.is_active for p in page)

    def test_pagination_with_order_by(self, db_session, sample_data):
        """Test pagination with different order by clauses."""
        page_size = 5
        
        # Ascending
        asc_page = db_session.query(Product).order_by(Product.price.asc()).offset(0).limit(page_size).all()
        prices = [p.price for p in asc_page]
        assert prices == sorted(prices)
        
        # Descending
        desc_page = db_session.query(Product).order_by(Product.price.desc()).offset(0).limit(page_size).all()
        prices = [p.price for p in desc_page]
        assert prices == sorted(prices, reverse=True)
        
        # Multiple columns
        multi_page = db_session.query(Product).order_by(Product.category, Product.price.desc()).offset(0).limit(page_size).all()
        categories = [p.category for p in multi_page]
        assert categories == sorted(categories)


class TestFilteringOperations:
    """Test various filtering operations."""
    
    def test_equality_filtering(self, db_session, sample_data):
        """Test equality filtering."""
        # Filter by exact category
        products = db_session.query(Product).filter(Product.category == 'Electronics').all()
        assert all(p.category == 'Electronics' for p in products)
        
        # Filter by exact status
        orders = db_session.query(Order).filter(Order.status == 'delivered').all()
        assert all(o.status == 'delivered' for o in orders)

    def test_comparison_filtering(self, db_session, sample_data):
        """Test comparison operators filtering."""
        # Greater than
        expensive_products = db_session.query(Product).filter(Product.price > 100.0).all()
        assert all(p.price > 100.0 for p in expensive_products)
        
        # Less than
        cheap_products = db_session.query(Product).filter(Product.price < 50.0).all()
        assert all(p.price < 50.0 for p in cheap_products)
        
        # Greater than or equal
        high_stock = db_session.query(Product).filter(Product.stock_quantity >= 50).all()
        assert all(p.stock_quantity >= 50 for p in high_stock)
        
        # Between
        mid_price = db_session.query(Product).filter(Product.price.between(50.0, 100.0)).all()
        assert all(50.0 <= p.price <= 100.0 for p in mid_price)

    def test_in_filtering(self, db_session, sample_data):
        """Test IN clause filtering."""
        categories = ['Electronics', 'Books', 'Toys']
        products = db_session.query(Product).filter(Product.category.in_(categories)).all()
        assert all(p.category in categories for p in products)
        
        # Nested IN with subquery
        statuses = ['shipped', 'delivered']
        orders = db_session.query(Order).filter(Order.status.in_(statuses)).all()
        assert all(o.status in statuses for o in orders)

    def test_pattern_filtering(self, db_session, sample_data):
        """Test LIKE pattern filtering."""
        # Starts with
        products1 = db_session.query(Product).filter(Product.name.like('Product1%')).all()
        assert all(p.name.startswith('Product1') for p in products1)
        
        # Contains
        products2 = db_session.query(Product).filter(Product.description.contains('product 1')).all()
        assert all('product 1' in p.description.lower() for p in products2)
        
        # Ends with
        customers = db_session.query(Customer).filter(Customer.email.like('%@example.com')).all()
        assert all(c.email.endswith('@example.com') for c in customers)

    def test_date_filtering(self, db_session, sample_data):
        """Test date and time filtering."""
        # Filter by date range
        start_date = datetime.utcnow() - timedelta(days=10)
        end_date = datetime.utcnow()
        
        recent_orders = db_session.query(Order).filter(
            Order.order_date.between(start_date, end_date)
        ).all()
        assert all(start_date <= o.order_date <= end_date for o in recent_orders)
        
        # Filter by specific day (converted to date)
        target_date = datetime.utcnow().date()
        orders_on_date = db_session.query(Order).filter(
            func.date(Order.order_date) == target_date
        ).all()

    def test_boolean_filtering(self, db_session, sample_data):
        """Test boolean field filtering."""
        active_customers = db_session.query(Customer).filter(Customer.is_active == True).all()
        assert all(c.is_active for c in active_customers)
        
        inactive_products = db_session.query(Product).filter(Product.is_active == False).all()
        assert all(not p.is_active for p in inactive_products)


class TestAdvancedFiltering:
    """Test advanced filtering techniques."""
    
    def test_and_conditions(self, db_session, sample_data):
        """Test AND combinations."""
        # Multiple conditions
        products = db_session.query(Product).filter(
            Product.category == 'Electronics',
            Product.price > 50.0,
            Product.stock_quantity > 10
        ).all()
        assert all(p.category == 'Electronics' and p.price > 50.0 and p.stock_quantity > 10 for p in products)
        
        # Using and_()
        products2 = db_session.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.price.between(20.0, 80.0)
            )
        ).all()
        assert all(p.is_active and 20.0 <= p.price <= 80.0 for p in products2)

    def test_or_conditions(self, db_session, sample_data):
        """Test OR combinations."""
        products = db_session.query(Product).filter(
            or_(
                Product.category == 'Electronics',
                Product.category == 'Books',
                Product.price > 200.0
            )
        ).all()
        assert all(p.category in ['Electronics', 'Books'] or p.price > 200.0 for p in products)

    def test_complex_filtering(self, db_session, sample_data):
        """Test complex combinations of AND and OR."""
        products = db_session.query(Product).filter(
            or_(
                and_(
                    Product.category == 'Electronics',
                    Product.price < 100.0
                ),
                and_(
                    Product.category == 'Books',
                    Product.price < 50.0
                ),
                Product.category == 'Toys'
            )
        ).all()
        
        for p in products:
            assert (p.category == 'Electronics' and p.price < 100.0) or \
                   (p.category == 'Books' and p.price < 50.0) or \
                   (p.category == 'Toys')

    def test_negation_filtering(self, db_session, sample_data):
        """Test NOT conditions."""
        # Not equal
        products = db_session.query(Product).filter(Product.category != 'Electronics').all()
        assert all(p.category != 'Electronics' for p in products)
        
        # Not IN
        excluded_categories = ['Food', 'Beauty']
        products2 = db_session.query(Product).filter(~Product.category.in_(excluded_categories)).all()
        assert all(p.category not in excluded_categories for p in products2)
        
        # NOT EXISTS
        # Products with no order items
        products_without_orders = db_session.query(Product).filter(
            ~Product.order_items.any()
        ).all()

    def test_nested_filtering(self, db_session, sample_data):
        """Test filtering with nested queries."""
        # Subquery filter
        subquery = db_session.query(OrderItem.product_id).filter(
            OrderItem.quantity > 3
        ).distinct()
        
        popular_products = db_session.query(Product).filter(
            Product.id.in_(subquery)
        ).all()
        
        # Existence filter
        products_with_orders = db_session.query(Product).filter(
            Product.order_items.any()
        ).all()
        assert len(products_with_orders) > 0


class TestPaginationAndFilteringCombined:
    """Test pagination combined with filtering."""
    
    def test_paginated_filtered_query(self, db_session, sample_data):
        """Test filtering and pagination together."""
        page_size = 10
        page_number = 3
        
        # Filter active electronics with price > 50
        query = db_session.query(Product).filter(
            Product.is_active == True,
            Product.category == 'Electronics',
            Product.price > 50.0
        ).order_by(Product.id)
        
        total_count = query.count()
        page = query.offset((page_number - 1) * page_size).limit(page_size).all()
        
        assert len(page) <= page_size
        assert all(p.is_active and p.category == 'Electronics' and p.price > 50.0 for p in page)

    def test_paginated_with_sorting(self, db_session, sample_data):
        """Test pagination with sorting and filtering."""
        page_size = 15
        
        # Filter and sort by price descending
        query = db_session.query(Product).filter(
            Product.is_active == True,
            Product.stock_quantity > 20
        ).order_by(Product.price.desc(), Product.id)
        
        page = query.offset(0).limit(page_size).all()
        
        # Verify sorting
        prices = [p.price for p in page]
        assert prices == sorted(prices, reverse=True)
        
        # Verify filtering
        assert all(p.is_active and p.stock_quantity > 20 for p in page)

    def test_paginated_with_multiple_filters(self, db_session, sample_data):
        """Test pagination with multiple filter criteria."""
        page_size = 8
        
        # Complex filter
        query = db_session.query(Order).filter(
            Order.status.in_(['shipped', 'delivered']),
            Order.total_amount > 100.0,
            Order.payment_method == 'credit_card'
        ).order_by(Order.order_date.desc(), Order.id)
        
        total_count = query.count()
        page1 = query.offset(0).limit(page_size).all()
        page2 = query.offset(page_size).limit(page_size).all()
        
        # Verify all conditions
        for order in page1 + page2:
            assert order.status in ['shipped', 'delivered']
            assert order.total_amount > 100.0
            assert order.payment_method == 'credit_card'

    def test_cursor_pagination_with_filters(self, db_session, sample_data):
        """Test cursor-based pagination with filters."""
        page_size = 8
        last_price = None
        last_id = None
        
        # Filter products with price > 50
        query = db_session.query(Product).filter(
            Product.is_active == True,
            Product.price > 50.0
        ).order_by(Product.price, Product.id)
        
        # First page
        page1 = query.limit(page_size).all()
        assert len(page1) == page_size
        last_price = page1[-1].price
        last_id = page1[-1].id
        
        # Next page using cursor
        page2 = db_session.query(Product).filter(
            Product.is_active == True,
            Product.price > 50.0,
            or_(
                Product.price > last_price,
                and_(
                    Product.price == last_price,
                    Product.id > last_id
                )
            )
        ).order_by(Product.price, Product.id).limit(page_size).all()
        
        # Verify no overlap
        page1_ids = set(p.id for p in page1)
        page2_ids = set(p.id for p in page2)
        assert page1_ids.isdisjoint(page2_ids)
        
        # Verify order
        all_prices = [p.price for p in page1 + page2]
        assert all_prices == sorted(all_prices)


class TestEdgeCasesAndPerformance:
    """Test edge cases and performance scenarios."""
    
    def test_empty_results_pagination(self, db_session, sample_data):
        """Test pagination with no results."""
        query = db_session.query(Product).filter(Product.category == 'Nonexistent')
        
        page = query.offset(0).limit(10).all()
        assert len(page) == 0
        
        count = query.count()
        assert count == 0

    def test_pagination_beyond_data(self, db_session, sample_data):
        """Test pagination beyond available data."""
        total = db_session.query(Product).count()
        beyond = db_session.query(Product).offset(total + 100).limit(10).all()
        assert len(beyond) == 0
        
        # Page number beyond total pages
        large_offset = db_session.query(Product).offset(9999).limit(10).all()
        assert len(large_offset) == 0

    def test_partial_page(self, db_session, sample_data):
        """Test last page with fewer items."""
        page_size = 7
        total = db_session.query(Product).count()
        last_page_start = ((total - 1) // page_size) * page_size
        
        last_page = db_session.query(Product).order_by(Product.id).offset(last_page_start).limit(page_size).all()
        expected_count = total - last_page_start
        assert len(last_page) == expected_count
        assert len(last_page) < page_size

    def test_pagination_with_joins(self, db_session, sample_data):
        """Test pagination with joined tables."""
        page_size = 12
        
        # Query with join and filter
        query = db_session.query(Order).join(Customer).filter(
            Customer.is_active == True,
            Order.total_amount > 150.0
        ).order_by(Order.id)
        
        page = query.offset(0).limit(page_size).all()
        
        # Verify results
        for order in page:
            assert order.total_amount > 150.0
            assert order.customer.is_active

    def test_pagination_with_aggregation(self, db_session, sample_data):
        """Test pagination with aggregated results."""
        page_size = 10
        
        # Group by product and aggregate
        query = db_session.query(
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(OrderItem).group_by(Product.id).having(
            func.sum(OrderItem.quantity) > 5
        ).order_by(func.sum(OrderItem.quantity).desc())
        
        page = query.offset(0).limit(page_size).all()
        assert len(page) <= page_size
        
        # Verify aggregation
        for item in page:
            assert item.total_sold > 5

    def test_pagination_with_distinct(self, db_session, sample_data):
        """Test pagination with DISTINCT queries."""
        page_size = 8
        
        # Distinct categories with pagination
        query = db_session.query(Product.category).distinct().order_by(Product.category)
        
        categories = query.offset(0).limit(page_size).all()
        assert len(categories) <= page_size
        assert len(set(c[0] for c in categories)) == len(categories)  # All distinct

    def test_combined_search_and_pagination(self, db_session, sample_data):
        """Test combined search functionality with pagination."""
        search_term = "product"
        page_size = 10
        
        # Full-text search simulation
        query = db_session.query(Product).filter(
            or_(
                Product.name.contains(search_term),
                Product.description.contains(search_term)
            )
        ).order_by(Product.id)
        
        total = query.count()
        page = query.offset(0).limit(page_size).all()
        
        assert len(page) <= page_size
        assert all(search_term in p.name.lower() or search_term in p.description.lower() for p in page)

    def test_pagination_with_complex_order_by(self, db_session, sample_data):
        """Test pagination with complex ordering including nulls."""
        page_size = 10
        
        # Order by multiple columns with nulls
        query = db_session.query(Product).order_by(
            Product.category.asc(),
            Product.price.desc(),
            Product.id.asc()
        )
        
        page = query.offset(0).limit(page_size).all()
        
        # Verify ordering
        for i in range(len(page) - 1):
            assert page[i].category <= page[i+1].category
            if page[i].category == page[i+1].category:
                assert page[i].price >= page[i+1].price

    def test_filtering_with_pagination_cache(self, db_session, sample_data):
        """Test that pagination results are consistent."""
        page_size = 15
        
        # Execute same query twice with different offset
        query = db_session.query(Product).filter(
            Product.is_active == True,
            Product.category == 'Electronics'
        ).order_by(Product.id)
        
        page1 = query.offset(0).limit(page_size).all()
        page2 = query.offset(page_size).limit(page_size).all()
        page3 = query.offset(page_size * 2).limit(page_size).all()
        
        # Ensure no overlapping IDs
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        page3_ids = {p.id for p in page3}
        
        assert page1_ids.isdisjoint(page2_ids)
        assert page2_ids.isdisjoint(page3_ids)
        assert page1_ids.isdisjoint(page3_ids)


class TestAdvancedFilteringScenarios:
    """Test advanced filtering scenarios."""
    
    def test_range_filtering_with_pagination(self, db_session, sample_data):
        """Test range filters with pagination."""
        price_range = (50.0, 150.0)
        date_range = (datetime.utcnow() - timedelta(days=30), datetime.utcnow())
        page_size = 12
        
        query = db_session.query(Product).filter(
            Product.price.between(price_range[0], price_range[1]),
            Product.created_at.between(date_range[0], date_range[1])
        ).order_by(Product.price)
        
        page = query.offset(0).limit(page_size).all()
        assert all(price_range[0] <= p.price <= price_range[1] for p in page)
        assert all(date_range[0] <= p.created_at <= date_range[1] for p in page)

    def test_multi_tenant_filtering(self, db_session, sample_data):
        """Test filtering in multi-tenant scenarios."""
        # Simulate tenant filtering by country
        country = 'Country0'
        
        customers = db_session.query(Customer).filter(Customer.country == country).all()
        assert all(c.country == country for c in customers)
        
        # Paginated tenant data
        page_size = 10
        query = db_session.query(Customer).filter(
            Customer.country == country,
            Customer.is_active == True
        ).order_by(Customer.id)
        
        page = query.offset(0).limit(page_size).all()
        assert all(c.country == country and c.is_active for c in page)

    def test_filtering_by_relationship(self, db_session, sample_data):
        """Test filtering based on related data."""
        # Customers who placed orders
        customers_with_orders = db_session.query(Customer).filter(
            Customer.orders.any()
        ).all()
        assert len(customers_with_orders) > 0
        
        # Customers with expensive orders (> 200)
        customers_with_expensive_orders = db_session.query(Customer).filter(
            Customer.orders.any(Order.total_amount > 200.0)
        ).all()
        
        # Paginated results
        page_size = 8
        query = db_session.query(Customer).filter(
            Customer.orders.any(Order.total_amount > 150.0)
        ).order_by(Customer.id)
        
        page = query.offset(0).limit(page_size).all()
        assert len(page) <= page_size

    def test_filtering_with_exists(self, db_session, sample_data):
        """Test EXISTS conditions with pagination."""
        # Products that have been ordered
        products_with_orders = db_session.query(Product).filter(
            db_session.query(OrderItem).filter(
                OrderItem.product_id == Product.id
            ).exists()
        ).order_by(Product.id)
        
        page = products_with_orders.offset(0).limit(10).all()
        assert len(page) > 0

    def test_filtering_with_case_sensitivity(self, db_session, sample_data):
        """Test case-insensitive filtering."""
        # Case-insensitive search
        search_term = 'product'
        products = db_session.query(Product).filter(
            func.lower(Product.name).contains(search_term.lower())
        ).all()
        
        assert all(search_term.lower() in p.name.lower() for p in products)

    def test_pagination_with_dynamic_filters(self, db_session, sample_data):
        """Test dynamic filter building with pagination."""
        filters = {
            'category': 'Electronics',
            'min_price': 50.0,
            'max_price': 200.0,
            'active': True,
            'min_stock': 10
        }
        
        # Build dynamic query
        query = db_session.query(Product)
        
        if filters.get('category'):
            query = query.filter(Product.category == filters['category'])
        if filters.get('min_price'):
            query = query.filter(Product.price >= filters['min_price'])
        if filters.get('max_price'):
            query = query.filter(Product.price <= filters['max_price'])
        if filters.get('active'):
            query = query.filter(Product.is_active == filters['active'])
        if filters.get('min_stock'):
            query = query.filter(Product.stock_quantity >= filters['min_stock'])
        
        query = query.order_by(Product.id)
        
        page_size = 10
        page = query.offset(0).limit(page_size).all()
        
        # Verify all filters applied
        for p in page:
            assert p.category == filters['category']
            assert p.price >= filters['min_price']
            assert p.price <= filters['max_price']
            assert p.is_active == filters['active']
            assert p.stock_quantity >= filters['min_stock']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
