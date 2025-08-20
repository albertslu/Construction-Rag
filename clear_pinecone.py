#!/usr/bin/env python3
"""
Clear Pinecone index
"""
import os
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings
import pinecone

def clear_pinecone_index():
    """Clear all vectors from the Pinecone index"""
    print(f"🗑️  Clearing Pinecone index: {settings.pinecone_index_name}")
    print(f"🗑️  Namespace: {settings.pinecone_namespace}")
    
    # Initialize Pinecone
    pc = pinecone.Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(settings.pinecone_index_name)
    
    # Delete all vectors in the namespace
    try:
        index.delete(delete_all=True, namespace=settings.pinecone_namespace)
        print(f"✅ Cleared namespace: {settings.pinecone_namespace}")
        return True
    except Exception as e:
        print(f"❌ Error clearing index: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Clearing Pinecone index...")
    if clear_pinecone_index():
        print("✅ Index cleared successfully!")
    else:
        print("❌ Failed to clear index!")

