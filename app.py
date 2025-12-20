"""
Simplified RAG Service API - Returns only retrieved chunks
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from RAGService import RAGService

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="RAG Service - Chunks API",
    description="Simple RAG API that returns retrieved chunks only",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Service
try:
    rag_service = RAGService(
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    print("✓ RAG Service initialized successfully")
except Exception as e:
    print(f"ERROR: Failed to initialize RAG Service: {str(e)}")
    raise


# ============================================================
# Request/Response Models
# ============================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    query: str
    collection_name: Optional[str] = None
    collection_names: Optional[List[str]] = None
    top_k: int = 5

    def get_collections(self) -> Optional[List[str]]:
        """Get list of collections from either field"""
        if self.collection_names:
            return self.collection_names
        elif self.collection_name:
            return [self.collection_name]
        return None


class RetrievedChunk(BaseModel):
    """Model for a single retrieved chunk"""
    text: str
    score: Optional[float] = None
    metadata: Optional[dict] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    query: str
    chunks: List[RetrievedChunk]
    total_chunks: int
    collections_searched: Optional[List[str]] = None


class DataIngestionRequest(BaseModel):
    """Request model for data ingestion"""
    text: Optional[str] = None
    pdf_path: Optional[str] = None
    excel_path: Optional[str] = None
    url: Optional[str] = None
    collection_name: str = "main_collection"


class StatusResponse(BaseModel):
    """Generic status response"""
    status: str
    message: str
    details: Optional[dict] = None


class DeleteCollectionRequest(BaseModel):
    """Request model for deleting a collection"""
    collection_name: str


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "RAG Service - Chunks API (FAISS-based)",
        "version": "1.0.0",
        "documentation": "/docs",
        "description": "Simple RAG API that returns only retrieved chunks without LLM generation",
        "storage": "FAISS (local vector database)",
        "endpoints": {
            "POST /chat": "Retrieve relevant chunks from knowledge base",
            "POST /data_ingestion": "Ingest data from multiple sources (PDF, Excel, URL)",
            "POST /data_ingestion_file": "Upload and ingest files (PDF, Excel)",
            "GET /collections": "List all collections with document counts",
            "POST /delete_collection": "Delete a specific collection",
            "POST /clear_index": "Clear the entire FAISS index",
            "GET /stats": "Get FAISS index statistics",
            "GET /health": "Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RAG Service - Chunks API",
        "rag_service": "operational"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Retrieve relevant chunks from knowledge base without LLM generation.
    
    Args:
        request: ChatRequest containing:
            - query: User's question
            - collection_name: Single collection name (optional)
            - collection_names: List of collection names (optional)
            - top_k: Number of chunks to retrieve (default: 5)
    
    Returns:
        ChatResponse with retrieved chunks only
    
    Examples:
        Single collection:
        {
            "query": "What is insurance?",
            "collection_name": "insurance_docs",
            "top_k": 3
        }
        
        Multiple collections:
        {
            "query": "Compare products",
            "collection_names": ["products", "pricing"],
            "top_k": 5
        }
        
        Search all collections:
        {
            "query": "What is AI?",
            "top_k": 5
        }
    """
    try:
        # Get collections list
        collections = request.get_collections()
        
        print(f"📥 Chat request - Query: '{request.query}', Collections: {collections or 'ALL'}, Top-K: {request.top_k}")
        
        # Perform retrieval-based search
        search_results = rag_service.retrieval_based_search(
            query=request.query,
            collections=collections,
            top_k=request.top_k
        )
        
        if not search_results:
            print(f"⚠️ No results found for query: '{request.query}'")
            return ChatResponse(
                query=request.query,
                chunks=[],
                total_chunks=0,
                collections_searched=collections
            )
        
        # Format chunks
        chunks = []
        for result in search_results:
            chunk = RetrievedChunk(
                text=result.get('text', ''),
                score=result.get('score'),
                metadata=result.get('metadata', {})
            )
            chunks.append(chunk)
        
        print(f"✓ Found {len(chunks)} chunks")
        
        return ChatResponse(
            query=request.query,
            chunks=chunks,
            total_chunks=len(chunks),
            collections_searched=collections
        )
        
    except Exception as e:
        print(f"ERROR in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/data_ingestion", response_model=StatusResponse)
async def data_ingestion(request: DataIngestionRequest):
    """
    Ingest data from various sources into FAISS index.
    
    Supports: PDF, Excel, and URLs
    Note: Direct text ingestion not supported - use PDF/Excel/URL sources
    """
    try:
        print(f"📥 Data ingestion request - Collection: '{request.collection_name}'")
        
        source_type = None
        
        # Process based on data source using load_data method directly
        if request.pdf_path:
            source_type = "pdf"
            print(f"  Source: PDF file - {request.pdf_path}")
            print(f"  Loading into FAISS index with collection: '{request.collection_name}'")
            
            rag_service.load_data(
                collection_name=request.collection_name,
                pdf_file=request.pdf_path
            )
            
        elif request.excel_path:
            source_type = "excel"
            print(f"  Source: Excel file - {request.excel_path}")
            print(f"  Loading into FAISS index with collection: '{request.collection_name}'")
            
            rag_service.load_data(
                collection_name=request.collection_name,
                excel_file=request.excel_path
            )
            
        elif request.url:
            source_type = "url"
            print(f"  Source: URL - {request.url}")
            print(f"  Loading into FAISS index with collection: '{request.collection_name}'")
            
            rag_service.load_data(
                collection_name=request.collection_name,
                url_link=request.url
            )
            
        elif request.text:
            # For text, we need to save it temporarily and load it
            raise HTTPException(
                status_code=400,
                detail="Direct text ingestion not supported. Please use pdf_path, excel_path, or url"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="No data source provided. Provide one of: pdf_path, excel_path, or url"
            )
        
        print(f"✓ Data ingestion completed successfully")
        
        return StatusResponse(
            status="success",
            message="Data ingested successfully",
            details={
                "collection_name": request.collection_name,
                "source_type": source_type
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in data_ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")


@app.post("/data_ingestion_file", response_model=StatusResponse)
async def data_ingestion_file(
    file: UploadFile = File(...),
    collection_name: str = Form("main_collection")
):
    """
    Ingest data from uploaded file (PDF, Excel).
    """
    try:
        print(f"📥 File upload - Filename: '{file.filename}', Collection: '{collection_name}'")
        
        # Save uploaded file temporarily
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            # Determine file type and process
            file_ext = file.filename.lower().split('.')[-1]
            
            if file_ext == 'pdf':
                rag_service.load_data(
                    collection_name=collection_name,
                    pdf_file=tmp_path
                )
                source_type = "pdf"
            elif file_ext in ['xlsx', 'xls']:
                rag_service.load_data(
                    collection_name=collection_name,
                    excel_file=tmp_path
                )
                source_type = "excel"
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}. Supported: pdf, xlsx, xls")
            
            print(f"✓ File ingestion completed successfully")
            
            return StatusResponse(
                status="success",
                message="File ingested successfully",
                details={
                    "filename": file.filename,
                    "collection_name": collection_name,
                    "source_type": source_type
                }
            )
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File ingestion failed: {str(e)}")


@app.post("/clear_index", response_model=StatusResponse)
async def clear_index():
    """
    Clear the entire FAISS index.
    """
    try:
        print(f"📥 Clear index request")
        
        rag_service.clear_index()
        
        print(f"✓ Index cleared successfully")
        
        return StatusResponse(
            status="success",
            message="FAISS index cleared successfully"
        )
        
    except Exception as e:
        print(f"ERROR clearing index: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {str(e)}")


@app.get("/stats")
async def get_stats():
    """
    Get FAISS index statistics.
    """
    try:
        stats = rag_service.get_stats()
        
        print(f"✓ Retrieved stats")
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        print(f"ERROR getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/collections")
async def list_collections():
    """
    Get list of all collections and their document counts.
    
    Returns:
        Dictionary with collection names and their respective document counts
    
    Example Response:
        {
            "status": "success",
            "total_collections": 3,
            "collections": {
                "langchain": 150,
                "insurance_docs": 75,
                "product_info": 200
            }
        }
    """
    try:
        stats = rag_service.get_stats()
        collections = stats.get("collections", {})
        
        print(f"✓ Found {len(collections)} collections")
        
        return {
            "status": "success",
            "total_collections": len(collections),
            "collections": collections
        }
        
    except Exception as e:
        print(f"ERROR listing collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@app.post("/delete_collection", response_model=StatusResponse)
async def delete_collection(request: DeleteCollectionRequest):
    """
    Delete a specific collection from the FAISS index.
    
    Note: FAISS doesn't support efficient deletion, so the index will be rebuilt
    without the specified collection's vectors.
    
    Args:
        request: DeleteCollectionRequest containing collection_name
    
    Example Request:
        {
            "collection_name": "langchain"
        }
    """
    try:
        print(f"📥 Delete collection request - Collection: '{request.collection_name}'")
        
        # Check if collection exists
        stats = rag_service.get_stats()
        collections = stats.get("collections", {})
        
        if request.collection_name not in collections:
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{request.collection_name}' not found. Available collections: {list(collections.keys())}"
            )
        
        docs_count = collections[request.collection_name]
        
        # Delete the collection
        rag_service.delete_collection(request.collection_name)
        
        print(f"✓ Collection '{request.collection_name}' deleted successfully ({docs_count} documents removed)")
        
        return StatusResponse(
            status="success",
            message=f"Collection '{request.collection_name}' deleted successfully",
            details={
                "collection_name": request.collection_name,
                "documents_removed": docs_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR deleting collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting RAG Service - Chunks API...")
    print("📖 Documentation available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

