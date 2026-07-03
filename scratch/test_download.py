import sys
import os

# Append project root directory to path to resolve imports correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.models import User

app.config['TESTING'] = True

with app.app_context():
    user = User.query.first()
    print("Using user:", user.username if user else "None")
    if not user:
        sys.exit(1)
        
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
        
    res = client.get('/report/download/AAPL')
    print("Response Status Code:", res.status_code)
    print("Content Length:", len(res.data))
    print("Headers:", dict(res.headers))
    if len(res.data) > 0:
        print("First 100 bytes:", res.data[:100])
        # Save it to check if it opens
        with open('scratch/downloaded_from_client.pdf', 'wb') as f:
            f.write(res.data)
        print("Saved to scratch/downloaded_from_client.pdf")
