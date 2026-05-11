import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

def main():
    load_dotenv()

    required_vars = ["SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    email = sys.argv[1] if len(sys.argv) > 1 else "user1@example.com"

    try:
        supabase: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_PUBLISHABLE_KEY"]
        )
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)

    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": "testpass123"})

        if response.session and response.session.access_token:
            token = response.session.access_token
            print(f"✅ Token for {email}:\n")
            print(f"Authorization: Bearer {token}")
        else:
            print("❌ Failed to generate token")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
