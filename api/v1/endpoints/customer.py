from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
import httpx
import os

router = APIRouter()

class VerifyTokenRequest(BaseModel):
    access_token: str
    customer_id: str
    store_id: str

@router.post("/api/v1/customer/verify-token")
async def verify_customer_token(
    request: VerifyTokenRequest,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    # Verify API key
    if x_api_key != os.environ.get('UN360_API_KEY'):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Call Shopify Customer Account API (no CORS on server)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://shopify.com/account/api/2024-01/graphql.json',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {request.access_token}'
                },
                json={
                    'query': '{ customer { id email firstName lastName displayName } }'
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return {
                    'verified': False,
                    'error': f'Shopify API returned {response.status_code}'
                }
            
            data = response.json()
            customer = data.get('data', {}).get('customer')
            
            if not customer:
                return {'verified': False, 'error': 'No customer in response'}
            
            # Verify the customer ID matches
            returned_id = customer['id'].split('/')[-1]
            if returned_id != request.customer_id:
                return {'verified': False, 'error': 'Customer ID mismatch'}
            
            return {
                'verified': True,
                'customerId': returned_id,
                'email': customer['email'],
                'name': customer.get('displayName') or f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
            }
            
    except httpx.TimeoutException:
        return {'verified': False, 'error': 'Shopify API timeout'}
    except Exception as e:
        print(f"Customer verification error: {e}")
        return {'verified': False, 'error': str(e)}