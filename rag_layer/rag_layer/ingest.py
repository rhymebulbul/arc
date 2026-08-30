import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding
from mcp_ast_server.parser import parse_file

DB_PATH = os.path.join(os.path.dirname(__file__), "qdrant_db")
COLLECTION_NAME = "arc_codebase"

def get_client():
    return QdrantClient(path=DB_PATH)

def get_embedding_model():
    return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def extract_skeleton_and_chunks(repo_path: str):
    skeleton_lines = []
    chunks = []
    
    for root, dirs, files in os.walk(repo_path):
        if '.git' in root or 'venv' in root or '__pycache__' in root or 'qdrant_db' in root:
            continue
            
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            skeleton_lines.append(f"File: {rel_path}")
            
            try:
                tree, src = parse_file(file_path)
            except Exception:
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks.append({
                "path": rel_path,
                "content": content
            })
            
            def walk_nodes(node):
                if node.type == 'function_definition':
                    name = node.child_by_field_name('name')
                    if name:
                        func_name = src[name.start_byte:name.end_byte].decode('utf8')
                        skeleton_lines.append(f"  Function: {func_name}")
                elif node.type == 'class_definition':
                    name = node.child_by_field_name('name')
                    if name:
                        class_name = src[name.start_byte:name.end_byte].decode('utf8')
                        skeleton_lines.append(f"  Class: {class_name}")
                
                for child in node.children:
                    walk_nodes(child)
                    
            walk_nodes(tree.root_node)
            
    return "\n".join(skeleton_lines), chunks

def ingest_repo(repo_path: str):
    client = get_client()
    model = get_embedding_model()
    
    # We use 384 dimensions for bge-small-en-v1.5
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        
    skeleton, chunks = extract_skeleton_and_chunks(repo_path)
    
    skeleton_path = os.path.join(repo_path, 'repo_skeleton.txt')
    with open(skeleton_path, 'w', encoding='utf-8') as f:
        f.write(skeleton)
        
    documents = [c["content"] for c in chunks]
    if not documents:
        return skeleton_path, 0
        
    embeddings = list(model.embed(documents))
    
    points = [
        PointStruct(
            id=i,
            vector=embedding.tolist(),
            payload={"path": chunks[i-1]["path"], "content": documents[i-1]}
        )
        for i, embedding in enumerate(embeddings, start=1)
    ]
    
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    
    return skeleton_path, len(documents)

if __name__ == "__main__":
    ingest_repo(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
