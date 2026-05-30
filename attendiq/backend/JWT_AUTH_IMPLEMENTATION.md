# JWT Authentication & Protected Routes Guide
# ============================================================
#  AttendIQ — JWT Authentication Implementation
#  Generated: May 29, 2026
# ============================================================

## Files Modified

1. **backend/app/dependencies/auth.py** (NEW)
   - JWT authentication dependency module
   - `get_current_user` dependency: Extracts Bearer token, validates with Supabase, returns authenticated user
   - Proper 401 error handling with WWW-Authenticate header

2. **backend/app/dependencies/__init__.py** (NEW)
   - Package initialization file
   - Exports `get_current_user` for reuse

3. **backend/app/routes/auth.py** (UPDATED)
   - Simplified `/auth/me` endpoint to use the `get_current_user` dependency
   - Removed manual header parsing (now handled by dependency)
   - Cleaner, more Pythonic code


## How It Works

### JWT Dependency Flow

```
HTTP Request with Authorization Header
           ↓
FastAPI Route Handler
           ↓
get_current_user Dependency (Automatic)
           ↓
Extract Bearer Token from Header
           ↓
Validate Token with Supabase
           ↓
Fetch User Profile from DB
           ↓
Return UserResponse or 401 Error
           ↓
Route Handler Receives Current User
```

### Using the Dependency in Routes

To protect any route, simply add `current_user: UserResponse = Depends(get_current_user)`:

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import UserResponse

router = APIRouter()

@router.get("/protected")
def protected_route(current_user: UserResponse = Depends(get_current_user)):
    """This route requires a valid Bearer token."""
    return {"message": f"Hello, {current_user.full_name}"}

@router.post("/another-protected")
def another_protected(current_user: UserResponse = Depends(get_current_user)):
    """Access the authenticated user here."""
    return {"user_id": current_user.id, "role": current_user.role}
```


## Testing in Swagger UI

### 1. Access Swagger at http://localhost:8000/docs

### 2. Test Endpoints

#### **POST /auth/register** (No token required)
1. Click "Try it out"
2. Enter JSON:
   ```json
   {
     "full_name": "Test Student",
     "email": "test.student@college.edu",
     "password": "SecurePassword123!",
     "role": "student",
     "department_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
     "roll_number": "CS2021001",
     "phone": "9876543210"
   }
   ```
3. Click "Execute"
4. Response (201 Created):
   ```json
   {
     "id": "uuid-here",
     "full_name": "Test Student",
     "email": "test.student@college.edu",
     "role": "student",
     "department_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
     "roll_number": "CS2021001",
     "phone": "9876543210",
     "is_active": true,
     "face_enrolled": false,
     "voice_enrolled": false
   }
   ```

#### **POST /auth/login** (No token required)
1. Click "Try it out"
2. Enter JSON:
   ```json
   {
     "email": "test.student@college.edu",
     "password": "SecurePassword123!"
   }
   ```
3. Click "Execute"
4. Response (200 OK):
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "user": {
       "id": "uuid-here",
       "full_name": "Test Student",
       "email": "test.student@college.edu",
       "role": "student",
       ...
     }
   }
   ```
5. **Copy the `access_token` value** (you'll need it for protected routes)

#### **GET /auth/me** (Requires Bearer token)
1. Click "Try it out"
2. Click on "Authorize" button (top-right of Swagger UI)
3. In the modal, enter:
   ```
   Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
   (Paste your access_token from the login response)
4. Click "Authorize" and close the modal
5. Go back to GET /auth/me and click "Try it out"
6. Click "Execute"
7. Response (200 OK):
   ```json
   {
     "id": "uuid-here",
     "full_name": "Test Student",
     "email": "test.student@college.edu",
     "role": "student",
     ...
   }
   ```

### Testing Without Swagger (cURL)

#### Register:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Student",
    "email": "test.student@college.edu",
    "password": "SecurePassword123!",
    "role": "student",
    "department_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "roll_number": "CS2021001"
  }'
```

#### Login:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test.student@college.edu",
    "password": "SecurePassword123!"
  }'
```

#### Get Current User (with Bearer token):
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Test Missing Token (should return 401):
```bash
curl -X GET http://localhost:8000/auth/me
```

Response:
```json
{"detail": "Authorization header missing."}
```

#### Test Invalid Token (should return 401):
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer invalid-token-here"
```

Response:
```json
{"detail": "Unable to validate the current user: [Supabase error details]"}
```


## Error Responses (401 Unauthorized)

All protected routes return 401 with `WWW-Authenticate: Bearer` header for these scenarios:

| Scenario | Response |
|----------|----------|
| Missing Authorization header | `{"detail": "Authorization header missing."}` |
| Invalid scheme (not Bearer) | `{"detail": "Invalid authorization scheme. Use 'Bearer <token>'."}`  |
| Empty token | `{"detail": "Bearer token missing."}` |
| Invalid token | `{"detail": "Unable to validate the current user: [error details]"}` |
| Expired token | `{"detail": "Unable to validate the current user: [error details]"}` |


## Creating Additional Protected Routes

Example: Protected faculty route to get attendance records

```python
# backend/app/routes/faculty.py
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import UserResponse, UserRole

router = APIRouter(prefix="/faculty", tags=["faculty"])

@router.get("/my-sessions")
def get_my_sessions(current_user: UserResponse = Depends(get_current_user)):
    """Get attendance sessions for the current faculty member."""
    # The dependency automatically ensures:
    # 1. Bearer token is present and valid
    # 2. User exists in profiles table
    # 3. current_user contains full user data
    
    if current_user.role != UserRole.faculty:
        raise HTTPException(
            status_code=403,
            detail="Only faculty can access this resource."
        )
    
    # Fetch and return sessions for this faculty member
    return {"faculty_id": current_user.id, "sessions": []}
```


## Key Benefits

✅ **Single Source of Truth**: Token validation logic in one place  
✅ **Reusable**: Use `Depends(get_current_user)` on any route  
✅ **Clean**: No manual header parsing in route handlers  
✅ **Type-Safe**: FastAPI provides full IDE autocomplete  
✅ **Production-Ready**: Proper error handling and WWW-Authenticate headers  
✅ **Secure**: Automatic 401 responses for missing/invalid tokens  
✅ **Easy Testing**: Works seamlessly with Swagger UI


## Implementation Details

### Dependency Injection
- FastAPI automatically injects the `Authorization` header
- Dependency validates and returns `UserResponse` object
- If validation fails, FastAPI automatically returns 401 error
- Route handler never receives invalid/missing tokens

### Token Validation Flow
1. Extract Bearer token from header
2. Call `get_current_user_service(access_token=token)` from auth_service
3. This calls `supabase.auth.get_user(jwt=token)`
4. Fetches user profile from `profiles` table by user ID
5. Returns complete `UserResponse` object

### Error Handling
- All exceptions caught and converted to 401 HTTPException
- `WWW-Authenticate` header included for standards compliance
- Supabase error details included in response for debugging
