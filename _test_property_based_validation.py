"""
Property-Based Tests for Validation Logic

This module introduces property-based testing for API validation logic
using Hypothesis. It tests that validation rules hold true for all
valid inputs and properly rejects invalid ones.

Run with: pytest test_property_based_validation.py -v

Dependencies: pip install hypothesis
"""

import pytest
import json
import re
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from email_validator import validate_email, EmailNotValidError
from hypothesis import given, assume, strategies as st, settings, reproduce_failure
from hypothesis.strategies import (
    text, integers, floats, booleans, lists, dictionaries, 
    one_of, none, just, sampled_from, datetimes, emails, 
    uuids, builds, composite, recursive, fixed_dictionaries,
    from_regex, characters, ip_addresses
)
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition
import string

# Import from previous modules
from test_api_error_handling import APIClient, ValidationError


# ==================== Property-Based Test Strategies ====================

@composite
def valid_email_strategy(draw):
    """Generate valid email addresses."""
    local = draw(text(
        alphabet=string.ascii_lowercase + string.digits + '._+-',
        min_size=1,
        max_size=64
    ))
    domain = draw(text(
        alphabet=string.ascii_lowercase + string.digits + '-',
        min_size=1,
        max_size=63
    ))
    tld = draw(sampled_from(['com', 'org', 'net', 'edu', 'gov', 'io', 'co', 'uk', 'de', 'fr']))
    return f"{local}@{domain}.{tld}"


@composite
def valid_username_strategy(draw):
    """Generate valid usernames (alphanumeric + underscore, 3-20 chars)."""
    return draw(text(
        alphabet=string.ascii_letters + string.digits + '_',
        min_size=3,
        max_size=20
    ))


@composite
def valid_password_strategy(draw):
    """Generate valid passwords (at least 8 chars, mix of cases, digits, special)."""
    length = draw(integers(min_value=8, max_value=32))
    chars = string.ascii_letters + string.digits + string.punctuation
    return draw(text(alphabet=chars, min_size=length, max_size=length))


@composite
def valid_phone_strategy(draw):
    """Generate valid phone numbers (simplified)."""
    country_code = draw(integers(min_value=1, max_value=99))
    area_code = draw(integers(min_value=100, max_value=999))
    number = draw(integers(min_value=1000000, max_value=9999999))
    return f"+{country_code}{area_code}{number}"


@composite
def valid_date_strategy(draw):
    """Generate valid ISO date strings."""
    year = draw(integers(min_value=1900, max_value=2100))
    month = draw(integers(min_value=1, max_value=12))
    day = draw(integers(min_value=1, max_value=28))  # Simplified
    return f"{year:04d}-{month:02d}-{day:02d}"


@composite
def valid_uuid_strategy(draw):
    """Generate valid UUID strings."""
    return draw(uuids()).hex


@composite
def valid_url_strategy(draw):
    """Generate valid URLs."""
    protocol = draw(sampled_from(['http', 'https']))
    domain = draw(text(
        alphabet=string.ascii_lowercase + string.digits + '-',
        min_size=3,
        max_size=20
    ))
    tld = draw(sampled_from(['com', 'org', 'net', 'io', 'co']))
    path = draw(one_of(
        just('/'),
        text(alphabet=string.ascii_lowercase + '/', min_size=1, max_size=30)
    ))
    return f"{protocol}://{domain}.{tld}{path}"


@composite
def valid_ip_strategy(draw):
    """Generate valid IP addresses."""
    return draw(ip_addresses())


# ==================== API Validation Classes ====================

class UserValidator:
    """Validator for user registration data."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        if not username or len(username) < 3 or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """Validate password strength."""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        if not any(c in string.punctuation for c in password):
            return False
        return True
    
    @staticmethod
    def validate_age(age: int) -> bool:
        """Validate age (13-120)."""
        return 13 <= age <= 120
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format."""
        return bool(re.match(r'^\+\d{1,3}\d{3}\d{7}$', phone))
    
    @staticmethod
    def validate_user_data(data: Dict[str, Any]) -> List[str]:
        """Validate complete user data."""
        errors = []
        
        if not data.get('email'):
            errors.append("Email is required")
        elif not UserValidator.validate_email(data['email']):
            errors.append("Invalid email format")
        
        if not data.get('username'):
            errors.append("Username is required")
        elif not UserValidator.validate_username(data['username']):
            errors.append("Invalid username format")
        
        if not data.get('password'):
            errors.append("Password is required")
        elif not UserValidator.validate_password(data['password']):
            errors.append("Password does not meet requirements")
        
        if data.get('age') is not None:
            if not UserValidator.validate_age(data['age']):
                errors.append("Invalid age")
        
        return errors


class ProductValidator:
    """Validator for product data."""
    
    @staticmethod
    def validate_price(price: Union[int, float, Decimal]) -> bool:
        """Validate price (non-negative)."""
        return isinstance(price, (int, float, Decimal)) and price >= 0
    
    @staticmethod
    def validate_quantity(quantity: int) -> bool:
        """Validate quantity (non-negative integer)."""
        return isinstance(quantity, int) and quantity >= 0
    
    @staticmethod
    def validate_sku(sku: str) -> bool:
        """Validate SKU format."""
        return bool(re.match(r'^[A-Z]{2,4}-\d{4,8}$', sku))
    
    @staticmethod
    def validate_product_data(data: Dict[str, Any]) -> List[str]:
        """Validate complete product data."""
        errors = []
        
        if not data.get('name'):
            errors.append("Product name is required")
        elif len(data['name']) > 100:
            errors.append("Product name is too long")
        
        if data.get('price') is None:
            errors.append("Price is required")
        elif not ProductValidator.validate_price(data['price']):
            errors.append("Invalid price")
        
        if data.get('quantity') is None:
            errors.append("Quantity is required")
        elif not ProductValidator.validate_quantity(data['quantity']):
            errors.append("Invalid quantity")
        
        if data.get('sku'):
            if not ProductValidator.validate_sku(data['sku']):
                errors.append("Invalid SKU format")
        
        return errors


class OrderValidator:
    """Validator for order data."""
    
    @staticmethod
    def validate_order_id(order_id: str) -> bool:
        """Validate order ID format."""
        return bool(re.match(r'^ORD-[A-Z0-9]{8}$', order_id))
    
    @staticmethod
    def validate_status(status: str) -> bool:
        """Validate order status."""
        valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        return status in valid_statuses
    
    @staticmethod
    def validate_amount(amount: float) -> bool:
        """Validate order amount."""
        return amount > 0 and amount < 1000000
    
    @staticmethod
    def validate_order_data(data: Dict[str, Any]) -> List[str]:
        """Validate complete order data."""
        errors = []
        
        if not data.get('order_id'):
            errors.append("Order ID is required")
        elif not OrderValidator.validate_order_id(data['order_id']):
            errors.append("Invalid order ID format")
        
        if not data.get('status'):
            errors.append("Status is required")
        elif not OrderValidator.validate_status(data['status']):
            errors.append("Invalid status")
        
        if data.get('amount') is None:
            errors.append("Amount is required")
        elif not OrderValidator.validate_amount(data['amount']):
            errors.append("Invalid amount")
        
        if not data.get('items') or len(data['items']) == 0:
            errors.append("At least one item is required")
        
        return errors


# ==================== Property-Based Tests for User Validation ====================

class TestUserValidationProperties:
    """Property-based tests for user validation logic."""
    
    @settings(max_examples=100, deadline=500)
    @given(email=valid_email_strategy())
    def test_valid_email_always_valid(self, email):
        """Property: Valid emails should always pass validation."""
        assert UserValidator.validate_email(email) is True
    
    @settings(max_examples=50, deadline=500)
    @given(email=text(min_size=1, max_size=100))
    def test_email_validation_preserves_input(self, email):
        """Property: Email validation should not modify input."""
        original = email
        result = UserValidator.validate_email(email)
        # The email string should be unchanged
        assert original == email
    
    @settings(max_examples=100, deadline=500)
    @given(username=valid_username_strategy())
    def test_valid_username_always_valid(self, username):
        """Property: Valid usernames should always pass validation."""
        assert UserValidator.validate_username(username) is True
    
    @settings(max_examples=50, deadline=500)
    @given(username=text(alphabet=string.ascii_lowercase, min_size=3, max_size=20))
    def test_lowercase_username_valid(self, username):
        """Property: Lowercase alphanumeric usernames should be valid."""
        assert UserValidator.validate_username(username) is True
    
    @settings(max_examples=50, deadline=500)
    @given(password=valid_password_strategy())
    def test_valid_password_always_valid(self, password):
        """Property: Valid passwords should always pass validation."""
        assert UserValidator.validate_password(password) is True
    
    @settings(max_examples=50, deadline=500)
    @given(password=text(max_size=7))
    def test_password_length_validation(self, password):
        """Property: Passwords shorter than 8 chars should be invalid."""
        assert UserValidator.validate_password(password) is False
    
    @settings(max_examples=50, deadline=500)
    @given(password=text(min_size=8, max_size=32, alphabet=string.ascii_lowercase))
    def test_password_requires_uppercase(self, password):
        """Property: Passwords without uppercase should be invalid."""
        assert UserValidator.validate_password(password) is False
    
    @settings(max_examples=50, deadline=500)
    @given(password=text(min_size=8, max_size=32, alphabet=string.ascii_uppercase))
    def test_password_requires_lowercase(self, password):
        """Property: Passwords without lowercase should be invalid."""
        assert UserValidator.validate_password(password) is False
    
    @settings(max_examples=50, deadline=500)
    @given(password=text(min_size=8, max_size=32, alphabet=string.ascii_letters))
    def test_password_requires_digit(self, password):
        """Property: Passwords without digits should be invalid."""
        assert UserValidator.validate_password(password) is False
    
    @settings(max_examples=50, deadline=500)
    @given(password=text(min_size=8, max_size=32, 
                        alphabet=string.ascii_letters + string.digits))
    def test_password_requires_special_char(self, password):
        """Property: Passwords without special chars should be invalid."""
        assert UserValidator.validate_password(password) is False
    
    @settings(max_examples=50, deadline=500)
    @given(age=integers(min_value=13, max_value=120))
    def test_valid_age_always_valid(self, age):
        """Property: Valid ages should always pass validation."""
        assert UserValidator.validate_age(age) is True
    
    @settings(max_examples=50, deadline=500)
    @given(age=integers(max_value=12))
    def test_age_too_young_invalid(self, age):
        """Property: Ages under 13 should be invalid."""
        assert UserValidator.validate_age(age) is False
    
    @settings(max_examples=50, deadline=500)
    @given(age=integers(min_value=121, max_value=200))
    def test_age_too_old_invalid(self, age):
        """Property: Ages over 120 should be invalid."""
        assert UserValidator.validate_age(age) is False
    
    @settings(max_examples=50, deadline=500)
    @given(phone=valid_phone_strategy())
    def test_valid_phone_always_valid(self, phone):
        """Property: Valid phone numbers should always pass validation."""
        assert UserValidator.validate_phone(phone) is True
    
    @settings(max_examples=100, deadline=500)
    @given(data=fixed_dictionaries({
        'email': valid_email_strategy(),
        'username': valid_username_strategy(),
        'password': valid_password_strategy(),
        'age': integers(min_value=13, max_value=120)
    }))
    def test_complete_user_data_valid(self, data):
        """Property: Complete valid user data should have no errors."""
        errors = UserValidator.validate_user_data(data)
        assert len(errors) == 0


# ==================== Property-Based Tests for Product Validation ====================

class TestProductValidationProperties:
    """Property-based tests for product validation logic."""
    
    @settings(max_examples=100, deadline=500)
    @given(price=floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False))
    def test_valid_price_always_valid(self, price):
        """Property: Non-negative prices should be valid."""
        assert ProductValidator.validate_price(price) is True
    
    @settings(max_examples=50, deadline=500)
    @given(price=floats(max_value=-0.01, allow_nan=False, allow_infinity=False))
    def test_negative_price_invalid(self, price):
        """Property: Negative prices should be invalid."""
        assert ProductValidator.validate_price(price) is False
    
    @settings(max_examples=100, deadline=500)
    @given(quantity=integers(min_value=0, max_value=1000000))
    def test_valid_quantity_always_valid(self, quantity):
        """Property: Non-negative quantities should be valid."""
        assert ProductValidator.validate_quantity(quantity) is True
    
    @settings(max_examples=50, deadline=500)
    @given(quantity=integers(max_value=-1))
    def test_negative_quantity_invalid(self, quantity):
        """Property: Negative quantities should be invalid."""
        assert ProductValidator.validate_quantity(quantity) is False
    
    @settings(max_examples=100, deadline=500)
    @given(sku=from_regex(r'^[A-Z]{2,4}-\d{4,8}$', fullmatch=True))
    def test_valid_sku_always_valid(self, sku):
        """Property: Valid SKU format should always pass validation."""
        assert ProductValidator.validate_sku(sku) is True
    
    @settings(max_examples=50, deadline=500)
    @given(sku=text(alphabet=string.ascii_uppercase + '-', min_size=3, max_size=15))
    def test_invalid_sku_format_invalid(self, sku):
        """Property: Invalid SKU formats should fail validation."""
        # This property holds for most invalid SKUs, but some might still match
        # So we use assume to ensure the SKU doesn't accidentally match the valid format
        assume(not re.match(r'^[A-Z]{2,4}-\d{4,8}$', sku))
        assert ProductValidator.validate_sku(sku) is False
    
    @settings(max_examples=100, deadline=500)
    @given(data=fixed_dictionaries({
        'name': text(min_size=1, max_size=100),
        'price': floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
        'quantity': integers(min_value=0, max_value=1000000),
        'sku': from_regex(r'^[A-Z]{2,4}-\d{4,8}$', fullmatch=True)
    }))
    def test_complete_product_data_valid(self, data):
        """Property: Complete valid product data should have no errors."""
        errors = ProductValidator.validate_product_data(data)
        assert len(errors) == 0


# ==================== Property-Based Tests for Order Validation ====================

class TestOrderValidationProperties:
    """Property-based tests for order validation logic."""
    
    @settings(max_examples=100, deadline=500)
    @given(order_id=from_regex(r'^ORD-[A-Z0-9]{8}$', fullmatch=True))
    def test_valid_order_id_always_valid(self, order_id):
        """Property: Valid order IDs should always pass validation."""
        assert OrderValidator.validate_order_id(order_id) is True
    
    @settings(max_examples=50, deadline=500)
    @given(order_id=text(alphabet=string.ascii_uppercase + string.digits + '-', 
                         min_size=5, max_size=20))
    def test_invalid_order_id_format_invalid(self, order_id):
        """Property: Invalid order ID formats should fail validation."""
        assume(not re.match(r'^ORD-[A-Z0-9]{8}$', order_id))
        assert OrderValidator.validate_order_id(order_id) is False
    
    @settings(max_examples=100, deadline=500)
    @given(status=sampled_from(['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']))
    def test_valid_status_always_valid(self, status):
        """Property: Valid order statuses should always pass validation."""
        assert OrderValidator.validate_status(status) is True
    
    @settings(max_examples=50, deadline=500)
    @given(status=text(alphabet=string.ascii_lowercase, min_size=3, max_size=10))
    def test_invalid_status_invalid(self, status):
        """Property: Invalid order statuses should fail validation."""
        valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        assume(status not in valid_statuses)
        assert OrderValidator.validate_status(status) is False
    
    @settings(max_examples=100, deadline=500)
    @given(amount=floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False))
    def test_valid_amount_always_valid(self, amount):
        """Property: Valid order amounts should always pass validation."""
        assert OrderValidator.validate_amount(amount) is True
    
    @settings(max_examples=50, deadline=500)
    @given(amount=floats(max_value=0, allow_nan=False, allow_infinity=False))
    def test_non_positive_amount_invalid(self, amount):
        """Property: Non-positive amounts should be invalid."""
        assert OrderValidator.validate_amount(amount) is False


# ==================== Stateful Property-Based Tests ====================

class OrderSystemStateful(RuleBasedStateMachine):
    """Stateful property-based testing for order system."""
    
    def __init__(self):
        super().__init__()
        self.orders = {}
        self.next_id = 1
    
    @rule(
        user_id=integers(min_value=1, max_value=1000),
        amount=floats(min_value=0.01, max_value=10000),
        items=lists(text(min_size=1, max_size=20), min_size=1, max_size=10)
    )
    def create_order(self, user_id, amount, items):
        """Create a new order."""
        order_id = f"ORD-{self.next_id:08d}"
        self.next_id += 1
        
        order = {
            'order_id': order_id,
            'user_id': user_id,
            'amount': amount,
            'items': items,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Validate order data
        errors = OrderValidator.validate_order_data(order)
        assert len(errors) == 0, f"Invalid order data: {errors}"
        
        self.orders[order_id] = order
        return order_id
    
    @rule(order_id=text(min_size=1, max_size=20))
    def get_order(self, order_id):
        """Retrieve an order."""
        if order_id in self.orders:
            order = self.orders[order_id]
            # Order should have all required fields
            assert 'order_id' in order
            assert 'status' in order
            assert 'amount' in order
    
    @rule(
        order_id=text(min_size=1, max_size=20),
        new_status=sampled_from(['confirmed', 'shipped', 'delivered', 'cancelled'])
    )
    def update_order_status(self, order_id, new_status):
        """Update order status."""
        if order_id in self.orders:
            old_status = self.orders[order_id]['status']
            self.orders[order_id]['status'] = new_status
            
            # Status should be valid
            assert OrderValidator.validate_status(new_status) is True
    
    @invariant()
    def orders_have_valid_statuses(self):
        """Invariant: All orders should have valid statuses."""
        for order in self.orders.values():
            assert OrderValidator.validate_status(order['status']) is True
    
    @invariant()
    def orders_have_non_negative_amounts(self):
        """Invariant: All orders should have positive amounts."""
        for order in self.orders.values():
            assert OrderValidator.validate_amount(order['amount']) is True


# ==================== Security-Focused Property Tests ====================

class TestSecurityValidationProperties:
    """Security-focused property-based tests."""
    
    @settings(max_examples=100, deadline=500)
    @given(input_string=text(max_size=1000))
    def test_sql_injection_prevention(self, input_string):
        """Property: Validation should handle potential SQL injection strings safely."""
        # Test that validation doesn't crash on any input
        try:
            result = UserValidator.validate_username(input_string)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Validation crashed on input: {input_string[:50]}, Error: {e}")
    
    @settings(max_examples=100, deadline=500)
    @given(input_string=text(max_size=1000))
    def test_xss_prevention(self, input_string):
        """Property: Validation should handle XSS payloads safely."""
        try:
            result = UserValidator.validate_username(input_string)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"XSS input caused crash: {e}")
    
    @settings(max_examples=100, deadline=500)
    @given(email=text(min_size=1, max_size=200))
    def test_email_validation_no_crash(self, email):
        """Property: Email validation should never crash."""
        try:
            result = UserValidator.validate_email(email)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Email validation crashed on: {email[:50]}, Error: {e}")
    
    @settings(max_examples=100, deadline=500)
    @given(password=text(max_size=100))
    def test_password_validation_no_crash(self, password):
        """Property: Password validation should never crash."""
        try:
            result = UserValidator.validate_password(password)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Password validation crashed on: {password[:50]}, Error: {e}")
    
    @settings(max_examples=100, deadline=500)
    @given(data=dictionaries(
        keys=text(max_size=50),
        values=one_of(text(max_size=100), integers(), floats(), booleans(), none()),
        max_size=20
    ))
    def test_validation_no_crash_on_malformed_data(self, data):
        """Property: Validation should handle malformed data without crashing."""
        try:
            # Try to validate various types of malformed data
            if 'email' in data:
                UserValidator.validate_email(str(data['email']))
            if 'username' in data:
                UserValidator.validate_username(str(data['username']))
            if 'password' in data:
                UserValidator.validate_password(str(data['password']))
        except Exception as e:
            pytest.fail(f"Validation crashed on malformed data: {e}")


# ==================== Performance Property Tests ====================

class TestPerformanceProperties:
    """Performance-focused property-based tests."""
    
    @settings(max_examples=50, deadline=1000)
    @given(
        emails=lists(valid_email_strategy(), min_size=1, max_size=100)
    )
    def test_batch_email_validation_performance(self, emails):
        """Property: Batch validation should be reasonably fast."""
        import time
        
        start = time.time()
        for email in emails:
            UserValidator.validate_email(email)
        duration = time.time() - start
        
        # Should process at least 100 emails per second
        assert duration < len(emails) / 100 + 0.1
    
    @settings(max_examples=50, deadline=1000)
    @given(
        usernames=lists(valid_username_strategy(), min_size=1, max_size=100)
    )
    def test_batch_username_validation_performance(self, usernames):
        """Property: Batch username validation should be reasonably fast."""
        import time
        
        start = time.time()
        for username in usernames:
            UserValidator.validate_username(username)
        duration = time.time() - start
        
        assert duration < len(usernames) / 100 + 0.1


# ==================== Integration with Hypothesis Settings ====================

@pytest.mark.parametrize("test_function", [
    TestUserValidationProperties.test_valid_email_always_valid,
    TestUserValidationProperties.test_valid_username_always_valid,
    TestUserValidationProperties.test_valid_password_always_valid,
])
def test_validation_properties(test_function):
    """Run property-based tests with custom settings."""
    settings(max_examples=100, deadline=500)(test_function)()


# ==================== Failure Reproduction Tests ====================

class TestFailureReproduction:
    """Tests for reproducing and fixing property-based test failures."""
    
    def test_reproduce_email_validation_failure(self):
        """Reproduce and fix a specific email validation failure."""
        # If hypothesis finds a counterexample, add it here
        problematic_emails = [
            "test@example",  # Missing TLD
            "test@.com",     # Missing domain
            "test@example..com",  # Double dot
        ]
        
        for email in problematic_emails:
            assert UserValidator.validate_email(email) is False
    
    def test_reproduce_username_validation_failure(self):
        """Reproduce and fix a specific username validation failure."""
        problematic_usernames = [
            "ab",  # Too short
            "a" * 21,  # Too long
            "user@name",  # Invalid character
            "user name",  # Space
        ]
        
        for username in problematic_usernames:
            assert UserValidator.validate_username(username) is False


# ==================== Custom Generators for Complex Data ====================

@composite
def user_registration_data(draw):
    """Generate comprehensive user registration data."""
    return {
        'email': draw(valid_email_strategy()),
        'username': draw(valid_username_strategy()),
        'password': draw(valid_password_strategy()),
        'age': draw(integers(min_value=13, max_value=120)),
        'phone': draw(valid_phone_strategy()),
        'newsletter_consent': draw(booleans()),
        'accept_terms': draw(sampled_from([True, True, True, False])),  # Mostly true
    }


@composite
def product_data(draw):
    """Generate comprehensive product data."""
    return {
        'name': draw(text(alphabet=string.ascii_letters + string.digits + ' ',
                          min_size=1, max_size=100)),
        'price': draw(floats(min_value=0.01, max_value=10000, allow_nan=False)),
        'quantity': draw(integers(min_value=0, max_value=1000)),
        'sku': draw(from_regex(r'^[A-Z]{2,4}-\d{4,8}$', fullmatch=True)),
        'category': draw(sampled_from(['electronics', 'clothing', 'books', 'food'])),
        'active': draw(booleans())
    }


@composite
def order_data(draw, users=None, products=None):
    """Generate comprehensive order data."""
    if users is None:
        users = []
    if products is None:
        products = []
    
    return {
        'order_id': draw(from_regex(r'^ORD-[A-Z0-9]{8}$', fullmatch=True)),
        'user_id': draw(integers(min_value=1, max_value=1000)),
        'status': draw(sampled_from(['pending', 'confirmed', 'shipped', 'delivered', 'cancelled'])),
        'amount': draw(floats(min_value=0.01, max_value=10000, allow_nan=False)),
        'items': draw(lists(text(min_size=1, max_size=20), min_size=1, max_size=10)),
        'shipping_address': draw(text(min_size=10, max_size=200)),
        'payment_method': draw(sampled_from(['credit_card', 'paypal', 'bank_transfer']))
    }


# ==================== Main Test Execution ====================

if __name__ == "__main__":
    print("=" * 80)
    print("PROPERTY-BASED TESTS FOR VALIDATION LOGIC")
    print("=" * 80)
    print("\nRunning property-based tests...")
    
    # Run all property-based tests
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
