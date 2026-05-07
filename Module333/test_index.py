import os
import json
import re
import time
import pickle
from inverted_index import InvertedIndex


# 分词函数（简单提取俄语/英语单词）
def tokenize(text):
    # 匹配字母（包括俄语）
    return re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]+\b', text.lower())


def load_real_docs(jsonl_path):
    docs = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for doc_id, line in enumerate(f):
            data = json.loads(line)
            text = data.get('text', '')
            tokens = tokenize(text)
            if tokens:
                docs[doc_id] = tokens
    return docs


def build_index(docs):
    idx = InvertedIndex()
    start = time.time()
    for doc_id, tokens in docs.items():
        idx.add_document(doc_id, tokens)
    idx.build()
    build_time = time.time() - start
    return idx, build_time


def compare_compression(idx):
    # 未压缩大小（pickle）
    unp_path = "uncompressed.idx"
    with open(unp_path, 'wb') as f:
        pickle.dump((dict(idx.index), idx.doc_count), f)
    uncompressed_size = os.path.getsize(unp_path)
    os.remove(unp_path)

    results = {'uncompressed': uncompressed_size}
    for method in ['gamma', 'delta', 'golomb']:
        path = f"compressed_{method}.idx"
        idx.save_compressed(path, method=method)
        size = os.path.getsize(path)
        results[method] = size
        os.remove(path)
    return results


def query_speed(idx, query_terms, repeats=20):
    start = time.time()
    for _ in range(repeats):
        for term in query_terms:
            idx.search(term)
    elapsed = (time.time() - start) * 1000
    return elapsed / repeats  # ms per query (per term)


if __name__ == "__main__":
    docs = load_real_docs("E:\Module333\data\pages.jsonl")
    print(f"Loaded {len(docs)} documents")

    if len(docs) == 0:
        print("No documents loaded. Check pages.jsonl path and content.")
        exit()


    idx, build_time = build_index(docs)
    print(f"Index built in {build_time:.2f} sec")
    stats = idx.get_stats()
    print(f"Statistics: {stats}")


    print("\nCompression comparison:")
    sizes = compare_compression(idx)
    for k, v in sizes.items():
        print(f"  {k:12s}: {v / 1024:.2f} KB")
    if 'uncompressed' in sizes:
        uncomp = sizes['uncompressed']
        for m in ['gamma', 'delta', 'golomb']:
            if m in sizes:
                ratio = (1 - sizes[m] / uncomp) * 100
                print(f"  {m} saves {ratio:.1f}%")

    sample_terms = list(idx.index.keys())[:5]
    print(f"\nTest query terms: {sample_terms}")
    avg_time = query_speed(idx, sample_terms, repeats=10)
    print(f"Average query time: {avg_time:.3f} ms per term")