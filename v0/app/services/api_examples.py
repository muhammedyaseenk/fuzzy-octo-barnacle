# =====================================================
# AURUM MATRIMONY API USAGE EXAMPLES
# =====================================================

import requests
import json

BASE_URL = "http://localhost:8000"

# =====================================================
# 1️⃣ USER SIGNUP
# =====================================================

def signup_example():
    """Step 1: User signs up with basic info"""
    
    signup_data = {
        "phone": "+919876543210",
        "email": "john.doe@example.com",  # Optional
        "whatsapp_number": "+919876543210",  # Optional
        "first_name": "John",
        "last_name": "Doe",
        "password": "SecurePassword123"
    }
    
    response = requests.post(f"{BASE_URL}/signup", json=signup_data)
    print("Signup Response:", response.json())
    return response.json()["user_id"]

# =====================================================
# 2️⃣ COMPLETE PROFILE
# =====================================================

def complete_profile_example(user_id):
    """Step 2: User completes mandatory profile details"""
    
    profile_data = {
        "profile": {
            "display_name": "John D",
            "date_of_birth": "1995-06-15",
            "gender": "Male",
            "marital_status": "Never Married",
            "height_cm": 175,
            "weight_kg": 70,
            "complexion": "Fair",
            "body_type": "Athletic",
            "blood_group": "O+",
            "country_id": 1,
            "state_id": 1,
            "district_id": 1,
            "city_id": 1,
            "current_location": "Kochi, Kerala",
            "native_place": "Thrissur, Kerala",
            "religion_id": 1,
            "caste_id": 1,
            "sub_caste": "Nair",
            "mother_tongue_id": 1,
            "diet": "Vegetarian",
            "smoking": "Never",
            "drinking": "Occasionally"
        },
        "education": {
            "degree_level": "Bachelor",
            "degree_name": "B.Tech Computer Science",
            "specialization": "Software Engineering",
            "university": "Kerala University",
            "graduation_year": 2017,
            "is_highest": True
        },
        "career": {
            "occupation": "Software Engineer",
            "company_name": "Tech Solutions Pvt Ltd",
            "designation": "Senior Developer",
            "annual_income": 1200000,
            "employment_type": "Employed",
            "is_current": True
        },
        "family": {
            "father_name": "Ravi Doe",
            "mother_name": "Priya Doe",
            "family_type": "Nuclear",
            "family_status": "Middle Class",
            "total_siblings": 1,
            "family_contact_person": "Ravi Doe",
            "family_contact_phone": "+919876543211"
        },
        "preferences": {
            "preferred_age_min": 22,
            "preferred_age_max": 28,
            "preferred_height_min": 155,
            "preferred_height_max": 170,
            "preferred_religions": [1],
            "preferred_castes": [1, 2, 3],
            "preferred_income_min": 500000,
            "willing_to_relocate": True,
            "partner_expectations": "Looking for a caring and understanding partner"
        }
    }
    
    response = requests.post(f"{BASE_URL}/complete-profile/{user_id}", json=profile_data)
    print("Profile Completion Response:", response.json())

# =====================================================
# 3️⃣ CHECK VERIFICATION STATUS
# =====================================================

def check_verification_status(user_id):
    """Step 3: Check if admin has approved the user"""
    
    response = requests.get(f"{BASE_URL}/verification-status/{user_id}")
    print("Verification Status:", response.json())

# =====================================================
# 4️⃣ ADMIN OPERATIONS
# =====================================================

def admin_get_pending_verifications():
    """Admin: Get all pending user verifications"""
    
    response = requests.get(f"{BASE_URL}/admin/pending-verifications")
    print("Pending Verifications:", response.json())

def admin_verify_user(user_id, approved=True, notes="Profile looks good"):
    """Admin: Approve or reject user"""
    
    data = {
        "approved": approved,
        "admin_notes": notes
    }
    
    response = requests.post(f"{BASE_URL}/admin/verify-user/{user_id}", params=data)
    print("Admin Verification Response:", response.json())

# =====================================================
# 5️⃣ COMPLETE WORKFLOW EXAMPLE
# =====================================================

def complete_onboarding_workflow():
    """Complete user onboarding workflow"""
    
    print("🚀 Starting Aurum Matrimony Onboarding...")
    
    # Step 1: User Signup
    print("\n1️⃣ User Signup...")
    user_id = signup_example()
    
    # Step 2: Complete Profile
    print("\n2️⃣ Completing Profile...")
    complete_profile_example(user_id)
    
    # Step 3: Check Status (Pending)
    print("\n3️⃣ Checking Status...")
    check_verification_status(user_id)
    
    # Step 4: Admin Reviews
    print("\n4️⃣ Admin Review Process...")
    admin_get_pending_verifications()
    
    # Step 5: Admin Approves
    print("\n5️⃣ Admin Approval...")
    admin_verify_user(user_id, approved=True, notes="Excellent profile, approved for platform")
    
    # Step 6: Final Status Check
    print("\n6️⃣ Final Status Check...")
    check_verification_status(user_id)
    
    print("\n✅ User onboarding completed successfully!")

if __name__ == "__main__":
    complete_onboarding_workflow()