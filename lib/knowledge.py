import os
import multiprocessing
from typing import cast
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
# from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource
# from crewai.knowledge.source.csv_knowledge_source import CSVKnowledgeSource
from crewai.rag.config.types import ChromaDBConfig
from crewai.rag.chromadb.types import ChromaEmbeddingFunctionWrapper
from crewai.rag.embeddings.factory import build_embedder
from crewai.rag.config.utils import set_rag_config
from crewai.knowledge.knowledge import Knowledge
from chromadb.config import Settings
from lib.utils import get_embedder_config_from_env, get_db_storage_path


def init_rag_countext():
    from crewai.rag.config.utils import _rag_context
    if _rag_context.get() is None:
        embedding = build_embedder(get_embedder_config_from_env())
        set_rag_config(
            config=ChromaDBConfig(
                batch_size=64, # ai api 限制
                embedding_function=cast(
                    ChromaEmbeddingFunctionWrapper, embedding
                ),
                setting=Settings(
                    persist_directory=get_db_storage_path(),
                    allow_reset=True,
                    is_persistent=True,
                )
            )
        )
    return _rag_context.get()


def find_files_by_extensions(directory, extensions, recursive=True, relative_path=False, prefix=None):
    """
    简洁版本的文件查找函数
    """
    # 处理后缀
    exts = [ext if ext.startswith('.') else '.' + ext for ext in extensions]
    exts = [ext.lower() for ext in exts]
    
    # 查找文件
    if recursive:
        files = [os.path.join(root, f) for root, _, files in os.walk(directory) 
                for f in files if os.path.splitext(f)[1].lower() in exts]
    else:
        files = [os.path.join(directory, f) for f in os.listdir(directory) 
                if os.path.isfile(os.path.join(directory, f)) and 
                os.path.splitext(f)[1].lower() in exts]
    
    # 路径处理
    if relative_path:
        files = [os.path.relpath(f, directory) for f in files]
    if prefix:
        files = [os.path.join(prefix, f) for f in files]
    
    return files


text_source = None
if text_source is None:
    file_paths = []
    knowledge_dir = "knowledge"
    for key in os.listdir(knowledge_dir):
        if key != "ctf": # 只处理ctf目录，具体自行调节
            continue
        key_path = os.path.join(knowledge_dir, key)
        if os.path.isdir(key_path):
            file_paths += find_files_by_extensions(key_path, ["md", "txt"], recursive=True, relative_path=True, prefix=key)

    text_source = TextFileKnowledgeSource(
        chunk_size=1000,  # Maximum size of each chunk (default: 4000)
        chunk_overlap=50,  # Overlap between chunks (default: 200)
        file_paths= file_paths
    )


_knowledge_SINGLETON = None
_lock = multiprocessing.Lock()
def get_knowledge():
    global _knowledge_SINGLETON
    if _knowledge_SINGLETON is not None:
        return _knowledge_SINGLETON
    rag_context = init_rag_countext()
    with _lock:
        if _knowledge_SINGLETON is None:
            knowledge = Knowledge(
                sources=[text_source],
                collection_name="ctf",
            )
            knowledge.add_sources()
            knowledge.storage._client = rag_context.client
            _knowledge_SINGLETON = knowledge
    return _knowledge_SINGLETON