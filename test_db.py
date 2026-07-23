from database import init_db, save_assessment, get_assessments, create_user, verify_user
import uuid

init_db()

username = f"testuser_{uuid.uuid4().hex[:6]}"
email = f"{username}@example.com"
password = "password123"

print("Creating user...")
success = create_user(username, email, password)
print(f"User creation: {'SUCCESS' if success else 'FAILED'}")

print("Verifying user...")
user = verify_user(username, password)
print(f"User verification: {'SUCCESS' if user else 'FAILED'}")

if user:
    user_id = user['id']
    save_assessment(
        user_id,
        "Car",
        20,
        250,
        "Non-Vegetarian",
        2,
        3200,
        65
    )
    
    print(get_assessments(user_id))