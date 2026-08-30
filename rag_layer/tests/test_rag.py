import os
from rag_layer.ingest import ingest_repo
from rag_layer.search import hybrid_search

def test_ingestion_and_search():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../mcp_ast_server/tests"))
    
    skeleton_path, count = ingest_repo(repo_path)
    
    assert os.path.exists(skeleton_path)
    assert count > 0
    
    with open(skeleton_path, 'r') as f:
        skeleton = f.read()
        
    assert 'PaymentGateway' in skeleton
    assert 'calculate_tax' in skeleton
    
    results = hybrid_search("PaymentGateway calculate_tax")
    assert len(results) > 0
    
    found = False
    for res in results:
        if 'dummy_code.py' in res['path']:
            found = True
            break
            
    assert found
