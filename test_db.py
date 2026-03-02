import os
import sys

sys.path.append(os.getcwd())

from app.core.database import get_supabase
from app.crud.crud_user import user as crud_user

def main():
    try:
        db = get_supabase()
        res = crud_user.get_by_username(db, "keerthu_test_no_exist")
        print("Success, res is:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
