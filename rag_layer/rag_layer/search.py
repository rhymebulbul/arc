from .ingest import get_client, get_embedding_model, COLLECTION_NAME

def hybrid_search(query: str, limit: int = 5):
    client = get_client()
    model = get_embedding_model()
    
    if not client.collection_exists(COLLECTION_NAME):
        return []
        
    query_vector = list(model.embed([query]))[0].tolist()
    
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit
    )
    
    return [{"path": hit.payload.get("path"), "score": hit.score, "content": hit.payload.get("content")} for hit in results.points]
