# 
# Test the functions in base/views/primary.py file
# 

def test_primary(client):
    response = client.get('https://localhost:8080/')
    assert response.status_code == 200
    assert b'Caenorhabditis elegans Natural Diversity Resource' in response.data