"""Test captcha verification API endpoint."""
import requests

BASE_URL = "http://localhost:8000"

def test_captcha_correct():
    """Test with correct captcha (user1's password)."""
    response = requests.post(
        f"{BASE_URL}/api/auth/captcha/verify",
        json={"code": "123456"}
    )
    print(f"✓ Correct captcha test: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_captcha_wrong():
    """Test with wrong captcha."""
    response = requests.post(
        f"{BASE_URL}/api/auth/captcha/verify",
        json={"code": "wrong_code"}
    )
    print(f"✓ Wrong captcha test: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["success"] is False

if __name__ == "__main__":
    print("Testing captcha verification API...")
    print("Note: Make sure the backend server is running on http://localhost:8000\n")

    try:
        test_captcha_correct()
        test_captcha_wrong()
        print("\n✅ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to backend server.")
        print("Please start the server with: uvicorn api.main:app --reload")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
