from app import create_app
app = create_app()

with app.test_client() as c:
    c.post('/register', data={'username':'uiuser99','email':'ui99@test.com','password':'pass1234','confirm_password':'pass1234'})
    c.post('/login', data={'username':'uiuser99','password':'pass1234'})

    checks = [
        ('/models',  'ML Studio'),
        ('/chatbot', 'AI Assistant'),
        ('/symbols', None),
        ('/api/stock/AAPL/summary', None),
    ]
    for url, keyword in checks:
        r = c.get(url, follow_redirects=True)
        assert r.status_code == 200, f'GET {url} -> {r.status_code}'
        if keyword:
            assert keyword.encode() in r.data, f'Keyword "{keyword}" missing from {url}'
        print(f'GET {url}: OK (200){" -- keyword found" if keyword else ""}')

    r = c.post('/api/predict/AAPL', json={'model': 'XGBoost'})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('success') == True, f'Predict failed: {data}'
    print(f'POST /api/predict/AAPL: OK -- predicted ${data["predicted_price"]:.2f}')

print()
print('ALL VALIDATION CHECKS PASSED')
